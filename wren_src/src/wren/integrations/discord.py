"""
Discord Integration - Real implementation using discord.py.

Provides synchronous wrappers around discord.py's async API for sending
messages, reading channel history, creating channels, and adding reactions.
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, ClassVar

from . import register_integration
from .base import BaseIntegration
from .docs import AuthType, IntegrationDocs, MethodDoc, ParamDoc

# Defer import to allow SDK to work without discord.py installed
discord_module: Any = None


def _get_discord():
    """Lazy import discord.py."""
    global discord_module
    if discord_module is None:
        try:
            import discord

            discord_module = discord
        except ImportError as e:
            raise ImportError(
                "discord.py is required for the Discord integration. "
                "Install it with: pip install discord.py"
            ) from e
    return discord_module


@dataclass
class DiscordMessage:
    """Represents a Discord message."""

    id: str
    channel_id: str
    content: str
    author: str
    timestamp: datetime
    embeds: list[dict[str, Any]]


class DiscordClient:
    """
    Synchronous wrapper around discord.py's HTTP-only API.

    Uses login() instead of start() — no gateway/websocket connection needed
    since all operations are REST-based.
    """

    def __init__(self, token: str) -> None:
        self._token = token
        self._discord = _get_discord()

    def _run_async(self, coro):
        """Run an async coroutine synchronously."""
        return asyncio.run(coro)

    async def _run_with_client(self, callback):
        """
        Create a discord.py client, log in via REST (no gateway), run
        callback, then cleanly close the HTTP session.
        """
        discord = self._discord
        intents = discord.Intents.default()
        client = discord.Client(intents=intents)
        try:
            await client.login(self._token)
            return await callback(client)
        finally:
            await client.close()

    def send_message(
        self,
        channel_id: str,
        content: str,
        embed: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send a message to a channel."""
        discord = self._discord

        async def _do(client):
            channel = await client.fetch_channel(int(channel_id))
            embed_obj = discord.Embed.from_dict(embed) if embed else None
            message = await channel.send(content=content, embed=embed_obj)
            return {
                "id": str(message.id),
                "channel_id": str(message.channel.id),
                "content": message.content,
                "timestamp": message.created_at.isoformat(),
            }

        return self._run_async(self._run_with_client(_do))

    def get_messages(self, channel_id: str, limit: int = 50) -> list[DiscordMessage]:
        """Get recent messages from a channel."""

        async def _do(client):
            channel = await client.fetch_channel(int(channel_id))
            messages = []
            async for msg in channel.history(limit=limit):
                messages.append(
                    DiscordMessage(
                        id=str(msg.id),
                        channel_id=str(msg.channel.id),
                        content=msg.content,
                        author=str(msg.author),
                        timestamp=msg.created_at,
                        embeds=[e.to_dict() for e in msg.embeds],
                    )
                )
            return messages

        return self._run_async(self._run_with_client(_do))

    def create_channel(
        self,
        name: str,
        guild_id: str,
        channel_type: str = "text",
    ) -> dict[str, Any]:
        """Create a new channel in a guild."""

        async def _do(client):
            guild = await client.fetch_guild(int(guild_id))
            if channel_type == "voice":
                channel = await guild.create_voice_channel(name=name)
            else:
                channel = await guild.create_text_channel(name=name)
            return {
                "id": str(channel.id),
                "name": channel.name,
                "type": channel_type,
                "guild_id": str(guild.id),
            }

        return self._run_async(self._run_with_client(_do))

    def add_reaction(self, channel_id: str, message_id: str, emoji: str) -> None:
        """Add a reaction to a message."""

        async def _do(client):
            channel = await client.fetch_channel(int(channel_id))
            message = await channel.fetch_message(int(message_id))
            await message.add_reaction(emoji)

        self._run_async(self._run_with_client(_do))


