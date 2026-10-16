from uuid import uuid4

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
            command.upgrade(config, "head")
            assert "resource_occupancies" in inspect(engine).get_table_names(schema=schema)
            command.downgrade(config, "base")
            assert "bookings" not in inspect(engine).get_table_names(schema=schema)
            command.upgrade(config, "head")
            assert "bookings" in inspect(engine).get_table_names(schema=schema)
        finally:
            engine.dispose()
            with database.begin() as connection:
                connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
    settings.cache_clear()
