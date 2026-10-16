from sqlalchemy import create_engine
from sqlalchemy.orm import Session


def build_engine(url: str):
    return create_engine(url, pool_pre_ping=True, hide_parameters=True)


def get_session():
    # Engine is attached at application startup; dependency import avoids a cycle.
    from jordy.main import get_engine

    with Session(get_engine()) as session:
        yield session
