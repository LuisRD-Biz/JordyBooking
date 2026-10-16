import hashlib
import logging
from contextlib import asynccontextmanager
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from jordy.api import router
from jordy.auth import router as auth_router
from jordy.config import settings
from jordy.crm import router as crm_router
from jordy.db import build_engine
from jordy.documents import router as document_router
from jordy.domain import Conflict, RuleViolation
from jordy.repository import NotFound
from jordy.search import router as search_router

logger = logging.getLogger("jordy")


@lru_cache
def get_engine():
    return build_engine(settings().database_url)


@asynccontextmanager
async def lifespan(app):
    settings()  # Fail closed if no sufficiently strong administrative key is configured.
    yield
    get_engine().dispose()


app = FastAPI(title="Jordy Studio — Reservaciones", version="0.1.0", lifespan=lifespan)
app.include_router(router)
app.include_router(auth_router)
app.include_router(crm_router)
app.include_router(search_router)
app.include_router(document_router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/ready")
def ready():
    """No secrets or paths; identify this checkout before the launcher reuses a port."""
    root = Path(__file__).resolve().parents[2]
    instance = hashlib.sha256(str(root).casefold().encode()).hexdigest()[:24]
    try:
        from alembic.config import Config
        from alembic.script import ScriptDirectory

        config = Config(str(root / "alembic.ini"))
        config.set_main_option("script_location", str(root / "migrations"))
        head = ScriptDirectory.from_config(config).get_current_head()
        with get_engine().connect() as connection:
            version = connection.scalar(text("SELECT version_num FROM alembic_version"))
        valid = version == head and (root / "frontend/dist/index.html").is_file()
    except Exception:
        valid = False
    return JSONResponse(
        status_code=200 if valid else 503,
        content={
            "status": "ready" if valid else "not_ready",
            "application": "jordy-studio",
            "instance": instance,
        },
    )


@app.exception_handler(RuleViolation)
async def rule_error(request: Request, exc: RuleViolation):
    status = 404 if isinstance(exc, NotFound) else 409 if isinstance(exc, Conflict) else 422
    return JSONResponse(status_code=status, content={"detail": str(exc)})


@app.exception_handler(IntegrityError)
async def integrity_error(request: Request, exc: IntegrityError):
    logger.warning("database_constraint_conflict", extra={"path": request.url.path})
    return JSONResponse(
        status_code=409, content={"detail": "Conflicto de integridad o disponibilidad."}
    )


frontend = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if frontend.is_dir():
    app.mount("/", StaticFiles(directory=frontend, html=True), name="panel")
