from datetime import UTC, datetime

import pytest
from httpx import AsyncClient


def _run_payload(**kwargs):
    base = {
        "workout_type": "run",
        "started_at": datetime.now(UTC).isoformat(),
        "duration_seconds": 3600,
        "distance_meters": 10000,
        "avg_pace_sec_per_km": 360,
        "avg_hr": 145,
    }
    base.update(kwargs)
    return base


def _gym_payload(**kwargs):
    base = {
        "workout_type": "gym",
        "started_at": datetime.now(UTC).isoformat(),
        "duration_seconds": 3600,
        "sets": [{"set_number": 1, "exercise_name": "squat", "reps": 5, "weight_kg": 100.0}],
    }
    base.update(kwargs)
    return base


@pytest.mark.integration
class TestLogWorkout:
    async def test_log_run_returns_201(
        self, async_client: AsyncClient, test_user, auth_headers, test_engine
    ):
        resp = await async_client.post(
            "/api/v1/workouts", json=_run_payload(), headers=auth_headers
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["workout_type"] == "run"
        assert "id" in data

    async def test_log_gym_returns_201(
        self, async_client: AsyncClient, test_user, auth_headers, test_engine
    ):
        resp = await async_client.post(
            "/api/v1/workouts", json=_gym_payload(), headers=auth_headers
        )
        assert resp.status_code == 201
        assert resp.json()["workout_type"] == "gym"

    async def test_log_workout_requires_auth(self, async_client: AsyncClient, test_engine):
        resp = await async_client.post("/api/v1/workouts", json=_run_payload())
        assert resp.status_code == 403

    async def test_run_without_distance_returns_422(
        self, async_client: AsyncClient, auth_headers, test_engine
    ):
        payload = _run_payload()
        del payload["distance_meters"]
        resp = await async_client.post("/api/v1/workouts", json=payload, headers=auth_headers)
        assert resp.status_code == 422


@pytest.mark.integration
class TestListWorkouts:
    async def test_list_returns_logged_workouts(
        self, async_client: AsyncClient, test_user, auth_headers, test_engine
    ):
        await async_client.post("/api/v1/workouts", json=_run_payload(), headers=auth_headers)
        resp = await async_client.get("/api/v1/workouts", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        assert "meta" in body
        assert len(body["data"]) >= 1

    async def test_list_requires_auth(self, async_client: AsyncClient, test_engine):
        resp = await async_client.get("/api/v1/workouts")
        assert resp.status_code == 403

    async def test_filter_by_type(
        self, async_client: AsyncClient, test_user, auth_headers, test_engine
    ):
        await async_client.post("/api/v1/workouts", json=_run_payload(), headers=auth_headers)
        await async_client.post("/api/v1/workouts", json=_gym_payload(), headers=auth_headers)
        resp = await async_client.get(
            "/api/v1/workouts?workout_type=run", headers=auth_headers
        )
        assert resp.status_code == 200
        for w in resp.json()["data"]:
            assert w["workout_type"] == "run"
