"""
Integration Registry - Central registry for integration definitions.

This module defines the contract between SDK and backend for credentials:
- What credentials each integration requires
- How credentials map to environment variables
- OAuth scopes and setup URLs

The SDK registers integration *names* in script metadata.
The backend uses this registry to:
1. Validate credentials exist at deploy time
2. Inject credentials as env vars at runtime
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


class CredentialType(Enum):
    """Type of credential required by an integration."""

    OAUTH2 = "oauth2"  # Requires OAuth 2.0 flow (Google, Slack, etc.)
    API_KEY = "api_key"  # Simple API key
    TOKEN = "token"  # Bearer token or similar
    BASIC_AUTH = "basic_auth"  # Username/password pair
    CUSTOM = "custom"  # Integration-specific credential format


@dataclass
class CredentialSpec:
    """Specification for a credential required by an integration.

    Defines what credential is needed and how it maps to environment variables.
    """

    key: str  # Credential key in storage (e.g., "access_token", "api_key")
    type: CredentialType
    description: str  # Human-readable description
    env_var: str  # Environment variable name for injection (e.g., "GMAIL_ACCESS_TOKEN")
    required: bool = True  # Is this credential required?

    # OAuth-specific fields
    oauth_scopes: list[str] = field(default_factory=list)

    # For refresh tokens
    refresh_key: str | None = None  # Key for refresh token if applicable
    refresh_env_var: str | None = None  # Env var for refresh token


@dataclass
class IntegrationSpec:
    """Complete specification for an integration.

    This is the authoritative definition of what an integration needs.
    The SDK just registers the integration name; the backend uses this
    spec to handle credentials.
    """

    name: str  # Integration identifier (e.g., "gmail", "slack")
    display_name: str  # Human-readable name (e.g., "Gmail", "Slack")
    description: str  # What this integration does

    # Credential requirements
    credentials: list[CredentialSpec] = field(default_factory=list)

    # OAuth configuration (if applicable)
    oauth_provider: str | None = None  # "google", "slack", "microsoft", etc.
    oauth_scopes: list[str] = field(default_factory=list)  # Combined scopes

    # URLs
    setup_url_template: str | None = None  # URL template with {user_id} placeholder
    docs_url: str | None = None

    # Validation and refresh functions (set by integration modules)
    validate_credentials: Callable | None = None
    refresh_credentials: Callable | None = None

    def get_setup_url(self, user_id: str) -> str | None:
        """Get the setup URL for a specific user."""
        if self.setup_url_template:
            return self.setup_url_template.format(user_id=user_id)
        return None

    def get_env_mapping(self) -> dict[str, str]:
        """Get mapping from credential keys to environment variable names.

        Returns:
            Dict mapping credential key -> env var name
            e.g., {"access_token": "GMAIL_ACCESS_TOKEN", "refresh_token": "GMAIL_REFRESH_TOKEN"}
        """
        mapping = {}
        for cred in self.credentials:
            mapping[cred.key] = cred.env_var
            if cred.refresh_key and cred.refresh_env_var:
                mapping[cred.refresh_key] = cred.refresh_env_var
        return mapping

    def get_required_credential_keys(self) -> list[str]:
        """Get list of required credential keys."""
        return [c.key for c in self.credentials if c.required]


# =============================================================================
# Global Registry
# =============================================================================

_INTEGRATION_REGISTRY: dict[str, IntegrationSpec] = {}


def register_integration(spec: IntegrationSpec) -> IntegrationSpec:
    """Register an integration specification.

    Args:
        spec: The integration specification to register

    Returns:
        The registered spec (for decorator chaining)
    """
    _INTEGRATION_REGISTRY[spec.name] = spec
    return spec


def get_integration(name: str) -> IntegrationSpec | None:
    """Get an integration specification by name.

    Args:
        name: Integration name (e.g., "gmail")

    Returns:
        IntegrationSpec or None if not found
    """
    return _INTEGRATION_REGISTRY.get(name)


def list_integrations() -> list[str]:
    """List all registered integration names.

    Returns:
        Sorted list of integration names
    """
    return sorted(_INTEGRATION_REGISTRY.keys())


def get_all_integrations() -> dict[str, IntegrationSpec]:
    """Get all registered integration specifications.

    Returns:
        Dict mapping name -> IntegrationSpec
    """
    return dict(_INTEGRATION_REGISTRY)


def get_env_for_credentials(
    integration_name: str, credentials: dict[str, str]
) -> dict[str, str]:
    """Convert stored credentials to environment variables.

    Uses the integration's credential spec to map credential keys
    to the correct environment variable names.

    Args:
        integration_name: Name of the integration
        credentials: Dict of stored credentials (key -> value)

    Returns:
        Dict of environment variables (env_var_name -> value)
    """
    spec = get_integration(integration_name)
    if not spec:
        # Fallback: use simple PREFIX_KEY format
        prefix = integration_name.upper()
        return {f"{prefix}_{k.upper()}": v for k, v in credentials.items()}

    env_mapping = spec.get_env_mapping()
    env_vars = {}

    for cred_key, value in credentials.items():
        if cred_key in env_mapping:
            env_vars[env_mapping[cred_key]] = value
        else:
            # Fallback for unmapped keys
            prefix = integration_name.upper()
            env_vars[f"{prefix}_{cred_key.upper()}"] = value

    return env_vars
