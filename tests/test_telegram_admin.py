"""Telegram commands over a migrated, empty PostgreSQL schema. No network transport."""

import socket
from datetime import UTC, date, datetime, timedelta
from unittest.mock import Mock
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import event, text
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.orm import Session
from test_telegram import ALLOWED, UID, incoming

from jordy import services, telegram
from jordy.admin_queries import build_read_engine, read_session
from jordy.admin_reads import AdminInputError, AdminReads
from jordy.models import Booking, Customer, Message, Occupancy
from jordy.schemas import PackageInput, ResourceInput

ZONE = "America/Mexico_City"
NOW = datetime(2040, 1, 2, 2, tzinfo=UTC)  # Still Jan 1 in the studio.
MIDNIGHT = datetime(2040, 1, 1, tzinfo=ZoneInfo(ZONE))


@pytest.fixture
def reads(empty_database):
    return AdminReads(empty_database, ZONE, clock=lambda: NOW)


@pytest.fixture
def catalog(empty_database):
    with Session(empty_database) as session, session.begin():
        resource = services.create_resource(
            session, ResourceInput(name="Prueba", kind="staff", capabilities=["foto"])
        )
        package = services.save_package(
            session,
            PackageInput(
                name="Paquete de prueba",
                kind="session",
                price=50,
                duration_minutes=60,
                preparation_minutes=15,
                buffer_minutes=30,
                requirements=[{"capability": "foto", "quantity": 1}],
            ),
        )
        customer = Customer(name="Nombre privado", contact="contacto@example.invalid")
        session.add(customer)
        session.flush()
        return resource.id, package.id, customer.id


def add_booking(session, catalog, start, status="pending_approval", kind="session"):
    _, package_id, customer_id = catalog
    row = Booking(
        customer_id=customer_id,
        package_id=package_id,
        kind=kind,
        starts_at=start,
        ends_at=start + timedelta(hours=1),
        status=status,
        snapshot={},
        location="Ubicación privada",
    )
    session.add(row)
    session.flush()
    return row.id


def reply(command, reads):
    uid, body = telegram.reply_for(incoming(command), ALLOWED, reads)
    assert uid == UID
    return body


def test_calendar_overlap_week_and_local_midnight(reads, catalog, empty_database):
    with Session(empty_database) as session, session.begin():
        add_booking(session, catalog, MIDNIGHT - timedelta(hours=1))
        overnight = add_booking(
            session, catalog, MIDNIGHT - timedelta(minutes=30), "confirmed", "event"
        )
        tomorrow = add_booking(session, catalog, MIDNIGHT + timedelta(days=1))
        last = add_booking(session, catalog, MIDNIGHT + timedelta(days=6))
        add_booking(session, catalog, MIDNIGHT + timedelta(days=7))
    assert reads.agenda().start_day == date(2040, 1, 1)
    assert [row.id for row in reads.agenda().bookings] == [overnight]
    assert [row.id for row in reads.agenda("mañana").bookings] == [tomorrow]
    week = reads.agenda("semana")
    assert week.end_day == date(2040, 1, 7)
    assert [row.id for row in week.bookings] == [overnight, tomorrow, last]
    body = reply("/agenda 2040-01-01", reads)
    for detail in (f"#{overnight}", "23:30", "00:30", "Evento", "confirmada", ZONE):
        assert detail in body
    for private in ("Nombre privado", "contacto@example.invalid", "Ubicación privada"):
        assert private not in body


def test_empty_results_and_connection_recovery(empty_database, reads):
    def disconnect_once(*args):
        raise OperationalError("SELECT private-test", {}, Exception("synthetic-secret"))

    event.listen(empty_database, "before_cursor_execute", disconnect_once, once=True)
    failure = reply("/agenda", reads)
    assert "no está disponible" in failure
    assert "synthetic-secret" not in failure and "private-test" not in failure
    assert "Sin reservas" in reply("/agenda", reads)
    pending = reply("/pendientes", reads)
    assert "Sin solicitudes" in pending and "Sin seguimientos" in pending


def test_database_unreachable_hides_connection_details():
    # Reserve the address without listening. No operational server can own this port.
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        engine = build_read_engine(f"postgresql+psycopg://fake@127.0.0.1:{port}/fake_test")
        try:
            result = reply("/pendientes", AdminReads(engine, ZONE))
            assert "no está disponible" in result
            assert "127.0.0.1" not in result and "fake" not in result
        finally:
            engine.dispose()


@pytest.mark.parametrize(
    "command", ["/agenda", "/pendientes", "/disponibilidad 2040-01-02 10:00 1"]
)
def test_private_authorization_precedes_reads(command):
    reads = Mock(spec_set=AdminReads)
    for msg in (
        incoming(command, uid=55),
        incoming(command, chat={"id": UID, "type": "supergroup"}),
        incoming(command, chat={"id": 55, "type": "private"}),
        incoming(command, **{"from": {"id": UID, "is_bot": True}}),
    ):
        assert telegram.reply_for(msg, ALLOWED, reads) is None
    assert reads.method_calls == []


