from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.training_plan import TrainingPlan
from app.models.user import User

router = APIRouter()


@router.get("", response_model=list[dict])
async def list_plans(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TrainingPlan)
        .where(TrainingPlan.user_id == current_user.id)
        .order_by(TrainingPlan.created_at.desc())
    )
    plans = result.scalars().all()
    return [
        {
            "id": str(p.id),
            "goal": p.goal,
            "status": p.status,
            "duration_weeks": p.duration_weeks,
            "created_at": p.created_at.isoformat(),
        }
        for p in plans
    ]


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

    return {
        "id": str(plan.id),
        "goal": plan.goal,
        "status": plan.status,
        "duration_weeks": plan.duration_weeks,
        "created_at": plan.created_at.isoformat(),
        "ai_explanation": plan.ai_explanation,
        "items": [
            {
                "id": str(item.id),
                "week_number": item.week_number,
                "day_of_week": item.day_of_week,
                "session_type": item.session_type,
                "title": item.title,
                "description": item.description,
                "duration_min": item.duration_min,
                "target_distance_km": float(item.target_distance_km) if item.target_distance_km else None,
                "is_completed": item.is_completed,
            }
            for item in sorted(plan.items, key=lambda x: (x.week_number, x.day_of_week))
        ],
    }


@router.patch("/{plan_id}/activate", response_model=dict)
async def activate_plan(
    plan_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Deactivate any existing active plan
    result = await db.execute(
        select(TrainingPlan).where(
            TrainingPlan.user_id == current_user.id,
            TrainingPlan.status == "active",
        )
    )
    for active in result.scalars().all():
        active.status = "archived"

    result = await db.execute(
        select(TrainingPlan).where(TrainingPlan.id == plan_id, TrainingPlan.user_id == current_user.id)
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    plan.status = "active"
    await db.flush()
    return {"id": str(plan.id), "status": plan.status}
