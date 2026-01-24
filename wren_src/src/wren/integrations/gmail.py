"""
Gmail Integration - Stub implementation.

Registers the Gmail integration name and provides a lazy client that
fails on method calls until a real implementation is provided.
"""

from __future__ import annotations

from . import register_integration
from .stub import StubIntegration


@register_integration("gmail")
class GmailIntegration(StubIntegration):
    """Stub Gmail integration."""

