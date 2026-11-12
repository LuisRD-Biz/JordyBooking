import os
import secrets
import socket
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import psycopg

ROOT = Path(__file__).resolve().parents[1]
PG_BIN = Path(os.environ.get("PG_BIN", r"C:\Program Files\PostgreSQL\18\bin"))


def main(args):
    if not (PG_BIN / "initdb.exe").is_file():
        raise SystemExit("Configura PG_BIN con la carpeta bin de PostgreSQL.")
    with TemporaryDirectory(prefix="jordy-pytest-") as scratch:
        root = Path(scratch)
        cluster = root / "cluster"
        password = secrets.token_hex(32)
        password_file = root / "pw"
        password_file.write_text(password, encoding="ascii")
        subprocess.run(
            [
                PG_BIN / "initdb.exe",
                "-D",
                cluster,
                "-U",
                "test",
                "-A",
                "scram-sha-256",
                f"--pwfile={password_file}",
                "--encoding=UTF8",
                "--locale=C",
            ],
            check=True,
        )
        password_file.unlink()
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        control = [PG_BIN / "pg_ctl.exe", "-D", cluster, "-w"]
        subprocess.run(
            [*control, "-l", root / "pg.log", "-o", f"-h 127.0.0.1 -p {port}", "start"],
            check=True,
        )
        try:
            with psycopg.connect(
                host="127.0.0.1",
                port=port,
                user="test",
                password=password,
                dbname="postgres",
                autocommit=True,
            ) as conn:
                conn.execute("CREATE DATABASE jordy_test")
            url = f"postgresql+psycopg://test:{password}@127.0.0.1:{port}/jordy_test"
            env = {
                **os.environ,
                "DATABASE_URL": url,
                "TEST_DATABASE_URL": url,
                "ADMIN_API_KEY": "test-only-admin-key-with-at-least-32-chars",
                "DOCUMENT_ROOT": str(root / "documents"),
                "STUDIO_TIMEZONE": "America/Mexico_City",
                "LOCAL_PANEL_ACCESS": "false",
                "WHATSAPP_SEND_ENABLED": "false",
            }
            return subprocess.run(
                [sys.executable, "-m", "pytest", *args], cwd=ROOT, env=env
            ).returncode
        finally:
            subprocess.run([*control, "-m", "fast", "stop"], check=True)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
