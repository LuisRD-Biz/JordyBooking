from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str
    admin_api_key: SecretStr = Field(min_length=32)
    studio_timezone: str = "America/Mexico_City"
    local_panel_access: bool = False
    panel_origin: str = "http://127.0.0.1:8000"
    document_root: Path = Path(__file__).resolve().parents[2] / ".local" / "documents"
    document_max_bytes: int = Field(default=10 * 1024 * 1024, ge=1024, le=50 * 1024 * 1024)


@lru_cache
def settings() -> Settings:
    return Settings()
