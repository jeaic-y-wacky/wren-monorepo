"""Supabase-based storage for scripts, deployments, and runs."""

import secrets
from datetime import UTC, datetime

import structlog
from supabase import Client

from wren_backend.core.supabase_client import (
    get_supabase_admin_client,
    get_supabase_client,
)
from wren_backend.models.deployment import (
    Deployment,
    DeploymentStatus,
    Trigger,
    TriggerConfig,
    TriggerType,
)
from wren_backend.models.run import Run, RunStatus

logger = structlog.get_logger()


def generate_id(prefix: str) -> str:
    """Generate a unique ID with the given prefix."""
    return f"{prefix}_{secrets.token_hex(8)}"


class Storage:
    """Async Supabase storage for Wren Backend."""

    def __init__(self):
        self._client: Client | None = None
        self._admin_client: Client | None = None

    async def connect(self) -> None:
        """Initialize the Supabase client connection."""
        self._client = get_supabase_client()
        self._admin_client = get_supabase_admin_client()
        logger.info("supabase_connected", has_admin=self._admin_client is not None)

    async def close(self) -> None:
        """Close the connection (no-op for Supabase)."""
        pass

    def _get_client(self, use_admin: bool = False) -> Client:
        """Get the appropriate Supabase client."""
        if use_admin and self._admin_client:
            return self._admin_client
        if not self._client:
            raise RuntimeError("Storage not connected")
        return self._client

    # Deployment operations

    async def create_deployment(
        self,
        user_id: str,
        name: str,
        script_content: str,
        triggers: list[Trigger],
        integrations: list[str],
    ) -> Deployment:
        """Create a new deployment."""
        deployment_id = generate_id("dep")
        now = datetime.now(UTC)

        data = {
            "id": deployment_id,
            "user_id": user_id,
            "name": name,
            "script_content": script_content,
            "status": DeploymentStatus.ACTIVE.value,
            "triggers": [t.model_dump() for t in triggers],
            "integrations": integrations,
            "version": 1,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }

        client = self._get_client(use_admin=True)
        result = client.table("deployments").insert(data).execute()

        if not result.data:
            raise RuntimeError("Failed to create deployment")

        return Deployment(
            id=deployment_id,
            user_id=user_id,
            name=name,
            script_content=script_content,
            status=DeploymentStatus.ACTIVE,
            triggers=triggers,
            integrations=integrations,
            created_at=now,
            updated_at=now,
            version=1,
        )

    async def get_deployment(self, deployment_id: str) -> Deployment | None:
        """Get a deployment by ID."""
        client = self._get_client(use_admin=True)
        result = (
            client.table("deployments")
            .select("*")
            .eq("id", deployment_id)
            .execute()
        )

        if not result.data:
            return None

        return self._row_to_deployment(result.data[0])

    async def get_deployments_by_user(self, user_id: str) -> list[Deployment]:
        """Get all deployments for a user."""
        client = self._get_client(use_admin=True)
        result = (
            client.table("deployments")
            .select("*")
            .eq("user_id", user_id)
            .neq("status", DeploymentStatus.DELETED.value)
            .order("created_at", desc=True)
            .execute()
        )

        return [self._row_to_deployment(row) for row in result.data]

    async def get_active_deployments(self) -> list[Deployment]:
        """Get all active deployments (for scheduler startup)."""
        client = self._get_client(use_admin=True)
        result = (
            client.table("deployments")
            .select("*")
            .eq("status", DeploymentStatus.ACTIVE.value)
            .execute()
        )

        return [self._row_to_deployment(row) for row in result.data]

    async def update_deployment_status(
        self, deployment_id: str, status: DeploymentStatus
    ) -> None:
        """Update a deployment's status."""
        client = self._get_client(use_admin=True)
        client.table("deployments").update(
            {"status": status.value, "updated_at": datetime.now(UTC).isoformat()}
        ).eq("id", deployment_id).execute()

    async def delete_deployment(self, deployment_id: str) -> None:
        """Soft delete a deployment."""
        await self.update_deployment_status(deployment_id, DeploymentStatus.DELETED)

    def _row_to_deployment(self, row: dict) -> Deployment:
        """Convert a Supabase row to a Deployment Pydantic model."""
        triggers_data = row.get("triggers") or []
        triggers = []
        for t in triggers_data:
            triggers.append(
                Trigger(
                    type=TriggerType(t["type"]),
                    func=t["func"],
                    config=TriggerConfig(**t["config"]),
                )
            )

        return Deployment(
            id=row["id"],
            user_id=row["user_id"],
            name=row["name"],
            script_content=row["script_content"],
            status=DeploymentStatus(row["status"]),
            triggers=triggers,
            integrations=row.get("integrations") or [],
            created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(row["updated_at"].replace("Z", "+00:00")),
            version=row.get("version", 1),
        )

    # Run operations

    async def create_run(
        self, deployment_id: str, user_id: str, trigger_type: str, trigger_func: str
    ) -> Run:
        """Create a new run record."""
        run_id = generate_id("run")
        now = datetime.now(UTC)

        data = {
            "id": run_id,
            "deployment_id": deployment_id,
            "user_id": user_id,
            "trigger_type": trigger_type,
            "trigger_func": trigger_func,
            "status": RunStatus.PENDING.value,
            "created_at": now.isoformat(),
        }

        client = self._get_client(use_admin=True)
        result = client.table("runs").insert(data).execute()

        if not result.data:
            raise RuntimeError("Failed to create run")

        return Run(
            id=run_id,
            deployment_id=deployment_id,
            trigger_type=trigger_type,
            trigger_func=trigger_func,
            status=RunStatus.PENDING,
            created_at=now,
        )

    async def update_run_started(self, run_id: str) -> None:
        """Mark a run as started."""
        client = self._get_client(use_admin=True)
        client.table("runs").update(
            {
                "status": RunStatus.RUNNING.value,
                "started_at": datetime.now(UTC).isoformat(),
            }
        ).eq("id", run_id).execute()

    async def update_run_completed(
        self,
        run_id: str,
        status: RunStatus,
        exit_code: int | None,
        stdout: str,
        stderr: str,
        error_message: str | None = None,
    ) -> None:
        """Mark a run as completed with results."""
        now = datetime.now(UTC)

        # Get the run to calculate duration
        client = self._get_client(use_admin=True)
        result = client.table("runs").select("started_at").eq("id", run_id).execute()

        duration_ms = None
        if result.data and result.data[0].get("started_at"):
            started_at = datetime.fromisoformat(
                result.data[0]["started_at"].replace("Z", "+00:00")
            )
            duration_ms = int((now - started_at).total_seconds() * 1000)

        client.table("runs").update(
            {
                "status": status.value,
                "completed_at": now.isoformat(),
                "duration_ms": duration_ms,
                "exit_code": exit_code,
                "stdout": stdout,
                "stderr": stderr,
                "error_message": error_message,
            }
        ).eq("id", run_id).execute()

    async def get_run(self, run_id: str) -> Run | None:
        """Get a run by ID."""
        client = self._get_client(use_admin=True)
        result = client.table("runs").select("*").eq("id", run_id).execute()

        if not result.data:
            return None

        return self._row_to_run(result.data[0])

    async def get_runs_by_deployment(
        self, deployment_id: str, limit: int = 50
    ) -> list[Run]:
        """Get runs for a deployment, most recent first."""
        client = self._get_client(use_admin=True)
        result = (
            client.table("runs")
            .select("*")
            .eq("deployment_id", deployment_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

        return [self._row_to_run(row) for row in result.data]

    async def get_last_run(self, deployment_id: str) -> Run | None:
        """Get the most recent run for a deployment."""
        runs = await self.get_runs_by_deployment(deployment_id, limit=1)
        return runs[0] if runs else None

    def _row_to_run(self, row: dict) -> Run:
        """Convert a Supabase row to a Run Pydantic model."""
        return Run(
            id=row["id"],
            deployment_id=row["deployment_id"],
            trigger_type=row["trigger_type"],
            trigger_func=row.get("trigger_func") or "",
            status=RunStatus(row["status"]),
            started_at=(
                datetime.fromisoformat(row["started_at"].replace("Z", "+00:00"))
                if row.get("started_at")
                else None
            ),
            completed_at=(
                datetime.fromisoformat(row["completed_at"].replace("Z", "+00:00"))
                if row.get("completed_at")
                else None
            ),
            duration_ms=row.get("duration_ms"),
            exit_code=row.get("exit_code"),
            stdout=row.get("stdout") or "",
            stderr=row.get("stderr") or "",
            error_message=row.get("error_message"),
        )
