"""In-memory fakes for Storage and CredentialStore.

These replace the Supabase-backed implementations so tests
can run without network access or credentials.
"""

from datetime import UTC, datetime

from wren_backend.core.credentials import CredentialStore
from wren_backend.core.storage import Storage, generate_id
from wren_backend.models.deployment import DeploymentStatus
from wren_backend.models.run import Run, RunStatus


class InMemoryStorage(Storage):
    """Dict-backed storage for testing — no Supabase required."""

    def __init__(self):
        # Skip parent __init__ (it sets up Supabase client placeholders)
        self._deployments: dict[str, dict] = {}
        self._runs: dict[str, dict] = {}

    # -- connection stubs --------------------------------------------------

    async def connect(self) -> None:
        pass

    async def close(self) -> None:
        pass

    # -- deployment CRUD ---------------------------------------------------

    async def create_deployment(self, user_id, name, script_content, triggers, integrations):
        deployment_id = generate_id("dep")
        now = datetime.now(UTC).isoformat()
        row = {
            "id": deployment_id,
            "user_id": user_id,
            "name": name,
            "script_content": script_content,
            "status": DeploymentStatus.ACTIVE.value,
            "triggers": [t.model_dump() for t in triggers],
            "integrations": integrations,
            "version": 1,
            "created_at": now,
            "updated_at": now,
        }
        self._deployments[deployment_id] = row
        return self._row_to_deployment(row)

    async def get_deployment(self, deployment_id):
        row = self._deployments.get(deployment_id)
        if row is None:
            return None
        return self._row_to_deployment(row)

    async def get_deployments_by_user(self, user_id):
        rows = [
            r for r in self._deployments.values()
            if r["user_id"] == user_id and r["status"] != DeploymentStatus.DELETED.value
        ]
        rows.sort(key=lambda r: r["created_at"], reverse=True)
        return [self._row_to_deployment(r) for r in rows]

    async def get_active_deployments(self):
        rows = [
            r for r in self._deployments.values()
            if r["status"] == DeploymentStatus.ACTIVE.value
        ]
        return [self._row_to_deployment(r) for r in rows]

    async def update_deployment_status(self, deployment_id, status):
        row = self._deployments.get(deployment_id)
        if row:
            row["status"] = status.value
            row["updated_at"] = datetime.now(UTC).isoformat()

    async def delete_deployment(self, deployment_id):
        await self.update_deployment_status(deployment_id, DeploymentStatus.DELETED)

    # -- run CRUD ----------------------------------------------------------

    async def create_run(self, deployment_id, user_id, trigger_type, trigger_func):
        run_id = generate_id("run")
        now = datetime.now(UTC).isoformat()
        row = {
            "id": run_id,
            "deployment_id": deployment_id,
            "user_id": user_id,
            "trigger_type": trigger_type,
            "trigger_func": trigger_func,
            "status": RunStatus.PENDING.value,
            "created_at": now,
            "started_at": None,
            "completed_at": None,
            "duration_ms": None,
            "exit_code": None,
            "stdout": "",
            "stderr": "",
            "error_message": None,
        }
        self._runs[run_id] = row
        return self._row_to_run(row)

    async def update_run_started(self, run_id):
        row = self._runs.get(run_id)
        if row:
            row["status"] = RunStatus.RUNNING.value
            row["started_at"] = datetime.now(UTC).isoformat()

    async def update_run_completed(self, run_id, status, exit_code, stdout, stderr, error_message=None):
        row = self._runs.get(run_id)
        if row:
            now = datetime.now(UTC)
            duration_ms = None
            if row.get("started_at"):
                started = datetime.fromisoformat(row["started_at"].replace("Z", "+00:00"))
                duration_ms = int((now - started).total_seconds() * 1000)
            row["status"] = status.value
            row["completed_at"] = now.isoformat()
            row["duration_ms"] = duration_ms
            row["exit_code"] = exit_code
            row["stdout"] = stdout
            row["stderr"] = stderr
            row["error_message"] = error_message

    async def get_run(self, run_id):
        row = self._runs.get(run_id)
        if row is None:
            return None
        return self._row_to_run(row)

    async def get_runs_by_deployment(self, deployment_id, limit=50):
        rows = [
            r for r in self._runs.values()
            if r["deployment_id"] == deployment_id
        ]
        rows.sort(key=lambda r: r["created_at"], reverse=True)
        return [self._row_to_run(r) for r in rows[:limit]]

    async def get_last_run(self, deployment_id):
        runs = await self.get_runs_by_deployment(deployment_id, limit=1)
        return runs[0] if runs else None


class InMemoryCredentialStore(CredentialStore):
    """Dict-backed credential store for testing — no Supabase required."""

    def __init__(self):
        # Skip parent __init__
        self._creds: dict[tuple[str, str], dict[str, str]] = {}

    async def connect(self) -> None:
        pass

    async def get_credentials(self, user_id, integration):
        return self._creds.get((user_id, integration))

    async def set_credentials(self, user_id, integration, credentials):
        self._creds[(user_id, integration)] = credentials

    async def delete_credentials(self, user_id, integration):
        self._creds.pop((user_id, integration), None)
