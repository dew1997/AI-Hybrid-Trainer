from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.agent import CoachingQueryRequest, CoachingQueryResponse, GeneratePlanRequest, TrainingPlanOut

router = APIRouter()


@router.post("/coaching-query", response_model=CoachingQueryResponse)
async def coaching_query(
    body: CoachingQueryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.agent.coach_agent import run_coaching_query

    return await run_coaching_query(body, current_user, db)


@router.post("/generate-plan", response_model=TrainingPlanOut, status_code=201)
async def generate_plan(
    body: GeneratePlanRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.agent.coach_agent import run_generate_plan

    return await run_generate_plan(body, current_user, db)
