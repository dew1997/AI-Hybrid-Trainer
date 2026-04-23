"""
Celery background tasks for async workout processing and analytics aggregation.
"""

import asyncio
from datetime import date, timedelta

import structlog
from celery import Celery
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import selectinload

from app.config import settings

celery_app = Celery(
    "trainer",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    task_track_started=True,
    beat_schedule={
        "nightly-analytics-rollup": {
            "task": "app.pipeline.tasks.nightly_analytics_rollup",
            "schedule": 3600 * 24,  # daily
        }
    },
)

logger = structlog.get_logger(__name__)


def _run_async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(OperationalError,),
)
def process_workout(self, workout_id: str) -> dict:
    return _run_async(_process_workout_async(workout_id))


async def _process_workout_async(workout_id: str) -> dict:
    from app.db.session import AsyncSessionLocal
    from app.models.workout import Workout
    from app.pipeline.metrics import (
        compute_gym_tss,
        compute_gym_volume,
        compute_pace_zone,
        compute_run_tss,
        get_threshold_pace_from_profile,
    )

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Workout)
            .options(selectinload(Workout.sets), selectinload(Workout.splits))
            .where(Workout.id == workout_id)
        )
        workout = result.scalar_one_or_none()
        if not workout:
            logger.error("workout_not_found", workout_id=workout_id)
            return {"error": "workout not found"}

        from app.models.user import User
        user_res = await db.execute(select(User).where(User.id == workout.user_id))
        user = user_res.scalar_one_or_none()

        try:
            if workout.workout_type == "run":
                if (workout.avg_hr and user and user.max_hr and user.resting_hr):
                    tss = compute_run_tss(
                        workout.duration_seconds or 0,
                        workout.avg_hr,
                        user.max_hr,
                        user.resting_hr,
                    )
                    workout.tss = tss

                threshold = get_threshold_pace_from_profile(user) if user else None
                if workout.avg_pace_sec_per_km and threshold:
                    workout.pace_zone = compute_pace_zone(
                        float(workout.avg_pace_sec_per_km), threshold
                    )

            elif workout.workout_type == "gym":
                workout.total_volume_kg = compute_gym_volume(workout.sets)
                workout.tss = compute_gym_tss(
                    workout.duration_seconds or 3600,
                    workout.perceived_effort,
                )

            workout.status = "processed"
            await db.commit()

            # Regenerate analytics snapshot for this workout's week
            await _update_analytics_snapshot(workout.user_id, workout.started_at.date(), db)

            logger.info("workout_processed", workout_id=workout_id, tss=workout.tss)
            return {"status": "processed", "workout_id": workout_id}

        except Exception as e:
            workout.status = "failed"
            await db.commit()
            logger.error("workout_processing_failed", workout_id=workout_id, error=str(e))
            raise


async def _update_analytics_snapshot(user_id, workout_date: date, db) -> None:
    from sqlalchemy.dialects.postgresql import insert

    from app.models.analytics import AnalyticsSnapshot
    from app.models.workout import Workout

    week_start = workout_date - timedelta(days=workout_date.weekday())

    result = await db.execute(
        select(Workout).where(
            Workout.user_id == user_id,
            Workout.started_at >= week_start,
            Workout.started_at < week_start + timedelta(weeks=1),
            Workout.status == "processed",
        )
    )
    week_workouts = result.scalars().all()

    runs = [w for w in week_workouts if w.workout_type == "run"]
    gyms = [w for w in week_workouts if w.workout_type == "gym"]

    total_tss = sum(float(w.tss) for w in week_workouts if w.tss)
    total_run_km = sum(float(w.distance_meters or 0) / 1000 for w in runs)
    total_gym_vol = sum(float(w.total_volume_kg or 0) for w in gyms)
    total_duration = sum((w.duration_seconds or 0) for w in week_workouts) // 60

    avg_pace = None
    if runs:
        paces = [float(w.avg_pace_sec_per_km) for w in runs if w.avg_pace_sec_per_km]
        avg_pace = sum(paces) / len(paces) if paces else None

    stmt = insert(AnalyticsSnapshot).values(
        user_id=user_id,
        week_start_date=week_start,
        total_workouts=len(week_workouts),
        run_workouts=len(runs),
        gym_workouts=len(gyms),
        total_run_km=total_run_km,
        total_gym_volume_kg=total_gym_vol,
        total_duration_min=total_duration,
        weekly_tss=total_tss,
        avg_pace_sec_per_km=avg_pace,
    ).on_conflict_do_update(
        constraint="uq_analytics_user_week",
        set_={
            "total_workouts": len(week_workouts),
            "run_workouts": len(runs),
            "gym_workouts": len(gyms),
            "total_run_km": total_run_km,
            "total_gym_volume_kg": total_gym_vol,
            "total_duration_min": total_duration,
            "weekly_tss": total_tss,
            "avg_pace_sec_per_km": avg_pace,
        },
    )
    await db.execute(stmt)
    await db.commit()


@celery_app.task
def nightly_analytics_rollup() -> dict:
    return _run_async(_nightly_rollup_async())


async def _nightly_rollup_async() -> dict:
    """Recompute ATL/CTL/TSB rolling series for all recently active users."""

    from app.db.session import AsyncSessionLocal
    from app.models.analytics import AnalyticsSnapshot
    from app.models.user import User
    from app.models.workout import Workout
    from app.pipeline.metrics import compute_atl_ctl

    cutoff = date.today() - timedelta(days=90)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User.id).distinct().join(Workout).where(Workout.started_at >= cutoff)
        )
        user_ids = result.scalars().all()

        processed = 0
        for user_id in user_ids:
            snapshots = await db.execute(
                select(AnalyticsSnapshot)
                .where(AnalyticsSnapshot.user_id == user_id)
                .order_by(AnalyticsSnapshot.week_start_date.asc())
            )
            snaps = snapshots.scalars().all()
            if not snaps:
                continue

            tss_series = [float(s.weekly_tss or 0) / 7 for s in snaps]  # daily avg
            load = compute_atl_ctl(tss_series)

            # Update most recent snapshot
            latest = snaps[-1]
            latest.acute_load = load.acute_load
            latest.chronic_load = load.chronic_load
            latest.training_stress_balance = load.tsb
            processed += 1

        await db.commit()
        logger.info("nightly_rollup_complete", users_processed=processed)
        return {"users_processed": processed}
