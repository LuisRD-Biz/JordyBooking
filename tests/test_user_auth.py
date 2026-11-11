from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from jordy import accounts
from jordy.auth import COOKIE, GENERIC_LOGIN_ERROR
from jordy.config import settings

ORIGIN = "http://127.0.0.1:8000"
PASSWORD = "luz-de-tarde-en-el-jardin-2026"


@pytest.fixture
def browser(client, monkeypatch):
    """Cookie-only client with its own synthetic client IP, isolated from other tests."""
    client.headers.pop("X-Admin-Key", None)
    monkeypatch.setattr(settings(), "client_ip_header", "X-Test-Client-IP")
    client.headers["X-Test-Client-IP"] = f"198.51.100.{uuid4().int % 250 + 1}"
    client.headers["Origin"] = ORIGIN
    return client


def make_user(database, role="admin", password=PASSWORD, active=True):
    email = f"user-{uuid4().hex[:10]}@example.invalid"
    with Session(database) as session, session.begin():
        user = accounts.create_user(session, email, "Synthetic User", password, role)
        user.is_active = active
    return email


def login(client, email, password=PASSWORD, **kwargs):
    return client.post("/auth/login", json={"email": email, "password": password}, **kwargs)


def test_login_logout_and_server_side_revocation(browser, database):
    email = make_user(database)
    assert browser.get("/api/bookings").status_code == 401
    assert login(browser, email, headers={"Origin": "https://evil.invalid"}).status_code == 403

    response = login(browser, email.upper())  # e-mail is case-insensitive
    assert response.status_code == 200
    cookie = response.headers["set-cookie"]
    assert cookie.startswith(f"{COOKIE}=")
    assert "HttpOnly" in cookie and "SameSite=strict" in cookie
    assert PASSWORD not in response.text
    assert response.json()["email"] == email
    assert browser.get("/auth/session").json()["role"] == "admin"
    assert browser.get("/api/bookings").status_code == 200

    data = {"name": "Login Test", "contact": f"{uuid4().hex[:8]}@example.invalid"}
    assert browser.post("/api/customers", json=data, headers={"Origin": ""}).status_code == 403
    assert browser.post("/api/customers", json=data).status_code == 201

    token = browser.cookies.get(COOKIE)
    with Session(database) as session:
        stored = session.scalars(select(accounts.UserSession.token_hash)).all()
    assert token not in stored and accounts.hash_token(token) in stored

    assert browser.post("/auth/logout").status_code == 200
    assert browser.get("/api/bookings").status_code == 401
    browser.cookies.set(COOKIE, token)  # a copied cookie is useless after logout
    assert browser.get("/api/bookings").status_code == 401


def test_unknown_email_and_wrong_password_look_identical(browser, database):
    email = make_user(database)
    wrong = login(browser, email, "not-the-password-at-all")
    unknown = login(browser, f"nobody-{uuid4().hex[:8]}@example.invalid", "whatever-password")
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json() == {"detail": GENERIC_LOGIN_ERROR}


def test_lockout_after_five_failures_even_with_correct_password(browser, database):
    email = make_user(database)
    for _ in range(accounts.MAX_FAILURES_PER_EMAIL):
        assert login(browser, email, "wrong-password-123").status_code == 401
    locked = login(browser, email)
    assert locked.status_code == 429
    assert locked.headers["retry-after"] == "900"
    # Moving to another IP does not help: the e-mail itself is throttled.
    browser.headers["X-Test-Client-IP"] = "203.0.113.77"
    assert login(browser, email).status_code == 429
    # Unknown e-mails lock the same way, so lockouts do not reveal real accounts.
    ghost = f"ghost-{uuid4().hex[:8]}@example.invalid"
    for _ in range(accounts.MAX_FAILURES_PER_EMAIL):
        assert login(browser, ghost, "wrong-password-123").status_code == 401
    assert login(browser, ghost, "wrong-password-123").status_code == 429


def test_ip_is_throttled_across_many_emails(browser, database):
    email = make_user(database)
    for _ in range(accounts.MAX_FAILURES_PER_IP):
        target = f"spray-{uuid4().hex[:8]}@example.invalid"
        assert login(browser, target, "Password123!Password").status_code == 401
    assert login(browser, email).status_code == 429


def test_lock_expires_after_window(browser, database):
    email = make_user(database)
    for _ in range(accounts.MAX_FAILURES_PER_EMAIL):
        login(browser, email, "wrong-password-123")
    assert login(browser, email).status_code == 429
    with Session(database) as session, session.begin():
        session.execute(
            update(accounts.LoginAttempt)
            .where(accounts.LoginAttempt.email == email)
            .values(created_at=accounts.now() - accounts.ATTEMPT_WINDOW - timedelta(minutes=1))
        )
    assert login(browser, email).status_code == 200


