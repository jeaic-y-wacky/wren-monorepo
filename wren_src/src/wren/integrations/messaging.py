"""
Messaging Integration - Generic messaging platform mock.

A mock/placeholder integration representing Slack, Teams, or similar
messaging platforms. Provides a common API for sending messages.

Usage:
    messaging = wren.integrations.messaging.init(
        default_channel="#alerts"
    )

    # Send to default channel
    messaging.post("Deployment completed!")

    # Send to specific channel
    messaging.send_message("#engineering", "Build passed")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from datetime import datetime

from .base import BaseIntegration
from . import register_integration


@dataclass
class Message:
    """Represents a sent message (for mock tracking)."""
    channel: str
    text: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)


class MockMessagingClient:
    """Mock client that tracks sent messages."""

    def __init__(self, config: dict[str, Any]) -> None:
        self._config = config
        self._messages: list[Message] = []

    def send(self, channel: str, text: str, **kwargs: Any) -> dict[str, Any]:
        """Send a message and return confirmation."""
        msg = Message(channel=channel, text=text, metadata=kwargs)
        self._messages.append(msg)
        return {
            "ok": True,
            "channel": channel,
            "ts": msg.timestamp.isoformat(),
            "message": {"text": text},
        }

    @property
    def sent_messages(self) -> list[Message]:
        """Return all sent messages (for testing)."""
        return list(self._messages)

    def clear(self) -> None:
        """Clear sent messages (for testing)."""
        self._messages.clear()


@register_integration("messaging")
class MessagingIntegration(BaseIntegration):
    """
    Mock messaging integration (Slack/Teams-like).

    Provides a simple API for sending messages. In production,
    this would connect to an actual messaging service.
    """

    def _connect(self) -> None:
        """Initialize the mock client."""
        self._client = MockMessagingClient(self._config)

    @property
    def default_channel(self) -> str:
        """Get the configured default channel."""
        return self._config.get("default_channel", "#general")

    def send_message(
        self,
        channel: str,
        text: str,
        **kwargs: Any
    ) -> dict[str, Any]:
        """
        Send a message to a specific channel.

        Args:
            channel: Channel name (e.g., "#alerts")
            text: Message content
            **kwargs: Additional options (attachments, etc.)

        Returns:
            API response dict with ok, channel, ts, message
        """
        self._ensure_connected()
        return self._client.send(channel, text, **kwargs)

    def post(self, message: str, **kwargs: Any) -> dict[str, Any]:
        """
        Post a message to the default channel.

        Convenience method for quick notifications.

        Args:
            message: Message content
            **kwargs: Additional options

        Returns:
            API response dict
        """
        return self.send_message(self.default_channel, message, **kwargs)

    def get_sent_messages(self) -> list[Message]:
        """Return sent messages (for testing/debugging)."""
        self._ensure_connected()
        return self._client.sent_messages

    def clear_messages(self) -> None:
        """Clear message history (for testing)."""
        if self._connected and self._client:
            self._client.clear()
