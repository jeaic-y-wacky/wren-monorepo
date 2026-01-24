"""Deployment model for Wren Backend."""

from datetime import UTC, datetime
from enum import Enum
from functools import partial
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class DeploymentStatus(str, Enum):
    """Status of a deployment."""

    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"
    DELETED = "deleted"


class TriggerType(str, Enum):
    """Type of trigger for script execution."""

    SCHEDULE = "schedule"
    EMAIL = "email"
    WEBHOOK = "webhook"
    MANUAL = "manual"


class TriggerConfig(BaseModel):
    """Configuration for a trigger."""

    cron: str | None = None
    timezone: str = "UTC"
    filter: dict[str, Any] | None = None


class Trigger(BaseModel):
    """A trigger that initiates script execution."""

    type: TriggerType
    func: str
    config: TriggerConfig


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Deployment(BaseModel):
    """A deployed script with its metadata."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Unique deployment ID (dep_xxx)")
    user_id: str = Field(..., description="Owner user ID")
    name: str = Field(..., description="Deployment name")
    script_content: str = Field(..., description="Python script content")
    status: DeploymentStatus = DeploymentStatus.ACTIVE
    triggers: list[Trigger] = Field(default_factory=list)
    integrations: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    version: int = Field(default=1, description="Script version number")


class DeploymentSummary(BaseModel):
    """Summary view of a deployment for listing."""

    id: str
    name: str
    status: DeploymentStatus
    triggers: int
    last_run: datetime | None = None
    next_run: datetime | None = None
    created_at: datetime


class DeploymentCreateResponse(BaseModel):
    """Response after creating a deployment."""

    deployment_id: str
    status: DeploymentStatus
    triggers_registered: int
    created_at: datetime
    next_run: datetime | None = None
