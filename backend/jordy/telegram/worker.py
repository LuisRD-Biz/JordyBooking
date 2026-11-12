import logging
import sys
from contextlib import ExitStack
from zoneinfo import ZoneInfoNotFoundError

import httpx
from pydantic import ValidationError
from pydantic_settings import SettingsError
from sqlalchemy.exc import SQLAlchemyError

from jordy.admin_queries import build_read_engine
from jordy.admin_reads import AdminReads
from jordy.config import StudioDatabaseSettings
from jordy.telegram.config import ROOT, TelegramSettings
from jordy.telegram.poller_lock import PollerLockError, single_poller
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
    for name in ("httpx", "httpcore"):
        logging.getLogger(name).setLevel(logging.WARNING)
    token = settings.bot_token.get_secret_value()
    try:
        with ExitStack() as stack:
            stack.enter_context(single_poller(token.split(":", 1)[0]))
            reads = None
            try:
                db = StudioDatabaseSettings(_env_file=ROOT / ".env", _env_file_encoding="utf-8-sig")
                engine = build_read_engine(db.database_url)
                stack.callback(engine.dispose)
                reads = AdminReads(
                    engine, db.studio_timezone, messaging_enabled=db.messaging_enabled
                )
            except (SettingsError, SQLAlchemyError, ValueError, ZoneInfoNotFoundError):
                print(
                    "Consultas inactivas. Revisa DATABASE_URL y STUDIO_TIMEZONE.", file=sys.stderr
                )
            client = stack.enter_context(
                httpx.Client(
                    base_url=f"https://api.telegram.org/bot{token}/", timeout=40, trust_env=False
                )
            )
            poll(client, settings.allowed_user_ids, reads=reads)
    except PollerLockError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except ApiFailure as exc:
        print(f"{exc}. Revisa el token, el webhook y otras instancias.", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        pass
    return 0
