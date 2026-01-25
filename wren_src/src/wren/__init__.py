"""
Wren - AI-Native SDK

An SDK designed specifically for LLMs to write code against.
Zero configuration, intelligent defaults, educational errors.

Quick Start:
    import wren

    # Simple AI decisions
    if wren.ai("Is this urgent?", email_text):
        escalate()

    # Structured extraction
    booking: BookingRequest = wren.ai.extract(email_text)

    # Context flows automatically
    @wren.on_email()
    def handle_email(email):
        if wren.ai("booking?", email):
            process_booking()  # Has access to email context
"""

__version__ = "0.1.0"
__author__ = "Jeaic"

# Import from subpackages
from .ai import ai, llm
from .core import (
    config,
    context,
    get_config,
    get_metadata,
    get_request_id,
    registry,
    reload_config,
    with_context,
)
from .errors import WrenError, handle_error
from .integrations import integrations
from .triggers import on_email, on_schedule

# Public API exports
__all__ = [
    # Main interfaces
    "ai",
    "context",
    "config",
    "llm",
    # Prompting approach (event system)
    "registry",
    "get_metadata",
    "on_schedule",
    "on_email",
    "integrations",
    # Functions
    "get_config",
    "reload_config",
    "with_context",
    "get_request_id",
    "handle_error",
    # Types
    "WrenError",
    # Version info
    "__version__",
]


# Convenience: allow wren.ai() directly
def __getattr__(name):
    """Allow direct access to ai methods at module level.

    Example:
        import wren
        wren.ai("question?")  # Works
    """
    if hasattr(ai, name):
        return getattr(ai, name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
