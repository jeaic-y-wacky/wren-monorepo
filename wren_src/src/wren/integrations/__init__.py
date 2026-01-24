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
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from ..core.registry import registry
from .base import BaseIntegration

if TYPE_CHECKING:
    from typing import Type

# Registry of available integrations
_INTEGRATION_REGISTRY: dict[str, Type[BaseIntegration]] = {}


def register_integration(name: str):
    """Decorator to register an integration class."""
    def decorator(cls: Type[BaseIntegration]) -> Type[BaseIntegration]:
        _INTEGRATION_REGISTRY[name] = cls
        return cls
    return decorator


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
    """

    def __getattr__(self, name: str) -> IntegrationInitializer:
        """Return an initializer for the requested integration."""
        return IntegrationInitializer(name)


# Global integration manager instance
integrations = IntegrationManager()

# Import integrations to register them
from . import cron  # noqa: E402, F401
from . import messaging  # noqa: E402, F401
from . import gmail  # noqa: E402, F401
from . import slack  # noqa: E402, F401

__all__ = [
    "integrations",
    "BaseIntegration",
    "register_integration",
]
