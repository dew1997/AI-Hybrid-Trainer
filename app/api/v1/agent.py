import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.coaching import ChatMessage, CoachingSession
from app.models.user import User
from app.schemas.agent import (
    CoachingQueryRequest,
    CoachingQueryResponse,
    CoachingSessionDetailOut,
    CoachingSessionOut,
    GeneratePlanRequest,
    TrainingPlanOut,
)

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


@router.get("/sessions", response_model=list[CoachingSessionOut])
async def list_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(
            CoachingSession,
            func.count(ChatMessage.id).label("message_count"),
        )
        .outerjoin(ChatMessage, ChatMessage.session_id == CoachingSession.id)
        .where(CoachingSession.user_id == current_user.id)
        .group_by(CoachingSession.id)
        .order_by(CoachingSession.updated_at.desc())
    )
    rows = result.all()
    out = []
    for session, count in rows:
        d = CoachingSessionOut.model_validate(session)
        d.message_count = count
        out.append(d)
    return out


@router.get("/sessions/{session_id}", response_model=CoachingSessionDetailOut)
async def get_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CoachingSession)
        .options(selectinload(CoachingSession.messages))
        .where(
            CoachingSession.id == session_id,
            CoachingSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    out = CoachingSessionDetailOut.model_validate(session)
    out.message_count = len(session.messages)
    return out


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CoachingSession).where(
            CoachingSession.id == session_id,
            CoachingSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    await db.delete(session)
    await db.commit()
