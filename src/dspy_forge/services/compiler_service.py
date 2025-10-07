from typing import Dict, Any, List, Tuple
from datetime import datetime

from dspy_forge.models.workflow import Workflow, NodeType
from dspy_forge.storage.factory import get_storage_backend
from dspy_forge.core.logging import get_logger
from dspy_forge.utils.workflow_utils import get_execution_order
from dspy_forge.core.templates import TemplateFactory, CodeGenerationContext
from dspy_forge.components import registry  # This will auto-register all templates

logger = get_logger(__name__)


class WorkflowCompilerService:
    """Service for compiling workflows to optimized DSPy code"""
    
    def __init__(self):
        self.compiled_workflows: Dict[str, str] = {}  # Cache compiled code
    
    def compile_workflow_to_code(self, workflow: Workflow) -> Tuple[str, Dict[str, str]]:
        """
        Compile a workflow to optimized DSPy code using template system

        Args:
            workflow: The workflow to compile

        Returns:
            Tuple of (generated DSPy code as string, node_id to variable name mapping)
        """
        try:
            # Initialize code generation context
            context = CodeGenerationContext()
            
            # Check if workflow contains UnstructuredRetrieve nodes
            has_unstructured_retrieve = any(
                node.type == NodeType.RETRIEVER and 
                node.data.get('retriever_type') == 'UnstructuredRetrieve'
                for node in workflow.nodes
            )

            # Check if workflow contains StructuredRetrieve nodes
            has_structured_retrieve = any(
                node.type == NodeType.RETRIEVER and
                node.data.get('retriever_type') == 'StructuredRetrieve'
                for node in workflow.nodes
            )

            # Check if workflow contains enum type fields
            has_enum_fields = any(
                node.type == NodeType.SIGNATURE_FIELD and
                any(field.get('type') == 'enum' for field in node.data.get('fields', []))
                for node in workflow.nodes
            )

            code_lines = [
                "import dspy",
                "import mlflow",
                "",
            ]

            # Add typing imports
            if has_enum_fields:
                code_lines.append("from typing import Any, List, Dict, Optional, Literal")
            else:
                code_lines.append("from typing import Any, List, Dict, Optional")
            
            # Add DatabricksRM import only if needed
            if has_unstructured_retrieve:
                code_lines.extend([
                    "from dspy.retrievers.databricks_rm import DatabricksRM",
                ])
            if has_structured_retrieve:
                code_lines.extend([
                    "from databricks_ai_bridge.genie import Genie",
                    "from dspy.primitives.prediction import Prediction",
                    "from databricks_ai_bridge import ModelServingUserCredentials",
                    "from databricks.sdk import WorkspaceClient",
                    "",
                    "def get_user_authorized_client() -> Any:",
                    "    user_authorized_client = WorkspaceClient(",
                    "        credentials_strategy=ModelServingUserCredentials()",
                    "    )",
                    "    return user_authorized_client"
                ])
            
            code_lines.append("")

            # Find start and end nodes
            signature_field_nodes = [node for node in workflow.nodes if node.type == NodeType.SIGNATURE_FIELD]
            start_nodes = [node for node in signature_field_nodes if node.data.get('is_start', False) or node.data.get('isStart', False)]
            end_nodes = [node for node in signature_field_nodes if node.data.get('is_end', False) or node.data.get('isEnd', False)]
            
            # Get overall input and output fields
            start_fields = self._extract_field_names(start_nodes)
            end_fields = self._extract_field_names(end_nodes)
            
            if not start_fields:
                start_fields = ['input']
            if not end_fields:
                end_fields = ['output']
            
            # Get execution order
            execution_order, graph = get_execution_order(workflow)
            
            # Generate code for each node using templates
            signatures = []
            instances = []
            forward_code_blocks = []
            instance_vars = []
            class_definitions = []
            
            for node_id in execution_order:
                node = next((n for n in workflow.nodes if n.id == node_id), None)
                if not node:
                    continue
                
                # Create template for this node
                template = TemplateFactory.create_template(node, workflow)
                
                # Generate code for this node
                node_code = template.generate_code(context)
                
                # Collect code components
                if node_code.get('class_definition'):
                    class_definitions.append(node_code['class_definition'])

                if node_code.get('signature'):
                    signatures.append(node_code['signature'])
                
                if node_code.get('instance'):
                    instances.append(node_code['instance'])
                
                if node_code.get('forward'):
                    forward_code_blocks.append(node_code['forward'])
                
                if node_code.get('instance_var'):
                    instance_vars.append(node_code['instance_var'])
            
            # Generate class definitions
            for class_def in class_definitions:
                if class_def.strip():
                    code_lines.append(class_def)
                    code_lines.append("")

            # Add signatures to code (avoid duplicates)
            added_signature_names = set()
            for signature in signatures:
                if signature.strip():
                    # Extract signature class name (e.g., "PredictSignature_2" from "class PredictSignature_2(dspy.Signature):")
                    signature_name = signature.split('(')[0].replace('class', '').strip()
                    if signature_name not in added_signature_names:
                        code_lines.append(signature)
                        code_lines.append("")
                        added_signature_names.add(signature_name)
            
            # Check if workflow contains Router nodes (need helper methods)
            has_router = any(
                node.type == NodeType.LOGIC and
                node.data.get('logic_type') == 'Router'
                for node in workflow.nodes
            )

            # Generate CompoundProgram class
            code_lines.append("class CompoundProgram(dspy.Module):")
            code_lines.append("    def __init__(self):")
            code_lines.append("        super().__init__()")

            # Add instance creation code
            for instance in instances:
                if instance.strip():
                    code_lines.append(instance)
            
            code_lines.append("")
            
            # Generate forward method
            code_lines.append("")
            code_lines.append("    def forward(self, " + ", ".join(start_fields) + "):")

            # Add forward code blocks
            for forward_block in forward_code_blocks:
                if forward_block.strip():
                    code_lines.append(forward_block)
            
            # Return final prediction
            return_args = ", ".join([f"{field}={field}" for field in end_fields])
            code_lines.append(f"        return dspy.Prediction({return_args})")
            
            # Generate main method
            self._generate_main_method(start_fields, code_lines)
            
            compiled_code = '\n'.join(code_lines)

            # Cache the compiled code
            self.compiled_workflows[workflow.id] = compiled_code

            # Return code and node-to-variable mapping
            return compiled_code, context.node_to_var_mapping
            
        except Exception as e:
            logger.error(f"Failed to compile workflow {workflow.id}: {e}")
            raise
    
    async def save_compiled_workflow(self, workflow_id: str, workflow_code: str) -> bool:
        """
        Save compiled workflow code using storage backend

        Args:
            workflow_id: ID of the workflow
            workflow_code: Generated code to save

        Returns:
            True if successful, False otherwise
        """
        try:
            storage = await get_storage_backend()

            # Add header to workflow code
            workflow_code_with_header = f"# DSPy Workflow: {workflow_id}\n"
            workflow_code_with_header += f"# Generated at: {datetime.now().isoformat()}\n\n"
            workflow_code_with_header += workflow_code

            # Save using storage backend
            success = await storage.save_compiled_workflow(workflow_id, workflow_code_with_header, "program.py")

            if success:
                logger.info(f"Workflow code saved for workflow: {workflow_id}")
            else:
                logger.error(f"Failed to save workflow code for: {workflow_id}")

            return success

        except Exception as e:
            logger.error(f"Failed to save workflow code: {str(e)}")
            return False
    
    def get_compiled_code(self, workflow_id: str) -> str:
        """Get cached compiled code for a workflow"""
        return self.compiled_workflows.get(workflow_id, "")

    async def get_compiled_workflow_from_storage(self, workflow_id: str, filename: str = "program.py") -> str:
        """Get compiled workflow code from storage backend"""
        try:
            storage = await get_storage_backend()
            content = await storage.get_compiled_workflow(workflow_id, filename)
            return content or ""
        except Exception as e:
            logger.error(f"Failed to get compiled workflow {workflow_id} from storage: {e}")
            return ""
    
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
    


# Global compiler service instance
compiler_service = WorkflowCompilerService()