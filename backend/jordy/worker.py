"""Single-batch simulated outbox processor. Real integrations are intentionally disabled."""

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from jordy.integrations import CalendarProvider, FakeCalendar
from jordy.models import Outbox
from jordy.services import now


def process_batch(session: Session, provider: CalendarProvider, limit: int = 50) -> int:
    rows = session.scalars(
        select(Outbox)
        .where(Outbox.status == "pending", Outbox.available_at <= now())
        .order_by(Outbox.id)
        .limit(limit)
        .with_for_update(skip_locked=True)
    ).all()
    for row in rows:
        row.attempts += 1
        try:
            provider.apply_booking_change(row.payload, row.event_key)
        except Exception:
            # Never persist provider exception strings: they can contain credentials/PII.
            row.last_error = "provider_error"
            row.available_at = now() + timedelta(seconds=min(3600, 2**row.attempts))
            if row.attempts >= 5:
                row.status = "failed"
        else:
            row.status = "simulated"
            row.last_error = None
    return len(rows)


if __name__ == "__main__":
    from jordy.main import get_engine

    with Session(get_engine()) as session, session.begin():
        print(f"Operaciones simuladas: {process_batch(session, FakeCalendar())}")
