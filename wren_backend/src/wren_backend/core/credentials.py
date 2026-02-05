"""Credential storage and management using Supabase.

This module handles:
- Storing user credentials for integrations in Supabase
- Validating credentials exist for script deployment
- Converting credentials to environment variables for script execution

The credential -> env var mapping is defined in the integration registry.
"""

import structlog
from supabase import Client

from wren_backend.core.supabase_client import get_supabase_admin_client, get_supabase_client
from wren_backend.integrations import get_env_for_credentials, get_integration

logger = structlog.get_logger()


class CredentialStore:
    """Manages credentials for integrations using Supabase.

    Uses the credentials table in Supabase with RLS policies.
    The admin client is used for server-side operations.
    """

    def __init__(self):
        self._client: Client | None = None
        self._admin_client: Client | None = None

    async def connect(self) -> None:
        """Initialize the Supabase client connection."""
        self._client = get_supabase_client()
        self._admin_client = get_supabase_admin_client()
        logger.info("credential_store_connected", has_admin=self._admin_client is not None)

    def _get_client(self, use_admin: bool = False) -> Client:
        """Get the appropriate Supabase client."""
        if use_admin and self._admin_client:
            return self._admin_client
        if not self._client:
            raise RuntimeError("CredentialStore not connected")
        return self._client

    async def get_credentials(
        self, user_id: str, integration: str
    ) -> dict[str, str] | None:
        """Get credentials for a user's integration.

        Args:
            user_id: The user ID (UUID)
            integration: Integration name (e.g., "gmail", "slack")

        Returns:
            Credentials dict or None if not configured
        """
        client = self._get_client(use_admin=True)
        result = (
            client.table("credentials")
            .select("credentials")
            .eq("user_id", user_id)
            .eq("integration", integration)
            .execute()
        )

        if not result.data:
            return None

        return result.data[0]["credentials"]

    async def set_credentials(
        self, user_id: str, integration: str, credentials: dict[str, str]
    ) -> None:
        """Store credentials for a user's integration.

        Args:
            user_id: The user ID (UUID)
            integration: Integration name
            credentials: Credentials to store (e.g., {"access_token": "...", "refresh_token": "..."})
        """
        client = self._get_client(use_admin=True)

        # Use upsert to handle both insert and update
        client.table("credentials").upsert(
            {
                "user_id": user_id,
                "integration": integration,
                "credentials": credentials,
            },
            on_conflict="user_id,integration",
        ).execute()

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

        creds = await self.get_credentials(user_id, integration)
        if not creds:
            return False

        # If integration has required credentials, verify they're all present
        if spec:
            required_keys = spec.get_required_credential_keys()
            return all(k in creds for k in required_keys)

        return True

    async def delete_credentials(self, user_id: str, integration: str) -> None:
        """Delete credentials for a user's integration."""
        client = self._get_client(use_admin=True)
        client.table("credentials").delete().eq("user_id", user_id).eq(
            "integration", integration
        ).execute()

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
            user_id: The user ID (UUID)
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
            user_id: The user ID (UUID)
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
