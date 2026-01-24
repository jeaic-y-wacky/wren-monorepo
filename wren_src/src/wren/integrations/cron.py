"""
Cron Integration - Mock scheduled task support.

This is a mock/placeholder integration for cron-based scheduling.
In production, the platform handles actual scheduling - this integration
exists primarily for registration and metadata extraction.

Usage:
    cron = wren.integrations.cron.init()

    # Decorators are the primary way to schedule tasks
    @wren.on_schedule("0 9 * * *")
    def daily_job():
        pass

    # Alternative: manual scheduling via integration
    cron.schedule("*/5 * * * *", check_health)
"""

from __future__ import annotations

from typing import Any, Callable

from .base import BaseIntegration
from . import register_integration
from ..core.registry import registry


@register_integration("cron")
class CronIntegration(BaseIntegration):
    """
    Mock cron integration.

    The platform handles actual cron execution - this integration
    provides an API for manual schedule registration as an alternative
    to decorators.
    """

    def _connect(self) -> None:
        """No actual connection needed for cron."""
        pass

    def schedule(
        self,
        cron_expr: str,
        func: Callable[..., Any],
        timezone: str | None = None
    ) -> None:
        """
        Manually register a scheduled task.

        Alternative to @wren.on_schedule decorator for cases where
        decorators aren't suitable (e.g., dynamic schedule generation).

        Args:
            cron_expr: Cron expression (e.g., "0 9 * * *")
            func: Function to schedule
            timezone: Optional timezone name
        """
        config = {"cron": cron_expr, "timezone": timezone}
        registry.register_trigger("schedule", config, func)

    def get_schedules(self) -> list[dict[str, Any]]:
        """Return all registered schedules (for debugging/testing)."""
        triggers = registry.get_metadata()["triggers"]
        return [t for t in triggers if t["type"] == "schedule"]
