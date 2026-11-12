import hashlib
import hmac
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from jordy.messaging import api as messaging_api
from jordy.messaging import webhook
from jordy.messaging.config import MessagingSettings
from jordy.messaging.provider import SendResult, WhatsAppAdapter
from jordy.messaging.worker import receive_one, send_one
from jordy.models import Booking, Conversation, Customer, Lead, Message, Outbox, Quote
from jordy.services import now
from jordy.worker import process_batch

pytestmark = pytest.mark.usefixtures("messaging_enabled")


@pytest.fixture
def wa(database, monkeypatch):
    config = MessagingSettings(
        _env_file=None,
        database_url="unused",
        whatsapp_send_enabled=True,
        whatsapp_token_rotated=True,
        whatsapp_access_token="test-token-not-a-real-secret",
        meta_app_secret="test-app-secret",
        meta_webhook_verify_token="test-verify-secret-32-characters-long",
        whatsapp_phone_number_id="123456",
        whatsapp_business_account_id=str(uuid4().int)[:20],
        meta_graph_api_version="v99.0",
        whatsapp_allowed_recipients=["5215551234567"],
        whatsapp_approved_templates=["hello_world:en_US"],
    )
    monkeypatch.setattr(webhook, "messaging_settings", lambda: config)
    monkeypatch.setattr(webhook, "webhook_engine", lambda: database)
    monkeypatch.setattr(messaging_api, "messaging_settings", lambda: config)

    def forbid_network(*args, **kwargs):
        raise AssertionError("Real network forbidden in messaging tests")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbid_network)
    return config


def payload(config, mid=None, sender="5215551234567", kind="text", stamp=None):
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": config.whatsapp_business_account_id,
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "metadata": {"phone_number_id": config.whatsapp_phone_number_id},
                            "contacts": [
                                {"wa_id": sender, "profile": {"name": "Nombre declarado"}}
                            ],
                            "messages": [
                                {
                                    "from": sender,
                                    "id": mid or "wamid." + uuid4().hex,
                                    "timestamp": str(int((stamp or now()).timestamp())),
                                    "type": kind,
                                    "text": {"body": "Consulta privada de prueba"},
                                    "image": {
                                        "id": "private-media-id",
                                        "url": "https://do-not-download.invalid",
                                    },
                                }
                            ],
                        },
                    }
                ],
            }
        ],
    }


def post(config, data, headers=None):
    raw = json.dumps(data).encode()
    signature = (
        "sha256="
        + hmac.new(
            config.meta_app_secret.get_secret_value().encode(), raw, hashlib.sha256
        ).hexdigest()
    )
    with TestClient(webhook.app) as client:
        return client.post(
            webhook.PATH,
            content=raw,
            headers=headers if headers is not None else {"X-Hub-Signature-256": signature},
        )


def drain(database):
    for _ in range(100):
        if not receive_one(database):
            return
    raise AssertionError("Inbound queue did not drain")


def incoming(wa, database, **kwargs):
    assert post(wa, payload(wa, **kwargs)).status_code == 200
    drain(database)
    with Session(database) as session:
        c = session.scalar(
            select(Conversation).where(Conversation.account_id == wa.whatsapp_business_account_id)
        )
        assert c is not None
        session.expunge(c)
        return c


def reply(client, c, **changes):
    body = dict(request_key=str(uuid4()), confirm_send=True, kind="text", body="Respuesta manual")
    body.update(changes)
    return client.post(f"/api/messaging/conversations/{c.id}/reply", json=body)


def counts(session):
    return [
        session.scalar(select(func.count()).select_from(m))
        for m in (Customer, Lead, Booking, Quote)
    ]


def test_verification_and_isolation(wa):
    with TestClient(webhook.app) as client:
        params = {
            "hub.mode": "subscribe",
            "hub.verify_token": wa.meta_webhook_verify_token.get_secret_value(),
            "hub.challenge": "1234",
        }
        r = client.get(webhook.PATH, params=params)
        assert r.status_code == 200 and r.text == "1234"
        for bad in ({}, {**params, "hub.verify_token": "wrong"}, {**params, "hub.mode": "invalid"}):
            r = client.get(webhook.PATH, params=bad)
            assert r.status_code == 403
            assert "test-verify" not in r.text
        for path in (
            "/",
            "/auth/local",
            "/auth/login",
            "/auth/config",
            "/api/customers",
            "/api/messaging/config",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            "/.env",
            "/.local/documents/x",
            "/webhooks/whatsapp/",
        ):
            for method in ("get", "post"):
                assert getattr(client, method)(path).status_code == 404
        for method in ("put", "delete", "patch", "options", "head"):
            assert getattr(client, method)(webhook.PATH).status_code == 405


