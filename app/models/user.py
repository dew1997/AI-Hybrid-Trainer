import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, Numeric, SmallInteger, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Fitness profile
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    weight_kg: Mapped[float | None] = mapped_column(Numeric(5, 2))
    height_cm: Mapped[float | None] = mapped_column(Numeric(5, 1))
    resting_hr: Mapped[int | None] = mapped_column(SmallInteger)
    max_hr: Mapped[int | None] = mapped_column(SmallInteger)
    ftp_watts: Mapped[int | None] = mapped_column(SmallInteger)
    vo2max_estimate: Mapped[float | None] = mapped_column(Numeric(4, 1))
    primary_goal: Mapped[str | None] = mapped_column(String(50))
    experience_level: Mapped[str | None] = mapped_column(String(20))
    weekly_hours_target: Mapped[float | None] = mapped_column(Numeric(4, 1))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    workouts: Mapped[list["Workout"]] = relationship(back_populates="user", lazy="select")
    training_plans: Mapped[list["TrainingPlan"]] = relationship(
        back_populates="user", lazy="select"
    )
