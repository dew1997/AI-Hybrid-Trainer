import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class CoachingQueryRequest(BaseModel):
    query: str = Field(min_length=5, max_length=1000)
    context_weeks: int = Field(default=4, ge=1, le=12)
    session_id: uuid.UUID | None = None
    persist: bool = True  # set False for ephemeral calls (e.g. dashboard briefing)


class RetrievedSource(BaseModel):
    title: str
    relevance: float


class CoachingQueryResponse(BaseModel):
    answer: str
    reasoning: str | None
    sources: list[RetrievedSource]
    suggested_actions: list[str]
    token_usage: dict[str, int]
    session_id: uuid.UUID | None


class ChatMessageOut(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    sources: list[RetrievedSource] = []
    actions: list[str] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class CoachingSessionOut(BaseModel):
    id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    model_config = {"from_attributes": True}


class CoachingSessionDetailOut(CoachingSessionOut):
    messages: list[ChatMessageOut] = []


class SessionPlanItem(BaseModel):
    day_of_week: int = Field(ge=1, le=7)
    session_type: str
    title: str
    description: str | None = None
    duration_min: int | None = None
    target_distance_km: float | None = None
    target_pace_min_per_km: float | None = None
    target_hr_zone: int | None = None
    target_rpe: int | None = None
    exercises: list[dict] = []


class WeekPlan(BaseModel):
    week_number: int
    theme: str
    target_tss: float | None = None
    sessions: list[SessionPlanItem]


class GeneratePlanRequest(BaseModel):
    goal: str = Field(min_length=2, max_length=100)
    weeks: int = Field(default=8, ge=2, le=24)
    training_days_per_week: int = Field(default=4, ge=2, le=6)
    start_date: date | None = None


class PlanItemOut(BaseModel):
    id: uuid.UUID
    week_number: int
    day_of_week: int
    session_type: str
    title: str
    description: str | None = None
    duration_min: int | None = None
    target_distance_km: float | None = None
    is_completed: bool

    model_config = {"from_attributes": True}


class TrainingPlanOut(BaseModel):
    id: uuid.UUID
    goal: str
    duration_weeks: int
    status: str
    created_at: datetime
    ai_explanation: str | None
    items: list[PlanItemOut]
    token_usage: dict[str, int] | None = None

    model_config = {"from_attributes": True}
