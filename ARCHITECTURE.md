# Architecture Guide

A walkthrough of every folder, file, and how they all connect.

---

## What This App Does

An AI-powered fitness coaching platform for **hybrid athletes** — people who
run *and* lift. You log your workouts, the app computes your fitness/fatigue
metrics, and you can chat with an AI coach (Claude) that knows your training
history and answers questions or generates personalised multi-week plans.

---

## The Big Picture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Your Browser                             │
│                    React + TypeScript SPA                       │
└───────────────────────────┬─────────────────────────────────────┘
                            │  HTTP / JSON  (port 8000)
┌───────────────────────────▼─────────────────────────────────────┐
│                      FastAPI Backend                            │
│   /auth  /workouts  /analytics  /agent  (API routes)           │
└────┬──────────────┬──────────────────────┬───────────────────┬──┘
     │              │                      │                   │
     ▼              ▼                      ▼                   ▼
PostgreSQL      Celery Worker         Claude API         Sentence-
(main DB +    (background jobs)    (AI coaching &     Transformers
 pgvector)                          plan generation)   (embeddings)
     ▲              │
     │         Redis Queue
     └──────────────┘
   (worker writes results back to DB)
```

**Request flow in plain English:**

1. You open the app → React frontend loads from the same server (FastAPI serves the built React files).
2. You log a workout → React calls `POST /api/v1/workouts` → FastAPI validates the data and saves it to PostgreSQL → drops a job onto the **Redis queue**.
3. The **Celery worker** picks up the job → computes your TSS (training stress score), updates your fitness metrics (ATL/CTL/TSB) → writes results back to PostgreSQL.
4. You ask the AI coach a question → FastAPI fetches your recent workouts + pulls relevant training articles from the knowledge base (RAG) → sends everything to Claude → streams the answer back to you.

---

## Backend — `app/`

```
app/
├── main.py                ← FastAPI app entry point
├── config.py              ← All environment variable settings
├── core/
│   ├── exceptions.py      ← Custom HTTP exception classes
│   ├── logging.py         ← Structured JSON logging (structlog)
│   ├── middleware.py      ← Request timing + correlation IDs
│   └── security.py        ← JWT token creation/verification, password hashing
├── db/
│   ├── session.py         ← Database connection pool + get_db() dependency
│   └── repositories/
│       └── user_repo.py   ← Database queries for users (CRUD)
├── api/
│   └── v1/                ← All HTTP route handlers (see below)
├── models/                ← SQLAlchemy ORM table definitions (see below)
├── schemas/               ← Pydantic request/response shapes (see below)
├── pipeline/              ← Data processing + background jobs (see below)
├── rag/                   ← Knowledge base + retrieval system (see below)
└── agent/                 ← Claude AI coaching agent (see below)
```

### `app/main.py` — The Entry Point

Creates the FastAPI application, registers all the routes, mounts the built
React frontend as static files, and exposes two health-check endpoints:

- `GET /health` — always returns `{"status": "ok"}`
- `GET /health/ready` — checks database + Redis are reachable

When you run `docker-compose up` or `uvicorn app.main:app`, this is the file
that starts everything.

### `app/config.py` — Settings

Reads from your `.env` file. Every configurable value lives here — database
URL, Redis URL, Anthropic API key, JWT secret, token expiry times, etc.
Import `settings` anywhere in the app to access them.

---

## API Routes — `app/api/v1/`

These are the HTTP endpoints the React frontend calls. Every route requires
a valid JWT token (via the `get_current_user` dependency) except register/login.

```
app/api/v1/
├── auth.py       ← Register, login, refresh token, get/update profile
├── workouts.py   ← Log, list, view, edit, delete workouts
├── analytics.py  ← Fitness summary, ATL/CTL/TSB chart, weekly snapshots
├── agent.py      ← Ask the AI coach, generate a training plan
└── plans.py      ← List, view, and activate training plans
```

| File | Endpoints |
|------|-----------|
| `auth.py` | `POST /auth/register` `POST /auth/login` `POST /auth/refresh` `GET /auth/me` `PATCH /auth/me` |
| `workouts.py` | `POST /workouts` `GET /workouts` `GET /workouts/{id}` `PATCH /workouts/{id}` `DELETE /workouts/{id}` |
| `analytics.py` | `GET /analytics/summary` `GET /analytics/fitness-freshness` `GET /analytics/weekly` |
| `agent.py` | `POST /agent/coaching-query` `POST /agent/generate-plan` |
| `plans.py` | `GET /agent/plans` `GET /agent/plans/{id}` `PATCH /agent/plans/{id}/activate` |

---

## Database Models — `app/models/`

These Python classes define what the PostgreSQL tables look like. Each class = one table.

```
app/models/
├── user.py           ← users table
├── workout.py        ← workouts + workout_sets + run_splits tables
├── training_plan.py  ← training_plans + training_plan_items tables
├── document.py       ← documents table (RAG knowledge base)
└── analytics.py      ← analytics_snapshots table
```

### Table Overview

```
users
  id, email, password_hash, display_name
  fitness profile: max_hr, resting_hr, vo2max, ftp, weight, height
  training profile: goal, experience, weekly_hours_target
  → has many workouts, training_plans

