"""Failure/reuse tests never start or stop an operational process."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

spec = importlib.util.spec_from_file_location(
    "launcher", Path(__file__).parents[1] / "scripts/launch_panel.py"
)
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


@pytest.fixture
def launch(monkeypatch, tmp_path):
    monkeypatch.setattr(launcher, "LOCAL", tmp_path)
    monkeypatch.setattr(
        launcher, "configuration", lambda: (SimpleNamespace(port=55433), tmp_path, tmp_path)
    )
    monkeypatch.setattr(launcher, "pg_control", Mock(return_value=0))
    monkeypatch.setattr(launcher, "database_ready", Mock())
    monkeypatch.setattr(launcher.subprocess, "Popen", Mock())
    return launcher


def test_reuses_ready_server_without_spawning(launch, monkeypatch):
    monkeypatch.setattr(launch, "occupied", lambda port: True)
    monkeypatch.setattr(launch, "ready", lambda: True)
    launch.start()
    launch.subprocess.Popen.assert_not_called()
    launch.pg_control.assert_not_called()
    launch.database_ready.assert_called_once()


def test_foreign_web_port_is_never_killed(launch, monkeypatch):
    monkeypatch.setattr(launch, "occupied", lambda port: True)
    monkeypatch.setattr(launch, "ready", lambda: False)
    with pytest.raises(RuntimeError, match="8000"):
        launch.start()
    launch.subprocess.Popen.assert_not_called()
    launch.pg_control.assert_not_called()


def test_foreign_database_port_is_never_touched(launch, monkeypatch):
    monkeypatch.setattr(launch, "occupied", lambda port: port == 55433)
    launch.pg_control.return_value = 3
    with pytest.raises(RuntimeError, match="55433"):
        launch.start()
    assert launch.pg_control.call_count == 1  # status only
    launch.subprocess.Popen.assert_not_called()


def test_partial_failure_stops_only_cluster_started_here(launch, monkeypatch):
    monkeypatch.setattr(launch, "occupied", lambda port: False)
    launch.pg_control.side_effect = [3, 0, 0]
    launch.database_ready.side_effect = RuntimeError("not ready")
    with pytest.raises(RuntimeError, match="not ready"):
        launch.start()
    assert launch.pg_control.call_args.args[-1] == "stop"
    launch.subprocess.Popen.assert_not_called()


def test_missing_configuration_has_clear_error(monkeypatch, tmp_path):
    monkeypatch.setattr(launcher, "ROOT", tmp_path)
    with pytest.raises(RuntimeError, match="configuración local"):
        launcher.configuration()
    assert not list(tmp_path.iterdir())


def test_missing_frontend_has_clear_error(monkeypatch, tmp_path):
    monkeypatch.setattr(launcher, "ROOT", tmp_path)
    (tmp_path / ".env").write_text("")
    with pytest.raises(RuntimeError, match="React"):
        launcher.configuration()
