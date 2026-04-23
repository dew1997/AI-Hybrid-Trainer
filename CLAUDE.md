# AI Hybrid Training Intelligence Platform

## Project Overview
Production-grade AI fitness coaching platform. Tracks hybrid training (running + gym),
processes performance data via a Celery pipeline, and uses Claude + RAG to generate
coaching insights and training plans via an AI agent.

## Stack
- **Backend**: FastAPI (Python 3.12), async SQLAlchemy + asyncpg
- **Database**: PostgreSQL 16 + pgvector extension
- **Queue**: Celery + Redis
- **AI**: Anthropic Claude claude-sonnet-4-6 (agent), OpenAI text-embedding-3-small (RAG)
- **Deploy**: GCP Cloud Run + Cloud SQL

## Local Development
```bash
# Start all services
docker-compose up

# Run DB migrations (first time)
alembic upgrade head

# Seed RAG knowledge base
python scripts/seed_knowledge_base.py

# Run API directly
uvicorn app.main:app --reload

# Run tests
pytest tests/unit/ -v
pytest tests/integration/ -v -m "not contract"
```

## Key Architecture Decisions
- **pgvector in PostgreSQL**: no separate vector DB — keeps infra simple for solo dev
- **Hybrid RAG**: semantic + keyword (pg_trgm) + RRF for better recall than naive vector search
- **Native Claude tool_use**: no LangChain; direct Anthropic API for simplicity + reliability
- **Three-tier validation**: reject/quarantine/warn avoids hard failures on imperfect data
- **ATL/CTL/TSB**: Banister impulse-response model for training load management

## Module Map
| Module | Purpose |
|--------|---------|
| `app/api/v1/` | FastAPI route handlers |
| `app/pipeline/` | Validation, metrics (TSS/ATL/CTL), Celery tasks |
| `app/rag/` | Embeddings, chunking, hybrid retrieval, prompts |
| `app/agent/` | Claude tool_use agent loop + tool implementations |
| `app/models/` | SQLAlchemy ORM models |
| `app/schemas/` | Pydantic request/response models |
| `app/db/repositories/` | Database access layer |
| `alembic/versions/` | Database migrations |
| `scripts/` | One-off operational scripts |
| `tests/unit/` | Pure unit tests (no DB required) |
| `tests/integration/` | API tests with real DB |
| `tests/contract/` | LLM API contract tests (marked @pytest.mark.contract) |

## Environment Variables
See `.env.example` for all required variables.
Never commit `.env` — use `.env.example` as the template.

## Commit Convention
Semantic commits: `feat:`, `fix:`, `chore:`, `docs:`, `test:`, `ci:`, `refactor:`
