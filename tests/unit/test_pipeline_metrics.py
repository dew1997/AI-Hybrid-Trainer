import pytest

from app.pipeline.metrics import (
    TrainingLoad,
    compute_atl_ctl,
    compute_gym_tss,
    compute_gym_volume,
    compute_pace_zone,
    compute_run_tss,
    estimate_1rm,
)


class TestComputeRunTss:
    def test_moderate_effort_produces_expected_range(self):
        tss = compute_run_tss(
            duration_sec=3600, avg_hr=155, max_hr=185, resting_hr=55
        )
        assert 70 < tss < 120

    def test_easy_effort_lower_tss_than_hard(self):
        easy = compute_run_tss(3600, avg_hr=130, max_hr=185, resting_hr=55)
        hard = compute_run_tss(3600, avg_hr=170, max_hr=185, resting_hr=55)
        assert easy < hard

    def test_longer_duration_higher_tss(self):
        short = compute_run_tss(1800, avg_hr=150, max_hr=185, resting_hr=55)
        long_ = compute_run_tss(5400, avg_hr=150, max_hr=185, resting_hr=55)
        assert long_ > short * 2.5

    def test_invalid_hr_range_returns_zero(self):
        tss = compute_run_tss(3600, avg_hr=55, max_hr=55, resting_hr=55)
        assert tss == 0.0

    def test_result_is_non_negative(self):
        tss = compute_run_tss(600, avg_hr=120, max_hr=185, resting_hr=55)
        assert tss >= 0


class TestComputePaceZone:
    def test_easy_pace_is_z2(self):
        # 6:00/km vs 5:00/km threshold = 120% → Z2
        assert compute_pace_zone(360, 300) == "Z2_aerobic"

    def test_very_slow_is_z1(self):
        # 7:00/km vs 5:00/km threshold = 140% → Z1
        assert compute_pace_zone(420, 300) == "Z1_recovery"

    def test_threshold_pace_is_z3(self):
        # 5:05/km vs 5:00/km = 101.7% → Z3
        assert compute_pace_zone(305, 300) == "Z3_tempo"

    def test_fast_pace_is_z4(self):
        # 4:50/km vs 5:00/km = 96.7% → Z4
        assert compute_pace_zone(290, 300) == "Z4_vo2max"

    def test_sprint_pace_is_z5(self):
        # 4:30/km vs 5:00/km = 90% → Z5
        assert compute_pace_zone(270, 300) == "Z5_sprint"


class TestComputeGymVolume:
    def test_excludes_warmup_sets(self):
        class FakeSet:
            def __init__(self, reps, weight_kg, is_warmup):
                self.reps = reps
                self.weight_kg = weight_kg
                self.is_warmup = is_warmup

        sets = [
            FakeSet(10, 60.0, is_warmup=True),   # warmup — excluded
            FakeSet(5, 100.0, is_warmup=False),   # working set
            FakeSet(5, 100.0, is_warmup=False),   # working set
        ]
        assert compute_gym_volume(sets) == 1000.0

    def test_empty_sets_returns_zero(self):
        assert compute_gym_volume([]) == 0.0

    def test_all_warmups_returns_zero(self):
        class FakeSet:
            def __init__(self):
                self.reps = 10
                self.weight_kg = 60.0
                self.is_warmup = True

        assert compute_gym_volume([FakeSet(), FakeSet()]) == 0.0


class TestEstimate1rm:
    def test_single_rep_returns_weight(self):
        assert estimate_1rm(100.0, 1) == 100.0

    def test_five_rep_max_epley(self):
        expected = 100.0 * (1 + 5 / 30)
        assert estimate_1rm(100.0, 5) == round(expected, 2)

    def test_higher_reps_lower_weight_gives_similar_1rm(self):
        one = estimate_1rm(100.0, 5)
        two = estimate_1rm(80.0, 10)
        assert abs(one - two) < 15


class TestComputeAtlCtl:
    def test_empty_series_returns_zeros(self):
        result = compute_atl_ctl([])
        assert result == TrainingLoad(acute_load=0.0, chronic_load=0.0, tsb=0.0)

    def test_single_day_returns_same_value(self):
        result = compute_atl_ctl([50.0])
        assert result.acute_load == 50.0
        assert result.chronic_load == 50.0
        assert result.tsb == 0.0

    def test_increasing_load_produces_negative_tsb(self):
        """Heavy training load: ATL rises faster than CTL → TSB negative."""
        high_load = [100.0] * 14
        result = compute_atl_ctl(high_load)
        assert result.acute_load > result.chronic_load
        assert result.tsb < 0

    def test_rest_period_produces_positive_tsb(self):
        """ATL trained hard then rest: CTL > ATL → TSB positive (fresh)."""
        training = [80.0] * 30
        rest = [10.0] * 10
        result = compute_atl_ctl(training + rest)
        assert result.tsb > 0