@pytest.mark.parametrize("headers", [{}, {"X-Hub-Signature-256": "sha256=bad"}])
def test_bad_signature(wa, headers):
    assert post(wa, payload(wa), headers).status_code == 401


def test_tampered_large_invalid_and_wrong_account(wa):
    raw = json.dumps(payload(wa)).encode()
    signature = (
        "sha256="
        + hmac.new(wa.meta_app_secret.get_secret_value().encode(), raw, hashlib.sha256).hexdigest()
    )
    with TestClient(webhook.app) as client:
        assert (
            client.post(
                webhook.PATH, content=raw + b" ", headers={"X-Hub-Signature-256": signature}
            ).status_code
            == 401
        )
        assert (
            client.post(
                webhook.PATH, content=b"x" * (wa.whatsapp_max_webhook_bytes + 1)
            ).status_code
            == 413
        )
    assert post(wa, {"object": "bad"}).status_code == 400
    data = payload(wa)
    data["entry"][0]["id"] = "different"
    assert post(wa, data).status_code == 400
    data = payload(wa)
    data["entry"][0]["changes"][0]["value"]["metadata"]["phone_number_id"] = "other"
    assert post(wa, data).status_code == 400


def test_storage_failure_retries(wa, database, monkeypatch):
    data = payload(wa)
    original = webhook.persist

    def fail(events):
        raise RuntimeError("SECRET MUST NEVER APPEAR")

    monkeypatch.setattr(webhook, "persist", fail)
    r = post(wa, data)
    assert r.status_code == 503 and "SECRET" not in r.text
    monkeypatch.setattr(webhook, "persist", original)
    assert post(wa, data).status_code == 200
    drain(database)
    with Session(database) as session:
        assert (
            session.scalar(
                select(func.count(Message.id)).where(
                    Message.account_id == wa.whatsapp_business_account_id
                )
            )
            == 1
        )


def test_concurrent_duplicate_and_no_automatic_business(wa, database):
    data = payload(wa, sender=str(uuid4().int)[:13])
    with Session(database) as session:
        before = counts(session)
    with ThreadPoolExecutor(max_workers=4) as pool:
        responses = list(pool.map(lambda _: post(wa, data), range(8)))
    assert all(r.status_code == 200 for r in responses)
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda _: drain(database), range(4)))
    with Session(database) as session:
        assert (
            session.scalar(
                select(func.count(Message.id)).where(
                    Message.account_id == wa.whatsapp_business_account_id
                )
            )
            == 1
        )
        assert (
            session.scalar(
                select(func.count(Conversation.id)).where(
                    Conversation.account_id == wa.whatsapp_business_account_id
                )
            )
            == 1
        )
        assert counts(session) == [before[0] + 1, *before[1:]]
        stored = session.scalar(
            select(Outbox)
            .where(Outbox.topic == "whatsapp.inbound", Outbox.event_key.like("wa:in:%"))
            .order_by(Outbox.id.desc())
        )
        assert "body" not in stored.payload


def test_known_contact_and_ambiguous_contact(wa, database):
    phone = str(uuid4().int)[:13]
    with Session(database) as session, session.begin():
        customer = Customer(
            name="Existing", contact="+" + phone, phone=phone, normalized_phone=phone
        )
        session.add(customer)
        session.flush()
        cid = customer.id
    c = incoming(wa, database, sender=phone)
    assert c.customer_id == cid and c.link_method == "exact_phone"
    assert post(wa, payload(wa, sender=phone)).status_code == 200
    drain(database)
    with Session(database) as session:
        assert (
            session.scalar(select(func.count(Message.id)).where(Message.conversation_id == c.id))
            == 2
        )
    ambiguous = str(uuid4().int)[:13]
    with Session(database) as session, session.begin():
        for _ in range(2):
            session.add(Customer(name="Shared", contact=ambiguous, normalized_phone=ambiguous))
    assert post(wa, payload(wa, sender=ambiguous)).status_code == 200
    drain(database)
    with Session(database) as session:
        c = session.scalar(select(Conversation).where(Conversation.external_contact == ambiguous))
        assert c.customer_id is None and c.link_method == "ambiguous"