@pytest.mark.parametrize(
    ("command", "missing"),
    [
        ("/disponibilidad", "fecha"),
        ("/disponibilidad 2040-01-02", "hora"),
        ("/disponibilidad 2040-01-02 10:00", "ID del paquete"),
    ],
)
def test_availability_requests_missing_parameters(command, missing):
    reads = Mock(spec_set=AdminReads)
    assert missing in reply(command, reads)
    assert reads.method_calls == []


def test_availability_uses_capacity_and_preserves_bookings(reads, catalog, empty_database):
    resource_id, package_id, _ = catalog
    start = MIDNIGHT + timedelta(days=1, hours=10)
    with Session(empty_database) as session, session.begin():
        identity = add_booking(session, catalog, start)
    result = reads.availability("2040-01-02", "10:00", package_id)
    assert result.available and result.assignments == ((resource_id, "foto"),)
    assert "preliminar" in reply(f"/disponibilidad 2040-01-02 10:00 {package_id}", reads)
    with Session(empty_database) as session, session.begin():
        assert session.get(Booking, identity).status == "pending_approval"
        # Block starts 29 minutes after the nominal end; the package adds a 30 min buffer.
        session.add(
            Occupancy(
                resource_id=resource_id,
                reason="Bloqueo de prueba",
                starts_at=start + timedelta(minutes=89),
                ends_at=start + timedelta(minutes=105),
            )
        )
    assert not reads.availability("2040-01-02", "10:00", package_id).available
    assert not reads.availability("2040-01-02", "11:59", package_id).available
    assert reads.availability("2040-01-02", "12:00", package_id).available
    assert reads.pending().bookings[0].id == identity
    with pytest.raises(AdminInputError):
        reads.availability("2040-01-02", "10:00", 2147483647)


def test_database_enforces_read_only_for_all_commands(reads, catalog, empty_database):
    settings_seen = []

    def verify_transaction(conn, cursor, statement, parameters, context, executemany):
        if statement.startswith("SELECT "):
            cursor.execute("SHOW transaction_read_only")
            settings_seen.append(cursor.fetchone()[0])

    event.listen(empty_database, "before_cursor_execute", verify_transaction)
    try:
        for command in ("/agenda", "/pendientes", f"/disponibilidad 2040-01-02 10:00 {catalog[1]}"):
            settings_seen.clear()
            reply(command, reads)
            assert settings_seen and set(settings_seen) == {"on"}
    finally:
        event.remove(empty_database, "before_cursor_execute", verify_transaction)


def test_postgres_refuses_writes_even_when_no_rows_match(empty_database):
    with read_session(empty_database) as session:
        with pytest.raises(DBAPIError) as exc:
            session.execute(text("UPDATE bookings SET status = status WHERE false"))
        assert exc.value.orig.sqlstate == "25006"  # read_only_sql_transaction


def test_pending_matches_inbox_policy(reads, catalog, empty_database):
    from test_commercial import conversation

    with Session(empty_database) as session, session.begin():
        waiting = add_booking(session, catalog, MIDNIGHT)
        add_booking(session, catalog, MIDNIGHT, "confirmed")
        wanted = set()
        for status in ("failed", "queued", "accepted", "delivered", "closed", "old_reply"):
            conv = conversation(session, "Consulta sintética privada")
            if status == "closed":
                conv.state = "closed"
                continue
            stamp = conv.last_incoming_at
            if status == "old_reply":
                stamp -= timedelta(seconds=1)
            if status in {"failed", "queued", "old_reply"}:
                wanted.add(conv.id)
            session.add(
                Message(
                    conversation_id=conv.id,
                    channel=conv.channel,
                    account_id=conv.account_id,
                    direction="outgoing",
                    kind="text",
                    occurred_at=stamp,
                    created_at=stamp,
                    status="read" if status == "old_reply" else status,
                )
            )
    result = reads.pending()
    assert [row.id for row in result.bookings] == [waiting]
    assert {row.id for row in result.conversations} == wanted
    assert "Consulta sintética privada" not in reply("/pendientes", reads)


def test_bounded_and_stable_lists(reads, catalog, empty_database):
    with Session(empty_database) as session, session.begin():
        ids = [add_booking(session, catalog, MIDNIGHT) for _ in range(40)]
    agenda = reads.agenda()
    pending = reads.pending()
    for items, more in ((agenda.bookings, agenda.more), (pending.bookings, pending.more_bookings)):
        assert 0 < len(items) < len(ids)
        assert [item.id for item in items] == ids[: len(items)]
        assert more
    assert len(reply("/agenda", reads)) <= 4096
    assert len(reply("/pendientes", reads)) <= 4096


def test_ambiguous_and_missing_local_times_are_rejected(empty_database):
    reads = AdminReads(empty_database, "America/New_York", clock=lambda: NOW)
    for day, hour, error in (
        ("2040-03-11", "02:30", "no existe"),
        ("2040-11-04", "01:30", "ambigua"),
        ("2040-02-30", "10:30", "fecha válida"),
    ):
        with pytest.raises(AdminInputError, match=error):
            reads.availability(day, hour, 1)
