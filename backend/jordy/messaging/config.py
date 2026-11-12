import hashlib
import hmac
import json
import re
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[3]


class RecipientBinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    account_id: str = Field(pattern=r"^[0-9]{1,100}$")
    phone_number_id: str = Field(pattern=r"^[0-9]{1,100}$")
    external_contact: str = Field(min_length=1, max_length=200)
    send_recipient: str = Field(pattern=r"^[0-9]{7,15}$")


class MessagingSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(ROOT / ".env", ROOT / ".env.whatsapp"), extra="ignore"
    )
    database_url: str
    whatsapp_access_token: SecretStr = SecretStr("")
    whatsapp_phone_number_id: str = ""
    whatsapp_business_account_id: str = ""
    meta_app_secret: SecretStr = SecretStr("")
    meta_webhook_verify_token: SecretStr = SecretStr("")
    meta_graph_api_version: str = ""
    whatsapp_send_enabled: bool = False
    whatsapp_token_rotated: bool = False
    whatsapp_allowed_recipients: list[str] = Field(default_factory=list)
    whatsapp_recipient_bindings: list[RecipientBinding] = Field(default_factory=list)
    whatsapp_approved_templates: list[str] = Field(default_factory=list)
    whatsapp_max_webhook_bytes: int = Field(default=262144, ge=1024, le=1048576)

    def send_config_revision(self):
        data = self.model_dump(
            mode="json",
            exclude={
                "database_url",
                "whatsapp_access_token",
                "meta_app_secret",
                "meta_webhook_verify_token",
                "whatsapp_max_webhook_bytes",
            },
        )
        return hmac.new(
            self.whatsapp_access_token.get_secret_value().encode(),
            json.dumps(data, sort_keys=True).encode(),
            hashlib.sha256,
        ).hexdigest()

    def send_blocker_codes(self):
        codes = []
        if not self.whatsapp_send_enabled:
            codes.append("send_disabled")
        if not self.whatsapp_token_rotated:
            codes.append("token_rotation_required")
        if not self.whatsapp_access_token.get_secret_value():
            codes.append("access_token_missing")
        if not all(
            re.fullmatch(r"[0-9]{1,100}", x)
            for x in (self.whatsapp_phone_number_id, self.whatsapp_business_account_id)
        ):
            codes.append("sender_config_invalid")
        if not re.fullmatch(r"v[0-9]{1,3}\.0", self.meta_graph_api_version):
            codes.append("graph_version_invalid")
        if not self.whatsapp_allowed_recipients:
            codes.append("recipient_not_authorized")
        return codes

    def send_blockers(self):
        reasons = []
        if not self.whatsapp_send_enabled:
            reasons.append("Los envíos reales están deshabilitados.")
        if not self.whatsapp_token_rotated:
            reasons.append("Falta confirmar la sustitución del token expuesto.")
        if not self.whatsapp_access_token.get_secret_value():
            reasons.append("Falta configurar el token de acceso nuevo.")
        if not all(
            re.fullmatch(r"[0-9]{1,100}", x)
            for x in (self.whatsapp_phone_number_id, self.whatsapp_business_account_id)
        ):
            reasons.append("Falta configurar la cuenta y el número emisor.")
        if not re.fullmatch(r"v[0-9]{1,3}\.0", self.meta_graph_api_version):
            reasons.append("Falta una versión vigente de Graph API.")
        if not self.whatsapp_allowed_recipients:
            reasons.append("Falta autorizar los destinatarios de prueba.")
        return reasons


@lru_cache
def messaging_settings():
    return MessagingSettings()
