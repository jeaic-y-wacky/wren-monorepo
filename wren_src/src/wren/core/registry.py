"""
Wren Registry - Metadata collection during import.

The registry tracks integrations and triggers as they are registered
during script import. No AST parsing needed - decorators and init()
calls record directly to this registry.

Usage:
    # Integrations register via init()
    gmail = wren.integrations.gmail.init()  # Records "gmail"

    # Decorators register triggers
    @wren.on_schedule("0 9 * * *")
    def job(): pass  # Records trigger

    # Platform extracts metadata
    metadata = wren.get_metadata()
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class TriggerEntry:
    """A registered trigger (schedule, email, webhook, etc.)."""
    type: str              # "schedule", "email", "webhook", etc.
    func_name: str
    func: Callable
    config: dict[str, Any]  # type-specific configuration


class WrenRegistry:
    """
    Global registry for tracking metadata during script import.

    This is the core of the "prompting approach" - instead of AST parsing,
    decorators and init() calls record metadata directly here during import.
    """

    def __init__(self) -> None:
        self._integrations: list[str] = []
        self._triggers: list[TriggerEntry] = []
        self._schedules: list[dict[str, str]] = []

    def register_integration(self, name: str) -> None:
        """Record an integration as being used."""
        if name not in self._integrations:
            self._integrations.append(name)

    def register_trigger(
        self,
        trigger_type: str,
        config: dict[str, Any],
        func: Callable,
    ) -> None:
        """
        Record a trigger of any type.

        Args:
            trigger_type: Type of trigger ("schedule", "email", "webhook", etc.)
            config: Type-specific configuration dict
            func: The function to be triggered
        """
        entry = TriggerEntry(
            type=trigger_type,
            func_name=func.__name__,
            func=func,
            config=config,
        )
        self._triggers.append(entry)
        if trigger_type == "schedule":
            cron = config.get("cron")
            if cron:
                self._schedules.append({"cron": cron, "func_name": func.__name__})

    def get_triggers_by_type(self, trigger_type: str) -> list[TriggerEntry]:
        """Get all triggers of a specific type."""
        return [t for t in self._triggers if t.type == trigger_type]

    def get_metadata(self) -> dict[str, Any]:
        """
        Return all registered metadata.

        Used by the platform to extract integration requirements and
        event triggers after importing a user's script.
        """
        return {
            "integrations": list(self._integrations),
            "schedules": list(self._schedules),
            "triggers": [
                {
                    "type": t.type,
                    "func": t.func_name,
                    "config": t.config,
                }
                for t in self._triggers
            ],
        }

    def get_functions(self) -> dict[str, Callable]:
        """
        Return a mapping of function names to their callables.

        Used by the runtime to invoke registered functions by name.
        """
        return {t.func_name: t.func for t in self._triggers}

    def clear(self) -> None:
        """Clear all registered metadata. Useful for testing."""
        self._integrations.clear()
        self._triggers.clear()
        self._schedules.clear()


# Global registry instance
registry = WrenRegistry()


def get_metadata() -> dict[str, Any]:
    """Get all registered metadata from the global registry."""
    return registry.get_metadata()
