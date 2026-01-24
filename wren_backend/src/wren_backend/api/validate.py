"""POST /v1/integrations/validate - Check integration configuration."""

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from wren_backend.api.deps import get_credential_store, get_current_user_id
from wren_backend.core.credentials import CredentialStore
from wren_backend.models.deployment import TriggerConfig, TriggerType

logger = structlog.get_logger()

router = APIRouter(prefix="/integrations")


class TriggerInput(BaseModel):
    """Input trigger for validation."""

    type: TriggerType
    func: str
    config: TriggerConfig


class ValidateRequest(BaseModel):
    """Request body for /v1/integrations/validate."""

    model_config = ConfigDict(extra="forbid")

    integrations: list[str] = []


class ValidationError(BaseModel):
    """A validation error."""

    type: str = "UserFacingConfigError"
    code: str
    message: str
    integration: str | None = None
    action_url: str | None = None
    docs_url: str | None = None


class ValidateResponse(BaseModel):
    """Response from /v1/integrations/validate."""

    valid: bool
    errors: list[ValidationError] = []
    warnings: list[str] = []


def validate_cron_expression(cron: str) -> str | None:
    """Validate a cron expression. Returns error message or None if valid."""
    parts = cron.split()
    if len(parts) != 5:
        return f"Cron expression must have 5 parts, got {len(parts)}"

    # Basic validation - APScheduler will do full validation
    labels = ["minute", "hour", "day", "month", "day_of_week"]
    ranges = [(0, 59), (0, 23), (1, 31), (1, 12), (0, 6)]

    for i, (part, label, (min_val, max_val)) in enumerate(
        zip(parts, labels, ranges)
    ):
        if part == "*":
            continue
        if part.startswith("*/"):
            try:
                step = int(part[2:])
                if step < 1:
                    return f"Invalid step value in {label}: {part}"
            except ValueError:
                return f"Invalid step value in {label}: {part}"
            continue
        try:
            val = int(part)
            if val < min_val or val > max_val:
                return f"Invalid {label} value: {val} (must be {min_val}-{max_val})"
        except ValueError:
            # Could be a range (1-5) or list (1,3,5) - let APScheduler handle
            pass

    return None


def validate_triggers(
    triggers: list[TriggerInput],
    integrations: list[str],
) -> tuple[list[ValidationError], list[str]]:
    """Validate trigger configs and return errors + warnings."""
    errors: list[ValidationError] = []
    warnings: list[str] = []

    # Check integrations
    for trigger in triggers:
        if trigger.type == TriggerType.SCHEDULE:
            if not trigger.config.cron:
                errors.append(
                    ValidationError(
                        type="AgentFixableError",
                        code="MISSING_CRON_EXPRESSION",
                        message=f"Schedule trigger for '{trigger.func}' missing cron expression",
                    )
                )
            else:
                cron_error = validate_cron_expression(trigger.config.cron)
                if cron_error:
                    errors.append(
                        ValidationError(
                            type="AgentFixableError",
                            code="INVALID_CRON_EXPRESSION",
                            message=f"Invalid cron expression for '{trigger.func}': {cron_error}",
                    )
                )

        elif trigger.type == TriggerType.EMAIL:
            # Email triggers require email integration
            if "gmail" not in integrations:
                warnings.append(
                    f"Email trigger '{trigger.func}' may require gmail integration"
                )

        elif trigger.type == TriggerType.WEBHOOK:
            # Webhook triggers are always valid (platform generates URL)
            pass

    return errors, warnings


async def validate_integrations(
    integrations: list[str],
    user_id: str,
    credential_store: CredentialStore,
    log: structlog.stdlib.BoundLogger,
) -> list[ValidationError]:
    """Validate required integrations are configured."""
    errors: list[ValidationError] = []
    for integration in integrations:
        has_creds = await credential_store.has_credentials(user_id, integration)
        if not has_creds:
            log.info("integration_not_configured", integration=integration)
            errors.append(
                ValidationError(
                    code="INTEGRATION_NOT_CONFIGURED",
                    message=f"{integration.title()} integration not configured",
                    integration=integration,
                    action_url=f"https://wrens.ie/integrations/{integration}/setup",
                    docs_url=f"https://docs.wrens.ie/integrations/{integration}",
                )
            )
    return errors


@router.post("/validate", response_model=ValidateResponse)
async def validate(
    request: ValidateRequest,
    user_id: str = Depends(get_current_user_id),
    credential_store: CredentialStore = Depends(get_credential_store),
) -> ValidateResponse:
    """Validate that integrations are configured and authorized."""
    log = logger.bind(user_id=user_id)

    errors = await validate_integrations(
        request.integrations, user_id, credential_store, log
    )
    warnings: list[str] = []

    valid = len(errors) == 0
    log.info("validation_complete", valid=valid, errors=len(errors))

    return ValidateResponse(valid=valid, errors=errors, warnings=warnings)
