import uuid
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.training_plan import TrainingPlan, TrainingPlanItem
from app.models.user import User

router = APIRouter()

# ── session-type → workout-type compatibility ──────────────────────────────

RUN_SESSION_TYPES  = {"easy_run", "tempo_run", "interval_run", "long_run", "cross_training"}
GYM_SESSION_TYPES  = {"strength", "mobility"}

WORKOUT_TYPE_TO_SESSION_TYPES = {
    "run": RUN_SESSION_TYPES,
    "gym": GYM_SESSION_TYPES,
}


def _plan_item_dict(item: TrainingPlanItem, start_date: date | None) -> dict:
    actual_date = None
    if start_date:
        actual_date = (
            start_date
            + timedelta(days=(item.week_number - 1) * 7 + (item.day_of_week - 1))
        ).isoformat()
    return {
        "id": str(item.id),
        "week_number": item.week_number,
        "day_of_week": item.day_of_week,
        "actual_date": actual_date,
        "session_type": item.session_type,
        "title": item.title,
        "description": item.description,
        "duration_min": item.duration_min,
        "target_distance_km": float(item.target_distance_km) if item.target_distance_km else None,
        "is_completed": item.is_completed,
        "completed_workout_id": str(item.completed_workout_id) if item.completed_workout_id else None,
    }


def _plan_dict(plan: TrainingPlan, include_items: bool = False) -> dict:
    d: dict = {
        "id": str(plan.id),
        "goal": plan.goal,
        "status": plan.status,
        "duration_weeks": plan.duration_weeks,
        "start_date": plan.start_date.isoformat() if plan.start_date else None,
        "created_at": plan.created_at.isoformat(),
        "ai_explanation": plan.ai_explanation,
    }
    if include_items:
        d["items"] = [
            _plan_item_dict(item, plan.start_date)
            for item in sorted(plan.items, key=lambda x: (x.week_number, x.day_of_week))
        ]
    return d


# ── endpoints ─────────────────────────────────────────────────────────────

@router.get("", response_model=list[dict])
async def list_plans(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TrainingPlan)
        .options(selectinload(TrainingPlan.items))
        .where(TrainingPlan.user_id == current_user.id)
        .order_by(TrainingPlan.created_at.desc())
    )
    plans = result.scalars().all()
    return [_plan_dict(p, include_items=False) for p in plans]


@router.get("/active", response_model=dict)
async def get_active_plan(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the user's single active plan with all items and computed actual_date."""
    result = await db.execute(
        select(TrainingPlan)
        .options(selectinload(TrainingPlan.items))
        .where(
            TrainingPlan.user_id == current_user.id,
            TrainingPlan.status == "active",
        )
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="No active plan")
    return _plan_dict(plan, include_items=True)


@router.get("/{plan_id}", response_model=dict)
async def get_plan(
    plan_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TrainingPlan)
        .options(selectinload(TrainingPlan.items))
        .where(TrainingPlan.id == plan_id, TrainingPlan.user_id == current_user.id)
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Training plan not found")
    return _plan_dict(plan, include_items=True)


@router.patch("/{plan_id}/activate", response_model=dict)
async def activate_plan(
    plan_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Archive existing active plan
    result = await db.execute(
        select(TrainingPlan).where(
            TrainingPlan.user_id == current_user.id,
            TrainingPlan.status == "active",
        )
    )
    for active in result.scalars().all():
        active.status = "archived"

    result = await db.execute(
        select(TrainingPlan).where(
            TrainingPlan.id == plan_id, TrainingPlan.user_id == current_user.id
        )
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    plan.status = "active"
    # Anchor the plan to the Monday of the current week
    today = date.today()
    plan.start_date = today - timedelta(days=today.weekday())
    await db.flush()
    return _plan_dict(plan)


@router.patch("/items/{item_id}/complete", response_model=dict)
async def mark_item_complete(
    item_id: uuid.UUID,
    workout_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually mark a plan session as complete, optionally linking a workout."""
    result = await db.execute(
        select(TrainingPlanItem)
        .join(TrainingPlan)
        .where(TrainingPlanItem.id == item_id, TrainingPlan.user_id == current_user.id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Plan item not found")

    item.is_completed = not item.is_completed  # toggle
    if item.is_completed and workout_id:
        item.completed_workout_id = workout_id
    elif not item.is_completed:
        item.completed_workout_id = None
    await db.commit()
    return {"id": str(item.id), "is_completed": item.is_completed}
