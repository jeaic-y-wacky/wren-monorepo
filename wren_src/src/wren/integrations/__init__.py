"""
Wren Integrations - Module-level initialization pattern.

Provides lazy-loading integration manager that records to registry
during init() calls.

Usage:
    # At module level (runs at import)
    cron = wren.integrations.cron.init()
    messaging = wren.integrations.messaging.init(default_channel="#alerts")

    # Later in functions
    messaging.post("Hello!")  # Connects lazily here

    # Documentation access
    wren.integrations.list_all()           # ["cron", "gmail", ...]
    wren.integrations.get_docs("gmail") # IntegrationDocs for gmail
    wren.integrations.render_docs()     # Markdown of all integration docs
"""

from __future__ import annotations

from typing import Any

from ..core.registry import registry
from .base import BaseIntegration
from .docs import AuthType, IntegrationDocs, render_all_docs

# Registry of available integrations
_INTEGRATION_REGISTRY: dict[str, type[BaseIntegration]] = {}

# Registry of integration documentation
_DOCS_REGISTRY: dict[str, IntegrationDocs] = {}


def register_integration(name: str):
    """Decorator to register an integration class and its documentation."""

    def decorator(cls: type[BaseIntegration]) -> type[BaseIntegration]:
        _INTEGRATION_REGISTRY[name] = cls
        # Also register DOCS if the class has them
        if hasattr(cls, "DOCS") and cls.DOCS is not None:
            _DOCS_REGISTRY[name] = cls.DOCS
        return cls

    return decorator


def list_integrations() -> list[str]:
    """
    List all registered integration names.

    Returns:
        List of integration names (e.g., ["gmail", "slack", "cron", ...])
    """
    return sorted(_INTEGRATION_REGISTRY.keys())


def get_integration_docs(name: str) -> IntegrationDocs | None:
    """
    Get documentation for a specific integration.

    Args:
        name: Integration name (e.g., "gmail")

    Returns:
        IntegrationDocs if available, None otherwise
    """
    return _DOCS_REGISTRY.get(name)


def render_integration_docs(names: list[str] | None = None) -> str:
    """
    Render integration documentation as markdown.

    Args:
        names: Optional list of integration names to include.
               If None, includes all integrations with docs.

    Returns:
        Markdown string with integration documentation
    """
    if names is None:
        docs = list(_DOCS_REGISTRY.values())
    else:
        docs = [_DOCS_REGISTRY[n] for n in names if n in _DOCS_REGISTRY]

    return render_all_docs(docs)


class IntegrationInitializer:
    """
    Proxy for initializing a specific integration.

    Returned when accessing wren.integrations.<name>.
    Call .init() to register and get the lazy client.
    """

    def __init__(self, name: str) -> None:
        self._name = name

    def init(self, **config: Any) -> BaseIntegration:
        """
        Initialize the integration.

        1. Records integration name to registry (for metadata extraction)
        2. Returns a lazy client that connects on first method call

        Args:
            **config: Integration-specific configuration

        Returns:
            Integration client instance
        """
        # Record to registry for metadata extraction
        registry.register_integration(self._name)

        # Get the integration class
        if self._name not in _INTEGRATION_REGISTRY:
            raise ValueError(
                f"Unknown integration: {self._name!r}. "
                f"Available: {list(_INTEGRATION_REGISTRY.keys())}"
            )

        integration_cls = _INTEGRATION_REGISTRY[self._name]
        return integration_cls(self._name, config)

    def __getattr__(self, name: str) -> Any:
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        raise AttributeError(
            f"Integration '{self._name}' is not initialized. "
            f"Call wren.integrations.{self._name}.init() before using '{name}'."
        )


class IntegrationManager:
    """
    Lazy-loading manager for integrations.

    Access as wren.integrations.<name> to get an IntegrationInitializer.

    Example:
        gmail = wren.integrations.gmail.init()
        slack = wren.integrations.slack.init(token="...")

    Documentation access:
        wren.integrations.list_all()            # List all integration names
        wren.integrations.get_docs("gmail") # Get docs for one integration
        wren.integrations.render_docs()     # Render all docs as markdown
    """

    def list_all(self) -> list[str]:
        """List all registered integration names."""
        return list_integrations()

    def get_docs(self, name: str) -> IntegrationDocs | None:
        """Get documentation for a specific integration."""
        return get_integration_docs(name)

    def render_docs(self, names: list[str] | None = None) -> str:
        """Render integration documentation as markdown."""
        return render_integration_docs(names)

    def __getattr__(self, name: str) -> IntegrationInitializer:
        """Return an initializer for the requested integration."""
        return IntegrationInitializer(name)


# Global integration manager instance
integrations = IntegrationManager()

# Import integrations to register them (side effect: registers them)
from . import (  # noqa: E402, F401
    cron,
    gmail,
    messaging,
    slack,
)

__all__ = [
    "integrations",
    "BaseIntegration",
    "AuthType",
    "IntegrationDocs",
    "register_integration",
    "list_integrations",
    "get_integration_docs",
    "render_integration_docs",
]
