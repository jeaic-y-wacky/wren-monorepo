"""Credentials API - Manage integration credentials."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from .deps import get_credential_store, get_current_user_id
from ..core.credentials import CredentialStore

router = APIRouter(prefix="/credentials")


class SetCredentialsRequest(BaseModel):
    """Request body for setting credentials."""

    credentials: dict[str, str]


class CredentialsResponse(BaseModel):
    """Response for credential operations."""

    integration: str
    configured: bool
    credential_keys: list[str]


@router.put("/{integration}")
async def set_credentials(
    integration: str,
    request: SetCredentialsRequest,
    user_id: str = Depends(get_current_user_id),
    credential_store: CredentialStore = Depends(get_credential_store),
) -> CredentialsResponse:
    """Set credentials for an integration.

    This stores credentials in the credential store for use during script execution.
    """
    await credential_store.set_credentials(user_id, integration, request.credentials)

    return CredentialsResponse(
        integration=integration,
        configured=True,
        credential_keys=list(request.credentials.keys()),
    )


@router.get("/{integration}")
async def get_credentials_status(
    integration: str,
    user_id: str = Depends(get_current_user_id),
    credential_store: CredentialStore = Depends(get_credential_store),
) -> CredentialsResponse:
    """Check if credentials are configured for an integration."""
    creds = await credential_store.get_credentials(user_id, integration)

    return CredentialsResponse(
        integration=integration,
        configured=creds is not None,
        credential_keys=list(creds.keys()) if creds else [],
    )


@router.delete("/{integration}")
async def delete_credentials(
    integration: str,
    user_id: str = Depends(get_current_user_id),
    credential_store: CredentialStore = Depends(get_credential_store),
) -> CredentialsResponse:
    """Delete credentials for an integration."""
    await credential_store.delete_credentials(user_id, integration)

    return CredentialsResponse(
        integration=integration,
        configured=False,
        credential_keys=[],
    )
