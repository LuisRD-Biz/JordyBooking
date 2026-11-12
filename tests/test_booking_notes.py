"""Booking notes, the booking summary, place edits and the real actor in the audit trail."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from jordy import accounts
from jordy.config import settings
from jordy.models import AuditLog
from jordy.notes import BODY_MAX, LOCAL_AUTHOR, BookingNote

ORIGIN = "http://127.0.0.1:8000"
PASSWORD = "luz-de-tarde-en-el-jardin-2026"
START = (datetime.now(UTC) + timedelta(days=200)).replace(minute=0, second=0, microsecond=0)


def make_booking(client, start=START):
    role = "photo_" + uuid4().hex
    client.post("/api/resources", json={"name": "Foto", "kind": "staff", "capabilities": [role]})
    customer = client.post(
        "/api/customers",
        json={
            "name": "Cliente Notas",
            "phone": f"555{uuid4().int % 10**7:07d}",
            "email": f"notas-{uuid4().hex[:8]}@example.invalid",
        },
    ).json()["id"]
    package = client.post(
        "/api/packages",
        json={
            "name": "Sesión notas",
            "kind": "session",
            "price": "900.00",
            "duration_minutes": 60,
            "requirements": [{"capability": role, "quantity": 1}],
        },
    ).json()["id"]
    response = client.post(
        "/api/bookings",
        json={"customer_id": customer, "package_id": package, "starts_at": start.isoformat()},
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def sign_in(client, database, monkeypatch, role="admin", name="Ana Synthetic"):
    """Switch the client from the admin key to a cookie session of a new account."""
    client.headers.pop("X-Admin-Key", None)
    monkeypatch.setattr(settings(), "client_ip_header", "X-Test-Client-IP")
    client.headers["X-Test-Client-IP"] = f"198.51.100.{uuid4().int % 250 + 1}"
    client.headers["Origin"] = ORIGIN
    email = f"notes-{uuid4().hex[:10]}@example.invalid"
    with Session(database) as session, session.begin():
        accounts.create_user(session, email, name, PASSWORD, role)
    assert (
        client.post("/auth/login", json={"email": email, "password": PASSWORD}).status_code == 200
    )
    return email


def last_audit(database, action, entity_id):
    with Session(database) as session:
        return session.scalars(
            select(AuditLog)
            .where(AuditLog.action == action, AuditLog.entity_id == entity_id)
            .order_by(AuditLog.id.desc())
        ).first()


def test_create_and_list_notes_signed_by_the_account(client, database, monkeypatch):
    booking = make_booking(client)
    path = f"/api/bookings/{booking}/notes"
    assert client.get(path).json() == []
    keyed = client.post(path, json={"body": "  Prefiere fotos al atardecer.  "})
    assert keyed.status_code == 201
    assert keyed.json()["body"] == "Prefiere fotos al atardecer."
    assert (keyed.json()["author_user_id"], keyed.json()["author_name"]) == (None, LOCAL_AUTHOR)
    assert last_audit(database, "booking.note_added", booking).actor == "jordy-admin"

    email = sign_in(client, database, monkeypatch)
    second = client.post(path, json={"body": "Confirmó el anticipo."})
    assert second.status_code == 201
    note = second.json()
    assert note["author_name"] == "Ana Synthetic" and note["author_user_id"] is not None
    assert note["booking_id"] == booking and note["created_at"]
    assert last_audit(database, "booking.note_added", booking).actor == email

    listed = client.get(path).json()
    assert [n["body"] for n in listed] == ["Prefiere fotos al atardecer.", "Confirmó el anticipo."]
    assert [n["author_name"] for n in listed] == [LOCAL_AUTHOR, "Ana Synthetic"]
    # Append-only: there is no way to edit or delete a note through the API.
    for method in ("put", "patch", "delete"):
        assert getattr(client, method)(f"{path}/{note['id']}").status_code in {404, 405}


def test_notes_are_validated(client):
    booking = make_booking(client)
    path = f"/api/bookings/{booking}/notes"
    assert client.post(path, json={"body": "   "}).status_code == 422
    assert client.post(path, json={}).status_code == 422
    assert client.post(path, json={"body": "x" * (BODY_MAX + 1)}).status_code == 422
    assert client.post(path, json={"body": "ok", "author_user_id": 1}).status_code == 422
    assert client.post(path, json={"body": "x" * BODY_MAX}).status_code == 201
    assert client.post("/api/bookings/999999999/notes", json={"body": "nada"}).status_code == 404
    assert client.get("/api/bookings/999999999/notes").status_code == 404


def test_retry_with_the_same_key_writes_one_note(client):
    booking, other = make_booking(client), make_booking(client)
    path, key = f"/api/bookings/{booking}/notes", {"Idempotency-Key": str(uuid4())}
    first = client.post(path, json={"body": "Una sola vez."}, headers=key)
    again = client.post(path, json={"body": "Una sola vez."}, headers=key)
    assert (first.status_code, again.status_code) == (201, 200)
    assert first.json()["id"] == again.json()["id"]
    stamps = [datetime.fromisoformat(r.json()["created_at"]) for r in (first, again)]
    assert stamps[0] == stamps[1]  # same instant, whatever offset it is rendered in
    assert len(client.get(path).json()) == 1
    assert client.post(path, json={"body": "Otro texto."}, headers=key).status_code == 409
    wrong_booking = client.post(
        f"/api/bookings/{other}/notes", json={"body": "Una sola vez."}, headers=key
    )
    assert wrong_booking.status_code == 409
    assert (
        client.post(path, json={"body": "x"}, headers={"Idempotency-Key": "no"}).status_code == 422
    )


def test_notes_require_session_admin_role_and_same_origin(client, database, monkeypatch):
    booking = make_booking(client)
    path = f"/api/bookings/{booking}/notes"
    client.headers.pop("X-Admin-Key")
    assert client.get(path).status_code == 401
    assert client.post(path, json={"body": "sin sesión"}).status_code == 401

    sign_in(client, database, monkeypatch, role="employee")
    assert client.get(path).status_code == 403
    assert client.post(path, json={"body": "sin permiso"}).status_code == 403
    assert client.post("/auth/logout").status_code == 200

    sign_in(client, database, monkeypatch)
    for origin in ("", "https://evil.invalid"):
        refused = client.post(path, json={"body": "otro origen"}, headers={"Origin": origin})
        assert refused.status_code == 403
    assert client.get(path, headers={"Origin": ""}).status_code == 200  # reads are not CSRF-prone
    assert client.get(path).json() == []
    assert client.post(path, json={"body": "mismo origen"}).status_code == 201


def test_database_rejects_empty_notes(client, database):
    booking = make_booking(client)
    with Session(database) as session:
        session.add(BookingNote(booking_id=booking, body="", created_at=datetime.now(UTC)))
        with pytest.raises(IntegrityError):
            session.commit()


def test_place_can_change_without_rescheduling(client, database, monkeypatch):
    booking = make_booking(client)
    email = sign_in(client, database, monkeypatch)
    path = f"/api/bookings/{booking}/location"
    assert client.post(path, json={"location": ""}).status_code == 422
    changed = client.post(path, json={"location": "Jardín Botánico"})
    assert changed.status_code == 200
    assert changed.json()["location"] == "Jardín Botánico"
    assert datetime.fromisoformat(changed.json()["starts_at"]) == START
    audit = last_audit(database, "booking.location_changed", booking)
    assert audit.actor == email
    # Repeating the same value changes nothing and is not logged again.
    assert client.post(path, json={"location": "Jardín Botánico"}).status_code == 200
    assert last_audit(database, "booking.location_changed", booking).id == audit.id

    # Rescheduling without a place keeps the one already agreed.
    moved = client.post(
        f"/api/bookings/{booking}/reschedule",
        json={"starts_at": (START + timedelta(days=1)).isoformat()},
    )
    assert moved.status_code == 200 and moved.json()["location"] == "Jardín Botánico"
    assert last_audit(database, "booking.rescheduled", booking).actor == email

    assert client.post(f"/api/bookings/{booking}/cancel").status_code == 200
    assert client.post(path, json={"location": "Otro lugar"}).status_code == 409
    assert (
        client.post("/api/bookings/999999999/location", json={"location": "x"}).status_code == 404
    )


def test_summary_gathers_what_the_detail_view_needs(client):
    booking = make_booking(client)
    assert client.post(f"/api/bookings/{booking}/notes", json={"body": "Nota"}).status_code == 201
    assert (
        client.post(f"/api/bookings/{booking}/approve", json={"location": "Estudio"}).status_code
        == 200
    )
    summary = client.get(f"/api/bookings/{booking}/summary").json()
    assert summary["booking"]["id"] == booking and summary["booking"]["status"] == "confirmed"
    assert summary["customer"]["name"] == "Cliente Notas"
    assert summary["customer"]["phone"].startswith("555") and summary["customer"]["email"]
    assert summary["contract"] is None and summary["appointments"] == []
    assert [a["resource_name"] for a in summary["assignments"]] == ["Foto"]
    assert summary["counts"] == {"notes": 1, "documents": 0, "contract_documents": 0}
    assert client.get("/api/bookings/999999999/summary").status_code == 404
