"""FastAPI application entry point for Wren Backend."""

import asyncio
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from wren_backend.api import api_router
from wren_backend.api.deps import init_dependencies
from wren_backend.core.credentials import CredentialStore
from wren_backend.core.executor import Executor
from wren_backend.core.scheduler import Scheduler
from wren_backend.core.storage import Storage
from wren_backend.models.errors import (
    AgentFixableError,
    ErrorDetail,
    ErrorResponse,
    InternalError,
    UserFacingConfigError,
)

# Configure structlog
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Global instances
storage: Storage | None = None
scheduler: Scheduler | None = None
executor: Executor | None = None
credential_store: CredentialStore | None = None


async def execute_run(
    deployment_id: str, trigger_type: str, func_name: str
) -> None:
    """Execute a scheduled run. Called by the scheduler."""
    log = logger.bind(
        deployment_id=deployment_id,
        trigger_type=trigger_type,
        func_name=func_name,
    )

    if not storage or not executor or not credential_store:
        log.error("services_not_initialized")
        return

    # Get deployment
    deployment = await storage.get_deployment(deployment_id)
    if not deployment:
        log.error("deployment_not_found")
        return

    # Create run record with user_id for RLS
    run = await storage.create_run(
        deployment_id, deployment.user_id, trigger_type, func_name
    )
    log = log.bind(run_id=run.id)
    log.info("run_created")

    # Mark as started
    await storage.update_run_started(run.id)

    # Get credentials as env vars
    env = await credential_store.get_env_for_execution(
        deployment.user_id, deployment.integrations
    )
    log.info(
        "credentials_loaded",
        user_id=deployment.user_id,
        integrations=deployment.integrations,
        env_keys=list(env.keys()),
    )

    # Execute
    log.info("executing_script")
    result = await executor.execute(
        script_content=deployment.script_content,
        func_name=func_name,
        env=env,
    )

    # Update run with results
    await storage.update_run_completed(
        run_id=run.id,
        status=result.status,
        exit_code=result.exit_code,
        stdout=result.stdout,
        stderr=result.stderr,
        error_message=result.error_message,
    )

    log.info(
        "run_completed",
        status=result.status.value,
        exit_code=result.exit_code,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    global storage, scheduler, executor, credential_store

    logger.info("starting_wren_backend")

    # Initialize services
    storage = Storage()
    await storage.connect()
    logger.info("storage_connected")

    credential_store = CredentialStore()
    await credential_store.connect()
    logger.info("credential_store_connected")

    scheduler = Scheduler()
    executor = Executor()

    # Set up scheduler callback
    scheduler.set_run_callback(execute_run)

    # Initialize dependencies for FastAPI
    init_dependencies(storage, scheduler, credential_store)

    # Load existing deployments into scheduler
    active_deployments = await storage.get_active_deployments()
    for deployment in active_deployments:
        scheduler.register_deployment(deployment)
    logger.info("loaded_deployments", count=len(active_deployments))

    # Start scheduler
    scheduler.start()

    yield

    # Shutdown
    logger.info("shutting_down_wren_backend")
    scheduler.shutdown(wait=True)
    await storage.close()
    logger.info("shutdown_complete")


# Create FastAPI app
app = FastAPI(
    title="Wren Backend",
    description="Execution platform for agent-written scripts",
    version="0.1.0",
    lifespan=lifespan,
)


# Exception handlers
@app.exception_handler(AgentFixableError)
async def agent_fixable_error_handler(
    request: Request, exc: AgentFixableError
) -> JSONResponse:
    """Handle agent-fixable errors."""
    return JSONResponse(
        status_code=400,
        content=ErrorResponse(
            error=ErrorDetail(
                type="AgentFixableError",
                code=exc.code,
                message=exc.message,
            )
        ).model_dump(),
    )


@app.exception_handler(UserFacingConfigError)
async def user_facing_error_handler(
    request: Request, exc: UserFacingConfigError
) -> JSONResponse:
    """Handle user-facing config errors."""
    return JSONResponse(
        status_code=400,
        content=ErrorResponse(
            error=ErrorDetail(
                type="UserFacingConfigError",
                code=exc.code,
                message=exc.message,
                action_url=exc.action_url,
                docs_url=exc.docs_url,
                integration=exc.integration,
            )
        ).model_dump(),
    )


@app.exception_handler(InternalError)
async def internal_error_handler(
    request: Request, exc: InternalError
) -> JSONResponse:
    """Handle internal errors (log but don't expose details)."""
    logger.exception(
        "internal_error",
        code=exc.code,
        message=exc.message,
        cause=str(exc.cause) if exc.cause else None,
    )
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error=ErrorDetail(
                type="InternalError",
                code="INTERNAL_ERROR",
                message="An internal error occurred. Please try again later.",
            )
        ).model_dump(),
    )


# CORS — allow the frontend origin(s)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "0.1.0"}


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "Wren Backend",
        "version": "0.1.0",
        "docs_url": "/docs",
        "openapi_url": "/openapi.json",
    }


def main():
    """Run the server using uvicorn."""
    import uvicorn

    uvicorn.run(
        "wren_backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    main()
