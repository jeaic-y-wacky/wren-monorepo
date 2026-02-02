"""Integration definitions and registry.

This module provides:
- IntegrationSpec definitions for all supported integrations
- Registry functions to query integration requirements
- Credential-to-environment-variable mapping

The integration name is the contract between SDK and backend:
- SDK registers names in script metadata: {"integrations": ["gmail", "slack"]}
- Backend uses this registry to validate and inject credentials
"""

from .registry import (
    CredentialSpec,
    CredentialType,
    IntegrationSpec,
    get_all_integrations,
    get_env_for_credentials,
    get_integration,
    list_integrations,
    register_integration,
)

# Import integrations to register them
from .gmail import GMAIL_SPEC, GmailIntegration
from .slack import SLACK_SPEC, SlackIntegration

# Register additional integrations that don't have their own modules yet

# Messaging - generic messaging (no credentials needed, it's a mock)
MESSAGING_SPEC = register_integration(
    IntegrationSpec(
        name="messaging",
        display_name="Messaging",
        description="Generic messaging integration for prototyping",
        credentials=[],  # No credentials - it's a mock
        docs_url="https://docs.wrens.ie/integrations/messaging",
    )
)

# Cron - no credentials needed, platform handles scheduling
CRON_SPEC = register_integration(
    IntegrationSpec(
        name="cron",
        display_name="Cron",
        description="Schedule tasks using cron expressions",
        credentials=[],  # No credentials - platform handles it
        docs_url="https://docs.wrens.ie/integrations/cron",
    )
)

# Discord - bot token authentication
DISCORD_SPEC = register_integration(
    IntegrationSpec(
        name="discord",
        display_name="Discord",
        description="Send messages and interact with Discord servers",
        credentials=[
            CredentialSpec(
                key="bot_token",
                type=CredentialType.TOKEN,
                description="Discord bot token",
                env_var="DISCORD_BOT_TOKEN",
                required=True,
            ),
        ],
        setup_url_template="https://wrens.ie/integrations/discord/setup?user={user_id}",
        docs_url="https://docs.wrens.ie/integrations/discord",
    )
)

__all__ = [
    # Registry types
    "CredentialSpec",
    "CredentialType",
    "IntegrationSpec",
    # Registry functions
    "register_integration",
    "get_integration",
    "list_integrations",
    "get_all_integrations",
    "get_env_for_credentials",
    # Integration specs
    "GMAIL_SPEC",
    "SLACK_SPEC",
    "MESSAGING_SPEC",
    "CRON_SPEC",
    "DISCORD_SPEC",
    # Legacy classes (for backwards compatibility)
    "GmailIntegration",
    "SlackIntegration",
]