@register_integration("discord")
class DiscordIntegration(BaseIntegration):
    """
    Discord integration using discord.py.

    Provides methods for sending messages, reading channel history,
    creating channels, and adding reactions to Discord servers.
    """

    DOCS: ClassVar[IntegrationDocs] = IntegrationDocs(
        name="discord",
        description="Send messages and interact with Discord servers (guilds).",
        auth_type=AuthType.TOKEN,
        init_params=[
            ParamDoc(
                name="token",
                type="str",
                description="Discord bot token (or set DISCORD_BOT_TOKEN env var)",
                required=False,
                default="None",
            ),
            ParamDoc(
                name="default_channel_id",
                type="str",
                description="Default channel ID for post() method",
                required=False,
                default="None",
            ),
            ParamDoc(
                name="default_guild_id",
                type="str",
                description="Default guild (server) ID for operations",
                required=False,
                default="None",
            ),
        ],
        methods=[
            MethodDoc(
                name="post",
                description="Send a message to the default channel.",
                params=[
                    ParamDoc(
                        name="content",
                        type="str",
                        description="Message text to send",
                        required=True,
                    ),
                    ParamDoc(
                        name="embed",
                        type="dict",
                        description="Optional embed object for rich formatting",
                        required=False,
                        default="None",
                    ),
                ],
                returns="dict - Discord API response with message id and channel_id",
                example='discord.post("Deployment completed successfully!")',
            ),
            MethodDoc(
                name="send_message",
                description="Send a message to a specific channel.",
                params=[
                    ParamDoc(
                        name="channel_id",
                        type="str",
                        description="Discord channel ID",
                        required=True,
                    ),
                    ParamDoc(
                        name="content",
                        type="str",
                        description="Message text to send",
                        required=True,
                    ),
                    ParamDoc(
                        name="embed",
                        type="dict",
                        description="Optional embed object for rich formatting",
                        required=False,
                        default="None",
                    ),
                ],
                returns="dict - Discord API response",
                example='discord.send_message("123456789", "Hello from Wren!")',
            ),
            MethodDoc(
                name="get_messages",
                description="Get recent messages from a channel.",
                params=[
                    ParamDoc(
                        name="channel_id",
                        type="str",
                        description="Discord channel ID",
                        required=True,
                    ),
                    ParamDoc(
                        name="limit",
                        type="int",
                        description="Maximum messages to return (1-100)",
                        required=False,
                        default="50",
                    ),
                ],
                returns="list[DiscordMessage] - List of message objects",
                example='messages = discord.get_messages("123456789", limit=20)',
            ),
            MethodDoc(
                name="create_channel",
                description="Create a new channel in a guild.",
                params=[
                    ParamDoc(
                        name="name",
                        type="str",
                        description="Name for the new channel",
                        required=True,
                    ),
                    ParamDoc(
                        name="guild_id",
                        type="str",
                        description="Guild ID (uses default_guild_id if not provided)",
                        required=False,
                        default="None",
                    ),
                    ParamDoc(
                        name="channel_type",
                        type="str",
                        description="Channel type: 'text' or 'voice'",
                        required=False,
                        default="text",
                    ),
                ],
                returns="dict - Created channel object with id and name",
                example='channel = discord.create_channel("alerts", channel_type="text")',
            ),
            MethodDoc(
                name="add_reaction",
                description="Add an emoji reaction to a message.",
                params=[
                    ParamDoc(
                        name="channel_id",
                        type="str",
                        description="Discord channel ID",
                        required=True,
                    ),
                    ParamDoc(
                        name="message_id",
                        type="str",
                        description="Message ID to react to",
                        required=True,
                    ),
                    ParamDoc(
                        name="emoji",
                        type="str",
                        description="Emoji to add (Unicode or custom format)",
                        required=True,
                    ),
                ],
                returns="None",
                example='discord.add_reaction("123456789", "987654321", "👍")',
            ),
        ],
        example="""import wren

discord = wren.integrations.discord.init(default_channel_id="123456789")

@wren.on_schedule("0 9 * * *")
def daily_weather():
    weather = wren.ai("Get today's weather forecast for Dublin")
    discord.post(f"Good morning! Today's weather: {weather}")""",
    )

    def _connect(self) -> None:
        """Initialize the Discord client with bot token."""
        token = self._config.get("token") or os.environ.get("DISCORD_BOT_TOKEN")
        if not token:
            raise ValueError(
                "Discord bot token required. "
                "Pass token= to init() or set DISCORD_BOT_TOKEN environment variable."
            )
        self._client = DiscordClient(token)

    @property
    def default_channel_id(self) -> str | None:
        """Get the configured default channel ID."""
        return self._config.get("default_channel_id")

    @property
    def default_guild_id(self) -> str | None:
        """Get the configured default guild ID."""
        return self._config.get("default_guild_id")

    def send_message(
        self,
        channel_id: str,
        content: str,
        embed: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Send a message to a specific channel.

        Args:
            channel_id: Discord channel ID
            content: Message text to send
            embed: Optional embed dict for rich formatting

        Returns:
            Dict with message id, channel_id, content, and timestamp
        """
        self._ensure_connected()
        return self._client.send_message(channel_id, content, embed)

    def post(
        self,
        content: str,
        embed: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Send a message to the default channel.

        Args:
            content: Message text to send
            embed: Optional embed dict for rich formatting

        Returns:
            Dict with message id, channel_id, content, and timestamp

        Raises:
            ValueError: If no default_channel_id is configured
        """
        if not self.default_channel_id:
            raise ValueError(
                "No default_channel_id configured. "
                "Pass default_channel_id= to init() or use send_message() instead."
            )
        return self.send_message(self.default_channel_id, content, embed)

    def get_messages(
        self,
        channel_id: str,
        limit: int = 50,
    ) -> list[DiscordMessage]:
        """
        Get recent messages from a channel.

        Args:
            channel_id: Discord channel ID
            limit: Maximum messages to return (1-100)

        Returns:
            List of DiscordMessage objects
        """
        self._ensure_connected()
        return self._client.get_messages(channel_id, limit)

    def create_channel(
        self,
        name: str,
        guild_id: str | None = None,
        channel_type: str = "text",
    ) -> dict[str, Any]:
        """
        Create a new channel in a guild.

        Args:
            name: Name for the new channel
            guild_id: Guild ID (uses default_guild_id if not provided)
            channel_type: 'text' or 'voice'

        Returns:
            Dict with channel id, name, type, and guild_id

        Raises:
            ValueError: If no guild_id provided and no default configured
        """
        self._ensure_connected()
        gid = guild_id or self.default_guild_id
        if not gid:
            raise ValueError(
                "No guild_id provided and no default_guild_id configured. "
                "Pass guild_id= or configure default_guild_id in init()."
            )
        return self._client.create_channel(name, gid, channel_type)

    def add_reaction(
        self,
        channel_id: str,
        message_id: str,
        emoji: str,
    ) -> None:
        """
        Add an emoji reaction to a message.

        Args:
            channel_id: Discord channel ID
            message_id: Message ID to react to
            emoji: Emoji to add (Unicode emoji or custom format)
        """
        self._ensure_connected()
        self._client.add_reaction(channel_id, message_id, emoji)
