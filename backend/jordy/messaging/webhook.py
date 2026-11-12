import hashlib
import hmac
import json
from datetime import UTC, datetime
from functools import lru_cache

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from jordy.db import build_engine
from jordy.messaging.config import messaging_settings
from jordy.models import Outbox

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, redirect_slashes=False)
PATH = "/webhooks/whatsapp"


@lru_cache
def webhook_engine():
    return build_engine(messaging_settings().database_url)


def string(value, limit=200):
    if not isinstance(value, str) or not 0 < len(value) <= limit:
        raise ValueError("invalid_string")
    return value


def timestamp(value):
    stamp = datetime.fromtimestamp(int(value), UTC)
    if stamp.year < 2000 or stamp.timestamp() > datetime.now(UTC).timestamp() + 300:
        raise ValueError("invalid_timestamp")
    return stamp.isoformat()


def normalize(payload, config):
    if payload["object"] != "whatsapp_business_account":
        raise ValueError("wrong_object")
    if not isinstance(payload["entry"], list) or not payload["entry"]:
        raise ValueError("invalid_entries")
    events = []
    for entry in payload["entry"]:
        account = string(entry["id"], 100)
        if account != config.whatsapp_business_account_id:
            raise ValueError("wrong_account")
        for change in entry["changes"]:
            value = change["value"]
            if change["field"] != "messages":
                events.append(
                    dict(
                        event="notice",
                        account=account,
                        error_code=None,
                        notice_kind=string(change["field"], 80),
                    )
                )
                continue
            phone = string(value["metadata"]["phone_number_id"], 100)
            if phone != config.whatsapp_phone_number_id:
                raise ValueError("wrong_phone")
            names = {
                c["wa_id"]: str(c.get("profile", {}).get("name", ""))[:200]
                for c in value.get("contacts", [])
                if "wa_id" in c
            }
            for msg in value.get("messages", []):
                sender = string(msg["from"])
                kind = string(msg["type"], 30)
                event = dict(
                    event="message",
                    account=account,
                    phone=phone,
                    sender=sender,
                    name=names.get(sender, ""),
                    external_id=string(msg["id"], 300),
                    kind=kind,
                    time=timestamp(msg["timestamp"]),
                    body=None,
                )
                if kind == "text":
                    event["body"] = string(msg["text"]["body"], 4096)
                events.append(event)
            for status in value.get("statuses", []):
                state = string(status["status"], 30)
                events.append(
                    dict(
                        event="status",
                        account=account,
                        phone=phone,
                        external_id=string(status["id"], 300),
                        status=state,
                        recipient=string(status["recipient_id"]),
                        time=timestamp(status["timestamp"]),
                        error_code=error_code(status.get("errors", [])),
                    )
                )
            for error in value.get("errors", []):
                events.append(
                    dict(
                        event="notice", account=account, phone=phone, error_code=error_code([error])
                    )
                )
    if len(events) > 500:
        raise ValueError("too_many_events")
    return events


def error_code(errors):
    if errors and isinstance(errors[0].get("code"), int):
        return str(errors[0]["code"])[:30]
    return None


def persist(events):
    with Session(webhook_engine()) as session, session.begin():
        for event in events:
            identity = {
                k: event[k]
                for k in (
                    ("account", "event", "external_id")
                    if event["event"] == "message"
                    else ("account", "event", "external_id", "status", "time")
                    if event["event"] == "status"
                    else ("account", "event", "error_code")
                )
            }
            if event["event"] == "notice":
                identity["notice_kind"] = event.get("notice_kind")
                identity["phone"] = event.get("phone")
            key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
            session.execute(
                insert(Outbox)
                .values(
                    topic="whatsapp.inbound",
                    event_key="wa:in:" + key,
                    payload=event,
                    status="pending",
                    attempts=0,
                    available_at=datetime.now(UTC),
                )
                .on_conflict_do_nothing(index_elements=["event_key"])
            )


@app.get(PATH, response_class=PlainTextResponse)
async def verify(request: Request):
    config = messaging_settings()
    secret = config.meta_webhook_verify_token.get_secret_value()
    query = request.query_params
    if not secret or len(secret) < 32 or secret == config.whatsapp_access_token.get_secret_value():
        raise HTTPException(503, "verification_not_configured")
    if (
        query.get("hub.mode") != "subscribe"
        or not hmac.compare_digest(query.get("hub.verify_token", "").encode(), secret.encode())
        or not query.get("hub.challenge")
        or len(query["hub.challenge"]) > 1024
    ):
        raise HTTPException(403, "verification_failed")
    return query["hub.challenge"]


@app.post(PATH)
async def receive(request: Request):
    config = messaging_settings()
    secret = config.meta_app_secret.get_secret_value()
    if not secret or not config.whatsapp_phone_number_id or not config.whatsapp_business_account_id:
        raise HTTPException(503, "receiver_not_configured")
    raw = bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw) > config.whatsapp_max_webhook_bytes:
            raise HTTPException(413, "payload_too_large")
    expected = "sha256=" + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    provided = request.headers.get("X-Hub-Signature-256", "")
    if not hmac.compare_digest(expected.encode(), provided.encode()):
        raise HTTPException(401, "invalid_signature")
    try:
        events = normalize(json.loads(raw), config)
    except (
        ValueError,
        KeyError,
        TypeError,
        AttributeError,
        OverflowError,
        OSError,
        RecursionError,
    ):
        raise HTTPException(400, "invalid_event") from None
    try:
        await run_in_threadpool(persist, events)
    except Exception:
        raise HTTPException(503, "durable_storage_unavailable") from None
    return {"accepted": True}
