"""Private Telegram worker. Run separately from the FastAPI server."""

import logging
import sys

import httpx
from pydantic import ValidationError
from pydantic_settings import SettingsError

from jordy.telegram.config import TelegramSettings
from jordy.telegram.transport import ApiFailure, poll


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
