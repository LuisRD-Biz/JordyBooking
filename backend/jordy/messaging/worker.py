"""Poll durable jobs. Inbound transactions retry; uncertain outbound jobs NEVER retry."""

import time
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from jordy.domain import RuleViolation
from jordy.messaging.config import messaging_settings
from jordy.messaging.policy import SendPolicyViolation
from jordy.messaging.provider import SendResult, WhatsAppAdapter
from jordy.messaging.service import (
    lock,
    process_incoming,
    process_status,
    reconcile,
    validate_send,
)
from jordy.models import Conversation, Message, Outbox
from jordy.services import now


def receive_one(engine):
    with Session(engine) as session, session.begin():
        row = session.scalar(
            select(Outbox)
            .where(
                Outbox.topic == "whatsapp.inbound",
                Outbox.status == "pending",
                Outbox.available_at <= now(),
            )
            .order_by(Outbox.id)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if not row:
            return False
        row.attempts += 1
        try:
            with session.begin_nested():
                if row.payload["event"] == "message":
                    process_incoming(session, row.payload)
                elif row.payload["event"] == "status":
                    process_status(session, row.payload)
                session.flush()
        except Exception:
            row.last_error = "inbound_processing_failed"
            row.available_at = now() + timedelta(seconds=min(3600, 2 ** min(row.attempts, 12)))
            if row.attempts >= 10:
                row.status = "failed"
        else:
            row.status, row.last_error = "processed", None
            # Keep the dedup key; private body lives only in its message, not twice.
            if row.payload["event"] != "notice":
                row.payload = {"event": row.payload["event"]}
        return True


def send_one(engine, config, provider):
    with Session(engine) as session, session.begin():
        # Interrupted sends are uncertain, even if a crash occurred before opening the socket.
        stale = session.scalars(
            select(Outbox)
            .where(
                Outbox.topic == "whatsapp.send",
                Outbox.status == "sending",
                Outbox.available_at < now() - timedelta(minutes=2),
            )
            .with_for_update(skip_locked=True)
        ).all()
        for row in stale:
            row.status, row.last_error = "unknown", "interrupted_send"
            msg = session.get(Message, row.payload["message_id"], with_for_update=True)
            if msg.status == "submitting":
                msg.status, msg.error_code = "unknown", "interrupted_send"
        row = session.scalar(
            select(Outbox)
            .where(
                Outbox.topic == "whatsapp.send",
                Outbox.status == "pending",
                Outbox.available_at <= now(),
            )
            .order_by(Outbox.id)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if not row:
            return False
        message = session.get(Message, row.payload["message_id"], with_for_update=True)
        conversation = session.get(Conversation, message.conversation_id)
        try:
            recipient = validate_send(config, conversation, message.kind, message.details)
            # Legacy queued jobs may only use their unchanged, explicitly authorized identity.
            expected = message.details.get("send_recipient", conversation.external_contact)
            if recipient != expected:
                raise SendPolicyViolation("send_recipient_changed")
            revision = row.payload.get("send_config_revision")
            if revision and revision != config.send_config_revision():
                raise SendPolicyViolation("send_config_changed")
        except SendPolicyViolation as exc:
            row.status, row.last_error = "failed", exc.code
            message.status, message.error_code = "failed", exc.code
            return True
        except RuleViolation:
            row.status, row.last_error = "failed", "send_policy_blocked"
            message.status, message.error_code = "failed", "send_policy_blocked"
            return True
        row.status, row.available_at = "sending", now()
        row.attempts += 1
        message.status = "submitting"
        row_id, message_id = row.id, message.id
        account = message.account_id
        args = (recipient, message.kind, message.body, message.details)
    # Commit claim before network; no database locks held across an HTTP call.
    try:
        result = provider.send(*args)
    except Exception:
        result = SendResult("unknown", error_code="provider_result_unknown")
    with Session(engine) as session, session.begin():
        if result.external_id:
            lock(session, "wa:receipt:" + account + ":" + result.external_id)
        row = session.get(Outbox, row_id, with_for_update=True)
        message = session.get(Message, message_id, with_for_update=True)
        message.status, message.external_id = result.status, result.external_id
        message.error_code = result.error_code
        session.flush()
        reconcile(session, message)
        row.status, row.last_error = result.status, result.error_code
    return True


def main():
    from jordy.messaging.webhook import webhook_engine

    config = messaging_settings()
    engine = webhook_engine()
    provider = WhatsAppAdapter(config)
    print("Procesador de mensajes iniciado. Ctrl+C para detener.")
    print(f"Revisión de configuración de envío: {config.send_config_revision()[:12]}", flush=True)
    try:
        while True:
            try:
                received = receive_one(engine)
                sent = send_one(engine, config, provider)
            except Exception:
                # No traceback: SQL parameters and provider errors may contain private content.
                print("Operación pendiente de revisión; se reintentará la lectura de la cola.")
                received = sent = False
            if not received and not sent:
                time.sleep(2)
    except KeyboardInterrupt:
        pass
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
