"""initial schema

Revision ID: 0001
Revises:
Create Date: 2025-01-01 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # ENUMS
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE workout_type AS ENUM ('run', 'gym', 'cycle', 'other');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE workout_status AS ENUM ('pending', 'processed', 'failed', 'quarantined');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE doc_source_type AS ENUM ('training_science', 'workout_history', 'user_profile');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE plan_status AS ENUM ('draft', 'active', 'completed', 'archived');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE session_type AS ENUM (
                'easy_run', 'tempo_run', 'interval_run', 'long_run',
                'strength', 'mobility', 'rest', 'cross_training'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """)

    # USERS
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(100)),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("date_of_birth", sa.Date),
        sa.Column("weight_kg", sa.Numeric(5, 2)),
        sa.Column("height_cm", sa.Numeric(5, 1)),
        sa.Column("resting_hr", sa.SmallInteger),
        sa.Column("max_hr", sa.SmallInteger),
        sa.Column("ftp_watts", sa.SmallInteger),
        sa.Column("vo2max_estimate", sa.Numeric(4, 1)),
        sa.Column("primary_goal", sa.String(50)),
        sa.Column("experience_level", sa.String(20)),
        sa.Column("weekly_hours_target", sa.Numeric(4, 1)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("idx_users_email", "users", ["email"])

    # WORKOUTS
    op.create_table(
        "workouts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("workout_type", sa.Enum("run", "gym", "cycle", "other", name="workout_type"), nullable=False),
        sa.Column("status", sa.Enum("pending", "processed", "failed", "quarantined", name="workout_status"), nullable=False, server_default="pending"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
        sa.Column("duration_seconds", sa.Integer),
        sa.Column("notes", sa.Text),
        sa.Column("perceived_effort", sa.SmallInteger),
        sa.Column("source", sa.String(50), server_default="manual"),
        sa.Column("raw_payload", postgresql.JSONB),
        # Run fields
        sa.Column("distance_meters", sa.Numeric(10, 2)),
        sa.Column("avg_pace_sec_per_km", sa.Numeric(8, 2)),
        sa.Column("avg_hr", sa.SmallInteger),
        sa.Column("max_hr", sa.SmallInteger),
        sa.Column("elevation_gain_m", sa.Numeric(8, 2)),
        sa.Column("route_name", sa.String(200)),
        # Gym fields
        sa.Column("total_volume_kg", sa.Numeric(10, 2)),
        sa.Column("muscle_groups", postgresql.ARRAY(sa.String)),
        sa.Column("workout_template", sa.String(100)),
        # Computed
        sa.Column("tss", sa.Numeric(8, 2)),
        sa.Column("fatigue_score", sa.Numeric(5, 2)),
        sa.Column("fitness_score", sa.Numeric(5, 2)),
        sa.Column("pace_zone", sa.String(20)),
        sa.Column("intensity_factor", sa.Numeric(4, 3)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_workouts_user_id", "workouts", ["user_id"])
    op.create_index("idx_workouts_started_at", "workouts", ["user_id", sa.text("started_at DESC")])
    op.create_index("idx_workouts_type", "workouts", ["user_id", "workout_type"])

    # WORKOUT SETS
    op.create_table(
        "workout_sets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("workout_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workouts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("set_number", sa.SmallInteger, nullable=False),
        sa.Column("exercise_name", sa.String(100), nullable=False),
        sa.Column("reps", sa.SmallInteger),
        sa.Column("weight_kg", sa.Numeric(6, 2)),
        sa.Column("duration_seconds", sa.Integer),
        sa.Column("rest_seconds", sa.SmallInteger),
        sa.Column("is_warmup", sa.Boolean, server_default="false"),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_workout_sets_workout_id", "workout_sets", ["workout_id"])

    # RUN SPLITS
    op.create_table(
        "run_splits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("workout_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workouts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("split_number", sa.SmallInteger, nullable=False),
        sa.Column("split_unit", sa.String(10), server_default="km", nullable=False),
        sa.Column("distance_m", sa.Numeric(8, 2)),
        sa.Column("duration_seconds", sa.Integer, nullable=False),
        sa.Column("avg_hr", sa.SmallInteger),
        sa.Column("avg_pace_sec_per_km", sa.Numeric(8, 2)),
        sa.Column("elevation_gain_m", sa.Numeric(6, 2)),
        sa.Column("cadence_spm", sa.SmallInteger),
        sa.Column("power_watts", sa.SmallInteger),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_run_splits_workout_id", "run_splits", ["workout_id"])

    # ANALYTICS SNAPSHOTS
    op.create_table(
        "analytics_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("week_start_date", sa.Date, nullable=False),
        sa.Column("total_workouts", sa.SmallInteger, server_default="0"),
        sa.Column("run_workouts", sa.SmallInteger, server_default="0"),
        sa.Column("gym_workouts", sa.SmallInteger, server_default="0"),
        sa.Column("total_run_km", sa.Numeric(8, 2), server_default="0"),
        sa.Column("total_gym_volume_kg", sa.Numeric(12, 2), server_default="0"),
        sa.Column("total_duration_min", sa.Integer, server_default="0"),
        sa.Column("weekly_tss", sa.Numeric(8, 2)),
        sa.Column("acute_load", sa.Numeric(8, 2)),
        sa.Column("chronic_load", sa.Numeric(8, 2)),
        sa.Column("training_stress_balance", sa.Numeric(8, 2)),
        sa.Column("avg_pace_sec_per_km", sa.Numeric(8, 2)),
        sa.Column("avg_hr_run", sa.SmallInteger),
        sa.Column("longest_run_km", sa.Numeric(6, 2)),
        sa.Column("easy_run_pct", sa.Numeric(5, 2)),
        sa.Column("avg_session_volume_kg", sa.Numeric(10, 2)),
        sa.Column("top_lift_1rm_squat", sa.Numeric(6, 2)),
        sa.Column("top_lift_1rm_bench", sa.Numeric(6, 2)),
        sa.Column("avg_rpe", sa.Numeric(4, 2)),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("user_id", "week_start_date", name="uq_analytics_user_week"),
    )
    op.create_index("idx_analytics_user_week", "analytics_snapshots", ["user_id", sa.text("week_start_date DESC")])

    # DOCUMENTS
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("source_type", sa.Enum("training_science", "workout_history", "user_profile", name="doc_source_type"), nullable=False),
        sa.Column("title", sa.String(500)),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("chunk_index", sa.SmallInteger, server_default="0"),
        sa.Column("parent_doc_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("metadata", postgresql.JSONB, server_default="{}"),
        sa.Column("embedding", sa.Text),  # placeholder; pgvector type applied below
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    # Alter embedding column to proper vector type after table creation
    op.execute("ALTER TABLE documents DROP COLUMN embedding")
    op.execute("ALTER TABLE documents ADD COLUMN embedding vector(1536)")
    op.create_index("idx_documents_source_type", "documents", ["source_type", "is_active"])
    op.create_index("idx_documents_user_id", "documents", ["user_id"])
    op.execute(
        "CREATE INDEX idx_documents_content_trgm ON documents USING gin (content gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX idx_documents_embedding ON documents "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50)"
    )

    # TRAINING PLANS
    op.create_table(
        "training_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.SmallInteger, nullable=False, server_default="1"),
        sa.Column("status", sa.Enum("draft", "active", "completed", "archived", name="plan_status"), nullable=False, server_default="draft"),
        sa.Column("goal", sa.Text, nullable=False),
        sa.Column("duration_weeks", sa.SmallInteger, nullable=False, server_default="4"),
        sa.Column("start_date", sa.Date),
        sa.Column("model_used", sa.String(100)),
        sa.Column("prompt_version", sa.String(20)),
        sa.Column("generation_metadata", postgresql.JSONB, server_default="{}"),
        sa.Column("ai_explanation", sa.Text),
        sa.Column("raw_llm_output", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_training_plans_user_id", "training_plans", ["user_id", "status"])

    # TRAINING PLAN ITEMS
    op.create_table(
        "training_plan_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("training_plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("week_number", sa.SmallInteger, nullable=False),
        sa.Column("day_of_week", sa.SmallInteger, nullable=False),
        sa.Column("session_type", sa.Enum("easy_run", "tempo_run", "interval_run", "long_run", "strength", "mobility", "rest", "cross_training", name="session_type"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("duration_min", sa.SmallInteger),
        sa.Column("target_distance_km", sa.Numeric(6, 2)),
        sa.Column("target_pace_min_per_km", sa.Numeric(5, 2)),
        sa.Column("target_hr_zone", sa.SmallInteger),
        sa.Column("target_rpe", sa.SmallInteger),
        sa.Column("exercises", postgresql.JSONB, server_default="[]"),
        sa.Column("is_completed", sa.Boolean, server_default="false"),
        sa.Column("completed_workout_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workouts.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_plan_items_plan_id", "training_plan_items", ["plan_id", "week_number", "day_of_week"])

    # updated_at trigger
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
        op.drop_table(table)
    for enum in ["workout_type", "workout_status", "doc_source_type", "plan_status", "session_type"]:
        op.execute(f"DROP TYPE IF EXISTS {enum}")
    op.execute("DROP FUNCTION IF EXISTS set_updated_at()")
