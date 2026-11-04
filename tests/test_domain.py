from datetime import date

import pytest

from jordy.domain import (
    AvailabilityService,
    Candidate,
    Conflict,
    RuleViolation,
    christmas_slots,
    require_confirmation,
    require_transition,
)


def test_multiskilled_person_cannot_fill_two_slots():
    candidates = [Candidate(1, frozenset({"assistant", "second_camera"}))]
    assert (
        AvailabilityService.check_availability({"assistant": 1, "second_camera": 1}, candidates)
        is None
    )


def test_matching_reassigns_flexible_person():
    candidates = [Candidate(1, frozenset({"photo", "video"})), Candidate(2, frozenset({"photo"}))]
    assert AvailabilityService.check_availability({"photo": 1, "video": 1}, candidates) == {
        1: "video",
        2: "photo",
    }


def test_no_daily_two_events_limit():
    candidates = [Candidate(i, frozenset({"photo"})) for i in range(3)]
    assert len(AvailabilityService.check_availability({"photo": 3}, candidates)) == 3


def test_event_requires_signature_and_session_requires_location():
    with pytest.raises(RuleViolation):
        require_confirmation("pending_approval", "event", "Salon", None)
    with pytest.raises(RuleViolation):
        require_confirmation("pending_approval", "session", " ", None)
    require_confirmation("pending_approval", "session", "Estudio", None)


@pytest.mark.parametrize(
    "current,target",
    [
        ("cancelled", "confirmed"),
        ("pending_approval", "completed"),
        ("completed", "cancelled"),
        ("confirmed", "pending_approval"),
    ],
)
def test_illegal_transitions(current, target):
    with pytest.raises(Conflict):
        require_transition(current, target)


def test_christmas_calendar_template():
    slots = christmas_slots(date(2030, 10, 1), "America/Mexico_City")
    assert [s.hour for s in slots] == [10, 12, 14, 16, 18, 20]
    assert all(s.utcoffset() is not None for s in slots)
    assert christmas_slots(date(2030, 10, 5), "America/Mexico_City") == []
    assert christmas_slots(date(2030, 12, 2), "America/Mexico_City") == []
