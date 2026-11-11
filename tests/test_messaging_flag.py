"""WhatsApp and the commercial follow-up stay in the codebase but are switched off by default."""

from datetime import UTC, datetime

import pytest

from jordy.admin_reads import AdminReads
from jordy.config import settings
from jordy.telegram.commands import pending

PATHS = [
    "/api/messaging/conversations",
    "/api/messaging/config",
    "/api/commercial/schedule",
    "/api/commercial/plans",
]


def test_flag_defaults_to_off(client):
    assert settings().messaging_enabled is False


@pytest.mark.parametrize("path", PATHS)
def test_disabled_routes_do_not_exist(client, path):
    assert client.get(path).status_code == 404
    # Indistinguishable from an unknown path, and decided before authentication.
    client.headers.pop("X-Admin-Key")
    assert client.get(path).status_code == 404
    assert client.get("/api/bookings").status_code == 401


def test_enabled_routes_require_authentication_again(client, messaging_enabled):
    assert client.get("/api/commercial/schedule").status_code == 200
    client.headers.pop("X-Admin-Key")
    assert client.get("/api/commercial/schedule").status_code == 401


def test_telegram_pending_omits_follow_ups_when_disabled(empty_database):
    clock = lambda: datetime(2026, 7, 1, tzinfo=UTC)  # noqa: E731
    off = AdminReads(empty_database, "America/Mexico_City", clock=clock)
    assert off.pending().conversations is None
    text = pending(off, [])
    assert "Sin solicitudes pendientes." in text
    assert "seguimiento" not in text.lower() and "conversaciones" not in text.lower()

    on = AdminReads(empty_database, "America/Mexico_City", clock=clock, messaging_enabled=True)
    assert on.pending().conversations == ()
    assert "Sin seguimientos pendientes." in pending(on, [])
