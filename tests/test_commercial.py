from datetime import UTC, date, datetime, time, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from jordy.commercial import analyze, generate_summary, recover_summaries
from jordy.commercial_models import CommercialSignal, DailySummary, SummarySchedule
from jordy.commercial_rules import detect
from jordy.models import (
    Booking,
    Contract,
    Conversation,
    Customer,
    Lead,
    Message,
    Occupancy,
    Outbox,
    Package,
)

STAMP = datetime(2026, 10, 20, 17, tzinfo=UTC)
ZONE = "America/Mexico_City"


@pytest.mark.parametrize(
    ("body", "kind", "context"),
    [
        ("¿Entonces confirmamos la boda?", "agreement", "question"),
        ("No quiero cancelar mi boda.", "cancellation", "negated"),
        ("Si contratamos la boda, ¿cuánto cuesta?", "agreement", "hypothetical"),
        ("Mejor sería el 22 de mayo.", "reschedule", "correction"),
        ("No quiero cambiar de fecha.", "reschedule", "negated"),
    ],
)
def test_intention_is_not_effective_confirmation(body, kind, context):
    signals = detect(body, STAMP, ZONE)
    signal = next(s for s in signals if s["kind"] == kind)
    assert signal["certainty"] == "possible"
    assert signal["context"] == context


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ("15 de mayo", None),
        ("15 de mayo de 2027", date(2027, 5, 15)),
        ("31 de febrero de 2027", None),
        ("03/04/2027", None),
        ("el próximo sábado", None),
        ("mañana", date(2026, 10, 21)),
        ("pasado mañana", date(2026, 10, 22)),
        ("2027-05-15", date(2027, 5, 15)),
    ],
)
def test_conservative_dates(body, expected):
    signals = [s for s in detect(body, STAMP, ZONE) if s["kind"] == "date"]
    assert len(signals) == 1
    assert signals[0]["mentioned_date"] == expected
    if expected is None:
        assert signals[0]["certainty"] == "ambiguous"


def test_local_day_and_false_positives():
    stamp = datetime(2026, 10, 21, 2, tzinfo=UTC)  # Still October 20 in the studio.
    assert detect("mañana", stamp, ZONE)[0]["mentioned_date"] == date(2026, 10, 21)
    assert not detect("quince fotos por la mañana", stamp, ZONE)
    assert not detect(None, stamp, ZONE)


def conversation(session, body):
    customer = Customer(name="Prueba comercial", contact="Sintético")
    session.add(customer)
    session.flush()
    conv = Conversation(
        channel="test",
        account_id=uuid4().hex,
        phone_number_id="test",
        external_contact=uuid4().hex,
        display_name="Prueba",
        customer_id=customer.id,
        link_method="manual",
        state="human",
        created_at=STAMP,
        last_activity_at=STAMP,
        last_incoming_at=STAMP,
    )
    session.add(conv)
    session.flush()
    session.add(
        Message(
            conversation_id=conv.id,
            channel="test",
            account_id=conv.account_id,
            direction="incoming",
            kind="text",
            body=body,
            occurred_at=STAMP,
            created_at=STAMP,
            status="received",
            details={},
        )
    )
    session.flush()
    return conv


def counts(session):
    return [
        session.scalar(select(func.count()).select_from(model))
        for model in (Booking, Occupancy, Outbox)
    ]


def test_analysis_report_and_no_operational_side_effects(database, monkeypatch):
    import jordy.commercial as commercial

    monkeypatch.setattr(commercial, "now", lambda: STAMP)
    with Session(database) as s, s.begin():
        conv = conversation(
            s, "Hola, cuánto cuesta una boda para 200 personas el 15 de mayo. ¿Tienen esa fecha?"
        )
        before = counts(s)
        analyze(s, conv.id)
        first = s.scalars(
            select(CommercialSignal).where(CommercialSignal.conversation_id == conv.id)
        ).all()
        assert {"price", "wedding", "date", "availability"} <= {r.kind for r in first}
        first[0].review_state = "reviewed"
        s.flush()
        analyze(s, conv.id)
        assert len(
            s.scalars(
                select(CommercialSignal).where(CommercialSignal.conversation_id == conv.id)
            ).all()
        ) == len(first)
        summary = generate_summary(s, STAMP.date())
        assert summary["content"] == generate_summary(s, STAMP.date())["content"]
        assert (
            s.scalar(
                select(func.count())
                .select_from(DailySummary)
                .where(DailySummary.day == STAMP.date())
            )
            == 1
        )
        assert first[0].review_state == "reviewed"
        assert counts(s) == before


