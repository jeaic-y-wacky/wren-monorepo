# Wren Integrations System

This document explains how integrations work in the Wren SDK and backend, including:
- How to add new integrations
- How credentials flow from backend to SDK
- How the agent discovers and uses integration documentation

## Overview

Wren integrations are self-documenting components split across SDK and backend:

| Component | Responsibility |
|-----------|----------------|
| **SDK** | API documentation, method stubs, registers integration *name* in metadata |
| **Backend** | Credential definitions (OAuth scopes, env var mappings), validation, injection |

The **integration name** (e.g., "gmail", "slack") is the contract linking them together.

---

## SDK-Backend Credential Contract

### The Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              SCRIPT TIME (SDK)                               │
│                                                                             │
│   gmail = wren.integrations.gmail.init()  ──► Registers "gmail" in metadata │
│   slack = wren.integrations.slack.init()  ──► Registers "slack" in metadata │
│                                                                             │
│   Script metadata: { "integrations": ["gmail", "slack"] }                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            DEPLOY TIME (Backend)                             │
│                                                                             │
│   POST /v1/scripts/deploy                                                   │
│   Body: { script, metadata: { integrations: ["gmail", "slack"] } }          │
│                                                                             │
│   Backend does:                                                             │
│   1. Look up "gmail" in registry ──► GMAIL_SPEC (scopes, env vars, etc.)   │
│   2. Check credential_store.has_credentials(user_id, "gmail")               │
│   3. If missing → Return error with setup_url for OAuth flow                │
│   4. If present → Store script, schedule triggers                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                             RUN TIME (Backend)                               │
│                                                                             │
│   Trigger fires (cron, email, etc.)                                         │
│                                                                             │
│   Backend does:                                                             │
│   1. credential_store.get_env_for_execution(user_id, ["gmail", "slack"])   │
│      Returns: { "GMAIL_ACCESS_TOKEN": "...", "SLACK_ACCESS_TOKEN": "..." } │
│                                                                             │
│   2. Execute script in sandbox with env vars injected                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          INSIDE SCRIPT (SDK)                                 │
│                                                                             │
│   gmail._connect() is called lazily on first method use                     │
│                                                                             │
│   def _connect(self):                                                       │
│       token = os.environ.get("GMAIL_ACCESS_TOKEN")  # Injected by backend  │
│       self._client = GmailAPIClient(token=token)                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Environment Variable Naming Convention

The backend uses the integration's `CredentialSpec` to map stored credentials to environment variables:

| Integration | Stored Key | Environment Variable |
|-------------|------------|---------------------|
| gmail | `access_token` | `GMAIL_ACCESS_TOKEN` |
| gmail | `refresh_token` | `GMAIL_REFRESH_TOKEN` |
| slack | `access_token` | `SLACK_ACCESS_TOKEN` |
| slack | `refresh_token` | `SLACK_REFRESH_TOKEN` |

The mapping is defined in `wren_backend/src/wren_backend/integrations/` for each integration.

---

## Adding a New Integration

Adding a new integration requires changes in **both** SDK and backend.

### Step 1: Define Credentials in Backend

Create or update `wren_backend/src/wren_backend/integrations/my_service.py`:

```python
"""MyService integration definition."""

from .registry import (
    CredentialSpec,
    CredentialType,
    IntegrationSpec,
    register_integration,
)

MY_SERVICE_SPEC = register_integration(
    IntegrationSpec(
        name="my_service",
        display_name="MyService",
        description="Connect to MyService API",
        oauth_provider="my_service",  # If using OAuth
        oauth_scopes=["read", "write"],
        credentials=[
            CredentialSpec(
                key="access_token",
                type=CredentialType.OAUTH2,
                description="MyService OAuth access token",
                env_var="MY_SERVICE_ACCESS_TOKEN",
                required=True,
                refresh_key="refresh_token",
                refresh_env_var="MY_SERVICE_REFRESH_TOKEN",
            ),
        ],
        setup_url_template="https://wrens.ie/integrations/my_service/setup?user={user_id}",
        docs_url="https://docs.wrens.ie/integrations/my_service",
    )
)
```

