import hashlib
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from jordy.domain import (
    AvailabilityService,
    Conflict,
    RuleViolation,
    require_confirmation,
    require_transition,
)
from jordy.models import (
    AuditLog,
    Booking,
    BookingDocument,
    Capability,
    Contract,
    Customer,
    IdempotencyRecord,
    Lead,
    Occupancy,
    Outbox,
    Package,
    PackageRequirement,
    Quote,
    Resource,
    ResourceCapability,
)
from jordy.repository import available_resources, require
from jordy.schemas import BookingInput, PackageInput, ResourceInput


def now():
    return datetime.now(UTC)


def audit(session: Session, action: str, entity_id: int):
    session.add(AuditLog(action=action, entity_id=entity_id, created_at=now()))


def capabilities(session: Session, codes):
    for code in sorted(set(codes)):
        session.execute(insert(Capability).values(code=code).on_conflict_do_nothing())


def create_resource(session: Session, data: ResourceInput):
    capabilities(session, data.capabilities)
    resource = Resource(
        name=data.name,
        kind=data.kind,
        capabilities=[ResourceCapability(capability=c) for c in data.capabilities],
    )
    session.add(resource)
    session.flush()
    audit(session, "resource.created", resource.id)
    return resource


def save_package(session: Session, data: PackageInput, identity: int | None = None):
    capabilities(session, [r.capability for r in data.requirements])
    package = require(session, Package, identity, lock=True) if identity else Package()
    if identity:
        package.requirements.clear()
        session.flush()
    for key, value in data.model_dump(exclude={"requirements"}).items():
        setattr(package, key, value)
    package.requirements = [PackageRequirement(**r.model_dump()) for r in data.requirements]
    session.add(package)
    session.flush()
    audit(session, "package.updated" if identity else "package.created", package.id)
    return package


def snapshot(package: Package):
    return {
        "name": package.name,
        "price": str(package.price),
        "currency": package.currency,
        "terms": package.terms,
        "duration_minutes": package.duration_minutes,
        "buffer_minutes": package.buffer_minutes,
        "preparation_minutes": package.preparation_minutes,
        "requirements": {r.capability: r.quantity for r in package.requirements},
    }


def allocation(session: Session, snap: dict, start: datetime, *, lock=False):
    end = start + timedelta(minutes=snap["duration_minutes"])
    buffer = timedelta(minutes=snap["buffer_minutes"])
    preparation = timedelta(minutes=snap["preparation_minutes"])
    candidates = available_resources(session, start - preparation, end + buffer, lock=lock)
    return AvailabilityService.check_availability(snap["requirements"], candidates)


def create_booking(session: Session, data: BookingInput, key: str):
    # Transaction-scoped advisory lock serializes retries with the same key.
    from sqlalchemy import text

    session.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"), {"key": key})
    omitted = {field for field in ["new_customer", "quote_id"] if getattr(data, field) is None}
    digest = hashlib.sha256(data.model_dump_json(exclude=omitted).encode()).hexdigest()
    prior = session.get(IdempotencyRecord, key)
    if prior:
        if prior.request_hash != digest:
            raise Conflict("La clave de idempotencia ya se utilizó con otros datos.")
        return require(session, Booking, prior.booking_id)
    if data.starts_at <= now():
        raise RuleViolation("La solicitud debe tener una fecha futura.")
    from jordy.customers import save_customer

    customer = (
        save_customer(session, data.new_customer)
        if data.new_customer
        else require(session, Customer, data.customer_id)
    )
    quote = require(session, Quote, data.quote_id) if data.quote_id else None
    lead = require(session, Lead, quote.lead_id, lock=True) if quote else None
    package = require(session, Package, data.package_id, lock=True)
    snap = snapshot(package)
    if quote:
        if lead.customer_id != customer.id or quote.package_id != package.id:
            raise RuleViolation("La cotización no corresponde al contacto y paquete seleccionados.")
        if lead.status in {"lost", "won", "pending_booking"}:
            raise Conflict("La oportunidad está cerrada o ya tiene una solicitud en curso.")
        snap = quote.snapshot.copy()
        lead.status, lead.last_activity_at = "pending_booking", now()
    booking = Booking(
        customer_id=customer.id,
        package_id=package.id,
        kind=snap.get("kind", package.kind),
        starts_at=data.starts_at,
        ends_at=data.starts_at + timedelta(minutes=snap["duration_minutes"]),
        location=data.location,
        snapshot=snap,
        quote_id=data.quote_id,
    )
    customer.last_activity_at = now()
    session.add(booking)
    session.flush()
    session.add(IdempotencyRecord(key=key, request_hash=digest, booking_id=booking.id))
    audit(session, "booking.requested", booking.id)
    return booking


