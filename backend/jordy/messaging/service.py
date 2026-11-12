import hashlib
import json
import re
from datetime import datetime, timedelta

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert

from jordy.customers import possible_duplicates
from jordy.domain import Conflict, RuleViolation
from jordy.messaging.policy import SendPolicyViolation, resolve_recipient
from jordy.models import Conversation, Customer, Message, MessageReceipt, Outbox
from jordy.schemas import CustomerInput
from jordy.services import audit, now


def lock(session, key):
    session.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"), {"key": key})


def process_incoming(session, event):
    when = datetime.fromisoformat(event["time"])
    sender = event["sender"]
    lock(session, "wa:identity:" + event["account"] + ":" + sender)
    if session.scalar(
        select(Message.id).where(
            Message.channel == "whatsapp",
            Message.account_id == event["account"],
            Message.external_id == event["external_id"],
        )
    ):
        return
    conversation = session.scalar(
        select(Conversation)
        .where(
            Conversation.channel == "whatsapp",
            Conversation.account_id == event["account"],
            Conversation.external_contact == sender,
        )
        .with_for_update()
    )
    if conversation is None:
        phone = sender if re.fullmatch(r"[0-9]{7,15}", sender) else None
        lock(session, "customer-contact:" + (phone or "wa:" + sender))
        matches = (
            possible_duplicates(
                session,
                CustomerInput(
                    name=event["name"] or "Contacto de WhatsApp",
                    contact=phone or "",
                    phone=phone,
                ),
            )
            if phone
            else []
        )
        customer_id = None
        method = "ambiguous" if matches else "new_contact"
        if len(matches) == 1:
            customer_id, method = matches[0], "exact_phone"
        elif not matches:
            customer = Customer(
                name=event["name"] or "Contacto de WhatsApp",
                contact=phone or "WhatsApp",
                phone=phone,
                normalized_phone=phone,
                notes="",
                featured=False,
                created_at=now(),
                last_activity_at=when,
            )
            session.add(customer)
            session.flush()
            customer_id = customer.id
            audit(session, "messaging.contact_created", customer.id)
        conversation = Conversation(
            channel="whatsapp",
            account_id=event["account"],
            phone_number_id=event["phone"],
            external_contact=sender,
            display_name=event["name"] or "Contacto de WhatsApp",
            customer_id=customer_id,
            link_method=method,
            state="human",
            created_at=now(),
            last_activity_at=when,
        )
        session.add(conversation)
        session.flush()
    if conversation.phone_number_id != event["phone"]:
        raise RuleViolation("El número emisor cambió; requiere revisión administrativa.")
    session.add(
        Message(
            conversation_id=conversation.id,
            channel="whatsapp",
            account_id=event["account"],
            external_id=event["external_id"],
            direction="incoming",
            kind=event["kind"],
            body=event["body"],
            details={},
            occurred_at=when,
            created_at=now(),
            status="received",
        )
    )
    conversation.last_activity_at = max(conversation.last_activity_at, when)
    if event["kind"] == "text":
        effective_time = min(when, now())
        conversation.last_incoming_at = max(
            conversation.last_incoming_at or effective_time, effective_time
        )
    if conversation.customer_id:
        customer = session.get(Customer, conversation.customer_id, with_for_update=True)
        customer.last_activity_at = max(customer.last_activity_at or when, when)


RANK = {
    "queued": 0,
    "submitting": 1,
    "unknown": 1,
    "failed": 2,
    "accepted": 3,
    "sent": 4,
    "delivered": 5,
    "read": 6,
}


