from fastapi import APIRouter, HTTPException, status
from typing import List, Dict, Any
from pydantic import BaseModel

from app.models.workflow import Workflow
from app.services.workflow_service import workflow_service
from app.services.validation_service import WorkflowValidationError
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


class WorkflowCreateRequest(BaseModel):
    name: str
    description: str = ""
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []


class WorkflowUpdateRequest(BaseModel):
    name: str = None
    description: str = None
    nodes: List[Dict[str, Any]] = None
    edges: List[Dict[str, Any]] = None


@router.post("/", response_model=Workflow, status_code=status.HTTP_201_CREATED)
async def create_workflow(workflow_request: WorkflowCreateRequest):
    """Create a new workflow"""
    try:
        logger.info(f"Creating workflow: {workflow_request.name}")
        workflow_data = workflow_request.model_dump()
        logger.debug(f"Workflow data: {workflow_data}")
        
        workflow = await workflow_service.create_workflow(workflow_data)
        logger.info(f"Successfully created workflow with ID: {workflow.id}")
        return workflow
    except WorkflowValidationError as e:
        logger.warning(f"Workflow validation failed: {str(e)}")
        logger.debug(f"Failed workflow data: {workflow_request.model_dump()}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to create workflow: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create workflow: {str(e)}"
        )


@router.get("/", response_model=List[Workflow])
async def list_workflows():
    """List all workflows"""
    try:
        workflows = await workflow_service.list_workflows()
        return workflows
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list workflows: {str(e)}"
        )


@router.get("/{workflow_id}", response_model=Workflow)
async def get_workflow(workflow_id: str):
    """Get a specific workflow by ID"""
    workflow = await workflow_service.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found"
        )
    return workflow


@router.put("/{workflow_id}", response_model=Workflow)
async def update_workflow(workflow_id: str, workflow_request: WorkflowUpdateRequest):
    """Update an existing workflow"""
    try:
        logger.info(f"Updating workflow: {workflow_id}")
        
        # Get existing workflow
        existing_workflow = await workflow_service.get_workflow(workflow_id)
        if not existing_workflow:
            logger.warning(f"Workflow not found for update: {workflow_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found"
            )
        
        # Merge updates with existing data
        workflow_data = existing_workflow.model_dump()
        update_data = workflow_request.model_dump(exclude_unset=True)
        workflow_data.update(update_data)
        logger.debug(f"Updated workflow data: {workflow_data}")
        
        workflow = await workflow_service.update_workflow(workflow_id, workflow_data)
        logger.info(f"Successfully updated workflow: {workflow_id}")
        return workflow
    except WorkflowValidationError as e:
        logger.warning(f"Workflow validation failed during update: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to update workflow {workflow_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update workflow: {str(e)}"
        )


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(workflow_id: str):
    """Delete a workflow"""
    success = await workflow_service.delete_workflow(workflow_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found"
        )


@router.post("/{workflow_id}/duplicate", response_model=Workflow, status_code=status.HTTP_201_CREATED)
async def duplicate_workflow(workflow_id: str, new_name: str = None):
    """Duplicate an existing workflow"""
    try:
        workflow = await workflow_service.duplicate_workflow(workflow_id, new_name)
        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found"
            )
        return workflow
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to duplicate workflow: {str(e)}"
        )


@router.post("/{workflow_id}/validate")
async def validate_workflow_endpoint(workflow_id: str):
    """Validate a workflow"""
    workflow = await workflow_service.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found"
        )
    
    try:
        from app.services.validation_service import validation_service
        errors = validation_service.validate_workflow(workflow)
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate workflow: {str(e)}"
        )


@router.get("/_health")
async def storage_health():
    """Get storage backend health status"""
    try:
        health_data = await workflow_service.get_storage_health()
        status_code = status.HTTP_200_OK if health_data.get("status") == "healthy" else status.HTTP_503_SERVICE_UNAVAILABLE
        return health_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get storage health: {str(e)}"
        )