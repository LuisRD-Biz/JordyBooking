import secrets
from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.security import APIKeyHeader
from sqlalchemy import select
from sqlalchemy.orm import Session

from jordy import services
from jordy.auth import same_origin, valid_session
from jordy.config import settings
from jordy.db import get_session
from jordy.domain import Conflict, RuleViolation, christmas_slots
from jordy.models import (
    AuditLog,
    Booking,
    Customer,
    Occupancy,
    Outbox,
    Package,
    Resource,
    ResourceCapability,
)
from jordy.repository import available_resources, require
from jordy.schemas import (
    ApprovalInput,
    AvailabilityInput,
    BlockInput,
    BookingInput,
    BookingOutput,
    ContractInput,
    CustomerInput,
    PackageInput,
    RescheduleInput,
    ResourceInput,
)

key_header = APIKeyHeader(name="X-Admin-Key", auto_error=False)


def authenticate(request: Request, key: Annotated[str | None, Depends(key_header)]):
    if valid_session(request):
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            same_origin(request)
        return
    expected = settings().admin_api_key.get_secret_value()
    if key is None or not secrets.compare_digest(key.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="Acceso administrativo requerido.")


router = APIRouter(prefix="/api", dependencies=[Depends(authenticate)])
DB = Annotated[Session, Depends(get_session)]
Limit = Annotated[int, Query(ge=1, le=200)]


@router.post("/customers", status_code=201)
def customer_create(data: CustomerInput, session: DB):
    with session.begin():
        customer = Customer(**data.model_dump())
        session.add(customer)
        session.flush()
        services.audit(session, "customer.created", customer.id)
        result = {"id": customer.id, **data.model_dump()}
    return result


@router.get("/customers")
def customers(session: DB, limit: Limit = 100, offset: int = Query(0, ge=0)):
    return session.scalars(select(Customer).order_by(Customer.id).limit(limit).offset(offset)).all()


@router.post("/resources", status_code=201)
def resource_create(data: ResourceInput, session: DB):
    with session.begin():
        resource = services.create_resource(session, data)
        result = {"id": resource.id, **data.model_dump()}
    return result


@router.get("/resources")
def resources(session: DB, limit: Limit = 100, offset: int = Query(0, ge=0)):
    return [
        {
            "id": r.id,
            "name": r.name,
            "kind": r.kind,
            "capabilities": [c.capability for c in r.capabilities],
        }
        for r in session.scalars(select(Resource).order_by(Resource.id).limit(limit).offset(offset))
    ]


@router.post("/packages", status_code=201)
def package_create(data: PackageInput, session: DB):
    with session.begin():
        package = services.save_package(session, data)
        result = {"id": package.id, **data.model_dump()}
    return result


@router.put("/packages/{identity}")
def package_update(identity: int, data: PackageInput, session: DB):
    with session.begin():
        package = services.save_package(session, data, identity)
        result = {"id": package.id, **data.model_dump()}
    return result


@router.get("/packages")
def packages(session: DB, limit: Limit = 100, offset: int = Query(0, ge=0)):
    return [
        {"id": p.id, "kind": p.kind, **services.snapshot(p)}
        for p in session.scalars(select(Package).order_by(Package.id).limit(limit).offset(offset))
    ]


@router.post("/availability")
def availability(data: AvailabilityInput, session: DB):
    package = require(session, Package, data.package_id)
    assignments = services.allocation(session, services.snapshot(package), data.starts_at)
    return {
        "available": assignments is not None,
        "suggested_assignments": assignments or {},
        "notice": "La consulta no aparta recursos; se revalida al confirmar.",
    }


@router.get("/availability/christmas-slots")
def christmas_availability(day: date, package_id: int, session: DB):
    package = require(session, Package, package_id)
    if (
        package.kind != "session"
        or package.duration_minutes != 90
        or package.buffer_minutes != 30
        or package.preparation_minutes != 0
    ):
        raise RuleViolation(
            "La plantilla navideña requiere sesión de 90 min y margen posterior de 30."
        )
    snap = services.snapshot(package)
    return {
        "timezone": settings().studio_timezone,
        "holds_enabled": False,
        "slots": [
            {
                "starts_at": start,
                "session_ends_at": start + timedelta(minutes=90),
                "resource_free_at": start + timedelta(minutes=120),
                "available": start > services.now()
                and services.allocation(session, snap, start) is not None,
            }
            for start in christmas_slots(day, settings().studio_timezone)
        ],
    }


@router.post("/bookings", response_model=BookingOutput, status_code=201)
def booking_create(
    data: BookingInput,
    session: DB,
    idempotency_key: Annotated[str, Header(min_length=8, max_length=100)],
):
    with session.begin():
        result = BookingOutput.model_validate(
            services.create_booking(session, data, idempotency_key)
        )
    return result


@router.get("/bookings", response_model=list[BookingOutput])
def bookings(session: DB, limit: Limit = 100, offset: int = Query(0, ge=0)):
    return session.scalars(
        select(Booking).order_by(Booking.starts_at, Booking.id).limit(limit).offset(offset)
    ).all()


