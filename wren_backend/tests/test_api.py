"""Tests for API endpoints."""

import pytest


@pytest.mark.asyncio
async def test_health_check(client):
    """Test health check endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_root_endpoint(client):
    """Test root endpoint returns API info."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Wren Backend"
    assert "version" in data


@pytest.mark.asyncio
async def test_validate_empty_request(client, auth_headers):
    """Test validation with no integrations."""
    response = await client.post(
        "/v1/integrations/validate",
        json={"integrations": []},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    assert data["errors"] == []


@pytest.mark.asyncio
async def test_validate_missing_integration(client, auth_headers):
    """Test validation fails for unconfigured integration."""
    response = await client.post(
        "/v1/integrations/validate",
        json={"integrations": ["gmail"]},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False
    assert len(data["errors"]) == 1
    assert data["errors"][0]["code"] == "INTEGRATION_NOT_CONFIGURED"
    assert data["errors"][0]["integration"] == "gmail"


@pytest.mark.asyncio
async def test_validate_requires_auth(client):
    """Test validation requires authentication."""
    response = await client.post(
        "/v1/integrations/validate",
        json={"integrations": []},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_deploy_script(client, auth_headers, sample_script, sample_metadata):
    """Test deploying a script."""
    response = await client.post(
        "/v1/scripts/deploy",
        json={
            "script": sample_script,
            "metadata": sample_metadata,
            "name": "test_deployment",
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["deployment_id"].startswith("dep_")
    assert data["status"] == "active"
    assert data["triggers_registered"] == 1


@pytest.mark.asyncio
async def test_list_deployments(client, auth_headers, sample_script, sample_metadata):
    """Test listing deployments."""
    # Deploy a script first
    await client.post(
        "/v1/scripts/deploy",
        json={
            "script": sample_script,
            "metadata": sample_metadata,
            "name": "list_test",
        },
        headers=auth_headers,
    )

    # List deployments
    response = await client.get("/v1/deployments", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "deployments" in data
    assert len(data["deployments"]) >= 1
    assert any(d["name"] == "list_test" for d in data["deployments"])


@pytest.mark.asyncio
async def test_get_deployment(client, auth_headers, sample_script, sample_metadata):
    """Test getting a specific deployment."""
    # Deploy a script first
    deploy_response = await client.post(
        "/v1/scripts/deploy",
        json={"script": sample_script, "metadata": sample_metadata},
        headers=auth_headers,
    )
    deployment_id = deploy_response.json()["deployment_id"]

    # Get the deployment
    response = await client.get(
        f"/v1/deployments/{deployment_id}", headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == deployment_id
    assert data["status"] == "active"


@pytest.mark.asyncio
async def test_delete_deployment(client, auth_headers, sample_script, sample_metadata):
    """Test deleting a deployment."""
    # Deploy a script first
    deploy_response = await client.post(
        "/v1/scripts/deploy",
        json={"script": sample_script, "metadata": sample_metadata},
        headers=auth_headers,
    )
    deployment_id = deploy_response.json()["deployment_id"]

    # Delete the deployment
    response = await client.delete(
        f"/v1/deployments/{deployment_id}", headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["status"] == "deleted"

    # Verify it's gone from list
    list_response = await client.get("/v1/deployments", headers=auth_headers)
    deployments = list_response.json()["deployments"]
    assert not any(d["id"] == deployment_id for d in deployments)


@pytest.mark.asyncio
async def test_pause_resume_deployment(
    client, auth_headers, sample_script, sample_metadata
):
    """Test pausing and resuming a deployment."""
    # Deploy a script first
    deploy_response = await client.post(
        "/v1/scripts/deploy",
        json={"script": sample_script, "metadata": sample_metadata},
        headers=auth_headers,
    )
    deployment_id = deploy_response.json()["deployment_id"]

    # Pause
    pause_response = await client.post(
        f"/v1/deployments/{deployment_id}/pause", headers=auth_headers
    )
    assert pause_response.status_code == 200
    assert pause_response.json()["status"] == "paused"

    # Resume
    resume_response = await client.post(
        f"/v1/deployments/{deployment_id}/resume", headers=auth_headers
    )
    assert resume_response.status_code == 200
    assert resume_response.json()["status"] == "active"


@pytest.mark.asyncio
async def test_list_runs_empty(client, auth_headers, sample_script, sample_metadata):
    """Test listing runs for a deployment with no runs."""
    # Deploy a script first
    deploy_response = await client.post(
        "/v1/scripts/deploy",
        json={"script": sample_script, "metadata": sample_metadata},
        headers=auth_headers,
    )
    deployment_id = deploy_response.json()["deployment_id"]

    # List runs
    response = await client.get(
        f"/v1/deployments/{deployment_id}/runs", headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["runs"] == []


@pytest.mark.asyncio
async def test_deployment_not_found(client, auth_headers):
    """Test getting a non-existent deployment returns 404."""
    response = await client.get(
        "/v1/deployments/dep_nonexistent", headers=auth_headers
    )
    assert response.status_code == 404
@pytest.mark.asyncio
async def test_deploy_invalid_cron(client, auth_headers, sample_script):
    """Test deploy fails for invalid cron expression."""
    response = await client.post(
        "/v1/scripts/deploy",
        json={
            "script": sample_script,
            "metadata": {
                "integrations": [],
                "triggers": [
                    {
                        "type": "schedule",
                        "func": "my_func",
                        "config": {"cron": "invalid", "timezone": "UTC"},
                    }
                ],
            },
        },
        headers=auth_headers,
    )
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["errors"][0]["code"] == "INVALID_CRON_EXPRESSION"


@pytest.mark.asyncio
async def test_deploy_missing_cron(client, auth_headers, sample_script):
    """Test deploy fails when cron is missing for schedule trigger."""
    response = await client.post(
        "/v1/scripts/deploy",
        json={
            "script": sample_script,
            "metadata": {
                "integrations": [],
                "triggers": [
                    {
                        "type": "schedule",
                        "func": "my_func",
                        "config": {"timezone": "UTC"},
                    }
                ],
            },
        },
        headers=auth_headers,
    )
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["errors"][0]["code"] == "MISSING_CRON_EXPRESSION"
