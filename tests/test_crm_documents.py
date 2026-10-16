import hashlib
import io
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from pypdf import PdfWriter
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from test_api import START, approve, request_booking, setup

from jordy.config import settings
from jordy.main import app
from jordy.models import Booking, Customer, Occupancy


@pytest.mark.parametrize(
    "zone,day,hours",
    [
        ("America/Mexico_City", "2035-03-11", 24),
        ("America/New_York", "2035-03-11", 23),
        ("America/New_York", "2035-11-04", 25),
    ],
)
def test_local_day_boundaries_follow_configured_timezone(monkeypatch, zone, day, hours):
    from jordy import search

    monkeypatch.setattr(search, "settings", lambda: SimpleNamespace(studio_timezone=zone))
    lower, upper = search.date_bounds(search.Filters(day=day))
    assert (upper - lower).total_seconds() == hours * 3600


def pdf_bytes():
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


@pytest.fixture
def private_files(client, monkeypatch, tmp_path):
    monkeypatch.setattr(settings(), "document_root", tmp_path / "documents")
    return settings().document_root


def upload(client, identity, body=None, **params):
    return client.post(
        f"/api/bookings/{identity}/documents",
        params={"filename": "Contrato.pdf", **params},
        content=body if body is not None else pdf_bytes(),
        headers={"Content-Type": "application/octet-stream"},
    )


def test_pdf_metadata_download_persistence_and_no_implicit_signature(client, private_files):
    _, _, data = setup(client, "event")
    booking = request_booking(client, data)
    content = pdf_bytes()
    response = upload(client, booking["id"], content, notes="Original firmado")
    assert response.status_code == 201, response.text
    doc = response.json()
    assert doc["sha256"] == hashlib.sha256(content).hexdigest()
    assert doc["size"] == len(content) and doc["mime"] == "application/pdf"
    assert doc["actor"] == "jordy-admin" and doc["version"] == 1
    assert "storage_key" not in doc
    assert client.get(f"/api/documents/{doc['id']}/download").content == content
    assert client.get(f"/api/bookings/{booking['id']}/contract").json() is None
    assert approve(client, booking["id"]).status_code == 422
    # Fresh application client/connection still retrieves the original bytes from disk.
    with TestClient(
        app, headers={"X-Admin-Key": settings().admin_api_key.get_secret_value()}
    ) as fresh:
        assert fresh.get(f"/api/documents/{doc['id']}/download").content == content
    anonymous = client.get(f"/api/documents/{doc['id']}/download", headers={"X-Admin-Key": "wrong"})
    assert anonymous.status_code == 401
    assert client.get(f"/api/documents/{doc['id']}/preview").status_code == 422
    assert len(list(private_files.glob("*.bin"))) == 1


@pytest.mark.parametrize(
    "filename,body",
    [
        ("virus.exe", b"MZ..."),
        ("fake.pdf", b"%PDF-1.4\nnot a PDF"),
        ("fake.jpg", b"not jpeg"),
        ("../escape.pdf", b"bad"),
        ("a\\b.pdf", b"bad"),
    ],
)
def test_reject_invalid_uploads_and_cleanup(client, private_files, filename, body):
    _, _, data = setup(client)
    b = request_booking(client, data)
    assert upload(client, b["id"], body, filename=filename).status_code == 422
    assert not list(private_files.glob("*"))


def test_size_limit_and_nonexistent_booking_leave_no_file(client, private_files, monkeypatch):
    monkeypatch.setattr(settings(), "document_max_bytes", 1024)
    assert upload(client, 2147483647, b"x" * 1025).status_code == 413
    assert upload(client, 2147483647).status_code == 404
    assert not list(private_files.glob("*"))


