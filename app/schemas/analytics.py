from datetime import date

from pydantic import BaseModel


class WeeklySnapshotOut(BaseModel):
    week_start_date: date
    total_workouts: int
    run_workouts: int
    gym_workouts: int
    total_run_km: float
    total_gym_volume_kg: float
    total_duration_min: int
    weekly_tss: float | None
    acute_load: float | None
    chronic_load: float | None
    training_stress_balance: float | None
    avg_pace_sec_per_km: float | None
    avg_hr_run: int | None
    avg_rpe: float | None

    model_config = {"from_attributes": True}


class FitnessFreshnessPoint(BaseModel):
    week_start: date
    acute_load: float | None
    chronic_load: float | None
    tsb: float | None
    weekly_tss: float | None


class FitnessFreshnessResponse(BaseModel):
    data: list[FitnessFreshnessPoint]
    current: FitnessFreshnessPoint | None


class PersonalBest(BaseModel):
    exercise_or_distance: str
    value: float
    unit: str
    achieved_at: date | None


class PersonalBestsResponse(BaseModel):
    fastest_5k_pace: PersonalBest | None
    fastest_10k_pace: PersonalBest | None
    longest_run_km: PersonalBest | None
    heaviest_squat_1rm: PersonalBest | None
    heaviest_bench_1rm: PersonalBest | None
    heaviest_deadlift_1rm: PersonalBest | None


class AnalyticsSummaryResponse(BaseModel):
    current_week: WeeklySnapshotOut | None
    trailing_4_weeks: list[WeeklySnapshotOut]
    fitness_trend: str | None
