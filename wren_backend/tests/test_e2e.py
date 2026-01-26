"""End-to-end tests for Wren Backend.

Tests the backend API directly without depending on wren_src.
This validates the backend accepts the payloads the SDK sends.
"""

import pytest


class TestE2EWorkflow:
    """End-to-end tests for the backend API."""

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Test the health endpoint."""
        response = await client.get("/health")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_full_deploy_workflow(self, client, auth_headers):
        """Test the full deploy workflow: deploy -> list -> get -> delete."""
        # Sample script content (what SDK would send)
        script_content = '''import wren

@wren.on_schedule("0 9 * * *")
def daily_report():
    return "ok"
'''
        # Metadata as SDK sends it (note: timezone can be null)
        deploy_request = {
            "script": script_content,
            "metadata": {
                "integrations": [],
                "triggers": [
                    {
                        "type": "schedule",
                        "func": "daily_report",
                        "config": {
                            "cron": "0 9 * * *",
                            "timezone": None,  # SDK sends null when not specified
                        },
                    }
                ],
            },
        }

        # Step 1: Deploy
        response = await client.post(
            "/v1/scripts/deploy",
            json=deploy_request,
            headers=auth_headers,
        )
        assert response.status_code == 200, f"Deploy failed: {response.text}"

        deploy_data = response.json()
        assert "deployment_id" in deploy_data
        deployment_id = deploy_data["deployment_id"]
        assert deploy_data["status"] == "active"
        assert deploy_data["triggers_registered"] == 1

        # Step 2: List deployments
        response = await client.get("/v1/deployments", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        deployments = data["deployments"]
        assert len(deployments) >= 1
        assert any(d["id"] == deployment_id for d in deployments)

        # Step 3: Get specific deployment
        response = await client.get(
            f"/v1/deployments/{deployment_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        deployment = response.json()
        assert deployment["id"] == deployment_id
        assert deployment["status"] == "active"
        assert len(deployment["triggers"]) == 1
        assert deployment["triggers"][0]["func"] == "daily_report"

        # Step 4: Delete deployment (soft delete)
        response = await client.delete(
            f"/v1/deployments/{deployment_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200

        # Verify status is "deleted"
        response = await client.get(
            f"/v1/deployments/{deployment_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "deleted"

    @pytest.mark.asyncio
    async def test_deploy_with_explicit_timezone(self, client, auth_headers):
        """Test deployment with explicit timezone."""
        deploy_request = {
            "script": "def task(): pass",
            "metadata": {
                "integrations": [],
                "triggers": [
                    {
                        "type": "schedule",
                        "func": "task",
                        "config": {
                            "cron": "*/5 * * * *",
                            "timezone": "America/New_York",
                        },
                    }
                ],
            },
        }

        response = await client.post(
            "/v1/scripts/deploy",
            json=deploy_request,
            headers=auth_headers,
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_deploy_invalid_cron(self, client, auth_headers):
        """Test that deployment rejects invalid cron expressions."""
        deploy_request = {
            "script": "def test(): pass",
            "metadata": {
                "integrations": [],
                "triggers": [
                    {
                        "type": "schedule",
                        "func": "test",
                        "config": {"cron": "not a cron"},
                    }
                ],
            },
        }

        response = await client.post(
            "/v1/scripts/deploy",
            json=deploy_request,
            headers=auth_headers,
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_deploy_missing_cron(self, client, auth_headers):
        """Test that schedule trigger requires cron expression."""
        deploy_request = {
            "script": "def test(): pass",
            "metadata": {
                "integrations": [],
                "triggers": [
                    {
                        "type": "schedule",
                        "func": "test",
                        "config": {},  # Missing cron
                    }
                ],
            },
        }

        response = await client.post(
            "/v1/scripts/deploy",
            json=deploy_request,
            headers=auth_headers,
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_pause_resume_deployment(self, client, auth_headers):
        """Test pausing and resuming a deployment."""
        # Create deployment
        deploy_request = {
            "script": "def task(): pass",
            "metadata": {
                "integrations": [],
                "triggers": [
                    {
                        "type": "schedule",
                        "func": "task",
                        "config": {"cron": "0 * * * *"},
                    }
                ],
            },
        }

        response = await client.post(
            "/v1/scripts/deploy",
            json=deploy_request,
            headers=auth_headers,
        )
        assert response.status_code == 200
        deployment_id = response.json()["deployment_id"]

        # Pause
        response = await client.post(
            f"/v1/deployments/{deployment_id}/pause",
            headers=auth_headers,
        )
        assert response.status_code == 200

        # Verify paused
        response = await client.get(
            f"/v1/deployments/{deployment_id}",
            headers=auth_headers,
        )
        assert response.json()["status"] == "paused"

        # Resume
        response = await client.post(
            f"/v1/deployments/{deployment_id}/resume",
            headers=auth_headers,
        )
        assert response.status_code == 200

        # Verify active
        response = await client.get(
            f"/v1/deployments/{deployment_id}",
            headers=auth_headers,
        )
        assert response.json()["status"] == "active"