Register it in `wren_backend/src/wren_backend/integrations/__init__.py`:

```python
from .my_service import MY_SERVICE_SPEC
```

### Step 2: Create SDK Integration

Create `wren_src/src/wren/integrations/my_service.py`:

```python
"""MyService Integration."""

from __future__ import annotations

import os
from typing import ClassVar

from . import register_integration
from .base import BaseIntegration
from .docs import AuthType, IntegrationDocs, MethodDoc, ParamDoc


@register_integration("my_service")
class MyServiceIntegration(BaseIntegration):
    """MyService integration."""

    DOCS: ClassVar[IntegrationDocs] = IntegrationDocs(
        name="my_service",
        description="Connect to MyService to do X and Y.",
        auth_type=AuthType.OAUTH,  # Indicates OAuth is needed
        init_params=[
            ParamDoc(
                name="region",
                type="str",
                description="Service region",
                required=False,
                default="us-east-1",
            ),
        ],
        methods=[
            MethodDoc(
                name="get_items",
                description="Retrieve items from the service.",
                params=[
                    ParamDoc("category", "str", "Category to filter by"),
                    ParamDoc("limit", "int", "Max items", required=False, default="100"),
                ],
                returns="list[Item]",
                example='items = my_service.get_items("pending", limit=50)',
            ),
        ],
        example="""import wren

my_service = wren.integrations.my_service.init(region="eu-west-1")

@wren.on_schedule("0 */6 * * *")
def sync_items():
    items = my_service.get_items("pending")
    for item in items:
        process_item(item)""",
    )

    def _connect(self) -> None:
        """Establish connection using injected credentials."""
        # Credentials are injected as env vars by the backend
        token = os.environ.get("MY_SERVICE_ACCESS_TOKEN")
        if not token:
            raise RuntimeError("MyService credentials not configured")

        self._client = MyServiceClient(
            token=token,
            region=self._config.get("region", "us-east-1"),
        )

    def get_items(self, category: str, limit: int = 100) -> list:
        """Retrieve items from the service."""
        self._ensure_connected()
        return self._client.list_items(category=category, limit=limit)
```

Register it in `wren_src/src/wren/integrations/__init__.py`:

```python
from . import my_service  # noqa: E402, F401
```

### Step 3: Add Tests

Both SDK and backend should have tests for the new integration.

---

## Backend Registry Reference

### CredentialType

```python
class CredentialType(Enum):
    OAUTH2 = "oauth2"      # Requires OAuth 2.0 flow
    API_KEY = "api_key"    # Simple API key
    TOKEN = "token"        # Bearer token
    BASIC_AUTH = "basic_auth"  # Username/password
    CUSTOM = "custom"      # Integration-specific
```

### CredentialSpec

| Field | Type | Description |
|-------|------|-------------|
| `key` | `str` | Credential key in storage (e.g., "access_token") |
| `type` | `CredentialType` | Type of credential |
| `description` | `str` | Human-readable description |
| `env_var` | `str` | Environment variable name for injection |
| `required` | `bool` | Is this credential required? |
| `oauth_scopes` | `list[str]` | OAuth scopes (if applicable) |
| `refresh_key` | `str` | Key for refresh token |
| `refresh_env_var` | `str` | Env var for refresh token |

### IntegrationSpec

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Integration identifier (e.g., "gmail") |
| `display_name` | `str` | Human-readable name |
| `description` | `str` | What this integration does |
| `credentials` | `list[CredentialSpec]` | Required credentials |
| `oauth_provider` | `str` | OAuth provider name |
| `oauth_scopes` | `list[str]` | Combined OAuth scopes |
| `setup_url_template` | `str` | URL template with `{user_id}` |
| `docs_url` | `str` | Documentation URL |

