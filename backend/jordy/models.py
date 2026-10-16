from datetime import datetime
from decimal import Decimal

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
    contract: Mapped["Contract | None"] = relationship(uselist=False, lazy="selectin")


class Contract(Base):
    __tablename__ = "contracts"
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"), primary_key=True)
    reference: Mapped[str] = mapped_column(String(300))
    signed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


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
