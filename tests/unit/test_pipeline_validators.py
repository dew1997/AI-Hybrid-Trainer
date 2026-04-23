from datetime import datetime, timezone

import pytest

from app.pipeline.validators import validate_workout
from app.schemas.workout import WorkoutCreateRequest, WorkoutSetIn


def _run_workout(**kwargs) -> WorkoutCreateRequest:
    defaults = dict(
        workout_type="run",
        started_at=datetime.now(timezone.utc),
        duration_seconds=3600,
        distance_meters=10000,
        avg_pace_sec_per_km=360,
        avg_hr=145,
    )
    defaults.update(kwargs)
    return WorkoutCreateRequest(**defaults)


def _gym_workout(**kwargs) -> WorkoutCreateRequest:
    sets = [WorkoutSetIn(set_number=1, exercise_name="squat", reps=5, weight_kg=100.0)]
    defaults = dict(
        workout_type="gym",
        started_at=datetime.now(timezone.utc),
        duration_seconds=3600,
        sets=sets,
    )
    defaults.update(kwargs)
    return WorkoutCreateRequest(**defaults)


class TestRunValidation:
    def test_valid_run_is_accepted(self):
        result = validate_workout(_run_workout())
        assert result.is_valid
        assert result.action == "accept"
        assert not result.errors

    def test_world_record_pace_is_rejected(self):
        result = validate_workout(_run_workout(avg_pace_sec_per_km=95))
        assert not result.is_valid
        assert result.action == "reject"
        assert any("world record" in e.lower() for e in result.errors)

    def test_impossibly_slow_pace_is_rejected(self):
        result = validate_workout(_run_workout(avg_pace_sec_per_km=1500))
        assert not result.is_valid
        assert result.action == "reject"

    def test_hr_over_250_is_rejected(self):
        result = validate_workout(_run_workout(avg_hr=260))
        assert not result.is_valid
        assert result.action == "reject"

    def test_hr_exceeding_user_max_is_quarantined(self):
        result = validate_workout(_run_workout(avg_hr=190), user_max_hr=185)
        assert result.is_valid
        assert result.action == "quarantine"
        assert any("max HR" in w for w in result.warnings)

    def test_large_duration_distance_mismatch_is_quarantined(self):
        # Pace 360s/km × 10km = 3600s expected; give 7200s duration
        result = validate_workout(_run_workout(duration_seconds=7200))
        assert result.is_valid
        assert result.action == "quarantine"

    def test_very_long_run_produces_warning(self):
        result = validate_workout(_run_workout(distance_meters=60000))
        assert result.is_valid
        assert result.action == "quarantine"
        assert any("unusually long" in w for w in result.warnings)


class TestGymValidation:
    def test_valid_gym_workout_is_accepted(self):
        result = validate_workout(_gym_workout())
        assert result.is_valid
        assert result.action == "accept"

    def test_superhuman_weight_is_rejected(self):
        sets = [WorkoutSetIn(set_number=1, exercise_name="deadlift", reps=1, weight_kg=700.0)]
        result = validate_workout(_gym_workout(sets=sets))
        assert not result.is_valid
        assert result.action == "reject"

    def test_implausible_reps_is_quarantined(self):
        sets = [WorkoutSetIn(set_number=1, exercise_name="pushup", reps=250, weight_kg=0)]
        result = validate_workout(_gym_workout(sets=sets))
        assert result.is_valid
        assert result.action == "quarantine"
