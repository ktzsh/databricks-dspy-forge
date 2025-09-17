from fastapi import APIRouter
from app.api.endpoints import workflows, execution, deployment

router = APIRouter()

router.include_router(workflows.router, prefix="/workflows", tags=["workflows"])
router.include_router(execution.router, prefix="/execution", tags=["execution"])
router.include_router(deployment.router, prefix="/deployment", tags=["deployment"])