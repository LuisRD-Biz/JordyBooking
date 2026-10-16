from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from jordy import services
from jordy.domain import Conflict
from jordy.integrations import FakeCalendar
from jordy.models import Booking, Occupancy, Outbox
from jordy.worker import process_batch

START = (datetime.now(UTC) + timedelta(days=100)).replace(
    hour=16, minute=0, second=0, microsecond=0
)


def setup(client, kind="session", buffer=30):
    # Each test has a distinct capability so independently created resources cannot mask conflicts.
    role = "photo_" + uuid4().hex
    resource = client.post(
        "/api/resources",
        json={
            "name": "Jordy",
            "kind": "staff",
            "capabilities": [role],
        },
    ).json()["id"]
    customer = client.post(
        "/api/customers",
        json={
            "name": "Cliente de prueba",
            "contact": f"synthetic-{uuid4().hex}@example.invalid",
        },
    ).json()["id"]
    package_data = {
        "name": "Sesión",
        "kind": kind,
        "price": "1500.00",
        "duration_minutes": 90,
        "buffer_minutes": buffer,
        "requirements": [{"capability": role, "quantity": 1}],
    }
    package = client.post("/api/packages", json=package_data).json()["id"]
    data = {"customer_id": customer, "package_id": package, "starts_at": START.isoformat()}
    return resource, package_data, data


def request_booking(client, data, key=None):
    response = client.post(
        "/api/bookings", json=data, headers={"Idempotency-Key": key or str(uuid4())}
    )
    assert response.status_code == 201, response.text
    return response.json()


def approve(client, identity):
    return client.post(f"/api/bookings/{identity}/approve", json={"location": "Estudio"})


def test_auth_required(client):
    for path in ["/api/bookings", "/api/customers", "/api/resources", "/api/operations"]:
        response = client.get(path, headers={"X-Admin-Key": "wrong"})
        assert response.status_code == 401


def test_pending_does_not_block_and_only_confirmation_consumes_capacity(client):
    _, _, data = setup(client)
    first, second = request_booking(client, data), request_booking(client, data)
    assert first["status"] == "pending_approval"
    assert approve(client, first["id"]).status_code == 200
    assert approve(client, second["id"]).status_code == 409
    assert client.post(f"/api/bookings/{first['id']}/cancel").status_code == 200
    assert approve(client, second["id"]).status_code == 200
    assert approve(client, first["id"]).status_code == 409


def test_event_needs_signed_contract(client):
    _, _, data = setup(client, "event")
    booking = request_booking(client, data)
    assert approve(client, booking["id"]).status_code == 422
    response = client.post(
        f"/api/bookings/{booking['id']}/contract",
        json={
            "reference": "Contrato físico de prueba 001",
            "signed_at": (datetime.now(UTC) - timedelta(minutes=1)).isoformat(),
        },
    )
    assert response.status_code == 201
    assert approve(client, booking["id"]).status_code == 200


def test_snapshot_and_idempotency(client):
    _, package_data, data = setup(client)
    key = str(uuid4())
    first = request_booking(client, data, key)
    assert request_booking(client, data, key)["id"] == first["id"]
    changed = {**data, "location": "Otra"}
    assert (
        client.post("/api/bookings", json=changed, headers={"Idempotency-Key": key}).status_code
        == 409
    )
    package_data["price"] = "9000.00"
    package_data["duration_minutes"] = 180
    assert client.put(f"/api/packages/{data['package_id']}", json=package_data).status_code == 200
    saved = client.get(f"/api/bookings/{first['id']}").json()
    assert saved["snapshot"]["price"] == "1500.00"
    assert saved["snapshot"]["duration_minutes"] == 90


def test_christmas_90_minutes_plus_30_allows_next_two_hour_slot(client):
    _, _, data = setup(client)
    first = request_booking(client, data)
    assert approve(client, first["id"]).status_code == 200
    for minutes, expected in [(90, False), (119, False), (120, True)]:
        result = client.post(
            "/api/availability",
            json={
                "package_id": data["package_id"],
                "starts_at": (START + timedelta(minutes=minutes)).isoformat(),
            },
        )
        assert result.json()["available"] is expected


def test_blocks_and_failed_reschedule_preserve_original(client):
    resource, _, data = setup(client)
    first = request_booking(client, data)
    assert approve(client, first["id"]).status_code == 200
    target = START + timedelta(days=1)
    block = client.post(
        "/api/blocks",
        json={
            "resource_id": resource,
            "starts_at": target.isoformat(),
            "ends_at": (target + timedelta(hours=3)).isoformat(),
            "reason": "Personal",
        },
    )
    assert block.status_code == 201
    response = client.post(
        f"/api/bookings/{first['id']}/reschedule",
        json={
            "starts_at": target.isoformat(),
            "location": "Estudio",
        },
    )
    assert response.status_code == 409
    saved = client.get(f"/api/bookings/{first['id']}").json()
    assert datetime.fromisoformat(saved["starts_at"]) == START
    assert len(client.get(f"/api/bookings/{first['id']}/assignments").json()) == 1
    assert client.post(f"/api/blocks/{block.json()['id']}/release").status_code == 200
    assert (
        client.post(
            f"/api/bookings/{first['id']}/reschedule",
            json={
                "starts_at": target.isoformat(),
                "location": "Estudio",
            },
        ).status_code
        == 200
    )


