"""Private Telegram worker. Run separately from the FastAPI server."""

import logging
import re
import sys
import time
from pathlib import Path
from typing import Annotated

import httpx
from pydantic import Field, SecretStr, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict, SettingsError

ROOT = Path(__file__).resolve().parents[2]
UserID = Annotated[int, Field(strict=True, gt=0, lt=2**52)]
REPLIES = {"/start": "¡Hola, Jordy! El bot está listo.", "/ping": "pong"}


class TelegramSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="TELEGRAM_",
        env_file=ROOT / ".env.telegram",
        env_file_encoding="utf-8-sig",
        extra="ignore",
        hide_input_in_errors=True,
    )
    bot_token: SecretStr
    allowed_user_ids: frozenset[UserID] = frozenset()

    @field_validator("bot_token")
    @classmethod
    def valid_token(cls, value: SecretStr) -> SecretStr:
        if not re.fullmatch(r"[0-9]+:[A-Za-z0-9_-]+", value.get_secret_value()):
            raise ValueError("Token no válido")
        return value


def reply_for(update: dict, allowed: frozenset[int]) -> tuple[int, str] | None:
    msg = update.get("message")
    if not isinstance(msg, dict):
        return None
    sender, chat, text = msg.get("from"), msg.get("chat"), msg.get("text")
    if not isinstance(sender, dict) or not isinstance(chat, dict) or not isinstance(text, str):
        return None
    uid = sender.get("id")
    if (
        type(uid) is not int
        or uid not in allowed
        or sender.get("is_bot") is not False
        or chat.get("type") != "private"
        or type(chat.get("id")) is not int
        or chat["id"] != uid
    ):
        return None
    reply = REPLIES.get(text.strip())
    return (uid, reply) if reply else None


class ApiFailure(Exception):
    def __init__(self, status: int, delay: int = 5):
        self.status = status
        self.delay = delay
        super().__init__(f"Error de Telegram ({status})")


def call(client: httpx.Client, method: str, **params):
    # Never propagate raw HTTP exceptions: their URL contains the token.
    try:
        response = client.post(method, json=params)
    except httpx.RequestError:
        raise ApiFailure(503) from None
    try:
        data = response.json()
    except ValueError:
        data = None
    if response.is_success and isinstance(data, dict) and data.get("ok") is True:
        return data.get("result")
    status = response.status_code if not response.is_success else 502
    details = data.get("parameters") if isinstance(data, dict) else None
    delay = details.get("retry_after") if isinstance(details, dict) else None
    raise ApiFailure(status, delay if type(delay) is int and delay > 0 else 5)


def poll(client: httpx.Client, allowed: frozenset[int], sleep=time.sleep):
    offset = 0
    while True:
        try:
            batch = call(
                client, "getUpdates", offset=offset, timeout=30, allowed_updates=["message"]
            )
            if not isinstance(batch, list):
                raise ApiFailure(502)
            for update in batch:
                if not isinstance(update, dict) or type(update.get("update_id")) is not int:
                    raise ApiFailure(502)
                reply = reply_for(update, allowed)
                if reply:
                    try:
                        call(client, "sendMessage", chat_id=reply[0], text=reply[1])
                    except ApiFailure as exc:
                        if exc.status not in (400, 403):
                            raise
                        print("Respuesta rechazada; se omite ese mensaje.", file=sys.stderr)
                offset = update["update_id"] + 1
        except ApiFailure as exc:
            if exc.status != 429 and exc.status < 500:
                raise
            print("Telegram no disponible; se reintentará.", file=sys.stderr)
            sleep(exc.delay)


def main() -> int:
    try:
        settings = TelegramSettings()
    except (ValidationError, SettingsError):
        print("Revisa TELEGRAM_BOT_TOKEN y TELEGRAM_ALLOWED_USER_IDS.", file=sys.stderr)
        return 2
    if not settings.allowed_user_ids:
        print("La allowlist está vacía. No se inicia el bot.", file=sys.stderr)
        return 2
    # httpx's INFO request log includes the full Telegram URL.
    for name in ("httpx", "httpcore"):
        logging.getLogger(name).setLevel(logging.WARNING)
    token = settings.bot_token.get_secret_value()
    try:
        with httpx.Client(
            base_url=f"https://api.telegram.org/bot{token}/", timeout=40, trust_env=False
        ) as client:
            poll(client, settings.allowed_user_ids)
    except ApiFailure as exc:
        print(f"{exc}. Revisa el token, el webhook y otras instancias.", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
