from datetime import date, datetime, time

from sqlalchemy import Date, DateTime, ForeignKey, String, Time, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from jordy.models import Base


class CommercialSignal(Base):
    __tablename__ = "commercial_signals"
    __table_args__ = (UniqueConstraint("message_id", "signal_key"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), index=True)
    message_id: Mapped[int] = mapped_column(ForeignKey("messages.id"), index=True)
    signal_key: Mapped[str] = mapped_column(String(100))
    kind: Mapped[str] = mapped_column(String(40))
    evidence: Mapped[str] = mapped_column(String(500))
    mentioned_date: Mapped[date | None] = mapped_column(Date)
    certainty: Mapped[str] = mapped_column(String(20))
    context: Mapped[str] = mapped_column(String(30))
    review_state: Mapped[str] = mapped_column(String(20), default="pending")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rule_version: Mapped[str] = mapped_column(String(20), default="1")


class CommercialNote(Base):
    __tablename__ = "commercial_notes"
    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), index=True)
    body: Mapped[str] = mapped_column(String(2000))
    source: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    actor: Mapped[str] = mapped_column(String(100), default="jordy-admin")


class CommercialPlan(Base):
    __tablename__ = "commercial_plans"
    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), index=True)
    lead_id: Mapped[int | None] = mapped_column(ForeignKey("leads.id"))
    booking_id: Mapped[int | None] = mapped_column(ForeignKey("bookings.id"))
    requested_date: Mapped[date] = mapped_column(Date, index=True)
    alternative_dates: Mapped[list] = mapped_column(JSONB, default=list)
    tentative_date: Mapped[date | None] = mapped_column(Date)
    time_note: Mapped[str] = mapped_column(String(200), default="")
    kind: Mapped[str] = mapped_column(String(30))
    agreement: Mapped[str] = mapped_column(String(30))
    notes: Mapped[str] = mapped_column(String(2000), default="")
    review_state: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class DailySummary(Base):
    __tablename__ = "daily_summaries"
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    timezone: Mapped[str] = mapped_column(String(80))
    content: Mapped[dict] = mapped_column(JSONB)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SummarySchedule(Base):
    __tablename__ = "summary_schedule"
    id: Mapped[int] = mapped_column(primary_key=True)
    local_time: Mapped[time | None] = mapped_column(Time)
    start_day: Mapped[date] = mapped_column(Date)
    last_day: Mapped[date | None] = mapped_column(Date)
    last_error: Mapped[str | None] = mapped_column(String(60))
