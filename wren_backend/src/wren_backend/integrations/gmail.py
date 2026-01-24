"""Gmail integration definition.

Defines credential requirements and OAuth configuration for Gmail.
The SDK's gmail integration will receive these credentials as environment
variables at runtime.

Environment variables injected:
- GMAIL_ACCESS_TOKEN: OAuth access token
- GMAIL_REFRESH_TOKEN: OAuth refresh token (for token refresh)
"""

import structlog

from .registry import (
    CredentialSpec,
    CredentialType,
    IntegrationSpec,
    register_integration,
)

logger = structlog.get_logger()


async def validate_gmail_credentials(credentials: dict) -> bool:
    """Validate that Gmail credentials are still valid.

    Returns True if credentials are valid and not expired.
    """
    # TODO: Implement actual validation (call Gmail API to verify token)
    logger.info("gmail_validate_credentials", status="stub")
    return "access_token" in credentials


async def refresh_gmail_credentials(credentials: dict) -> dict:
    """Refresh Gmail OAuth token if expired.

    Returns updated credentials dict with new access_token.
    """
    # TODO: Implement actual refresh using refresh_token
    logger.info("gmail_refresh_token", status="stub")
    return credentials


# Register Gmail integration
GMAIL_SPEC = register_integration(
    IntegrationSpec(
        name="gmail",
        display_name="Gmail",
        description="Read and send emails via Gmail API",
        oauth_provider="google",
        oauth_scopes=[
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/gmail.labels",
        ],
        credentials=[
            CredentialSpec(
                key="access_token",
                type=CredentialType.OAUTH2,
                description="Gmail OAuth access token",
                env_var="GMAIL_ACCESS_TOKEN",
                required=True,
                oauth_scopes=[
                    "https://www.googleapis.com/auth/gmail.readonly",
                    "https://www.googleapis.com/auth/gmail.send",
                ],
                refresh_key="refresh_token",
                refresh_env_var="GMAIL_REFRESH_TOKEN",
            ),
        ],
        setup_url_template="https://wrens.ie/integrations/gmail/setup?user={user_id}",
        docs_url="https://docs.wrens.ie/integrations/gmail",
        validate_credentials=validate_gmail_credentials,
        refresh_credentials=refresh_gmail_credentials,
    )
)


# Backwards compatibility - keep class for any existing code
class GmailIntegration:
    """Gmail integration handler (legacy interface).

    Prefer using GMAIL_SPEC and the registry directly.
    """

    name = GMAIL_SPEC.name
    display_name = GMAIL_SPEC.display_name
    scopes = GMAIL_SPEC.oauth_scopes

    @staticmethod
    async def validate_credentials(credentials: dict) -> bool:
        return await validate_gmail_credentials(credentials)

    @staticmethod
    async def refresh_token(credentials: dict) -> dict:
        return await refresh_gmail_credentials(credentials)

    @staticmethod
    def get_setup_url(user_id: str) -> str:
        return GMAIL_SPEC.get_setup_url(user_id) or ""

    @staticmethod
    def get_docs_url() -> str:
        return GMAIL_SPEC.docs_url or ""
