from datetime import timedelta
from uuid import uuid4

import httpx
import pytest
from pydantic import SecretStr
from sqlalchemy.orm import Session
from test_messaging import drain, incoming, post, reply, status_payload
from test_messaging import wa as wa_fixture

from jordy.messaging.config import ROOT, MessagingSettings, RecipientBinding
from jordy.messaging.policy import SendPolicyViolation, resolve_recipient
from jordy.messaging.provider import SendResult, WhatsAppAdapter
from jordy.messaging.service import validate_send
from jordy.messaging.worker import send_one
from jordy.models import Conversation, Message
from jordy.services import now

pytestmark = pytest.mark.usefixtures("messaging_enabled")


@pytest.fixture
def wa(database, monkeypatch):
    return wa_fixture.__wrapped__(database, monkeypatch)


INCOMING = "5215551234567"
OUTGOING = "525551234567"


def bind(config, target=OUTGOING, account=None):
    config.whatsapp_recipient_bindings = [
        RecipientBinding(
            account_id=account or config.whatsapp_business_account_id,
            phone_number_id=config.whatsapp_phone_number_id,
            external_contact=INCOMING,
            send_recipient=target,
        )
    ]
    config.whatsapp_allowed_recipients = [OUTGOING]


def test_binding_end_to_end_preserves_identity(wa, database, client):
    c = incoming(wa, database)
    bind(wa)
    assert validate_send(wa, c, "text", {}) == OUTGOING
    key = str(uuid4())
    response = reply(client, c, request_key=key)
    assert response.status_code == 202
    mid = response.json()["id"]
    assert reply(client, c, request_key=key).json()["id"] == mid
    external = "wamid." + uuid4().hex

    class Provider:
        calls = 0

        def send(self, recipient, *args):
            self.calls += 1
            assert recipient == OUTGOING
            return SendResult("accepted", external)

    provider = Provider()
    while send_one(database, wa, provider):
        pass
    assert provider.calls == 1
    assert post(wa, status_payload(wa, external, "delivered")).status_code == 200
    drain(database)
    with Session(database) as session:
        assert session.get(Conversation, c.id).external_contact == INCOMING
        m = session.get(Message, mid)
        assert m.status == "delivered" and m.details["send_recipient"] == OUTGOING
    assert not send_one(database, wa, provider)


def test_binding_required_not_country_heuristic(wa, database, client):
    c = incoming(wa, database)
    wa.whatsapp_allowed_recipients = [OUTGOING]
    assert reply(client, c).status_code == 422
    with pytest.raises(SendPolicyViolation, match="asociación") as error:
        resolve_recipient(wa, c)
    assert error.value.code == "recipient_unresolved"
    c.external_contact = "14155550100"
    wa.whatsapp_allowed_recipients = ["4155550100"]
    with pytest.raises(SendPolicyViolation):
        resolve_recipient(wa, c)


@pytest.mark.parametrize("case", ["unlisted_target", "wrong_account", "wrong_sender", "ambiguous"])
def test_binding_is_scoped_and_not_authorization(wa, database, client, case):
    c = incoming(wa, database)
    bind(wa)
    if case == "unlisted_target":
        wa.whatsapp_allowed_recipients = [INCOMING]
    elif case == "wrong_account":
        bind(wa, account="999999")
    elif case == "wrong_sender":
        wa.whatsapp_recipient_bindings[0] = wa.whatsapp_recipient_bindings[0].model_copy(
            update={"phone_number_id": "999999"}
        )
    else:
        wa.whatsapp_recipient_bindings *= 2
    assert reply(client, c).status_code == 422


