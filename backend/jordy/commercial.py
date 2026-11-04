"""Stored observations and reports; deliberately no messaging/booking dispatch."""

from collections import Counter
from datetime import date, datetime, time, timedelta
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query
from fastapi.encoders import jsonable_encoder
from pydantic import Field, model_validator
from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from jordy.api import authenticate
from jordy.commercial_models import (
    CommercialNote,
    CommercialPlan,
    CommercialSignal,
    DailySummary,
    SummarySchedule,
)
from jordy.commercial_rules import detect
from jordy.config import settings
from jordy.crm import serialize
from jordy.db import get_session
from jordy.domain import RuleViolation
from jordy.models import AuditLog, Booking, Conversation, Lead, Message
from jordy.repository import require
from jordy.schemas import Input
from jordy.services import audit, now

router = APIRouter(prefix="/api/commercial", dependencies=[Depends(authenticate)])
DB = Annotated[Session, Depends(get_session)]


def analyze(session, conversation_id):
    require(session, Conversation, conversation_id)
    # Append-only message detections. Unique keys also protect concurrent manual/nightly runs.
    for message in session.scalars(
        select(Message)
        .where(
            Message.conversation_id == conversation_id,
            Message.kind == "text",
            (Message.direction == "incoming")
            | Message.status.in_(["accepted", "sent", "delivered", "read"]),
        )
        .order_by(Message.occurred_at, Message.id)
    ):
        for signal in detect(message.body, message.occurred_at, settings().studio_timezone):
            session.execute(
                insert(CommercialSignal)
                .values(
                    conversation_id=conversation_id,
                    message_id=message.id,
                    review_state="pending",
                    rule_version="1",
                    **signal,
                )
                .on_conflict_do_nothing(index_elements=["message_id", "signal_key"])
            )


def commercial_data(session, conversation_id):
    require(session, Conversation, conversation_id)
    return {
        "signals": [
            serialize(r)
            for r in session.scalars(
                select(CommercialSignal)
                .where(CommercialSignal.conversation_id == conversation_id)
                .order_by(CommercialSignal.id)
            )
        ],
        "notes": [
            serialize(r)
            for r in session.scalars(
                select(CommercialNote)
                .where(CommercialNote.conversation_id == conversation_id)
                .order_by(CommercialNote.id.desc())
            )
        ],
        "plans": [
            serialize(r)
            for r in session.scalars(
                select(CommercialPlan)
                .where(CommercialPlan.conversation_id == conversation_id)
                .order_by(CommercialPlan.id.desc())
            )
        ],
    }


@router.get("/conversations/{conversation_id}")
def details(conversation_id: int, session: DB):
    return commercial_data(session, conversation_id)


@router.post("/conversations/{conversation_id}/analyze")
def run_analysis(conversation_id: int, session: DB):
    with session.begin():
        analyze(session, conversation_id)
        return commercial_data(session, conversation_id)


class Review(Input):
    state: Literal["reviewed", "dismissed", "pending"]


@router.patch("/conversations/{conversation_id}/signals/{signal_id}")
def review_signal(conversation_id: int, signal_id: int, data: Review, session: DB):
    with session.begin():
        signal = require(session, CommercialSignal, signal_id)
        if signal.conversation_id != conversation_id:
            raise RuleViolation("COMMERCIAL_SCOPE: La señal pertenece a otra conversación.")
        signal.review_state = data.state
        signal.reviewed_at = now() if data.state != "pending" else None
        audit(session, "commercial.signal_" + data.state, signal.id)
        return serialize(signal)


class NoteInput(Input):
    body: str = Field(min_length=1, max_length=2000)
    source: Literal["manual", "call", "audio", "in_person"] = "manual"


@router.post("/conversations/{conversation_id}/notes")
def add_note(conversation_id: int, data: NoteInput, session: DB):
    with session.begin():
        require(session, Conversation, conversation_id)
        if not data.body.strip():
            raise RuleViolation("COMMERCIAL_NOTE_EMPTY: Escribe el acuerdo o contexto.")
        row = CommercialNote(conversation_id=conversation_id, created_at=now(), **data.model_dump())
        session.add(row)
        session.flush()
        audit(session, "commercial.note_added", row.id)
        return serialize(row)


