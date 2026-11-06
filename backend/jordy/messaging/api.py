from datetime import timedelta
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import Field, model_validator
from sqlalchemy import func, or_, select, tuple_
from sqlalchemy.orm import Session

from jordy.api import authenticate
from jordy.commercial_models import CommercialSignal
from jordy.crm import serialize
from jordy.db import get_session
from jordy.domain import RuleViolation
from jordy.messaging.config import messaging_settings
from jordy.messaging.policy import ERRORS, SendPolicyViolation, error_diagnostic, resolve_recipient
from jordy.messaging.queries import needs_reply
from jordy.messaging.service import queue_reply
from jordy.models import Conversation, Customer, Lead, Message, Outbox
from jordy.repository import require
from jordy.schemas import Input
from jordy.services import audit, now

router = APIRouter(prefix="/api/messaging", dependencies=[Depends(authenticate)])
DB = Annotated[Session, Depends(get_session)]


class Reply(Input):
    request_key: UUID
    confirm_send: bool = False
    expected_recipient: str | None = Field(default=None, pattern=r"^[0-9]{7,15}$")
    kind: Literal["text", "template"] = "text"
    body: str | None = Field(default=None, max_length=4096)
    template_name: str = Field(default="", max_length=100, pattern=r"^[a-z0-9_]*$")
    template_language: str = Field(default="", max_length=20, pattern=r"^[A-Za-z_]*$")

    @model_validator(mode="after")
    def valid_message(self):
        if self.kind == "text" and (not self.body or not self.body.strip()):
            raise ValueError("Escribe un mensaje.")
        if self.kind == "template" and (
            not self.template_name or not self.template_language or self.body
        ):
            raise ValueError("Selecciona una plantilla sin parámetros; no añadas texto libre.")
        return self


class Attention(Input):
    state: Literal["human", "closed"]
    responsible: str | None = Field(default=None, max_length=100)


class Link(Input):
    customer_id: int = Field(gt=0)
    confirmed: bool = False


@router.get("/config")
def config_status(session: DB):
    config = messaging_settings()
    counts = session.execute(
        select(Outbox.status, func.count())
        .where(
            Outbox.topic.in_(["whatsapp.inbound", "whatsapp.send"]),
            Outbox.status.in_(["pending", "sending", "failed", "unknown"]),
        )
        .group_by(Outbox.status)
    ).all()
    latest = session.scalar(
        select(Message)
        .join(Outbox, Outbox.payload["message_id"].as_integer() == Message.id)
        .where(
            Outbox.topic == "whatsapp.send",
            Outbox.payload["send_config_revision"].as_string() == config.send_config_revision(),
            Message.account_id == config.whatsapp_business_account_id,
            Message.status.in_(["failed", "unknown", "accepted", "sent", "delivered", "read"]),
        )
        .order_by(Message.created_at.desc(), Message.id.desc())
        .limit(1)
    )
    provider_review = error_diagnostic(latest.error_code) if latest else None
    return {
        "send_blockers": config.send_blockers(),
        "send_blocker_codes": config.send_blocker_codes(),
        "send_config_revision": config.send_config_revision(),
        "error_labels": ERRORS,
        "templates": config.whatsapp_approved_templates,
        "jobs": dict(counts),
        # A current-config failed attempt is a review item, not a live token check.
        "provider_review": (
            {**provider_review, "message_id": latest.id}
            if provider_review
            and provider_review["category"] in {"credential", "provider_temporary", "review"}
            else None
        ),
        "receiver_configured": bool(
            config.meta_app_secret.get_secret_value()
            and config.meta_webhook_verify_token.get_secret_value()
            and config.whatsapp_phone_number_id
            and config.whatsapp_business_account_id
        ),
    }


def conversation_dict(session, conversation):
    result = serialize(conversation)
    customer = session.get(Customer, conversation.customer_id) if conversation.customer_id else None
    result["customer_name"] = customer.name if customer else None
    try:
        result["send_recipient"] = resolve_recipient(messaging_settings(), conversation)
        result["recipient_error"] = None
    except SendPolicyViolation as exc:
        result["send_recipient"] = None
        result["recipient_error"] = str(exc)
    last = session.scalar(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.occurred_at.desc(), Message.id.desc())
        .limit(1)
    )
    result["last_message"] = serialize(last) if last else None
    result["pending_signals"] = session.scalar(
        select(func.count())
        .select_from(CommercialSignal)
        .where(
            CommercialSignal.conversation_id == conversation.id,
            CommercialSignal.review_state == "pending",
        )
    )
    result["needs_reply"] = session.scalar(
        select(needs_reply()).select_from(Conversation).where(Conversation.id == conversation.id)
    )
    return result


