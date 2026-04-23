import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    ARRAY,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
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

WorkoutTypeEnum = Enum("run", "gym", "cycle", "other", name="workout_type")
WorkoutStatusEnum = Enum("pending", "processed", "failed", "quarantined", name="workout_status")


class Workout(Base):
    __tablename__ = "workouts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workout_type: Mapped[str] = mapped_column(WorkoutTypeEnum, nullable=False)
    status: Mapped[str] = mapped_column(WorkoutStatusEnum, nullable=False, default="pending")

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)
    perceived_effort: Mapped[int | None] = mapped_column(SmallInteger)
    source: Mapped[str] = mapped_column(String(50), default="manual")
    raw_payload: Mapped[dict | None] = mapped_column(JSONB)

    # Run-specific
    distance_meters: Mapped[float | None] = mapped_column(Numeric(10, 2))
    avg_pace_sec_per_km: Mapped[float | None] = mapped_column(Numeric(8, 2))
    avg_hr: Mapped[int | None] = mapped_column(SmallInteger)
    max_hr: Mapped[int | None] = mapped_column(SmallInteger)
    elevation_gain_m: Mapped[float | None] = mapped_column(Numeric(8, 2))
    route_name: Mapped[str | None] = mapped_column(String(200))

    # Gym-specific
    total_volume_kg: Mapped[float | None] = mapped_column(Numeric(10, 2))
    muscle_groups: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    workout_template: Mapped[str | None] = mapped_column(String(100))

    # Computed pipeline fields
    tss: Mapped[float | None] = mapped_column(Numeric(8, 2))
    fatigue_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    fitness_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    pace_zone: Mapped[str | None] = mapped_column(String(20))
    intensity_factor: Mapped[float | None] = mapped_column(Numeric(4, 3))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="workouts")
    splits: Mapped[list["RunSplit"]] = relationship(
        back_populates="workout", cascade="all, delete-orphan", lazy="select"
    )
    sets: Mapped[list["WorkoutSet"]] = relationship(
        back_populates="workout", cascade="all, delete-orphan", lazy="select"
    )


class WorkoutSet(Base):
    __tablename__ = "workout_sets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workout_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workouts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    set_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    exercise_name: Mapped[str] = mapped_column(String(100), nullable=False)
    reps: Mapped[int | None] = mapped_column(SmallInteger)
    weight_kg: Mapped[float | None] = mapped_column(Numeric(6, 2))
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    rest_seconds: Mapped[int | None] = mapped_column(SmallInteger)
    is_warmup: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    workout: Mapped["Workout"] = relationship(back_populates="sets")


class RunSplit(Base):
    __tablename__ = "run_splits"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workout_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workouts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    split_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    split_unit: Mapped[str] = mapped_column(String(10), default="km", nullable=False)
    distance_m: Mapped[float | None] = mapped_column(Numeric(8, 2))
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_hr: Mapped[int | None] = mapped_column(SmallInteger)
    avg_pace_sec_per_km: Mapped[float | None] = mapped_column(Numeric(8, 2))
    elevation_gain_m: Mapped[float | None] = mapped_column(Numeric(6, 2))
    cadence_spm: Mapped[int | None] = mapped_column(SmallInteger)
    power_watts: Mapped[int | None] = mapped_column(SmallInteger)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    workout: Mapped["Workout"] = relationship(back_populates="splits")
