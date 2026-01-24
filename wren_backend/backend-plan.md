# Wren Backend Implementation Plan

## Overview

The Wren Backend is the execution platform where agent-written scripts are deployed and run. It handles validation of platform requirements, script storage, scheduled execution, credential management, and observability.

**Domain:** wrens.ie

### Architecture Principle

> "Agent writes code, platform handles infrastructure"

The backend receives validated scripts from agents and manages everything needed to run them reliably: scheduling, secrets, sandboxing, logging, and error handling.

---

## System Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                              Agent / CLI                                  │
│                                                                          │
│   wren test script.py     →  Import script, surface import-time errors   │
│   wren validate script.py →  Extract metadata, validate integrations     │
│   wren deploy script.py   →  Send script + metadata to backend           │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                           Wren Backend (wrens.ie)                         │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                            API Layer                                 │ │
│  │                                                                      │ │
│  │   POST /v1/integrations/validate - Check integration configuration    │ │
│  │   POST /v1/scripts/deploy        - Store script, register triggers    │ │
│  │   GET  /v1/deployments - List user's deployments                     │ │
│  │   GET  /v1/runs        - Execution history and logs                  │ │
│  │                                                                      │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                      │                                    │
│         ┌────────────────────────────┼────────────────────────┐          │
│         ▼                            ▼                        ▼          │
│  ┌─────────────┐          ┌─────────────────┐        ┌──────────────┐   │
│  │   Script    │          │    Scheduler    │        │  Credential  │   │
│  │   Storage   │          │                 │        │    Store     │   │
│  │             │          │  APScheduler /  │        │              │   │
│  │  SQLite /   │          │  Celery Beat    │        │  Encrypted   │   │
│  │  PostgreSQL │          │                 │        │  secrets     │   │
│  └─────────────┘          └─────────────────┘        └──────────────┘   │
│         │                            │                        │          │
│         └────────────────────────────┼────────────────────────┘          │
│                                      ▼                                    │
│                           ┌─────────────────┐                            │
│                           │    Executor     │                            │
│                           │                 │                            │
│                           │  Sandboxed      │                            │
│                           │  Python runtime │                            │
│                           └─────────────────┘                            │
│                                      │                                    │
│                                      ▼                                    │
│                           ┌─────────────────┐                            │
│                           │  Observability  │                            │
│                           │                 │                            │
│                           │  Logs, traces,  │                            │
│                           │  run history    │                            │
│                           └─────────────────┘                            │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## API Design

### POST /v1/integrations/validate

Validates that the platform can support a script's integrations. Receives **integrations only**, not the script itself.

**Request:**
```json
{
  "integrations": ["gmail", "slack"]
}
```

**Response (success):**
```json
{
  "valid": true,
  "warnings": []
}
```

**Response (failure):**
```json
{
  "valid": false,
  "errors": [
    {
      "type": "UserFacingConfigError",
      "code": "INTEGRATION_NOT_CONFIGURED",
      "integration": "gmail",
      "message": "Gmail integration not configured",
      "action_url": "https://wrens.ie/integrations/gmail/setup",
      "docs_url": "https://docs.wrens.ie/integrations/gmail"
    }
  ]
}
```

**Validation checks:**
- Required integrations are configured and authorized
- OAuth tokens are valid and not expired
- User has necessary permissions
- Quotas not exceeded
- Trigger configurations are validated during deploy

---

### POST /v1/scripts/deploy

Deploys a validated script to the platform.

**Request:**
```
Content-Type: application/json

{
  "script": "<python script content>",
  "metadata": {
    "integrations": ["gmail", "slack"],
    "triggers": [
      {"type": "schedule", "func": "daily_report", "config": {"cron": "0 9 * * *"}}
    ],
    "schedules": [{"cron": "0 9 * * *", "func_name": "daily_report"}]
  },
  "name": "optional-deployment-name"
}
```

**Response:**
```json
{
  "deployment_id": "dep_abc123",
  "status": "active",
  "triggers_registered": 2,
  "created_at": "2024-12-08T10:30:00Z",
  "next_run": "2024-12-09T09:00:00Z"
}
```

**Deployment process:**
1. Store script content with version
2. Parse metadata and validate again (defensive)
3. Register triggers with scheduler
4. Return deployment confirmation

---

### GET /v1/deployments

List user's deployments.

