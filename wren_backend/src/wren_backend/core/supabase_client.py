"""Supabase client singleton and configuration."""

import os
from functools import lru_cache

from supabase import create_client, Client

# Environment variables for Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://gvbfhpoolkdlxnvusccg.supabase.co")
SUPABASE_PUBLISHABLE_KEY = os.getenv(
    "SUPABASE_PUBLISHABLE_KEY",
    "sb_publishable_f-FvU_XTHic7MNOyC41VsA_VduLNnZy",
)
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """Get the Supabase client singleton (uses publishable key for RLS).

    This client respects Row Level Security policies and should be used
    for user-facing operations where auth context is available.
    """
    return create_client(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY)


@lru_cache(maxsize=1)
def get_supabase_admin_client() -> Client | None:
    """Get the Supabase admin client (bypasses RLS).

    This client uses the secret key and bypasses RLS.
    Only use for admin operations like scheduler callbacks.
    Returns None if secret key is not configured.
    """
    if not SUPABASE_SECRET_KEY:
        return None
    return create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)
