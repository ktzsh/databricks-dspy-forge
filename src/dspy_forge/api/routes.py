from fastapi import APIRouter
from dspy_forge.api.endpoints import workflows, execution, config

router = APIRouter()

router.include_router(workflows.router, prefix="/workflows", tags=["workflows"])
router.include_router(execution.router, prefix="/execution", tags=["execution"])
router.include_router(config.router, prefix="/config", tags=["config"])
