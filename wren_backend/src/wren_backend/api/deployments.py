"""GET /v1/deployments - List and manage deployments."""

from datetime import datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from wren_backend.api.deps import get_current_user_id, get_scheduler, get_storage
from wren_backend.core.scheduler import Scheduler
from wren_backend.core.storage import Storage
from wren_backend.models.deployment import DeploymentStatus, DeploymentSummary

logger = structlog.get_logger()

router = APIRouter()


class DeploymentsListResponse(BaseModel):
    """Response for listing deployments."""

    deployments: list[DeploymentSummary]


@router.get("/deployments", response_model=DeploymentsListResponse)
async def list_deployments(
    user_id: str = Depends(get_current_user_id),
    storage: Storage = Depends(get_storage),
    scheduler: Scheduler = Depends(get_scheduler),
) -> DeploymentsListResponse:
    """List all deployments for the current user."""
    log = logger.bind(user_id=user_id)

    deployments = await storage.get_deployments_by_user(user_id)
    log.info("deployments_listed", count=len(deployments))

    summaries = []
    for dep in deployments:
        # Get last run
        last_run = await storage.get_last_run(dep.id)
        last_run_time = last_run.started_at if last_run else None

        # Get next scheduled run
        next_run = scheduler.get_next_run_time(dep.id)

        summaries.append(
            DeploymentSummary(
                id=dep.id,
                name=dep.name,
                status=dep.status,
                triggers=len(dep.triggers),
                last_run=last_run_time,
                next_run=next_run,
                created_at=dep.created_at,
            )
        )

    return DeploymentsListResponse(deployments=summaries)


@router.get("/deployments/{deployment_id}")
async def get_deployment(
    deployment_id: str,
    user_id: str = Depends(get_current_user_id),
    storage: Storage = Depends(get_storage),
    scheduler: Scheduler = Depends(get_scheduler),
):
    """Get details of a specific deployment."""
    deployment = await storage.get_deployment(deployment_id)

    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")

    if deployment.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    next_run = scheduler.get_next_run_time(deployment_id)

    return {
        "id": deployment.id,
        "name": deployment.name,
        "status": deployment.status,
        "triggers": [t.model_dump() for t in deployment.triggers],
        "integrations": deployment.integrations,
        "created_at": deployment.created_at,
        "updated_at": deployment.updated_at,
        "version": deployment.version,
        "next_run": next_run,
    }


@router.delete("/deployments/{deployment_id}")
async def delete_deployment(
    deployment_id: str,
    user_id: str = Depends(get_current_user_id),
    storage: Storage = Depends(get_storage),
    scheduler: Scheduler = Depends(get_scheduler),
):
    """Delete (undeploy) a deployment."""
    log = logger.bind(user_id=user_id, deployment_id=deployment_id)

    deployment = await storage.get_deployment(deployment_id)

    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")

    if deployment.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Unregister from scheduler
    removed = scheduler.unregister_deployment(deployment_id)
    log.info("triggers_unregistered", count=removed)

    # Soft delete
    await storage.delete_deployment(deployment_id)
    log.info("deployment_deleted")

    return {"status": "deleted", "deployment_id": deployment_id}


@router.post("/deployments/{deployment_id}/pause")
async def pause_deployment(
    deployment_id: str,
    user_id: str = Depends(get_current_user_id),
    storage: Storage = Depends(get_storage),
    scheduler: Scheduler = Depends(get_scheduler),
):
    """Pause a deployment (stop scheduled runs)."""
    deployment = await storage.get_deployment(deployment_id)

    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")

    if deployment.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Unregister from scheduler
    scheduler.unregister_deployment(deployment_id)

    # Update status
    await storage.update_deployment_status(deployment_id, DeploymentStatus.PAUSED)

    return {"status": "paused", "deployment_id": deployment_id}


@router.post("/deployments/{deployment_id}/resume")
async def resume_deployment(
    deployment_id: str,
    user_id: str = Depends(get_current_user_id),
    storage: Storage = Depends(get_storage),
    scheduler: Scheduler = Depends(get_scheduler),
):
    """Resume a paused deployment."""
    deployment = await storage.get_deployment(deployment_id)

    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")

    if deployment.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    if deployment.status != DeploymentStatus.PAUSED:
        raise HTTPException(
            status_code=400, detail="Deployment is not paused"
        )

    # Re-register with scheduler
    scheduler.register_deployment(deployment)

    # Update status
    await storage.update_deployment_status(deployment_id, DeploymentStatus.ACTIVE)

    next_run = scheduler.get_next_run_time(deployment_id)

    return {
        "status": "active",
        "deployment_id": deployment_id,
        "next_run": next_run,
    }