@router.get("/conversations")
def conversations(
    session: DB,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    q: str = Query("", max_length=100),
):
    stmt = select(Conversation)
    if q.strip():
        term = "%" + q.strip().replace("%", r"\%").replace("_", r"\_") + "%"
        stmt = stmt.outerjoin(Customer).where(
            or_(
                Conversation.display_name.ilike(term),
                Conversation.external_contact.ilike(term),
                Customer.name.ilike(term),
            )
        )
    total = session.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = session.scalars(
        stmt.order_by(Conversation.last_activity_at.desc(), Conversation.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {"items": [conversation_dict(session, c) for c in rows], "total": total}


@router.get("/conversations/{conversation_id}")
def conversation_detail(conversation_id: int, session: DB):
    conversation = require(session, Conversation, conversation_id)
    result = conversation_dict(session, conversation)
    result["customer"] = (
        serialize(session.get(Customer, conversation.customer_id))
        if conversation.customer_id
        else None
    )
    result["leads"] = [
        serialize(lead)
        for lead in session.scalars(
            select(Lead)
            .where(
                Lead.customer_id == conversation.customer_id if conversation.customer_id else False,
            )
            .order_by(Lead.last_activity_at.desc())
            .limit(20)
        )
    ]
    result["text_window_open"] = bool(
        conversation.last_incoming_at
        and conversation.last_incoming_at > now() - timedelta(hours=24)
    )
    return result


@router.get("/conversations/{conversation_id}/messages")
def history(
    conversation_id: int,
    session: DB,
    before: int | None = Query(None, gt=0),
    limit: int = Query(50, ge=1, le=100),
):
    require(session, Conversation, conversation_id)
    stmt = select(Message).where(Message.conversation_id == conversation_id)
    if before:
        cursor = require(session, Message, before)
        if cursor.conversation_id != conversation_id:
            raise RuleViolation("Cursor de otra conversación.")
        stmt = stmt.where(tuple_(Message.occurred_at, Message.id) < (cursor.occurred_at, cursor.id))
    rows = list(
        session.scalars(
            stmt.order_by(Message.occurred_at.desc(), Message.id.desc()).limit(limit + 1)
        )
    )
    more = len(rows) > limit
    rows = rows[:limit]
    return {
        "items": [message_dict(row) for row in reversed(rows)],
        "before": rows[-1].id if more else None,
    }


def message_dict(message):
    return {**serialize(message), "diagnostic": error_diagnostic(message.error_code)}


@router.get("/conversations/{conversation_id}/messages/{message_id}")
def original_message(conversation_id: int, message_id: int, session: DB):
    row = require(session, Message, message_id)
    if row.conversation_id != conversation_id:
        raise RuleViolation("El mensaje pertenece a otra conversación.")
    return message_dict(row)


@router.patch("/conversations/{conversation_id}")
def attention(conversation_id: int, data: Attention, session: DB):
    with session.begin():
        conversation = require(session, Conversation, conversation_id)
        conversation.state, conversation.responsible = data.state, data.responsible
        audit(session, "messaging.attention_changed", conversation.id)
        return serialize(conversation)


@router.post("/conversations/{conversation_id}/customer")
def link(conversation_id: int, data: Link, session: DB):
    if not data.confirmed:
        raise RuleViolation("Confirma que verificaste la identidad del contacto.")
    with session.begin():
        conversation = require(session, Conversation, conversation_id)
        require(session, Customer, data.customer_id)
        conversation.customer_id, conversation.link_method = data.customer_id, "admin_confirmed"
        audit(session, "messaging.identity_linked", conversation.id)
        return serialize(conversation)


@router.post("/conversations/{conversation_id}/reply", status_code=202)
def reply(conversation_id: int, data: Reply, session: DB):
    with session.begin():
        conversation = session.scalar(
            select(Conversation).where(Conversation.id == conversation_id).with_for_update()
        )
        if conversation is None:
            conversation = require(session, Conversation, conversation_id)
        return serialize(queue_reply(session, messaging_settings(), conversation, data))