def test_session_fixation_forged_and_idle_sessions_are_rejected(browser, database):
    email = make_user(database)
    browser.cookies.set(COOKIE, "attacker-chosen-session-value")
    assert browser.get("/api/bookings").status_code == 401
    response = login(browser, email)
    assert response.status_code == 200
    token = response.cookies[COOKIE]
    assert token != "attacker-chosen-session-value"
    browser.cookies.clear()
    browser.cookies.set(COOKIE, "attacker-chosen-session-value")
    assert browser.get("/api/bookings").status_code == 401  # the planted value never works
    browser.cookies.clear()
    browser.cookies.set(COOKIE, token)
    assert browser.get("/api/bookings").status_code == 200
    with Session(database) as session, session.begin():
        session.execute(
            update(accounts.UserSession)
            .where(accounts.UserSession.token_hash == accounts.hash_token(token))
            .values(last_seen_at=accounts.now() - accounts.SESSION_IDLE - timedelta(minutes=1))
        )
    assert browser.get("/api/bookings").status_code == 401


def test_disabled_accounts_and_non_admin_roles(browser, database):
    disabled = make_user(database, active=False)
    assert login(browser, disabled).status_code == 401

    email = make_user(database)
    assert login(browser, email).status_code == 200
    with Session(database) as session, session.begin():
        user = session.scalar(select(accounts.User).where(accounts.User.email == email))
        user.is_active = False
    assert browser.get("/api/bookings").status_code == 401

    employee = make_user(database, role="employee")
    assert login(browser, employee).status_code == 200
    assert browser.get("/api/bookings").status_code == 403


def test_password_change_rotates_other_sessions(browser, database):
    email = make_user(database)
    assert login(browser, email).status_code == 200
    first = browser.cookies.get(COOKIE)
    browser.cookies.clear()
    assert login(browser, email).status_code == 200

    new = "otra-frase-mucho-mas-larga-2027"
    change = "/auth/password"
    bad = browser.post(change, json={"current_password": "nope", "new_password": new})
    assert bad.status_code == 401
    weak = browser.post(change, json={"current_password": PASSWORD, "new_password": "short"})
    assert weak.status_code == 422
    ok = browser.post(change, json={"current_password": PASSWORD, "new_password": new})
    assert ok.status_code == 200
    assert browser.get("/api/bookings").status_code == 200  # this session survives

    current = browser.cookies.get(COOKIE)
    browser.cookies.set(COOKIE, first)
    assert browser.get("/api/bookings").status_code == 401  # the other one was revoked
    browser.cookies.set(COOKIE, current)
    assert browser.post("/auth/logout").status_code == 200
    assert login(browser, email).status_code == 401
    assert login(browser, email, new).status_code == 200


def test_admin_key_header_can_be_disabled(client, monkeypatch):
    assert client.get("/api/bookings").status_code == 200
    monkeypatch.setattr(settings(), "admin_key_header", False)
    assert client.get("/api/bookings").status_code == 401


def test_security_headers(browser):
    response = browser.get("/auth/config")
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["method"] == "password"


def test_secure_cookie_name_on_https(browser, database, monkeypatch):
    email = make_user(database)
    monkeypatch.setattr(settings(), "panel_origin", "https://admin.example.invalid")
    browser.headers["Origin"] = "https://admin.example.invalid"
    cookie = login(browser, email).headers["set-cookie"]
    assert cookie.startswith("__Host-jordy_session=")
    assert "Secure" in cookie and "Domain" not in cookie


def test_password_policy():
    with pytest.raises(accounts.PasswordRejected):
        accounts.validate_password("corta")
    with pytest.raises(accounts.PasswordRejected):
        accounts.validate_password("aaaaaaaaaaaaaaaa")
    with pytest.raises(accounts.PasswordRejected):
        accounts.validate_password("jordyflores-2026!!", "jordyflores@example.com")
    accounts.validate_password("caballo correcto batería grapa")


def test_manage_users_cli(database, monkeypatch, capsys):
    from jordy import manage_users

    email = f"cli-{uuid4().hex[:8]}@example.invalid"
    monkeypatch.setattr(manage_users.getpass, "getpass", lambda prompt: PASSWORD)
    manage_users.main(["create", "--email", email, "--name", "Cli Admin"])
    assert "Usuario creado" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        manage_users.main(["create", "--email", email, "--name", "Again"])
    manage_users.main(["disable", "--email", email])
    with Session(database) as session:
        user = session.scalar(select(accounts.User).where(accounts.User.email == email))
        assert not user.is_active
        assert accounts.hasher.verify(user.password_hash, PASSWORD)
