"""API endpoints for Wren Backend."""

from fastapi import APIRouter

from .validate import router as validate_router
from .deploy import router as deploy_router
from .deployments import router as deployments_router
from .runs import router as runs_router

api_router = APIRouter(prefix="/v1")
api_router.include_router(validate_router, tags=["integrations"])
api_router.include_router(deploy_router, tags=["scripts"])
api_router.include_router(deployments_router, tags=["deployments"])
api_router.include_router(runs_router, tags=["runs"])

__all__ = ["api_router"]
