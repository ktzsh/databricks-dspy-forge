import uuid
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import asyncio
import dspy
import os
import inspect

from app.models.workflow import Workflow, WorkflowExecution, NodeType
from app.core.config import settings
from app.core.logging import get_logger
from app.core.dspy_types import (
    create_dspy_signature, 
    get_module_class, 
    DSPyModuleType, 
    DSPyLogicType,
    SignatureFieldDefinition,
    python_type_to_dspy_type
)
from app.utils.workflow_utils import (
    get_execution_order, 
    extract_signature_fields, 
    extract_modules, 
    extract_logic_components,
    find_start_nodes,
    find_end_nodes,
    get_node_dependencies,
    get_node_dependents
)
from app.services.compiler_service import compiler_service
from app.core.templates import TemplateFactory
from app.components import registry  # This will auto-register all templates

logger = get_logger(__name__)


class ExecutionContext:
    """Context for workflow execution"""
    def __init__(self, workflow: Workflow, input_data: Dict[str, Any]):
        self.workflow = workflow
        self.input_data = input_data
        self.node_outputs: Dict[str, Dict[str, Any]] = {}
        self.execution_trace: List[Dict[str, Any]] = []
        self.models: Dict[str, Any] = {}
        self.node_counts: Dict[str, int] = {}  # Track count of each module type
        
    def set_node_output(self, node_id: str, output: Dict[str, Any]):
        """Set output for a node"""
        self.node_outputs[node_id] = output
        
    def get_node_output(self, node_id: str) -> Dict[str, Any]:
        """Get output from a node"""
        return self.node_outputs.get(node_id, {})
        
    def add_trace_entry(self, node_id: str, node_type: str, inputs: Dict[str, Any], outputs: Dict[str, Any], execution_time: float):
        """Add entry to execution trace"""
        self.execution_trace.append({
            'node_id': node_id,
            'node_type': node_type,
            'inputs': inputs,
            'outputs': outputs,
            'execution_time': execution_time,
            'timestamp': datetime.now().isoformat()
        })


class WorkflowExecutionEngine:
    """Engine for executing DSPy workflows"""
    
    def __init__(self):
        self.active_executions: Dict[str, WorkflowExecution] = {}
    
    
    def _compile_and_save_workflow(self, workflow: Workflow, context: ExecutionContext = None):
        """Compile workflow to code and save if debug_compiler is enabled"""
        if settings.debug_compiler:
            try:
                workflow_code = compiler_service.compile_workflow_to_code(workflow, context)
                compiler_service.save_compiled_workflow(workflow.id, workflow_code)
            except Exception as e:
                logger.error(f"Failed to compile and save workflow {workflow.id}: {e}")
    
    
    async def execute_workflow(self, workflow: Workflow, input_data: Dict[str, Any]) -> WorkflowExecution:
        """Execute a workflow with given input data"""
        execution_id = str(uuid.uuid4())
        
        execution = WorkflowExecution(
            workflow_id=workflow.id,
            input_data=input_data,
            execution_id=execution_id,
            status="pending"
        )
        
        self.active_executions[execution_id] = execution
        
        try:
            # Update status to running
            execution.status = "running"
            
            # Create execution context
            context = ExecutionContext(workflow, input_data)
            
            # Get execution order
            execution_order = get_execution_order(workflow)
            
            # Execute nodes in order
            for node_id in execution_order:
                await self._execute_node(node_id, context)
            
            # Get final outputs
            end_nodes = find_end_nodes(workflow)
            final_outputs = {}
            for end_node_id in end_nodes:
                final_outputs[end_node_id] = context.get_node_output(end_node_id)
            
            # Include execution trace and intermediate outputs in result
            execution.result = {
                'final_outputs': final_outputs,
                'execution_trace': context.execution_trace,
                'node_outputs': context.node_outputs
            }
            execution.status = "completed"
            
            # Generate workflow code if debug_compiler is enabled
            # self._compile_and_save_workflow(workflow, context)
            
        except Exception as e:
            execution.error = str(e)
            execution.status = "failed"
        
        return execution
    
    async def _execute_node(self, node_id: str, context: ExecutionContext):
        """Execute a single node using template system"""
        start_time = datetime.now()
        
        # Find the node
        node = next((n for n in context.workflow.nodes if n.id == node_id), None)
        if not node:
            raise ValueError(f"Node {node_id} not found")
        
        inputs = self._get_node_inputs(node_id, context)
        outputs = {}
        
        try:
            # Create template for this node using the factory
            template = TemplateFactory.create_template(node, context.workflow)
            
            # Execute the node using its template
            outputs = await template.execute(inputs, context)
            
            context.set_node_output(node_id, outputs)
            
        except Exception as e:
            # Log error but continue execution
            logger.error(f"Error executing node {node_id}: {e}")
            outputs = {'error': str(e)}
            context.set_node_output(node_id, outputs)
        
        # Add to trace
        execution_time = (datetime.now() - start_time).total_seconds()
        context.add_trace_entry(node_id, node.type.value, inputs, outputs, execution_time)
    
    def _get_node_inputs(self, node_id: str, context: ExecutionContext) -> Dict[str, Any]:
        """Get inputs for a node from its dependencies"""
        dependencies = get_node_dependencies(context.workflow, node_id)
        
        # Check if this is a start node
        start_nodes = find_start_nodes(context.workflow)
        if node_id in start_nodes:
            # Use workflow input data
            return context.input_data
        
        # Get inputs considering field-level connections
        inputs = {}
        
        # Find edges that target this node
        incoming_edges = [edge for edge in context.workflow.edges if edge.target == node_id]
        
        for edge in incoming_edges:
            source_outputs = context.get_node_output(edge.source)
            
            if edge.sourceHandle and edge.targetHandle:
                # Field-level connection
                source_field = edge.sourceHandle.replace('source-', '')
                target_field = edge.targetHandle.replace('target-', '')
                
                if source_field in source_outputs:
                    inputs[target_field] = source_outputs[source_field]
            else:
                # Whole-node connection
                inputs.update(source_outputs)
        
        # Fallback to legacy behavior for nodes without specific edges
        if not incoming_edges:
            for dep_node_id in dependencies:
                dep_outputs = context.get_node_output(dep_node_id)
                inputs.update(dep_outputs)
        
        return inputs
    
    def get_execution_status(self, execution_id: str) -> Optional[WorkflowExecution]:
        """Get execution status"""
        return self.active_executions.get(execution_id)
    
    def get_execution_trace(self, execution_id: str) -> List[Dict[str, Any]]:
        """Get execution trace"""
        execution = self.active_executions.get(execution_id)
        if not execution:
            return []
        
        # For now, return empty trace - would be populated during execution
        return []


# Global execution engine instance
execution_engine = WorkflowExecutionEngine()