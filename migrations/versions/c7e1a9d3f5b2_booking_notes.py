"""Add append-only notes on bookings, signed by the account that wrote them."""

import sqlalchemy as sa
from alembic import op

revision = "c7e1a9d3f5b2"
down_revision = "b4d2e6f8a1c3"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "booking_notes",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("booking_id", sa.Integer(), sa.ForeignKey("bookings.id"), nullable=False),
        sa.Column("author_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("body", sa.String(length=4000), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("request_key", sa.Uuid(), nullable=True),
        sa.CheckConstraint("char_length(body) BETWEEN 1 AND 4000", name="ck_booking_notes_body"),
        sa.UniqueConstraint("request_key", name="uq_booking_notes_request_key"),
    )
    op.create_index(
        "ix_booking_notes_booking_created", "booking_notes", ["booking_id", "created_at"]
    )


def downgrade():
    raise RuntimeError("Destructive downgrade disabled: preserve booking notes.")
