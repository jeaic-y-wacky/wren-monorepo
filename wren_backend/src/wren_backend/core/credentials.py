"""Credential storage and management (stub for Phase 1)."""

import structlog

logger = structlog.get_logger()


class CredentialStore:
    """Manages credentials for integrations.

    This is a stub implementation for Phase 1.
    Phase 3 will add:
    - Encrypted storage
    - OAuth token management
    - Secret injection to executor
    """

    def __init__(self):
        # In-memory store for Phase 1
        self._credentials: dict[str, dict[str, str]] = {}

    async def get_credentials(
        self, user_id: str, integration: str
    ) -> dict[str, str] | None:
        """Get credentials for a user's integration.

        Args:
            user_id: The user ID
            integration: Integration name (e.g., "gmail", "slack")

        Returns:
            Credentials dict or None if not configured
        """
        key = f"{user_id}:{integration}"
        return self._credentials.get(key)

    async def set_credentials(
        self, user_id: str, integration: str, credentials: dict[str, str]
    ) -> None:
        """Store credentials for a user's integration.

        Args:
            user_id: The user ID
            integration: Integration name
            credentials: Credentials to store
        """
        key = f"{user_id}:{integration}"
        self._credentials[key] = credentials
        logger.info(
            "credentials_stored",
            user_id=user_id,
            integration=integration,
        )

    async def has_credentials(self, user_id: str, integration: str) -> bool:
        """Check if credentials exist for a user's integration."""
        key = f"{user_id}:{integration}"
        return key in self._credentials

    async def delete_credentials(self, user_id: str, integration: str) -> None:
        """Delete credentials for a user's integration."""
        key = f"{user_id}:{integration}"
        if key in self._credentials:
            del self._credentials[key]
            logger.info(
                "credentials_deleted",
                user_id=user_id,
                integration=integration,
            )

    async def get_env_for_execution(
        self, user_id: str, integrations: list[str]
    ) -> dict[str, str]:
        """Get environment variables for script execution.

        Converts stored credentials to environment variables
        that can be injected into the executor.

        Args:
            user_id: The user ID
            integrations: List of integrations the script uses

        Returns:
            Dict of environment variables
        """
        env = {}
        for integration in integrations:
            creds = await self.get_credentials(user_id, integration)
            if creds:
                # Convert to env vars with prefix
                prefix = integration.upper()
                for key, value in creds.items():
                    env_key = f"{prefix}_{key.upper()}"
                    env[env_key] = value
        return env