**Response:**
```json
{
  "deployments": [
    {
      "id": "dep_abc123",
      "name": "daily_report",
      "status": "active",
      "triggers": 2,
      "last_run": "2024-12-08T09:00:00Z",
      "next_run": "2024-12-09T09:00:00Z",
      "created_at": "2024-12-01T10:30:00Z"
    }
  ]
}
```

---

### GET /v1/deployments/{id}/runs

Get execution history for a deployment.

**Response:**
```json
{
  "runs": [
    {
      "run_id": "run_xyz789",
      "deployment_id": "dep_abc123",
      "trigger": "schedule",
      "status": "success",
      "started_at": "2024-12-08T09:00:00Z",
      "completed_at": "2024-12-08T09:00:15Z",
      "duration_ms": 15000,
      "logs_url": "/v1/runs/run_xyz789/logs"
    }
  ]
}
```

---

## Error Taxonomy

All errors follow a consistent classification:

| Error Type | Visible To | Example | Action |
|------------|------------|---------|--------|
| `AgentFixableError` | Agent | Syntax error, missing function | Agent fixes code locally |
| `UserFacingConfigError` | User | Missing OAuth, no permissions | User configures via UI |
| `InternalError` | Logged only | Database failure, scheduler crash | Ops team investigates |

**Error response format:**
```json
{
  "error": {
    "type": "UserFacingConfigError",
    "code": "OAUTH_TOKEN_EXPIRED",
    "message": "Gmail OAuth token has expired",
    "action_url": "https://wrens.ie/integrations/gmail/reauthorize",
    "correlation_id": "corr_abc123"
  }
}
```

---

## Implementation Phases

### Phase 1: Minimal Viable Backend

**Goal:** Deploy a script with `@wren.on_schedule`, see it execute.

| Component | Implementation | Notes |
|-----------|---------------|-------|
| API Server | FastAPI | Async, good OpenAPI docs |
| Storage | SQLite | Simple start, migrate later |
| Scheduler | APScheduler | In-process, sufficient for MVP |
| Executor | subprocess | Basic isolation |
| Auth | API keys | Simple token auth |

**Deliverables:**
- [ ] FastAPI app with `/v1/integrations/validate` and `/v1/scripts/deploy`
- [ ] SQLite storage for scripts and metadata
- [ ] APScheduler integration for cron triggers
- [ ] Basic subprocess executor
- [ ] CLI commands: `wren deploy`, `wren status`

---

### Phase 2: Error Handling & Observability

**Goal:** Structured errors, execution logs, run tracing.

| Component | Implementation | Notes |
|-----------|---------------|-------|
| Error taxonomy | Custom exceptions | Map to response types |
| Logging | structlog | JSON logs with correlation IDs |
| Run storage | SQLite table | stdout, stderr, status |
| Traces | Run IDs | Propagate through execution |

**Deliverables:**
- [ ] Error classes: `AgentFixableError`, `UserFacingConfigError`, `InternalError`
- [ ] Correlation ID middleware
- [ ] Execution log capture and storage
- [ ] `/v1/runs/{id}/logs` endpoint

---

### Phase 3: Credentials & Integrations

**Goal:** Securely store and inject credentials for integrations.

| Component | Implementation | Notes |
|-----------|---------------|-------|
| Credential store | Encrypted SQLite / Vault | Start simple |
| OAuth flows | FastAPI routes | Gmail, Slack |
| Integration validation | Check on validate | Before deploy |
| Secret injection | Environment variables | Sandboxed |

**Deliverables:**
- [ ] Credential storage with encryption at rest
- [ ] OAuth setup endpoints (`/integrations/gmail/setup`)
- [ ] Validation checks for configured integrations
- [ ] Secure credential injection to executor

---

### Phase 4: Email Triggers

**Goal:** Trigger scripts based on incoming emails.

| Component | Implementation | Notes |
|-----------|---------------|-------|
| Email ingestion | IMAP polling / webhook | Start with polling |
| Filter matching | Rule engine | Subject, from, body patterns |
| Email object | Pydantic model | Passed to handler function |

**Deliverables:**
- [ ] Email polling service
- [ ] Filter matching for `@wren.on_email` triggers
- [ ] Email object injection to handlers

---

### Phase 5: Production Hardening

**Goal:** Security, sandboxing, scalability.

| Component | Implementation | Notes |
|-----------|---------------|-------|
| Sandboxing | nsjail / bubblewrap | Secure isolation |
| Database | PostgreSQL | Scale beyond SQLite |
| Task queue | Celery + Redis | Distributed execution |
| Rate limiting | Redis | Per-user limits |
| Monitoring | Prometheus + Grafana | Metrics, alerts |

