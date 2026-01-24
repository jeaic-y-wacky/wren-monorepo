"""SQLAlchemy-based storage for scripts, deployments, and runs."""

import json
import secrets
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from wren_backend.core.database import Database, DeploymentModel, RunModel
from wren_backend.models.deployment import (
    Deployment,
    DeploymentStatus,
    Trigger,
    TriggerConfig,
    TriggerType,
)
from wren_backend.models.run import Run, RunStatus


def generate_id(prefix: str) -> str:
    """Generate a unique ID with the given prefix."""
    return f"{prefix}_{secrets.token_hex(8)}"


class Storage:
    """Async SQLAlchemy storage for Wren Backend."""

    def __init__(self, db_url: str = "sqlite+aiosqlite:///wren.db"):
        self._db = Database(db_url)

    async def connect(self) -> None:
        """Connect to the database and create tables if needed."""
        await self._db.create_tables()

    async def close(self) -> None:
        """Close the database connection."""
        await self._db.close()

    def _session(self) -> AsyncSession:
        """Get a new database session."""
        return self._db.session_factory()

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

        db_deployment = DeploymentModel(
            id=deployment_id,
            user_id=user_id,
            name=name,
            script_content=script_content,
            status=DeploymentStatus.ACTIVE.value,
            triggers=json.dumps([t.model_dump() for t in triggers]),
            integrations=json.dumps(integrations),
            created_at=now,
            updated_at=now,
            version=1,
        )

        async with self._session() as session:
            session.add(db_deployment)
            await session.commit()

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
        async with self._session() as session:
            result = await session.execute(
                select(DeploymentModel).where(DeploymentModel.id == deployment_id)
            )
            db_deployment = result.scalar_one_or_none()
            if not db_deployment:
                return None
            return self._model_to_deployment(db_deployment)

    async def get_deployments_by_user(self, user_id: str) -> list[Deployment]:
        """Get all deployments for a user."""
        async with self._session() as session:
            result = await session.execute(
                select(DeploymentModel)
                .where(DeploymentModel.user_id == user_id)
                .where(DeploymentModel.status != DeploymentStatus.DELETED.value)
                .order_by(DeploymentModel.created_at.desc())
            )
            db_deployments = result.scalars().all()
            return [self._model_to_deployment(d) for d in db_deployments]

    async def get_active_deployments(self) -> list[Deployment]:
        """Get all active deployments (for scheduler startup)."""
        async with self._session() as session:
            result = await session.execute(
                select(DeploymentModel).where(
                    DeploymentModel.status == DeploymentStatus.ACTIVE.value
                )
            )
            db_deployments = result.scalars().all()
            return [self._model_to_deployment(d) for d in db_deployments]

    async def update_deployment_status(
        self, deployment_id: str, status: DeploymentStatus
    ) -> None:
        """Update a deployment's status."""
        async with self._session() as session:
            result = await session.execute(
                select(DeploymentModel).where(DeploymentModel.id == deployment_id)
            )
            db_deployment = result.scalar_one_or_none()
            if db_deployment:
                db_deployment.status = status.value
                db_deployment.updated_at = datetime.now(UTC)
                await session.commit()

    async def delete_deployment(self, deployment_id: str) -> None:
        """Soft delete a deployment."""
        await self.update_deployment_status(deployment_id, DeploymentStatus.DELETED)

    def _model_to_deployment(self, db_model: DeploymentModel) -> Deployment:
        """Convert a database model to a Deployment Pydantic model."""
        triggers_data = json.loads(db_model.triggers)
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
            id=db_model.id,
            user_id=db_model.user_id,
            name=db_model.name,
            script_content=db_model.script_content,
            status=DeploymentStatus(db_model.status),
            triggers=triggers,
            integrations=json.loads(db_model.integrations),
            created_at=db_model.created_at,
            updated_at=db_model.updated_at,
            version=db_model.version,
        )

    # Run operations

    async def create_run(
        self, deployment_id: str, trigger_type: str, trigger_func: str
    ) -> Run:
        """Create a new run record."""
        run_id = generate_id("run")

        db_run = RunModel(
            id=run_id,
            deployment_id=deployment_id,
            trigger_type=trigger_type,
            trigger_func=trigger_func,
            status=RunStatus.PENDING.value,
        )

        async with self._session() as session:
            session.add(db_run)
            await session.commit()

        return Run(
            id=run_id,
            deployment_id=deployment_id,
            trigger_type=trigger_type,
            trigger_func=trigger_func,
            status=RunStatus.PENDING,
        )

    async def update_run_started(self, run_id: str) -> None:
        """Mark a run as started."""
        async with self._session() as session:
            result = await session.execute(
                select(RunModel).where(RunModel.id == run_id)
            )
            db_run = result.scalar_one_or_none()
            if db_run:
                db_run.status = RunStatus.RUNNING.value
                db_run.started_at = datetime.now(UTC)
                await session.commit()

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

        async with self._session() as session:
            result = await session.execute(
                select(RunModel).where(RunModel.id == run_id)
            )
            db_run = result.scalar_one_or_none()
            if db_run:
                duration_ms = None
                if db_run.started_at:
                    started_at = db_run.started_at
                    if started_at.tzinfo is None:
                        started_at = started_at.replace(tzinfo=UTC)
                    duration_ms = int((now - started_at).total_seconds() * 1000)

                db_run.status = status.value
                db_run.completed_at = now
                db_run.duration_ms = duration_ms
                db_run.exit_code = exit_code
                db_run.stdout = stdout
                db_run.stderr = stderr
                db_run.error_message = error_message
                await session.commit()

    async def get_run(self, run_id: str) -> Run | None:
        """Get a run by ID."""
        async with self._session() as session:
            result = await session.execute(
                select(RunModel).where(RunModel.id == run_id)
            )
            db_run = result.scalar_one_or_none()
            if not db_run:
                return None
            return self._model_to_run(db_run)

    async def get_runs_by_deployment(
        self, deployment_id: str, limit: int = 50
    ) -> list[Run]:
        """Get runs for a deployment, most recent first."""
        async with self._session() as session:
            result = await session.execute(
                select(RunModel)
                .where(RunModel.deployment_id == deployment_id)
                .order_by(RunModel.started_at.desc())
                .limit(limit)
            )
            db_runs = result.scalars().all()
            return [self._model_to_run(r) for r in db_runs]

    async def get_last_run(self, deployment_id: str) -> Run | None:
        """Get the most recent run for a deployment."""
        runs = await self.get_runs_by_deployment(deployment_id, limit=1)
        return runs[0] if runs else None

    def _model_to_run(self, db_model: RunModel) -> Run:
        """Convert a database model to a Run Pydantic model."""
        return Run(
            id=db_model.id,
            deployment_id=db_model.deployment_id,
            trigger_type=db_model.trigger_type,
            trigger_func=db_model.trigger_func,
            status=RunStatus(db_model.status),
            started_at=db_model.started_at,
            completed_at=db_model.completed_at,
            duration_ms=db_model.duration_ms,
            exit_code=db_model.exit_code,
            stdout=db_model.stdout or "",
            stderr=db_model.stderr or "",
            error_message=db_model.error_message,
        )
