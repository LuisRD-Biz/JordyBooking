import argparse
import os

import psycopg
from alembic import command
from alembic.config import Config
from psycopg import sql


def upgrade(config):
    password = os.environ.get("JORDY_APP_PASSWORD", "")
    if len(password) < 32 or password == os.environ["PGPASSWORD"]:
        raise SystemExit(
            "Configura una contraseña de aplicación independiente de al menos 32 caracteres."
        )

    with psycopg.connect(autocommit=True) as owner:
        if not owner.execute("SELECT pg_try_advisory_lock(90421281)").fetchone()[0]:
            raise SystemExit("Ya se está preparando esta base. Espera a que termine.")
        role = owner.execute("""
            SELECT rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls
                OR EXISTS (SELECT 1 FROM pg_auth_members WHERE member = r.oid)
                OR has_schema_privilege(r.oid, 'public', 'CREATE')
            FROM pg_roles r WHERE rolname = 'jordy_app'
        """).fetchone()
        if role and role[0]:
            raise SystemExit("El rol jordy_app existente excede los permisos esperados.")
        if role is None:
            verifier = owner.pgconn.encrypt_password(
                password.encode(), b"jordy_app", b"scram-sha-256"
            )
            owner.execute(
                sql.SQL("CREATE ROLE jordy_app LOGIN PASSWORD {}").format(
                    sql.Literal(verifier.decode())
                )
            )
        with psycopg.connect(user="jordy_app", password=password):
            pass

        command.upgrade(config, "head")
        with owner.transaction():
            owner.execute("GRANT USAGE ON SCHEMA public TO jordy_app")
            owner.execute(
                "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO jordy_app"
            )
            owner.execute("REVOKE INSERT, UPDATE, DELETE ON alembic_version FROM jordy_app")
            owner.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO jordy_app")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", nargs="?", choices=["current", "upgrade"], default="current")
    args = parser.parse_args()
    config = Config("alembic.ini")
    if args.action == "upgrade":
        upgrade(config)
    else:
        command.current(config, verbose=True)
