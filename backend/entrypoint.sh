#!/bin/sh
set -e

# Both flags default off so a scaled-out service never migrates implicitly.
# Compose turns them on; production prefers one-off jobs with command overrides.
if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
  echo "Running database migrations..."
  alembic upgrade head
fi

if [ "${RUN_SEED:-false}" = "true" ]; then
  echo "Seeding lesson content..."
  python -m app.seed
fi

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8080}"
