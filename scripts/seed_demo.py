"""Synthetic studio fixtures for the running jordy-lab Compose project."""

import os
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from jordy import api, crm
from jordy.db import build_engine
from jordy.messaging.service import process_incoming
from jordy.models import Conversation, IdempotencyRecord
from jordy.schemas import ApprovalInput, BookingInput, CustomerInput, PackageInput, ResourceInput
from jordy.services import now

FIRST_BOOKING = "jordy-demo-v1:familiar"
LOCATION = "Demo · Estudio Jacaranda"


def seed(engine, zone):
    with engine.begin() as connection:
        connection.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"), {"key": FIRST_BOOKING}
        )
        if connection.scalar(
            select(IdempotencyRecord.booking_id).where(IdempotencyRecord.key == FIRST_BOOKING)
        ):
            return False

        # The application handlers own their sessions' transactions. Savepoints keep
        # every handler inside this single commit, including audit and outbox records.
        with Session(connection, join_transaction_mode="create_savepoint") as db:
            populate(db, zone)
    return True


def populate(db, zone):
    today = now().astimezone(zone).date()
    portrait_day = datetime.combine(today + timedelta(days=1), time(16), zone)
    wedding_day = datetime.combine(today + timedelta(days=14), time(16), zone)
    meeting_day = datetime.combine(today + timedelta(days=2), time(11), zone)

    for name, kind, capability in [
        ("Demo · Fotógrafa de estudio", "staff", "demo_fotografia"),
        ("Demo · Kit de iluminación", "equipment", "demo_iluminacion"),
    ]:
        api.resource_create(ResourceInput(name=name, kind=kind, capabilities=[capability]), db)

    requirements = [
        {"capability": "demo_fotografia", "quantity": 1},
        {"capability": "demo_iluminacion", "quantity": 1},
    ]
    portrait = api.package_create(
        PackageInput(
            name="Demo · Retrato familiar",
            kind="session",
            price="1800",
            duration_minutes=60,
            buffer_minutes=15,
            requirements=requirements,
            terms="Sesión en estudio con diez fotografías digitales.",
        ),
        db,
    )["id"]
    wedding = api.package_create(
        PackageInput(
            name="Demo · Boda civil",
            kind="event",
            price="8500",
            duration_minutes=240,
            preparation_minutes=30,
            requirements=requirements,
            terms="Cobertura de cuatro horas y galería digital.",
        ),
        db,
    )["id"]

    def customer(name, alias):
        return CustomerInput(name=f"Demo · {name}", email=f"{alias}@example.invalid")

    camila = api.customer_create(customer("Camila Sol", "camila.demo"), db)["id"]
    confirmed = api.booking_create(
        BookingInput(customer_id=camila, package_id=portrait, starts_at=portrait_day),
        db,
        FIRST_BOOKING,
    )
    api.booking_approve(confirmed.id, ApprovalInput(location=LOCATION), db)
    api.booking_create(
        BookingInput(
            new_customer=customer("Rafael Luna", "rafael.demo"),
            package_id=portrait,
            starts_at=portrait_day,
            location=LOCATION,
        ),
        db,
        "jordy-demo-v1:conflicto",
    )

    lead = crm.create_lead(
        crm.LeadInput(
            new_customer=customer("Jimena Nube", "jimena.demo"),
            service="Boda civil",
            channel="Presencial",
            requested_date=wedding_day,
        ),
        db,
    )
    quote = crm.create_quote(lead["id"], crm.QuoteInput(package_id=wedding), db)
    event = api.booking_create(
        BookingInput(
            customer_id=lead["customer_id"],
            package_id=wedding,
            quote_id=quote["id"],
            starts_at=wedding_day,
            location="Demo · Jardín del Lago",
        ),
        db,
        "jordy-demo-v1:boda",
    )
    crm.create_appointment(
        crm.AppointmentInput(
            customer_id=lead["customer_id"],
            lead_id=lead["id"],
            booking_id=event.id,
            kind="contract",
            starts_at=meeting_day,
            ends_at=meeting_day + timedelta(minutes=30),
            location=LOCATION,
            notes="Revisar la cotización y practicar el registro de firma.",
        ),
        db,
    )

    # Opaque demo identities can't route to a phone. Process locally without a webhook or a send.
    with db.begin():
        process_incoming(
            db,
            {
                "account": "demo-studio",
                "phone": "demo-emisor",
                "sender": "demo-ines",
                "external_id": "demo-v1-consulta",
                "name": "Demo · Inés Mar",
                "kind": "text",
                "time": now().isoformat(),
                "body": "¿Cuánto cuesta una sesión de retrato familiar?",
            },
        )
        prospect = db.scalars(
            select(Conversation.customer_id).where(
                Conversation.channel == "whatsapp",
                Conversation.account_id == "demo-studio",
                Conversation.external_contact == "demo-ines",
            )
        ).one()
    inquiry = crm.create_lead(
        crm.LeadInput(customer_id=prospect, service="Retrato familiar", channel="WhatsApp"), db
    )
    crm.create_quote(inquiry["id"], crm.QuoteInput(package_id=portrait), db)


if __name__ == "__main__":
    lab_url = "postgresql+psycopg://jordy_app@db:5432/jordy"
    if os.environ.get("DATABASE_URL") != lab_url:
        raise SystemExit("Ejecuta scripts/seed-demo.ps1 en el proyecto de pruebas jordy-lab.")
    engine = build_engine(lab_url)
    try:
        created = seed(engine, ZoneInfo(os.environ.get("STUDIO_TIMEZONE", "America/Mexico_City")))
        print("Datos Demo cargados." if created else "Los datos Demo ya estaban cargados.")
    finally:
        engine.dispose()
