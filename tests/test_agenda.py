from datetime import date, datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy.orm import Session

from jordy import accounts
from jordy.agenda import MAX_DAYS
from jordy.config import settings

ORIGIN = "http://127.0.0.1:8000"
PASSWORD = "luz-de-tarde-en-el-jardin-2026"
ZONE = ZoneInfo("America/Mexico_City")
DAY = date(2093, 3, 10) + timedelta(days=uuid4().int % 2000)


def local(day, hour, minute=0):
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=ZONE)


def fetch(client, start, end, **params):
    query = {"from": start.isoformat(), "to": end.isoformat(), **params}
    return client.get("/api/agenda", params=query)


@pytest.fixture
def studio(client):
    role = "photo_" + uuid4().hex
    resource = client.post(
        "/api/resources",
        json={"name": "Recurso sintético", "kind": "staff", "capabilities": [role]},
    ).json()["id"]
    customer = client.post(
        "/api/customers",
        json={"name": "Cliente Agenda", "contact": f"agenda-{uuid4().hex}@example.invalid"},
    ).json()["id"]
    package = client.post(
        "/api/packages",
        json={
            "name": "Sesión agenda",
            "kind": "session",
            "price": "1500.00",
            "duration_minutes": 60,
            "requirements": [{"capability": role, "quantity": 1}],
        },
    ).json()["id"]

    def book(start):
        response = client.post(
            "/api/bookings",
            json={"customer_id": customer, "package_id": package, "starts_at": start.isoformat()},
            headers={"Idempotency-Key": str(uuid4())},
        )
        assert response.status_code == 201, response.text
        return response.json()["id"]

    return {"resource": resource, "customer": customer, "book": book}


def mine(response, ids):
    assert response.status_code == 200, response.text
    return [item for item in response.json() if (item["type"], item["id"]) in ids]


def test_normalized_items_of_every_type_ordered_by_start(client, studio):
    confirmed = studio["book"](local(DAY, 16))
    approved = client.post(f"/api/bookings/{confirmed}/approve", json={"location": "Estudio"})
    assert approved.status_code == 200
    pending = studio["book"](local(DAY, 9))
    appointment = client.post(
        "/api/appointments",
        json={
            "customer_id": studio["customer"],
            "booking_id": pending,
            "kind": "contract",
            "starts_at": local(DAY, 12).isoformat(),
            "ends_at": local(DAY, 13).isoformat(),
            "location": "Oficina",
        },
    ).json()["id"]
    block = client.post(
        "/api/blocks",
        json={
            "resource_id": studio["resource"],
            "starts_at": local(DAY, 19).isoformat(),
            "ends_at": local(DAY + timedelta(days=2), 8).isoformat(),
            "reason": "Viaje",
        },
    ).json()["id"]
    ids = {
        ("booking", confirmed),
        ("booking", pending),
        ("appointment", appointment),
        ("block", block),
    }

    items = mine(fetch(client, DAY, DAY), ids)
    assert [(item["type"], item["id"]) for item in items] == [
        ("booking", pending),
        ("appointment", appointment),
        ("booking", confirmed),
        ("block", block),
    ]
    first, signing, second, blocked = items
    assert first == {
        "type": "booking",
        "id": pending,
        "starts_at": first["starts_at"],
        "ends_at": first["ends_at"],
        "title": "Cliente Agenda",
        "subtitle": "Sesión agenda",
        "status": "pending_approval",
        "kind": "session",
        "customer_id": studio["customer"],
        "booking_id": pending,
        "resource_id": None,
        "location": None,
    }
    assert datetime.fromisoformat(first["starts_at"]) == local(DAY, 9)
    assert (second["status"], second["location"]) == ("confirmed", "Estudio")
    assert (signing["kind"], signing["subtitle"], signing["status"]) == (
        "contract",
        "Firma de contrato",
        "scheduled",
    )
    assert signing["booking_id"] == pending and signing["location"] == "Oficina"
    assert (blocked["title"], blocked["subtitle"], blocked["kind"], blocked["customer_id"]) == (
        "Recurso sintético",
        "Viaje",
        "staff",
        None,
    )
    assert blocked["resource_id"] == studio["resource"]

    following = mine(fetch(client, DAY + timedelta(days=1), DAY + timedelta(days=1)), ids)
    assert [(item["type"], item["id"]) for item in following] == [("block", block)]
    assert client.post(f"/api/blocks/{block}/release").status_code == 200
    assert ("block", block) not in {(i["type"], i["id"]) for i in fetch(client, DAY, DAY).json()}


def test_days_are_local_to_the_studio_and_cancelled_is_opt_in(client, studio):
    day = DAY + timedelta(days=5)
    late = studio["book"](local(day, 23, 30))
    early = studio["book"](local(day + timedelta(days=1), 0, 45))
    cancelled = studio["book"](local(day, 11))
    assert client.post(f"/api/bookings/{cancelled}/cancel").status_code == 200
    ids = {("booking", late), ("booking", early), ("booking", cancelled)}

    assert [item["id"] for item in mine(fetch(client, day, day), ids)] == [late]
    next_day = mine(fetch(client, day + timedelta(days=1), day + timedelta(days=1)), ids)
    assert [item["id"] for item in next_day] == [late, early]
    everything = mine(fetch(client, day, day, include_cancelled="true"), ids)
    assert [(item["id"], item["status"]) for item in everything] == [
        (cancelled, "cancelled"),
        (late, "pending_approval"),
    ]


def test_range_is_validated(client):
    assert fetch(client, DAY, DAY + timedelta(days=MAX_DAYS - 1)).status_code == 200
    too_long = fetch(client, DAY, DAY + timedelta(days=MAX_DAYS))
    assert too_long.status_code == 422 and str(MAX_DAYS) in too_long.json()["detail"]
    assert fetch(client, DAY, DAY - timedelta(days=1)).status_code == 422
    assert fetch(client, date(9999, 12, 1), date(9999, 12, 31)).status_code == 422
    assert client.get("/api/agenda", params={"from": "2093-03-10"}).status_code == 422
    assert (
        client.get("/api/agenda", params={"from": "mañana", "to": "2093-03-10"}).status_code == 422
    )


def test_requires_an_administrator(client, database, monkeypatch):
    client.headers.pop("X-Admin-Key")
    assert fetch(client, DAY, DAY).status_code == 401
    monkeypatch.setattr(settings(), "client_ip_header", "X-Test-Client-IP")
    client.headers.update({"X-Test-Client-IP": "198.51.100.201", "Origin": ORIGIN})
    for role, expected in (("employee", 403), ("admin", 200)):
        email = f"agenda-{uuid4().hex[:10]}@example.invalid"
        with Session(database) as session, session.begin():
            accounts.create_user(session, email, "Synthetic User", PASSWORD, role)
        login = client.post("/auth/login", json={"email": email, "password": PASSWORD})
        assert login.status_code == 200
        assert fetch(client, DAY, DAY).status_code == expected
        assert client.post("/auth/logout").status_code == 200
