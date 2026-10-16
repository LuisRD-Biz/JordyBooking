"""Contact capture, duplicate warnings and verifiable commercial classification."""

import re

from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.orm import Session

from jordy.domain import Conflict
from jordy.models import Customer
from jordy.schemas import CustomerInput


def normalized_phone(value):
    return "".join(c for c in (value or "") if c.isdigit()) or None


def contact_identifiers(data):
    legacy = (data.contact or "").strip()
    phone = data.phone or (legacy if re.fullmatch(r"[+()0-9 .-]{7,}", legacy) else None)
    email = data.email or (legacy if re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", legacy) else None)
    return normalized_phone(phone), email.lower() if email else None


def possible_duplicates(session: Session, data: CustomerInput, exclude=None):
    conditions = []
    phone, email = contact_identifiers(data)
    if phone:
        conditions.append(
            or_(
                Customer.normalized_phone == phone,
                and_(
                    Customer.contact.op("~")(r"^[+()0-9 .-]{7,}$"),
                    func.regexp_replace(Customer.contact, "[^0-9]", "", "g") == phone,
                ),
            )
        )
    if email:
        conditions.append(
            or_(
                Customer.normalized_email == email, func.lower(func.trim(Customer.contact)) == email
            )
        )
    if not conditions:
        return []
    stmt = select(Customer.id).where(or_(*conditions))
    if exclude is not None:
        stmt = stmt.where(Customer.id != exclude)
    return list(session.scalars(stmt.limit(20)))


def save_customer(session: Session, data: CustomerInput, existing: Customer | None = None):
    from jordy.services import audit, now

    identifiers = contact_identifiers(data)
    for identifier in sorted(value for value in identifiers if value):
        session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:value, 0))"),
            {"value": "customer-contact:" + identifier},
        )
    duplicates = possible_duplicates(session, data, existing.id if existing else None)
    if duplicates and not data.duplicate_ack:
        raise Conflict(
            "Hay contactos con el mismo teléfono o correo. Revisa coincidencias y "
            "confirma expresamente si se trata de otra persona."
        )
    customer = existing or Customer()
    for key, value in data.model_dump(exclude={"duplicate_ack"}).items():
        setattr(customer, key, value)
    customer.normalized_phone, customer.normalized_email = identifiers
    customer.last_activity_at = now()
    session.add(customer)
    session.flush()
    audit(session, "customer.updated" if existing else "customer.created", customer.id)
    return customer
