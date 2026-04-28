import structlog
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.models.workout import RunSplit, Workout, WorkoutSet
from app.pipeline.validators import validate_workout
from app.schemas.workout import WorkoutCreateRequest

logger = structlog.get_logger(__name__)


async def ingest_workout(
    body: WorkoutCreateRequest,
    user: User,
    db: AsyncSession,
) -> Workout:
    validation = validate_workout(
        body,
        user_max_hr=user.max_hr,
        user_resting_hr=user.resting_hr,
    )

    if not validation.is_valid:
        logger.warning(
            "workout_rejected",
            user_id=str(user.id),
            workout_type=body.workout_type,
            errors=validation.errors,
        )
        raise HTTPException(
            status_code=422,
            detail={"errors": validation.errors, "warnings": validation.warnings},
        )

    status = "quarantined" if validation.action == "quarantine" else "pending"
    if validation.warnings:
        logger.warning(
            "workout_quarantined",
            user_id=str(user.id),
            workout_type=body.workout_type,
            warnings=validation.warnings,
        )

    workout = Workout(
        user_id=user.id,
        workout_type=body.workout_type,
        status=status,
        started_at=body.started_at,
        duration_seconds=body.duration_seconds,
        notes=body.notes,
        perceived_effort=body.perceived_effort,
        raw_payload=body.model_dump(mode="json"),
        # Run fields
        distance_meters=body.distance_meters,
        avg_pace_sec_per_km=body.avg_pace_sec_per_km,
        avg_hr=body.avg_hr,
        max_hr=body.max_hr,
        elevation_gain_m=body.elevation_gain_m,
        route_name=body.route_name,
        # Gym fields
        muscle_groups=body.muscle_groups,
        workout_template=body.workout_template,
    )
    db.add(workout)
    await db.flush()
    await db.refresh(workout)

    for split_in in body.splits:
        db.add(RunSplit(workout_id=workout.id, **split_in.model_dump()))

    for set_in in body.sets:
        db.add(WorkoutSet(workout_id=workout.id, **set_in.model_dump()))

    await db.flush()

    # Re-fetch with relationships eagerly loaded to avoid lazy-load errors
    result = await db.execute(
        select(Workout)
        .options(selectinload(Workout.splits), selectinload(Workout.sets))
        .where(Workout.id == workout.id)
    )
    workout = result.scalar_one()

    # Auto-link to active training plan item for this day
    await _autolink_plan_item(workout, db)

    # Enqueue async pipeline processing (fire-and-forget)
    if status == "pending":
        try:
            from app.pipeline.tasks import process_workout
            process_workout.delay(str(workout.id))
        except Exception:
            logger.warning("celery_enqueue_failed", workout_id=str(workout.id))

    logger.info(
        "workout_created",
        workout_id=str(workout.id),
        workout_type=body.workout_type,
        status=status,
    )
    return workout


async def _autolink_plan_item(workout: Workout, db: AsyncSession) -> None:
    """If the user has an active plan with a session scheduled for this workout's date,
    mark it complete and link it to this workout."""
    from datetime import timedelta

    from sqlalchemy import select

    from app.api.v1.plans import WORKOUT_TYPE_TO_SESSION_TYPES
    from app.models.training_plan import TrainingPlan, TrainingPlanItem

    compatible_types = WORKOUT_TYPE_TO_SESSION_TYPES.get(workout.workout_type, set())
    if not compatible_types:
        return

    plan_result = await db.execute(
        select(TrainingPlan).where(
            TrainingPlan.user_id == workout.user_id,
            TrainingPlan.status == "active",
            TrainingPlan.start_date.isnot(None),
        )
    )
    plan = plan_result.scalar_one_or_none()
    if not plan or not plan.start_date:
        return

    workout_date = workout.started_at.date()

    # Find all plan items whose computed date matches the workout date
    items_result = await db.execute(
        select(TrainingPlanItem).where(
            TrainingPlanItem.plan_id == plan.id,
            TrainingPlanItem.is_completed.is_(False),
            TrainingPlanItem.session_type.in_(list(compatible_types)),
        )
    )
    for item in items_result.scalars().all():
        item_date = plan.start_date + timedelta(
            days=(item.week_number - 1) * 7 + (item.day_of_week - 1)
        )
        if item_date == workout_date:
            item.is_completed = True
            item.completed_workout_id = workout.id
            logger.info(
                "plan_item_auto_linked",
                item_id=str(item.id),
                workout_id=str(workout.id),
            )
            break  # link first matching item only