def test_simultaneous_confirmations_have_one_winner(client, database):
    _, _, data = setup(client)
    identities = [request_booking(client, data)["id"] for _ in range(2)]
    barrier = Barrier(2)

    def attempt(identity):
        with Session(database) as session:
            barrier.wait(timeout=10)
            try:
                with session.begin():
                    services.approve(session, identity, "Estudio")
                return "confirmed"
            except Conflict:
                return "conflict"

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(attempt, identities)) == ["confirmed", "conflict"]
    with Session(database) as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(Occupancy)
                .where(Occupancy.booking_id.in_(identities), Occupancy.active.is_(True))
            )
            == 1
        )
        assert (
            session.scalar(
                select(func.count())
                .select_from(Booking)
                .where(Booking.id.in_(identities), Booking.status == "pending_approval")
            )
            == 1
        )


def test_database_itself_rejects_overlap(client, database):
    resource, _, _ = setup(client)
    with Session(database) as session, session.begin():
        session.add(
            Occupancy(
                resource_id=resource,
                starts_at=START,
                ends_at=START + timedelta(hours=1),
                reason="Test",
            )
        )
    with pytest.raises(IntegrityError):
        with Session(database) as session, session.begin():
            session.add(
                Occupancy(
                    resource_id=resource,
                    starts_at=START,
                    ends_at=START + timedelta(hours=1),
                    reason="Overlap",
                )
            )


def test_validation_timezone_location_and_future_signature(client):
    _, _, data = setup(client, "event")
    response = client.post(
        "/api/bookings",
        json={**data, "starts_at": "2030-01-01T10:00:00"},
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert response.status_code == 422
    booking = request_booking(client, data)
    assert (
        client.post(f"/api/bookings/{booking['id']}/approve", json={"location": "  "}).status_code
        == 422
    )
    assert (
        client.post(
            f"/api/bookings/{booking['id']}/contract",
            json={
                "reference": "Test",
                "signed_at": START.isoformat(),
            },
        ).status_code
        == 422
    )
    assert client.post(f"/api/bookings/{booking['id']}/complete").status_code == 409


def test_worker_retries_and_simulation_is_explicit(database):
    class FailingCalendar:
        def apply_booking_change(self, payload, idempotency_key):
            raise RuntimeError("sensitive information must not be logged")

    with Session(database) as session, session.begin():
        # Isolate this row from events generated by other integration tests.
        row = Outbox(
            event_key=str(uuid4()),
            payload={"booking_id": 1},
            available_at=datetime.now(UTC) - timedelta(days=1),
        )
        session.add(row)
        session.flush()
        identity = row.id
        process_batch(session, FailingCalendar(), limit=10000)
    with Session(database) as session, session.begin():
        row = session.get(Outbox, identity)
        assert row.status == "pending" and row.attempts == 1
        assert row.last_error == "provider_error"
        row.available_at = datetime.now(UTC) - timedelta(seconds=1)
    fake = FakeCalendar()
    with Session(database) as session, session.begin():
        process_batch(session, fake, limit=10000)
    with Session(database) as session:
        assert session.get(Outbox, identity).status == "simulated"


def test_shared_equipment_limits_two_photographers(client):
    _, package_data, data = setup(client)
    role = package_data["requirements"][0]["capability"]
    client.post(
        "/api/resources",
        json={
            "name": "Segundo fotógrafo",
            "kind": "staff",
            "capabilities": [role],
        },
    )
    equipment_role = "set_" + uuid4().hex
    client.post(
        "/api/resources",
        json={
            "name": "Set navideño único",
            "kind": "equipment",
            "capabilities": [equipment_role],
        },
    )
    package_data["requirements"].append({"capability": equipment_role, "quantity": 1})
    assert client.put(f"/api/packages/{data['package_id']}", json=package_data).status_code == 200
    first, second = request_booking(client, data), request_booking(client, data)
    assert approve(client, first["id"]).status_code == 200
    assert approve(client, second["id"]).status_code == 409


def test_concurrent_idempotent_creation(client, database):
    from jordy.schemas import BookingInput

    _, _, data = setup(client)
    key = str(uuid4())
    barrier = Barrier(2)

    def attempt(_):
        with Session(database) as session, session.begin():
            barrier.wait(timeout=10)
            return services.create_booking(session, BookingInput(**data), key).id

    with ThreadPoolExecutor(max_workers=2) as executor:
        identities = list(executor.map(attempt, range(2)))
    assert identities[0] == identities[1]


def test_christmas_slots_endpoint(client):
    _, _, data = setup(client)
    result = client.get(
        "/api/availability/christmas-slots",
        params={
            "day": "2030-10-01",
            "package_id": data["package_id"],
        },
    )
    assert result.status_code == 200
    assert len(result.json()["slots"]) == 6
    assert result.json()["holds_enabled"] is False
    last = result.json()["slots"][-1]
    assert datetime.fromisoformat(last["starts_at"]).hour == 20
    assert datetime.fromisoformat(last["session_ends_at"]).minute == 30
    assert datetime.fromisoformat(last["resource_free_at"]).hour == 22
