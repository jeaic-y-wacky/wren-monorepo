"""Pytest fixtures for Wren Backend tests."""

import asyncio

import pytest
import pytest_asyncio
from fastapi import Header, HTTPException
from httpx import ASGITransport, AsyncClient

from wren_backend.api.deps import get_current_user_id, init_dependencies
from wren_backend.core.executor import Executor
from wren_backend.core.scheduler import Scheduler
from wren_backend.main import app

from .fakes import InMemoryCredentialStore, InMemoryStorage


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def storage():
    """Create an in-memory storage instance."""
    store = InMemoryStorage()
    await store.connect()
    yield store
    await store.close()


@pytest.fixture
def scheduler():
    """Create a scheduler instance (not started)."""
    return Scheduler()


@pytest.fixture
def executor():
    """Create an executor instance."""
    return Executor(timeout_seconds=30)


@pytest_asyncio.fixture
async def credential_store():
    """Create an in-memory credential store instance."""
    store = InMemoryCredentialStore()
    await store.connect()
    return store


@pytest.fixture
def api_key():
    """Return a test API key (used as user_id in Phase 1)."""
    return "test_user_12345678"


@pytest_asyncio.fixture
async def client(storage, scheduler, credential_store, api_key):
    """Create an async test client with initialized dependencies."""
    init_dependencies(storage, scheduler, credential_store)
    scheduler.start()

    # Override auth to skip Supabase JWT / API-key lookup.
    # Preserves 401 for missing credentials (test_validate_requires_auth).
    async def override_auth(
        x_api_key: str | None = Header(None, alias="X-API-Key"),
        authorization: str | None = Header(None),
    ) -> str:
        if not x_api_key and not authorization:
            raise HTTPException(status_code=401, detail="Missing authentication")
        return api_key

    app.dependency_overrides[get_current_user_id] = override_auth

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    scheduler.shutdown(wait=False)
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(api_key):
    """Return headers with API key authentication."""
    return {"X-API-Key": api_key}


@pytest.fixture
def sample_script():
    """Return a sample Python script for testing."""
    return '''
def hello_world():
    print("Hello from Wren!")
    return "success"

def daily_report():
    print("Running daily report...")
    return {"status": "done"}
'''


@pytest.fixture
def sample_metadata():
    """Return sample deployment metadata."""
    return {
        "integrations": [],
        "triggers": [
            {
                "type": "schedule",
                "func": "daily_report",
                "config": {"cron": "0 9 * * *", "timezone": "UTC"},
            }
        ],
    }
