"""
Slack Integration - Stub implementation.

Registers the Slack integration name and provides a lazy client that
fails on method calls until a real implementation is provided.
"""

from __future__ import annotations

from typing import ClassVar

from . import register_integration
from .docs import AuthType, IntegrationDocs, MethodDoc, ParamDoc
from .stub import StubIntegration


@register_integration("slack")
class SlackIntegration(StubIntegration):
    """Stub Slack integration."""

    DOCS: ClassVar[IntegrationDocs] = IntegrationDocs(
        name="slack",
        description="Send messages and interact with Slack workspaces.",
        auth_type=AuthType.OAUTH,
        init_params=[
            ParamDoc(
                name="default_channel",
                type="str",
                description="Default channel for post() method",
                required=False,
                default="#general",
            ),
        ],
        methods=[
            MethodDoc(
                name="post",
                description="Post a message to the default channel.",
                params=[
                    ParamDoc(
                        name="message",
                        type="str",
                        description="Message text to post",
                        required=True,
                    ),
                ],
                returns="dict - Slack API response with ts (timestamp) and channel",
                example='slack.post("Deployment completed successfully!")',
            ),
            MethodDoc(
                name="send_message",
                description="Send a message to a specific channel.",
                params=[
                    ParamDoc(
                        name="channel",
                        type="str",
                        description="Channel name (e.g., '#alerts') or ID",
                        required=True,
                    ),
                    ParamDoc(
                        name="text",
                        type="str",
                        description="Message text",
                        required=True,
                    ),
                    ParamDoc(
                        name="thread_ts",
                        type="str",
                        description="Thread timestamp to reply to",
                        required=False,
                        default="None",
                    ),
                ],
                returns="dict - Slack API response",
                example='slack.send_message("#engineering", "Build passed!")',
            ),
            MethodDoc(
                name="get_messages",
                description="Get recent messages from a channel.",
                params=[
                    ParamDoc(
                        name="channel",
                        type="str",
                        description="Channel name or ID",
                        required=True,
                    ),
                    ParamDoc(
                        name="limit",
                        type="int",
                        description="Maximum messages to return",
                        required=False,
                        default="100",
                    ),
                ],
                returns="list[Message] - List of message objects",
                example='messages = slack.get_messages("#support", limit=50)',
            ),
        ],
        example="""import wren

slack = wren.integrations.slack.init(default_channel="#notifications")

@wren.on_email(from_addr="*@alerts.pagerduty.com")
def handle_alert(email):
    summary = wren.ai.summarize(email.body, max_length=200)
    slack.post(f"PagerDuty Alert: {summary}")""",
    )
