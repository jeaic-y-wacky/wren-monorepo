"""Pytest fixtures for Wren Backend tests."""

import asyncio
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from wren_backend.api.deps import init_dependencies
from wren_backend.core.credentials import CredentialStore
from wren_backend.core.executor import Executor
from wren_backend.core.scheduler import Scheduler
from wren_backend.core.storage import Storage
from wren_backend.main import app


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def storage(tmp_path: Path):
    """Create a temporary storage instance."""
    db_path = tmp_path / "test.db"
    db_url = f"sqlite+aiosqlite:///{db_path}"
    store = Storage(db_url)
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


@pytest.fixture
def credential_store():
    """Create a credential store instance."""
    return CredentialStore()


@pytest_asyncio.fixture
async def client(storage, scheduler, credential_store):
    """Create an async test client with initialized dependencies."""
    init_dependencies(storage, scheduler, credential_store)
    scheduler.start()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    scheduler.shutdown(wait=False)


@pytest.fixture
def api_key():
    """Return a test API key (used as user_id in Phase 1)."""
    return "test_user_12345678"


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
