# 🏳️ Site Trincheiras — O Tratado de Versalhes: Paz ou Pausa?

Interactive educational website for 9th-grade History students exploring the Treaty of
Versailles through quizzes, drag-and-drop activities, an interactive map, and a trench
warfare challenge — built as a small, reusable **lesson platform**: all lesson content
lives in PostgreSQL, and the same engine can host new lessons without code changes.

---

## Stack

| Layer            | Technology                                          |
| ---------------- | --------------------------------------------------- |
| HTML rendering   | FastAPI + Jinja2 (server-rendered, template inheritance) |
| Backend          | FastAPI + Uvicorn (Python 3.13)                     |
| Browser code     | Vanilla TypeScript, ES modules                      |
| Frontend build   | Vite (`vanilla-ts`), manifest-based asset injection |
| Styling          | Plain CSS (hand-written design tokens)              |
| Database         | PostgreSQL 16                                       |
| DB layer         | SQLAlchemy 2 ORM + Alembic migrations               |
| API contracts    | Pydantic v2 / OpenAPI → generated TypeScript types  |
| Backend tests    | pytest + FastAPI TestClient (real Postgres)         |
| Browser tests    | Playwright (Chromium, Firefox, WebKit)              |
| Packaging        | Multi-stage Docker (Node build → Python runtime)    |

## Architecture

```
┌───────────────────────────────────────────────────────┐
│                       Browser                         │
│   Server-rendered HTML (Jinja2, content from DB)      │
│   + TypeScript modules (Vite bundle, hashed assets)   │
│   Leaflet map · Web Audio · drag-and-drop             │
└──────────────┬────────────────────────────────────────┘
               │ GET /            (SSR page)
               │ GET /static/*    (Vite build, avatars, images)
               │ /api/v1/*        (JSON)
┌──────────────▼────────────────────────────────────────┐
│                 FastAPI (one container)               │
│  routers → services (domain boundaries) → SQLAlchemy  │
│  pages · players · answers · lessons · admin · reports│
└──────────────┬────────────────────────────────────────┘
               │ psycopg3
┌──────────────▼────────────────────────────────────────┐
│                     PostgreSQL 16                     │
│  players, answers │ lessons, content_blocks,          │
│  map_regions/features, activities, questions,         │
│  question_options, match_documents                    │
│  Schema owned by Alembic; content seeded from fixtures│
└───────────────────────────────────────────────────────┘
```

**Single-service design:** one FastAPI process serves the page, the static assets, and
the API — one container on Cloud Run. Display-only content (flip cards, participants,
treaty clauses) is **server-rendered** from the database; interactive data (map
features, quiz questions) is fetched by TypeScript from the JSON API.

## Reusable API map

The app is a **modular monolith**. Each domain is a router + service pair that could be
extracted into its own deployable API later; routers never touch the ORM directly, and
services exchange Pydantic schemas/ids only.

| Boundary | Owns | Endpoints | Reuse story |
| --- | --- | --- | --- |
| **Player identity** (`services/players.py`) | `players` | `POST /api/v1/players` | Participant registration for any classroom activity |
| **Lesson content** (`services/content.py`) | `lessons`, `content_blocks`, `map_*`, `activities`, `questions`, `question_options`, `match_documents` | `GET /api/v1/lessons/{slug}/bundle`, `PUT/DELETE /api/v1/admin/lessons/...` | CMS-lite lesson engine — a new lesson is new rows + seed fixtures, zero code. One service feeds both the Jinja SSR page and the JSON bundle |
| **Answer telemetry** (`services/answers.py`) | `answers` | `POST /api/v1/answers` | Generic answer/event collector (question FK, chosen value, correctness, score delta) |
| **Reporting** (`services/reports.py`) | read-only joins | `GET /api/v1/reports/players`, `/reports/players/{id}/answers`, `/reports/answers` | Teacher-facing read model; the natural first extraction |

Interactive API docs: `http://localhost:8000/docs` (OpenAPI). The spec is committed at
[backend/openapi.json](backend/openapi.json) and generates the frontend types
([frontend/src/api/types.gen.ts](frontend/src/api/types.gen.ts)) — regenerate with
`make gen-api`; CI-able drift check via `python -m app.openapi_export --check openapi.json`.

Admin and report endpoints require the `X-Admin-Token` header (matching `ADMIN_TOKEN`).
With `ADMIN_TOKEN` empty they are disabled outright.

