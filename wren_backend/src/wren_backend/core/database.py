"""SQLAlchemy database models and engine setup."""

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from wren_backend.models.deployment import DeploymentStatus
from wren_backend.models.run import RunStatus


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for SQLAlchemy models."""

    pass


class DeploymentModel(Base):
    """SQLAlchemy model for deployments."""

    __tablename__ = "deployments"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    script_content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=DeploymentStatus.ACTIVE.value
    )
    triggers: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    integrations: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Relationship to runs
    runs: Mapped[list["RunModel"]] = relationship(
        "RunModel", back_populates="deployment", cascade="all, delete-orphan"
    )

    def get_triggers(self) -> list[dict[str, Any]]:
        """Parse triggers JSON."""
        return json.loads(self.triggers)

    def set_triggers(self, triggers: list[dict[str, Any]]) -> None:
        """Serialize triggers to JSON."""
        self.triggers = json.dumps(triggers)

    def get_integrations(self) -> list[str]:
        """Parse integrations JSON."""
        return json.loads(self.integrations)

    def set_integrations(self, integrations: list[str]) -> None:
        """Serialize integrations to JSON."""
        self.integrations = json.dumps(integrations)


class RunModel(Base):
    """SQLAlchemy model for runs."""

    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    deployment_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("deployments.id"), nullable=False, index=True
    )
    trigger_type: Mapped[str] = mapped_column(String(32), nullable=False)
    trigger_func: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=RunStatus.PENDING.value
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    exit_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stdout: Mapped[str] = mapped_column(Text, nullable=False, default="")
    stderr: Mapped[str] = mapped_column(Text, nullable=False, default="")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationship to deployment
    deployment: Mapped["DeploymentModel"] = relationship(
        "DeploymentModel", back_populates="runs"
    )


class Database:
    """Async database connection manager."""

    def __init__(self, db_url: str = "sqlite+aiosqlite:///wren.db"):
        self.engine = create_async_engine(db_url, echo=False)
        self.session_factory = async_sessionmaker(
            self.engine, expire_on_commit=False
        )

    async def create_tables(self) -> None:
        """Create all tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def close(self) -> None:
        """Close the database connection."""
        await self.engine.dispose()
