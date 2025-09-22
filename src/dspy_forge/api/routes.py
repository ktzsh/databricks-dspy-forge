from fastapi import APIRouter
from dspy_forge.api.endpoints import workflows, execution

router = APIRouter()

router.include_router(workflows.router, prefix="/workflows", tags=["workflows"])
router.include_router(execution.router, prefix="/execution", tags=["execution"])
