"""initial booking availability schema"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "5e8d8dfa2f56"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("actor", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "capabilities",
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.PrimaryKeyConstraint("code"),
    )
    op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("contact", sa.String(length=300), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "outbox",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_key", sa.String(length=160), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_error", sa.String(length=200), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_key"),
    )
    op.create_table(
        "packages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("terms", sa.String(length=4000), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("buffer_minutes", sa.Integer(), nullable=False),
        sa.Column("preparation_minutes", sa.Integer(), nullable=False),
        sa.CheckConstraint("kind IN ('session', 'event')"),
        sa.CheckConstraint(
            "duration_minutes > 0 AND buffer_minutes >= 0 AND preparation_minutes >= 0"
        ),
        sa.CheckConstraint("price >= 0"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "resources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.CheckConstraint("kind IN ('staff', 'equipment')"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "bookings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("package_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("location", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("kind IN ('session', 'event')"),
        sa.CheckConstraint("status IN ('pending_approval','confirmed','cancelled','completed')"),
        sa.CheckConstraint("ends_at > starts_at"),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["customers.id"],
        ),
        sa.ForeignKeyConstraint(
            ["package_id"],
            ["packages.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_bookings_customer_id"), "bookings", ["customer_id"], unique=False)
    op.create_index(op.f("ix_bookings_starts_at"), "bookings", ["starts_at"], unique=False)
    op.create_index(op.f("ix_bookings_status"), "bookings", ["status"], unique=False)
    op.create_table(
        "package_requirements",
        sa.Column("package_id", sa.Integer(), nullable=False),
        sa.Column("capability", sa.String(length=80), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.CheckConstraint("quantity > 0"),
        sa.ForeignKeyConstraint(
            ["capability"],
            ["capabilities.code"],
        ),
        sa.ForeignKeyConstraint(
            ["package_id"],
            ["packages.id"],
        ),
        sa.PrimaryKeyConstraint("package_id", "capability"),
    )
    op.create_table(
        "resource_capabilities",
        sa.Column("resource_id", sa.Integer(), nullable=False),
        sa.Column("capability", sa.String(length=80), nullable=False),
        sa.ForeignKeyConstraint(
            ["capability"],
            ["capabilities.code"],
        ),
        sa.ForeignKeyConstraint(
            ["resource_id"],
            ["resources.id"],
        ),
        sa.PrimaryKeyConstraint("resource_id", "capability"),
    )
    op.create_table(
        "contracts",
        sa.Column("booking_id", sa.Integer(), nullable=False),
        sa.Column("reference", sa.String(length=300), nullable=False),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["booking_id"],
            ["bookings.id"],
        ),
        sa.PrimaryKeyConstraint("booking_id"),
    )
    op.create_table(
        "idempotency_records",
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("booking_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["booking_id"],
            ["bookings.id"],
        ),
        sa.PrimaryKeyConstraint("key"),
    )
    op.create_table(
        "resource_occupancies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("resource_id", sa.Integer(), nullable=False),
        sa.Column("booking_id", sa.Integer(), nullable=True),
        sa.Column("capability", sa.String(length=80), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        postgresql.ExcludeConstraint(
            (sa.column("resource_id"), "="),
            (sa.text("tstzrange(starts_at, ends_at, '[)')"), "&&"),
            where=sa.text("active"),
            using="gist",
            name="no_resource_overlap",
        ),
        sa.CheckConstraint(
            "(booking_id IS NOT NULL AND capability IS NOT NULL AND reason IS NULL) OR "
            "(booking_id IS NULL AND capability IS NULL AND reason IS NOT NULL)"
        ),
        sa.CheckConstraint("ends_at > starts_at"),
        sa.ForeignKeyConstraint(
            ["booking_id"],
            ["bookings.id"],
        ),
        sa.ForeignKeyConstraint(
            ["capability"],
            ["capabilities.code"],
        ),
        sa.ForeignKeyConstraint(
            ["resource_id"],
            ["resources.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("booking_id", "resource_id"),
    )
    op.create_index(
        op.f("ix_resource_occupancies_booking_id"),
        "resource_occupancies",
        ["booking_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_resource_occupancies_resource_id"),
        "resource_occupancies",
        ["resource_id"],
        unique=False,
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f("ix_resource_occupancies_resource_id"), table_name="resource_occupancies")
    op.drop_index(op.f("ix_resource_occupancies_booking_id"), table_name="resource_occupancies")
    op.drop_table("resource_occupancies")
    op.drop_table("idempotency_records")
    op.drop_table("contracts")
    op.drop_table("resource_capabilities")
    op.drop_table("package_requirements")
    op.drop_index(op.f("ix_bookings_status"), table_name="bookings")
    op.drop_index(op.f("ix_bookings_starts_at"), table_name="bookings")
    op.drop_index(op.f("ix_bookings_customer_id"), table_name="bookings")
    op.drop_table("bookings")
    op.drop_table("resources")
    op.drop_table("packages")
    op.drop_table("outbox")
    op.drop_table("customers")
    op.drop_table("capabilities")
    op.drop_table("audit_logs")
    # ### end Alembic commands ###