def test_images_versions_and_explicit_contract_association(client, private_files):
    _, _, data = setup(client, "event")
    b = request_booking(client, data)
    first = upload(client, b["id"]).json()
    second = upload(client, b["id"], replaces=first["id"]).json()
    listing = client.get(f"/api/bookings/{b['id']}/documents").json()
    assert listing["total"] == 2
    assert second["version"] == 2 and second["group_id"] == first["group_id"]
    assert len(list(private_files.glob("*.bin"))) == 2
    assert upload(client, b["id"], replaces=first["id"]).status_code == 409
    image = io.BytesIO()
    Image.new("RGB", (20, 20), "white").save(image, format="PNG")
    doc = upload(
        client, b["id"], image.getvalue(), filename="anticipo.png", document_type="deposit"
    ).json()
    assert client.get(f"/api/documents/{doc['id']}/preview").headers["content-type"] == "image/png"
    payload = {
        "reference": "Signed 001",
        "signed_at": datetime.now(UTC).isoformat(),
        "document_id": doc["id"],
    }
    assert client.post(f"/api/bookings/{b['id']}/contract", json=payload).status_code == 422
    payload["document_id"] = second["id"]
    assert client.post(f"/api/bookings/{b['id']}/contract", json=payload).status_code == 201
    assert approve(client, b["id"]).status_code == 200
    prior = client.get(f"/api/bookings/{b['id']}/contract").json()
    assert (
        client.post(
            f"/api/bookings/{b['id']}/contract/document", json={"document_id": first["id"]}
        ).status_code
        == 200
    )
    linked = client.get(f"/api/bookings/{b['id']}/contract").json()
    assert linked["reference"] == prior["reference"] and linked["signed_at"] == prior["signed_at"]
    assert linked["document_id"] == first["id"]
    assert (
        client.post(
            f"/api/bookings/{b['id']}/contract/document", json={"document_id": doc["id"]}
        ).status_code
        == 422
    )


def test_inline_customer_atomic_idempotent_and_duplicate_warning(client, database):
    _, _, base = setup(client)
    phone = str(1000000000 + int(uuid4().hex[:7], 16))
    data = {
        "package_id": base["package_id"],
        "starts_at": base["starts_at"],
        "new_customer": {"name": "Ocasional", "phone": phone},
    }
    key = str(uuid4())
    first = request_booking(client, data, key)
    assert request_booking(client, data, key)["customer_id"] == first["customer_id"]
    duplicate = client.post("/api/bookings", json=data, headers={"Idempotency-Key": str(uuid4())})
    assert duplicate.status_code == 409
    with Session(database) as session:
        assert (
            session.scalar(
                select(func.count()).select_from(Customer).where(Customer.phone == phone)
            )
            == 1
        )
    assert client.get("/api/search/customers", params={"q": phone}).json()["total"] == 1
    assert (
        client.get("/api/search/contact-matches", params={"phone": phone}).json()[0]["id"]
        == first["customer_id"]
    )
    data["new_customer"]["duplicate_ack"] = True
    assert request_booking(client, data)["customer_id"] != first["customer_id"]
    bad = {
        **data,
        "package_id": 2147483647,
        "new_customer": {"name": "Rollback", "phone": "123456789765"},
    }
    assert (
        client.post(
            "/api/bookings", json=bad, headers={"Idempotency-Key": str(uuid4())}
        ).status_code
        == 404
    )
    assert client.get("/api/search/customers", params={"q": "123456789765"}).json()["total"] == 0


def test_legacy_contact_is_in_duplicate_warnings_without_rewriting_it(client, database):
    phone = "554" + str(int(uuid4().hex[:7], 16))
    with Session(database) as session:
        customer = Customer(name="Contacto anterior", contact="+" + phone, normalized_phone=None)
        session.add(customer)
        session.commit()
        identity = customer.id
    matches = client.get("/api/search/contact-matches", params={"phone": phone}).json()
    assert any(c["id"] == identity for c in matches)
    assert (
        client.post("/api/customers", json={"name": "Mismo contacto", "phone": phone}).status_code
        == 409
    )
    with Session(database) as session:
        assert session.get(Customer, identity).contact == "+" + phone


def test_date_filters_timezone_order_pagination(client):
    _, _, data = setup(client)
    dates = [
        "2035-11-15T05:59:59Z",
        "2035-11-15T06:00:00Z",
        "2035-11-16T05:59:59Z",
        "2035-11-16T06:00:00Z",
    ]
    ids = [request_booking(client, {**data, "starts_at": date})["id"] for date in dates]
    params = {"customer_id": data["customer_id"], "day": "2035-11-15", "page_size": 1}
    first = client.get("/api/search/bookings", params=params).json()
    second = client.get("/api/search/bookings", params={**params, "page": 2}).json()
    assert first["total"] == 2
    assert [first["items"][0]["id"], second["items"][0]["id"]] == ids[1:3]
    reverse = client.get("/api/search/bookings", params={**params, "order": "desc"}).json()
    assert reverse["items"][0]["id"] == ids[2]
    for filters in [
        {"date_from": "2035-11-14", "date_to": "2035-11-16"},
        {"month": 11, "year": 2035},
    ]:
        assert (
            client.get(
                "/api/search/bookings", params={"customer_id": data["customer_id"], **filters}
            ).json()["total"]
            == 4
        )
    assert (
        client.get("/api/search/bookings", params={**params, "status": "confirmed"}).json()["total"]
        == 0
    )
    assert (
        client.get(
            "/api/search/bookings", params={"date_from": "2035-12-01", "date_to": "2035-11-01"}
        ).status_code
        == 422
    )
    assert client.get("/api/search/bookings", params={"month": 13, "year": 2035}).status_code == 422


