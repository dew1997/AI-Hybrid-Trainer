import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio(loop_scope="session")


def _email():
    return f"athlete-{uuid.uuid4().hex[:8]}@example.com"


async def _token(client: AsyncClient) -> str:
    email = _email()
    resp = await client.post("/api/v1/auth/register", json={
        "email": email, "password": "testpass123",
    })
    return resp.json()["access_token"]


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
    async def test_log_run_returns_201(self, async_client: AsyncClient):
        headers = {"Authorization": f"Bearer {await _token(async_client)}"}
        resp = await async_client.post("/api/v1/workouts", json=_run_payload(), headers=headers)
        assert resp.status_code == 201
        data = resp.json()
        assert "workout" in data
        assert data["workout"]["workout_type"] == "run"
        assert "id" in data["workout"]

    async def test_log_gym_returns_201(self, async_client: AsyncClient):
        headers = {"Authorization": f"Bearer {await _token(async_client)}"}
        resp = await async_client.post("/api/v1/workouts", json=_gym_payload(), headers=headers)
        assert resp.status_code == 201
        assert resp.json()["workout"]["workout_type"] == "gym"

    async def test_log_workout_requires_auth(self, async_client: AsyncClient):
        resp = await async_client.post("/api/v1/workouts", json=_run_payload())
        assert resp.status_code == 403

    async def test_run_without_distance_returns_422(self, async_client: AsyncClient):
        headers = {"Authorization": f"Bearer {await _token(async_client)}"}
        payload = _run_payload()
        del payload["distance_meters"]
        resp = await async_client.post("/api/v1/workouts", json=payload, headers=headers)
        assert resp.status_code == 422


@pytest.mark.integration
class TestListWorkouts:
    async def test_list_returns_logged_workouts(self, async_client: AsyncClient):
        headers = {"Authorization": f"Bearer {await _token(async_client)}"}
        await async_client.post("/api/v1/workouts", json=_run_payload(), headers=headers)
        resp = await async_client.get("/api/v1/workouts", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        assert "meta" in body
        assert len(body["data"]) >= 1

    async def test_list_requires_auth(self, async_client: AsyncClient):
        resp = await async_client.get("/api/v1/workouts")
        assert resp.status_code == 403

    async def test_filter_by_type(self, async_client: AsyncClient):
        headers = {"Authorization": f"Bearer {await _token(async_client)}"}
        await async_client.post("/api/v1/workouts", json=_run_payload(), headers=headers)
        await async_client.post("/api/v1/workouts", json=_gym_payload(), headers=headers)
        resp = await async_client.get("/api/v1/workouts?workout_type=run", headers=headers)
        assert resp.status_code == 200
        for w in resp.json()["data"]:
            assert w["workout_type"] == "run"
