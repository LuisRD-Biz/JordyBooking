import logging
from contextlib import asynccontextmanager
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import IntegrityError

from jordy.api import router
from jordy.auth import router as auth_router
from jordy.config import settings
from jordy.db import build_engine
from jordy.domain import Conflict, RuleViolation
from jordy.repository import NotFound

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


@app.get("/health")
def health():
    return {"status": "ok"}


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