def occupy(session: Session, booking: Booking):
    assignments = allocation(session, booking.snapshot, booking.starts_at, lock=True)
    if assignments is None:
        raise Conflict("No hay personal o equipo suficiente para este horario.")
    buffer = timedelta(minutes=booking.snapshot["buffer_minutes"])
    preparation = timedelta(minutes=booking.snapshot["preparation_minutes"])
    for resource_id, role in assignments.items():
        session.add(
            Occupancy(
                resource_id=resource_id,
                booking_id=booking.id,
                capability=role,
                starts_at=booking.starts_at - preparation,
                ends_at=booking.ends_at + buffer,
            )
        )


def enqueue(session: Session, booking: Booking, action: str):
    entry = Outbox(
        event_key=f"booking:{booking.id}:{action}",
        payload={"booking_id": booking.id, "action": action},
        available_at=now(),
    )
    session.add(entry)


def approve(session: Session, identity: int, location: str):
    booking = require(session, Booking, identity, lock=True)
    signed_at = booking.contract.signed_at if booking.contract else None
    require_confirmation(booking.status, booking.kind, location, signed_at)
    if booking.starts_at <= now():
        raise RuleViolation("No se puede confirmar una reservación en el pasado.")
    occupy(session, booking)
    booking.location = location
    booking.status = "confirmed"
    booking.approved_at = now()
    require(session, Customer, booking.customer_id).last_activity_at = now()
    if booking.quote_id:
        quote = require(session, Quote, booking.quote_id)
        lead = require(session, Lead, quote.lead_id, lock=True)
        lead.status, lead.last_activity_at = "won", now()
    audit(session, "booking.confirmed", booking.id)
    enqueue(session, booking, "confirmed")
    return booking


def register_contract(
    session: Session, identity: int, reference: str, signed_at: datetime, document_id=None
):
    booking = require(session, Booking, identity, lock=True)
    if booking.kind != "event" or booking.status != "pending_approval":
        raise Conflict("Solo se registra contrato para eventos pendientes.")
    if signed_at > now():
        raise RuleViolation("La firma no puede estar fechada en el futuro.")
    if booking.contract:
        raise Conflict("Ya existe un contrato registrado; requiere revisión explícita.")
    if document_id:
        document = session.get(BookingDocument, document_id)
        if not document or document.booking_id != identity or document.document_type != "contract":
            raise RuleViolation("Selecciona un contrato adjunto de esta misma reservación.")
    session.add(
        Contract(
            booking_id=identity, reference=reference, signed_at=signed_at, document_id=document_id
        )
    )
    audit(session, "contract.recorded", identity)


def transition(session: Session, identity: int, target: str):
    booking = require(session, Booking, identity, lock=True)
    require_transition(booking.status, target)
    if target == "completed" and booking.ends_at > now():
        raise RuleViolation("La reservación todavía no ha terminado.")
    if target == "cancelled":
        session.execute(
            update(Occupancy).where(Occupancy.booking_id == identity).values(active=False)
        )
    booking.status = target
    require(session, Customer, booking.customer_id).last_activity_at = now()
    audit(session, f"booking.{target}", identity)
    enqueue(session, booking, target)
    return booking


def reschedule(session: Session, identity: int, start: datetime, location: str):
    booking = require(session, Booking, identity, lock=True)
    if booking.status not in {"pending_approval", "confirmed"}:
        raise Conflict("No se puede reprogramar esta reservación.")
    if booking.kind == "event" and booking.contract:
        raise Conflict("Un evento con contrato requiere revisar el contrato antes de reprogramar.")
    if start <= now():
        raise RuleViolation("La nueva fecha debe ser futura.")
    # Reuse occupancy rows only after locking resources. Any failure rolls the whole
    # transaction back, preserving the original schedule and assignments.
    available_resources(session, booking.starts_at, booking.ends_at, lock=True)
    existing = session.scalars(select(Occupancy).where(Occupancy.booking_id == identity)).all()
    for row in existing:
        session.delete(row)
    session.flush()
    booking.starts_at = start
    booking.ends_at = start + timedelta(minutes=booking.snapshot["duration_minutes"])
    booking.location = location
    if booking.status == "confirmed":
        occupy(session, booking)
    audit(session, "booking.rescheduled", identity)
    # Each successful reschedule gets a distinct durable event identifier.
    session.flush()
    from uuid import uuid4

    enqueue(session, booking, f"rescheduled:{uuid4()}")
    return booking