---

## SDK Documentation Reference

### AuthType

Simplified indicator for the agent (detailed specs are in backend):

```python
class AuthType(Enum):
    NONE = "none"        # No auth needed (cron, messaging mock)
    OAUTH = "oauth"      # Requires OAuth flow
    API_KEY = "api_key"  # Requires API key
    TOKEN = "token"      # Requires bearer token
```

### IntegrationDocs

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Integration identifier |
| `description` | `str` | Brief description |
| `auth_type` | `AuthType` | What kind of auth is needed |
| `methods` | `list[MethodDoc]` | Available methods |
| `init_params` | `list[ParamDoc]` | Parameters for `.init()` |
| `example` | `str` | Complete usage example |

### MethodDoc

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Method name |
| `description` | `str` | What the method does |
| `params` | `list[ParamDoc]` | Method parameters |
| `returns` | `str` | Return type description |
| `example` | `str` | Short usage example |

### ParamDoc

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Parameter name |
| `type` | `str` | Type annotation |
| `description` | `str` | What the parameter does |
| `required` | `bool` | Is it required? (default: True) |
| `default` | `str` | Default value as string |

---

## Agent Loading Modes

The agent can discover integration documentation in three ways:

### Mode 1: All Docs Upfront

```python
from wren_agent.agent.core import create_agent

agent = create_agent(include_all_integration_docs=True)
```

**Best for:** Small number of integrations (~50 or fewer)

### Mode 2: Dynamic Loading

```python
agent = create_agent(include_dynamic_tools=True)
```

The agent gets tools: `list_integrations()` and `get_integration_docs(name)`

**Best for:** Large number of integrations (100+)

### Mode 3: Hybrid

```python
agent = create_agent(
    specific_integrations=["gmail", "slack", "cron"],
    include_dynamic_tools=True
)
```

**Best for:** Common integrations upfront, edge cases on demand

---

## Accessing Documentation

### From SDK

```python
import wren

# List available integrations
names = wren.integrations.list()  # ["cron", "gmail", "messaging", "slack"]

# Get docs for one integration
docs = wren.integrations.get_docs("gmail")
print(docs.name)         # "gmail"
print(docs.auth_type)    # AuthType.OAUTH
print(docs.methods)      # [MethodDoc(...), ...]

# Render as markdown
markdown = wren.integrations.render_docs()
markdown = wren.integrations.render_docs(["gmail", "slack"])  # Specific ones
```

### From Backend

```python
from wren_backend.integrations import get_integration, list_integrations

# List available integrations
names = list_integrations()  # ["cron", "gmail", "messaging", "slack"]

# Get integration spec
spec = get_integration("gmail")
print(spec.oauth_scopes)     # ["gmail.readonly", "gmail.send", ...]
print(spec.get_setup_url("user123"))  # "https://wrens.ie/integrations/gmail/setup?user=user123"

# Get env var mapping
mapping = spec.get_env_mapping()
# {"access_token": "GMAIL_ACCESS_TOKEN", "refresh_token": "GMAIL_REFRESH_TOKEN"}
```

---

## Testing

### SDK Tests

```bash
cd wren_src
uv run pytest tests/test_integration_docs.py -v
```

Validates:
- All integrations have DOCS
- DOCS has required fields (name, description, example)
- DOCS has at least one method
- auth_type is set correctly

### Backend Tests

```bash
cd wren_backend
uv run pytest tests/ -v
```

Validates:
- All integrations are registered
- Credential specs are complete
- Env var mapping works correctly

---

## Current Integrations

| Integration | SDK Auth Type | Backend OAuth Provider | Credentials |
|-------------|---------------|----------------------|-------------|
| gmail | `OAUTH` | google | access_token, refresh_token |
| slack | `OAUTH` | slack | access_token, refresh_token |
| cron | `NONE` | - | None (platform handles) |
| messaging | `NONE` | - | None (mock) |
