"""Framework-independent scheduling and booking rules."""

from dataclasses import dataclass
from datetime import datetime, time
from zoneinfo import ZoneInfo


class RuleViolation(Exception):
    pass


class Conflict(RuleViolation):
    pass


def christmas_slots(day, timezone: str) -> list[datetime]:
    """Campaign template: weekdays in October/November, six two-hour slots."""
    if day.month not in {10, 11} or day.weekday() >= 5:
        return []
    zone = ZoneInfo(timezone)
    return [datetime.combine(day, time(hour=hour), zone) for hour in range(10, 21, 2)]


@dataclass(frozen=True)
class Candidate:
    id: int
    capabilities: frozenset[str]


class AvailabilityService:
    @staticmethod
    def check_availability(
        requirements: dict[str, int], candidates: list[Candidate]
    ) -> dict[int, str] | None:
        """Bipartite matching, so a multi-skilled person is never counted twice."""
        slots = [role for role, count in requirements.items() for _ in range(count)]
        slots.sort(key=lambda role: sum(role in c.capabilities for c in candidates))
        assigned: dict[int, int] = {}

        def match(slot: int, seen: set[int]) -> bool:
            for candidate in candidates:
                if candidate.id in seen or slots[slot] not in candidate.capabilities:
                    continue
                seen.add(candidate.id)
                previous = assigned.get(candidate.id)
                if previous is None or match(previous, seen):
                    assigned[candidate.id] = slot
                    return True
            return False

        if not all(match(slot, set()) for slot in range(len(slots))):
            return None
        return {resource: slots[slot] for resource, slot in assigned.items()}


def require_confirmation(
    status: str, kind: str, location: str | None, signed_at: datetime | None
) -> None:
    if status != "pending_approval":
        raise Conflict("Solo una solicitud pendiente puede confirmarse.")
    if not location or not location.strip():
        raise RuleViolation("Jordy debe acordar el lugar antes de confirmar.")
    if kind == "event" and signed_at is None:
        raise RuleViolation("El evento requiere un contrato firmado.")


def require_transition(current: str, target: str) -> None:
    allowed = {
        "pending_approval": {"cancelled"},
        "confirmed": {"cancelled", "completed"},
        "completed": set(),
        "cancelled": set(),
    }
    if target not in allowed.get(current, set()):
        raise Conflict(f"Transición no permitida: {current} → {target}.")
