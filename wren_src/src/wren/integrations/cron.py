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

from typing import Any, Callable, ClassVar

from ..core.registry import registry
from . import register_integration
from .base import BaseIntegration
from .docs import AuthType, IntegrationDocs, MethodDoc, ParamDoc


@register_integration("cron")
class CronIntegration(BaseIntegration):
    """
    Mock cron integration.

    The platform handles actual cron execution - this integration
    provides an API for manual schedule registration as an alternative
    to decorators.
    """

    DOCS: ClassVar[IntegrationDocs] = IntegrationDocs(
        name="cron",
        description="Schedule tasks using cron expressions. Prefer using @wren.on_schedule() decorator instead of this integration directly.",
        init_params=[],
        methods=[
            MethodDoc(
                name="schedule",
                description="Manually register a scheduled task. Use this when decorators aren't suitable (e.g., dynamic schedule generation).",
                params=[
                    ParamDoc(
                        name="cron_expr",
                        type="str",
                        description="Cron expression (minute hour day month weekday)",
                        required=True,
                    ),
                    ParamDoc(
                        name="func",
                        type="Callable",
                        description="Function to schedule",
                        required=True,
                    ),
                    ParamDoc(
                        name="timezone",
                        type="str",
                        description="Timezone name (e.g., 'America/New_York')",
                        required=False,
                        default="None",
                    ),
                ],
                returns="None",
                example='cron.schedule("0 9 * * 1-5", send_weekday_report)',
            ),
            MethodDoc(
                name="get_schedules",
                description="Return all registered schedules (for debugging/testing).",
                params=[],
                returns="list[dict] - List of schedule configurations",
                example="schedules = cron.get_schedules()",
            ),
        ],
        example="""import wren

cron = wren.integrations.cron.init()

# Preferred: use decorator
@wren.on_schedule("0 9 * * *")
def daily_report():
    generate_and_send_report()

# Alternative: manual registration for dynamic schedules
def create_schedule(hour: int):
    cron.schedule(f"0 {hour} * * *", check_status)

# Common cron patterns:
# "0 9 * * *"     - Daily at 9 AM
# "*/15 * * * *"  - Every 15 minutes
# "0 0 * * 0"     - Weekly on Sunday at midnight
# "0 9 * * 1-5"   - Weekdays at 9 AM""",
    )

    def _connect(self) -> None:
        """No actual connection needed for cron."""
        pass

    def schedule(
        self, cron_expr: str, func: Callable[..., Any], timezone: str | None = None
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
