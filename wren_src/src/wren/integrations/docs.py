"""
Integration Documentation System - Self-documenting integration definitions.

Provides structured dataclasses for integration documentation that can be:
- Rendered to markdown for system prompts
- Queried dynamically via agent tools
- Validated for completeness

Each integration defines a DOCS class attribute with its documentation.

NOTE: Credential requirements (OAuth scopes, setup URLs, env var mappings) are
defined in the BACKEND, not here. The SDK docs just indicate what TYPE of auth
is needed so the agent knows to warn users about setup requirements.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


class AuthType(Enum):
    """Type of authentication required by an integration.

    This is a simplified indicator for the agent. The detailed credential
    specifications (OAuth scopes, env var names, etc.) are defined in the
    backend's integration registry.
    """

    NONE = "none"  # No auth needed (e.g., cron, messaging mock)
    OAUTH = "oauth"  # Requires OAuth flow (e.g., gmail, slack)
    API_KEY = "api_key"  # Requires API key
    TOKEN = "token"  # Requires bearer token


@dataclass
class ParamDoc:
    """Documentation for a method parameter or init parameter."""

    name: str
    type: str
    description: str
    required: bool = True
    default: str | None = None

    def render_markdown(self) -> str:
        """Render parameter as markdown list item."""
        req = "" if self.required else " (optional)"
        default = f", default: `{self.default}`" if self.default else ""
        return f"  - `{self.name}` ({self.type}{req}): {self.description}{default}"


@dataclass
class MethodDoc:
    """Documentation for an integration method."""

    name: str
    description: str
    params: list[ParamDoc] = field(default_factory=list)
    returns: str = "None"
    example: str | None = None

    def render_markdown(self) -> str:
        """Render method as markdown section."""
        lines = [f"#### `{self.name}()`", "", self.description, ""]

        if self.params:
            lines.append("**Parameters:**")
            for param in self.params:
                lines.append(param.render_markdown())
            lines.append("")

        lines.append(f"**Returns:** {self.returns}")

        if self.example:
            lines.extend(["", "**Example:**", "```python", self.example, "```"])

        return "\n".join(lines)


@dataclass
class IntegrationDocs:
    """Complete documentation for an integration.

    NOTE: Detailed credential specs (OAuth scopes, setup URLs, env var mappings)
    are defined in the backend. The SDK only indicates the auth TYPE so the
    agent knows to warn users about setup requirements.
    """

    name: str
    description: str
    methods: list[MethodDoc] = field(default_factory=list)
    init_params: list[ParamDoc] = field(default_factory=list)
    example: str | None = None
    auth_type: AuthType = AuthType.NONE  # What kind of auth is needed

    def render_markdown(self) -> str:
        """Render complete integration docs as markdown."""
        lines = [f"### {self.name}", "", self.description, ""]

        if self.auth_type != AuthType.NONE:
            auth_desc = {
                AuthType.OAUTH: "OAuth authentication (configure in platform)",
                AuthType.API_KEY: "API key (configure in platform)",
                AuthType.TOKEN: "Access token (configure in platform)",
            }
            lines.append(f"**Requires:** {auth_desc.get(self.auth_type, 'Authentication')}")
            lines.append("")

        if self.init_params:
            lines.append("**Init Parameters:**")
            for param in self.init_params:
                lines.append(param.render_markdown())
            lines.append("")

        if self.example:
            lines.extend(["**Quick Example:**", "```python", self.example, "```", ""])

        if self.methods:
            lines.append("**Methods:**")
            lines.append("")
            for method in self.methods:
                lines.append(method.render_markdown())
                lines.append("")

        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "methods": [
                {
                    "name": m.name,
                    "description": m.description,
                    "params": [
                        {
                            "name": p.name,
                            "type": p.type,
                            "description": p.description,
                            "required": p.required,
                            "default": p.default,
                        }
                        for p in m.params
                    ],
                    "returns": m.returns,
                    "example": m.example,
                }
                for m in self.methods
            ],
            "init_params": [
                {
                    "name": p.name,
                    "type": p.type,
                    "description": p.description,
                    "required": p.required,
                    "default": p.default,
                }
                for p in self.init_params
            ],
            "example": self.example,
            "auth_type": self.auth_type.value,
        }


def render_all_docs(docs: Sequence[IntegrationDocs]) -> str:
    """
    Render multiple integration docs into a single markdown document.

    Args:
        docs: Sequence of IntegrationDocs to render

    Returns:
        Complete markdown string with all integrations documented
    """
    lines = [
        "# Wren Integrations Reference",
        "",
        "Available integrations for use in Wren scripts.",
        "",
    ]

    for doc in docs:
        lines.append(doc.render_markdown())
        lines.append("---")
        lines.append("")

    return "\n".join(lines)
