import hashlib
import os
import re
import secrets
import socket
import subprocess
from pathlib import Path
from uuid import uuid4

import httpx
import psycopg
from test_api import request_booking
from test_api import setup as booking_inputs
from test_crm_documents import pdf_bytes, upload

ROOT = Path(__file__).resolve().parents[1]
CHECK_IMAGE = """
import os
from pathlib import Path

assert os.getuid() == 10001
private_env = {"ADMIN_API_KEY", "PGPASSWORD", "POSTGRES_PASSWORD", "DATABASE_URL"}
assert not private_env.intersection(os.environ)
assert not any(Path("/app").rglob(".env*"))
assert not any(Path("/app", name).exists() for name in (".git", ".local", "Photos", "website"))
"""


def test_compose_foundation(tmp_path):
    project = "jordy-test-" + uuid4().hex
    env_file = tmp_path / "empty.env"
    env_file.touch()
    with socket.socket() as panel, socket.socket() as db:
        panel.bind(("127.0.0.1", 0))
        db.bind(("127.0.0.1", 0))
        panel_port, db_port = panel.getsockname()[1], db.getsockname()[1]
    env = {
        **os.environ,
        "POSTGRES_PASSWORD": secrets.token_hex(32),
        "JORDY_APP_PASSWORD": secrets.token_hex(32),
        "ADMIN_API_KEY": secrets.token_hex(32),
        "PANEL_PORT": str(panel_port),
        "POSTGRES_HOST_PORT": str(db_port),
        "STUDIO_TIMEZONE": "America/Mexico_City",
        "COMPOSE_PROFILES": "",
    }
    cli = ["docker", "compose", "-f", "compose.yaml", "-p", project, "--env-file", str(env_file)]

    def compose(*args):
        subprocess.run([*cli, *args], cwd=ROOT, env=env, check=True)

    def db_connect(user, password):
        return psycopg.connect(
            host="127.0.0.1",
            port=db_port,
            dbname="jordy",
            user=user,
            password=password,
            connect_timeout=5,
        )

    url = f"http://127.0.0.1:{panel_port}"
    compose("--profile", "tools", "config", "--quiet")
    compose("build", "api")
    try:
        compose("up", "-d", "api")
        compose("up", "-d", "--wait", "--wait-timeout", "90", "db")
        compose("run", "--rm", "migrate", "current")
        with db_connect("jordy", env["POSTGRES_PASSWORD"]) as conn:
            assert conn.execute("SELECT to_regclass('public.alembic_version')").fetchone() == (
                None,
            )
        compose("run", "--rm", "migrate", "upgrade")
        compose("run", "--rm", "migrate", "upgrade")
        compose("up", "-d", "--wait", "--wait-timeout", "90")
        with db_connect("jordy_app", env["JORDY_APP_PASSWORD"]) as conn:
            assert conn.execute(
                "SELECT NOT rolsuper FROM pg_roles WHERE rolname=current_user"
            ).fetchone()[0]
            assert not conn.execute("SELECT has_schema_privilege('public','CREATE')").fetchone()[0]
            assert not conn.execute(
                "SELECT has_table_privilege('alembic_version','UPDATE')"
            ).fetchone()[0]

        subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "--network",
                "none",
                f"{project}-app:local",
                "python",
                "-c",
                CHECK_IMAGE,
            ],
            check=True,
            env=env,
        )
        with httpx.Client(base_url=url, trust_env=False) as client:
            assert client.get("/health/ready").json()["status"] == "ready"
            html = client.get("/").raise_for_status().text
            asset = re.search(r'<script[^>]+src="(/assets/[^"]+\.js)"', html)
            assert asset and client.get(asset[1]).status_code == 200
            assert client.get("/api/customers").status_code == 401
            assert client.post("/auth/local", headers={"Origin": url}).status_code == 403
            client.headers["X-Admin-Key"] = env["ADMIN_API_KEY"]
            _, _, data = booking_inputs(client)
            booking = request_booking(client, data)
            original = pdf_bytes()
            doc = upload(client, booking["id"], original).raise_for_status().json()
            assert doc["sha256"] == hashlib.sha256(original).hexdigest()
            assert client.get(f"/{doc['id'].replace('-', '')}.bin").status_code == 404

        compose("down")
        compose("up", "-d", "--wait", "--wait-timeout", "90")
        with httpx.Client(
            base_url=url, headers={"X-Admin-Key": env["ADMIN_API_KEY"]}, trust_env=False
        ) as client:
            assert (
                client.get(f"/api/bookings/{booking['id']}").json()["status"] == "pending_approval"
            )
            assert (
                client.get(f"/api/documents/{doc['id']}/download").raise_for_status().content
                == original
            )
    finally:
        compose("down", "--volumes")
        subprocess.run(["docker", "image", "rm", f"{project}-app:local"], check=True, env=env)
