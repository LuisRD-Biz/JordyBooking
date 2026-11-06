import sys
import time

import httpx

from jordy.admin_reads import AdminReads
from jordy.telegram.commands import reply_for


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


def poll(
    client: httpx.Client,
    allowed: frozenset[int],
    sleep=time.sleep,
    *,
    reads: AdminReads | None = None,
):
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
                reply = reply_for(update, allowed, reads)
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
