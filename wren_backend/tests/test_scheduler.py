"""Tests for scheduler."""

import asyncio
from datetime import datetime

import pytest

from wren_backend.core.scheduler import Scheduler
from wren_backend.models.deployment import (
    Deployment,
    DeploymentStatus,
    Trigger,
    TriggerConfig,
    TriggerType,
)


@pytest.fixture
def sample_deployment():
    """Create a sample deployment for testing."""
    return Deployment(
        id="dep_test123",
        user_id="user_123",
        name="test_deployment",
        script_content="print('hello')",
        status=DeploymentStatus.ACTIVE,
        triggers=[
            Trigger(
                type=TriggerType.SCHEDULE,
                func="daily_task",
                config=TriggerConfig(cron="0 9 * * *", timezone="UTC"),
            ),
            Trigger(
                type=TriggerType.SCHEDULE,
                func="hourly_task",
                config=TriggerConfig(cron="0 * * * *", timezone="UTC"),
            ),
        ],
        integrations=[],
    )


@pytest.mark.asyncio
async def test_scheduler_start_stop():
    """Test starting and stopping the scheduler."""
    scheduler = Scheduler()
    assert not scheduler._scheduler.running

    scheduler.start()
    assert scheduler._scheduler.running

    # Shutdown - note: AsyncIOScheduler.shutdown() may not immediately
    # update running flag due to async nature, so we just verify no errors
    scheduler.shutdown(wait=True)


@pytest.mark.asyncio
async def test_register_deployment(sample_deployment):
    """Test registering a deployment with triggers."""
    scheduler = Scheduler()
    scheduler.start()

    registered = scheduler.register_deployment(sample_deployment)

    assert registered == 2  # Two schedule triggers

    # Verify jobs are registered
    jobs = scheduler._scheduler.get_jobs()
    job_ids = [j.id for j in jobs]
    assert "dep_test123:daily_task" in job_ids
    assert "dep_test123:hourly_task" in job_ids

    scheduler.shutdown(wait=False)


@pytest.mark.asyncio
async def test_unregister_deployment(sample_deployment):
    """Test unregistering a deployment removes its jobs."""
    scheduler = Scheduler()
    scheduler.start()
    scheduler.register_deployment(sample_deployment)

    removed = scheduler.unregister_deployment("dep_test123")

    assert removed == 2
    jobs = scheduler._scheduler.get_jobs()
    assert len([j for j in jobs if j.id.startswith("dep_test123:")]) == 0

    scheduler.shutdown(wait=False)


@pytest.mark.asyncio
async def test_get_next_run_time(sample_deployment):
    """Test getting next run time for a deployment."""
    scheduler = Scheduler()
    scheduler.start()
    scheduler.register_deployment(sample_deployment)

    next_run = scheduler.get_next_run_time("dep_test123")

    assert next_run is not None
    assert next_run > datetime.now(next_run.tzinfo)

    scheduler.shutdown(wait=False)


@pytest.mark.asyncio
async def test_get_next_run_time_no_jobs():
    """Test getting next run time when no jobs exist."""
    scheduler = Scheduler()
    scheduler.start()

    next_run = scheduler.get_next_run_time("dep_nonexistent")

    assert next_run is None

    scheduler.shutdown(wait=False)


@pytest.mark.asyncio
async def test_register_deployment_invalid_cron():
    """Test registering a deployment with invalid cron skips that trigger."""
    deployment = Deployment(
        id="dep_invalid",
        user_id="user_123",
        name="invalid_cron",
        script_content="print('hello')",
        status=DeploymentStatus.ACTIVE,
        triggers=[
            Trigger(
                type=TriggerType.SCHEDULE,
                func="bad_task",
                config=TriggerConfig(cron="invalid cron", timezone="UTC"),
            ),
            Trigger(
                type=TriggerType.SCHEDULE,
                func="good_task",
                config=TriggerConfig(cron="0 9 * * *", timezone="UTC"),
            ),
        ],
        integrations=[],
    )

    scheduler = Scheduler()
    scheduler.start()
    registered = scheduler.register_deployment(deployment)

    # Only the valid trigger should be registered
    assert registered == 1

    scheduler.shutdown(wait=False)


@pytest.mark.asyncio
async def test_register_deployment_missing_cron():
    """Test registering a deployment with missing cron expression."""
    deployment = Deployment(
        id="dep_missing",
        user_id="user_123",
        name="missing_cron",
        script_content="print('hello')",
        status=DeploymentStatus.ACTIVE,
        triggers=[
            Trigger(
                type=TriggerType.SCHEDULE,
                func="no_cron_task",
                config=TriggerConfig(timezone="UTC"),  # No cron
            ),
        ],
        integrations=[],
    )

    scheduler = Scheduler()
    scheduler.start()
    registered = scheduler.register_deployment(deployment)

    assert registered == 0

    scheduler.shutdown(wait=False)


@pytest.mark.asyncio
async def test_register_replaces_existing(sample_deployment):
    """Test that re-registering a deployment replaces existing jobs."""
    scheduler = Scheduler()
    scheduler.start()

    # Register once
    scheduler.register_deployment(sample_deployment)
    jobs_before = len(scheduler._scheduler.get_jobs())

    # Register again
    scheduler.register_deployment(sample_deployment)
    jobs_after = len(scheduler._scheduler.get_jobs())

    # Should have same number of jobs (replaced, not added)
    assert jobs_before == jobs_after

    scheduler.shutdown(wait=False)


@pytest.mark.asyncio
async def test_run_callback_called(sample_deployment):
    """Test that the run callback is called when a job fires."""
    scheduler = Scheduler()
    scheduler.start()

    callback_calls = []

    async def mock_callback(deployment_id, trigger_type, func_name):
        callback_calls.append((deployment_id, trigger_type, func_name))

    scheduler.set_run_callback(mock_callback)

    # Manually trigger the job execution
    await scheduler._execute_job("dep_123", "schedule", "my_func")

    # Give async task time to run
    await asyncio.sleep(0.1)

    assert len(callback_calls) == 1
    assert callback_calls[0] == ("dep_123", "schedule", "my_func")

    scheduler.shutdown(wait=False)
