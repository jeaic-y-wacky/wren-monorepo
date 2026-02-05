"""Tests for storage layer."""

import pytest

from wren_backend.models.deployment import (
    DeploymentStatus,
    Trigger,
    TriggerConfig,
    TriggerType,
)
from wren_backend.models.run import RunStatus


@pytest.mark.asyncio
async def test_create_deployment(storage):
    """Test creating a deployment."""
    triggers = [
        Trigger(
            type=TriggerType.SCHEDULE,
            func="my_func",
            config=TriggerConfig(cron="0 9 * * *"),
        )
    ]

    deployment = await storage.create_deployment(
        user_id="user_123",
        name="test_deployment",
        script_content="print('hello')",
        triggers=triggers,
        integrations=["gmail"],
    )

    assert deployment.id.startswith("dep_")
    assert deployment.user_id == "user_123"
    assert deployment.name == "test_deployment"
    assert deployment.status == DeploymentStatus.ACTIVE
    assert len(deployment.triggers) == 1
    assert deployment.integrations == ["gmail"]


@pytest.mark.asyncio
async def test_get_deployment(storage):
    """Test retrieving a deployment by ID."""
    deployment = await storage.create_deployment(
        user_id="user_123",
        name="get_test",
        script_content="print('test')",
        triggers=[],
        integrations=[],
    )

    retrieved = await storage.get_deployment(deployment.id)
    assert retrieved is not None
    assert retrieved.id == deployment.id
    assert retrieved.name == "get_test"


@pytest.mark.asyncio
async def test_get_deployment_not_found(storage):
    """Test retrieving a non-existent deployment returns None."""
    result = await storage.get_deployment("dep_nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_get_deployments_by_user(storage):
    """Test listing deployments for a user."""
    # Create deployments for different users
    await storage.create_deployment(
        user_id="user_a",
        name="deployment_a1",
        script_content="print('a1')",
        triggers=[],
        integrations=[],
    )
    await storage.create_deployment(
        user_id="user_a",
        name="deployment_a2",
        script_content="print('a2')",
        triggers=[],
        integrations=[],
    )
    await storage.create_deployment(
        user_id="user_b",
        name="deployment_b1",
        script_content="print('b1')",
        triggers=[],
        integrations=[],
    )

    # Get user_a's deployments
    deployments = await storage.get_deployments_by_user("user_a")
    assert len(deployments) == 2
    assert all(d.user_id == "user_a" for d in deployments)


@pytest.mark.asyncio
async def test_update_deployment_status(storage):
    """Test updating a deployment's status."""
    deployment = await storage.create_deployment(
        user_id="user_123",
        name="status_test",
        script_content="print('test')",
        triggers=[],
        integrations=[],
    )

    await storage.update_deployment_status(deployment.id, DeploymentStatus.PAUSED)

    updated = await storage.get_deployment(deployment.id)
    assert updated.status == DeploymentStatus.PAUSED


@pytest.mark.asyncio
async def test_delete_deployment(storage):
    """Test soft deleting a deployment."""
    deployment = await storage.create_deployment(
        user_id="user_123",
        name="delete_test",
        script_content="print('test')",
        triggers=[],
        integrations=[],
    )

    await storage.delete_deployment(deployment.id)

    # Should still exist but with deleted status
    deleted = await storage.get_deployment(deployment.id)
    assert deleted.status == DeploymentStatus.DELETED

    # Should not appear in user's deployments list
    deployments = await storage.get_deployments_by_user("user_123")
    assert not any(d.id == deployment.id for d in deployments)


@pytest.mark.asyncio
async def test_create_run(storage):
    """Test creating a run record."""
    deployment = await storage.create_deployment(
        user_id="user_123",
        name="run_test",
        script_content="print('test')",
        triggers=[],
        integrations=[],
    )

    run = await storage.create_run(
        deployment_id=deployment.id,
        user_id="user_123",
        trigger_type="schedule",
        trigger_func="my_func",
    )

    assert run.id.startswith("run_")
    assert run.deployment_id == deployment.id
    assert run.status == RunStatus.PENDING


@pytest.mark.asyncio
async def test_update_run_lifecycle(storage):
    """Test the full run lifecycle: pending -> running -> completed."""
    deployment = await storage.create_deployment(
        user_id="user_123",
        name="lifecycle_test",
        script_content="print('test')",
        triggers=[],
        integrations=[],
    )

    run = await storage.create_run(
        deployment_id=deployment.id,
        user_id="user_123",
        trigger_type="schedule",
        trigger_func="my_func",
    )
    assert run.status == RunStatus.PENDING

    # Start the run
    await storage.update_run_started(run.id)
    started_run = await storage.get_run(run.id)
    assert started_run.status == RunStatus.RUNNING
    assert started_run.started_at is not None

    # Complete the run
    await storage.update_run_completed(
        run_id=run.id,
        status=RunStatus.SUCCESS,
        exit_code=0,
        stdout="Hello, world!",
        stderr="",
    )
    completed_run = await storage.get_run(run.id)
    assert completed_run.status == RunStatus.SUCCESS
    assert completed_run.exit_code == 0
    assert completed_run.stdout == "Hello, world!"
    assert completed_run.completed_at is not None
    assert completed_run.duration_ms is not None


@pytest.mark.asyncio
async def test_get_runs_by_deployment(storage):
    """Test listing runs for a deployment."""
    deployment = await storage.create_deployment(
        user_id="user_123",
        name="runs_list_test",
        script_content="print('test')",
        triggers=[],
        integrations=[],
    )

    # Create multiple runs
    for i in range(3):
        run = await storage.create_run(
            deployment_id=deployment.id,
            user_id="user_123",
            trigger_type="schedule",
            trigger_func=f"func_{i}",
        )
        await storage.update_run_started(run.id)
        await storage.update_run_completed(
            run_id=run.id,
            status=RunStatus.SUCCESS,
            exit_code=0,
            stdout=f"output_{i}",
            stderr="",
        )

    runs = await storage.get_runs_by_deployment(deployment.id)
    assert len(runs) == 3


@pytest.mark.asyncio
async def test_get_last_run(storage):
    """Test getting the most recent run for a deployment."""
    deployment = await storage.create_deployment(
        user_id="user_123",
        name="last_run_test",
        script_content="print('test')",
        triggers=[],
        integrations=[],
    )

    # Create runs
    for i in range(3):
        run = await storage.create_run(
            deployment_id=deployment.id,
            user_id="user_123",
            trigger_type="schedule",
            trigger_func=f"func_{i}",
        )
        await storage.update_run_started(run.id)
        await storage.update_run_completed(
            run_id=run.id,
            status=RunStatus.SUCCESS,
            exit_code=0,
            stdout=f"output_{i}",
            stderr="",
        )

    last_run = await storage.get_last_run(deployment.id)
    assert last_run is not None
    assert last_run.trigger_func == "func_2"


@pytest.mark.asyncio
async def test_get_active_deployments(storage):
    """Test getting all active deployments for scheduler startup."""
    # Create active and paused deployments
    await storage.create_deployment(
        user_id="user_1",
        name="active_1",
        script_content="print('active')",
        triggers=[],
        integrations=[],
    )
    deployment2 = await storage.create_deployment(
        user_id="user_2",
        name="paused_1",
        script_content="print('paused')",
        triggers=[],
        integrations=[],
    )
    await storage.update_deployment_status(deployment2.id, DeploymentStatus.PAUSED)

    active = await storage.get_active_deployments()
    assert all(d.status == DeploymentStatus.ACTIVE for d in active)
    assert any(d.name == "active_1" for d in active)
    assert not any(d.name == "paused_1" for d in active)
