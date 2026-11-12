from datetime import timedelta
from uuid import uuid4

import pytest
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_messaging import incoming, reply
from test_messaging import wa as wa_fixture

from jordy.messaging.policy import error_diagnostic
from jordy.models import Message, Outbox

pytestmark = pytest.mark.usefixtures("messaging_enabled")


@pytest.fixture
def wa(database, monkeypatch):
    return wa_fixture.__wrapped__(database, monkeypatch)


@pytest.mark.parametrize(
    ("code", "category"),
    [
        ("http_400", "attempt"),
        ("send_policy_blocked", "attempt"),
        ("http_401_meta_190", "credential"),
        ("http_503", "provider_temporary"),
        ("http_429_meta_130429", "provider_temporary"),
        ("provider_result_unknown", "review"),
    ],
)
def test_safe_diagnostics(code, category):
    result = error_diagnostic(code)
    assert result["category"] == category
    assert result["code"] == code
    assert result["message"]
    assert error_diagnostic(None) is None


def test_original_message_scope_and_authentication(wa, database, client):
    c = incoming(wa, database)
    with Session(database) as s:
        message_id = s.scalar(select(Message.id).where(Message.conversation_id == c.id))
    path = f"/api/messaging/conversations/{c.id}/messages/{message_id}"
    assert client.get(path).status_code == 200
    assert (
        client.get(f"/api/messaging/conversations/{c.id + 999}/messages/{message_id}").status_code
        == 422
    )
    headers = dict(client.headers)
    client.headers.clear()
    assert client.get(path).status_code == 401
    client.headers.update(headers)


def test_historical_errors_do_not_become_current_config_alerts(wa, database, client):
    c = incoming(wa, database)
    assert client.get(f"/api/messaging/conversations/{c.id}").json()["needs_reply"]
    message = reply(client, c).json()
    with Session(database) as s, s.begin():
        row = s.get(Message, message["id"])
        row.status, row.error_code = "failed", "http_401_meta_190"
        job = s.scalar(
            select(Outbox).where(
                Outbox.payload["message_id"].as_integer() == row.id,
                Outbox.topic == "whatsapp.send",
            )
        )
        job.status = "failed"
    current = client.get("/api/messaging/config").json()
    assert current["provider_review"]["category"] == "credential"
    assert current["send_blocker_codes"] == []
    original_token = wa.whatsapp_access_token
    wa.whatsapp_access_token = SecretStr("different-test-credential")
    assert client.get("/api/messaging/config").json()["provider_review"] is None
    wa.whatsapp_access_token = original_token
    with Session(database) as s, s.begin():
        previous = s.get(Message, message["id"])
        delivered = Message(
            conversation_id=c.id,
            channel=c.channel,
            account_id=c.account_id,
            direction="outgoing",
            kind="text",
            body="Synthetic delivered response",
            status="delivered",
            details={},
            created_at=previous.created_at + timedelta(seconds=1),
            occurred_at=previous.occurred_at + timedelta(seconds=1),
        )
        s.add(delivered)
        s.flush()
        s.add(
            Outbox(
                topic="whatsapp.send",
                event_key="test:" + uuid4().hex,
                payload={
                    "message_id": delivered.id,
                    "send_config_revision": wa.send_config_revision(),
                },
                status="delivered",
                available_at=delivered.created_at,
            )
        )
    assert not client.get(f"/api/messaging/conversations/{c.id}").json()["needs_reply"]
    assert client.get("/api/messaging/config").json()["provider_review"] is None
    history = client.get(f"/api/messaging/conversations/{c.id}/messages").json()["items"]
    assert (
        next(m for m in history if m["id"] == message["id"])["diagnostic"]["code"]
        == "http_401_meta_190"
    )
