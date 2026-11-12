"""Administrative use cases. Consumers receive limited records with no customer details."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import Engine

from jordy import admin_queries as queries
from jordy.admin_queries import RESULT_LIMIT
from jordy.admin_queries import AdminReadUnavailable as AdminReadUnavailable
from jordy.domain import day_bounds
from jordy.repository import NotFound
from jordy.services import now, preview_allocation


class AdminInputError(ValueError):
    """A validation message suitable for display to an authorized operator."""


@dataclass(frozen=True)
class BookingItem:
    id: int
    starts_at: datetime
    ends_at: datetime
    kind: str
    status: str


@dataclass(frozen=True)
class Agenda:
    start_day: date
    end_day: date  # Inclusive, local to the studio
    bookings: tuple[BookingItem, ...]
    more: bool


@dataclass(frozen=True)
class Availability:
    package_id: int
    starts_at: datetime
    available: bool
    assignments: tuple[tuple[int, str], ...]
    more_assignments: bool


@dataclass(frozen=True)
class FollowUp:
    id: int
    last_incoming_at: datetime


@dataclass(frozen=True)
class Pending:
    bookings: tuple[BookingItem, ...]
    # None when messaging is disabled: there is no inbox to follow up.
    conversations: tuple[FollowUp, ...] | None
    more_bookings: bool
    more_conversations: bool


def _date(value: str) -> date:
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        parsed = None
    # Leave room for interval arithmetic and timezone conversion at year boundaries.
    if not parsed or not 1 < parsed.year < 9999 or parsed.isoformat() != value:
        raise AdminInputError("Indica una fecha válida en formato AAAA-MM-DD.")
    return parsed


def _local_start(day: str, at: str, zone: ZoneInfo) -> datetime:
    parsed_day = _date(day)
    try:
        parsed_time = time.fromisoformat(at)
    except ValueError:
        parsed_time = None
    if not parsed_time or parsed_time.isoformat(timespec="minutes") != at or len(at) != 5:
        raise AdminInputError("Indica la hora local en formato HH:MM de 24 horas.")
    local = datetime.combine(parsed_day, parsed_time, zone)
    if local.astimezone(UTC).astimezone(zone) != local:
        raise AdminInputError("Esa hora local no existe por el cambio de horario.")
    if local.utcoffset() != local.replace(fold=1).utcoffset():
        raise AdminInputError(
            "Esa hora local es ambigua por el cambio de horario. Elige otra hora."
        )
    return local


class AdminReads:
    def __init__(
        self,
        engine: Engine,
        timezone: str,
        *,
        clock: Callable[[], datetime] = now,
        messaging_enabled: bool = False,
    ) -> None:
        self._engine = engine
        self._clock = clock
        self._messaging = messaging_enabled
        self.zone = ZoneInfo(timezone)

    def _bookings(self, rows) -> tuple[BookingItem, ...]:
        return tuple(
            BookingItem(
                row.id,
                row.starts_at.astimezone(self.zone),
                row.ends_at.astimezone(self.zone),
                row.kind,
                row.status,
            )
            for row in rows[:RESULT_LIMIT]
        )

    def agenda(self, period: str = "hoy") -> Agenda:
        today = self._clock().astimezone(self.zone).date()
        if period in ("hoy", "semana"):
            day = today
        elif period in ("mañana", "manana"):
            day = today + timedelta(days=1)
        else:
            day = _date(period)
        start, end = day_bounds(day, self.zone.key, days=7 if period == "semana" else 1)
        with queries.read_session(self._engine) as session:
            rows = queries.agenda(session, start, end)
            return Agenda(
                day, end.date() - timedelta(days=1), self._bookings(rows), len(rows) > RESULT_LIMIT
            )

    def availability(self, day: str, at: str, package_id: int) -> Availability:
        if type(package_id) is not int or not 0 < package_id <= 2**31 - 1:
            raise AdminInputError("Indica un ID de paquete válido.")
        start = _local_start(day, at, self.zone)
        with queries.read_session(self._engine) as session:
            try:
                # Pass an instant so preparation and duration are elapsed minutes across DST.
                allocation = preview_allocation(session, package_id, start.astimezone(UTC))
            except NotFound:
                raise AdminInputError("No se encontró el paquete indicado.") from None
        suggestions = sorted((allocation or {}).items())
        return Availability(
            package_id,
            start,
            allocation is not None,
            tuple(suggestions[:RESULT_LIMIT]),
            len(suggestions) > RESULT_LIMIT,
        )

    def pending(self) -> Pending:
        with queries.read_session(self._engine) as session:
            bookings = queries.pending_bookings(session)
            replies = queries.pending_replies(session) if self._messaging else None
        return Pending(
            self._bookings(bookings),
            None
            if replies is None
            else tuple(
                FollowUp(row.id, row.last_incoming_at.astimezone(self.zone))
                for row in replies[:RESULT_LIMIT]
            ),
            len(bookings) > RESULT_LIMIT,
            replies is not None and len(replies) > RESULT_LIMIT,
        )
