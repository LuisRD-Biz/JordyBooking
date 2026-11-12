import ipaddress
from functools import lru_cache
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field, SecretStr
from sqlalchemy.orm import Session

from jordy import accounts
from jordy.accounts import Principal
from jordy.config import settings
from jordy.db import build_engine

router = APIRouter(prefix="/auth", tags=["Panel"])
GENERIC_LOGIN_ERROR = "Correo o contraseña incorrectos."
THROTTLED_ERROR = "Demasiados intentos. Espera 15 minutos antes de volver a intentarlo."


def secure_cookies() -> bool:
    return settings().panel_origin.startswith("https:")


def cookie_name() -> str:
    return "__Host-jordy_session" if secure_cookies() else "jordy_session"


COOKIE = "jordy_session"


@lru_cache(maxsize=4)
def _engine(url: str):
    return build_engine(url)


def auth_db() -> Session:
    return Session(_engine(settings().database_url))


def same_origin(request: Request):
    if request.headers.get("origin") != settings().panel_origin:
        raise HTTPException(403, "Origen de la solicitud no permitido.")


def client_ip(request: Request) -> str:
    header = settings().client_ip_header
    if header:
        value = (request.headers.get(header) or "").strip()
        try:
            return str(ipaddress.ip_address(value))
        except ValueError:
            pass
    return request.client.host if request.client else "unknown"


def local_allowed(request: Request) -> bool:
    return (
        settings().local_panel_access
        and request.client is not None
        and request.client.host in {"127.0.0.1", "::1"}
        and urlparse(settings().panel_origin).hostname in {"127.0.0.1", "localhost"}
        and request.headers.get("host") == urlparse(settings().panel_origin).netloc
    )


def current_principal(request: Request) -> Principal | None:
    cached = getattr(request.state, "principal", False)
    if cached is not False:
        return cached
    token = request.cookies.get(cookie_name())
    principal = None
    if token:
        with auth_db() as db, db.begin():
            principal = accounts.resolve_session(db, token)
    request.state.principal = principal
    return principal


def valid_session(request: Request) -> bool:
    return current_principal(request) is not None


def _set_cookie(response: Response, token: str):
    response.set_cookie(
        cookie_name(),
        token,
        httponly=True,
        secure=secure_cookies(),
        samesite="strict",
        max_age=int(accounts.SESSION_LIFETIME.total_seconds()),
        path="/",
    )


def _profile(principal: Principal) -> dict:
    return {
        "name": principal.name,
        "email": principal.email,
        "role": principal.role,
        "local": principal.user_id is None,
        "timezone": settings().studio_timezone,
    }


def _no_store(response: Response):
    response.headers["Cache-Control"] = "no-store"


@router.get("/config")
def config(request: Request):
    return {"local_access": local_allowed(request), "method": "password"}


@router.get("/session")
def session(request: Request, response: Response):
    _no_store(response)
    principal = current_principal(request)
    if principal is None:
        raise HTTPException(401, "Inicia sesión para continuar.")
    return _profile(principal)


@router.post("/local")
def local_login(request: Request, response: Response):
    same_origin(request)
    if not local_allowed(request):
        raise HTTPException(403, "El acceso local no está habilitado.")
    with auth_db() as db, db.begin():
        accounts.revoke_session(db, request.cookies.get(cookie_name()))
        token = accounts.start_session(
            db, None, client_ip(request), request.headers.get("user-agent")
        )
    _set_cookie(response, token)
    _no_store(response)
    return _profile(Principal(0, None, "Acceso local", None, "admin"))


class Login(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: SecretStr = Field(min_length=1, max_length=accounts.PASSWORD_MAX)


@router.post("/login")
def login(data: Login, request: Request, response: Response):
    same_origin(request)
    _no_store(response)
    ip = client_ip(request)
    with auth_db() as db:
        try:
            with db.begin():
                user = accounts.authenticate(db, data.email, data.password.get_secret_value(), ip)
                accounts.revoke_session(db, request.cookies.get(cookie_name()))
                token = accounts.start_session(db, user, ip, request.headers.get("user-agent"))
                profile = {
                    "name": user.name,
                    "email": user.email,
                    "role": user.role,
                    "local": False,
                    "timezone": settings().studio_timezone,
                }
        except (accounts.LoginRejected, accounts.LoginThrottled) as error:
            with db.begin():
                db.add(
                    accounts.LoginAttempt(
                        email=accounts.normalize_email(data.email),
                        ip=ip,
                        succeeded=False,
                        created_at=accounts.now(),
                    )
                )
            if isinstance(error, accounts.LoginThrottled):
                raise HTTPException(429, THROTTLED_ERROR, headers={"Retry-After": "900"})
            raise HTTPException(401, GENERIC_LOGIN_ERROR)
    _set_cookie(response, token)
    return profile


@router.post("/logout")
def logout(request: Request, response: Response):
    same_origin(request)
    _no_store(response)
    with auth_db() as db, db.begin():
        accounts.revoke_session(db, request.cookies.get(cookie_name()))
    response.delete_cookie(cookie_name(), path="/", secure=secure_cookies(), httponly=True)
    return {"ok": True}


class PasswordChange(BaseModel):
    current_password: SecretStr = Field(min_length=1, max_length=accounts.PASSWORD_MAX)
    new_password: SecretStr = Field(min_length=1, max_length=accounts.PASSWORD_MAX)


@router.post("/password")
def change_password(data: PasswordChange, request: Request, response: Response):
    same_origin(request)
    _no_store(response)
    principal = current_principal(request)
    if principal is None:
        raise HTTPException(401, "Inicia sesión para continuar.")
    if principal.user_id is None:
        raise HTTPException(403, "El acceso local no tiene contraseña.")
    with auth_db() as db:
        try:
            with db.begin():
                user = db.get(accounts.User, principal.user_id)
                accounts.authenticate(
                    db, user.email, data.current_password.get_secret_value(), client_ip(request)
                )
                accounts.set_password(
                    db, user, data.new_password.get_secret_value(), principal.session_id
                )
        except (accounts.LoginRejected, accounts.LoginThrottled) as error:
            with db.begin():
                db.add(
                    accounts.LoginAttempt(
                        email=principal.email or "",
                        ip=client_ip(request),
                        succeeded=False,
                        created_at=accounts.now(),
                    )
                )
            if isinstance(error, accounts.LoginThrottled):
                raise HTTPException(429, THROTTLED_ERROR, headers={"Retry-After": "900"})
            raise HTTPException(401, "La contraseña actual no es correcta.")
        except accounts.PasswordRejected as error:
            raise HTTPException(422, str(error))
    return {"ok": True}