---

## File Structure

```
src/
├── wren/                      # Existing SDK (unchanged)
│   ├── __init__.py
│   ├── ai.py
│   ├── decorators.py
│   ├── registry.py
│   └── cli.py
│
└── wren_backend/              # New backend package
    ├── __init__.py
    ├── main.py                # FastAPI app entry point
    │
    ├── api/                   # API endpoints
    │   ├── __init__.py
    │   ├── validate.py        # POST /v1/integrations/validate
    │   ├── deploy.py          # POST /v1/scripts/deploy
    │   ├── deployments.py     # GET /v1/deployments
    │   └── runs.py            # GET /v1/runs
    │
    ├── core/                  # Business logic
    │   ├── __init__.py
    │   ├── storage.py         # Script & metadata persistence
    │   ├── scheduler.py       # Trigger registration
    │   ├── executor.py        # Script execution
    │   ├── credentials.py     # Secret management
    │   └── metadata.py        # Metadata extraction (reuse SDK)
    │
    ├── models/                # Data models
    │   ├── __init__.py
    │   ├── deployment.py      # Deployment model
    │   ├── run.py             # Execution run model
    │   └── errors.py          # Error taxonomy
    │
    └── integrations/          # Integration-specific logic
        ├── __init__.py
        ├── gmail.py           # Gmail OAuth + validation
        └── slack.py           # Slack OAuth + validation
```

---

## Tech Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| API Framework | FastAPI | Async, auto OpenAPI docs, Pydantic integration |
| Database | SQLite → PostgreSQL | Start simple, scale later |
| Scheduler | APScheduler | In-process, good cron support |
| Task Queue | (none) → Celery + Redis | Add when needed for scale |
| Sandboxing | subprocess → nsjail | Security hardening later |
| Secrets | .env → HashiCorp Vault | Production security |
| Logging | structlog | Structured JSON logs |
| Monitoring | (none) → Prometheus | Production observability |

---

## CLI Updates

Extend the existing `wren` CLI:

```bash
# Existing (local)
wren test script.py       # Syntax, types, cron validation
wren validate script.py   # Extract metadata, display locally

# New (backend interaction)
wren validate script.py --remote   # Send metadata to backend for platform validation
wren deploy script.py              # Deploy to backend
wren status                        # List deployments
wren logs <deployment_id>          # View execution logs
wren undeploy <deployment_id>      # Remove deployment
```

---

## Agent Workflow (End-to-End)

```
Agent receives task: "Send me a daily summary of my emails at 9am"
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │  Agent writes script:         │
                    │                               │
                    │  @wren.on_schedule("0 9 * *") │
                    │  def daily_summary():         │
                    │      emails = gmail.inbox()   │
                    │      summary = wren.ai(...)   │
                    │      gmail.send(summary)      │
                    │                               │
                    └───────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │  $ wren test script.py        │
                    │  ✓ Syntax valid               │
                    │  ✓ Cron expression valid      │
                    │  ✓ Functions defined          │
                    └───────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │  $ wren validate --remote     │
                    │                               │
                    │  POST /v1/integrations/validate            │
                    │  {"integrations": ["gmail"]}  │
                    │                               │
                    │  ✓ Gmail configured           │
                    │  ✓ OAuth token valid          │
                    └───────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │  $ wren deploy script.py      │
                    │                               │
                    │  POST /v1/scripts/deploy              │
                    │  <script + metadata>          │
                    │                               │
                    │  ✓ Deployed: dep_abc123       │
                    │  ✓ Next run: 9:00 AM tomorrow │
                    └───────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │  Platform executes daily      │
                    │                               │
                    │  Agent can check:             │
                    │  $ wren logs dep_abc123       │
                    └───────────────────────────────┘
```

---

## Next Steps

1. **Set up backend package structure** - Create `src/wren_backend/` with FastAPI skeleton
2. **Implement `/v1/integrations/validate`** - Receive integrations, check configuration (stub for now)
3. **Implement `/v1/scripts/deploy`** - Store script, register with APScheduler
4. **Basic executor** - Run scripts in subprocess, capture output
5. **Extend CLI** - Add `wren deploy`, `wren status` commands
6. **Integration test** - End-to-end: write script → deploy → execute → view logs
