"""Verify persisted bytes across actual server processes, in the isolated test schema."""

import os
import socket
import subprocess
import sys
import time

import httpx
from test_api import request_booking, setup
from test_crm_documents import pdf_bytes, upload

from jordy.config import settings


def test_download_survives_actual_server_restart(client, database, tmp_path, monkeypatch):
    root = tmp_path / "private"
    monkeypatch.setattr(settings(), "document_root", root)
    _, _, data = setup(client, "event")
    booking = request_booking(client, data)
    content = pdf_bytes()
    doc = upload(client, booking["id"], content).json()
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env = {
        **os.environ,
        "DATABASE_URL": database.url.render_as_string(hide_password=False),
        "DOCUMENT_ROOT": str(root),
        "LOCAL_PANEL_ACCESS": "false",
    }
    for attempt in range(2):
        with (tmp_path / f"server-{attempt}.log").open("w") as log:
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "jordy.main:app",
                    "--app-dir",
                    "backend",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(port),
                ],
                env=env,
                stdout=log,
                stderr=log,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            try:
                with httpx.Client(
                    base_url=f"http://127.0.0.1:{port}", trust_env=False, timeout=2
                ) as http:
                    for _ in range(80):
                        assert process.poll() is None, "Test server exited"
                        try:
                            if http.get("/health").status_code == 200:
                                break
                        except httpx.ConnectError:
                            pass
                        time.sleep(0.1)
                    response = http.get(
                        f"/api/documents/{doc['id']}/download",
                        headers={
                            "X-Admin-Key": settings().admin_api_key.get_secret_value(),
                        },
                    )
                    assert response.status_code == 200 and response.content == content
                    assert http.get(f"/api/documents/{doc['id']}/download").status_code == 401
            finally:
                if os.name == "nt":
                    subprocess.run(
                        ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                        capture_output=True,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                    )
                else:
                    process.terminate()
                process.wait(timeout=10)
