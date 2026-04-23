import base64
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.workout import RunSplit, Workout, WorkoutSet
from app.schemas.workout import (
    PaginationMeta,
    WorkoutCreateRequest,
    WorkoutListResponse,
    WorkoutOut,
    WorkoutUpdateRequest,
)

router = APIRouter()


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_workout(
    body: WorkoutCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.pipeline.ingestion import ingest_workout

    workout = await ingest_workout(body, current_user, db)
    return {
        "workout": WorkoutOut.model_validate(workout).model_dump(),
        "pipeline_status": "queued",
    }


@router.get("", response_model=WorkoutListResponse)
async def list_workouts(
    workout_type: str | None = Query(default=None),
    from_date: datetime | None = Query(default=None),
    to_date: datetime | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(Workout)
        .where(Workout.user_id == current_user.id)
        .order_by(Workout.started_at.desc())
    )

    if workout_type:
        query = query.where(Workout.workout_type == workout_type)
    if from_date:
        query = query.where(Workout.started_at >= from_date)
    if to_date:
        query = query.where(Workout.started_at <= to_date)

    if cursor:
        try:
            cursor_data = json.loads(base64.b64decode(cursor).decode())
            query = query.where(Workout.started_at < cursor_data["started_at"])
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid cursor")

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    result = await db.execute(query.limit(limit + 1))
    workouts = result.scalars().all()

    has_more = len(workouts) > limit
    if has_more:
        workouts = workouts[:limit]

    next_cursor = None
    if has_more and workouts:
        last = workouts[-1]
        cursor_payload = {"started_at": last.started_at.isoformat()}
        next_cursor = base64.b64encode(json.dumps(cursor_payload).encode()).decode()

    return WorkoutListResponse(
        data=[WorkoutOut.model_validate(w) for w in workouts],
        meta=PaginationMeta(total=total, limit=limit, next_cursor=next_cursor, has_more=has_more),
    )


@router.get("/{workout_id}", response_model=WorkoutOut)
async def get_workout(
    workout_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy.orm import selectinload

    result = await db.execute(
        select(Workout)
        .options(selectinload(Workout.splits), selectinload(Workout.sets))
        .where(Workout.id == workout_id, Workout.user_id == current_user.id)
    )
    workout = result.scalar_one_or_none()
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")
    return WorkoutOut.model_validate(workout)


@router.patch("/{workout_id}", response_model=WorkoutOut)
async def update_workout(
    workout_id: str,
    body: WorkoutUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Workout).where(Workout.id == workout_id, Workout.user_id == current_user.id)
    )
    workout = result.scalar_one_or_none()
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")

    for key, value in body.model_dump(exclude_none=True).items():
        setattr(workout, key, value)
    await db.flush()
    await db.refresh(workout)
    return WorkoutOut.model_validate(workout)


@router.delete("/{workout_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workout(
    workout_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Workout).where(Workout.id == workout_id, Workout.user_id == current_user.id)
    )
    workout = result.scalar_one_or_none()
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")
    await db.delete(workout)
