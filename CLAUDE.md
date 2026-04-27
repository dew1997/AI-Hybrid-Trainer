# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
Production-grade AI fitness coaching platform. Tracks hybrid training (running + gym),
processes performance data via a Celery pipeline, and uses an LLM + RAG to generate
coaching insights and training plans via an AI agent.

## Stack
- **Backend**: FastAPI (Python 3.12), async SQLAlchemy + asyncpg
- **Database**: PostgreSQL 16 + pgvector extension
- **Queue**: Celery + Redis
- **AI**: OpenRouter API (OpenAI-compatible, default model `meta-llama/llama-3.3-70b-instruct:free`), sentence-transformers all-MiniLM-L6-v2 (RAG embeddings, local)
- **Frontend**: React 19 + TypeScript, Vite, TanStack Query, Recharts, Tailwind CSS v4
- **Deploy**: GCP Cloud Run + Cloud SQL

## Local Development

```bash
# Start all services
docker-compose up

# Run DB migrations (first time or after new migration)
alembic upgrade head

# Seed RAG knowledge base (run once after first setup)
python scripts/seed_knowledge_base.py

# Run API directly (without Docker)
uvicorn app.main:app --reload

# Frontend dev server (hot reload on port 5173)
cd frontend && npm run dev

# Build frontend (outputs to frontend/dist/, served by FastAPI)
cd frontend && npm run build
```

## Testing

```bash
# Unit tests (no DB required)
pytest tests/unit/ -v

# Run a single test
pytest tests/unit/test_pipeline_metrics.py::test_tss_calculation -v

# Integration tests — need test DB + Redis first:
docker-compose -f docker-compose.test.yml up -d
pytest tests/integration/ -v -m "not contract"

# Contract tests (calls real LLM API — costs tokens)
pytest tests/contract/ -v -m contract

# Full coverage report (unit + integration combined)
pytest tests/unit/ tests/integration/ -v -m "not contract" --cov=app --cov-report=term-missing

# End-to-end UAT (requires docker-compose up + migrations + seeded KB)
python tests/uat/run_uat.py
```

Integration tests use a separate DB (`trainer_test` on port 5433) and Redis (port 6380)
defined in `docker-compose.test.yml`. `tests/conftest.py` sets these env vars automatically.

## Linting & Type Checking

```bash
ruff check .          # lint
ruff format .         # format
mypy app/             # type-check (strict=false, excludes alembic/ and tests/)
cd frontend && npm run lint   # ESLint
```

`pyproject.toml` configures ruff (line-length 100, rules E/F/I/N/W/UP) and mypy.

## Key Architecture Decisions
- **OpenRouter over Anthropic**: The agent uses OpenRouter's free LLMs via the OpenAI-compatible SDK (`openai.AsyncOpenAI` pointed at `https://openrouter.ai/api/v1`). No LangChain — direct API calls.
- **pgvector in PostgreSQL**: no separate vector DB — keeps infra simple for solo dev
- **Hybrid RAG**: semantic (pgvector cosine) + keyword (pg_trgm trigram) + RRF for better recall than naive vector search
- **Three-tier validation**: reject/quarantine/warn avoids hard failures on imperfect data
- **ATL/CTL/TSB**: Banister impulse-response model for training load management
- **Single-container frontend**: `docker/Dockerfile.api` builds React then packages with FastAPI; FastAPI serves `frontend/dist/` as static files

## Module Map
| Module | Purpose |
|--------|---------|
| `app/api/v1/` | FastAPI route handlers (auth, workouts, analytics, agent, plans) |
| `app/pipeline/` | Validation, metrics (TSS/ATL/CTL), Celery tasks |
| `app/rag/` | Embeddings, chunking, hybrid retrieval, prompts |
| `app/agent/` | OpenRouter agent loop + tool implementations |
| `app/models/` | SQLAlchemy ORM models |
| `app/schemas/` | Pydantic request/response models |
| `app/db/repositories/` | Database access layer |
| `alembic/versions/` | Database migrations |
| `scripts/` | One-off operational scripts |
| `tests/unit/` | Pure unit tests (no DB required) |
| `tests/integration/` | API tests with real DB |
| `tests/contract/` | LLM API contract tests (marked `@pytest.mark.contract`) |
| `tests/uat/` | End-to-end UAT script against live local server |
| `frontend/src/` | React SPA (pages/, components/, hooks/, api/) |

## Agent Loop
`app/agent/coach_agent.py` runs a multi-turn loop (max 6 turns) using the OpenAI chat completions format. The four tools in `app/agent/tools.py` are: `search_knowledge_base`, `get_user_stats`, `get_recent_workouts`, `create_training_plan`. The agent pre-fetches the athlete profile + RAG context before the first LLM call to reduce tool-call latency.

## Environment Variables
See `.env.example` for all required variables. Key ones:
- `OPENROUTER_API_KEY` — required for AI features (free at openrouter.ai)
- `SECRET_KEY` — generate with `openssl rand -hex 32`
- `DATABASE_URL` — asyncpg connection string
- `OPENROUTER_MODEL` — defaults to `meta-llama/llama-3.3-70b-instruct:free`

## Commit Convention
Semantic commits: `feat:`, `fix:`, `chore:`, `docs:`, `test:`, `ci:`, `refactor:`
