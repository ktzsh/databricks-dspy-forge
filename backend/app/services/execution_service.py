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
    
    
    def _save_workflow_code(self, workflow_id: str, workflow_code: str):
        """Save optimized workflow code to artifacts directory when debug_compiler is enabled"""
        if not settings.debug_compiler:
            return
            
        try:
            # Create artifacts directory if it doesn't exist
            artifacts_dir = os.path.join(settings.artifacts_path, "workflows", workflow_id)
            os.makedirs(artifacts_dir, exist_ok=True)
            
            # Save the workflow code
            filename = "workflow.py"
            filepath = os.path.join(artifacts_dir, filename)
            
            with open(filepath, 'w') as f:
                f.write(f"# DSPy Workflow: {workflow_id}\n")
                f.write(f"# Generated at: {datetime.now().isoformat()}\n\n")
                f.write(workflow_code)
            
            logger.info(f"Workflow code saved to: {filepath}")
            
        except Exception as e:
            logger.error(f"Failed to save workflow code: {str(e)}")
    
    def _generate_workflow_code(self, context: ExecutionContext) -> str:
        """Generate optimized workflow code from execution context"""
        code_lines = ["import dspy", ""]
        
        # Extract all modules from the workflow
        module_nodes = [node for node in context.workflow.nodes if node.type == NodeType.MODULE]
        signatures_created = set()
        node_counts = {}
        
        # Generate unique signatures first
        for node in module_nodes:
            module_type_str = node.data.get('module_type', 'Unknown')
            instruction = node.data.get('instruction', '')
            
            # Get input and output fields from connected signature nodes
            input_fields = self._get_expected_input_fields(node, context)
            if not input_fields:
                input_fields = ['input']
            output_fields = self._get_expected_output_fields(node, context)
            if not output_fields:
                output_fields = ['output']
            
            # Create signature key for deduplication
            signature_key = (module_type_str, tuple(input_fields), tuple(output_fields), instruction)
            
            if signature_key not in signatures_created:
                signatures_created.add(signature_key)
                
                # Generate unique signature name
                signature_name = f"{module_type_str}Signature"
                if len([s for s in signatures_created if s[0] == module_type_str]) > 1:
                    signature_name += f"_{len([s for s in signatures_created if s[0] == module_type_str])}"
                
                # Add signature class
                code_lines.append(f"class {signature_name}(dspy.Signature):")
                if instruction:
                    code_lines.append(f'    """{instruction}"""')
                
                for field_name in input_fields:
                    code_lines.append(f"    {field_name} = dspy.InputField()")
                
                if module_type_str == "ChainOfThought":
                    code_lines.append(f"    rationale = dspy.OutputField(desc='Step-by-step reasoning')")
                    
                for field_name in output_fields:
                    code_lines.append(f"    {field_name} = dspy.OutputField()")
                
                code_lines.append("")
        
        code_lines.append("# Module instances")
        
        # Generate module instances
        for node in module_nodes:
            module_type_str = node.data.get('module_type', 'Unknown')
            node_counts[module_type_str] = node_counts.get(module_type_str, 0) + 1
            node_index = node_counts[module_type_str]
            
            # Find matching signature
            instruction = node.data.get('instruction', '')
            input_fields = self._get_expected_input_fields(node, context)
            if not input_fields:
                input_fields = ['input']
            output_fields = self._get_expected_output_fields(node, context)
            if not output_fields:
                output_fields = ['output']
            
            signature_key = (module_type_str, tuple(input_fields), tuple(output_fields), instruction)
            signature_index = list(signatures_created).index(signature_key) + 1
            
            signature_name = f"{module_type_str}Signature"
            if len([s for s in signatures_created if s[0] == module_type_str]) > 1:
                signature_name += f"_{signature_index}"
            
            # Add module instantiation with cleaner naming
            module_var_name = f"{module_type_str.lower()}_{node_index}"
            
            if module_type_str == "Predict":
                code_lines.append(f"{module_var_name} = dspy.Predict({signature_name})")
            elif module_type_str == "ChainOfThought":
                code_lines.append(f"{module_var_name} = dspy.ChainOfThought({signature_name})")
        
        return '\n'.join(code_lines)
    
    
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
            
            # Generate workflow code if debug_compiler is enabled
            if settings.debug_compiler:
                workflow_code = self._generate_workflow_code(context)
                self._save_workflow_code(workflow.id, workflow_code)
            
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
            elif node.type == NodeType.RETRIEVER:
                outputs = await self._execute_retriever_node(node, inputs, context)
            
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
    
    async def _execute_signature_field_node(self, node: Any, inputs: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """Execute a signature field node (pass-through with validation)"""
        fields = node.data.get('fields', [])
        outputs = {}
        
        # Check if this is a start node or end node
        is_start = node.data.get('is_start', False) or node.data.get('isStart', False)
        is_end = node.data.get('is_end', False) or node.data.get('isEnd', False)
        
        # For start nodes, validate that required fields are present
        # For end nodes, just pass through whatever is available
        for field_data in fields:
            field_name = field_data.get('name')
            field_type = field_data.get('type', 'str')
            required = field_data.get('required', True)
            
            if field_name in inputs:
                # Field is available, pass it through
                outputs[field_name] = inputs[field_name]
            elif required and is_start:
                # Only enforce required fields for start nodes
                raise ValueError(f"Required field '{field_name}' not found in inputs for start node")
            elif is_end:
                # For end nodes, if field is not in inputs, it might be generated by modules
                # Don't fail, just continue - the field might not be needed
                continue
        
        # If no outputs were generated for an end node, pass through all inputs
        if is_end and not outputs:
            outputs = inputs.copy()
        
        return outputs
    
    def _get_expected_input_fields(self, node: Any, context: ExecutionContext) -> List[str]:
        """Get expected input field names from connected signature field nodes"""
        input_fields = []
        
        # Find incoming edges to this node
        incoming_edges = [edge for edge in context.workflow.edges if edge.target == node.id]
        
        for edge in incoming_edges:
            # Find the source node
            source_node = next((n for n in context.workflow.nodes if n.id == edge.source), None)
            if source_node and source_node.type == NodeType.SIGNATURE_FIELD:
                # Get field names from the source signature field
                fields = source_node.data.get('fields', [])
                for field_data in fields:
                    field_name = field_data.get('name')
                    if field_name and field_name not in input_fields:
                        input_fields.append(field_name)
        
        return input_fields
    
    def _get_expected_output_fields(self, node: Any, context: ExecutionContext) -> List[str]:
        """Get expected output field names from connected signature field nodes"""
        output_fields = []
        
        # Find outgoing edges from this node
        outgoing_edges = [edge for edge in context.workflow.edges if edge.source == node.id]
        
        for edge in outgoing_edges:
            # Find the target node
            target_node = next((n for n in context.workflow.nodes if n.id == edge.target), None)
            if target_node and target_node.type == NodeType.SIGNATURE_FIELD:
                # Get field names from the target signature field
                fields = target_node.data.get('fields', [])
                for field_data in fields:
                    field_name = field_data.get('name')
                    if field_name and field_name not in output_fields:
                        output_fields.append(field_name)
        
        return output_fields
    
    async def _execute_module_node(self, node: Any, inputs: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """Execute a DSPy module node"""
        module_type_str = node.data.get('module_type')
        model_name = node.data.get('model', '')
        instruction = node.data.get('instruction', '')
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
            # Track node count for indexing
            context.node_counts[module_type_str] = context.node_counts.get(module_type_str, 0) + 1
            node_index = context.node_counts[module_type_str]
            
            # Create dynamic signature with instruction
            class DynamicSignature(dspy.Signature):
                pass
            
            # Set instruction as docstring
            if instruction:
                DynamicSignature.__doc__ = instruction
            else:
                DynamicSignature.__doc__ = "Generate a response based on the input"
            
            # Get input and output fields from connected signature nodes
            input_fields = self._get_expected_input_fields(node, context)
            if not input_fields:
                input_fields = ['input']
            output_fields = self._get_expected_output_fields(node, context)
            if not output_fields:
                output_fields = ['output']
            
            # Add input fields dynamically
            for key in input_fields:
                setattr(DynamicSignature, key, dspy.InputField())
            
            # Add output fields dynamically
            for field_name in output_fields:
                setattr(DynamicSignature, field_name, dspy.OutputField())
            
            
            predictor = dspy.Predict(DynamicSignature)
            result = predictor(**inputs)
            return result.__dict__
            
        elif module_type == DSPyModuleType.CHAIN_OF_THOUGHT:
            # Track node count for indexing
            context.node_counts[module_type_str] = context.node_counts.get(module_type_str, 0) + 1
            node_index = context.node_counts[module_type_str]
            
            # Create dynamic signature with instruction
            class DynamicSignature(dspy.Signature):
                pass
            
            # Set instruction as docstring
            if instruction:
                DynamicSignature.__doc__ = instruction
            else:
                DynamicSignature.__doc__ = "Think step by step to generate a response"
            
            # Get input and output fields from connected signature nodes
            input_fields = self._get_expected_input_fields(node, context)
            if not input_fields:
                input_fields = ['input']
            output_fields = self._get_expected_output_fields(node, context)
            if not output_fields:
                output_fields = ['output']
            
            # Add input fields dynamically
            for key in input_fields:
                setattr(DynamicSignature, key, dspy.InputField())
            
            # Add rationale field for chain of thought
            setattr(DynamicSignature, 'rationale', dspy.OutputField(desc="Step-by-step reasoning"))
            
            # Add expected output fields
            for field_name in output_fields:
                setattr(DynamicSignature, field_name, dspy.OutputField())
            
            
            cot = dspy.ChainOfThought(DynamicSignature)
            result = cot(**inputs)
            return result.__dict__
            
        elif module_type == DSPyModuleType.RETRIEVE:
            # Legacy retrieve module - now deprecated in favor of retriever nodes
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
            
        elif logic_type == DSPyLogicType.FIELD_SELECTOR:
            # Field selection and filtering
            return self._execute_field_selector(node, inputs)
        
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
    
    def _execute_field_selector(self, node: Any, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute field selection logic"""
        selected_fields = node.data.get('selectedFields', [])
        field_mappings = node.data.get('fieldMappings', {})
        
        if not selected_fields:
            # If no fields are explicitly selected, pass through all inputs
            return inputs
        
        # Filter inputs to only include selected fields
        outputs = {}
        for field_name in selected_fields:
            if field_name in inputs:
                # Use mapped name if provided, otherwise use original name
                output_name = field_mappings.get(field_name, field_name)
                outputs[output_name] = inputs[field_name]
        
        return outputs
    
    async def _execute_retriever_node(self, node: Any, inputs: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """Execute a retriever node"""
        retriever_type = node.data.get('retriever_type')
        parameters = node.data.get('parameters', {})
        
        # Extract query from inputs
        query = inputs.get('query', inputs.get('question', ''))
        if not query:
            # Try to get the first string input as query
            for key, value in inputs.items():
                if isinstance(value, str) and value.strip():
                    query = value
                    break
        
        if not query:
            raise ValueError("No query found in inputs for retriever")
        
        try:
            if retriever_type == 'UnstructuredRetrieve':
                return await self._execute_unstructured_retrieve(node, query, context)
            elif retriever_type == 'StructuredRetrieve':
                return await self._execute_structured_retrieve(node, query, context)
            else:
                raise ValueError(f"Unknown retriever type: {retriever_type}")
                
        except Exception as e:
            raise ValueError(f"Retrieval failed: {str(e)}")
    
    async def _execute_unstructured_retrieve(self, node: Any, query: str, context: ExecutionContext) -> Dict[str, Any]:
        """Execute UnstructuredRetrieve node"""
        catalog_name = node.data.get('catalog_name', '')
        schema_name = node.data.get('schema_name', '')
        index_name = node.data.get('index_name', '')
        embedding_model = node.data.get('embedding_model')
        query_type = node.data.get('query_type', 'HYBRID')
        num_results = node.data.get('num_results', 3)
        score_threshold = node.data.get('score_threshold', 0.0)
        
        # Validate mandatory fields
        if not all([catalog_name, schema_name, index_name]):
            raise ValueError("UnstructuredRetrieve requires catalog_name, schema_name, and index_name")
        
        # TODO: Implement actual Databricks vector search integration
        # Simulate retrieval results
        mock_passages = [
            f"Mock retrieved passage 1 for query: {query}",
            f"Mock retrieved passage 2 for query: {query}",
            f"Mock retrieved passage 3 for query: {query}"
        ][:num_results]
        
        # Filter by score threshold if provided
        mock_scores = [0.95, 0.89, 0.82][:num_results]
        if score_threshold > 0:
            filtered_results = [(passage, score) for passage, score in zip(mock_passages, mock_scores) if score >= score_threshold]
            mock_passages = [p for p, s in filtered_results]
            mock_scores = [s for p, s in filtered_results]
        
        return {
            'context': mock_passages,  # Return as list[str] as expected by signature field
            'passages': mock_passages,  # Keep for backwards compatibility
            'scores': mock_scores,
            'query': query,
            'retriever_config': {
                'catalog': catalog_name,
                'schema': schema_name,
                'index': index_name,
                'embedding_model': embedding_model,
                'query_type': query_type,
                'num_results': len(mock_passages),
                'score_threshold': score_threshold
            }
        }
    
    async def _execute_structured_retrieve(self, node: Any, query: str, context: ExecutionContext) -> Dict[str, Any]:
        """Execute StructuredRetrieve node"""
        genie_space_id = node.data.get('genie_space_id', '')
        
        # Validate mandatory fields
        if not genie_space_id:
            raise ValueError("StructuredRetrieve requires genie_space_id")
        
        # TODO: Implement actual Genie integration for SQL generation and execution
        # Simulate SQL generation and execution results
        mock_sql_query = f"SELECT * FROM sales_data WHERE description LIKE '%{query}%' ORDER BY date DESC LIMIT 10;"
        mock_query_description = f"Searching for sales records related to '{query}', ordered by most recent first"
        mock_sql_results = f"""
| Date | Product | Sales | Region |
|------|---------|-------|--------|
| 2024-01-15 | Product A related to {query} | $1,500 | North |
| 2024-01-14 | Product B matching {query} | $2,300 | South |
| 2024-01-13 | Another item for {query} | $800 | East |

**Total Records Found:** 3
**Query Execution Time:** 0.45s
        """.strip()
        
        return {
            'context': mock_sql_results,  # SQL results in markdown format
            'sql_query': mock_sql_query,  # Generated SQL query
            'query_description': mock_query_description,  # Description of the generated SQL query
            'query': query,
            'retriever_config': {
                'genie_space_id': genie_space_id,
                'retriever_type': 'StructuredRetrieve'
            }
        }
    
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