def test_lead_quote_versions_booking_and_approval(client, database):
    _, package, data = setup(client)
    lead = client.post(
        "/api/leads",
        json={
            "customer_id": data["customer_id"],
            "service": "Sesión familiar",
            "channel": "Instagram",
            "requested_date": START.isoformat(),
        },
    ).json()
    with Session(database) as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(Booking)
                .where(Booking.customer_id == data["customer_id"])
            )
            == 0
        )
        assert (
            session.scalar(
                select(func.count())
                .select_from(Occupancy)
                .where(
                    Occupancy.booking_id.in_(
                        select(Booking.id).where(Booking.customer_id == data["customer_id"])
                    )
                )
            )
            == 0
        )
    quote = client.post(
        f"/api/leads/{lead['id']}/quotes", json={"package_id": data["package_id"]}
    ).json()
    package["price"] = "1900.00"
    client.put(f"/api/packages/{data['package_id']}", json=package)
    second = client.post(
        f"/api/leads/{lead['id']}/quotes", json={"package_id": data["package_id"]}
    ).json()
    assert second["version"] == 2 and quote["snapshot"]["price"] == "1500.00"
    booking = request_booking(client, {**data, "quote_id": quote["id"]})
    assert booking["snapshot"]["price"] == "1500.00"
    assert approve(client, booking["id"]).status_code == 200
    history = client.get(f"/api/leads/{lead['id']}/history").json()
    assert history["lead"]["status"] == "won" and len(history["quotes"]) == 2
    assert len(history["bookings"]) == 1
    assert client.get("/api/search/leads", params={"q": "Sesión familiar"}).status_code == 200
    customer = client.get("/api/search/customers", params={"classification": "client"}).json()
    assert any(
        c["id"] == data["customer_id"] and c["contracts_count"] == 1 for c in customer["items"]
    )
    assert (
        client.post(f"/api/leads/{lead['id']}/status", json={"status": "reopen"}).status_code == 409
    )
    assert client.post(f"/api/bookings/{booking['id']}/cancel").status_code == 200
    assert (
        client.post(f"/api/leads/{lead['id']}/status", json={"status": "reopen"}).status_code == 200
    )
    third = client.post(f"/api/leads/{lead['id']}/quotes", json={"package_id": data["package_id"]})
    assert third.status_code == 201 and third.json()["version"] == 3


def test_appointments_filter_and_customer_integrity(client):
    _, _, data = setup(client, "event")
    booking = request_booking(client, data)
    start = START + timedelta(days=1)
    payload = {
        "customer_id": data["customer_id"],
        "booking_id": booking["id"],
        "kind": "contract",
        "starts_at": start.isoformat(),
        "ends_at": (start + timedelta(hours=1)).isoformat(),
        "location": "Estudio",
    }
    response = client.post("/api/appointments", json=payload)
    assert response.status_code == 201, response.text
    assert (
        client.get("/api/search/appointments", params={"day": start.date().isoformat()}).json()[
            "total"
        ]
        >= 1
    )
    assert (
        client.post(
            f"/api/appointments/{response.json()['id']}/status", json={"status": "completed"}
        ).status_code
        == 422
    )
    assert (
        client.post(
            f"/api/appointments/{response.json()['id']}/status", json={"status": "cancelled"}
        ).status_code
        == 200
    )
    assert client.get("/api/dashboard").status_code == 200


def test_upcoming_search_includes_ongoing_service_from_previous_day(client, database):
    _, _, data = setup(client)
    booking = request_booking(client, data)
    assert approve(client, booking["id"]).status_code == 200
    with Session(database) as session:
        row = session.get(Booking, booking["id"])
        row.starts_at = datetime.now(UTC) - timedelta(days=1)
        row.ends_at = datetime.now(UTC) + timedelta(hours=1)
        session.commit()
    params = {"customer_id": data["customer_id"], "status": "confirmed", "upcoming": True}
    assert client.get("/api/search/bookings", params=params).json()["total"] == 1
    with Session(database) as session:
        session.get(Booking, booking["id"]).ends_at = datetime.now(UTC) - timedelta(hours=1)
        session.commit()
    assert client.get("/api/search/bookings", params=params).json()["total"] == 0
