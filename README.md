# 🏳️ Site Trincheiras — O Tratado de Versalhes: Paz ou Pausa?

Interactive educational website for 9th-grade History students exploring the Treaty of Versailles through quizzes, drag-and-drop activities, interactive maps, and a trench warfare challenge.

---

## Architecture

```
┌─────────────────────────────────────────────┐
│              Browser (Frontend)             │
│  index.html  ·  styles.css  ·  script.js    │
│         Leaflet maps · Web Audio API        │
└──────────────────┬──────────────────────────┘
                   │  fetch /api/*
┌──────────────────▼──────────────────────────┐
│          Node.js / Express (server/)        │
│  server.js  ·  routes.js  ·  db.js          │
│  Serves static files + REST API             │
└──────────────────┬──────────────────────────┘
                   │  pg (TCP 5432)
┌──────────────────▼──────────────────────────┐
│             PostgreSQL 16                   │
│  Tables: jogadores, respostas               │
│  Init script: server/init.sql               │
└─────────────────────────────────────────────┘
```

**Single-service design:** Express serves the static frontend _and_ the API from the same process. This keeps Cloud Run deployment simple (one container).

### API Endpoints

| Method | Endpoint           | Description                     |
| ------ | ------------------ | ------------------------------- |
| POST   | `/api/jogadores`   | Create a player (name + class)  |
| POST   | `/api/respostas`   | Record a quiz answer            |

---

## Project Structure

```
site-trincheiras/
├── server/
│   ├── server.js         # Express app entry point
│   ├── routes.js         # API routes
│   ├── db.js             # PostgreSQL connection pool
│   └── init.sql          # Database schema
├── public/
│   └── avatars/          # Player avatar images (PNG, AI-generated WWI style)
├── assets/               # Background and reference images
├── index.html            # Main HTML page (single-page app)
├── styles.css            # All styles (~5 000 lines)
├── script.js             # Frontend logic (~2 100 lines)
├── test.js               # Quick smoke test (JSDOM)
├── run.sh                # Helper: rebuild & restart Docker containers
├── Dockerfile            # Production container
├── docker-compose.yml    # Local dev environment (app + Postgres)
├── .env.example          # Environment variable template
├── .dockerignore
├── .gitignore
└── package.json
```

---

## Getting Started

### Prerequisites

- **Docker** and **Docker Compose** (recommended)
- Or: **Node.js 20+** and a running **PostgreSQL** instance

### Option 1: Docker Compose (recommended)

This spins up the app and a Postgres database in containers:

```bash
# Clone and enter the project
git clone https://github.com/alineisa1110-stack/site-trincheiras.git
cd site-trincheiras

# Start everything
docker compose up --build -d

# Open in browser
open http://localhost:3000
```

The database schema is automatically applied via `server/init.sql`.

### Option 2: Local Node.js + existing Postgres

```bash
# Install dependencies
npm install

# Copy and configure environment variables
cp .env.example .env
# Edit .env with your Postgres connection string

# Start the dev server
npm run dev

# Open in browser
open http://localhost:3000
```

---

## Running Tests

```bash
npm test
```

This runs a basic JSDOM smoke test that loads `script.js` and verifies the main functions are defined without errors.

---

## Querying the Local Database

With Docker Compose running:

```bash
# Open a psql session
docker compose exec db psql -U trincheiras -d trincheiras

# List all registered players
SELECT * FROM jogadores;

# List all quiz answers
SELECT * FROM respostas;

# Answers per player with scores
SELECT j.nome, j.turma, r.modulo, r.pergunta_id, r.correto, r.variacao_pontos
FROM respostas r
JOIN jogadores j ON j.id = r.jogador_id
ORDER BY r.criado_em;
```

---

## Deploying to Google Cloud Run

### 1. Build and push the container

```bash
# Set your project ID
export PROJECT_ID=your-gcp-project-id

# Build the image
gcloud builds submit --tag gcr.io/$PROJECT_ID/site-trincheiras

# Or use Docker directly
docker build -t gcr.io/$PROJECT_ID/site-trincheiras .
docker push gcr.io/$PROJECT_ID/site-trincheiras
```

### 2. Set up Cloud SQL (PostgreSQL)

Create a Cloud SQL PostgreSQL instance in the GCP Console. Run `server/init.sql` to initialize the schema.

### 3. Deploy to Cloud Run

```bash
gcloud run deploy site-trincheiras \
  --image gcr.io/$PROJECT_ID/site-trincheiras \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --add-cloudsql-instances=$PROJECT_ID:us-central1:your-instance-name \
  --set-env-vars="DATABASE_URL=postgresql://USER:PASS@/trincheiras?host=/cloudsql/$PROJECT_ID:us-central1:your-instance-name"
```

---

## Stopping the Local Environment

```bash
# Stop and remove containers
docker compose down

# Stop and also delete database data
docker compose down -v
```

---

## License

ISC