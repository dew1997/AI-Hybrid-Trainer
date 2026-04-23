import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.user import User

PlanStatusEnum = Enum("draft", "active", "completed", "archived", name="plan_status")
SessionTypeEnum = Enum(
    "easy_run", "tempo_run", "interval_run", "long_run",
    "strength", "mobility", "rest", "cross_training",
    name="session_type",
)


class TrainingPlan(Base):
    __tablename__ = "training_plans"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False)
    status: Mapped[str] = mapped_column(PlanStatusEnum, default="draft", nullable=False)
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    duration_weeks: Mapped[int] = mapped_column(SmallInteger, default=4, nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date)

    model_used: Mapped[str | None] = mapped_column(String(100))
    prompt_version: Mapped[str | None] = mapped_column(String(20))
    generation_metadata: Mapped[dict] = mapped_column(JSONB, default=dict)

    ai_explanation: Mapped[str | None] = mapped_column(Text)
    raw_llm_output: Mapped[dict | None] = mapped_column(JSONB)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="training_plans")
    items: Mapped[list["TrainingPlanItem"]] = relationship(
        back_populates="plan", cascade="all, delete-orphan", lazy="select"
    )


class TrainingPlanItem(Base):
    __tablename__ = "training_plan_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("training_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    week_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    day_of_week: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    session_type: Mapped[str] = mapped_column(SessionTypeEnum, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    duration_min: Mapped[int | None] = mapped_column(SmallInteger)
    target_distance_km: Mapped[float | None] = mapped_column(Numeric(6, 2))
    target_pace_min_per_km: Mapped[float | None] = mapped_column(Numeric(5, 2))
    target_hr_zone: Mapped[int | None] = mapped_column(SmallInteger)
    target_rpe: Mapped[int | None] = mapped_column(SmallInteger)

    exercises: Mapped[list] = mapped_column(JSONB, default=list)

    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_workout_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workouts.id"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    plan: Mapped["TrainingPlan"] = relationship(back_populates="items")