@router.get("/bookings/{identity}", response_model=BookingOutput)
def booking_get(identity: int, session: DB):
    return require(session, Booking, identity)


@router.get("/bookings/{identity}/assignments")
def booking_assignments(identity: int, session: DB):
    require(session, Booking, identity)
    return session.scalars(
        select(Occupancy)
        .where(Occupancy.booking_id == identity, Occupancy.active.is_(True))
        .order_by(Occupancy.resource_id)
    ).all()


@router.post("/bookings/{identity}/approve", response_model=BookingOutput)
def booking_approve(identity: int, data: ApprovalInput, session: DB):
    with session.begin():
        result = BookingOutput.model_validate(services.approve(session, identity, data.location))
    return result


@router.post("/bookings/{identity}/contract", status_code=201)
def booking_contract(identity: int, data: ContractInput, session: DB):
    with session.begin():
        services.register_contract(session, identity, data.reference, data.signed_at)
    return {"recorded": True, "notice": "Registro administrativo; no firma electrónica."}


@router.post("/bookings/{identity}/cancel", response_model=BookingOutput)
def booking_cancel(identity: int, session: DB):
    with session.begin():
        result = BookingOutput.model_validate(services.transition(session, identity, "cancelled"))
    return result


@router.post("/bookings/{identity}/complete", response_model=BookingOutput)
def booking_complete(identity: int, session: DB):
    with session.begin():
        result = BookingOutput.model_validate(services.transition(session, identity, "completed"))
    return result


@router.post("/bookings/{identity}/reschedule", response_model=BookingOutput)
def booking_reschedule(identity: int, data: RescheduleInput, session: DB):
    with session.begin():
        result = BookingOutput.model_validate(
            services.reschedule(session, identity, data.starts_at, data.location)
        )
    return result


@router.post("/blocks", status_code=201)
def block_create(data: BlockInput, session: DB):
    with session.begin():
        require(session, Resource, data.resource_id)
        available = available_resources(session, data.starts_at, data.ends_at, lock=True)
        if data.resource_id not in {r.id for r in available}:
            raise Conflict("El recurso ya está ocupado en ese horario.")
        row = Occupancy(**data.model_dump())
        session.add(row)
        session.flush()
        services.audit(session, "block.created", row.id)
        result = {"id": row.id, **data.model_dump()}
    return result


@router.get("/blocks")
def blocks(session: DB, limit: Limit = 100, offset: int = Query(0, ge=0)):
    return session.scalars(
        select(Occupancy)
        .where(Occupancy.booking_id.is_(None), Occupancy.active.is_(True))
        .order_by(Occupancy.starts_at)
        .limit(limit)
        .offset(offset)
    ).all()


@router.post("/blocks/{identity}/release")
def block_release(identity: int, session: DB):
    with session.begin():
        block = require(session, Occupancy, identity, lock=True)
        if block.booking_id is not None:
            raise Conflict("Use la cancelación de reservación para liberar asignaciones.")
        block.active = False
        services.audit(session, "block.released", identity)
    return {"released": True}


@router.get("/operations")
def operations(session: DB, limit: Limit = 100):
    return session.scalars(select(Outbox).order_by(Outbox.id.desc()).limit(limit)).all()


@router.put("/customers/{identity}")
def customer_update(identity: int, data: CustomerInput, session: DB):
    with session.begin():
        customer = require(session, Customer, identity, lock=True)
        customer.name, customer.contact = data.name, data.contact
        services.audit(session, "customer.updated", identity)
    return {"id": identity, **data.model_dump()}


@router.put("/resources/{identity}")
def resource_update(identity: int, data: ResourceInput, session: DB):
    with session.begin():
        resource = require(session, Resource, identity, lock=True)
        active_roles = set(
            session.scalars(
                select(Occupancy.capability).where(
                    Occupancy.resource_id == identity,
                    Occupancy.active.is_(True),
                    Occupancy.ends_at > services.now(),
                    Occupancy.booking_id.is_not(None),
                )
            )
        )
        if active_roles and (
            data.kind != resource.kind or not active_roles.issubset(data.capabilities)
        ):
            raise Conflict("No puedes quitar capacidades usadas en reservaciones vigentes.")
        services.capabilities(session, data.capabilities)
        resource.capabilities.clear()
        session.flush()
        resource.name, resource.kind = data.name, data.kind
        resource.capabilities = [ResourceCapability(capability=c) for c in data.capabilities]
        services.audit(session, "resource.updated", identity)
    return {"id": identity, **data.model_dump()}


@router.get("/bookings/{identity}/contract")
def contract_get(identity: int, session: DB):
    booking = require(session, Booking, identity)
    if booking.contract is None:
        return None
    return {"reference": booking.contract.reference, "signed_at": booking.contract.signed_at}


@router.get("/audit")
def audit_list(session: DB, limit: Limit = 100):
    return session.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(limit)).all()
