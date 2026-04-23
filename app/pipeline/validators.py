from dataclasses import dataclass, field
from typing import Literal

from app.schemas.workout import WorkoutCreateRequest


@dataclass
class ValidationResult:
    is_valid: bool
    action: Literal["accept", "quarantine", "reject"]
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def validate_workout(
    body: WorkoutCreateRequest,
    user_max_hr: int | None = None,
    user_resting_hr: int | None = None,
) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    if body.workout_type == "run":
        result = _validate_run(body, errors, warnings, user_max_hr)
    elif body.workout_type == "gym":
        result = _validate_gym(body, errors, warnings)
    else:
        result = ValidationResult(is_valid=True, action="accept")

    if errors:
        return ValidationResult(is_valid=False, action="reject", errors=errors, warnings=warnings)
    if warnings:
        return ValidationResult(is_valid=True, action="quarantine", errors=errors, warnings=warnings)
    return ValidationResult(is_valid=True, action="accept", errors=errors, warnings=warnings)


def _validate_run(
    body: WorkoutCreateRequest,
    errors: list[str],
    warnings: list[str],
    user_max_hr: int | None,
) -> None:
    pace = body.avg_pace_sec_per_km
    distance = body.distance_meters
    duration = body.duration_seconds
    avg_hr = body.avg_hr

    # REJECT: physically impossible
    if pace and pace < 120:
        errors.append(f"Pace {pace:.0f}s/km is faster than world record (2:00/km)")
    if pace and pace > 1200:
        errors.append(f"Pace {pace:.0f}s/km exceeds 20:00/km — likely a data error")
    if avg_hr and avg_hr > 250:
        errors.append(f"Average HR {avg_hr}bpm exceeds physiological maximum")
    if distance and distance <= 0:
        errors.append("Distance must be positive")
    if duration and duration <= 0:
        errors.append("Duration must be positive")

    # QUARANTINE: suspicious
    if avg_hr and user_max_hr and avg_hr > user_max_hr:
        warnings.append(
            f"Average HR ({avg_hr}bpm) exceeds your recorded max HR ({user_max_hr}bpm)"
        )
    if pace and duration and distance:
        expected_duration = (distance / 1000) * pace
        if abs(duration - expected_duration) > 300:
            warnings.append(
                f"Duration ({duration}s) and pace×distance ({expected_duration:.0f}s) "
                "mismatch by more than 5 minutes"
            )

    # WARN: unusual but acceptable
    if distance and distance > 50_000:
        warnings.append(f"Run distance {distance/1000:.1f}km is unusually long")
    if avg_hr and user_max_hr and avg_hr > 0.92 * user_max_hr and (body.perceived_effort or 10) <= 5:
        warnings.append(
            f"HR ({avg_hr}bpm) is very high for a low-RPE ({body.perceived_effort}) effort"
        )


def _validate_gym(
    body: WorkoutCreateRequest,
    errors: list[str],
    warnings: list[str],
) -> None:
    if not body.sets:
        errors.append("Gym workout must include at least one set")
        return

    for s in body.sets:
        if s.weight_kg and s.weight_kg > 600:
            errors.append(
                f"Set {s.set_number} weight ({s.weight_kg}kg) exceeds world record deadlift"
            )
        if s.reps and s.reps > 200:
            warnings.append(f"Set {s.set_number} rep count ({s.reps}) is implausible")

    if len(body.sets) > 80:
        warnings.append(f"Gym workout has {len(body.sets)} sets — unusually high")
