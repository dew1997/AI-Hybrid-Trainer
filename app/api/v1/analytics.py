from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.analytics import AnalyticsSnapshot
from app.models.user import User
from app.schemas.analytics import (
    AnalyticsSummaryResponse,
    FitnessFreshnessPoint,
    FitnessFreshnessResponse,
    WeeklySnapshotOut,
)

router = APIRouter()


def _week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


@router.get("/summary", response_model=AnalyticsSummaryResponse)
async def analytics_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    today = date.today()
    current_week = _week_start(today)
    four_weeks_ago = current_week - timedelta(weeks=4)

    result = await db.execute(
        select(AnalyticsSnapshot)
        .where(
            AnalyticsSnapshot.user_id == current_user.id,
            AnalyticsSnapshot.week_start_date >= four_weeks_ago,
        )
        .order_by(AnalyticsSnapshot.week_start_date.desc())
    )
    snapshots = result.scalars().all()

    current = next((s for s in snapshots if s.week_start_date == current_week), None)
    trailing = [s for s in snapshots if s.week_start_date < current_week][:4]

    trend = None
    if len(trailing) >= 2:
        recent_tss = trailing[0].weekly_tss or 0
        older_tss = trailing[1].weekly_tss or 0
        if recent_tss > older_tss * 1.1:
            trend = "increasing"
        elif recent_tss < older_tss * 0.9:
            trend = "decreasing"
        else:
            trend = "stable"

    return AnalyticsSummaryResponse(
        current_week=WeeklySnapshotOut.model_validate(current) if current else None,
        trailing_4_weeks=[WeeklySnapshotOut.model_validate(s) for s in trailing],
        fitness_trend=trend,
    )


@router.get("/fitness-freshness", response_model=FitnessFreshnessResponse)
async def fitness_freshness(
    weeks: int = 12,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cutoff = _week_start(date.today()) - timedelta(weeks=weeks)
    result = await db.execute(
        select(AnalyticsSnapshot)
        .where(
            AnalyticsSnapshot.user_id == current_user.id,
            AnalyticsSnapshot.week_start_date >= cutoff,
        )
        .order_by(AnalyticsSnapshot.week_start_date.asc())
    )
    snapshots = result.scalars().all()

    points = [
        FitnessFreshnessPoint(
            week_start=s.week_start_date,
            acute_load=float(s.acute_load) if s.acute_load else None,
            chronic_load=float(s.chronic_load) if s.chronic_load else None,
            tsb=float(s.training_stress_balance) if s.training_stress_balance else None,
            weekly_tss=float(s.weekly_tss) if s.weekly_tss else None,
        )
        for s in snapshots
    ]

    return FitnessFreshnessResponse(
        data=points,
        current=points[-1] if points else None,
    )


@router.get("/weekly", response_model=list[WeeklySnapshotOut])
async def weekly_snapshots(
    limit: int = 12,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AnalyticsSnapshot)
        .where(AnalyticsSnapshot.user_id == current_user.id)
        .order_by(AnalyticsSnapshot.week_start_date.desc())
        .limit(limit)
    )
    return [WeeklySnapshotOut.model_validate(s) for s in result.scalars().all()]