def reconcile(session, message):
    if not message.external_id or message.direction != "outgoing":
        return
    conversation = session.get(Conversation, message.conversation_id)
    receipts = session.scalars(
        select(MessageReceipt)
        .where(
            MessageReceipt.account_id == message.account_id,
            MessageReceipt.external_id == message.external_id,
            MessageReceipt.recipient.in_(
                [
                    conversation.external_contact,
                    message.details.get("send_recipient", conversation.external_contact),
                ]
            ),
        )
        .order_by(MessageReceipt.occurred_at, MessageReceipt.id)
    ).all()
    for receipt in receipts:
        if receipt.status == "failed" and RANK.get(message.status, 0) < 5:
            message.status, message.error_code = "failed", receipt.error_code
        elif receipt.status in ("sent", "delivered", "read") and (
            RANK[receipt.status] > RANK.get(message.status, 0)
        ):
            message.status, message.error_code = receipt.status, None


def process_status(session, event):
    lock(session, "wa:receipt:" + event["account"] + ":" + event["external_id"])
    session.execute(
        insert(MessageReceipt)
        .values(
            account_id=event["account"],
            external_id=event["external_id"],
            recipient=event["recipient"],
            status=event["status"],
            occurred_at=datetime.fromisoformat(event["time"]),
            error_code=event["error_code"],
        )
        .on_conflict_do_nothing()
    )
    message = session.scalar(
        select(Message)
        .where(
            Message.channel == "whatsapp",
            Message.account_id == event["account"],
            Message.external_id == event["external_id"],
            Message.direction == "outgoing",
        )
        .with_for_update()
    )
    if message:
        reconcile(session, message)


def validate_send(config, conversation, kind, details):
    codes = config.send_blocker_codes()
    if codes:
        raise SendPolicyViolation(codes[0])
    if conversation.state != "human":
        raise SendPolicyViolation("human_attention_required")
    if (
        conversation.channel != "whatsapp"
        or conversation.account_id != config.whatsapp_business_account_id
        or conversation.phone_number_id != config.whatsapp_phone_number_id
    ):
        raise SendPolicyViolation("sender_account_mismatch")
    recipient = resolve_recipient(config, conversation)
    if kind == "text":
        if not conversation.last_incoming_at or conversation.last_incoming_at <= now() - timedelta(
            hours=24
        ):
            raise SendPolicyViolation("service_window_expired")
    elif kind == "template":
        key = details["name"] + ":" + details["language"]
        if key not in config.whatsapp_approved_templates:
            raise SendPolicyViolation("template_not_authorized")
    else:
        raise SendPolicyViolation("message_type_unsupported")
    return recipient


def queue_reply(session, config, conversation, data):
    lock(session, "wa:request:" + str(data.request_key))
    content = data.model_dump(
        mode="json", exclude={"request_key", "confirm_send", "expected_recipient"}
    )
    content["conversation_id"] = conversation.id
    fingerprint = hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()
    existing = session.scalar(select(Message).where(Message.request_key == data.request_key))
    if existing:
        if existing.request_hash != fingerprint:
            raise Conflict("Esta solicitud ya se usó para otro mensaje.")
        return existing
    if not data.confirm_send:
        raise RuleViolation("Confirma expresamente el envío real.")
    details = (
        {"name": data.template_name, "language": data.template_language}
        if data.kind == "template"
        else {}
    )
    recipient = validate_send(config, conversation, data.kind, details)
    if data.expected_recipient is not None and data.expected_recipient != recipient:
        raise SendPolicyViolation("send_recipient_changed")
    details["send_recipient"] = recipient
    message = Message(
        conversation_id=conversation.id,
        channel=conversation.channel,
        account_id=conversation.account_id,
        request_key=data.request_key,
        request_hash=fingerprint,
        direction="outgoing",
        kind=data.kind,
        body=data.body if data.kind == "text" else None,
        details=details,
        occurred_at=now(),
        created_at=now(),
        status="queued",
    )
    session.add(message)
    session.flush()
    session.add(
        Outbox(
            topic="whatsapp.send",
            event_key="wa:send:" + str(data.request_key),
            payload={
                "message_id": message.id,
                "send_config_revision": config.send_config_revision(),
            },
            available_at=now(),
        )
    )
    conversation.last_activity_at = now()
    audit(session, "messaging.reply_queued", message.id)
    return message
