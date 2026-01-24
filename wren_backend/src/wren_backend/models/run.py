"""Run model for script executions."""

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field


class RunStatus(str, Enum):
    """Status of a script execution run."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class Run(BaseModel):
    """A single execution run of a deployment."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Unique run ID (run_xxx)")
    deployment_id: str = Field(..., description="Parent deployment ID")
    trigger_type: str = Field(..., description="What triggered this run")
    trigger_func: str = Field(..., description="Function that was called")
    status: RunStatus = RunStatus.PENDING
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: int | None = None
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    error_message: str | None = None


class RunSummary(BaseModel):
    """Summary view of a run for listing."""

    run_id: str
    deployment_id: str
    trigger: str
    status: RunStatus
    started_at: datetime | None
    completed_at: datetime | None
    duration_ms: int | None
    logs_url: str


class RunLogsResponse(BaseModel):
    """Response for run logs endpoint."""

    run_id: str
    stdout: str
    stderr: str
    exit_code: int | None
    error_message: str | None