@pytest.mark.parametrize("kind", ["image", "future_type", "system"])
def test_minimal_media_unknown(wa, database, kind):
    c = incoming(wa, database, kind=kind, sender="opaque-user-" + uuid4().hex)
    assert c.last_incoming_at is None
    with Session(database) as session:
        m = session.scalar(select(Message).where(Message.conversation_id == c.id))
        assert m.kind == kind and m.body is None and m.details == {}


def test_out_of_order_incoming_and_paginated_history(wa, database, client):
    c = incoming(wa, database)
    old = now() - timedelta(days=2)
    assert post(wa, payload(wa, stamp=old)).status_code == 200
    drain(database)
    detail = client.get(f"/api/messaging/conversations/{c.id}").json()
    assert detail["text_window_open"]
    first = client.get(f"/api/messaging/conversations/{c.id}/messages?limit=1").json()
    second = client.get(
        f"/api/messaging/conversations/{c.id}/messages?limit=1&before={first['before']}"
    ).json()
    assert first["items"][0]["occurred_at"] > second["items"][0]["occurred_at"]
    assert first["items"][0]["id"] != second["items"][0]["id"]
    assert client.get("/api/messaging/conversations?page_size=1").json()["total"] >= 1


@pytest.mark.parametrize(
    "field,value",
    [
        ("whatsapp_send_enabled", False),
        ("whatsapp_token_rotated", False),
        ("whatsapp_access_token", SecretStr("")),
        ("whatsapp_phone_number_id", ""),
        ("whatsapp_business_account_id", "other"),
        ("meta_graph_api_version", ""),
        ("whatsapp_allowed_recipients", []),
        ("whatsapp_allowed_recipients", ["9999999999"]),
    ],
)
def test_send_configuration_fail_closed(wa, database, client, field, value):
    c = incoming(wa, database)
    setattr(wa, field, value)
    r = reply(client, c)
    assert r.status_code == 422
    assert "test-token" not in r.text


def test_window_templates_attention_confirmation(wa, database, client):
    c = incoming(wa, database, stamp=now() - timedelta(hours=25))
    assert reply(client, c).status_code == 422
    assert (
        reply(
            client,
            c,
            kind="template",
            body=None,
            template_name="unapproved",
            template_language="es",
        ).status_code
        == 422
    )
    assert (
        reply(
            client,
            c,
            kind="template",
            body=None,
            template_name="hello_world",
            template_language="en_US",
            confirm_send=False,
        ).status_code
        == 422
    )
    r = reply(
        client,
        c,
        kind="template",
        body=None,
        template_name="hello_world",
        template_language="en_US",
    )
    assert r.status_code == 202
    assert (
        client.patch(
            f"/api/messaging/conversations/{c.id}", json={"state": "automated"}
        ).status_code
        == 422
    )
    assert (
        client.patch(f"/api/messaging/conversations/{c.id}", json={"state": "closed"}).status_code
        == 200
    )
    assert (
        reply(
            client,
            c,
            kind="template",
            body=None,
            template_name="hello_world",
            template_language="en_US",
        ).status_code
        == 422
    )


def test_reply_idempotency_and_authenticated_routes(wa, database, client):
    c = incoming(wa, database)
    key = str(uuid4())
    first = reply(client, c, request_key=key)
    assert first.status_code == 202
    second = reply(client, c, request_key=key)
    assert second.json()["id"] == first.json()["id"]
    assert reply(client, c, request_key=key, body="Different").status_code == 409
    from jordy.main import app

    with TestClient(app) as anonymous:
        assert anonymous.get("/api/messaging/conversations").status_code == 401


def test_verified_customer_link(wa, database, client):
    c = incoming(wa, database)
    r = client.post(
        f"/api/messaging/conversations/{c.id}/customer", json={"customer_id": c.customer_id}
    )
    assert r.status_code == 422
    r = client.post(
        f"/api/messaging/conversations/{c.id}/customer",
        json={"customer_id": c.customer_id, "confirmed": True},
    )
    assert r.status_code == 200 and r.json()["link_method"] == "admin_confirmed"


