import re
from pathlib import Path
from typing import Annotated

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[3]
UserID = Annotated[int, Field(strict=True, gt=0, lt=2**52)]


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
