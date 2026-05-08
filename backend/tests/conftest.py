"""
Shared test fixtures for KrishiBondhu backend tests.

Provides:
  - Async SQLite database (in-memory) with auto-rollback
  - FastAPI TestClient with dependency overrides
  - Mock Redis
  - Required environment variables
"""

import os
import sys
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from typing import AsyncGenerator

# Set test environment variables BEFORE any app imports
os.environ.update({
    "DATABASE_URL": "sqlite+aiosqlite:///",
    "REDIS_URL": "",
    "GROQ_API_KEY": "",
    "HUGGINGFACE_API_KEY": "",
    "WEATHER_API_KEY": "",
    "DEBUG": "true",
    "UPLOAD_DIR": "/tmp/test_uploads",
})

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool


# ---------------------------------------------------------------------------
# Mock Redis globally before app import
# ---------------------------------------------------------------------------
class MockRedis:
    """In-memory mock Redis for tests."""

    def __init__(self, *args, **kwargs):
        self._store = {}

    def get(self, key):
        return self._store.get(key)

    def set(self, key, value, **kwargs):
        self._store[key] = value

    def setex(self, key, ttl, value):
        self._store[key] = value

    def ping(self):
        return True

    def delete(self, key):
        self._store.pop(key, None)

    @classmethod
    def from_url(cls, *args, **kwargs):
        return cls()


# ---------------------------------------------------------------------------
# Database fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def async_engine():
    """Create an in-memory SQLite async engine."""
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Import all models and create tables
    from app.models.db_models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional database session that rolls back after each test."""
    session_factory = async_sessionmaker(async_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()


# ---------------------------------------------------------------------------
# FastAPI TestClient
# ---------------------------------------------------------------------------

@pytest.fixture
def test_client(db_session):
    """Create a FastAPI TestClient with database dependency overrides."""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.db import get_db

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_redis():
    """Provide a MockRedis instance."""
    return MockRedis()
