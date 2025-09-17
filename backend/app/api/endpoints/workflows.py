from fastapi import APIRouter, HTTPException, status
from typing import List, Dict, Any
from pydantic import BaseModel

from app.models.workflow import Workflow
from app.services.workflow_service import workflow_service
from app.utils.workflow_utils import WorkflowValidationError

router = APIRouter()


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
        workflow_data = workflow_request.model_dump()
        workflow = workflow_service.create_workflow(workflow_data)
        return workflow
    except WorkflowValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create workflow: {str(e)}"
        )


@router.get("/", response_model=List[Workflow])
async def list_workflows():
    """List all workflows"""
    try:
        workflows = workflow_service.list_workflows()
        return workflows
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list workflows: {str(e)}"
        )


@router.get("/{workflow_id}", response_model=Workflow)
async def get_workflow(workflow_id: str):
    """Get a specific workflow by ID"""
    workflow = workflow_service.get_workflow(workflow_id)
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
        # Get existing workflow
        existing_workflow = workflow_service.get_workflow(workflow_id)
        if not existing_workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found"
            )
        
        # Merge updates with existing data
        workflow_data = existing_workflow.model_dump()
        update_data = workflow_request.model_dump(exclude_unset=True)
        workflow_data.update(update_data)
        
        workflow = workflow_service.update_workflow(workflow_id, workflow_data)
        return workflow
    except WorkflowValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update workflow: {str(e)}"
        )


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(workflow_id: str):
    """Delete a workflow"""
    success = workflow_service.delete_workflow(workflow_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found"
        )


@router.post("/{workflow_id}/duplicate", response_model=Workflow, status_code=status.HTTP_201_CREATED)
async def duplicate_workflow(workflow_id: str, new_name: str = None):
    """Duplicate an existing workflow"""
    try:
        workflow = workflow_service.duplicate_workflow(workflow_id, new_name)
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
    workflow = workflow_service.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found"
        )
    
    try:
        from app.utils.workflow_utils import validate_workflow
        errors = validate_workflow(workflow)
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate workflow: {str(e)}"
        )