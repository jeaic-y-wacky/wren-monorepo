"""Tests for credentials API endpoints."""

import pytest


@pytest.mark.asyncio
async def test_set_credentials(client, auth_headers):
    """Test storing credentials for an integration."""
    response = await client.put(
        "/v1/credentials/slack",
        json={"credentials": {"token": "xoxb-test", "default_channel": "#general"}},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["integration"] == "slack"
    assert data["configured"] is True
    assert sorted(data["credential_keys"]) == ["default_channel", "token"]


@pytest.mark.asyncio
async def test_get_credentials_status_not_configured(client, auth_headers):
    """Test checking status of an unconfigured integration."""
    response = await client.get(
        "/v1/credentials/gmail",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["integration"] == "gmail"
    assert data["configured"] is False
    assert data["credential_keys"] == []


@pytest.mark.asyncio
async def test_get_credentials_status_configured(client, auth_headers):
    """Test checking status after storing credentials."""
    # Store first
    await client.put(
        "/v1/credentials/discord",
        json={"credentials": {"token": "bot-token-123"}},
        headers=auth_headers,
    )

    # Check status
    response = await client.get(
        "/v1/credentials/discord",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["configured"] is True
    assert data["credential_keys"] == ["token"]


@pytest.mark.asyncio
async def test_delete_credentials(client, auth_headers):
    """Test deleting credentials for an integration."""
    # Store first
    await client.put(
        "/v1/credentials/slack",
        json={"credentials": {"token": "xoxb-test"}},
        headers=auth_headers,
    )

    # Delete
    response = await client.delete(
        "/v1/credentials/slack",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["configured"] is False

    # Verify gone
    response = await client.get(
        "/v1/credentials/slack",
        headers=auth_headers,
    )
    assert response.json()["configured"] is False


@pytest.mark.asyncio
async def test_credentials_require_auth(client):
    """Test that credentials endpoints require authentication."""
    response = await client.get("/v1/credentials/slack")
    assert response.status_code == 401
