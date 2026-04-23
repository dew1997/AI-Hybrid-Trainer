"""initial schema

Revision ID: 0001
Revises:
Create Date: 2025-01-01 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.execute("CREATE TYPE workout_type AS ENUM ('run', 'gym', 'cycle', 'other')")
    op.execute("CREATE TYPE workout_status AS ENUM ('pending', 'processed', 'failed', 'quarantined')")
    op.execute("CREATE TYPE doc_source_type AS ENUM ('training_science', 'workout_history', 'user_profile')")
    op.execute("CREATE TYPE plan_status AS ENUM ('draft', 'active', 'completed', 'archived')")
    op.execute("CREATE TYPE session_type AS ENUM ('easy_run', 'tempo_run', 'interval_run', 'long_run', 'strength', 'mobility', 'rest', 'cross_training')")

    op.execute("""
        CREATE TABLE users (
            id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            email           VARCHAR(255) NOT NULL UNIQUE,
            hashed_password VARCHAR(255) NOT NULL,
            display_name    VARCHAR(100),
            is_active       BOOLEAN NOT NULL DEFAULT TRUE,
            date_of_birth   DATE,
            weight_kg       NUMERIC(5,2),
            height_cm       NUMERIC(5,1),
            resting_hr      SMALLINT,
            max_hr          SMALLINT,
            ftp_watts       SMALLINT,
            vo2max_estimate NUMERIC(4,1),
            primary_goal    VARCHAR(50),
            experience_level VARCHAR(20),
            weekly_hours_target NUMERIC(4,1),
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX idx_users_email ON users(email)")

    op.execute("""
        CREATE TABLE workouts (
            id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            workout_type        workout_type NOT NULL,
            status              workout_status NOT NULL DEFAULT 'pending',
            started_at          TIMESTAMPTZ NOT NULL,
            ended_at            TIMESTAMPTZ,
            duration_seconds    INTEGER,
            notes               TEXT,
            perceived_effort    SMALLINT CHECK (perceived_effort BETWEEN 1 AND 10),
            source              VARCHAR(50) DEFAULT 'manual',
            raw_payload         JSONB,
            distance_meters     NUMERIC(10,2),
            avg_pace_sec_per_km NUMERIC(8,2),
            avg_hr              SMALLINT,
            max_hr              SMALLINT,
            elevation_gain_m    NUMERIC(8,2),
            route_name          VARCHAR(200),
            total_volume_kg     NUMERIC(10,2),
            muscle_groups       TEXT[],
            workout_template    VARCHAR(100),
            tss                 NUMERIC(8,2),
            fatigue_score       NUMERIC(5,2),
            fitness_score       NUMERIC(5,2),
            pace_zone           VARCHAR(20),
            intensity_factor    NUMERIC(4,3),
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX idx_workouts_user_id ON workouts(user_id)")
    op.execute("CREATE INDEX idx_workouts_started_at ON workouts(user_id, started_at DESC)")
    op.execute("CREATE INDEX idx_workouts_type ON workouts(user_id, workout_type)")

    op.execute("""
        CREATE TABLE workout_sets (
            id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            workout_id      UUID NOT NULL REFERENCES workouts(id) ON DELETE CASCADE,
            set_number      SMALLINT NOT NULL,
            exercise_name   VARCHAR(100) NOT NULL,
            reps            SMALLINT,
            weight_kg       NUMERIC(6,2),
            duration_seconds INTEGER,
            rest_seconds    SMALLINT,
            is_warmup       BOOLEAN DEFAULT FALSE,
            notes           TEXT,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX idx_workout_sets_workout_id ON workout_sets(workout_id)")

    op.execute("""
        CREATE TABLE run_splits (
            id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            workout_id          UUID NOT NULL REFERENCES workouts(id) ON DELETE CASCADE,
            split_number        SMALLINT NOT NULL,
            split_unit          VARCHAR(10) NOT NULL DEFAULT 'km',
            distance_m          NUMERIC(8,2),
            duration_seconds    INTEGER NOT NULL,
            avg_hr              SMALLINT,
            avg_pace_sec_per_km NUMERIC(8,2),
            elevation_gain_m    NUMERIC(6,2),
            cadence_spm         SMALLINT,
            power_watts         SMALLINT,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX idx_run_splits_workout_id ON run_splits(workout_id)")

    op.execute("""
        CREATE TABLE analytics_snapshots (
            id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id                 UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            week_start_date         DATE NOT NULL,
            total_workouts          SMALLINT DEFAULT 0,
            run_workouts            SMALLINT DEFAULT 0,
            gym_workouts            SMALLINT DEFAULT 0,
            total_run_km            NUMERIC(8,2) DEFAULT 0,
            total_gym_volume_kg     NUMERIC(12,2) DEFAULT 0,
            total_duration_min      INTEGER DEFAULT 0,
            weekly_tss              NUMERIC(8,2),
            acute_load              NUMERIC(8,2),
            chronic_load            NUMERIC(8,2),
            training_stress_balance NUMERIC(8,2),
            avg_pace_sec_per_km     NUMERIC(8,2),
            avg_hr_run              SMALLINT,
            longest_run_km          NUMERIC(6,2),
            easy_run_pct            NUMERIC(5,2),
            avg_session_volume_kg   NUMERIC(10,2),
            top_lift_1rm_squat      NUMERIC(6,2),
            top_lift_1rm_bench      NUMERIC(6,2),
            avg_rpe                 NUMERIC(4,2),
            computed_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (user_id, week_start_date)
        )
    """)
    op.execute("CREATE INDEX idx_analytics_user_week ON analytics_snapshots(user_id, week_start_date DESC)")

    op.execute("""
        CREATE TABLE documents (
            id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
            source_type     doc_source_type NOT NULL,
            title           VARCHAR(500),
            content         TEXT NOT NULL,
            content_hash    CHAR(64) NOT NULL,
            chunk_index     SMALLINT DEFAULT 0,
            parent_doc_id   UUID REFERENCES documents(id),
            metadata        JSONB DEFAULT '{}',
            embedding       vector(384),
            is_active       BOOLEAN NOT NULL DEFAULT TRUE,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX idx_documents_source_type ON documents(source_type, is_active)")
    op.execute("CREATE INDEX idx_documents_user_id ON documents(user_id)")
    op.execute("CREATE INDEX idx_documents_content_trgm ON documents USING gin(content gin_trgm_ops)")
    op.execute("CREATE INDEX idx_documents_embedding ON documents USING ivfflat(embedding vector_cosine_ops) WITH (lists = 50)")

    op.execute("""
        CREATE TABLE training_plans (
            id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            version             SMALLINT NOT NULL DEFAULT 1,
            status              plan_status NOT NULL DEFAULT 'draft',
            goal                TEXT NOT NULL,
            duration_weeks      SMALLINT NOT NULL DEFAULT 4,
            start_date          DATE,
            model_used          VARCHAR(100),
            prompt_version      VARCHAR(20),
            generation_metadata JSONB DEFAULT '{}',
            ai_explanation      TEXT,
            raw_llm_output      JSONB,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX idx_training_plans_user_id ON training_plans(user_id, status)")

    op.execute("""
        CREATE TABLE training_plan_items (
            id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            plan_id                 UUID NOT NULL REFERENCES training_plans(id) ON DELETE CASCADE,
            week_number             SMALLINT NOT NULL,
            day_of_week             SMALLINT NOT NULL CHECK (day_of_week BETWEEN 1 AND 7),
            session_type            session_type NOT NULL,
            title                   VARCHAR(200) NOT NULL,
            description             TEXT,
            duration_min            SMALLINT,
            target_distance_km      NUMERIC(6,2),
            target_pace_min_per_km  NUMERIC(5,2),
            target_hr_zone          SMALLINT,
            target_rpe              SMALLINT,
            exercises               JSONB DEFAULT '[]',
            is_completed            BOOLEAN DEFAULT FALSE,
            completed_workout_id    UUID REFERENCES workouts(id),
            created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX idx_plan_items_plan_id ON training_plan_items(plan_id, week_number, day_of_week)")

    op.execute("""
        CREATE OR REPLACE FUNCTION set_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
        $$ LANGUAGE plpgsql
    """)
    for table in ["users", "workouts", "analytics_snapshots", "documents", "training_plans", "training_plan_items"]:
        op.execute(f"""
            CREATE TRIGGER trg_{table}_updated_at
            BEFORE UPDATE ON {table}
            FOR EACH ROW EXECUTE FUNCTION set_updated_at()
        """)


def downgrade() -> None:
    for table in ["training_plan_items", "training_plans", "documents",
                  "analytics_snapshots", "run_splits", "workout_sets", "workouts", "users"]:
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
    for enum in ["workout_type", "workout_status", "doc_source_type", "plan_status", "session_type"]:
        op.execute(f"DROP TYPE IF EXISTS {enum}")
    op.execute("DROP FUNCTION IF EXISTS set_updated_at()")