workouts
  id, user_id, type (run/gym/cycle), status (pending/processed/quarantined)
  timing: started_at, duration_seconds
  run fields: distance_m, avg_hr, avg_pace_sec_per_km, elevation_gain_m
  gym fields: total_volume_kg
  computed by pipeline: tss, pace_zone, atl, ctl, tsb
  → has many workout_sets (gym), run_splits (run)

workout_sets            ← one row per exercise set in a gym session
  exercise, reps, weight_kg, is_warmup, set_order

run_splits              ← one row per km/mile split in a run
  split_number, distance_m, duration_seconds, avg_hr, avg_pace, cadence

training_plans
  id, user_id, goal, duration_weeks, status (draft/active/completed/archived)
  ai_explanation: the coach's reasoning for the plan
  → has many training_plan_items

training_plan_items     ← one row per session in the plan
  week_number, day_of_week, session_type, title, description
  targets: duration, distance, pace, hr_zone, rpe, exercises (JSONB)

documents               ← RAG knowledge base chunks
  content, embedding (384-dim vector), content_hash
  source_type: training_science / workout_history / user_profile
  metadata: title, article source, etc.

analytics_snapshots     ← one row per user per week (upserted nightly)
  week_start_date, total_workouts, run_km, gym_volume_kg, total_tss
  atl, ctl, tsb, avg_run_pace, longest_run_km
```

---

## Schemas — `app/schemas/`

Pydantic models that validate what comes *in* from the API and shape what goes
*out* in responses. Think of them as the contract between frontend and backend.

```
app/schemas/
├── auth.py       ← RegisterRequest, LoginRequest, TokenResponse, UserOut, ProfileUpdateRequest
├── workout.py    ← WorkoutCreateRequest, WorkoutOut, WorkoutListResponse, RunSplitOut, WorkoutSetOut
├── analytics.py  ← AnalyticsSummaryResponse, FitnessFreshnessResponse, WeeklySnapshotOut
└── agent.py      ← CoachingQueryRequest, CoachingQueryResponse, GeneratePlanRequest, TrainingPlanOut
```

---

## Pipeline — `app/pipeline/`

Background processing that runs *after* you save a workout. The API saves the
raw data and queues a job; the pipeline does the math.

```
app/pipeline/
├── ingestion.py   ← Entry point: validate workout data, save to DB, queue job
├── validators.py  ← Data quality checks — reject/quarantine/warn bad data
├── metrics.py     ← The actual maths: TSS, ATL/CTL/TSB, pace zones, 1RM
└── tasks.py       ← Celery job definitions (background workers run these)
```

### How a workout gets processed

```
POST /workouts
      │
      ▼
ingestion.py → validators.py
      │              │
      │         reject?  → return 422 to user
      │         quarantine? → save with status=quarantined
      │         ok? → save with status=pending
      │
      ▼
