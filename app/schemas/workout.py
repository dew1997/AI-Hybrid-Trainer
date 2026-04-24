import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class RunSplitIn(BaseModel):
    split_number: int = Field(ge=1)
    split_unit: Literal["km", "mile"] = "km"
    distance_m: float | None = Field(default=None, ge=0)
    duration_seconds: int = Field(ge=1)
    avg_hr: int | None = Field(default=None, ge=30, le=250)
    avg_pace_sec_per_km: float | None = Field(default=None, ge=60, le=1800)
    elevation_gain_m: float | None = None
    cadence_spm: int | None = Field(default=None, ge=60, le=250)


class WorkoutSetIn(BaseModel):
    set_number: int = Field(ge=1)
    exercise_name: str = Field(min_length=1, max_length=100)
    reps: int | None = Field(default=None, ge=1, le=500)
    weight_kg: float | None = Field(default=None, ge=0, le=10_000)
    duration_seconds: int | None = Field(default=None, ge=1)
    rest_seconds: int | None = Field(default=None, ge=0)
    is_warmup: bool = False
    notes: str | None = None


class WorkoutCreateRequest(BaseModel):
    workout_type: Literal["run", "gym", "cycle", "other"]
    started_at: datetime
    duration_seconds: int | None = Field(default=None, ge=60, le=86400)
    notes: str | None = None
    perceived_effort: int | None = Field(default=None, ge=1, le=10)

    # Run fields — wide bounds here; business-logic limits enforced by pipeline validators
    distance_meters: float | None = Field(default=None, ge=1, le=1_000_000)
    avg_pace_sec_per_km: float | None = Field(default=None, ge=1, le=7200)
    avg_hr: int | None = Field(default=None, ge=1, le=300)
    max_hr: int | None = Field(default=None, ge=1, le=300)
    elevation_gain_m: float | None = Field(default=None, ge=0)
    route_name: str | None = Field(default=None, max_length=200)
    splits: list[RunSplitIn] = []

    # Gym fields
    muscle_groups: list[str] | None = None
    workout_template: str | None = Field(default=None, max_length=100)
    sets: list[WorkoutSetIn] = []

    @model_validator(mode="after")
    def validate_type_fields(self):
        if self.workout_type == "run" and not self.distance_meters:
            raise ValueError("distance_meters is required for run workouts")
        if self.workout_type == "gym" and not self.sets:
            raise ValueError("sets are required for gym workouts")
        return self


class WorkoutUpdateRequest(BaseModel):
    notes: str | None = None
    perceived_effort: int | None = Field(default=None, ge=1, le=10)
    route_name: str | None = None


class RunSplitOut(BaseModel):
    id: uuid.UUID
    split_number: int
    split_unit: str
    duration_seconds: int
    avg_pace_sec_per_km: float | None
    avg_hr: int | None
    cadence_spm: int | None

    model_config = {"from_attributes": True}


class WorkoutSetOut(BaseModel):
    id: uuid.UUID
    set_number: int
    exercise_name: str
    reps: int | None
    weight_kg: float | None
    is_warmup: bool

    model_config = {"from_attributes": True}


class WorkoutOut(BaseModel):
    id: uuid.UUID
    workout_type: str
    status: str
    started_at: datetime
    duration_seconds: int | None
    perceived_effort: int | None
    notes: str | None
    route_name: str | None
    # Run
    distance_meters: float | None
    avg_pace_sec_per_km: float | None
    avg_hr: int | None
    elevation_gain_m: float | None
    pace_zone: str | None
    tss: float | None
    # Gym
    total_volume_kg: float | None
    muscle_groups: list[str] | None
    splits: list[RunSplitOut] = []
    sets: list[WorkoutSetOut] = []

    model_config = {"from_attributes": True}


class PaginationMeta(BaseModel):
    total: int
    limit: int
    next_cursor: str | None
    has_more: bool


class WorkoutListResponse(BaseModel):
    data: list[WorkoutOut]
    meta: PaginationMeta
