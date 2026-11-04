"""PostgreSQL filtering and stable pagination in studio-local calendar days."""

from datetime import UTC, date, datetime, time, timedelta
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query
from pydantic import Field, model_validator
from sqlalchemy import case, exists, func, or_, select
from sqlalchemy.orm import Session

from jordy.api import authenticate
from jordy.config import settings
from jordy.customers import normalized_phone, possible_duplicates
from jordy.db import get_session
from jordy.domain import RuleViolation
from jordy.models import Appointment, Booking, BookingDocument, Contract, Customer, Lead
from jordy.schemas import BookingOutput, CustomerInput, Input

router = APIRouter(prefix="/api/search", dependencies=[Depends(authenticate)])
DB = Annotated[Session, Depends(get_session)]


class Filters(Input):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=25, ge=1, le=100)
    q: str = Field(default="", max_length=200)
    day: date | None = None
    date_from: date | None = None
    date_to: date | None = None
    month: int | None = Field(default=None, ge=1, le=12)
    year: int | None = Field(default=None, ge=1900, le=9998)
    order: Literal["asc", "desc"] = "asc"

    @model_validator(mode="after")
    def dates_valid(self):
        if bool(self.month) != bool(self.year):
            raise ValueError("Indica mes y año juntos")
        if (
            sum(
                [
                    self.day is not None,
                    self.month is not None,
                    self.date_from is not None or self.date_to is not None,
                ]
            )
            > 1
        ):
            raise ValueError("Usa fecha exacta, rango o mes/año; no los combines")
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("El rango de fechas está invertido")
        if any(d and d.year >= 9999 for d in [self.day, self.date_from, self.date_to]):
            raise ValueError("Fecha fuera del rango admitido")
        return self


class BookingFilters(Filters):
    upcoming: bool = False
    status: Literal["pending_approval", "confirmed", "completed", "cancelled"] | None = None
    kind: Literal["session", "event"] | None = None
    customer_id: int | None = Field(default=None, gt=0)
    has_contract: bool | None = None
    uploaded_from: date | None = None
    uploaded_to: date | None = None
    signed_from: date | None = None
    signed_to: date | None = None


class CustomerFilters(Filters):
    classification: Literal[
        "all", "contracted", "prospect", "occasional", "client", "recurrent", "featured"
    ] = "all"
    date_field: Literal["created", "activity", "requested"] = "created"


class LeadFilters(Filters):
    status: Literal["new", "contacted", "quoted", "pending_booking", "won", "lost"] | None = None
    date_field: Literal["created", "activity", "requested"] = "created"


def date_bounds(f: Filters):
    start, end = f.date_from, f.date_to
    if f.day:
        start = end = f.day
    if f.month:
        start = date(f.year, f.month, 1)
        end = (
            date(f.year + 1, 1, 1) if f.month == 12 else date(f.year, f.month + 1, 1)
        ) - timedelta(days=1)
    zone = ZoneInfo(settings().studio_timezone)
    lower = datetime.combine(start, time.min, zone).astimezone(UTC) if start else None
    upper = (
        datetime.combine(end + timedelta(days=1), time.min, zone).astimezone(UTC) if end else None
    )
    return lower, upper


def date_predicates(column, start=None, end=None, filters=None):
    try:
        f = filters or Filters(date_from=start, date_to=end)
    except ValueError as exc:
        raise RuleViolation("Rango de fechas inválido.") from exc
    lower, upper = date_bounds(f)
    return ([column >= lower] if lower else []) + ([column < upper] if upper else [])


def paginate(session, statement, f, sort):
    total = session.scalar(select(func.count()).select_from(statement.order_by(None).subquery()))
    ordered = [column.desc() if f.order == "desc" else column.asc() for column in sort]
    rows = session.execute(
        statement.order_by(*ordered).offset((f.page - 1) * f.page_size).limit(f.page_size)
    ).all()
    return rows, {"total": total, "page": f.page, "page_size": f.page_size}


def booking_query(f):
    statement = select(Booking, Customer.name).join(Customer)
    if f.upcoming:
        statement = statement.where(Booking.ends_at >= datetime.now(UTC))
    if f.q:
        statement = statement.where(
            or_(
                Customer.name.icontains(f.q, autoescape=True),
                Booking.snapshot["name"].astext.icontains(f.q, autoescape=True),
            )
        )
    for field in ["status", "kind", "customer_id"]:
        if getattr(f, field) is not None:
            statement = statement.where(getattr(Booking, field) == getattr(f, field))
    statement = statement.where(*date_predicates(Booking.starts_at, filters=f))
    docs = exists(
        select(BookingDocument.id).where(
            BookingDocument.booking_id == Booking.id, BookingDocument.document_type == "contract"
        )
    )
    if f.has_contract is not None:
        statement = statement.where(docs if f.has_contract else ~docs)
    if f.uploaded_from or f.uploaded_to:
        statement = statement.where(
            exists(
                select(BookingDocument.id).where(
                    BookingDocument.booking_id == Booking.id,
                    *date_predicates(BookingDocument.created_at, f.uploaded_from, f.uploaded_to),
                )
            )
        )
    if f.signed_from or f.signed_to:
        statement = statement.where(
            exists(
                select(Contract.booking_id).where(
                    Contract.booking_id == Booking.id,
                    *date_predicates(Contract.signed_at, f.signed_from, f.signed_to),
                )
            )
        )
    return statement


