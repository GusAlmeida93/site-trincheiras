# ---- Stage 1: build the TypeScript frontend ----
FROM node:22-alpine AS frontend-build
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
# vite.config.ts points outDir at ../backend for local dev; inside the image
# we build to a local dist and copy it into the runtime stage instead.
RUN npm run typecheck && npx vite build --outDir=dist

# ---- Stage 2: Python runtime ----
FROM python:3.13-slim AS runtime
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /uvx /usr/local/bin/
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1
WORKDIR /srv

COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev

COPY backend/alembic.ini ./
COPY backend/alembic ./alembic
COPY backend/app ./app
COPY --from=frontend-build /build/dist ./app/static/dist
COPY backend/entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh \
    && useradd --system --uid 1001 appuser \
    && chown -R appuser:appuser /srv
USER appuser
ENV PATH="/srv/.venv/bin:$PATH"

# Cloud Run injects PORT (defaults to 8080); the entrypoint honors it.
EXPOSE 8080
ENTRYPOINT ["/entrypoint.sh"]
