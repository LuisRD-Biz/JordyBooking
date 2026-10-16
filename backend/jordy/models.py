from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, ExcludeConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Customer(Base):
    __tablename__ = "customers"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    contact: Mapped[str] = mapped_column(String(300))
    phone: Mapped[str | None] = mapped_column(String(40))
    email: Mapped[str | None] = mapped_column(String(254))
    normalized_phone: Mapped[str | None] = mapped_column(String(40), index=True)
    normalized_email: Mapped[str | None] = mapped_column(String(254), index=True)
    notes: Mapped[str] = mapped_column(String(4000), default="", server_default="")
    featured: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)


class Resource(Base):
    __tablename__ = "resources"
    __table_args__ = (CheckConstraint("kind IN ('staff', 'equipment')"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(20))
    capabilities: Mapped[list["ResourceCapability"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin"
    )


class Capability(Base):
    __tablename__ = "capabilities"
    code: Mapped[str] = mapped_column(String(80), primary_key=True)


class ResourceCapability(Base):
    __tablename__ = "resource_capabilities"
    resource_id: Mapped[int] = mapped_column(ForeignKey("resources.id"), primary_key=True)
    capability: Mapped[str] = mapped_column(ForeignKey("capabilities.code"), primary_key=True)


class Package(Base):
    __tablename__ = "packages"
    __table_args__ = (
        CheckConstraint("kind IN ('session', 'event')"),
        CheckConstraint("price >= 0"),
        CheckConstraint(
            "duration_minutes > 0 AND buffer_minutes >= 0 AND preparation_minutes >= 0"
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(20))
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="MXN")
    terms: Mapped[str] = mapped_column(String(4000), default="")
    duration_minutes: Mapped[int]
    buffer_minutes: Mapped[int] = mapped_column(default=0)
    preparation_minutes: Mapped[int] = mapped_column(default=0)
    requirements: Mapped[list["PackageRequirement"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin"
    )


class PackageRequirement(Base):
    __tablename__ = "package_requirements"
    __table_args__ = (CheckConstraint("quantity > 0"),)
    package_id: Mapped[int] = mapped_column(ForeignKey("packages.id"), primary_key=True)
    capability: Mapped[str] = mapped_column(ForeignKey("capabilities.code"), primary_key=True)
    quantity: Mapped[int]


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (
        CheckConstraint("ends_at > starts_at"),
        CheckConstraint("kind IN ('session', 'event')"),
        CheckConstraint("status IN ('pending_approval','confirmed','cancelled','completed')"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    package_id: Mapped[int] = mapped_column(ForeignKey("packages.id"))
    kind: Mapped[str] = mapped_column(String(20))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    location: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(30), default="pending_approval", index=True)
    snapshot: Mapped[dict] = mapped_column(JSONB)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    quote_id: Mapped[int | None] = mapped_column(ForeignKey("quotes.id"), unique=True)
    contract: Mapped["Contract | None"] = relationship(uselist=False, lazy="selectin")


class Contract(Base):
    __tablename__ = "contracts"
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"), primary_key=True)
    reference: Mapped[str] = mapped_column(String(300))
    signed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    document_id: Mapped[UUID | None] = mapped_column(ForeignKey("booking_documents.id"))


class BookingDocument(Base):
    __tablename__ = "booking_documents"
    __table_args__ = (
        UniqueConstraint("group_id", "version"),
        CheckConstraint("size > 0 AND version > 0"),
        CheckConstraint("document_type IN ('contract','deposit','annex','other')"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"), index=True)
    group_id: Mapped[UUID] = mapped_column(index=True)
    version: Mapped[int] = mapped_column(default=1)
    is_current: Mapped[bool] = mapped_column(default=True)
    document_type: Mapped[str] = mapped_column(String(20))
    original_name: Mapped[str] = mapped_column(String(240))
    storage_key: Mapped[str] = mapped_column(String(80), unique=True)
    mime: Mapped[str] = mapped_column(String(80))
    size: Mapped[int]
    sha256: Mapped[str] = mapped_column(String(64))
    notes: Mapped[str] = mapped_column(String(2000), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    actor: Mapped[str] = mapped_column(String(100), default="jordy-admin")


class Lead(Base):
    __tablename__ = "leads"
    __table_args__ = (
        CheckConstraint("status IN ('new','contacted','quoted','pending_booking','won','lost')"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    service: Mapped[str] = mapped_column(String(200))
    channel: Mapped[str] = mapped_column(String(100))
    requested_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    notes: Mapped[str] = mapped_column(String(4000), default="")
    status: Mapped[str] = mapped_column(String(30), default="new", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class Quote(Base):
    __tablename__ = "quotes"
    __table_args__ = (UniqueConstraint("lead_id", "version"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id"), index=True)
    version: Mapped[int]
    package_id: Mapped[int] = mapped_column(ForeignKey("packages.id"))
    snapshot: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    actor: Mapped[str] = mapped_column(String(100), default="jordy-admin")


class Appointment(Base):
    __tablename__ = "appointments"
    __table_args__ = (
        CheckConstraint("ends_at > starts_at"),
        CheckConstraint("kind IN ('contract','meeting')"),
        CheckConstraint("status IN ('scheduled','completed','cancelled')"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    booking_id: Mapped[int | None] = mapped_column(ForeignKey("bookings.id"), index=True)
    lead_id: Mapped[int | None] = mapped_column(ForeignKey("leads.id"), index=True)
    kind: Mapped[str] = mapped_column(String(20))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    location: Mapped[str] = mapped_column(String(500))
    notes: Mapped[str] = mapped_column(String(2000), default="")
    status: Mapped[str] = mapped_column(String(20), default="scheduled")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Occupancy(Base):
    __tablename__ = "resource_occupancies"
    __table_args__ = (
        CheckConstraint("ends_at > starts_at"),
        CheckConstraint(
            "(booking_id IS NOT NULL AND capability IS NOT NULL AND reason IS NULL) OR "
            "(booking_id IS NULL AND capability IS NULL AND reason IS NOT NULL)"
        ),
        UniqueConstraint("booking_id", "resource_id"),
        ExcludeConstraint(
            ("resource_id", "="),
            (text("tstzrange(starts_at, ends_at, '[)')"), "&&"),
            where=text("active"),
            using="gist",
            name="no_resource_overlap",
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    resource_id: Mapped[int] = mapped_column(ForeignKey("resources.id"), index=True)
    booking_id: Mapped[int | None] = mapped_column(ForeignKey("bookings.id"), index=True)
    capability: Mapped[str | None] = mapped_column(ForeignKey("capabilities.code"))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    reason: Mapped[str | None] = mapped_column(String(500))
    active: Mapped[bool] = mapped_column(default=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    action: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[int]
    actor: Mapped[str] = mapped_column(String(100), default="jordy-admin")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Outbox(Base):
    __tablename__ = "outbox"
    id: Mapped[int] = mapped_column(primary_key=True)
    event_key: Mapped[str] = mapped_column(String(160), unique=True)
    payload: Mapped[dict] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(String(200))


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    request_hash: Mapped[str] = mapped_column(String(64))
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"))
