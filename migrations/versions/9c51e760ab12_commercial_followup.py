import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "9c51e760ab12"
down_revision = "7b41c092a661"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "commercial_signals",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column(
            "conversation_id", sa.Integer(), sa.ForeignKey("conversations.id"), nullable=False
        ),
        sa.Column("message_id", sa.Integer(), sa.ForeignKey("messages.id"), nullable=False),
        sa.Column("signal_key", sa.String(length=100), nullable=False),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("evidence", sa.String(length=500), nullable=False),
        sa.Column("mentioned_date", sa.Date(), nullable=True),
        sa.Column("certainty", sa.String(length=20), nullable=False),
        sa.Column("context", sa.String(length=30), nullable=False),
        sa.Column("review_state", sa.String(length=20), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rule_version", sa.String(length=20), nullable=False),
        sa.UniqueConstraint("message_id", "signal_key"),
    )
    op.create_index(
        "ix_commercial_signals_conversation_id", "commercial_signals", ["conversation_id"]
    )
    op.create_index("ix_commercial_signals_message_id", "commercial_signals", ["message_id"])
    op.create_table(
        "commercial_notes",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column(
            "conversation_id", sa.Integer(), sa.ForeignKey("conversations.id"), nullable=False
        ),
        sa.Column("body", sa.String(length=2000), nullable=False),
        sa.Column("source", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor", sa.String(length=100), nullable=False),
    )
    op.create_index("ix_commercial_notes_conversation_id", "commercial_notes", ["conversation_id"])
    op.create_table(
        "commercial_plans",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column(
            "conversation_id", sa.Integer(), sa.ForeignKey("conversations.id"), nullable=False
        ),
        sa.Column("lead_id", sa.Integer(), sa.ForeignKey("leads.id"), nullable=True),
        sa.Column("booking_id", sa.Integer(), sa.ForeignKey("bookings.id"), nullable=True),
        sa.Column("requested_date", sa.Date(), nullable=False),
        sa.Column("alternative_dates", JSONB(), nullable=False),
        sa.Column("tentative_date", sa.Date(), nullable=True),
        sa.Column("time_note", sa.String(length=200), nullable=False),
        sa.Column("kind", sa.String(length=30), nullable=False),
        sa.Column("agreement", sa.String(length=30), nullable=False),
        sa.Column("notes", sa.String(length=2000), nullable=False),
        sa.Column("review_state", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_commercial_plans_conversation_id", "commercial_plans", ["conversation_id"])
    op.create_index("ix_commercial_plans_requested_date", "commercial_plans", ["requested_date"])
    op.create_table(
        "daily_summaries",
        sa.Column("day", sa.Date(), primary_key=True, nullable=False),
        sa.Column("timezone", sa.String(length=80), nullable=False),
        sa.Column("content", JSONB(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "summary_schedule",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("local_time", sa.Time(), nullable=True),
        sa.Column("start_day", sa.Date(), nullable=False),
        sa.Column("last_day", sa.Date(), nullable=True),
        sa.Column("last_error", sa.String(length=60), nullable=True),
    )


def downgrade():
    raise RuntimeError("Destructive downgrade disabled: preserve commercial history.")