## Project structure

```
site-trincheiras/
├── backend/
│   ├── app/
│   │   ├── main.py               # app factory: routers, templates, static mount
│   │   ├── config.py             # pydantic-settings (env vars)
│   │   ├── db.py                 # lazy engine + session dependency
│   │   ├── security.py           # X-Admin-Token dependency
│   │   ├── vite.py               # vite_asset() Jinja helper (dev server ⇄ manifest)
│   │   ├── avatars.py            # fixed avatar catalogue (static assets)
│   │   ├── models/               # SQLAlchemy 2 ORM (one module per domain)
│   │   ├── schemas/              # Pydantic contracts (API + seed validation)
│   │   ├── services/             # domain boundaries: players, content, answers, reports
│   │   ├── routers/              # pages, health, players, answers, lessons, admin, reports
│   │   ├── templates/            # base.html + index.html + partials/ (9 sections)
│   │   ├── static/               # avatars/, img/; dist/ = Vite output (gitignored)
│   │   ├── seed/                 # fixtures/*.json + idempotent seed runner
│   │   └── openapi_export.py     # spec export without a running server
│   ├── alembic/                  # migrations (baseline: full schema)
│   ├── tests/                    # pytest suite (transactional Postgres fixtures)
│   └── pyproject.toml            # uv-managed
├── frontend/
│   ├── src/
│   │   ├── main.ts               # boot: fetch lesson bundle, init features
│   │   ├── api/                  # typed client + generated OpenAPI types
│   │   ├── features/             # tabs, enlistment, flip-cards, participants,
│   │   │                         #   clauses, map, war-room, trench, effects/
│   │   ├── state/player.ts       # localStorage player id
│   │   └── styles/main.css       # ported design system (~5 000 lines)
│   ├── e2e/                      # Playwright specs + compose-driven setup
│   ├── vite.config.ts            # manifest build into backend/app/static/dist
│   └── playwright.config.ts
├── Dockerfile                    # node:22 build stage → python:3.13-slim runtime
├── docker-compose.yml            # local stack (db + app, auto migrate/seed)
├── docker-compose.test.yml       # throwaway e2e stack on :8001 (tmpfs db)
├── Makefile                      # common workflows (see `make` targets)
└── .env.example
```

## Getting started

### Prerequisites

- **Docker** (Postgres + full-stack runs)
- **uv** (Python; `brew install uv`)
- **Node.js 22+** (`brew install node`) — Vite build, Playwright

### Option 1 — full stack in Docker

```bash
docker compose up --build -d      # builds frontend + backend, migrates, seeds
open http://localhost:3000
```

### Option 2 — development loop (hot reload)

```bash
# 1. database
make db            # docker compose up -d db

# 2. one-time setup
cd backend && uv sync && cd ../frontend && npm install && cd ..
make migrate seed  # schema + lesson content

# 3. run (two terminals)
make backend       # uvicorn on :8000, pages point at the Vite dev server
make frontend      # vite dev server on :5173 (CSS/TS hot reload)

open http://localhost:8000       # always browse the FastAPI origin
```

CSS edits hot-swap instantly; TS edits reload the page; template edits reload with
uvicorn. To preview the production asset pipeline locally: `make build`, then run
`make backend` with `VITE_DEV_SERVER=` (empty) — tags now come from the build manifest.

## Testing

```bash
make test       # pytest: API, seed idempotency, SSR pages, admin, reports,
                #         and a migrations-match-models check (needs `make db`)
make e2e        # Playwright: builds the image, boots docker-compose.test.yml
                #         (tmpfs Postgres, :8001), runs 6 specs × 3 browsers
make check      # everything a PR should pass (tests + spec drift + types + e2e)
```

One-time for e2e: `cd frontend && npx playwright install`.

E2E against an already-running stack: `PW_BASE_URL=http://localhost:8000 npm run e2e`
(skips compose management; the target needs `APP_ENV=test` for the reset endpoint).

## Content management

Lesson content is data, not code:

- **Fixtures** in `backend/app/seed/fixtures/*.json` are the source of truth;
  `python -m app.seed` (or `make seed`) upserts them by slug — idempotent, safe on
  every deploy, and it never touches recorded answers.
- **Admin API** (`PUT /api/v1/admin/lessons/{lesson}/...`) uses the same upsert
  services, so ad-hoc edits behave exactly like seeding. Removing a question that
  already has recorded answers is refused with `409`.
