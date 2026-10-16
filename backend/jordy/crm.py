"""Sales opportunities, immutable quotation versions and signature appointments."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import AwareDatetime, Field, model_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from jordy.api import authenticate
from jordy.customers import save_customer
from jordy.db import get_session
from jordy.domain import Conflict, RuleViolation
from jordy.models import Appointment, Booking, Customer, Lead, Package, Quote, Resource
from jordy.repository import require
from jordy.schemas import CustomerInput, Input
from jordy.services import audit, now, snapshot

router = APIRouter(prefix="/api", dependencies=[Depends(authenticate)])
DB = Annotated[Session, Depends(get_session)]


class LeadInput(Input):
    customer_id: int | None = Field(default=None, gt=0)
    new_customer: CustomerInput | None = None
    service: str = Field(min_length=1, max_length=200)
    channel: str = Field(min_length=1, max_length=100)
    requested_date: AwareDatetime | None = None
    notes: str = Field(default="", max_length=4000)

    @model_validator(mode="after")
    def one_contact(self):
        if (self.customer_id is None) == (self.new_customer is None):
            raise ValueError("Selecciona o crea un contacto, no ambos")
        return self


class QuoteInput(Input):
    package_id: int = Field(gt=0)


class LeadStatus(Input):
    status: Literal["contacted", "lost", "reopen"]


class AppointmentInput(Input):
    customer_id: int = Field(gt=0)
    booking_id: int | None = Field(default=None, gt=0)
    lead_id: int | None = Field(default=None, gt=0)
    kind: Literal["contract", "meeting"]
    starts_at: AwareDatetime
    ends_at: AwareDatetime
    location: str = Field(min_length=1, max_length=500)
    notes: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def ordered(self):
        if self.ends_at <= self.starts_at:
            raise ValueError("El final debe ser posterior al inicio")
        return self


class AppointmentStatus(Input):
    status: Literal["completed", "cancelled"]


def serialize(record):
    return {column.name: getattr(record, column.name) for column in record.__table__.columns}


@router.get("/dashboard")
def dashboard(session: DB):
    def count(model, *conditions):
        return session.scalar(select(func.count()).select_from(model).where(*conditions))

    return {
        "upcoming": count(Booking, Booking.status == "confirmed", Booking.ends_at >= now()),
        "pending": count(Booking, Booking.status == "pending_approval"),
        "customers": count(Customer),
        "resources": count(Resource),
        "staff": count(Resource, Resource.kind == "staff"),
        "equipment": count(Resource, Resource.kind == "equipment"),
        "leads": count(Lead),
        "won": count(Lead, Lead.status == "won"),
        "quotes": count(Quote),
        "appointments": count(
            Appointment, Appointment.status == "scheduled", Appointment.ends_at >= now()
        ),
    }


@router.post("/leads", status_code=201)
def create_lead(data: LeadInput, session: DB):
    with session.begin():
        customer = (
            save_customer(session, data.new_customer)
            if data.new_customer
            else require(session, Customer, data.customer_id)
        )
        lead = Lead(
            **data.model_dump(exclude={"customer_id", "new_customer"}),
            customer_id=customer.id,
            created_at=now(),
            last_activity_at=now(),
        )
        customer.last_activity_at = now()
        session.add(lead)
        session.flush()
        audit(session, "lead.created", lead.id)
        result = serialize(lead)
    return result


@router.post("/leads/{identity}/status")
def lead_status(identity: int, data: LeadStatus, session: DB):
    with session.begin():
        lead = require(session, Lead, identity, lock=True)
        allowed = {
            "new": {"contacted", "lost"},
            "contacted": {"lost"},
            "quoted": {"lost"},
            "pending_booking": {"reopen"},
            "won": {"reopen"},
            "lost": set(),
        }
        if data.status not in allowed[lead.status]:
            raise Conflict("Transición comercial no permitida.")
        if data.status == "reopen":
            active = session.scalar(
                select(func.count())
                .select_from(Booking)
                .join(Quote)
                .where(Quote.lead_id == identity, Booking.status != "cancelled")
            )
            if active:
                raise Conflict(
                    "Para volver a cotizar, las reservaciones previas deben estar canceladas."
                )
        lead.status, lead.last_activity_at = (
            "quoted" if data.status == "reopen" else data.status,
            now(),
        )
        require(session, Customer, lead.customer_id).last_activity_at = now()
        audit(session, f"lead.{data.status}", identity)
        result = serialize(lead)
    return result


@router.post("/leads/{identity}/quotes", status_code=201)
def create_quote(identity: int, data: QuoteInput, session: DB):
    with session.begin():
        lead = require(session, Lead, identity, lock=True)
        if lead.status in {"won", "lost", "pending_booking"}:
            raise Conflict("La oportunidad está cerrada o ya tiene una solicitud en curso.")
        package = require(session, Package, data.package_id, lock=True)
        version = (
            session.scalar(select(func.max(Quote.version)).where(Quote.lead_id == identity)) or 0
        ) + 1
        quote = Quote(
            lead_id=identity,
            package_id=package.id,
            version=version,
            snapshot={**snapshot(package), "kind": package.kind},
            created_at=now(),
        )
        session.add(quote)
        session.flush()
        lead.status, lead.last_activity_at = "quoted", now()
        require(session, Customer, lead.customer_id).last_activity_at = now()
        audit(session, "quote.created", quote.id)
        result = serialize(quote)
    return result


@router.get("/leads/{identity}/history")
def history(identity: int, session: DB):
    lead = require(session, Lead, identity)
    quotes = list(
        session.scalars(select(Quote).where(Quote.lead_id == identity).order_by(Quote.version))
    )
    bookings = list(
        session.scalars(
            select(Booking).join(Quote).where(Quote.lead_id == identity).order_by(Booking.id)
        )
    )
    appointments = list(
        session.scalars(
            select(Appointment)
            .where(Appointment.lead_id == identity)
            .order_by(Appointment.starts_at)
        )
    )
    return {
        "lead": {
            **serialize(lead),
            "customer_name": require(session, Customer, lead.customer_id).name,
        },
        "quotes": [serialize(q) for q in quotes],
        "bookings": [serialize(b) for b in bookings],
        "appointments": [serialize(a) for a in appointments],
    }


@router.post("/appointments", status_code=201)
def create_appointment(data: AppointmentInput, session: DB):
    with session.begin():
        customer = require(session, Customer, data.customer_id)
        if data.starts_at <= now():
            raise RuleViolation("La cita debe ser futura.")
        for model, identity in [(Booking, data.booking_id), (Lead, data.lead_id)]:
            if identity and require(session, model, identity).customer_id != customer.id:
                raise RuleViolation("La cita debe pertenecer al mismo contacto.")
        if data.kind == "contract" and not data.booking_id:
            raise RuleViolation("La cita de firma requiere una reservación vinculada.")
        if data.booking_id:
            booking = require(session, Booking, data.booking_id)
            if booking.quote_id:
                linked_lead = require(session, Quote, booking.quote_id).lead_id
                if data.lead_id and data.lead_id != linked_lead:
                    raise RuleViolation(
                        "La cita no corresponde a la oportunidad de la reservación."
                    )
                data.lead_id = linked_lead
        appointment = Appointment(**data.model_dump(), created_at=now())
        session.add(appointment)
        session.flush()
        customer.last_activity_at = now()
        audit(session, "appointment.created", appointment.id)
        result = serialize(appointment)
    return result


@router.post("/appointments/{identity}/status")
def appointment_status(identity: int, data: AppointmentStatus, session: DB):
    with session.begin():
        appointment = require(session, Appointment, identity, lock=True)
        if appointment.status != "scheduled":
            raise Conflict("La cita ya está cerrada.")
        if data.status == "completed" and appointment.ends_at > now():
            raise RuleViolation("La cita todavía no ha terminado.")
        appointment.status = data.status
        require(session, Customer, appointment.customer_id).last_activity_at = now()
        audit(session, f"appointment.{data.status}", identity)
    return {"status": data.status}