Redis queue (Celery task enqueued)
      │
      ▼  (background, ~seconds later)
tasks.py → metrics.py
      │         compute TSS (HR-based for runs, RPE-based for gym)
      │         compute pace zone (Z1–Z5)
      │         compute gym volume (sets × reps × weight)
      │
      ▼
Update workout in DB: status=processed, tss=X, pace_zone=Y …
Update analytics_snapshots: rebuild this week's ATL/CTL/TSB
```

### Key metrics explained

| Metric | What it means |
|--------|--------------|
| **TSS** | Training Stress Score — how hard a session was (100 = 1 hour at threshold) |
| **ATL** | Acute Training Load — 7-day rolling average of TSS (short-term fatigue) |
| **CTL** | Chronic Training Load — 42-day rolling average (long-term fitness) |
| **TSB** | Training Stress Balance = CTL − ATL. Positive = fresh, negative = fatigued |

---

## RAG (Knowledge Base) — `app/rag/`

RAG = Retrieval-Augmented Generation. Before asking Claude a question, we
pull relevant training science articles and your personal workout history
so Claude answers with *your* data, not generic advice.

```
app/rag/
├── embeddings.py  ← Turn text into 384-dimensional vectors (sentence-transformers)
├── chunker.py     ← Split articles/workouts into smaller pieces for indexing
├── indexer.py     ← Save chunks + their embeddings into PostgreSQL (pgvector)
├── retriever.py   ← Search for relevant chunks (semantic + keyword, combined with RRF)
└── prompts.py     ← The system prompt and templates sent to Claude
```

### How retrieval works

```
User question: "Why are my easy runs feeling hard?"
        │
        ▼
embeddings.py: convert question → 384-dim vector
        │
        ▼
retriever.py: hybrid search in documents table
  ├── semantic search: pgvector cosine similarity (finds conceptually similar chunks)
  └── keyword search:  pg_trgm trigram match  (finds exact phrase matches)
        │
        ▼
Reciprocal Rank Fusion (RRF): combine both result lists into one ranked list
        │
        ▼
Top chunks assembled into prompt context (capped at 2400 tokens)
        │
        ▼
Claude receives: your question + your athlete profile + top chunks
```

**Why hybrid?** Semantic search finds *concepts* ("fatigue", "overreaching")
even if the words don't match. Keyword search finds exact terms like "TSB < -20".
Combining both gives better results than either alone.

---

## AI Agent — `app/agent/`

The Claude integration. Uses Anthropic's native `tool_use` API — Claude can
call functions (tools) to look things up, rather than just generating text.

```
app/agent/
├── coach_agent.py  ← The agent loop: prompt → tool calls → prompt → answer
└── tools.py        ← Four tools Claude can call + their implementations
```

### Tools Claude can use

| Tool | What it does |
|------|-------------|
| `search_knowledge_base` | Hybrid search across training science articles |
| `get_user_stats` | Fetch your current CTL/ATL/TSB, profile, volume averages |
| `get_recent_workouts` | List your recent sessions with full metrics |
| `create_training_plan` | Write a multi-week plan to the database |

### Agent loop (how a coaching query works)

```
POST /agent/coaching-query  {"question": "Should I do a hard run today?"}
      │
      ▼
coach_agent.py:
  1. Pre-fetch your athlete profile + last 4 weeks of workouts
  2. Run hybrid RAG search on your question
  3. Build prompt: system prompt + your profile + RAG context + question
  4. Send to Claude (claude-sonnet-4-6)
      │
      ▼
Claude responds with tool_use: get_user_stats()
      │
      ▼
tools.py executes get_user_stats() → returns CTL=65, ATL=72, TSB=-7
      │
      ▼
Claude receives tool result, responds with more tool_use or final answer
      │  (up to 6 turns)
      ▼
Final answer: "Your TSB is -7, meaning you're slightly fatigued…"
  + sources: [article titles retrieved]
  + actions: ["Consider a Z2 run instead", "Take tomorrow as rest"]
