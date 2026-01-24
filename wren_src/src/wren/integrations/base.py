"""
Base Integration Class - Lazy connection pattern.

Integrations use lazy connection - init() records to registry and returns
a client, but actual connection happens only when methods are called.

This allows metadata extraction (importing scripts) without triggering
real connections or requiring credentials.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from .docs import IntegrationDocs


class BaseIntegration(ABC):
    """
    Base class for all integrations with lazy connection.

    Subclasses should:
    1. Implement _connect() to establish the actual connection
    2. Call _ensure_connected() before any operation requiring connection
    3. Define DOCS class attribute for self-documentation
    """

    # Documentation for this integration (set in subclasses)
    DOCS: ClassVar[IntegrationDocs | None] = None

    def __init__(self, name: str, config: dict[str, Any] | None = None) -> None:
        self._name = name
        self._config = config or {}
        self._connected = False
        self._client: Any = None

    @property
    def name(self) -> str:
        """Integration name (e.g., 'gmail', 'slack')."""
        return self._name

    @property
    def config(self) -> dict[str, Any]:
        """Integration configuration."""
        return self._config

    @property
    def is_connected(self) -> bool:
        """Whether the integration has established a connection."""
        return self._connected

    @abstractmethod
    def _connect(self) -> None:
        """
        Establish the actual connection.

        Override this in subclasses to connect to the service.
        Called lazily on first method use.
        """
        pass

    def _ensure_connected(self) -> None:
        """Connect if not already connected."""
        if not self._connected:
            self._connect()
            self._connected = True

    def disconnect(self) -> None:
        """Disconnect and reset state."""
        self._connected = False
        self._client = None