- A new lesson = a new `lessons` row + its blocks/activities (fixtures or API), then
  point `DEFAULT_LESSON_SLUG` at it.

## Teacher reports

```bash
TOKEN=your-admin-token
curl -H "X-Admin-Token: $TOKEN" 'http://localhost:8000/api/v1/reports/players?class_group=9º A'
curl -H "X-Admin-Token: $TOKEN" 'http://localhost:8000/api/v1/reports/players/1/answers'
curl -H "X-Admin-Token: $TOKEN" 'http://localhost:8000/api/v1/reports/answers?activity=trench-mission&limit=50'
```

## Deploying to Google Cloud Run

```bash
export PROJECT_ID=your-gcp-project-id
export REGION=us-central1
export INSTANCE=$PROJECT_ID:$REGION:your-cloudsql-instance
export DB_URL="postgresql+psycopg://USER:PASS@/trincheiras?host=/cloudsql/$INSTANCE"

# 1. Build & push
gcloud builds submit --tag gcr.io/$PROJECT_ID/site-trincheiras

# 2. Migrate + seed via one-off jobs (same image, command override)
gcloud run jobs create trincheiras-migrate --image gcr.io/$PROJECT_ID/site-trincheiras \
  --region $REGION --set-cloudsql-instances $INSTANCE \
  --set-env-vars "DATABASE_URL=$DB_URL" --command alembic --args upgrade,head
gcloud run jobs execute trincheiras-migrate --region $REGION --wait

gcloud run jobs create trincheiras-seed --image gcr.io/$PROJECT_ID/site-trincheiras \
  --region $REGION --set-cloudsql-instances $INSTANCE \
  --set-env-vars "DATABASE_URL=$DB_URL" --command python --args -m,app.seed
gcloud run jobs execute trincheiras-seed --region $REGION --wait

# 3. Deploy the service
gcloud run deploy site-trincheiras \
  --image gcr.io/$PROJECT_ID/site-trincheiras \
  --platform managed --region $REGION --allow-unauthenticated \
  --add-cloudsql-instances $INSTANCE \
  --set-env-vars "DATABASE_URL=$DB_URL" \
  --set-secrets "ADMIN_TOKEN=trincheiras-admin-token:latest"
```

For subsequent releases: build → execute the migrate job (and seed job on content
changes) → deploy. Small-scale alternative: set `RUN_MIGRATIONS=true`/`RUN_SEED=true`
on the service and skip the jobs (fine at min-instances 0–1; Alembic serializes via its
version-table lock).

### Portability (AWS ECS or any container platform)

The image has no GCP dependencies:

- Listens on `$PORT` (defaults to 8080); stateless container.
- `GET /healthz` never touches the database — use it for ALB target-group checks so DB
  blips don't restart-loop tasks.
- `DATABASE_URL` works with RDS over TCP: `postgresql+psycopg://user:pass@host:5432/db?sslmode=require`.
- Inject `ADMIN_TOKEN` via ECS task-definition `secrets` (SSM / Secrets Manager).
- Run migrations/seed as one-off `RunTask` executions with command overrides
  (`alembic upgrade head` / `python -m app.seed`).

## Querying the local database

```bash
docker compose exec db psql -U trincheiras -d trincheiras

-- registered players
SELECT * FROM players;

-- answers with player and question context
SELECT p.name, p.class_group, a2.slug AS activity, q.slug AS question,
       a.selected_value, a.is_correct, a.score_delta, a.created_at
FROM answers a
JOIN questions q  ON q.id = a.question_id
JOIN activities a2 ON a2.id = q.activity_id
LEFT JOIN players p ON p.id = a.player_id
ORDER BY a.created_at;
```

(Or skip SQL entirely and use the `/api/v1/reports/*` endpoints.)

## Follow-ups (deliberately out of scope)

- **Server-side scoring** — the schema already supports it (`answers.selected_value`
  stores option/document slugs comparable against `question_options.is_correct` /
  `match_documents`); today correctness is client-reported for parity, and correct
  answers ship in the lesson bundle exactly as the legacy site shipped them in JS.
- Real authentication + an admin UI (the token-gated API is the seam).
- CI pipeline (GitHub Actions running `make check` + image build).
- Tab keyboard a11y (arrow-key roving focus), pointer-events drag-and-drop.
- A second lesson to exercise the content model end-to-end.

## License

ISC
