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
the API — one container, run by AWS Lambda in production. Display-only content (flip cards, participants,
treaty clauses) is **server-rendered** from the database; interactive data (map
features, quiz questions) is fetched by TypeScript from the JSON API.

## Reusable API map

The app is a **modular monolith**. Each domain is a router + service pair that could be
extracted into its own deployable API later; routers never touch the ORM directly, and
services exchange Pydantic schemas/ids only.

| Boundary | Owns | Endpoints | Reuse story |
| --- | --- | --- | --- |
| **Player identity** (`services/players.py`) | `players` | `POST /api/v1/players` | Participant registration for any classroom activity |
| **Lesson content** (`services/content.py`) | `lessons`, `content_blocks`, `map_*`, `activities`, `questions`, `question_options`, `match_documents` | `GET /api/v1/lessons/{slug}/bundle` (public, no answers), `GET /api/v1/admin/lessons/{slug}/activities` (with the answer key), `PUT/DELETE /api/v1/admin/lessons/...` | CMS-lite lesson engine — a new lesson is new rows + seed fixtures, zero code. One service feeds both the Jinja SSR page and the JSON bundle |
| **Answers and scoring** (`services/answers.py`, `services/scoring.py`) | `answers` | `POST /api/v1/answers` | Judges an attempt against the lesson content and the activity's scoring rules, and records it for enlisted players (see [Scoring](#scoring)) |
| **Reporting** (`services/reports.py`) | read-only joins | `GET /api/v1/reports/players`, `/reports/players/{id}/answers`, `/reports/answers` | Teacher-facing read model; the natural first extraction |

Interactive API docs: `http://localhost:8000/docs` (OpenAPI). The spec is committed at
[backend/openapi.json](backend/openapi.json) and generates the frontend types
([frontend/src/api/types.gen.ts](frontend/src/api/types.gen.ts)) — regenerate with
`make gen-api`; CI-able drift check via `python -m app.openapi_export --check openapi.json`.

Admin and report endpoints require the `X-Admin-Token` header (matching `ADMIN_TOKEN`).
With `ADMIN_TOKEN` empty they are disabled outright.

## Scoring

The server decides whether an answer is right and what it scores. The browser never
holds the answers.

**What students can read.** The public bundle and the server-rendered page carry the
questions, the option labels and the document texts, each with its id, and nothing
else about them: no `is_correct`, no document-to-drawer pairing, no feedback texts, no
scoring rules, and no slugs of options or documents (slugs are author-facing names; in
the seed `doc-3` belongs in `drawer-3`). The answer key is available to the teacher
through `GET /api/v1/admin/lessons/{slug}/activities`.

**The request** says only what was chosen:

```bash
curl -X POST http://localhost:8000/api/v1/answers -H 'Content-Type: application/json' \
  -d '{"player_id": 1, "question_id": 6, "choice_id": 17}'
```

`choice_id` is the id of an option (quiz) or of a document (war room, where
`question_id` is the drawer). Fields such as `is_correct` or `score_delta` are refused
with `422`, as is a choice that does not belong to the question; an unknown question
or player is `404`.

**The response** carries the verdict, and the feedback text when the answer is right:

```json
{"id": 42, "player_id": 1, "question_id": 6, "choice_id": 17,
 "is_correct": true, "score_delta": 10, "feedback": "Correto. A Alsácia-Lorena..."}
```

**Rules** come from the activity's `config` (`points_correct`, `points_wrong`,
`max_penalized_errors`; defaults 10, -5, 2). A wrong answer costs `points_wrong` until
the player has made `max_penalized_errors` wrong answers to that question; further
ones cost nothing. The count runs from the player's last correct answer to the
question, so replaying an activity starts clean while reloading the page mid-question
does not.

**Anonymous play** (`player_id` null or absent) is judged by the same rules and is not
recorded: the response is `200` with `"id": null`, and the score lives only in that
browser. With no identity to count errors against, the cap uses `prior_errors` from
the request (wrong attempts already made at the question on that page); for enlisted
players that field is ignored. `answers.selected_value` still stores the slug of the
chosen option or document, so reports read as before.

**Slow or failed requests.** The games show a verdict only when the server has given
one. After 0.4 s they say the answer is being checked, after 5 s that the server is
slow (the database may be resuming), and on a network error, a timeout or a
5xx they keep the score as it is and offer "Tentar novamente". The retry sends
`"retry": {"elapsed_ms": ..., "after_answer_id": ...}`; if the first send did reach
the database, the server returns that recorded answer with `200` instead of recording
the attempt twice. Requests for the same player and question are serialized with a
PostgreSQL advisory lock, so the error count and the retry lookup cannot race.

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
│   │   ├── routers/              # pages, health, players, answers, lessons, admin, reports,
│   │   │                         #   ops (migrate/seed, mounted only with OPS_MODE=true)
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
├── infra/                        # Terraform for AWS + deploy.sh (see "Deploying to AWS")
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
                #         (tmpfs Postgres, :8001), runs 7 specs × 3 browsers
make check      # everything a PR should pass (tests + spec drift + types + e2e)
```

One-time for e2e: `cd frontend && npx playwright install`.

Every pull request and every push to `main` runs the same gates in GitHub Actions
([`.github/workflows/ci.yml`](.github/workflows/ci.yml)): pytest, OpenAPI and generated-type
drift, type checks, the browser suite against the production image, and
`terraform fmt` / `validate`. CI does not deploy; releases stay a deliberate
`./infra/deploy.sh`.

E2E against an already-running stack: `PW_BASE_URL=http://localhost:8000 npm run e2e`
(skips compose management; the target needs `APP_ENV=test` for the reset endpoint).

