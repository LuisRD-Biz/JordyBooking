"""Real Graph adapter; no network retry, no redirects, no provider prose in errors."""

from dataclasses import dataclass
from typing import Protocol

import httpx


@dataclass
class SendResult:
    status: str
    external_id: str | None = None
    error_code: str | None = None


class MessagingProvider(Protocol):
    def send(self, recipient: str, kind: str, body: str | None, details: dict) -> SendResult: ...


class WhatsAppAdapter:
    def __init__(self, config, transport=None):
        self.config = config
        self.transport = transport

    def send(self, recipient, kind, body, details):
        config = self.config
        codes = config.send_blocker_codes()
        if codes:
            return SendResult("failed", error_code=codes[0])
        if recipient not in config.whatsapp_allowed_recipients:
            return SendResult("failed", error_code="recipient_not_authorized")
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": kind,
        }
        if kind == "text":
            payload["text"] = {"preview_url": False, "body": body}
        else:
            payload["template"] = {
                "name": details["name"],
                "language": {"code": details["language"]},
            }
        url = (
            f"https://graph.facebook.com/{config.meta_graph_api_version}/"
            f"{config.whatsapp_phone_number_id}/messages"
        )
        try:
            with httpx.Client(
                timeout=httpx.Timeout(20, connect=5),
                follow_redirects=False,
                trust_env=False,
                transport=self.transport,
            ) as client:
                with client.stream(
                    "POST",
                    url,
                    json=payload,
                    headers={
                        "Authorization": "Bearer "
                        + config.whatsapp_access_token.get_secret_value(),
                    },
                ) as response:
                    raw = bytearray()
                    for chunk in response.iter_bytes():
                        raw.extend(chunk)
                        if len(raw) > 65536:
                            return SendResult("unknown", error_code="oversized_response")
                    import json

                    try:
                        data = json.loads(raw)
                    except (ValueError, TypeError):
                        data = {}
                    if 200 <= response.status_code < 300:
                        messages = data.get("messages", []) if isinstance(data, dict) else []
                        external_id = (
                            messages[0].get("id")
                            if messages and isinstance(messages[0], dict)
                            else None
                        )
                        if isinstance(external_id, str) and 0 < len(external_id) <= 300:
                            return SendResult("accepted", external_id=external_id)
                        return SendResult("unknown", error_code="missing_message_id")
                    # Explicit rejection is terminal; manual review instead of duplicate-risk retry.
                    status = "failed" if 400 <= response.status_code < 500 else "unknown"
                    error = data.get("error") if isinstance(data, dict) else None
                    code = error.get("code") if isinstance(error, dict) else None
                    # Numeric Meta codes only; never copy message/details/trace IDs.
                    suffix = f"_meta_{code}" if type(code) is int and 0 <= code <= 999999999 else ""
                    return SendResult(status, error_code=f"http_{response.status_code}{suffix}")
        except (httpx.HTTPError, OSError):
            return SendResult("unknown", error_code="network_result_unknown")
