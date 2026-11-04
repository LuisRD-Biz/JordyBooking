"""Contracts for external integrations; no real credentials or network calls yet."""

from typing import Protocol


class CalendarProvider(Protocol):
    def apply_booking_change(self, payload: dict, idempotency_key: str) -> None: ...


class FakeCalendar:
    def __init__(self):
        self.applied: dict[str, dict] = {}

    def apply_booking_change(self, payload: dict, idempotency_key: str) -> None:
        self.applied.setdefault(idempotency_key, payload)
