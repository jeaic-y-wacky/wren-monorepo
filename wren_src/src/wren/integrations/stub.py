"""
Stub Integration - Lazy proxy for unimplemented integrations.

Provides a generic integration client that defers any work until a method
is called, then fails with a clear message. Useful for metadata extraction
and early SDK usage without real implementations.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .base import BaseIntegration


class StubIntegration(BaseIntegration):
    """Generic stub integration with lazy method proxies."""

    def _connect(self) -> None:
        """No-op connect for stub integrations."""
        self._client = None

    def __getattr__(self, name: str) -> Callable[..., Any]:
        if name.startswith("_"):
            raise AttributeError(f"{type(self).__name__} has no attribute {name!r}")

        def _missing(*args: Any, **kwargs: Any) -> Any:
            self._ensure_connected()
            raise NotImplementedError(
                f"Integration '{self._name}' does not implement {name!r} yet. "
                "Install or provide a real integration client before calling it."
            )

        return _missing