def test_scope_notes_and_proposals(client, database, monkeypatch):
    import jordy.main as main

    monkeypatch.setattr(main, "recover_summaries", lambda engine: None)
    with Session(database) as s, s.begin():
        a = conversation(s, "boda el 15 de mayo")
        b = conversation(s, "Mejor sería el 22 de mayo")
        lead = Lead(
            customer_id=b.customer_id,
            service="Boda",
            channel="test",
            notes="",
            status="new",
            created_at=STAMP,
            last_activity_at=STAMP,
        )
        package = Package(name="Solo prueba", kind="event", price=1, duration_minutes=60)
        s.add_all([lead, package])
        s.flush()
        booking = Booking(
            customer_id=a.customer_id,
            package_id=package.id,
            kind="event",
            starts_at=STAMP,
            ends_at=STAMP + timedelta(hours=1),
            status="confirmed",
            snapshot={},
            approved_at=STAMP,
        )
        s.add(booking)
        s.flush()
        s.add(Contract(booking_id=booking.id, reference="Firma sintética", signed_at=STAMP))
        s.flush()
        aid, bid, lid, booking_id = a.id, b.id, lead.id, booking.id
        before = counts(s)
    signals = client.post(f"/api/commercial/conversations/{bid}/analyze").json()["signals"]
    assert (
        client.patch(
            f"/api/commercial/conversations/{aid}/signals/{signals[0]['id']}",
            json={"state": "reviewed"},
        ).status_code
        == 422
    )
    base = f"/api/commercial/conversations/{aid}"
    assert (
        client.post(
            base + "/plans",
            json={
                "requested_date": "2027-05-22",
                "lead_id": lid,
            },
        ).status_code
        == 422
    )
    assert (
        client.post(
            base + "/plans",
            json={
                "requested_date": "2027-05-22",
                "kind": "reschedule",
            },
        ).status_code
        == 422
    )
    assert (
        client.post(
            base + "/plans",
            json={
                "requested_date": "2027-05-22",
                "kind": "tentative",
                "alternative_dates": ["2027-05-15"],
            },
        ).status_code
        == 200
    )
    assert (
        client.post(
            base + "/plans",
            json={
                "requested_date": "2027-05-22",
                "kind": "reschedule",
                "booking_id": booking_id,
            },
        ).status_code
        == 200
    )
    assert (
        client.post(
            base + "/notes",
            json={
                "body": "Acuerdo relatado en llamada, pendiente de Jordy.",
                "source": "call",
            },
        ).status_code
        == 200
    )
    assert client.get(f"/api/commercial/conversations/{bid}").json()["notes"] == []
    with Session(database) as s:
        assert counts(s) == before
        assert s.get(Booking, booking_id).starts_at == STAMP
        assert s.get(Booking, booking_id).status == "confirmed"
        assert s.get(Contract, booking_id).reference == "Firma sintética"


def test_schedule_recovery_without_duplicate_reports(database):
    with Session(database) as s, s.begin():
        s.merge(SummarySchedule(id=1, start_day=date(2026, 10, 18), local_time=time(1)))
    current = datetime(2026, 10, 20, 17, tzinfo=UTC)
    for _ in range(3):
        recover_summaries(database, current)
    with Session(database) as s:
        assert s.get(SummarySchedule, 1).last_day == date(2026, 10, 19)
        assert s.get(DailySummary, date(2026, 10, 18))
        assert s.get(DailySummary, date(2026, 10, 19))
