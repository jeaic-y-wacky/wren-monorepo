"""
Integration Documentation Tools - Dynamic loading of integration docs.

Provides tools for the agent to discover and query integration documentation
on demand, reducing token usage for large integration sets.
"""

from __future__ import annotations

import json

from agents import function_tool


@function_tool
def list_integrations() -> str:
    """List all available Wren SDK integrations.

    Use this to discover what integrations are available before looking up
    specific documentation.

    Returns:
        JSON list of integration names, e.g., ["gmail", "slack", "cron", ...]
    """
    try:
        from wren.integrations import list_integrations as wren_list

        integrations = wren_list()
        return json.dumps({"integrations": integrations}, indent=2)
    except ImportError:
        # Fallback if wren is not installed
        return json.dumps(
            {
                "integrations": ["gmail", "slack", "messaging", "cron"],
                "note": "Wren SDK not available, using defaults",
            },
            indent=2,
        )


@function_tool
def get_integration_docs(name: str) -> str:
    """Get detailed documentation for a specific integration.

    Use this after list_integrations() to get the full documentation for
    an integration you need to use in a script.

    Args:
        name: Integration name (e.g., "gmail", "slack")

    Returns:
        JSON documentation including methods, parameters, and examples
    """
    try:
        from wren.integrations import get_integration_docs as wren_get_docs

        docs = wren_get_docs(name)
        if docs is None:
            return json.dumps(
                {
                    "error": f"No documentation found for integration: {name}",
                    "available": list_integrations(),
                },
                indent=2,
            )
        return json.dumps(docs.to_dict(), indent=2)
    except ImportError:
        return json.dumps(
            {
                "error": "Wren SDK not available",
                "hint": "Install wren SDK to get integration documentation",
            },
            indent=2,
        )