class PlanInput(Input):
    requested_date: date
    alternative_dates: list[date] = Field(default_factory=list, max_length=20)
    tentative_date: date | None = None
    time_note: str = Field(default="", max_length=200)
    kind: Literal["inquiry", "tentative", "hold_review", "reschedule"] = "inquiry"
    agreement: Literal["unknown", "proposed", "verbally_reported"] = "unknown"
    lead_id: int | None = Field(default=None, gt=0)
    booking_id: int | None = Field(default=None, gt=0)
    notes: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def change_target(self):
        if self.kind == "reschedule" and self.booking_id is None:
            raise ValueError("Selecciona la reservación para proponer su cambio.")
        return self


@router.post("/conversations/{conversation_id}/plans")
def add_plan(conversation_id: int, data: PlanInput, session: DB):
    with session.begin():
        conversation = require(session, Conversation, conversation_id)
        for model, identifier in ((Lead, data.lead_id), (Booking, data.booking_id)):
            if identifier:
                record = require(session, model, identifier)
                if not conversation.customer_id or record.customer_id != conversation.customer_id:
                    raise RuleViolation(
                        "COMMERCIAL_SCOPE: Selecciona un registro de este contacto."
                    )
        row = CommercialPlan(
            conversation_id=conversation_id,
            created_at=now(),
            **{
                **data.model_dump(),
                "alternative_dates": [d.isoformat() for d in data.alternative_dates],
            },
        )
        session.add(row)
        session.flush()
        audit(session, "commercial.plan_proposed", row.id)
        return serialize(row)


@router.patch("/conversations/{conversation_id}/plans/{plan_id}")
def review_plan(conversation_id: int, plan_id: int, data: Review, session: DB):
    with session.begin():
        row = require(session, CommercialPlan, plan_id)
        if row.conversation_id != conversation_id:
            raise RuleViolation("COMMERCIAL_SCOPE: La propuesta pertenece a otra conversación.")
        row.review_state = data.state
        audit(session, "commercial.plan_" + data.state, row.id)
        return serialize(row)


@router.get("/plans")
def plans(session: DB, day: date | None = None, offset: int = Query(0, ge=0)):
    stmt = select(CommercialPlan)
    if day:
        stmt = stmt.where(
            (CommercialPlan.requested_date == day)
            | (CommercialPlan.tentative_date == day)
            | CommercialPlan.alternative_dates.contains([day.isoformat()])
        )
    return [
        serialize(r)
        for r in session.scalars(stmt.order_by(CommercialPlan.id.desc()).offset(offset).limit(200))
    ]


def day_bounds(day, timezone):
    zone = ZoneInfo(timezone)
    return (
        datetime.combine(day, time.min, zone),
        datetime.combine(day + timedelta(days=1), time.min, zone),
    )