```

---

## Database Migrations — `alembic/`

Alembic tracks changes to the database schema over time, like Git for your
tables. Each migration file describes what changed.

```
alembic/
├── env.py              ← Alembic config (async engine setup)
├── script.py.mako      ← Template for new migration files
└── versions/
    └── 0001_initial_schema.py  ← Creates ALL tables from scratch
```

`0001_initial_schema.py` creates every table listed in the models section above,
plus enables three PostgreSQL extensions:
- `uuid-ossp` — generates UUID primary keys
- `pgvector` — stores and searches 384-dim embedding vectors
- `pg_trgm` — trigram-based keyword search on document content

Run `alembic upgrade head` to apply all migrations to your database.

---

## Scripts — `scripts/`

One-off operational scripts, not part of the running app.

```
scripts/
└── seed_knowledge_base.py  ← Loads 7 training science articles into the RAG knowledge base
```

Run once after first setup:
```bash
python scripts/seed_knowledge_base.py
```

This populates the `documents` table with articles on: Zone 2 training, TSS/PMC,
progressive overload, hybrid athlete recovery, nutrition, overtraining recognition,
and running pace zones.

---

## Frontend — `frontend/`

A React + TypeScript single-page app. Vite builds it; FastAPI serves the built
files from `frontend/dist/` — so the whole product ships as one container.

```
frontend/
├── index.html
├── package.json        ← Dependencies (React, TanStack Query, Recharts, Tailwind, etc.)
└── src/
    ├── main.tsx        ← Bootstrap: React Router, TanStack Query, Auth provider
    ├── App.tsx         ← Route definitions + protected layout with sidebar
    ├── types/
    │   └── index.ts    ← TypeScript interfaces for every data shape
    ├── pages/          ← One file per screen (see below)
    ├── components/     ← Reusable UI pieces (see below)
    ├── api/            ← Functions that call the backend (see below)
    ├── hooks/          ← Shared React state logic (see below)
    └── lib/
        └── utils.ts    ← Formatting helpers (pace, duration, distance, dates)
```

### How routing works

```
App.tsx
  ├── /login        → Login.tsx         (public)
  ├── /register     → Register.tsx      (public)
  └── /             → ProtectedLayout   (requires login)
        ├── /dashboard    → Dashboard.tsx
        ├── /workouts     → Workouts.tsx
        ├── /log          → LogWorkout.tsx
        ├── /coaching     → Coaching.tsx
        ├── /plans        → Plans.tsx
        └── /settings     → Settings.tsx
