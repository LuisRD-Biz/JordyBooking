from fastapi.testclient import TestClient

from jordy.auth import COOKIE
from jordy.config import settings
from jordy.main import app

KEY = "test-only-admin-key-with-at-least-32-chars"
ORIGIN = "http://127.0.0.1:8000"


def test_browser_login_cookie_and_csrf(client):
    client.headers.pop("X-Admin-Key")
    assert client.get("/api/bookings").status_code == 401
    assert client.post("/auth/login", json={"key": KEY}).status_code == 403
    response = client.post("/auth/login", json={"key": KEY}, headers={"Origin": ORIGIN})
    assert response.status_code == 200
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=strict" in response.headers["set-cookie"]
    assert KEY not in response.text
    assert client.get("/api/bookings").status_code == 200
    data = {"name": "Browser Test", "contact": "synthetic@example.invalid"}
    assert client.post("/api/customers", json=data).status_code == 403
    assert (
        client.post(
            "/api/customers", json=data, headers={"Origin": "https://untrusted.invalid"}
        ).status_code
        == 403
    )
    assert client.post("/api/customers", json=data, headers={"Origin": ORIGIN}).status_code == 201
    assert client.post("/auth/logout", headers={"Origin": ORIGIN}).status_code == 200
    assert client.get("/api/bookings").status_code == 401


def test_forged_cookie_is_rejected(client):
    client.headers.pop("X-Admin-Key")
    client.cookies.set(COOKIE, "9999999999.fake.forged")
    assert client.get("/api/customers").status_code == 401


def test_local_mode_requires_loopback_origin_and_explicit_enable(client, monkeypatch):
    monkeypatch.setattr(settings(), "local_panel_access", True)
    with TestClient(app, base_url=ORIGIN, client=("127.0.0.1", 12345)) as browser:
        assert browser.post("/auth/local").status_code == 403
        assert (
            browser.post("/auth/local", headers={"Origin": "https://evil.invalid"}).status_code
            == 403
        )
        assert browser.post("/auth/local", headers={"Origin": ORIGIN}).status_code == 200
        monkeypatch.setattr(settings(), "local_panel_access", False)
        assert browser.post("/auth/local", headers={"Origin": ORIGIN}).status_code == 403
    monkeypatch.setattr(settings(), "local_panel_access", True)
    with TestClient(app, base_url=ORIGIN, client=("192.0.2.1", 12345)) as browser:
        assert browser.post("/auth/local", headers={"Origin": ORIGIN}).status_code == 403


def test_customer_edit_and_contract_read(client):
    response = client.post("/api/customers", json={"name": "Original", "contact": "test"})
    identity = response.json()["id"]
    assert (
        client.put(
            f"/api/customers/{identity}",
            json={"name": "Updated", "contact": "updated@example.invalid"},
        ).status_code
        == 200
    )
    assert client.get("/api/audit").status_code == 200
    assert client.get("/api/bookings/2147483647/contract").status_code == 404


def test_resource_edit_preserves_booked_capabilities(client):
    from test_api import approve, request_booking, setup

    resource_id, package, data = setup(client)
    booking = request_booking(client, data)
    assert approve(client, booking["id"]).status_code == 200
    assert (
        client.put(
            f"/api/resources/{resource_id}",
            json={"name": "Renamed", "kind": "staff", "capabilities": ["unrelated"]},
        ).status_code
        == 409
    )
    assert (
        client.put(
            f"/api/resources/{resource_id}",
            json={
                "name": "Renamed",
                "kind": "staff",
                "capabilities": [package["requirements"][0]["capability"], "assistant"],
            },
        ).status_code
        == 200
    )
