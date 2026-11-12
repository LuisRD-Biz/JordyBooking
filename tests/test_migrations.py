from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from jordy.config import settings


def test_upgrade_downgrade_upgrade_isolated_schema(database, monkeypatch):
    schema = "migration_" + uuid4().hex
    with database.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    url = database.url.update_query_dict({"options": f"-csearch_path={schema},public"})
    engine = create_engine(url)
    with monkeypatch.context() as patch:
        patch.setenv("DATABASE_URL", url.render_as_string(hide_password=False))
        settings.cache_clear()
        try:
            config = Config("alembic.ini")
            command.upgrade(config, "7b41c092a661")
            assert "resource_occupancies" in inspect(engine).get_table_names(schema=schema)
            command.downgrade(config, "base")
            assert "bookings" not in inspect(engine).get_table_names(schema=schema)
            command.upgrade(config, "head")
            assert "bookings" in inspect(engine).get_table_names(schema=schema)
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "INSERT INTO daily_summaries (day, timezone, content, generated_at) "
                        "VALUES ('2026-01-01', 'America/Mexico_City', '{}', now())"
                    )
                )
            with pytest.raises(RuntimeError, match="Destructive downgrade disabled"):
                command.downgrade(config, "base")
            with engine.connect() as connection:
                assert connection.scalar(text("SELECT count(*) FROM daily_summaries")) == 1
                assert connection.scalar(text("SELECT version_num FROM alembic_version")) == (
                    "c7e1a9d3f5b2"
                )
            command.upgrade(config, "head")
        finally:
            engine.dispose()
            with database.begin() as connection:
                connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
    settings.cache_clear()
