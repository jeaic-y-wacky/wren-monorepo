"""APScheduler integration for cron triggers."""

import asyncio
from datetime import datetime
from typing import Callable

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from wren_backend.models.deployment import Deployment, TriggerType

logger = structlog.get_logger()


class Scheduler:
    """Manages scheduled execution of deployments using APScheduler."""

    def __init__(self):
        self._scheduler = AsyncIOScheduler()
        self._run_callback: Callable[[str, str, str], None] | None = None

    def set_run_callback(
        self, callback: Callable[[str, str, str], None]
    ) -> None:
        """Set the callback to execute when a scheduled job fires.

        Args:
            callback: Async function(deployment_id, trigger_type, func_name)
        """
        self._run_callback = callback

    def start(self) -> None:
        """Start the scheduler."""
        if not self._scheduler.running:
            self._scheduler.start()
            logger.info("scheduler_started")

    def shutdown(self, wait: bool = True) -> None:
        """Shutdown the scheduler."""
        if self._scheduler.running:
            self._scheduler.shutdown(wait=wait)
            logger.info("scheduler_shutdown")

    def register_deployment(self, deployment: Deployment) -> int:
        """Register all triggers for a deployment.

        Returns:
            Number of triggers registered
        """
        registered = 0
        log = logger.bind(deployment_id=deployment.id)

        for trigger in deployment.triggers:
            if trigger.type == TriggerType.SCHEDULE:
                cron_expr = trigger.config.cron
                if not cron_expr:
                    log.warning("missing_cron_expression", func=trigger.func)
                    continue

                job_id = f"{deployment.id}:{trigger.func}"
                timezone = trigger.config.timezone or "UTC"

                try:
                    # Parse cron expression (minute hour day month day_of_week)
                    cron_parts = cron_expr.split()
                    if len(cron_parts) == 5:
                        cron_trigger = CronTrigger(
                            minute=cron_parts[0],
                            hour=cron_parts[1],
                            day=cron_parts[2],
                            month=cron_parts[3],
                            day_of_week=cron_parts[4],
                            timezone=timezone,
                        )

                        self._scheduler.add_job(
                            self._execute_job,
                            trigger=cron_trigger,
                            id=job_id,
                            args=[deployment.id, "schedule", trigger.func],
                            replace_existing=True,
                            name=f"{deployment.name}:{trigger.func}",
                        )

                        log.info(
                            "trigger_registered",
                            job_id=job_id,
                            cron=cron_expr,
                            timezone=timezone,
                            func=trigger.func,
                        )
                        registered += 1
                    else:
                        log.warning(
                            "invalid_cron_expression",
                            cron=cron_expr,
                            func=trigger.func,
                        )
                except Exception as e:
                    log.exception(
                        "failed_to_register_trigger",
                        error=str(e),
                        func=trigger.func,
                    )

            # TODO: Handle other trigger types (email, webhook)

        return registered

    def unregister_deployment(self, deployment_id: str) -> int:
        """Remove all scheduled jobs for a deployment.

        Returns:
            Number of jobs removed
        """
        removed = 0
        for job in self._scheduler.get_jobs():
            if job.id.startswith(f"{deployment_id}:"):
                self._scheduler.remove_job(job.id)
                logger.info("trigger_unregistered", job_id=job.id)
                removed += 1
        return removed

    def get_next_run_time(self, deployment_id: str) -> datetime | None:
        """Get the next scheduled run time for a deployment."""
        next_time = None
        for job in self._scheduler.get_jobs():
            if job.id.startswith(f"{deployment_id}:"):
                if job.next_run_time:
                    if next_time is None or job.next_run_time < next_time:
                        next_time = job.next_run_time
        return next_time

    async def _execute_job(
        self, deployment_id: str, trigger_type: str, func_name: str
    ) -> None:
        """Called by APScheduler when a job fires."""
        logger.info(
            "job_triggered",
            deployment_id=deployment_id,
            trigger_type=trigger_type,
            func_name=func_name,
        )

        if self._run_callback:
            # Run in background to not block scheduler
            asyncio.create_task(
                self._run_callback(deployment_id, trigger_type, func_name)
            )
        else:
            logger.warning("no_run_callback_set", deployment_id=deployment_id)
