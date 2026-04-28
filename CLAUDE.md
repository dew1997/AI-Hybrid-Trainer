# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
AI Hybrid Trainer — a web app for hybrid athletes (running + gym) that logs workouts, generates
AI-powered training plans from actual workout data, and provides an AI coaching chatbot.
Built by and for a solo hybrid athlete. Core pain point: balancing and progressively improving
both running and gym training over 2–3 month plan cycles.

## Stack
- **Backend**: FastAPI (Python 3.12), async SQLAlchemy + asyncpg
- **Database**: PostgreSQL 16 + pgvector extension
- **Queue**: Celery + Redis
- **AI**: OpenRouter (OpenAI-compatible) — model `openai/gpt-oss-20b:free` via `openai.AsyncOpenAI`. **Requires** `HTTP-Referer: http://localhost:8000` and `X-Title: AI Hybrid Trainer` headers on every completions call or returns 401.
- **Embeddings**: sentence-transformers `all-MiniLM-L6-v2` (local, no API key)
- **Frontend**: React 19 + TypeScript, Vite, TanStack Query, Recharts, Tailwind CSS v4, react-markdown
- **Deploy**: GCP Cloud Run + Cloud SQL

## Local Development

```bash
# Start all services
docker-compose up

# IMPORTANT: use 'up -d' not 'restart' to reload .env changes
docker-compose up -d api

# Run DB migrations
alembic upgrade head

# Seed RAG knowledge base (run once)
python scripts/seed_knowledge_base.py

# Seed demo account with 8 weeks of workout data
PYTHONPATH=. .venv/bin/python scripts/seed_demo_workouts.py

# Run API directly (without Docker)
uvicorn app.main:app --reload

# Frontend dev — changes need a rebuild + api restart
cd frontend && npm run build
docker-compose restart api   # for code changes (reloads via volume mount)
docker-compose up -d api     # for .env changes (full container recreate)
```

## Testing

```bash
# Unit tests (no DB required)
pytest tests/unit/ -v

# Run a single test
pytest tests/unit/test_pipeline_metrics.py::TestComputeAtlCtl -v

# Integration tests (needs test containers first)
docker-compose -f docker-compose.test.yml up -d
pytest tests/integration/ -v -m "not contract"

# Full UAT (requires docker-compose up + migrations + seeded KB)
python tests/uat/run_uat.py
```

## Linting & Type Checking

```bash
ruff check .          # lint
ruff format .         # format
mypy app/             # type-check
cd frontend && npm run lint
```

## Key Architecture Decisions

- **OpenRouter NOT Anthropic**: agent uses OpenRouter free LLMs via `openai.AsyncOpenAI` pointed at `https://openrouter.ai/api/v1`. Both `HTTP-Referer` and `X-Title` headers are required for free-tier models.
- **Plan generation brevity**: Tool schema enforces max 12-word session descriptions and 6-word titles. Without this, 8-week plans exceed the model's 8192-token output limit and truncate mid-JSON.
- **`persist: bool`** on `CoachingQueryRequest`: set `persist=False` for ephemeral calls (dashboard briefing) to skip `coaching_sessions` DB write.
- **`docker-compose restart` vs `up -d`**: `restart` keeps existing env vars. `up -d` recreates the container and picks up `.env` changes.
- **`index_elements` for analytics upsert**: constraint name `uq_analytics_user_week` never existed — the migration creates an unnamed UNIQUE constraint. Use `index_elements=["user_id", "week_start_date"]`.
- **`session_type` ENUM**: PostgreSQL enum values are `easy_run, tempo_run, interval_run, long_run, strength, mobility, rest, cross_training`. LLM sometimes returns plain `run`/`gym` — `_coerce_session_type()` in tools.py handles this.
- **plan `start_date`**: Set to the Monday of the current week when a plan is activated. All `TrainingPlanItem.actual_date` values are computed as `start_date + (week_number - 1) * 7 + (day_of_week - 1)` days.
- **pgvector in PostgreSQL**: no separate vector DB
- **Hybrid RAG**: semantic (pgvector cosine) + keyword (pg_trgm) + RRF

## Module Map

| Module | Purpose |
|--------|---------|
| `app/api/v1/` | FastAPI route handlers (auth, workouts, analytics, agent, plans) |
| `app/pipeline/` | Validation, metrics (TSS/ATL/CTL), Celery tasks, workout ingestion + auto-link |
| `app/rag/` | Embeddings, chunking, hybrid retrieval, prompts |
| `app/agent/` | OpenRouter agent loop + tool implementations |
| `app/models/` | SQLAlchemy ORM models |
| `app/schemas/` | Pydantic request/response models |
| `app/db/repositories/` | Database access layer |
| `alembic/versions/` | DB migrations (0001 initial schema, 0002 coaching sessions) |
| `scripts/` | Operational scripts (seed KB, seed demo workouts) |
| `tests/unit/` | Pure unit tests (no DB) |
| `tests/integration/` | API tests with real DB |
| `tests/uat/` | End-to-end UAT against live local server |
| `frontend/src/pages/` | React pages (Dashboard, Workouts, LogWorkout, Coaching, Plans, Settings) |
| `frontend/src/api/` | Axios API clients (workouts, agent, analytics, auth) |

## Key API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /workouts/exercises/history` | Last session's sets per exercise (for auto-populate) — must be before `/{id}` |
| `GET /workouts/exercises/prs` | Personal best 1RM per exercise — must be before `/{id}` |
| `GET /agent/plans/active` | Returns active plan with `actual_date` per item — must be before `/{id}` |
| `PATCH /agent/plans/items/{id}/complete` | Toggle item done/undone — must be before `/{plan_id}` |
| `POST /agent/coaching-query` | AI coaching — pass `persist: false` for ephemeral calls |

## Demo Account
- Email: `demo@aihybridtrainer.com` / Password: `Demo1234!`
- 8 weeks of seeded PPL gym + run data
- Re-seed: delete workouts via SQL first, then `PYTHONPATH=. .venv/bin/python scripts/seed_demo_workouts.py`

## Environment Variables
See `.env.example`. Key ones:
- `OPENROUTER_API_KEY` — required (get free key at openrouter.ai)
- `OPENROUTER_MODEL` — defaults to `openai/gpt-oss-20b:free`
- `SECRET_KEY` — generate with `openssl rand -hex 32`

## Commit Convention
Semantic commits with elaborated body: `feat:`, `fix:`, `chore:`, `docs:`, `test:`, `ci:`, `refactor:`
