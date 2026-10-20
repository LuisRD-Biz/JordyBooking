"""Read-only local preflight. Does not send messages or open any tunnel."""

import sys

import httpx


def main():
    try:
        with httpx.Client(
            base_url="http://127.0.0.1:8001", timeout=5, follow_redirects=False, trust_env=False
        ) as client:
            for route in (
                "/",
                "/auth/local",
                "/auth/config",
                "/api/customers",
                "/api/messaging/config",
                "/docs",
                "/redoc",
                "/openapi.json",
                "/.env",
                "/.local/",
                "/health",
                "/webhooks/whatsapp/",
            ):
                for method in ("GET", "POST"):
                    response = client.request(method, route)
                    if response.status_code != 404:
                        raise RuntimeError("unexpected route")
            for method in ("PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"):
                if client.request(method, "/webhooks/whatsapp").status_code != 405:
                    raise RuntimeError("unexpected method")
            if client.post("/webhooks/whatsapp", content=b"{}").status_code not in (401, 503):
                raise RuntimeError("unsigned event accepted")
    except Exception:
        print("No se verificó el aislamiento del puerto 8001. No abras el túnel.")
        return 1
    print("Puerto 8001: rutas administrativas inaccesibles y eventos sin firma rechazados.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
