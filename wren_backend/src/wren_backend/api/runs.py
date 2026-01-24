"""GET /v1/runs - Execution history and logs."""

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from wren_backend.api.deps import get_current_user_id, get_storage
from wren_backend.core.storage import Storage
from wren_backend.models.run import RunLogsResponse, RunStatus, RunSummary

logger = structlog.get_logger()

router = APIRouter()


class RunsListResponse(BaseModel):
    """Response for listing runs."""

    runs: list[RunSummary]


@router.get("/deployments/{deployment_id}/runs", response_model=RunsListResponse)
async def list_runs(
    deployment_id: str,
    limit: int = 50,
    user_id: str = Depends(get_current_user_id),
    storage: Storage = Depends(get_storage),
) -> RunsListResponse:
    """Get execution history for a deployment."""
    log = logger.bind(user_id=user_id, deployment_id=deployment_id)

    # Verify access
    deployment = await storage.get_deployment(deployment_id)
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")

    if deployment.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    runs = await storage.get_runs_by_deployment(deployment_id, limit=limit)
    log.info("runs_listed", count=len(runs))

    summaries = [
        RunSummary(
            run_id=run.id,
            deployment_id=run.deployment_id,
            trigger=run.trigger_type,
            status=run.status,
            started_at=run.started_at,
            completed_at=run.completed_at,
            duration_ms=run.duration_ms,
            logs_url=f"/v1/runs/{run.id}/logs",
        )
        for run in runs
    ]

    return RunsListResponse(runs=summaries)


@router.get("/runs/{run_id}/logs", response_model=RunLogsResponse)
async def get_run_logs(
    run_id: str,
    user_id: str = Depends(get_current_user_id),
    storage: Storage = Depends(get_storage),
) -> RunLogsResponse:
    """Get logs for a specific run."""
    log = logger.bind(user_id=user_id, run_id=run_id)

    run = await storage.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    # Verify access through deployment
    deployment = await storage.get_deployment(run.deployment_id)
    if not deployment or deployment.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    log.info("logs_retrieved")

    return RunLogsResponse(
        run_id=run.id,
        stdout=run.stdout,
        stderr=run.stderr,
        exit_code=run.exit_code,
        error_message=run.error_message,
    )


@router.get("/runs/{run_id}")
async def get_run(
    run_id: str,
    user_id: str = Depends(get_current_user_id),
    storage: Storage = Depends(get_storage),
):
    """Get details of a specific run."""
    run = await storage.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    # Verify access through deployment
    deployment = await storage.get_deployment(run.deployment_id)
    if not deployment or deployment.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    return {
        "id": run.id,
        "deployment_id": run.deployment_id,
        "trigger_type": run.trigger_type,
        "trigger_func": run.trigger_func,
        "status": run.status,
        "started_at": run.started_at,
        "completed_at": run.completed_at,
        "duration_ms": run.duration_ms,
        "exit_code": run.exit_code,
        "error_message": run.error_message,
    }
