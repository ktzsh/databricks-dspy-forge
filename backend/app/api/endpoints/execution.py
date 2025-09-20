from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel

from app.models.workflow import WorkflowExecution, NodeType, PlaygroundExecutionRequest, ExecutionRequest
from app.services.workflow_service import workflow_service
from app.services.execution_service import execution_engine
from app.core.logging import get_logger

from app.services.validation_service import validation_service
from app.models.workflow import Workflow
        
router = APIRouter()
logger = get_logger(__name__)


def _process_playground_input(input_data: Dict[str, Any], conversation_history: list, workflow) -> Dict[str, Any]:
    """
    Process playground input to dynamically handle question and history.
    
    Args:
        input_data: Raw input data from frontend (contains current message)
        conversation_history: List of previous conversation exchanges  
        workflow: The workflow object to determine expected input fields
        
    Returns:
        Processed input data with question and history fields
    """
    # Find start signature field nodes to determine expected input fields
    start_nodes = [
        node for node in workflow.nodes 
        if node.type == NodeType.SIGNATURE_FIELD and 
        (node.data.get('is_start', False) or node.data.get('isStart', False))
    ]
    
    expected_fields = set()
    for start_node in start_nodes:
        fields = start_node.data.get('fields', [])
        for field_data in fields:
            field_name = field_data.get('name')
            if field_name:
                expected_fields.add(field_name)
    
    logger.debug(f"Expected input fields from workflow: {expected_fields}")
    
    # Extract current question from input_data
    current_question = input_data['question']
    
    if not current_question:
        # If no recognizable input field, use the first string value
        for value in input_data.values():
            if isinstance(value, str) and value.strip():
                current_question = value
                break
    
    # Build processed input data
    processed_input = {}
    
    # Handle question field
    if 'question' in expected_fields:
        processed_input['question'] = current_question or ""
    
    # Handle history field  
    if 'history' in expected_fields:
        # Convert conversation history to the expected format
        history_list = []
        for exchange in conversation_history:
            if isinstance(exchange, dict):
                # Extract all relevant fields from the exchange
                history_entry = {}
                if 'question' in exchange:
                    history_entry['question'] = exchange['question']
                if 'answer' in exchange:
                    history_entry['answer'] = exchange['answer']
                # Add any other output fields that might exist
                for key, value in exchange.items():
                    if key not in ['question'] and value is not None:
                        history_entry[key] = value
                
                if history_entry:  # Only add non-empty entries
                    history_list.append(history_entry)
        
        processed_input['history'] = history_list
    
    # Add any other expected fields from input_data
    for field in expected_fields:
        if field not in processed_input and field in input_data:
            processed_input[field] = input_data[field]
    
    # If no expected fields found, fall back to original behavior
    if not expected_fields:
        processed_input = input_data.copy()
        if current_question:
            processed_input['question'] = current_question
    
    return processed_input


@router.post("/playground")
async def execute_workflow_playground(request: PlaygroundExecutionRequest):
    """Execute a workflow from the playground interface"""
    try:
        logger.info(f"Playground execution request with workflow IR")
        logger.debug(f"Question: {request.question}")
        logger.debug(f"Conversation history length: {len(request.conversation_history)}")
        
        # Use provided workflow ID
        workflow_id = request.workflow_id
        
        workflow_data = {
            "id": workflow_id,
            "name": "Playground Workflow",
            "description": "Temporary workflow for playground execution",
            "nodes": request.workflow_ir.get("nodes", []),
            "edges": request.workflow_ir.get("edges", []),
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        workflow = Workflow(**workflow_data)
        logger.debug(f"Created workflow with {len(workflow.nodes)} nodes and {len(workflow.edges)} edges")
        
        # Validate workflow
        errors = validation_service.validate_for_execution(workflow)
        
        if errors:
            logger.error(f"Workflow validation failed: {errors}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Workflow validation failed: {'; '.join(errors)}"
            )
        
        # Prepare input data with question and history
        input_data = {
            "question": request.question,
        }
        
        # Process input data to handle question and history dynamically
        processed_input = _process_playground_input(input_data, request.conversation_history, workflow)
        logger.debug(f"Processed input: {processed_input}")
        
        # Execute workflow directly
        logger.debug("Executing workflow")
        execution = await execution_engine.execute_workflow(workflow, processed_input)
        
        logger.info(f"Execution completed with status: {execution.status}")
        if execution.error:
            logger.error(f"Execution error details: {execution.error}")
        if execution.result:
            logger.debug(f"Execution result: {execution.result}")
        
        # Check if execution failed and return 500 error
        if execution.status == "failed":
            logger.error(f"Workflow execution failed: {execution.error}")
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
        
        logger.info(f"Playground execution completed successfully")
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