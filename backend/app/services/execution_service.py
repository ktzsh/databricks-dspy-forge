import uuid
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import asyncio
import dspy

from app.models.workflow import Workflow, WorkflowExecution, NodeType
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


class ExecutionContext:
    """Context for workflow execution"""
    def __init__(self, workflow: Workflow, input_data: Dict[str, Any]):
        self.workflow = workflow
        self.input_data = input_data
        self.node_outputs: Dict[str, Dict[str, Any]] = {}
        self.execution_trace: List[Dict[str, Any]] = []
        self.models: Dict[str, Any] = {}
        
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
            
            execution.result = final_outputs
            execution.status = "completed"
            
        except Exception as e:
            execution.error = str(e)
            execution.status = "failed"
        
        return execution
    
    async def _execute_node(self, node_id: str, context: ExecutionContext):
        """Execute a single node"""
        start_time = datetime.now()
        
        # Find the node
        node = next((n for n in context.workflow.nodes if n.id == node_id), None)
        if not node:
            raise ValueError(f"Node {node_id} not found")
        
        inputs = self._get_node_inputs(node_id, context)
        outputs = {}
        
        try:
            if node.type == NodeType.SIGNATURE_FIELD:
                outputs = await self._execute_signature_field_node(node, inputs, context)
            elif node.type == NodeType.MODULE:
                outputs = await self._execute_module_node(node, inputs, context)
            elif node.type == NodeType.LOGIC:
                outputs = await self._execute_logic_node(node, inputs, context)
            
            context.set_node_output(node_id, outputs)
            
        except Exception as e:
            # Log error but continue execution
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
        
        # Combine outputs from dependency nodes
        inputs = {}
        for dep_node_id in dependencies:
            dep_outputs = context.get_node_output(dep_node_id)
            inputs.update(dep_outputs)
        
        return inputs
    
    async def _execute_signature_field_node(self, node: Any, inputs: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """Execute a signature field node (pass-through with validation)"""
        fields = node.data.get('fields', [])
        outputs = {}
        
        # Validate and pass through inputs
        for field_data in fields:
            field_name = field_data.get('name')
            field_type = field_data.get('type', 'str')
            required = field_data.get('required', True)
            
            if field_name in inputs:
                # TODO: Add type validation here
                outputs[field_name] = inputs[field_name]
            elif required:
                raise ValueError(f"Required field '{field_name}' not found in inputs")
        
        return outputs
    
    async def _execute_module_node(self, node: Any, inputs: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """Execute a DSPy module node"""
        module_type_str = node.data.get('module_type')
        model_name = node.data.get('model', '')
        parameters = node.data.get('parameters', {})
        
        if not module_type_str:
            raise ValueError("Module type not specified")
        
        try:
            module_type = DSPyModuleType(module_type_str)
        except ValueError:
            raise ValueError(f"Unsupported module type: {module_type_str}")
        
        # Get or create model
        model = self._get_or_create_model(model_name, context)
        
        # Create signature (simplified for now)
        # In a real implementation, this would be derived from connected signature nodes
        
        if module_type == DSPyModuleType.PREDICT:
            # Simple predict module
            class SimpleSignature(dspy.Signature):
                """Basic prediction signature"""
                input = dspy.InputField()
                output = dspy.OutputField()
            
            predictor = dspy.Predict(SimpleSignature)
            result = predictor(**inputs)
            return result.__dict__
            
        elif module_type == DSPyModuleType.CHAIN_OF_THOUGHT:
            # Chain of thought module
            class SimpleSignature(dspy.Signature):
                """Chain of thought signature"""
                input = dspy.InputField()
                rationale = dspy.OutputField()
                output = dspy.OutputField()
            
            cot = dspy.ChainOfThought(SimpleSignature)
            result = cot(**inputs)
            return result.__dict__
            
        elif module_type == DSPyModuleType.RETRIEVE:
            # Retrieve module (placeholder)
            # In real implementation, this would use a configured retriever
            return {
                'passages': [f"Retrieved passage for: {inputs.get('query', 'N/A')}"],
                'scores': [0.95]
            }
        
        else:
            # Fallback for other module types
            return {'output': f"Output from {module_type} module"}
    
    async def _execute_logic_node(self, node: Any, inputs: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """Execute a logic node"""
        logic_type_str = node.data.get('logic_type')
        condition = node.data.get('condition', '')
        parameters = node.data.get('parameters', {})
        
        if not logic_type_str:
            raise ValueError("Logic type not specified")
        
        try:
            logic_type = DSPyLogicType(logic_type_str)
        except ValueError:
            raise ValueError(f"Unsupported logic type: {logic_type_str}")
        
        if logic_type == DSPyLogicType.IF_ELSE:
            # Evaluate condition (simplified)
            condition_result = self._evaluate_condition(condition, inputs)
            return {
                'condition_result': condition_result,
                'branch': 'true' if condition_result else 'false',
                **inputs  # Pass through inputs
            }
            
        elif logic_type == DSPyLogicType.MERGE:
            # Simple merge - combine all inputs
            return inputs
        
        else:
            return inputs
    
    def _evaluate_condition(self, condition: str, inputs: Dict[str, Any]) -> bool:
        """Evaluate a condition string (simplified implementation)"""
        if not condition:
            return True
        
        # Very basic condition evaluation - in production this would need proper parsing
        try:
            # Replace field names with actual values
            eval_string = condition
            for key, value in inputs.items():
                eval_string = eval_string.replace(key, str(value))
            
            # Basic safety check - only allow simple comparisons
            allowed_operators = ['>', '<', '>=', '<=', '==', '!=', 'and', 'or']
            if any(op in eval_string for op in ['import', 'exec', 'eval', '__']):
                return True  # Default to true for unsafe conditions
            
            return bool(eval(eval_string))
        except:
            return True  # Default to true if evaluation fails
    
    def _get_or_create_model(self, model_name: str, context: ExecutionContext) -> Any:
        """Get or create a model instance"""
        if model_name in context.models:
            return context.models[model_name]
        
        # Create mock model for demonstration
        # In production, this would create actual model instances
        mock_model = f"Model({model_name})"
        context.models[model_name] = mock_model
        return mock_model
    
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