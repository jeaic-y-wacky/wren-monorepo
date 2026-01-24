"""Error taxonomy for Wren Backend.

All errors follow a consistent classification:
- AgentFixableError: Visible to agent, agent can fix code locally
- UserFacingConfigError: Visible to user, requires UI configuration
- InternalError: Logged only, requires ops investigation
"""

from typing import Literal
from pydantic import BaseModel


class WrenError(Exception):
    """Base exception for all Wren errors."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class AgentFixableError(WrenError):
    """Error that the agent can fix by modifying code.

    Examples: syntax error, missing function, invalid cron expression.
    """

    error_type: Literal["AgentFixableError"] = "AgentFixableError"

    def __init__(self, code: str, message: str, details: dict | None = None):
        super().__init__(code, message)
        self.details = details or {}


class UserFacingConfigError(WrenError):
    """Error requiring user action via UI.

    Examples: missing OAuth, no permissions, expired token.
    """

    error_type: Literal["UserFacingConfigError"] = "UserFacingConfigError"

    def __init__(
        self,
        code: str,
        message: str,
        action_url: str | None = None,
        docs_url: str | None = None,
        integration: str | None = None,
    ):
        super().__init__(code, message)
        self.action_url = action_url
        self.docs_url = docs_url
        self.integration = integration


class InternalError(WrenError):
    """Internal error - logged but not exposed to users.

    Examples: database failure, scheduler crash.
    """

    error_type: Literal["InternalError"] = "InternalError"

    def __init__(self, code: str, message: str, cause: Exception | None = None):
        super().__init__(code, message)
        self.cause = cause


class ErrorDetail(BaseModel):
    """Error detail for API responses."""

    type: Literal["AgentFixableError", "UserFacingConfigError", "InternalError"]
    code: str
    message: str
    action_url: str | None = None
    docs_url: str | None = None
    integration: str | None = None
    correlation_id: str | None = None


class ErrorResponse(BaseModel):
    """Standard error response format."""

    error: ErrorDetail