def generate_summary(session, day):
    timezone = settings().studio_timezone
    if day > now().astimezone(ZoneInfo(timezone)).date():
        raise RuleViolation("SUMMARY_FUTURE: Elige hoy o un día anterior.")
    session.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:key))"), {"key": f"daily-summary:{day}"}
    )
    start, end = day_bounds(day, timezone)
    messages = list(
        session.scalars(
            select(Message)
            .where(Message.occurred_at >= start, Message.occurred_at < end)
            .order_by(Message.occurred_at, Message.id)
        )
    )
    ids = sorted({m.conversation_id for m in messages})
    conversations = []
    for cid in ids:
        analyze(session, cid)
        conv = session.get(Conversation, cid)
        incoming = [m for m in messages if m.conversation_id == cid and m.direction == "incoming"]
        first = session.scalar(
            select(func.min(Message.occurred_at)).where(
                Message.conversation_id == cid, Message.direction == "incoming"
            )
        )
        last_in = max((m.occurred_at for m in incoming), default=None)
        responded = bool(
            last_in
            and any(
                m.direction == "outgoing"
                and m.conversation_id == cid
                and m.occurred_at > last_in
                and m.status in {"accepted", "sent", "delivered", "read"}
                for m in messages
            )
        )
        conversations.append(
            {
                "id": cid,
                "name": conv.display_name,
                "customer_id": conv.customer_id,
                "first_contact": bool(incoming and first >= start),
                "returning": bool(incoming and first < start),
                "awaiting_reply_at_close": bool(last_in and not responded),
            }
        )
    signals = list(
        session.scalars(
            select(CommercialSignal)
            .join(Message)
            .where(Message.occurred_at >= start, Message.occurred_at < end)
            .order_by(CommercialSignal.id)
        )
    )
    directions = {m.id: m.direction for m in messages}
    effective = [
        s
        for s in signals
        if s.review_state != "dismissed"
        and s.context != "negated"
        and directions[s.message_id] == "incoming"
    ]
    operations = list(
        session.scalars(
            select(AuditLog)
            .where(
                AuditLog.created_at >= start,
                AuditLog.created_at < end,
                (AuditLog.action.like("booking.%"))
                | (AuditLog.action.like("appointment.%"))
                | (AuditLog.action.like("contract.%"))
                | (AuditLog.action.like("lead.%"))
                | (AuditLog.action.like("quote.%"))
                | (AuditLog.action.like("block.%")),
            )
            .order_by(AuditLog.created_at, AuditLog.id)
        )
    )
    notes = list(
        session.scalars(
            select(CommercialNote)
            .where(CommercialNote.created_at >= start, CommercialNote.created_at < end)
            .order_by(CommercialNote.id)
        )
    )
    proposals = list(
        session.scalars(
            select(CommercialPlan)
            .where(CommercialPlan.created_at >= start, CommercialPlan.created_at < end)
            .order_by(CommercialPlan.id)
        )
    )
    content = {
        "conversations": conversations,
        "first_contacts": sum(c["first_contact"] for c in conversations),
        "returning_contacts": sum(c["returning"] for c in conversations),
        "services": dict(
            Counter(
                s.kind for s in effective if s.kind in {"wedding", "xv", "session", "other_service"}
            )
        ),
        "questions": dict(
            Counter(
                s.kind
                for s in effective
                if s.kind in {"price", "availability", "deposit", "contract", "payment"}
            )
        ),
        "signals": [{**serialize(s), "direction": directions[s.message_id]} for s in signals],
        "pending_decisions": sum(s.review_state == "pending" for s in signals),
        "registered_operations": [serialize(o) for o in operations],
        "jordy_confirmed": [
            serialize(o)
            for o in operations
            if o.actor == "jordy-admin" and o.action in {"booking.confirmed", "booking.rescheduled"}
        ],
        "manual_notes": [serialize(n) for n in notes],
        "commercial_plans": [serialize(p) for p in proposals],
        "unanswered_note": "Sin respuesta al cierre del día; no implica abandono definitivo.",
        "scope": "Detecciones del texto almacenado; no confirma contratación ni modifica agenda.",
    }
    values = dict(day=day, timezone=timezone, content=jsonable_encoder(content), generated_at=now())
    session.execute(
        insert(DailySummary)
        .values(**values)
        .on_conflict_do_update(
            index_elements=["day"], set_={k: v for k, v in values.items() if k != "day"}
        )
    )
    return values


@router.get("/summaries/{day}")
def get_summary(day: date, session: DB):
    row = session.get(DailySummary, day)
    return serialize(row) if row else None


@router.post("/summaries/{day}")
def regenerate(day: date, session: DB):
    with session.begin():
        return generate_summary(session, day)


class ScheduleInput(Input):
    local_time: time | None = None
    start_day: date

    @model_validator(mode="after")
    def local_only(self):
        if self.local_time and (self.local_time.tzinfo or self.local_time.second):
            raise ValueError("Usa hora local con precisión de minutos.")
        return self


@router.get("/schedule")
def get_schedule(session: DB):
    row = session.get(SummarySchedule, 1)
    return serialize(row) if row else {"local_time": None, "start_day": None, "last_day": None}


@router.put("/schedule")
def set_schedule(data: ScheduleInput, session: DB):
    with session.begin():
        session.execute(
            insert(SummarySchedule)
            .values(id=1, **data.model_dump())
            .on_conflict_do_update(
                index_elements=["id"],
                set_={
                    **data.model_dump(),
                    "last_day": None,
                    "last_error": None,
                },
            )
        )
        audit(session, "commercial.schedule_changed", 1)
    return get_schedule(session)


def recover_summaries(engine, current=None):
    """Called at startup and each minute. One missed day per tick, no sending."""
    current = (current or now()).astimezone(ZoneInfo(settings().studio_timezone))
    with Session(engine) as session, session.begin():
        row = session.scalar(
            select(SummarySchedule).where(SummarySchedule.id == 1).with_for_update(skip_locked=True)
        )
        if not row or row.local_time is None:
            return
        # Selected local time generates the previous completed calendar day.
        latest = current.date() - timedelta(days=1 if current.time() >= row.local_time else 2)
        next_day = row.last_day + timedelta(days=1) if row.last_day else row.start_day
        day = max(row.start_day, next_day)
        if day <= latest:
            generate_summary(session, day)
            row.last_day, row.last_error = day, None
