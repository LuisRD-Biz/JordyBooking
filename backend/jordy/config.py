from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class StudioDatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str
    studio_timezone: str = "America/Mexico_City"
    # WhatsApp inbox and the commercial follow-up built on it. Off: their HTTP routes answer
    # 404, the summary scheduler does not start and Telegram omits conversation follow-ups.
    # The code and the tables stay in place, so turning it back on needs no migration.
    messaging_enabled: bool = False


class Settings(StudioDatabaseSettings):
    admin_api_key: SecretStr = Field(min_length=32)
    # X-Admin-Key header access for scripts and /docs. Disable on Internet-facing deployments.
    admin_key_header: bool = True
    # Header carrying the real client IP, set only when a trusted proxy is the sole entry point
    # (for example "CF-Connecting-IP" behind Cloudflare Tunnel). Otherwise use the socket peer.
    client_ip_header: str | None = None
    local_panel_access: bool = False
    panel_origin: str = "http://127.0.0.1:8000"
    document_root: Path = Path(__file__).resolve().parents[2] / ".local" / "documents"
    document_max_bytes: int = Field(default=10 * 1024 * 1024, ge=1024, le=50 * 1024 * 1024)


@lru_cache
def settings() -> Settings:
    return Settings()