@router.get("/bookings")
def bookings(session: DB, filters: Annotated[BookingFilters, Query()]):
    rows, result = paginate(
        session, booking_query(filters), filters, [Booking.starts_at, Booking.id]
    )
    result["items"] = [
        {**BookingOutput.model_validate(b).model_dump(), "customer_name": name} for b, name in rows
    ]
    return result


@router.get("/calendar")
def calendar_summary(
    session: DB, month: int = Query(ge=1, le=12), year: int = Query(ge=1900, le=9998)
):
    day = func.date(func.timezone(settings().studio_timezone, Booking.starts_at))
    rows = session.execute(
        select(day, func.count())
        .where(
            Booking.status != "cancelled",
            *date_predicates(Booking.starts_at, filters=Filters(month=month, year=year)),
        )
        .group_by(day)
    ).all()
    return {str(day): count for day, count in rows}


@router.get("/customers")
def customers(session: DB, filters: Annotated[CustomerFilters, Query()]):
    counts = (
        select(
            Booking.customer_id,
            func.count().label("contracts"),
            func.max(Booking.starts_at).label("last_booking"),
        )
        .where(Booking.status.in_(["confirmed", "completed"]))
        .group_by(Booking.customer_id)
        .subquery()
    )
    count = func.coalesce(counts.c.contracts, 0)
    has_lead = exists(select(Lead.id).where(Lead.customer_id == Customer.id))
    category = case(
        (count >= 2, "recurrent"),
        (count == 1, "client"),
        (has_lead, "prospect"),
        else_="occasional",
    )
    statement = select(Customer, count, counts.c.last_booking, category).outerjoin(
        counts, counts.c.customer_id == Customer.id
    )
    if filters.q:
        statement = statement.where(
            or_(
                *[
                    column.icontains(filters.q, autoescape=True)
                    for column in [
                        Customer.name,
                        Customer.contact,
                        Customer.phone,
                        Customer.email,
                    ]
                ]
                + (
                    [Customer.normalized_phone.contains(normalized_phone(filters.q))]
                    if normalized_phone(filters.q)
                    else []
                )
            )
        )
    if filters.classification == "featured":
        statement = statement.where(Customer.featured.is_(True))
    elif filters.classification == "contracted":
        statement = statement.where(count >= 1)
    elif filters.classification != "all":
        statement = statement.where(category == filters.classification)
    column = Customer.created_at if filters.date_field == "created" else Customer.last_activity_at
    if filters.date_field == "requested":
        if any(date_bounds(filters)):
            statement = statement.where(
                or_(
                    exists(
                        select(Booking.id).where(
                            Booking.customer_id == Customer.id,
                            *date_predicates(Booking.starts_at, filters=filters),
                        )
                    ),
                    exists(
                        select(Lead.id).where(
                            Lead.customer_id == Customer.id,
                            *date_predicates(Lead.requested_date, filters=filters),
                        )
                    ),
                )
            )
    else:
        statement = statement.where(*date_predicates(column, filters=filters))
    rows, result = paginate(session, statement, filters, [Customer.name, Customer.id])
    result["items"] = [
        {
            "id": c.id,
            "name": c.name,
            "contact": c.contact,
            "phone": c.phone,
            "email": c.email,
            "notes": c.notes,
            "featured": c.featured,
            "created_at": c.created_at,
            "last_activity_at": c.last_activity_at,
            "contracts_count": n,
            "last_booking": last,
            "classification": cat,
        }
        for c, n, last, cat in rows
    ]
    return result


@router.get("/contact-matches")
def contact_matches(
    session: DB,
    phone: str = Query(default="", max_length=40),
    email: str = Query(default="", max_length=200),
):
    if not phone and not email:
        return []
    # Partial input is expected while typing. Match exact normalized identifiers only.
    data = CustomerInput.model_construct(phone=phone, email=email)
    identities = possible_duplicates(session, data)
    return [
        {"id": c.id, "name": c.name, "phone": c.phone, "email": c.email, "contact": c.contact}
        for c in session.scalars(select(Customer).where(Customer.id.in_(identities)))
    ]


@router.get("/leads")
def leads(session: DB, filters: Annotated[LeadFilters, Query()]):
    statement = select(Lead, Customer.name).join(Customer)
    if filters.q:
        statement = statement.where(
            or_(
                Customer.name.icontains(filters.q, autoescape=True),
                Lead.service.icontains(filters.q, autoescape=True),
            )
        )
    if filters.status:
        statement = statement.where(Lead.status == filters.status)
    column = {
        "created": Lead.created_at,
        "activity": Lead.last_activity_at,
        "requested": Lead.requested_date,
    }[filters.date_field]
    statement = statement.where(*date_predicates(column, filters=filters))
    rows, result = paginate(session, statement, filters, [column, Lead.id])
    result["items"] = [
        {**{c.name: getattr(lead, c.name) for c in Lead.__table__.columns}, "customer_name": name}
        for lead, name in rows
    ]
    return result


@router.get("/appointments")
def appointments(session: DB, filters: Annotated[Filters, Query()]):
    statement = (
        select(Appointment, Customer.name)
        .join(Customer)
        .where(*date_predicates(Appointment.starts_at, filters=filters))
    )
    if filters.q:
        statement = statement.where(Customer.name.icontains(filters.q, autoescape=True))
    rows, result = paginate(session, statement, filters, [Appointment.starts_at, Appointment.id])
    result["items"] = [
        {
            **{c.name: getattr(a, c.name) for c in Appointment.__table__.columns},
            "customer_name": name,
        }
        for a, name in rows
    ]
    return result
