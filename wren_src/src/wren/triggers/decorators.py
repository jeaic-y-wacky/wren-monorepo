"""
Wren Event Decorators - Register triggers during import.

Decorators execute at import time, recording metadata to the registry
without modifying the decorated function's behavior.

Usage:
    @wren.on_schedule("0 9 * * *")
    def daily_report():
        # Runs every day at 9 AM
        pass

    @wren.on_email(filter={"subject": "urgent"})
    def handle_urgent(email):
        # Triggered when matching email arrives
        pass
"""

from __future__ import annotations

from functools import wraps
from typing import Any, Callable, TypeVar

from ..core.registry import registry

F = TypeVar("F", bound=Callable[..., Any])


def on_schedule(cron: str, timezone: str | None = None) -> Callable[[F], F]:
    """
    Decorator to register a function for scheduled execution.

    The function is recorded in the registry during import. At runtime,
    the platform will invoke it according to the cron schedule.

    Args:
        cron: Cron expression (e.g., "0 9 * * *" for 9 AM daily)
        timezone: Optional timezone (e.g., "America/New_York")

    Example:
        @wren.on_schedule("0 9 * * *")
        def daily_job():
            send_daily_summary()

        @wren.on_schedule("*/15 * * * *", timezone="UTC")
        def every_15_minutes():
            check_for_updates()
    """
    def decorator(func: F) -> F:
        config = {"cron": cron, "timezone": timezone}
        registry.register_trigger("schedule", config, func)
        return func
    return decorator


def on_email(
    filter: dict[str, Any] | None = None,
    **filter_kwargs: Any
) -> Callable[[F], F]:
    """
    Decorator to register a function for email-triggered execution.

    The function is recorded in the registry during import. At runtime,
    the platform will invoke it when a matching email arrives.

    Args:
        filter: Dict of email filters (subject, from, to, labels, etc.)
        **filter_kwargs: Alternative way to specify filters as kwargs

    Filter options:
        - subject: String or regex pattern to match subject
        - from_addr: Sender email address pattern
        - to_addr: Recipient email address pattern
        - labels: List of Gmail labels to match
        - has_attachment: Boolean for attachment presence

    Example:
        @wren.on_email(filter={"subject": "Invoice"})
        def process_invoice(email):
            extract_invoice_data(email)

        @wren.on_email(subject="urgent", from_addr="*@company.com")
        def handle_urgent(email):
            notify_team(email)
    """
    # Support both filter dict and kwargs
    filter_config = filter or {}
    if filter_kwargs:
        filter_config = {**filter_config, **filter_kwargs}

    def decorator(func: F) -> F:
        config = {"filter": filter_config}
        registry.register_trigger("email", config, func)
        return func
    return decorator
