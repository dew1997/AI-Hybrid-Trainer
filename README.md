# AI Hybrid Training Intelligence Platform

A production-grade AI fitness coaching platform that tracks hybrid training (running + gym),
processes performance data through a real data pipeline, and uses an LLM agent + RAG system
to generate evidence-based coaching insights and personalised training plans.

---

## Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                     REACT FRONTEND (Vite + TS)                         │
│  Dashboard · Workouts · Log · AI Coaching · Training Plans · Settings  │
└──────────────────────────────┬─────────────────────────────────────────┘
                               │ /api/v1 (proxied)
┌──────────────────────────────▼─────────────────────────────────────────┐
│                        FASTAPI APPLICATION                              │
│  /auth    /workouts    /analytics    /agent    /plans    /health        │
└──────────────────────┬────────────────────────┬────────────────────────┘
                       │ enqueue                 │ call
           ┌───────────▼──────────┐   ┌─────────▼──────────┐
           │    CELERY WORKER     │   │   CLAUDE AGENT      │
           │  TSS · ATL/CTL/TSB  │   │  tool_use loop      │
           │  Pace zones · 1RM   │   │  max 6 turns        │
           └───────────┬──────────┘   └─────────┬──────────┘
                       │                         │
           ┌───────────▼─────────────────────────▼──────────┐
           │              POSTGRESQL + pgvector              │
           │  users · workouts · analytics_snapshots         │
           │  training_plans · documents + embeddings         │
           └─────────────────────────────────────────────────┘
                       ▲                         │
           ┌───────────┴──────────┐   ┌──────────▼─────────┐
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
| **React + TanStack Query** | Type-safe SPA with cursor pagination, optimistic cache invalidation |

## Getting Started

### Prerequisites
- Docker + Docker Compose
- Python 3.12+
- Node.js 20+
- Anthropic API key

### Backend

```bash
# 1. Clone and configure
git clone https://github.com/dew1997/AI-Hybrid-Trainer.git
cd AI-Hybrid-Trainer
cp .env.example .env
# Edit .env with your API keys

# 2. Start all services (PostgreSQL, Redis, API, Celery)
docker-compose up -d

# 3. Run DB migrations
alembic upgrade head

# 4. Seed RAG knowledge base
python scripts/seed_knowledge_base.py

# 5. API is live at http://localhost:8000
# Swagger docs: http://localhost:8000/docs
```

### Frontend

```bash
cd frontend
npm install
npm run dev   # http://localhost:3000  (proxies /api → backend:8000)
```

### Run Tests

```bash
pip install -r requirements-dev.txt
pytest tests/unit/ -v
pytest tests/integration/ -v -m "not contract"
```

## Frontend

Built with React 19, TypeScript, Vite, TanStack Query v5, Tailwind CSS v4, and Recharts.

| Page | Description |
|------|-------------|
| **Dashboard** | Weekly TSS, run/gym volume, TSB form score; Performance Management Chart (CTL/ATL/TSB); last-4-weeks table; recent workouts |
| **Workouts** | Filterable list (all / run / gym) with cursor-based pagination; click any row to open a detail modal showing per-km splits or exercise sets |
| **Log Workout** | Unified form for runs (distance, pace, HR, elevation, splits) and gym sessions (template, muscle groups, dynamic sets table) |
| **AI Coaching** | Chat interface powered by Claude; suggested questions; action items and RAG source citations rendered per reply |
| **Training Plans** | Generate plans via Claude agent; expandable week-by-week view; activate plan with one click |
| **Settings** | Edit display name, weight, max HR, VO₂ max, primary goal, and experience level |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/register` | Create account |
| POST | `/api/v1/auth/login` | Get JWT tokens |
| GET | `/api/v1/auth/me` | Current user profile |
| PATCH | `/api/v1/auth/me` | Update profile |
| POST | `/api/v1/workouts` | Log a run or gym session |
| GET | `/api/v1/workouts` | List workouts (cursor pagination) |
| GET | `/api/v1/workouts/{id}` | Workout detail with splits/sets |
| GET | `/api/v1/analytics/summary` | Current week + trailing 4-week summary |
| GET | `/api/v1/analytics/fitness-freshness` | ATL/CTL/TSB chart data |
| POST | `/api/v1/agent/coaching-query` | AI coaching question |
| POST | `/api/v1/agent/generate-plan` | Generate training plan |
| GET | `/api/v1/agent/plans` | List training plans |
| PATCH | `/api/v1/agent/plans/{id}/activate` | Activate a plan |

Full API docs available at `/docs` when running locally.

## Project Structure

```
.
├── app/
│   ├── api/v1/          Route handlers (auth, workouts, analytics, agent, plans)
│   ├── pipeline/        Validation · TSS/ATL/CTL metrics · Celery tasks
│   ├── rag/             Embeddings · chunking · hybrid retrieval · prompts
│   ├── agent/           Claude tool_use loop · tool implementations
│   ├── models/          SQLAlchemy ORM (users, workouts, analytics, documents, plans)
│   ├── schemas/         Pydantic request/response models
│   └── db/repositories/ Database access layer
├── frontend/
│   └── src/
│       ├── api/         Typed axios wrappers (auth, workouts, analytics, agent)
│       ├── components/  Badge, Sidebar, Spinner, StatCard, Toast, WorkoutDetail
│       ├── hooks/       useAuth, useToast
│       ├── pages/       Dashboard, Workouts, LogWorkout, Coaching, Plans, Settings
│       ├── types/       Shared TypeScript interfaces
│       └── lib/         Formatters (pace, distance, duration, date)
├── alembic/             Database migrations
├── scripts/             Seed knowledge base
└── tests/
    ├── unit/            Pure unit tests (no DB)
    └── integration/     API tests with real DB
```

## Tech Stack

| Component | Technology | Reason |
|-----------|-----------|--------|
| Frontend | React 19 + Vite + TypeScript | Fast HMR, strict types end-to-end |
| State / data | TanStack Query v5 | Async cache, cursor pagination, auto-invalidation |
| Styling | Tailwind CSS v4 | Utility-first, dark theme, no runtime overhead |
| Charts | Recharts | Composable, works with Recharts ResponsiveContainer |
| API | FastAPI 0.115 | Async-native, auto-generated OpenAPI docs |
| Database | PostgreSQL 16 + pgvector | Vector search without extra infrastructure |
| Embeddings | all-MiniLM-L6-v2 (sentence-transformers) | Local inference, no API cost, 384-dim |
| LLM | Claude Sonnet 4.6 (Anthropic) | Superior tool_use reliability |
| Task queue | Celery + Redis | Industry standard, observable, retriable |
| Deployment | GCP Cloud Run + Cloud SQL | Serverless containers, scales to zero |

## Deployment

CI/CD via GitHub Actions:
- **CI** (every PR): ruff lint → mypy → unit tests → integration tests → coverage check
- **Deploy** (merge to main): build Docker images → push to Artifact Registry → run migrations → deploy to Cloud Run

## License
MIT
