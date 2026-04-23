# AI Hybrid Training Intelligence Platform

A production-grade AI fitness coaching platform that tracks hybrid training (running + gym),
processes performance data through a real data pipeline, and uses an LLM agent + RAG system
to generate evidence-based coaching insights and personalised training plans.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                       FASTAPI APPLICATION                            │
│  /auth    /workouts    /analytics    /agent    /health               │
└──────────────────────┬───────────────────────┬──────────────────────┘
                       │ enqueue                │ call
           ┌───────────▼──────────┐   ┌────────▼──────────┐
           │    CELERY WORKER     │   │   CLAUDE AGENT     │
           │  TSS · ATL/CTL/TSB  │   │  tool_use loop     │
           │  Pace zones · 1RM   │   │  max 6 turns       │
           └───────────┬──────────┘   └────────┬──────────┘
                       │                        │
           ┌───────────▼────────────────────────▼──────────┐
           │              POSTGRESQL + pgvector             │
           │  users · workouts · analytics_snapshots        │
           │  training_plans · documents + embeddings        │
           └────────────────────────────────────────────────┘
                       ▲                        │
           ┌───────────┴──────────┐   ┌─────────▼──────────┐
           │        REDIS         │   │  ANTHROPIC API      │
           │  Celery broker       │   │  Claude Sonnet 4.6  │
           └──────────────────────┘   └────────────────────┘
```

## Key Technical Features

| Feature | Detail |
|---------|--------|
| **RAG hybrid search** | pgvector cosine similarity + pg_trgm trigram, merged via Reciprocal Rank Fusion |
| **ATL/CTL/TSB model** | Banister impulse-response model for training load management |
| **Claude tool_use agent** | Multi-turn agentic loop using native Anthropic API, no LangChain |
| **Three-tier validation** | reject / quarantine / warn — handles real-world dirty data gracefully |
| **Pipeline idempotency** | Celery retries, workout status field, UPSERT for analytics |
| **Async FastAPI** | asyncpg + SQLAlchemy 2.0 async for maximum I/O throughput |

## Getting Started

### Prerequisites
- Docker + Docker Compose
- Python 3.12+
- Anthropic API key
- OpenAI API key (for embeddings)

### Local Development

```bash
# 1. Clone and configure
git clone https://github.com/dew1997/AI-Hybrid-Trainer.git
cd AI-Hybrid-Trainer
cp .env.example .env
# Edit .env with your API keys

# 2. Start all services
docker-compose up -d

# 3. Run DB migrations
alembic upgrade head

# 4. Seed RAG knowledge base
python scripts/seed_knowledge_base.py

# 5. API is live at http://localhost:8000
# Swagger docs: http://localhost:8000/docs
```

### Run Tests

```bash
pip install -r requirements-dev.txt
pytest tests/unit/ -v
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/register` | Create account |
| POST | `/api/v1/auth/login` | Get JWT tokens |
| POST | `/api/v1/workouts` | Log a run or gym session |
| GET | `/api/v1/analytics/fitness-freshness` | ATL/CTL/TSB performance chart |
| POST | `/api/v1/agent/coaching-query` | AI coaching question |
| POST | `/api/v1/agent/generate-plan` | Generate 4-week training plan |

Full API docs available at `/docs` when running locally.

## Project Structure

```
app/
├── api/v1/          Route handlers (auth, workouts, analytics, agent)
├── pipeline/        Validation · TSS/ATL/CTL metrics · Celery tasks
├── rag/             Embeddings · chunking · hybrid retrieval · prompts
├── agent/           Claude tool_use loop · tool implementations
├── models/          SQLAlchemy ORM (users, workouts, analytics, documents, plans)
├── schemas/         Pydantic request/response models
└── db/repositories/ Database access layer
```

## Tech Stack

| Component | Technology | Reason |
|-----------|-----------|--------|
| API | FastAPI 0.115 | Async-native, auto-generated OpenAPI docs |
| Database | PostgreSQL 16 + pgvector | Vector search without extra infrastructure |
| Embeddings | text-embedding-3-small (OpenAI) | Best retrieval/cost ratio |
| LLM | Claude claude-sonnet-4-6 (Anthropic) | Superior tool_use reliability |
| Task queue | Celery + Redis | Industry standard, observable, retriable |
| Deployment | GCP Cloud Run + Cloud SQL | Serverless containers, scales to zero |

## Deployment

CI/CD via GitHub Actions:
- **CI** (every PR): ruff lint → mypy → unit tests → integration tests → coverage check
- **Deploy** (merge to main): build Docker images → push to Artifact Registry → run migrations → deploy to Cloud Run

## License
MIT
