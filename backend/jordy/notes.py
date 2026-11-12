"""Append-only notes on a booking, each signed by the account that wrote it.

Notes are never edited or deleted: a correction is another note. That keeps the history
trustworthy when several people (and later an assistant) write on the same booking.
"""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Response
from pydantic import BaseModel, Field
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from jordy.accounts import User
from jordy.api import ADMIN
from jordy.db import get_session
from jordy.domain import Conflict
from jordy.models import Base, Booking
from jordy.repository import require
from jordy.schemas import Input
from jordy.services import audit, now

BODY_MAX = 4000
LOCAL_AUTHOR = "Acceso local"

router = APIRouter(prefix="/api", dependencies=ADMIN)
DB = Annotated[Session, Depends(get_session)]


class BookingNote(Base):
    __tablename__ = "booking_notes"
    __table_args__ = (
        CheckConstraint("char_length(body) BETWEEN 1 AND 4000", name="ck_booking_notes_body"),
        Index("ix_booking_notes_booking_created", "booking_id", "created_at"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"))
    # Null for access without an account (the desktop's local session or the admin key).
    author_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(String(BODY_MAX))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # Optional client-chosen key so a retried request does not write the note twice.
    request_key: Mapped[UUID | None] = mapped_column(unique=True)


class NoteInput(Input):
    body: str = Field(min_length=1, max_length=BODY_MAX)


class NoteOutput(BaseModel):
    id: int
    booking_id: int
    body: str
    created_at: datetime
    author_user_id: int | None
    author_name: str


def output(note: BookingNote, author: str | None) -> NoteOutput:
    return NoteOutput(
        id=note.id,
        booking_id=note.booking_id,
        body=note.body,
        created_at=note.created_at,
        author_user_id=note.author_user_id,
        author_name=author or LOCAL_AUTHOR,
    )


@router.get("/bookings/{identity}/notes", response_model=list[NoteOutput])
def notes(identity: int, session: DB):
    """Oldest first, so the list reads as a conversation."""
    require(session, Booking, identity)
    rows = session.execute(
        select(BookingNote, User.name)
        .outerjoin(User, User.id == BookingNote.author_user_id)
        .where(BookingNote.booking_id == identity)
        .order_by(BookingNote.created_at, BookingNote.id)
        .limit(500)
    )
    return [output(note, author) for note, author in rows]


@router.post("/bookings/{identity}/notes", response_model=NoteOutput, status_code=201)
def note_create(
    identity: int,
    data: NoteInput,
    session: DB,
    response: Response,
    idempotency_key: Annotated[UUID | None, Header()] = None,
):
    with session.begin():
        # The row lock also serializes two requests that carry the same key.
        require(session, Booking, identity, lock=True)
        author_id = session.info.get("actor_user_id")
        note = None
        if idempotency_key:
            note = session.scalar(
                select(BookingNote).where(BookingNote.request_key == idempotency_key)
            )
            if note and (note.booking_id, note.body) != (identity, data.body):
                raise Conflict("La clave de idempotencia ya se utilizó con otros datos.")
        if note:
            response.status_code = 200
        else:
            note = BookingNote(
                booking_id=identity,
                author_user_id=author_id,
                body=data.body,
                created_at=now(),
                request_key=idempotency_key,
            )
            session.add(note)
            session.flush()
            audit(session, "booking.note_added", identity)
        author = session.get(User, note.author_user_id) if note.author_user_id else None
        result = output(note, author.name if author else None)
    return result
