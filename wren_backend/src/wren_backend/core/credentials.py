"""Credential storage and management.

This module handles:
- Storing user credentials for integrations
- Validating credentials exist for script deployment
- Converting credentials to environment variables for script execution

The credential -> env var mapping is defined in the integration registry.
"""

import structlog

from ..integrations import get_env_for_credentials, get_integration

logger = structlog.get_logger()


class CredentialStore:
    """Manages credentials for integrations.

    Phase 1: In-memory storage
    Phase 3 will add:
    - Encrypted storage (SQLite + encryption or Vault)
    - OAuth token management with refresh
    - Audit logging
    """

    def __init__(self):
        # In-memory store for Phase 1
        # Key format: "{user_id}:{integration}"
        # Value: dict of credential key -> value
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
            credentials: Credentials to store (e.g., {"access_token": "...", "refresh_token": "..."})
        """
        key = f"{user_id}:{integration}"
        self._credentials[key] = credentials
        logger.info(
            "credentials_stored",
            user_id=user_id,
            integration=integration,
            credential_keys=list(credentials.keys()),
        )

    async def has_credentials(self, user_id: str, integration: str) -> bool:
        """Check if credentials exist for a user's integration.

        For integrations that don't require credentials (like cron, messaging),
        this always returns True.
        """
        # Check if integration requires credentials
        spec = get_integration(integration)
        if spec and not spec.credentials:
            # Integration doesn't require credentials
            return True

        key = f"{user_id}:{integration}"
        has_creds = key in self._credentials

        # If integration has required credentials, verify they're all present
        if has_creds and spec:
            stored = self._credentials[key]
            required_keys = spec.get_required_credential_keys()
            has_creds = all(k in stored for k in required_keys)

        return has_creds

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

        Converts stored credentials to environment variables using
        the mapping defined in each integration's spec.

        Args:
            user_id: The user ID
            integrations: List of integrations the script uses

        Returns:
            Dict of environment variables to inject into the executor

        Example:
            For gmail with stored {"access_token": "abc", "refresh_token": "xyz"}
            Returns: {"GMAIL_ACCESS_TOKEN": "abc", "GMAIL_REFRESH_TOKEN": "xyz"}
        """
        env = {}
        for integration in integrations:
            creds = await self.get_credentials(user_id, integration)
            if creds:
                # Use registry's mapping to convert to env vars
                integration_env = get_env_for_credentials(integration, creds)
                env.update(integration_env)
                logger.debug(
                    "credentials_injected",
                    integration=integration,
                    env_vars=list(integration_env.keys()),
                )
        return env

    async def validate_for_deployment(
        self, user_id: str, integrations: list[str]
    ) -> list[dict]:
        """Validate credentials for script deployment.

        Returns list of missing/invalid credential errors.

        Args:
            user_id: The user ID
            integrations: List of integrations the script uses

        Returns:
            List of error dicts, empty if all credentials are valid
        """
        errors = []
        for integration in integrations:
            if not await self.has_credentials(user_id, integration):
                spec = get_integration(integration)
                error = {
                    "integration": integration,
                    "code": "CREDENTIALS_MISSING",
                    "message": f"{spec.display_name if spec else integration} credentials not configured",
                }
                if spec:
                    setup_url = spec.get_setup_url(user_id)
                    if setup_url:
                        error["setup_url"] = setup_url
                    if spec.docs_url:
                        error["docs_url"] = spec.docs_url
                errors.append(error)
        return errors
