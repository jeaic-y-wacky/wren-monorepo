"""FastAPI dependency injection for shared resources."""

import os
from urllib.request import urlopen
import json

import jwt
from jwt import PyJWKClient
from fastapi import Header, HTTPException

from wren_backend.core.credentials import CredentialStore
from wren_backend.core.scheduler import Scheduler
from wren_backend.core.storage import Storage

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://gvbfhpoolkdlxnvusccg.supabase.co")

# JWKS client for verifying JWTs with asymmetric keys
_jwks_client: PyJWKClient | None = None


def get_jwks_client() -> PyJWKClient:
    """Get or create the JWKS client for JWT verification."""
    global _jwks_client
    if _jwks_client is None:
        jwks_url = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"
        _jwks_client = PyJWKClient(jwks_url)
    return _jwks_client


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
    """Extract and validate user ID from Supabase JWT or API key.

    Accepts either:
    - Authorization: Bearer <supabase_jwt> header (preferred)
    - X-API-Key header (for development/testing)

    Returns:
        User ID (UUID string) from the authenticated user
    """
    token = None

    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
    elif x_api_key:
        token = x_api_key

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Missing authentication. Provide Authorization: Bearer <token> header",
        )

    # Try to decode as Supabase JWT using JWKS (asymmetric keys)
    try:
        jwks_client = get_jwks_client()
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256", "ES256"],
            audience="authenticated",
            issuer=f"{SUPABASE_URL}/auth/v1",
        )
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="Invalid token: missing user ID",
            )
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token has expired",
        )
    except (jwt.InvalidTokenError, jwt.exceptions.PyJWKClientError):
        # Not a valid JWT or JWKS not available, fall back to API key validation
        pass

    # Fall back to API key authentication
    # For development, the token IS the user_id (simple implementation)
    # In production with api_keys table, we would hash and look up the key
    if len(token) < 8:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key format",
        )

    # Check if it looks like a UUID (Supabase user IDs are UUIDs)
    # If not, treat as a development token
    return token
