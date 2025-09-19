from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from typing import Dict, Any
from pydantic import BaseModel

from app.models.workflow import WorkflowExecution
from app.services.workflow_service import workflow_service
from app.services.execution_service import execution_engine
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


class ExecutionRequest(BaseModel):
    input_data: Dict[str, Any]


class PlaygroundExecutionRequest(BaseModel):
    workflow_id: str
    input_data: Dict[str, Any]


@router.post("/run/{workflow_id}")
async def run_workflow(workflow_id: str, execution_request: ExecutionRequest, background_tasks: BackgroundTasks):
    """Execute a workflow with given input data"""
    # Get workflow
    workflow = await workflow_service.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found"
        )
    
    try:
        # Start execution in background
        execution = await execution_engine.execute_workflow(workflow, execution_request.input_data)
        
        return {
            "execution_id": execution.execution_id,
            "status": execution.status,
            "result": execution.result,
            "error": execution.error
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute workflow: {str(e)}"
        )


@router.get("/status/{execution_id}")
async def get_execution_status(execution_id: str):
    """Get the status of a workflow execution"""
    execution = execution_engine.get_execution_status(execution_id)
    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found"
        )
    
    return {
        "execution_id": execution.execution_id,
        "workflow_id": execution.workflow_id,
        "status": execution.status,
        "result": execution.result,
        "error": execution.error,
        "created_at": execution.created_at
    }


@router.get("/trace/{execution_id}")
async def get_execution_trace(execution_id: str):
    """Get execution trace for workflow execution"""
    execution = execution_engine.get_execution_status(execution_id)
    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found"
        )
    
    trace = execution_engine.get_execution_trace(execution_id)
    
    return {
        "execution_id": execution_id,
        "trace": trace
    }


@router.get("/")
async def list_executions():
    """List all active executions"""
    executions = []
    for execution_id, execution in execution_engine.active_executions.items():
        executions.append({
            "execution_id": execution.execution_id,
            "workflow_id": execution.workflow_id,
            "status": execution.status,
            "created_at": execution.created_at
        })
    
    return executions


@router.delete("/{execution_id}")
async def cancel_execution(execution_id: str):
    """Cancel a running execution"""
    execution = execution_engine.get_execution_status(execution_id)
    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found"
        )
    
    if execution.status == "running":
        execution.status = "cancelled"
        execution.error = "Execution cancelled by user"
    
    return {"message": "Execution cancelled"}


@router.post("/validate/{workflow_id}")
async def validate_workflow_for_execution(workflow_id: str):
    """Validate if a workflow can be executed"""
    workflow = await workflow_service.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found"
        )
    
    try:
        from app.services.validation_service import validation_service
        errors = validation_service.validate_for_execution(workflow)
        
        # Additional execution-specific validation
        execution_errors = []
        
        # Check for start nodes
        start_nodes = [n for n in workflow.nodes if n.type.value == "signature_field" and n.data.get('is_start')]
        if not start_nodes:
            execution_errors.append("No start nodes defined")
        
        # Check for end nodes
        end_nodes = [n for n in workflow.nodes if n.type.value == "signature_field" and n.data.get('is_end')]
        if not end_nodes:
            execution_errors.append("No end nodes defined")
        
        all_errors = errors + execution_errors
        
        return {
            "executable": len(all_errors) == 0,
            "errors": all_errors
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate workflow: {str(e)}"
        )


@router.post("/playground")
async def execute_workflow_playground(request: PlaygroundExecutionRequest):
    """Execute a workflow from the playground interface"""
    try:
        logger.info(f"Playground execution request for workflow: {request.workflow_id}")
        logger.debug(f"Input data: {request.input_data}")
        
        # Get workflow
        workflow = await workflow_service.get_workflow(request.workflow_id)
        if not workflow:
            logger.error(f"Workflow not found: {request.workflow_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found"
            )
        
        logger.debug(f"Workflow nodes: {[n.id for n in workflow.nodes]}")
        logger.debug(f"Workflow edges: {[(e.source, e.target) for e in workflow.edges]}")
        
        # Execute workflow directly
        logger.debug("Executing workflow")
        execution = await execution_engine.execute_workflow(workflow, request.input_data)
        
        logger.info(f"Execution completed with status: {execution.status}")
        if execution.error:
            logger.error(f"Execution error details: {execution.error}")
        if execution.result:
            logger.debug(f"Execution result: {execution.result}")
        
        # Check if execution failed and return 500 error
        if execution.status == "failed":
            logger.error(f"Workflow execution failed for {request.workflow_id}: {execution.error}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Workflow execution failed: {execution.error}"
            )
        
        # Prepare successful response
        response = {
            "success": True,
            "execution_id": execution.execution_id,
            "status": execution.status,
            "result": execution.result,
            "error": None
        }
        
        logger.info(f"Playground execution completed successfully for workflow: {request.workflow_id}")
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Playground execution failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Playground execution failed: {str(e)}"
        )