import asyncio
import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://trainer:trainer@localhost:5433/trainer_test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6380/0")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6380/1")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6380/2")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("OPENAI_API_KEY", "test-key")

from app.db.session import Base
from app.main import app
from app.core.security import create_access_token


TEST_DATABASE_URL = os.environ["DATABASE_URL"]


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine):
    session_factory = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession):
    from app.db.repositories.user_repo import UserRepository
    from app.core.security import hash_password

    repo = UserRepository(db_session)
    user = await repo.create(
        email="test@example.com",
        hashed_password=hash_password("testpassword123"),
        display_name="Test Athlete",
        max_hr=185,
        resting_hr=55,
        vo2max_estimate=48.5,
        primary_goal="general",
        experience_level="intermediate",
    )
    return user


@pytest.fixture
def auth_headers(test_user):
    token = create_access_token({"sub": str(test_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def async_client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client
