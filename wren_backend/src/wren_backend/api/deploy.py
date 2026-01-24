"""POST /v1/scripts/deploy - Deploy a validated script."""

from datetime import UTC, datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict

from wren_backend.api.deps import (
    get_credential_store,
    get_current_user_id,
    get_scheduler,
    get_storage,
)
from wren_backend.api.validate import (
    TriggerInput,
    ValidationError,
    validate_integrations,
    validate_triggers,
)
from wren_backend.core.credentials import CredentialStore
from wren_backend.core.scheduler import Scheduler
from wren_backend.core.storage import Storage
from wren_backend.models.deployment import (
    DeploymentCreateResponse,
    DeploymentStatus,
    Trigger,
    TriggerConfig,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/scripts")


class DeployMetadata(BaseModel):
    """Metadata for deployment."""

    model_config = ConfigDict(extra="forbid")

    integrations: list[str] = []
    triggers: list[TriggerInput] = []
    schedules: list[dict[str, str]] = []


class DeployRequest(BaseModel):
    """Request body for /v1/scripts/deploy."""

    model_config = ConfigDict(extra="forbid")

    script: str
    metadata: DeployMetadata
    name: str | None = None


@router.post("/deploy", response_model=DeploymentCreateResponse)
async def deploy(
    request: DeployRequest,
    user_id: str = Depends(get_current_user_id),
    storage: Storage = Depends(get_storage),
    scheduler: Scheduler = Depends(get_scheduler),
    credential_store: CredentialStore = Depends(get_credential_store),
) -> DeploymentCreateResponse:
    """Deploy a validated script to the platform.

    Process:
    1. Read and store script content
    2. Parse and validate metadata (defensive re-validation)
    3. Register triggers with scheduler
    4. Return deployment confirmation
    """
    log = logger.bind(user_id=user_id)

    script_text = request.script
    deploy_metadata = request.metadata

    # Defensive validation
    integration_errors = await validate_integrations(
        deploy_metadata.integrations, user_id, credential_store, log
    )
    trigger_errors, trigger_warnings = validate_triggers(
        deploy_metadata.triggers, deploy_metadata.integrations
    )

    errors: list[ValidationError] = integration_errors + trigger_errors
    if errors:
        log.warning("validation_failed", errors=len(errors))
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Script validation failed",
                "errors": [e.model_dump() for e in errors],
                "warnings": trigger_warnings,
            },
        )

    # Generate deployment name if not provided
    name = request.name
    if not name:
        # Try to extract from script filename
        name = f"deployment_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"

    # Convert triggers
    triggers = [
        Trigger(
            type=t.type,
            func=t.func,
            config=TriggerConfig(**t.config.model_dump()),
        )
        for t in deploy_metadata.triggers
    ]

    # Store deployment
    deployment = await storage.create_deployment(
        user_id=user_id,
        name=name,
        script_content=script_text,
        triggers=triggers,
        integrations=deploy_metadata.integrations,
    )

    log.info("deployment_created", deployment_id=deployment.id, name=name)

    # Register with scheduler
    triggers_registered = scheduler.register_deployment(deployment)
    log.info(
        "triggers_registered",
        deployment_id=deployment.id,
        count=triggers_registered,
    )

    # Get next run time
    next_run = scheduler.get_next_run_time(deployment.id)

    return DeploymentCreateResponse(
        deployment_id=deployment.id,
        status=DeploymentStatus.ACTIVE,
        triggers_registered=triggers_registered,
        created_at=deployment.created_at,
        next_run=next_run,
    )
