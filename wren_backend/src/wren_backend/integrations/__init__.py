"""Integration-specific logic (stubs for Phase 1)."""

from .gmail import GmailIntegration
from .slack import SlackIntegration

__all__ = ["GmailIntegration", "SlackIntegration"]
