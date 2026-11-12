from alembic import context
from sqlalchemy import create_engine, pool

from jordy import accounts, commercial_models  # noqa: F401 — register model metadata
from jordy.config import StudioDatabaseSettings
from jordy.models import Base


def run():
    url = StudioDatabaseSettings().database_url
    if context.is_offline_mode():
        context.configure(url=url, target_metadata=Base.metadata, literal_binds=True)
        with context.begin_transaction():
            context.run_migrations()
    else:
        engine = create_engine(url, poolclass=pool.NullPool)
        with engine.connect() as connection:
            schema = connection.exec_driver_sql("SELECT current_schema()").scalar_one()
            connection.commit()
            context.configure(
                connection=connection,
                target_metadata=Base.metadata,
                version_table_schema=schema,
                include_object=lambda obj, name, kind, reflected, compare: (
                    name != "alembic_version"
                ),
            )
            with context.begin_transaction():
                context.run_migrations()


run()
