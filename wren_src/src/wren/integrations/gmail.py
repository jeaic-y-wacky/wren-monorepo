"""
Gmail Integration - Stub implementation.

Registers the Gmail integration name and provides a lazy client that
fails on method calls until a real implementation is provided.
"""

from __future__ import annotations

from typing import ClassVar

from . import register_integration
from .docs import AuthType, IntegrationDocs, MethodDoc, ParamDoc
from .stub import StubIntegration


@register_integration("gmail")
class GmailIntegration(StubIntegration):
    """Stub Gmail integration."""

    DOCS: ClassVar[IntegrationDocs] = IntegrationDocs(
        name="gmail",
        description="Read and send emails via Gmail API.",
        auth_type=AuthType.OAUTH,
        init_params=[],
        methods=[
            MethodDoc(
                name="inbox",
                description="Get emails from inbox.",
                params=[
                    ParamDoc(
                        name="unread",
                        type="bool",
                        description="Only return unread emails",
                        required=False,
                        default="False",
                    ),
                    ParamDoc(
                        name="limit",
                        type="int",
                        description="Maximum number of emails to return",
                        required=False,
                        default="50",
                    ),
                    ParamDoc(
                        name="labels",
                        type="list[str]",
                        description="Filter by label names",
                        required=False,
                        default="None",
                    ),
                ],
                returns="list[Email] - List of email objects with subject, body, from_addr, date",
                example='emails = gmail.inbox(unread=True, limit=10)',
            ),
            MethodDoc(
                name="send_email",
                description="Send an email.",
                params=[
                    ParamDoc(
                        name="to",
                        type="str | list[str]",
                        description="Recipient email address(es)",
                        required=True,
                    ),
                    ParamDoc(
                        name="subject",
                        type="str",
                        description="Email subject line",
                        required=True,
                    ),
                    ParamDoc(
                        name="body",
                        type="str",
                        description="Email body content",
                        required=True,
                    ),
                    ParamDoc(
                        name="html",
                        type="bool",
                        description="Whether body is HTML",
                        required=False,
                        default="False",
                    ),
                ],
                returns="dict - Send confirmation with message_id",
                example='gmail.send_email(to="team@company.com", subject="Update", body="...")',
            ),
            MethodDoc(
                name="search",
                description="Search emails with Gmail query syntax.",
                params=[
                    ParamDoc(
                        name="query",
                        type="str",
                        description="Gmail search query (e.g., 'from:boss subject:urgent')",
                        required=True,
                    ),
                    ParamDoc(
                        name="limit",
                        type="int",
                        description="Maximum results to return",
                        required=False,
                        default="50",
                    ),
                ],
                returns="list[Email] - Matching emails",
                example='emails = gmail.search("from:support@vendor.com after:2024/01/01")',
            ),
        ],
        example="""import wren

gmail = wren.integrations.gmail.init()

@wren.on_schedule("0 9 * * *")
def daily_summary():
    emails = gmail.inbox(unread=True)
    for email in emails:
        if wren.ai("Is this urgent?", email.body):
            gmail.send_email(
                to="me@company.com",
                subject=f"Urgent: {email.subject}",
                body=wren.ai.summarize(email.body)
            )""",
    )
