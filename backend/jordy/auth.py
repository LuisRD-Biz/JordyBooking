"""Administrative browser sessions. Local desktop access is explicitly opt-in."""

import hashlib
import hmac
import secrets
import time
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, SecretStr

from jordy.config import settings

router = APIRouter(prefix="/auth", tags=["Panel"])
COOKIE = "jordy_session"
LIFETIME = 8 * 3600


def same_origin(request: Request):
    if request.headers.get("origin") != settings().panel_origin:
        raise HTTPException(403, "Origen de la solicitud no permitido.")


def local_allowed(request: Request) -> bool:
    return (
        settings().local_panel_access
        and request.client is not None
        and request.client.host in {"127.0.0.1", "::1"}
        and urlparse(settings().panel_origin).hostname in {"127.0.0.1", "localhost"}
        and request.headers.get("host") == urlparse(settings().panel_origin).netloc
    )


def signature(value: str) -> str:
    return hmac.new(
        settings().admin_api_key.get_secret_value().encode(), value.encode(), hashlib.sha256
    ).hexdigest()


def valid_session(request: Request) -> bool:
    token = request.cookies.get(COOKIE, "")
    try:
        expiry, nonce, signed = token.split(".")
        return time.time() < int(expiry) <= time.time() + LIFETIME and hmac.compare_digest(
            signature(f"{expiry}.{nonce}"), signed
        )
    except (ValueError, TypeError):
        return False


def issue(response: Response):
    value = f"{int(time.time()) + LIFETIME}.{secrets.token_hex(16)}"
    response.set_cookie(
        COOKIE,
        f"{value}.{signature(value)}",
        httponly=True,
        secure=settings().panel_origin.startswith("https:"),
        samesite="strict",
        max_age=LIFETIME,
        path="/",
    )
    return {"name": "Jordy", "timezone": settings().studio_timezone}


@router.get("/config")
def config(request: Request):
    return {"local_access": local_allowed(request)}


@router.get("/session")
def session(request: Request):
    if not valid_session(request):
        raise HTTPException(401, "Inicia sesión para continuar.")
    return {"name": "Jordy", "timezone": settings().studio_timezone}


@router.post("/local")
def local_login(request: Request, response: Response):
    same_origin(request)
    if not local_allowed(request):
        raise HTTPException(403, "El acceso local no está habilitado.")
    return issue(response)


class Login(BaseModel):
    key: SecretStr


@router.post("/login")
def login(data: Login, request: Request, response: Response):
    same_origin(request)
    if not secrets.compare_digest(
        data.key.get_secret_value().encode(), settings().admin_api_key.get_secret_value().encode()
    ):
        raise HTTPException(401, "La clave de acceso no es correcta.")
    return issue(response)


@router.post("/logout")
def logout(request: Request, response: Response):
    same_origin(request)
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}