Two checkouts running the suite at once need separate stacks:
`E2E_PORT=8002 E2E_PROJECT=trincheiras-e2e-2 npm run e2e`.

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

## Deploying to AWS

Production runs in AWS account `249744179072`, region `us-east-1`, at
**https://historiaporaline.com.br**. Everything is Terraform in [`infra/`](infra/).

```
 Browser ──► CloudFront ──signed (SigV4)──► Lambda "web" ──► Aurora Serverless v2
             TLS, custom domain,            this image +      PostgreSQL 16, private
             /static/* cached at the edge   Lambda Web        subnets, pauses when idle
                                            Adapter
 aws lambda invoke ───────────────────────► Lambda "ops" ──► (same database)
                                            same image, POST /internal/ops
```

- **Scale to zero.** Lambda bills per request and Aurora pauses after 5 idle minutes,
  so an idle month costs storage only (roughly US$1–5). The first page load after a
  pause waits for the database to resume: about 15 s, 30 s or more after a day asleep.
  Open the site a minute before class.
- **Same container as local.** The [Lambda Web Adapter](https://github.com/awslabs/aws-lambda-web-adapter)
  in the image turns Lambda invocations into HTTP requests to uvicorn; outside Lambda it
  does nothing.
- **Private database.** Aurora has no public address, and the VPC has no internet
  gateway or NAT. Migrations and the seed therefore run through the `ops` function
  (`OPS_MODE=true` mounts `POST /internal/ops`), which has no URL and is reachable only
  with IAM credentials via `aws lambda invoke`.

### Release

```bash
./infra/deploy.sh
```

Builds the arm64 image, pushes it to ECR tagged with the commit, runs `terraform apply`
(it asks before changing anything), then invokes the `ops` function with
`{"task": "migrate-and-seed"}`. Both steps are idempotent. Needs `aws` (the `personal`
profile), `terraform` and Docker.

Other ops tasks: `migrate`, `seed`, `status` (Alembic revision and row counts):

```bash
aws lambda invoke --function-name trincheiras-ops --cli-binary-format raw-in-base64-out \
  --payload '{"task": "status"}' /dev/stdout
```

### Domain (registro.br)

The domain is registered at registro.br and its DNS is hosted in Route 53.
`domain_delegated` in [`infra/terraform.tfvars`](infra/terraform.tfvars) gates
everything that needs the delegation: while `false`, the site answers only on its
`cloudfront.net` address (`terraform output cloudfront_url`).

1. `cd infra && terraform output name_servers` lists four `awsdns` servers.
2. At registro.br, open the domain → **DNS** → **Alterar servidores DNS** and enter
   those four (no trailing dot). Leave the DS/DNSSEC fields empty.
3. Once `dig +short NS historiaporaline.com.br` returns them, set
   `domain_delegated = true` and run `./infra/deploy.sh`. That issues the certificate
   (validated through the zone), attaches the domain to CloudFront, creates the
   `A`/`AAAA` records for the apex and `www`, and redirects `www` to the apex.

### Admin and report calls in production

The token is generated by Terraform: `cd infra && terraform output -raw admin_token`.

CloudFront signs each request to Lambda, and Lambda rejects a `POST`/`PUT` whose body
hash is not part of that signature. The frontend sends it automatically
(`x-amz-content-sha256` in `frontend/src/api/client.ts`); with curl, add it yourself:

```bash
BODY='{"title": "..."}'
curl -X PUT https://historiaporaline.com.br/api/v1/admin/lessons/... \
  -H "X-Admin-Token: $TOKEN" -H 'Content-Type: application/json' \
  -H "x-amz-content-sha256: $(printf %s "$BODY" | shasum -a 256 | cut -d' ' -f1)" \
  -d "$BODY"
```

`GET` requests need nothing extra.

### Settings that matter on Lambda

| Variable | Value | Why |
| --- | --- | --- |
| `DB_POOL` | `false` | A frozen sandbox would hold a pooled connection open, and Aurora pauses only when none is left |
| `DB_CONNECT_RETRY_SECONDS` | `45` (web), `120` (ops) | Wait for Aurora to resume instead of failing the request |
| `AWS_LWA_READINESS_CHECK_PATH` | `/healthz` | Cold starts must not depend on the database |
| `OPS_MODE` | `true` on `ops` only | Mounts `POST /internal/ops` |

### One-time bootstrap

The Terraform state bucket was created by hand:

```bash
aws s3api create-bucket --bucket trincheiras-terraform-state-249744179072 --region us-east-1
```

```bash
aws s3api put-bucket-versioning --bucket trincheiras-terraform-state-249744179072 --versioning-configuration Status=Enabled
```

### Other container platforms

The image has no AWS dependencies either: it listens on `$PORT` (default 8080), is
stateless, answers `GET /healthz` without touching the database, and takes any
PostgreSQL `DATABASE_URL`. With `RUN_MIGRATIONS=true` / `RUN_SEED=true` the entrypoint
migrates and seeds on start (what docker-compose does).

## Querying the local database

```bash
docker compose exec db psql -U trincheiras -d trincheiras

-- registered players
SELECT * FROM players;

-- answers with player and question context
-- (is_correct and score_delta are computed by the server; anonymous play is not stored)
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

- Real authentication + an admin UI (the token-gated API is the seam).
- Pointer-events drag-and-drop (touch screens fall back to click-to-place today).
- A second lesson to exercise the content model end-to-end.

## License

ISC
