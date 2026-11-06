"""Read predicates shared by the inbox and administrative reports."""

from sqlalchemy import and_, select

from jordy.models import Conversation, Message


def needs_reply():
    """A successful outbound at or after the latest inbound closes the pending reply."""
    answered = (
        select(Message.id)
        .where(
            Message.conversation_id == Conversation.id,
            Message.direction == "outgoing",
            Message.status.in_(("accepted", "sent", "delivered", "read")),
            Message.occurred_at >= Conversation.last_incoming_at,
        )
        .correlate(Conversation)
        .exists()
    )
    return and_(
        Conversation.state == "human", Conversation.last_incoming_at.is_not(None), ~answered
    )
