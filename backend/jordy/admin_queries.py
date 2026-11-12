from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime

from sqlalchemy import Engine, create_engine, make_url, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from jordy.messaging.queries import needs_reply
from jordy.models import Booking, Conversation

RESULT_LIMIT = 15


class AdminReadUnavailable(Exception):
    pass


def build_read_engine(url: str) -> Engine:
    parsed = make_url(url)
    if parsed.drivername not in {"postgresql", "postgresql+psycopg"}:
        raise ValueError("Se requiere PostgreSQL con psycopg.")
    return create_engine(
        parsed.set(drivername="postgresql+psycopg"),
        pool_pre_ping=True,
        hide_parameters=True,
        connect_args={"connect_timeout": 5},
    )


@contextmanager
def read_session(engine: Engine) -> Iterator[Session]:
    try:
        with Session(engine, autoflush=False) as session:
            session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
            session.execute(text("SET LOCAL statement_timeout = '5s'"))
            yield session
    except SQLAlchemyError:
        raise AdminReadUnavailable("No se pudo consultar la base de datos.") from None


def _bookings():
    return select(Booking.id, Booking.starts_at, Booking.ends_at, Booking.kind, Booking.status)


def agenda(session: Session, start: datetime, end: datetime):
    return session.execute(
        _bookings()
        .where(Booking.starts_at < end, Booking.ends_at > start)
        .order_by(Booking.starts_at, Booking.id)
        .limit(RESULT_LIMIT + 1)
    ).all()


def pending_bookings(session: Session):
    return session.execute(
        _bookings()
        .where(Booking.status == "pending_approval")
        .order_by(Booking.starts_at, Booking.id)
        .limit(RESULT_LIMIT + 1)
    ).all()


def pending_replies(session: Session):
    return session.execute(
        select(Conversation.id, Conversation.last_incoming_at)
        .where(needs_reply())
        .order_by(Conversation.last_incoming_at, Conversation.id)
        .limit(RESULT_LIMIT + 1)
    ).all()
