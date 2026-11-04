"""Prepare a dedicated local panel database without changing existing databases."""

import os
import secrets
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / ".local"
PG = Path(os.environ.get("PG_BIN", r"C:\Program Files\PostgreSQL\18\bin"))
PORT = "55433"


def run(*args, **kwargs):
    subprocess.run([str(a) for a in args], check=True, cwd=ROOT, **kwargs)


def main():
    LOCAL.mkdir(exist_ok=True)
    password_file = LOCAL / "panel-db-password.txt"
    cluster = LOCAL / "panel-pgdata"
    if not cluster.exists():
        password_file.write_text(secrets.token_hex(24), encoding="utf-8")
        run(
            PG / "initdb.exe",
            "-D",
            cluster,
            "-U",
            "jordy_panel",
            "-A",
            "scram-sha-256",
            f"--pwfile={password_file}",
            "--encoding=UTF8",
        )
    if not password_file.exists():
        raise RuntimeError("Local database password missing. Do not recreate an existing cluster.")
    password = password_file.read_text(encoding="utf-8").strip()
    status = subprocess.run(
        [str(PG / "pg_ctl.exe"), "-D", str(cluster), "status"], capture_output=True
    )
    if status.returncode:
        run(
            PG / "pg_ctl.exe",
            "-D",
            cluster,
            "-l",
            LOCAL / "panel-postgres.log",
            "-o",
            f"-p {PORT} -h 127.0.0.1",
            "start",
        )
    import psycopg

    with psycopg.connect(
        host="127.0.0.1",
        port=PORT,
        user="jordy_panel",
        password=password,
        dbname="postgres",
        autocommit=True,
    ) as conn:
        for name in ["jordy_panel", "jordy_panel_test"]:
            if not conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,)).fetchone():
                conn.execute(
                    psycopg.sql.SQL("CREATE DATABASE {}").format(psycopg.sql.Identifier(name))
                )
    env_file = ROOT / ".env"
    if not env_file.exists():
        env_file.write_text(
            f"DATABASE_URL=postgresql+psycopg://jordy_panel:{password}@127.0.0.1:{PORT}/jordy_panel\n"
            f"ADMIN_API_KEY={secrets.token_urlsafe(48)}\n"
            "STUDIO_TIMEZONE=America/Mexico_City\nLOCAL_PANEL_ACCESS=true\n"
            "PANEL_ORIGIN=http://127.0.0.1:8000\n",
            encoding="utf-8",
        )
    run(ROOT / ".venv/Scripts/alembic.exe", "upgrade", "head")
    print("Panel database ready. Credentials remain in ignored local files.")


if __name__ == "__main__":
    main()
