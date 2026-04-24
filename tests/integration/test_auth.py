import uuid

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio(loop_scope="session")


def _email():
    return f"user-{uuid.uuid4().hex[:8]}@example.com"


async def _register_and_login(client: AsyncClient, email: str, password: str = "testpass123"):
    await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return resp.json()["access_token"]


@pytest.mark.integration
class TestRegister:
    async def test_register_creates_user(self, async_client: AsyncClient):
        resp = await async_client.post("/api/v1/auth/register", json={
            "email": _email(),
            "password": "securepass123",
            "display_name": "New User",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert "user" in data
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_duplicate_email_returns_409(self, async_client: AsyncClient):
        email = _email()
        payload = {"email": email, "password": "pass1234"}
        await async_client.post("/api/v1/auth/register", json=payload)
        resp = await async_client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 409

    async def test_register_requires_email(self, async_client: AsyncClient):
        resp = await async_client.post("/api/v1/auth/register", json={"password": "pass1234"})
        assert resp.status_code == 422


@pytest.mark.integration
class TestLogin:
    async def test_login_returns_tokens(self, async_client: AsyncClient):
        email = _email()
        await async_client.post("/api/v1/auth/register", json={
            "email": email, "password": "mypassword",
        })
        resp = await async_client.post("/api/v1/auth/login", json={
            "email": email, "password": "mypassword",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_wrong_password_returns_401(self, async_client: AsyncClient):
        email = _email()
        await async_client.post("/api/v1/auth/register", json={
            "email": email, "password": "correct",
        })
        resp = await async_client.post("/api/v1/auth/login", json={
            "email": email, "password": "wrong",
        })
        assert resp.status_code == 401

    async def test_unknown_email_returns_401(self, async_client: AsyncClient):
        resp = await async_client.post("/api/v1/auth/login", json={
            "email": "nobody@example.com", "password": "whatever",
        })
        assert resp.status_code == 401


@pytest.mark.integration
class TestMe:
    async def test_me_returns_current_user(self, async_client: AsyncClient):
        email = _email()
        token = await _register_and_login(async_client, email)
        resp = await async_client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        assert resp.json()["email"] == email

    async def test_me_without_token_returns_403(self, async_client: AsyncClient):
        resp = await async_client.get("/api/v1/auth/me")
        assert resp.status_code == 403

    async def test_patch_me_updates_profile(self, async_client: AsyncClient):
        token = await _register_and_login(async_client, _email())
        resp = await async_client.patch(
            "/api/v1/auth/me",
            json={"display_name": "Updated Name", "weight_kg": 75.0},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["display_name"] == "Updated Name"
