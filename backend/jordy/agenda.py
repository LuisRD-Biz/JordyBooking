from datetime import date, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from jordy.api import ADMIN
from jordy.config import settings
from jordy.db import get_session
from jordy.domain import RuleViolation, day_bounds
from jordy.models import Appointment, Booking, Customer, Occupancy, Resource

MAX_DAYS = 62
APPOINTMENT_LABELS = {"contract": "Firma de contrato", "meeting": "Reunión"}

router = APIRouter(prefix="/api", dependencies=ADMIN)
DB = Annotated[Session, Depends(get_session)]


class AgendaItem(BaseModel):
    type: Literal["booking", "appointment", "block"]
    id: int
    starts_at: datetime
    ends_at: datetime
    title: str
    subtitle: str
    status: str
    kind: str
    customer_id: int | None
    booking_id: int | None = None
    resource_id: int | None = None
    location: str | None = None


def window(start: date, end: date) -> tuple[datetime, datetime]:
    if not (1900 <= start.year and end.year <= 9998):
        raise RuleViolation("Fecha fuera del rango admitido.")
    if end < start:
        raise RuleViolation("El rango de fechas está invertido.")
    if (end - start).days + 1 > MAX_DAYS:
        raise RuleViolation(f"El rango máximo es de {MAX_DAYS} días.")
    zone = settings().studio_timezone
    return day_bounds(start, zone)[0], day_bounds(end, zone)[1]


def collect(
    session: Session, lower: datetime, upper: datetime, include_cancelled: bool = False
) -> list[AgendaItem]:
    def overlapping(model):
        return model.starts_at < upper, model.ends_at > lower

    items: list[AgendaItem] = []
    bookings = select(Booking, Customer.name).join(Customer).where(*overlapping(Booking))
    appointments = (
        select(Appointment, Customer.name).join(Customer).where(*overlapping(Appointment))
    )
    if not include_cancelled:
        bookings = bookings.where(Booking.status != "cancelled")
        appointments = appointments.where(Appointment.status != "cancelled")
    for booking, name in session.execute(bookings):
        items.append(
            AgendaItem(
                type="booking",
                id=booking.id,
                starts_at=booking.starts_at,
                ends_at=booking.ends_at,
                title=name,
                subtitle=booking.snapshot["name"],
                status=booking.status,
                kind=booking.kind,
                customer_id=booking.customer_id,
                booking_id=booking.id,
                location=booking.location,
            )
        )
    for appointment, name in session.execute(appointments):
        items.append(
            AgendaItem(
                type="appointment",
                id=appointment.id,
                starts_at=appointment.starts_at,
                ends_at=appointment.ends_at,
                title=name,
                subtitle=APPOINTMENT_LABELS[appointment.kind],
                status=appointment.status,
                kind=appointment.kind,
                customer_id=appointment.customer_id,
                booking_id=appointment.booking_id,
                location=appointment.location,
            )
        )
    blocks = (
        select(Occupancy, Resource.name, Resource.kind)
        .join(Resource, Resource.id == Occupancy.resource_id)
        .where(Occupancy.booking_id.is_(None), Occupancy.active.is_(True), *overlapping(Occupancy))
    )
    for block, name, kind in session.execute(blocks):
        items.append(
            AgendaItem(
                type="block",
                id=block.id,
                starts_at=block.starts_at,
                ends_at=block.ends_at,
                title=name,
                subtitle=block.reason or "",
                status="active",
                kind=kind,
                customer_id=None,
                resource_id=block.resource_id,
            )
        )
    return sorted(items, key=lambda item: (item.starts_at, item.type, item.id))


@router.get("/agenda", response_model=list[AgendaItem])
def agenda(
    session: DB,
    start: Annotated[date, Query(alias="from", description="Primer día, hora del estudio.")],
    end: Annotated[date, Query(alias="to", description="Último día, incluido.")],
    include_cancelled: bool = False,
):
    lower, upper = window(start, end)
    return collect(session, lower, upper, include_cancelled)
