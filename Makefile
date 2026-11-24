# Development workflow shortcuts. See README.md for the full guide.

.PHONY: db dev backend frontend seed migrate test e2e build openapi gen-api up down check

## Start only the Postgres container
db:
	docker compose up -d db

## Run migrations against DATABASE_URL (defaults to the local compose db)
migrate:
	cd backend && uv run alembic upgrade head

## Seed lesson content (idempotent)
seed:
	cd backend && uv run python -m app.seed

## Backend dev server with auto-reload (expects `make db` and VITE_DEV_SERVER for HMR)
backend:
	cd backend && VITE_DEV_SERVER=$${VITE_DEV_SERVER:-http://localhost:5173} uv run uvicorn app.main:app --reload --port 8000

## Vite dev server (HMR for TS/CSS)
frontend:
	cd frontend && npm run dev

## Backend tests (needs the compose db running)
test:
	cd backend && uv run pytest

## Full browser suite: builds the image, boots a throwaway stack, runs Playwright
e2e:
	cd frontend && npm run e2e

## Production asset build (typecheck + Vite -> backend/app/static/dist)
build:
	cd frontend && npm run build

## Export the OpenAPI spec (backend/openapi.json)
openapi:
	cd backend && uv run python -m app.openapi_export --out openapi.json

## Regenerate TypeScript API types from the exported spec
gen-api: openapi
	cd frontend && npm run gen:api

## Full local stack from the production image (http://localhost:3000)
up:
	docker compose up --build -d

down:
	docker compose down

## Everything a PR should pass: backend tests, spec drift, types, e2e
check: test
	cd backend && uv run python -m app.openapi_export --check openapi.json
	cd frontend && npm run typecheck && npm run typecheck:e2e && npm run e2e
