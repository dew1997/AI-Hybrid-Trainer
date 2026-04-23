import pytest
from httpx import AsyncClient


@pytest.mark.integration
class TestHealth:
    async def test_health_returns_ok(self, async_client: AsyncClient):
        resp = await async_client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    async def test_health_ready_checks_dependencies(self, async_client: AsyncClient):
        resp = await async_client.get("/health/ready")
        assert resp.status_code in (200, 503)
        body = resp.json()
        assert "status" in body
        assert "checks" in body
        assert "database" in body["checks"]
        assert "redis" in body["checks"]
