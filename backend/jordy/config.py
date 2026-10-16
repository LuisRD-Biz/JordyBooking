from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str
    admin_api_key: SecretStr = Field(min_length=32)
    studio_timezone: str = "America/Mexico_City"
    local_panel_access: bool = False
    panel_origin: str = "http://127.0.0.1:8000"


@lru_cache
def settings() -> Settings:
    return Settings()
