import json

import httpx
import pytest
from pydantic import ValidationError

from jordy import telegram

UID = 2**40 + 17
ALLOWED = frozenset({UID})


def incoming(text="/ping", uid=UID, **overrides):
    msg = {
        "from": {"id": uid, "is_bot": False},
        "chat": {"id": uid, "type": "private"},
        "text": text,
    }
    return {"update_id": 10, "message": {**msg, **overrides}}


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("/ping", "pong"),
        ("/start", "¡Hola, Jordy! El bot está listo."),
    ],
)
def test_commands(command, expected):
    assert telegram.reply_for(incoming(command), ALLOWED) == (UID, expected)


@pytest.mark.parametrize(
    "update",
    [
        incoming(uid=3),
        incoming(chat={"id": -99, "type": "group"}),
        incoming(chat={"id": 33, "type": "private"}),
        incoming(uid=str(UID)),
        incoming(**{"from": {"id": UID, "is_bot": True}}),
        incoming("/unknown"),
        {"edited_message": incoming()["message"]},
        {"message": None},
        incoming(text=None),
    ],
)
def test_silent_denial(update):
    assert telegram.reply_for(update, ALLOWED) is None


@pytest.mark.parametrize("value", ["true", '"123"', "0", "-9", "1.5"])
def test_config_rejects_non_ids(monkeypatch, value):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "1:dummy")
    monkeypatch.setenv("TELEGRAM_ALLOWED_USER_IDS", f"[{value}]")
    with pytest.raises(ValidationError):
        telegram.TelegramSettings(_env_file=None)


def test_launcher_empty_allowlist(monkeypatch, capsys):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "1:dummy")
    monkeypatch.setenv("TELEGRAM_ALLOWED_USER_IDS", "[]")
    monkeypatch.setattr(httpx, "Client", lambda **kw: pytest.fail("network client created"))
    assert telegram.main() == 2
    assert "1:dummy" not in capsys.readouterr().err


def test_poll_handles_unauthorized_retry_and_cursor():
    requests = []
    delays = []
    batch = [incoming(uid=77), {**incoming(), "update_id": 11}]
    responses = iter(
        [
            (429, {"ok": False, "parameters": {"retry_after": 9}}),
            (200, {"ok": True, "result": batch}),
            (200, {"ok": True, "result": {}}),
            (409, {"ok": False}),  # Another poller/webhook: stop.
        ]
    )

    def fake(request):
        requests.append((request.url.path, json.loads(request.content)))
        code, body = next(responses)
        return httpx.Response(code, json=body)

    with httpx.Client(base_url="https://mock.invalid/", transport=httpx.MockTransport(fake)) as c:
        with pytest.raises(telegram.ApiFailure, match="409"):
            telegram.poll(c, ALLOWED, sleep=delays.append)
    assert delays == [9]
    assert [p for p, _ in requests] == ["/getUpdates", "/getUpdates", "/sendMessage", "/getUpdates"]
    assert requests[0][1] == {"offset": 0, "timeout": 30, "allowed_updates": ["message"]}
    assert requests[2][1] == {"chat_id": UID, "text": "pong"}
    assert requests[3][1]["offset"] == 12


def test_transport_failure_hides_url():
    def fail(request):
        raise httpx.ReadTimeout(str(request.url))

    with httpx.Client(
        base_url="https://mock.invalid/bot1:dummy/", transport=httpx.MockTransport(fail)
    ) as c:
        with pytest.raises(telegram.ApiFailure) as exc:
            telegram.call(c, "getUpdates")
    assert exc.value.status == 503
    assert "dummy" not in str(exc.value)
