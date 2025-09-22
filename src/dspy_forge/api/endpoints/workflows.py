from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from typing import List, Dict, Any
from pydantic import BaseModel

from dspy_forge.models.workflow import (
    Workflow, WorkflowCreateRequest, WorkflowUpdateRequest, DeploymentRequest
)
from dspy_forge.services.workflow_service import workflow_service
from dspy_forge.services.validation_service import WorkflowValidationError
from dspy_forge.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


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
        from dspy_forge.services.validation_service import validation_service
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


@router.post("/deploy/{workflow_id}")
async def deploy_workflow(workflow_id: str, deployment_request: DeploymentRequest, background_tasks: BackgroundTasks):
    """Deploy compiled workflow to Databricks as agent endpoint"""
    try:
        logger.info(f"Starting deployment for workflow {workflow_id}")
        
        # Get workflow
        workflow = await workflow_service.get_workflow(workflow_id)
        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found"
            )
        
        # Start background deployment task
        from dspy_forge.services.deployment_service import deployment_service
        deployment_id = f"deploy_{workflow_id}_{deployment_request.model_name}"
        
        background_tasks.add_task(
            deployment_service.deploy_workflow_async,
            workflow,
            deployment_request.model_name,
            deployment_request.catalog_name,
            deployment_request.schema_name,
            deployment_id
        )
        
        return {
            "workflow_id": workflow_id,
            "deployment_id": deployment_id,
            "model_name": deployment_request.model_name,
            "catalog_name": deployment_request.catalog_name,
            "schema_name": deployment_request.schema_name,
            "status": "deployment_started",
            "message": "Deployment started in background. Check status using deployment_id."
        }
        
    except Exception as e:
        logger.error(f"Failed to start deployment for workflow {workflow_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start deployment: {str(e)}"
        )


@router.get("/deploy/status/{deployment_id}")
async def get_deployment_status(deployment_id: str):
    """Get deployment status"""
    try:
        logger.info(f"Getting deployment status for {deployment_id}")
        from dspy_forge.services.deployment_service import deployment_service
        status_info = deployment_service.get_deployment_status(deployment_id)
        
        if not status_info:
            logger.warning(f"Deployment status not found for {deployment_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Deployment not found"
            )
        
        logger.info(f"Found deployment status for {deployment_id}: {status_info.get('status')}")
        return status_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get deployment status for {deployment_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get deployment status: {str(e)}"
        )


@router.post("/optimize/{workflow_id}")
async def optimize_workflow(workflow_id: str, optimization_config: Dict[str, Any]):
    """Optimize workflow performance"""
    # TODO: Implement workflow optimization logic
    return {
        "workflow_id": workflow_id,
        "status": "optimized",
        "message": "Optimization not implemented yet"
    }


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