@pytest.mark.parametrize("change", ["mapping", "allowlist", "token"])
def test_recheck_dispatch_and_never_retry_failed(wa, database, client, change):
    c = incoming(wa, database)
    bind(wa)
    mid = reply(client, c).json()["id"]
    if change == "mapping":
        new_target = "525559999999"
        wa.whatsapp_allowed_recipients.append(new_target)
        wa.whatsapp_recipient_bindings[0] = wa.whatsapp_recipient_bindings[0].model_copy(
            update={"send_recipient": new_target}
        )
    elif change == "allowlist":
        wa.whatsapp_allowed_recipients = [INCOMING]
    else:
        wa.whatsapp_access_token = SecretStr("different-test-token")

    class Forbidden:
        def send(self, *args):
            pytest.fail("Must not send changed/unapproved destination or config")

    while send_one(database, wa, Forbidden()):
        pass
    with Session(database) as session:
        m = session.get(Message, mid)
        assert m.status == "failed"
        assert (
            m.error_code
            == {
                "mapping": "send_recipient_changed",
                "allowlist": "recipient_not_authorized",
                "token": "send_config_changed",
            }[change]
        )
    assert not send_one(database, wa, Forbidden())


def test_bound_identity_still_needs_service_window(wa, database, client):
    c = incoming(wa, database, stamp=now() - timedelta(hours=25))
    bind(wa)
    assert reply(client, c).status_code == 422
    assert (
        reply(
            client,
            c,
            kind="template",
            body=None,
            template_name="hello_world",
            template_language="en_US",
        ).status_code
        == 202
    )


@pytest.mark.parametrize(
    "field,value,code",
    [
        ("whatsapp_send_enabled", False, "send_disabled"),
        ("whatsapp_token_rotated", False, "token_rotation_required"),
        ("whatsapp_access_token", SecretStr(""), "access_token_missing"),
        ("whatsapp_phone_number_id", "", "sender_config_invalid"),
    ],
)
def test_safe_policy_categories(wa, database, field, value, code):
    c = incoming(wa, database)
    setattr(wa, field, value)
    with pytest.raises(SendPolicyViolation) as error:
        validate_send(wa, c, "text", {})
    assert error.value.code == code
    assert INCOMING not in str(error.value) and "test-token" not in str(error.value)


def test_graph_to_exact_and_numeric_error_only(wa):
    import json

    bind(wa)

    def handler(request):
        assert json.loads(request.content)["to"] == OUTGOING
        return httpx.Response(
            400,
            json={
                "error": {
                    "code": 131030,
                    "message": "SECRET provider prose",
                    "fbtrace_id": "PRIVATE",
                }
            },
        )

    result = WhatsAppAdapter(wa, httpx.MockTransport(handler)).send(OUTGOING, "text", "test", {})
    assert result.error_code == "http_400_meta_131030"
    assert "SECRET" not in str(result) and "PRIVATE" not in str(result)


def test_config_paths_and_revision(monkeypatch, tmp_path):
    assert all(
        path.is_absolute() and path.parent == ROOT
        for path in MessagingSettings.model_config["env_file"]
    )
    config = MessagingSettings(
        _env_file=None, database_url="unused", whatsapp_access_token="test-only"
    )
    original = config.send_config_revision()
    monkeypatch.chdir(tmp_path)
    assert config.send_config_revision() == original
    assert "test-only" not in original
    config.whatsapp_access_token = SecretStr("test-replacement")
    assert config.send_config_revision() != original


@pytest.mark.parametrize(
    "case,code",
    [
        ("closed", "human_attention_required"),
        ("account", "sender_account_mismatch"),
        ("window", "service_window_expired"),
        ("template", "template_not_authorized"),
    ],
)
def test_remaining_policy_categories(wa, database, case, code):
    c = incoming(wa, database)
    kind, details = "text", {}
    if case == "closed":
        c.state = "closed"
    elif case == "account":
        c.phone_number_id = "999999"
    elif case == "window":
        c.last_incoming_at = now() - timedelta(hours=25)
    else:
        kind, details = "template", {"name": "unapproved", "language": "es"}
    with pytest.raises(SendPolicyViolation) as error:
        validate_send(wa, c, kind, details)
    assert error.value.code == code


def test_confirmation_destination_must_match(wa, database, client):
    c = incoming(wa, database)
    bind(wa)
    assert reply(client, c, expected_recipient=INCOMING).status_code == 422
    assert reply(client, c, expected_recipient=OUTGOING).status_code == 202
