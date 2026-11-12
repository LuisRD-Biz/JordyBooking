import subprocess
import sys
from contextlib import nullcontext
from pathlib import Path

import pytest

from jordy.telegram import worker
from jordy.telegram.config import TelegramSettings
from jordy.telegram.poller_lock import single_poller


def test_poller_lock_excludes_another_process_and_releases(tmp_path):
    code = """
from pathlib import Path
import sys
from jordy.telegram.poller_lock import PollerLockError, single_poller
try:
    with single_poller('123', Path(sys.argv[1])):
        pass
except PollerLockError:
    sys.exit(42)
"""
    cmd = [sys.executable, "-c", code, str(tmp_path)]
    backend = Path(__file__).resolve().parents[1] / "backend"
    with single_poller("123", tmp_path):
        assert subprocess.run(cmd, cwd=backend, timeout=20).returncode == 42
    assert subprocess.run(cmd, cwd=backend, timeout=20).returncode == 0


@pytest.mark.parametrize(
    "dsn,enabled",
    [
        ("postgresql+psycopg://tester:private-marker@localhost/worker_test", True),
        ("postgresql://tester:private-marker@localhost/worker_test", True),
        ("invalid-private-marker", False),
    ],
)
def test_worker_loads_root_settings_without_database_connection(
    tmp_path, monkeypatch, capsys, dsn, enabled
):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("STUDIO_TIMEZONE", raising=False)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:synthetic")
    monkeypatch.setenv("TELEGRAM_ALLOWED_USER_IDS", "[7]")
    monkeypatch.setattr(worker, "ROOT", tmp_path)
    monkeypatch.setattr(worker, "TelegramSettings", lambda: TelegramSettings(_env_file=None))
    monkeypatch.setattr(worker, "single_poller", lambda bot_id: single_poller(bot_id, tmp_path))
    monkeypatch.setattr(worker.httpx, "Client", lambda **_: nullcontext(None))
    (tmp_path / ".env").write_text(f"DATABASE_URL={dsn}\nSTUDIO_TIMEZONE=Asia/Tokyo", "utf-8")
    services = []
    monkeypatch.setattr(worker, "poll", lambda c, allowed, reads: services.append(reads))
    assert worker.main() == 0
    assert len(services) == 1
    if enabled:
        assert str(services[0].zone) == "Asia/Tokyo"
    else:
        assert services[0] is None
    logs = capsys.readouterr().err
    assert "private-marker" not in logs and "123:synthetic" not in logs
