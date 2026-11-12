import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "7b41c092a661"
down_revision = "3f152243a93e"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "outbox", sa.Column("topic", sa.String(40), nullable=False, server_default="booking")
    )
    op.create_index("ix_outbox_topic", "outbox", ["topic"])
    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("channel", sa.String(30), nullable=False),
        sa.Column("account_id", sa.String(100), nullable=False),
        sa.Column("phone_number_id", sa.String(100), nullable=False),
        sa.Column("external_contact", sa.String(200), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id")),
        sa.Column("link_method", sa.String(30), nullable=False),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("responsible", sa.String(100)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_incoming_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("channel", "account_id", "external_contact"),
        sa.CheckConstraint("state IN ('human', 'closed')"),
    )
    for col in ("customer_id", "last_activity_at"):
        op.create_index("ix_conversations_" + col, "conversations", [col])
    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "conversation_id", sa.Integer(), sa.ForeignKey("conversations.id"), nullable=False
        ),
        sa.Column("channel", sa.String(30), nullable=False),
        sa.Column("account_id", sa.String(100), nullable=False),
        sa.Column("external_id", sa.String(300)),
        sa.Column("request_key", sa.Uuid(), unique=True),
        sa.Column("request_hash", sa.String(64)),
        sa.Column("direction", sa.String(20), nullable=False),
        sa.Column("kind", sa.String(30), nullable=False),
        sa.Column("body", sa.String(4096)),
        sa.Column("details", postgresql.JSONB(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("error_code", sa.String(80)),
        sa.UniqueConstraint("channel", "account_id", "external_id"),
        sa.CheckConstraint("direction IN ('incoming', 'outgoing')"),
    )
    for col in ("conversation_id", "occurred_at"):
        op.create_index("ix_messages_" + col, "messages", [col])
    op.create_table(
        "message_receipts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("account_id", sa.String(100), nullable=False),
        sa.Column("external_id", sa.String(300), nullable=False),
        sa.Column("recipient", sa.String(200), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("error_code", sa.String(80)),
        sa.UniqueConstraint("account_id", "external_id", "status", "occurred_at"),
    )
    op.create_index("ix_message_receipts_external_id", "message_receipts", ["external_id"])


def downgrade():
    connection = op.get_bind()
    for table in ("messages", "conversations", "message_receipts"):
        if connection.scalar(sa.text(f"SELECT EXISTS (SELECT 1 FROM {table})")):
            raise RuntimeError(
                "Refusing downgrade with messaging history. Restore a reviewed backup."
            )
    if connection.scalar(sa.text("SELECT EXISTS (SELECT 1 FROM outbox WHERE topic != 'booking')")):
        raise RuntimeError("Refusing downgrade with messaging jobs.")
    op.drop_table("message_receipts")
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_index("ix_outbox_topic", "outbox")
    op.drop_column("outbox", "topic")
