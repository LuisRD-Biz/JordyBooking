import os
from contextlib import contextmanager
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from jordy.config import settings
from jordy.db import get_session
from jordy.main import app

TEST_KEY = "test-only-admin-key-with-at-least-32-chars"


@contextmanager
def _migrated_test_database():
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL required for real PostgreSQL integration tests")
    if not (make_url(url).database or "").endswith("_test"):
        raise RuntimeError("Integration database name must end in _test")
    # A unique schema per suite: never truncate or drop existing application data.
    engine = create_engine(url)
    schema = "test_" + uuid4().hex
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS btree_gist"))
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    scoped = make_url(url).update_query_dict({"options": f"-csearch_path={schema},public"})
    previous = {k: os.environ.get(k) for k in ["DATABASE_URL", "ADMIN_API_KEY"]}
    os.environ["DATABASE_URL"] = scoped.render_as_string(hide_password=False)
    os.environ["ADMIN_API_KEY"] = TEST_KEY
    settings.cache_clear()
    test_engine = create_engine(scoped)
    try:
        command.upgrade(Config("alembic.ini"), "head")
        yield test_engine
    finally:
        test_engine.dispose()
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        settings.cache_clear()
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()


@pytest.fixture(scope="session")
def database():
    with _migrated_test_database() as engine:
        yield engine


@pytest.fixture
def empty_database():
    # Unfiltered administrative lists must see only the rows arranged by this test.
    with _migrated_test_database() as engine:
        yield engine


@pytest.fixture
def client(database):
    def override():
        with Session(database) as session:
            yield session

    app.dependency_overrides[get_session] = override
    with TestClient(app, headers={"X-Admin-Key": TEST_KEY}) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def messaging_enabled(monkeypatch):
    """WhatsApp and commercial follow-up are off by default; their suites opt in."""
    monkeypatch.setenv("MESSAGING_ENABLED", "true")
    settings.cache_clear()
    yield
    settings.cache_clear()