```

The `ProtectedLayout` renders the `Sidebar` and checks `useAuth()` — if no
token is found, it redirects to `/login`.

---

### Pages — `frontend/src/pages/`

| File | What the user sees |
|------|--------------------|
| `Login.tsx` | Email + password form |
| `Register.tsx` | Sign-up with fitness profile (goal, HR, experience) |
| `Dashboard.tsx` | Weekly stats cards + 16-week fitness/freshness chart + recent workouts |
| `Workouts.tsx` | Paginated list of all sessions, filter by type, click to view details |
| `LogWorkout.tsx` | Form to log a new run or gym session |
| `Coaching.tsx` | Chat interface with the AI coach, shows sources + action items |
| `Plans.tsx` | List of generated training plans, expand to see week-by-week schedule |
| `Settings.tsx` | Edit your profile (weight, HR zones, goals, FTP) |

---

### API Layer — `frontend/src/api/`

Functions that make HTTP requests to the backend. They all use `client.ts`
which automatically attaches your JWT token to every request.

```
frontend/src/api/
├── client.ts      ← Axios instance: base URL + auth header injector + 401 redirect
├── auth.ts        ← register(), login(), me(), updateProfile()
├── workouts.ts    ← list(), get(), createRun(), createGym()
├── analytics.ts   ← summary(), fitnessFreshness(), weekly()
└── agent.ts       ← coachingQuery(), generatePlan(), listPlans(), getPlan(), activatePlan()
```

These map 1-to-1 with the backend routes:

```
frontend/src/api/workouts.ts → app/api/v1/workouts.py
frontend/src/api/agent.ts    → app/api/v1/agent.py + plans.py
frontend/src/api/analytics.ts → app/api/v1/analytics.py
frontend/src/api/auth.ts     → app/api/v1/auth.py
```

---

### Components — `frontend/src/components/`

Reusable UI building blocks used across multiple pages.

| File | What it is |
|------|------------|
| `Sidebar.tsx` | Fixed left nav with links to all pages + logout |
| `Badge.tsx` | Coloured pill label (run=blue, gym=purple, pending=yellow, etc.) |
| `StatCard.tsx` | Card showing a big number with a label (used on Dashboard) |
| `Spinner.tsx` | Loading spinner |
| `Toast.tsx` | Temporary notification (success/error, auto-dismisses) |
| `WorkoutDetail.tsx` | Modal showing full details of a single workout |

---

### Hooks — `frontend/src/hooks/`

Shared stateful logic extracted from components.

| File | What it does |
|------|-------------|
| `useAuth.tsx` | Provides `user`, `login()`, `logout()`, `isAuthenticated`. Wraps the whole app so any component can call `useAuth()`. |
| `useToast.tsx` | Provides `showToast()` so any component can trigger a toast notification. |

---

### Types — `frontend/src/types/index.ts`

TypeScript interfaces matching the backend's Pydantic schemas. If the backend
adds a field to a response, you add it here and TypeScript catches any
components that need updating.

Key interfaces: `User`, `Workout`, `RunSplit`, `WorkoutSet`,
`AnalyticsSnapshot`, `FitnessFreshnessPoint`, `TrainingPlan`,
`TrainingPlanDetail`, `PlanItem`, `CoachingResponse`

---

## Deployment — `docker/`

```
docker/
├── Dockerfile.api     ← Multi-stage: builds React frontend, then packages with FastAPI
└── Dockerfile.worker  ← Python only: runs the Celery background worker
```

`docker-compose.yml` (local dev) starts five services:

| Service | What it runs | Port |
|---------|-------------|------|
| `api` | FastAPI + React (uvicorn) | 8000 |
| `worker` | Celery worker (processes workout jobs) | — |
| `beat` | Celery Beat (runs nightly ATL/CTL/TSB rollup) | — |
| `db` | PostgreSQL 16 + pgvector | 5433 |
| `redis` | Redis 7 (job queue) | 6379 |

---

## Environment Variables — `.env`

Copy `.env.example` to `.env` and fill in the blanks:

| Variable | Required | What it's for |
|----------|----------|---------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `REDIS_URL` | Yes | Redis connection (used by the API) |
| `CELERY_BROKER_URL` | Yes | Redis connection (used by Celery) |
| `CELERY_RESULT_BACKEND` | Yes | Redis connection (stores job results) |
| `ANTHROPIC_API_KEY` | Yes | Your Anthropic API key for Claude |
| `SECRET_KEY` | Yes | JWT signing key — generate with `openssl rand -hex 32` |
| `ANTHROPIC_MODEL` | No | Defaults to `claude-sonnet-4-6` |
| `EMBEDDING_MODEL` | No | Defaults to `all-MiniLM-L6-v2` (local, no API key needed) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | Defaults to 15 |
| `REFRESH_TOKEN_EXPIRE_DAYS` | No | Defaults to 7 |
| `SENTRY_DSN` | No | Error tracking (leave blank for local dev) |

---

## Local Setup — Quick Start

```bash
# 1. Clone and enter the project
git clone <repo-url>
cd AI-Hybrid-Trainer

# 2. Copy and fill in environment variables
cp .env.example .env
# Edit .env: set ANTHROPIC_API_KEY and generate a SECRET_KEY

# 3. Start all services (PostgreSQL, Redis, API, workers)
docker-compose up

# 4. In a new terminal — run database migrations
alembic upgrade head

# 5. Seed the AI knowledge base (training science articles)
python scripts/seed_knowledge_base.py

# 6. Open the app
open http://localhost:8000
```
