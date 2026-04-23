"""
Core training load and performance metric calculations.

Implements the Banister impulse-response model (ATL/CTL/TSB) and
HR-TRIMP method for Training Stress Score (TSS).
"""

import math
from dataclasses import dataclass


@dataclass
class TrainingLoad:
    acute_load: float   # ATL — 7-day exponential moving average of daily TSS
    chronic_load: float  # CTL — 42-day exponential moving average
    tsb: float           # TSB = CTL - ATL (positive = fresh, negative = fatigued)


def compute_run_tss(
    duration_sec: int,
    avg_hr: int,
    max_hr: int,
    resting_hr: int,
) -> float:
    """
    Estimate TSS for a run using the HR-TRIMP method.

    HRR = (avg_hr - resting_hr) / (max_hr - resting_hr)
    TRIMP = duration_min * HRR * 0.64 * e^(1.92 * HRR)
    TSS normalised: TRIMP scaled so 1hr at threshold ≈ 100 TSS
    """
    if max_hr <= resting_hr:
        return 0.0

    duration_min = duration_sec / 60
    hrr = (avg_hr - resting_hr) / (max_hr - resting_hr)
    hrr = max(0.0, min(1.0, hrr))  # clamp to [0, 1]

    trimp = duration_min * hrr * 0.64 * math.exp(1.92 * hrr)

    # Threshold TRIMP: 60 min at HRR≈0.80 (lactate threshold for most runners)
    threshold_hrr = 0.80
    threshold_trimp = 60 * threshold_hrr * 0.64 * math.exp(1.92 * threshold_hrr)

    tss = (trimp / threshold_trimp) * 100
    return round(tss, 2)


def compute_gym_tss(duration_sec: int, perceived_effort: int | None) -> float:
    """
    Approximate TSS for a gym session using RPE proxy.
    RPE 1–3 → low (20-40 TSS), RPE 4–6 → moderate (40-70), RPE 7–10 → high (70-100+)
    """
    rpe = perceived_effort or 6
    duration_min = duration_sec / 60
    rpe_factor = 0.1 + (rpe / 10) * 0.9
    return round(duration_min * rpe_factor * (100 / 60), 2)


def compute_gym_volume(sets: list) -> float:
    """Total volume load = sum(reps * weight_kg) for working (non-warmup) sets."""
    return sum(
        (s.reps or 0) * (float(s.weight_kg) if s.weight_kg else 0)
        for s in sets
        if not s.is_warmup
    )


def estimate_1rm(weight_kg: float, reps: int) -> float:
    """Epley formula: 1RM = weight * (1 + reps / 30)"""
    if reps == 1:
        return weight_kg
    return round(weight_kg * (1 + reps / 30), 2)


def compute_pace_zone(pace_sec_per_km: float, threshold_pace_sec_per_km: float) -> str:
    """
    5-zone model relative to athlete's threshold pace.
    Zone 1 (recovery):  > 130% of threshold
    Zone 2 (aerobic):   115–130%
    Zone 3 (tempo):     103–115%
    Zone 4 (VO2max):    95–103%
    Zone 5 (sprint):    < 95%
    """
    ratio = pace_sec_per_km / threshold_pace_sec_per_km  # higher ratio = slower = easier

    if ratio > 1.30:
        return "Z1_recovery"
    elif ratio > 1.15:
        return "Z2_aerobic"
    elif ratio > 1.03:
        return "Z3_tempo"
    elif ratio > 0.95:
        return "Z4_vo2max"
    else:
        return "Z5_sprint"


def compute_atl_ctl(
    daily_tss_series: list[float],
    atl_days: int = 7,
    ctl_days: int = 42,
) -> TrainingLoad:
    """
    Compute ATL and CTL via exponential moving averages.

    ATL: short-term fatigue (7-day EMA, k = 2 / (7+1))
    CTL: long-term fitness (42-day EMA, k = 2 / (42+1))
    TSB: form = CTL - ATL
    """
    if not daily_tss_series:
        return TrainingLoad(acute_load=0.0, chronic_load=0.0, tsb=0.0)

    k_atl = 2 / (atl_days + 1)
    k_ctl = 2 / (ctl_days + 1)

    atl = daily_tss_series[0]
    ctl = daily_tss_series[0]

    for tss in daily_tss_series[1:]:
        atl = tss * k_atl + atl * (1 - k_atl)
        ctl = tss * k_ctl + ctl * (1 - k_ctl)

    return TrainingLoad(
        acute_load=round(atl, 2),
        chronic_load=round(ctl, 2),
        tsb=round(ctl - atl, 2),
    )


def get_threshold_pace_from_profile(user) -> float | None:
    """
    Derive threshold pace from VO2max estimate using Jack Daniels' VDOT tables.
    Falls back to None if insufficient data.
    """
    if not user.vo2max_estimate:
        return None

    # Approximation: vVO2max (m/min) ≈ 173.1 + 1.37 * VO2max (from Daniels)
    # Threshold pace ≈ 85-88% of vVO2max
    vvo2max_m_per_min = 173.1 + 1.37 * float(user.vo2max_estimate)
    threshold_m_per_min = vvo2max_m_per_min * 0.86
    threshold_sec_per_km = (1000 / threshold_m_per_min) * 60
    return round(threshold_sec_per_km, 1)
