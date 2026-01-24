"""Slack integration (stub for Phase 1).

Phase 3 will add:
- OAuth 2.0 flow
- Token management
- Slack API wrapper
"""

import structlog

logger = structlog.get_logger()


class SlackIntegration:
    """Slack integration handler.

    This is a stub for Phase 1.
    Phase 3 will implement full OAuth flow and Slack operations.
    """

    name = "slack"
    display_name = "Slack"
    scopes = [
        "chat:write",
        "channels:read",
        "users:read",
    ]

    @staticmethod
    async def validate_credentials(credentials: dict) -> bool:
        """Validate that credentials are still valid.

        Returns True if credentials are valid and not expired.
        """
        # Stub - always return True for Phase 1
        logger.info("slack_validate_credentials", status="stub")
        return True

    @staticmethod
    async def refresh_token(credentials: dict) -> dict:
        """Refresh OAuth token if expired.

        Returns updated credentials dict.
        """
        # Stub - return credentials unchanged for Phase 1
        logger.info("slack_refresh_token", status="stub")
        return credentials

    @staticmethod
    def get_setup_url(user_id: str) -> str:
        """Get the OAuth setup URL for this integration."""
        return f"https://wrens.ie/integrations/slack/setup?user={user_id}"

    @staticmethod
    def get_docs_url() -> str:
        """Get the documentation URL for this integration."""
        return "https://docs.wrens.ie/integrations/slack"
