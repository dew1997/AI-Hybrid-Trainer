import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, SmallInteger, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.user import User


class AnalyticsSnapshot(Base):
    __tablename__ = "analytics_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    week_start_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Volume
    total_workouts: Mapped[int] = mapped_column(SmallInteger, default=0)
    run_workouts: Mapped[int] = mapped_column(SmallInteger, default=0)
    gym_workouts: Mapped[int] = mapped_column(SmallInteger, default=0)
    total_run_km: Mapped[float] = mapped_column(Numeric(8, 2), default=0)
    total_gym_volume_kg: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    total_duration_min: Mapped[int] = mapped_column(SmallInteger, default=0)

    # Load metrics
    weekly_tss: Mapped[float | None] = mapped_column(Numeric(8, 2))
    acute_load: Mapped[float | None] = mapped_column(Numeric(8, 2))
    chronic_load: Mapped[float | None] = mapped_column(Numeric(8, 2))
    training_stress_balance: Mapped[float | None] = mapped_column(Numeric(8, 2))

    # Running metrics
    avg_pace_sec_per_km: Mapped[float | None] = mapped_column(Numeric(8, 2))
    avg_hr_run: Mapped[int | None] = mapped_column(SmallInteger)
    longest_run_km: Mapped[float | None] = mapped_column(Numeric(6, 2))
    easy_run_pct: Mapped[float | None] = mapped_column(Numeric(5, 2))

    # Gym metrics
    avg_session_volume_kg: Mapped[float | None] = mapped_column(Numeric(10, 2))
    top_lift_1rm_squat: Mapped[float | None] = mapped_column(Numeric(6, 2))
    top_lift_1rm_bench: Mapped[float | None] = mapped_column(Numeric(6, 2))

    avg_rpe: Mapped[float | None] = mapped_column(Numeric(4, 2))
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship()