@pytest.mark.parametrize(
    "status,expected",
    [(200, "accepted"), (400, "failed"), (401, "failed"), (429, "failed"), (500, "unknown")],
)
def test_real_adapter_mock_http(wa, status, expected):
    def handler(request):
        assert request.url.host == "graph.facebook.com"
        assert request.headers["Authorization"] == "Bearer test-token-not-a-real-secret"
        assert json.loads(request.content)["text"]["body"] == "Hola"
        return httpx.Response(
            status, json={"messages": [{"id": "wamid.mock"}], "error": {"message": "private"}}
        )

    result = WhatsAppAdapter(wa, httpx.MockTransport(handler)).send(
        "5215551234567", "text", "Hola", {}
    )
    assert result.status == expected
    assert "private" not in str(result)


def test_timeout_and_template_adapter(wa):
    def timeout(request):
        raise httpx.ReadTimeout("SENSITIVE")

    result = WhatsAppAdapter(wa, httpx.MockTransport(timeout)).send(
        "5215551234567", "text", "Hola", {}
    )
    assert result.status == "unknown" and "SENSITIVE" not in str(result)

    def template(request):
        assert json.loads(request.content)["template"] == {
            "name": "hello_world",
            "language": {"code": "en_US"},
        }
        return httpx.Response(200, json={"messages": [{"id": "wamid.template"}]})

    assert (
        WhatsAppAdapter(wa, httpx.MockTransport(template))
        .send("5215551234567", "template", None, {"name": "hello_world", "language": "en_US"})
        .status
        == "accepted"
    )


def status_payload(wa, external, state, stamp=None):
    data = payload(wa)
    value = data["entry"][0]["changes"][0]["value"]
    value.pop("messages")
    value["statuses"] = [
        {
            "id": external,
            "status": state,
            "timestamp": str(int((stamp or now()).timestamp())),
            "recipient_id": "5215551234567",
            "errors": [{"code": 131000, "message": "private error prose"}],
        }
    ]
    return data


def test_worker_claim_before_network_and_late_receipts(wa, database, client):
    c = incoming(wa, database)
    response = reply(client, c)
    mid = response.json()["id"]
    external = "wamid." + uuid4().hex
    assert post(wa, status_payload(wa, external, "read")).status_code == 200
    drain(database)

    class Provider:
        calls = 0

        def send(self, *args):
            self.calls += 1
            with Session(database) as session:
                assert session.get(Message, mid).status == "submitting"
            return SendResult("accepted", external)

    provider = Provider()
    for _ in range(100):
        if not send_one(database, wa, provider):
            break
    assert provider.calls == 1
    assert (
        post(wa, status_payload(wa, external, "sent", now() - timedelta(minutes=2))).status_code
        == 200
    )
    assert post(wa, status_payload(wa, external, "failed")).status_code == 200
    drain(database)
    with Session(database) as session:
        assert session.get(Message, mid).status == "read"
    assert not send_one(database, wa, provider)
    assert provider.calls == 1


def test_uncertain_send_never_retries_and_calendar_ignores(wa, database, client):
    c = incoming(wa, database)
    mid = reply(client, c).json()["id"]

    class Calendar:
        def apply_booking_change(self, payload, key):
            assert "message_id" not in payload

    with Session(database) as session, session.begin():
        process_batch(session, Calendar())

    class Timeout:
        calls = 0

        def send(self, *args):
            self.calls += 1
            raise TimeoutError("private")

    provider = Timeout()
    for _ in range(100):
        if not send_one(database, wa, provider):
            break
    assert provider.calls == 1
    assert not send_one(database, wa, provider)
    with Session(database) as session:
        assert session.get(Message, mid).status == "unknown"


def test_interrupted_send_is_uncertain(wa, database, client):
    c = incoming(wa, database)
    mid = reply(client, c).json()["id"]
    with Session(database) as session, session.begin():
        row = session.scalar(
            select(Outbox).where(
                Outbox.event_key == "wa:send:" + str(session.get(Message, mid).request_key)
            )
        )
        row.status = "sending"
        row.available_at = now() - timedelta(minutes=3)
        session.get(Message, mid).status = "submitting"

    class Forbidden:
        def send(self, *args):
            raise AssertionError("must not resend")

    send_one(database, wa, Forbidden())
    with Session(database) as session:
        assert session.get(Message, mid).status == "unknown"


