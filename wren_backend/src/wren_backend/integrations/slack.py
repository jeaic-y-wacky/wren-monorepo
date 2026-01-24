"""Slack integration definition.

Defines credential requirements and OAuth configuration for Slack.
The SDK's slack integration will receive these credentials as environment
variables at runtime.

Environment variables injected:
- SLACK_ACCESS_TOKEN: OAuth access token (bot token)
- SLACK_REFRESH_TOKEN: OAuth refresh token (if using token rotation)
"""

import structlog

from .registry import (
    CredentialSpec,
    CredentialType,
    IntegrationSpec,
    register_integration,
)

logger = structlog.get_logger()


async def validate_slack_credentials(credentials: dict) -> bool:
    """Validate that Slack credentials are still valid.

    Returns True if credentials are valid and not expired.
    """
    # TODO: Implement actual validation (call Slack auth.test API)
    logger.info("slack_validate_credentials", status="stub")
    return "access_token" in credentials


async def refresh_slack_credentials(credentials: dict) -> dict:
    """Refresh Slack OAuth token if using token rotation.

    Returns updated credentials dict with new access_token.
    """
    # TODO: Implement actual refresh for token rotation
    logger.info("slack_refresh_token", status="stub")
    return credentials


# Register Slack integration
SLACK_SPEC = register_integration(
    IntegrationSpec(
        name="slack",
        display_name="Slack",
        description="Send messages and interact with Slack workspaces",
        oauth_provider="slack",
        oauth_scopes=[
            "chat:write",
            "channels:read",
            "channels:history",
            "users:read",
        ],
        credentials=[
            CredentialSpec(
                key="access_token",
                type=CredentialType.OAUTH2,
                description="Slack bot OAuth access token",
                env_var="SLACK_ACCESS_TOKEN",
                required=True,
                oauth_scopes=["chat:write", "channels:read"],
                refresh_key="refresh_token",
                refresh_env_var="SLACK_REFRESH_TOKEN",
            ),
        ],
        setup_url_template="https://wrens.ie/integrations/slack/setup?user={user_id}",
        docs_url="https://docs.wrens.ie/integrations/slack",
        validate_credentials=validate_slack_credentials,
        refresh_credentials=refresh_slack_credentials,
    )
)


# Backwards compatibility - keep class for any existing code
class SlackIntegration:
    """Slack integration handler (legacy interface).

    Prefer using SLACK_SPEC and the registry directly.
    """

    name = SLACK_SPEC.name
    display_name = SLACK_SPEC.display_name
    scopes = SLACK_SPEC.oauth_scopes

    @staticmethod
    async def validate_credentials(credentials: dict) -> bool:
        return await validate_slack_credentials(credentials)

    @staticmethod
    async def refresh_token(credentials: dict) -> dict:
        return await refresh_slack_credentials(credentials)

    @staticmethod
    def get_setup_url(user_id: str) -> str:
        return SLACK_SPEC.get_setup_url(user_id) or ""

    @staticmethod
    def get_docs_url() -> str:
        return SLACK_SPEC.docs_url or ""
