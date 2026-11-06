FROM node:24.22.1-bookworm-slim@sha256:be8204d4bd327363357f532187b752ff62759c31bedf98e9e18fc08c9cbd605c AS panel
WORKDIR /panel
RUN npm install --global pnpm@11.25.0
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/index.html frontend/tsconfig.json ./
COPY frontend/src/ ./src/
RUN pnpm run build

FROM ghcr.io/astral-sh/uv:0.12.5@sha256:e85be844203885286c60ffad8a858d48afb6c5a5c237ca0e67f12e74b8f174b1 AS uv
FROM python:3.13.15-slim-bookworm@sha256:2325bb286ec344af3e5898cc224b5844e2707ac6e26b1632516fd3edc84a5e26
WORKDIR /app
ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONPATH=/app/backend \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
COPY pyproject.toml uv.lock ./
RUN --mount=from=uv,source=/uv,target=/usr/local/bin/uv \
    uv sync --locked --no-dev --no-install-project --no-cache --no-managed-python
COPY backend/ ./backend/
COPY alembic.ini ./
COPY migrations/ ./migrations/
COPY docker/migrate.py ./docker/migrate.py
COPY --from=panel /panel/dist/ ./frontend/dist/
RUN groupadd --gid 10001 jordy && useradd --uid 10001 --gid jordy --no-create-home jordy \
    && install -d -m 0700 -o jordy -g jordy /var/lib/jordy/documents
USER 10001:10001
EXPOSE 8000
CMD ["uvicorn", "jordy.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-proxy-headers", "--no-access-log"]
