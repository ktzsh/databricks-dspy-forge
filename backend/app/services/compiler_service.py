import os
from typing import Dict, Any, List, Set, Tuple
from datetime import datetime

from app.models.workflow import Workflow, NodeType
from app.core.config import settings
from app.core.logging import get_logger
from app.core.dspy_types import DSPyModuleType
from app.utils.workflow_utils import (
    get_execution_order, 
    find_start_nodes,
    find_end_nodes
)

logger = get_logger(__name__)


class WorkflowCompilerService:
    """Service for compiling workflows to optimized DSPy code"""
    
    def __init__(self):
        self.compiled_workflows: Dict[str, str] = {}  # Cache compiled code
    
    def compile_workflow_to_code(self, workflow: Workflow, execution_context=None) -> str:
        """
        Compile a workflow to optimized DSPy code
        
        Args:
            workflow: The workflow to compile
            execution_context: Optional execution context for runtime data
            
        Returns:
            Generated DSPy code as string
        """
        try:
            code_lines = [
                "import dspy",
                "from typing import Any, List, Dict",
                ""
            ]
            
            # Extract all modules from the workflow
            module_nodes = [node for node in workflow.nodes if node.type == NodeType.MODULE]
            signature_field_nodes = [node for node in workflow.nodes if node.type == NodeType.SIGNATURE_FIELD]
            signatures_created = set()
            node_counts = {}
            module_instances = []
            
            # Find start and end nodes
            start_nodes = [node for node in signature_field_nodes if node.data.get('is_start', False) or node.data.get('isStart', False)]
            end_nodes = [node for node in signature_field_nodes if node.data.get('is_end', False) or node.data.get('isEnd', False)]
            
            # Get overall input and output fields
            start_fields = self._extract_field_names(start_nodes)
            end_fields = self._extract_field_names(end_nodes)
            
            if not start_fields:
                start_fields = ['input']
            if not end_fields:
                end_fields = ['output']
            
            # Generate unique signatures first
            signatures_created = self._generate_signatures(module_nodes, code_lines, workflow)
            
            # Generate CompoundProgram class
            code_lines.append("class CompoundProgram(dspy.Module):")
            code_lines.append("    def __init__(self):")
            code_lines.append("        super().__init__()")
            
            # Generate module instances in __init__
            module_instances = self._generate_module_instances(module_nodes, signatures_created, node_counts, code_lines, workflow)
            
            code_lines.append("")
            
            # Generate forward method
            self._generate_forward_method(workflow, start_fields, end_fields, module_instances, code_lines)
            
            # Generate main method
            self._generate_main_method(start_fields, code_lines)
            
            compiled_code = '\n'.join(code_lines)
            
            # Cache the compiled code
            self.compiled_workflows[workflow.id] = compiled_code
            
            return compiled_code
            
        except Exception as e:
            logger.error(f"Failed to compile workflow {workflow.id}: {e}")
            raise
    
    def save_compiled_workflow(self, workflow_id: str, workflow_code: str) -> str:
        """
        Save compiled workflow code to artifacts directory
        
        Args:
            workflow_id: ID of the workflow
            workflow_code: Generated code to save
            
        Returns:
            Path to saved file
        """
        if not settings.debug_compiler:
            logger.debug("Debug compiler disabled, skipping code save")
            return ""
            
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
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to save workflow code: {str(e)}")
            raise
    
    def get_compiled_code(self, workflow_id: str) -> str:
        """Get cached compiled code for a workflow"""
        return self.compiled_workflows.get(workflow_id, "")
    
    def _extract_field_names(self, nodes: List[Any]) -> List[str]:
        """Extract field names from signature field nodes"""
        fields = []
        for node in nodes:
            node_fields = node.data.get('fields', [])
            for field_data in node_fields:
                field_name = field_data.get('name')
                if field_name:
                    fields.append(field_name)
        return fields
    
    def _generate_signatures(self, module_nodes: List[Any], code_lines: List[str], workflow: Workflow) -> Set[tuple]:
        """Generate unique signature classes"""
        signatures_created = set()
        
        for node in module_nodes:
            module_type_str = node.data.get('module_type', 'Unknown')
            instruction = node.data.get('instruction', '')
            
            # Get input and output fields from connected signature nodes
            input_fields = self._get_expected_input_fields(node, workflow)
            if not input_fields:
                input_fields = ['input']
            output_fields = self._get_expected_output_fields(node, workflow)
            if not output_fields:
                output_fields = ['output']
            
            # Create signature key for deduplication
            signature_key = (module_type_str, tuple(input_fields), tuple(output_fields), instruction)
            
            if signature_key not in signatures_created:
                signatures_created.add(signature_key)
                
                # Generate unique signature name with simple numbering
                existing_sigs_of_type = len([s for s in signatures_created if s[0] == module_type_str])
                signature_name = f"{module_type_str}Signature_{existing_sigs_of_type}"
                
                # Add signature class
                code_lines.append(f"class {signature_name}(dspy.Signature):")
                if instruction:
                    code_lines.append(f'    """{instruction}"""')
                
                # Add input fields with types and descriptions
                for field_name in input_fields:
                    field_type, field_desc = self._get_field_info(node, field_name, workflow, is_input=True)
                    python_type = self._convert_ui_type_to_python(field_type)
                    if field_desc:
                        code_lines.append(f"    {field_name}: {python_type} = dspy.InputField(desc='{field_desc}')")
                    else:
                        code_lines.append(f"    {field_name}: {python_type} = dspy.InputField()")
                
                if module_type_str == "ChainOfThought":
                    code_lines.append(f"    rationale = dspy.OutputField(desc='Step-by-step reasoning')")
                    
                # Add output fields with types and descriptions  
                for field_name in output_fields:
                    field_type, field_desc = self._get_field_info(node, field_name, workflow, is_input=False)
                    python_type = self._convert_ui_type_to_python(field_type)
                    if field_desc:
                        code_lines.append(f"    {field_name}: {python_type} = dspy.OutputField(desc='{field_desc}')")
                    else:
                        code_lines.append(f"    {field_name}: {python_type} = dspy.OutputField()")
                
                code_lines.append("")
        
        return signatures_created
    
    def _generate_module_instances(self, module_nodes: List[Any], signatures_created: Set[tuple], 
                                 node_counts: Dict[str, int], code_lines: List[str], workflow: Workflow) -> List[tuple]:
        """Generate module instances in __init__ method"""
        module_instances = []
        
        for node in module_nodes:
            module_type_str = node.data.get('module_type', 'Unknown')
            node_counts[module_type_str] = node_counts.get(module_type_str, 0) + 1
            node_index = node_counts[module_type_str]
            
            # Find matching signature
            instruction = node.data.get('instruction', '')
            input_fields = self._get_expected_input_fields(node, workflow)
            if not input_fields:
                input_fields = ['input']
            output_fields = self._get_expected_output_fields(node, workflow)
            if not output_fields:
                output_fields = ['output']
            
            signature_key = (module_type_str, tuple(input_fields), tuple(output_fields), instruction)
            signature_index = list(signatures_created).index(signature_key) + 1
            
            signature_name = f"{module_type_str}Signature_{signature_index}"
            
            # Add module instantiation with cleaner naming
            module_var_name = f"{module_type_str.lower()}_{node_index}"
            module_instances.append((module_var_name, node.id))
            
            if module_type_str == "Predict":
                code_lines.append(f"        self.{module_var_name} = dspy.Predict({signature_name})")
            elif module_type_str == "ChainOfThought":
                code_lines.append(f"        self.{module_var_name} = dspy.ChainOfThought({signature_name})")
        
        return module_instances
    
    def _generate_forward_method(self, workflow: Workflow, start_fields: List[str], end_fields: List[str], 
                               module_instances: List[tuple], code_lines: List[str]):
        """Generate the forward method"""
        code_lines.append("    def forward(self, " + ", ".join(start_fields) + "):")
        
        # Get execution order
        execution_order = get_execution_order(workflow)
        
        # Generate forward logic based on execution order
        result_counter = 0
        for node_id in execution_order:
            node = next((n for n in workflow.nodes if n.id == node_id), None)
            if not node:
                continue
                
            if node.type == NodeType.MODULE:
                # Find the module instance
                module_instance = next((inst for inst in module_instances if inst[1] == node_id), None)
                if module_instance:
                    module_var_name = module_instance[0]
                    result_counter += 1
                    
                    # Get model name for this module
                    model_name = node.data.get('model', 'default')
                    
                    # Get inputs for this module
                    input_fields = self._get_expected_input_fields(node, workflow)
                    if not input_fields:
                        input_fields = start_fields
                    
                    # Generate module call with dspy.context and simple numbering
                    result_var = f"result_{result_counter}"
                    input_args = ", ".join([f"{field}={field}" for field in input_fields])
                    
                    if model_name and model_name != 'default':
                        code_lines.append(f"        with dspy.context(lm=dspy.LM('databricks/{model_name}')):")
                        code_lines.append(f"            {result_var} = self.{module_var_name}({input_args})")
                    else:
                        code_lines.append(f"        {result_var} = self.{module_var_name}({input_args})")
                    
                    # Extract outputs
                    output_fields = self._get_expected_output_fields(node, workflow)
                    if output_fields:
                        for field in output_fields:
                            code_lines.append(f"        {field} = {result_var}.{field}")
        
        # Return final prediction
        return_args = ", ".join([f"{field}={field}" for field in end_fields])
        code_lines.append(f"        return dspy.Prediction({return_args})")
    
    def _generate_main_method(self, start_fields: List[str], code_lines: List[str]):
        """Generate the main execution method"""
        code_lines.append("")
        code_lines.append("if __name__ == '__main__':")
        code_lines.append("    # Initialize the compound program")
        code_lines.append("    program = CompoundProgram()")
        code_lines.append("")
        code_lines.append("    # Example input")
        example_input = {field: f"example_{field}" for field in start_fields}
        input_str = ", ".join([f"{k}='{v}'" for k, v in example_input.items()])
        code_lines.append(f"    result = program({input_str})")
        code_lines.append("    print('Result:', result)")
    
    def _get_expected_input_fields(self, node: Any, workflow: Workflow) -> List[str]:
        """Get expected input field names from connected signature field nodes"""
        input_fields = []
        
        # Find incoming edges to this node
        incoming_edges = [edge for edge in workflow.edges if edge.target == node.id]
        
        for edge in incoming_edges:
            # Find the source node
            source_node = next((n for n in workflow.nodes if n.id == edge.source), None)
            if source_node and source_node.type == NodeType.SIGNATURE_FIELD:
                # Get field names from the source signature field
                fields = source_node.data.get('fields', [])
                for field_data in fields:
                    field_name = field_data.get('name')
                    if field_name and field_name not in input_fields:
                        input_fields.append(field_name)
        
        return input_fields
    
    def _get_expected_output_fields(self, node: Any, workflow: Workflow) -> List[str]:
        """Get expected output field names from connected signature field nodes"""
        output_fields = []
        
        # Find outgoing edges from this node
        outgoing_edges = [edge for edge in workflow.edges if edge.source == node.id]
        
        for edge in outgoing_edges:
            # Find the target node
            target_node = next((n for n in workflow.nodes if n.id == edge.target), None)
            if target_node and target_node.type == NodeType.SIGNATURE_FIELD:
                # Get field names from the target signature field
                fields = target_node.data.get('fields', [])
                for field_data in fields:
                    field_name = field_data.get('name')
                    if field_name and field_name not in output_fields:
                        output_fields.append(field_name)
        
        return output_fields
    
    def _get_field_info(self, node: Any, field_name: str, workflow: Workflow, is_input: bool = True) -> Tuple[str, str]:
        """Get field type and description from connected signature field nodes"""
        if is_input:
            # Find incoming edges to this node
            edges = [edge for edge in workflow.edges if edge.target == node.id]
        else:
            # Find outgoing edges from this node
            edges = [edge for edge in workflow.edges if edge.source == node.id]
        
        for edge in edges:
            # Find the connected signature field node
            if is_input:
                sig_node = next((n for n in workflow.nodes if n.id == edge.source), None)
            else:
                sig_node = next((n for n in workflow.nodes if n.id == edge.target), None)
            
            if sig_node and sig_node.type == NodeType.SIGNATURE_FIELD:
                # Get field info from the signature field
                fields = sig_node.data.get('fields', [])
                for field_data in fields:
                    if field_data.get('name') == field_name:
                        # Get type and description from the field data
                        field_type = field_data.get('type', 'str')
                        field_desc = field_data.get('description', '')
                        return field_type, field_desc
        return 'str', ''
    
    def _get_field_description(self, node: Any, field_name: str, workflow: Workflow, is_input: bool = True) -> str:
        """Get field description from connected signature field nodes (backwards compatibility)"""
        _, description = self._get_field_info(node, field_name, workflow, is_input)
        return description
    
    def _convert_ui_type_to_python(self, ui_type: str) -> str:
        """Convert UI field type to Python type annotation"""
        type_mapping = {
            'str': 'str',
            'int': 'int', 
            'bool': 'bool',
            'float': 'float',
            'list[str]': 'List[str]',
            'list[int]': 'List[int]',
            'dict': 'Dict',
            'list[dict[str, Any]]': 'List[Dict[str, Any]]',
            'Any': 'Any'
        }
        return type_mapping.get(ui_type, 'str')


# Global compiler service instance
compiler_service = WorkflowCompilerService()