def test_parallel_distinct_messages_share_identity(wa, database):
    sender = str(uuid4().int)[:13]
    for _ in range(6):
        assert post(wa, payload(wa, sender=sender)).status_code == 200
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda _: drain(database), range(4)))
    with Session(database) as session:
        conversations = session.scalars(
            select(Conversation).where(Conversation.account_id == wa.whatsapp_business_account_id)
        ).all()
        assert len(conversations) == 1
        assert (
            session.scalar(
                select(func.count(Message.id)).where(Message.conversation_id == conversations[0].id)
            )
            == 6
        )
        assert (
            session.scalar(
                select(func.count(Customer.id)).where(Customer.normalized_phone == sender)
            )
            == 1
        )


def test_inbound_transaction_failure_is_retryable(wa, database, monkeypatch):
    from jordy.messaging import worker

    original = worker.process_incoming

    def broken(session, event):
        original(session, event)
        raise RuntimeError("force rollback after creating contact")

    data = payload(wa, sender=str(uuid4().int)[:13])
    assert post(wa, data).status_code == 200
    monkeypatch.setattr(worker, "process_incoming", broken)
    assert receive_one(database)
    with Session(database) as session, session.begin():
        assert (
            session.scalar(
                select(func.count(Conversation.id)).where(
                    Conversation.account_id == wa.whatsapp_business_account_id
                )
            )
            == 0
        )
        row = session.scalar(
            select(Outbox).where(
                Outbox.payload["account"].astext == wa.whatsapp_business_account_id
            )
        )
        assert row.status == "pending" and row.attempts == 1
        row.available_at = now()
    monkeypatch.setattr(worker, "process_incoming", original)
    assert post(wa, data).status_code == 200
    drain(database)
    with Session(database) as session:
        assert (
            session.scalar(
                select(func.count(Message.id)).where(
                    Message.account_id == wa.whatsapp_business_account_id
                )
            )
            == 1
        )


def test_parallel_senders_claim_once(wa, database, client):
    import threading

    c = incoming(wa, database)
    mid = reply(client, c).json()["id"]

    class Provider:
        calls = 0
        mutex = threading.Lock()

        def send(self, *args):
            with self.mutex:
                self.calls += 1
            return SendResult("accepted", "wamid." + uuid4().hex)

    provider = Provider()
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda _: send_one(database, wa, provider), range(4)))
    assert provider.calls == 1
    with Session(database) as session:
        assert session.get(Message, mid).status == "accepted"


def test_policy_rechecked_after_queue(wa, database, client):
    c = incoming(wa, database)
    mid = reply(client, c).json()["id"]
    wa.whatsapp_send_enabled = False

    class Forbidden:
        def send(self, *args):
            pytest.fail("Disabled sender was called")

    assert send_one(database, wa, Forbidden())
    with Session(database) as session:
        assert session.get(Message, mid).status == "failed"


def test_late_delivery_and_malformed_success(wa, database, client):
    c = incoming(wa, database)
    mid = reply(client, c).json()["id"]
    external = "wamid." + uuid4().hex

    class Provider:
        def send(self, *args):
            return SendResult("accepted", external)

    assert send_one(database, wa, Provider())
    assert post(wa, status_payload(wa, external, "delivered")).status_code == 200
    drain(database)
    with Session(database) as session:
        assert session.get(Message, mid).status == "delivered"
    adapter = WhatsAppAdapter(wa, httpx.MockTransport(lambda r: httpx.Response(200, json={})))
    assert adapter.send("5215551234567", "text", "Hola", {}).status == "unknown"


def test_future_timestamp_and_notice(wa, database):
    assert post(wa, payload(wa, stamp=now() + timedelta(days=1))).status_code == 400
    data = payload(wa)
    data["entry"][0]["changes"] = [{"field": "future_event", "value": {"secret": "omit"}}]
    assert post(wa, data).status_code == 200
    drain(database)
    with Session(database) as session:
        row = session.scalar(
            select(Outbox).where(
                Outbox.payload["account"].astext == wa.whatsapp_business_account_id
            )
        )
        assert row.status == "processed" and "secret" not in row.payload


def test_small_clock_skew_does_not_extend_window(wa, database):
    c = incoming(wa, database, stamp=now() + timedelta(minutes=2))
    assert c.last_incoming_at <= now()
