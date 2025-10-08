from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from typing import List, Dict, Optional, Literal, Any
from pydantic import BaseModel, Field, field_validator

from dspy_forge.models.workflow import (
    Workflow, WorkflowCreateRequest, WorkflowUpdateRequest, DeploymentRequest
)
from dspy_forge.services.workflow_service import workflow_service
from dspy_forge.services.validation_service import (
    WorkflowValidationError,
    validation_service,
    optimization_validation_service
)
from dspy_forge.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


# Optimization models
class ScoringFunctionRequest(BaseModel):
    type: Literal['Correctness', 'Guidelines']
    name: str
    guideline: Optional[str] = None
    weightage: int = Field(..., ge=0, le=100)

    @field_validator('guideline')
    @classmethod
    def validate_guideline(cls, v, info):
        if info.data.get('type') == 'Guidelines' and not v:
            raise ValueError('Guideline is required for Guidelines type scoring functions')
        return v


class DatasetLocation(BaseModel):
    catalog: str
    schema: str
    table: str


class OptimizationRequest(BaseModel):
    workflow_id: str
    workflow_ir: Optional[Dict[str, Any]] = None
    optimizer_name: Literal['GEPA', 'BootstrapFewShotWithRandomSearch', 'MIPROv2']
    optimizer_config: Dict[str, str] = Field(default_factory=dict)
    scoring_functions: List[ScoringFunctionRequest]
    training_data: DatasetLocation
    validation_data: DatasetLocation

    @field_validator('scoring_functions')
    @classmethod
    def validate_weightage_sum(cls, v):
        total = sum(sf.weightage for sf in v)
        if total != 100:
            raise ValueError(f'Total weightage must equal 100, got {total}')
        return v


class OptimizationResponse(BaseModel):
    optimization_id: str
    status: str
    message: str


class ValidationErrorResponse(BaseModel):
    detail: str
    field_errors: Optional[Dict[str, str]] = None


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


@router.get("/{workflow_id}/history")
async def get_workflow_history(workflow_id: str):
    """Get workflow with optimization and deployment history"""
    try:
        # Get workflow
        workflow = await workflow_service.get_workflow(workflow_id)
        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found"
            )

        # Get storage backend
        from dspy_forge.storage.factory import get_storage_backend
        storage = await get_storage_backend()

        # Get optimization and deployment history
        optimizations = await storage.list_workflow_optimizations(workflow_id)
        deployments = await storage.list_workflow_deployments(workflow_id)

        return {
            "workflow_id": workflow_id,
            "workflow": workflow.model_dump(),
            "optimizations": optimizations,
            "deployments": deployments
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow history for {workflow_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get workflow history: {str(e)}"
        )


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
        status_info = await deployment_service.get_deployment_status(deployment_id)
        
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


@router.post("/optimize", response_model=OptimizationResponse)
async def optimize_workflow(request: OptimizationRequest, background_tasks: BackgroundTasks):
    """
    Start optimization job for a workflow using DSPy optimizers.

    Validates:
    - Workflow structure and integrity
    - Workflow exists and is valid
    - Optimizer configuration is valid for the selected optimizer
    - Dataset locations are properly specified
    - Scoring functions are valid and sum to 100%
    """
    try:
        logger.info(f"Starting optimization for workflow {request.workflow_id} with optimizer {request.optimizer_name}")

        # Step 1: Validate workflow exists
        workflow = await workflow_service.get_workflow(request.workflow_id)
        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found",
                headers={"X-Error-Field": "workflow_id"}
            )

        # Step 2: Validate workflow structure
        workflow_errors = validation_service.validate_workflow(workflow)
        if workflow_errors:
            logger.warning(f"Workflow validation failed for {request.workflow_id}: {workflow_errors}")
            error_response = ValidationErrorResponse(
                detail=f"Workflow validation failed: {'; '.join(workflow_errors)}",
                field_errors={"workflow": '; '.join(workflow_errors)}
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=error_response.model_dump()
            )

        # Step 3: Validate optimization configuration
        field_errors = optimization_validation_service.validate_optimization_request(
            optimizer_name=request.optimizer_name,
            optimizer_config=request.optimizer_config,
            scoring_functions=[sf.model_dump() for sf in request.scoring_functions],
            training_data=request.training_data.model_dump(),
            validation_data=request.validation_data.model_dump()
        )

        if field_errors:
            logger.warning(f"Optimization validation failed: {field_errors}")
            error_response = ValidationErrorResponse(
                detail="Optimization validation failed",
                field_errors=field_errors
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=error_response.model_dump()
            )

        # Step 4: Start background optimization task
        from dspy_forge.services.optimization_service import optimization_service

        optimization_id = f"opt_{request.workflow_id}"

        # Add optimization task to background
        background_tasks.add_task(
            optimization_service.optimize_workflow_async,
            workflow,
            request.optimizer_name,
            request.optimizer_config,
            [sf.model_dump() for sf in request.scoring_functions],
            request.training_data.model_dump(),
            request.validation_data.model_dump(),
            optimization_id
        )

        logger.info(f"Optimization job {optimization_id} queued for background execution")

        return OptimizationResponse(
            optimization_id=optimization_id,
            status="queued",
            message=f"Optimization job started with {request.optimizer_name}. Check status using optimization_id."
        )

    except HTTPException:
        raise
    except ValueError as e:
        # Pydantic validation errors
        logger.warning(f"Validation error in optimization request: {str(e)}")
        error_response = ValidationErrorResponse(
            detail=str(e),
            field_errors={}
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=error_response.model_dump()
        )
    except Exception as e:
        logger.error(f"Failed to start optimization: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start optimization: {str(e)}"
        )


@router.get("/optimize/status/{optimization_id}")
async def get_optimization_status(optimization_id: str):
    """Get optimization status"""
    try:
        logger.info(f"Getting optimization status for {optimization_id}")
        from dspy_forge.services.optimization_service import optimization_service
        status_info = await optimization_service.get_optimization_status(optimization_id)

        if not status_info:
            logger.warning(f"Optimization status not found for {optimization_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Optimization not found"
            )

        logger.info(f"Found optimization status for {optimization_id}: {status_info.get('status')}")
        return status_info

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get optimization status for {optimization_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get optimization status: {str(e)}"
        )


@router.post("/{workflow_id}/compile")
async def compile_workflow(workflow_id: str):
    """Compile workflow to DSPy code"""
    try:
        logger.info(f"Compiling workflow {workflow_id}")

        # Get workflow
        workflow = await workflow_service.get_workflow(workflow_id)
        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found"
            )

        # Compile workflow to code
        from dspy_forge.services.compiler_service import compiler_service
        compiled_code, node_mapping = compiler_service.compile_workflow_to_code(workflow)

        logger.info(f"Successfully compiled workflow {workflow_id}")
        return {
            "workflow_id": workflow_id,
            "code": compiled_code,
            "node_mapping": node_mapping
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to compile workflow {workflow_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compile workflow: {str(e)}"
        )


@router.get("/_health")
async def storage_health():
    """Get storage backend health status"""
    try:
        health_data = await workflow_service.get_storage_health()
        return health_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get storage health: {str(e)}"
        )