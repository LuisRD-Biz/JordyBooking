from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from jordy.domain import Candidate, RuleViolation
from jordy.models import Occupancy, Resource


class NotFound(RuleViolation):
    pass


def require(session: Session, model, identity, *, lock=False):
    statement = select(model).where(model.id == identity)
    if lock:
        statement = statement.with_for_update()
    result = session.scalar(statement)
    if result is None:
        raise NotFound("Registro no encontrado.")
    return result


def available_resources(session: Session, start: datetime, end: datetime, *, lock=False):
    # A deliberately conservative lock for a small studio. Every writer locks resources
    # in the same order. The exclusion constraint is the final database safeguard.
    statement = select(Resource).order_by(Resource.id)
    if lock:
        statement = statement.with_for_update()
    resources = session.scalars(statement).all()
    busy = set(
        session.scalars(
            select(Occupancy.resource_id).where(
                Occupancy.active.is_(True), Occupancy.starts_at < end, Occupancy.ends_at > start
            )
        )
    )
    return [
        Candidate(r.id, frozenset(c.capability for c in r.capabilities))
        for r in resources
        if r.id not in busy
    ]
