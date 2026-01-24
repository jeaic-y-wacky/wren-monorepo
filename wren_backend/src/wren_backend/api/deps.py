"""FastAPI dependency injection for shared resources."""

from fastapi import Header, HTTPException

from wren_backend.core.credentials import CredentialStore
from wren_backend.core.scheduler import Scheduler
from wren_backend.core.storage import Storage

# Singleton instances (initialized in main.py)
_storage: Storage | None = None
_scheduler: Scheduler | None = None
_credential_store: CredentialStore | None = None


def init_dependencies(
    storage: Storage,
    scheduler: Scheduler,
    credential_store: CredentialStore,
) -> None:
    """Initialize singleton dependencies."""
    global _storage, _scheduler, _credential_store
    _storage = storage
    _scheduler = scheduler
    _credential_store = credential_store


def get_storage() -> Storage:
    """Get the storage instance."""
    if _storage is None:
        raise RuntimeError("Storage not initialized")
    return _storage


def get_scheduler() -> Scheduler:
    """Get the scheduler instance."""
    if _scheduler is None:
        raise RuntimeError("Scheduler not initialized")
    return _scheduler


def get_credential_store() -> CredentialStore:
    """Get the credential store instance."""
    if _credential_store is None:
        raise RuntimeError("CredentialStore not initialized")
    return _credential_store


async def get_current_user_id(
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    authorization: str | None = Header(None),
) -> str:
    """Extract and validate user ID from request headers.

    For Phase 1, this is a simple API key implementation.
    Phase 3+ will add proper authentication (OAuth, JWT, etc.)

    Accepts either:
    - X-API-Key header
    - Authorization: Bearer <token> header
    """
    token = None

    if x_api_key:
        token = x_api_key
    elif authorization and authorization.startswith("Bearer "):
        token = authorization[7:]

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Provide X-API-Key header or Authorization: Bearer <token>",
        )

    # For Phase 1, the token IS the user_id (simple implementation)
    # In production, this would validate against a user database
    # and extract the user_id from a proper token

    # Basic validation - token should be non-empty and reasonable length
    if len(token) < 8:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key format",
        )

    # Return the token as user_id for now
    return token
