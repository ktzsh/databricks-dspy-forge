from typing import Dict, Any, List, Tuple
from datetime import datetime

from dspy_forge.models.workflow import Workflow, NodeType
from dspy_forge.storage.factory import get_storage_backend
from dspy_forge.core.logging import get_logger
from dspy_forge.utils.workflow_utils import (
    get_execution_order,
    identify_router_nodes,
    get_branch_paths,
    find_branch_merge_point
)
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

            # Identify router nodes
            router_node_ids = identify_router_nodes(workflow)

            # Build a mapping of router_id -> branch_paths
            router_branch_map = {}
            for router_id in router_node_ids:
                router_branch_map[router_id] = get_branch_paths(workflow, router_id)

            # Generate code for each node using templates
            signatures = []
            instances = []
            forward_code_blocks = []
            instance_vars = []
            class_definitions = []
            tool_methods = []  # Tool loading methods
            tool_init_calls = []  # Tool initialization calls in __init__
            processed_nodes = set()  # Track nodes already handled (in branches)

            # First pass: collect all non-branch node code
            node_code_map = {}  # Map node_id -> generated code

            for node_id in execution_order:
                node = next((n for n in workflow.nodes if n.id == node_id), None)
                if not node:
                    continue

                # Create template for this node
                template = TemplateFactory.create_template(node, workflow)

                # Generate code for this node
                node_code = template.generate_code(context)
                node_code_map[node_id] = node_code

                # Collect code components (except forward - handled separately)
                if node_code.get('class_definition'):
                    class_definitions.append(node_code['class_definition'])

                if node_code.get('signature'):
                    signatures.append(node_code['signature'])

                if node_code.get('instance'):
                    instances.append(node_code['instance'])

                if node_code.get('instance_var'):
                    instance_vars.append(node_code['instance_var'])

                # Collect tool-specific code (for ReAct nodes)
                if node_code.get('tool_methods'):
                    tool_methods.extend(node_code['tool_methods'])

                if node_code.get('tool_init_calls'):
                    tool_init_calls.extend(node_code['tool_init_calls'])

            # Second pass: generate forward method with router branching
            for node_id in execution_order:
                if node_id in processed_nodes:
                    continue

                node = next((n for n in workflow.nodes if n.id == node_id), None)
                if not node:
                    continue

                # Check if this is a router node
                if node_id in router_node_ids:
                    # Generate if-elif-else block for router
                    router_code = self._generate_router_code(
                        workflow, node, router_branch_map[node_id],
                        node_code_map, context
                    )
                    forward_code_blocks.append(router_code)

                    # Mark all branch nodes as processed
                    for branch_nodes in router_branch_map[node_id].values():
                        processed_nodes.update(branch_nodes)
                    processed_nodes.add(node_id)
                else:
                    # Regular node - add its forward code
                    node_code = node_code_map.get(node_id, {})
                    if node_code.get('forward'):
                        forward_code_blocks.append(node_code['forward'])
                    processed_nodes.add(node_id)
            
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
            code_lines.append("")

            # Add tool initialization calls first (before creating module instances)
            if tool_init_calls:
                code_lines.append("        # Load tools")
                for tool_init_call in tool_init_calls:
                    if tool_init_call.strip():
                        code_lines.append(tool_init_call)
                code_lines.append("")

            # Add instance creation code
            for instance in instances:
                if instance.strip():
                    code_lines.append(instance)

            code_lines.append("")

            # Check if there are async tool methods (MCP tools)
            has_async_tools = any('async def' in method for method in tool_methods)
            
            # Add tool loading methods to the class (after __init__)
            if tool_methods:
                for tool_method in tool_methods:
                    if tool_method.strip():
                        code_lines.append(tool_method)
                        code_lines.append("")
            
            # Generate initialize method if there are async tools
            if has_async_tools:
                self._generate_initialize_method(tool_methods, instances, instance_vars, code_lines)

            # Generate forward method
            code_lines.append("    def forward(self, " + ", ".join(start_fields) + "):")

            # Add forward code blocks
            for forward_block in forward_code_blocks:
                if forward_block.strip():
                    code_lines.append(forward_block)
            
            # Return final prediction
            return_args = ", ".join([f"{field}={field}" for field in end_fields])
            code_lines.append(f"        return dspy.Prediction({return_args})")
            
            # Generate main method
            self._generate_main_method(start_fields, code_lines, has_async_tools)
            
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

    def _generate_main_method(self, start_fields: List[str], code_lines: List[str], has_async_tools: bool = False):
        """Generate the main execution method"""
        code_lines.append("")
        if has_async_tools:
            # Generate async main for MCP tools
            code_lines.append("if __name__ == '__main__':")
            code_lines.append("    import asyncio")
            code_lines.append("")
            code_lines.append("    async def main():")
            code_lines.append("        # Initialize the compound program")
            code_lines.append("        program = CompoundProgram()")
            code_lines.append("        ")
            code_lines.append("        # Load async tools (MCP)")
            code_lines.append("        await program.initialize()")
            code_lines.append("")
            code_lines.append("        # Example input")
            example_input = {field: f"example_{field}" for field in start_fields}
            input_str = ", ".join([f"{k}='{v}'" for k, v in example_input.items()])
            code_lines.append(f"        result = program({input_str})")
            code_lines.append("        print('Result:', result)")
            code_lines.append("")
            code_lines.append("    asyncio.run(main())")
        else:
            # Generate regular main
            code_lines.append("if __name__ == '__main__':")
            code_lines.append("    # Initialize the compound program")
            code_lines.append("    program = CompoundProgram()")
            code_lines.append("")
            code_lines.append("    # Example input")
            example_input = {field: f"example_{field}" for field in start_fields}
            input_str = ", ".join([f"{k}='{v}'" for k, v in example_input.items()])
            code_lines.append(f"    result = program({input_str})")
            code_lines.append("    print('Result:', result)")

    def _generate_initialize_method(self, tool_methods: List[str], instances: List[str], instance_vars: List[str], code_lines: List[str]):
        """Generate async initialize method to load MCP tools and reinitialize modules"""
        code_lines.append("    async def initialize(self):")
        code_lines.append("        \"\"\"Load async tools (MCP) and update modules that use them\"\"\"")
        
        # Find all async tool loading methods and call them
        async_method_calls = []
        for method in tool_methods:
            if 'async def' in method:
                # Extract method name (e.g., "_load_react_1_0_tools")
                method_lines = method.strip().split('\n')
                method_def = next((line for line in method_lines if 'async def' in line), None)
                if method_def:
                    method_name = method_def.split('async def')[1].split('(')[0].strip()
                    # Extract variable name from method name (e.g., "react_1_0" from "_load_react_1_0_tools")
                    if method_name.startswith('_load_') and method_name.endswith('_tools'):
                        var_name = method_name.replace('_load_', '').replace('_tools', '')
                        async_method_calls.append((f"tools_{var_name}", method_name))
        
        # Call all async loading methods
        for tool_var, method_name in async_method_calls:
            code_lines.append(f"        self.{tool_var} = await self.{method_name}()")
        
        code_lines.append("")
        
        # Re-initialize modules that use these tools
        # Parse instances to find ReAct modules
        for instance in instances:
            if 'dspy.ReAct' in instance:
                # Extract instance variable and signature
                # Example: "        self.react_1 = dspy.ReAct(ReActSignature_1, tools=all_tools, max_iters=3)"
                instance_lines = instance.strip().split('\n')
                for line in instance_lines:
                    if 'self.' in line and '= dspy.ReAct' in line:
                        # Extract the instance variable name
                        instance_var = line.split('self.')[1].split('=')[0].strip()
                        # Extract the signature name
                        sig_match = line.split('dspy.ReAct(')[1].split(',')[0].strip()
                        
                        # Find which tool variable this instance uses by checking preceding lines
                        matching_tool_var = None
                        for tool_var, _ in async_method_calls:
                            # Check if this instance is associated with this tool variable
                            # by looking for the tool variable name pattern in instance variable
                            # e.g., "react_1" matches "tools_react_1_0"
                            tool_suffix = tool_var.replace('tools_', '').split('_')[0] + '_' + tool_var.replace('tools_', '').split('_')[1]
                            if tool_suffix in instance_var:
                                matching_tool_var = tool_var
                                break
                        
                        if matching_tool_var:
                            # Generate code to collect tools and reinitialize
                            code_lines.append(f"        # Update {instance_var} with loaded tools")
                            code_lines.append(f"        all_tools_{instance_var} = []")
                            code_lines.append(f"        all_tools_{instance_var}.extend(self.{matching_tool_var})")
                            
                            # Extract max_iters if present
                            max_iters = "3"
                            if "max_iters=" in line:
                                max_iters = line.split("max_iters=")[1].split(")")[0].split(",")[0].strip()
                            
                            code_lines.append(f"        self.{instance_var} = dspy.ReAct({sig_match}, tools=all_tools_{instance_var}, max_iters={max_iters})")
        
        code_lines.append("")

    def _generate_router_code(
        self,
        workflow: Workflow,
        router_node: Any,
        branch_paths: Dict[str, List[str]],
        node_code_map: Dict[str, Dict[str, Any]],
        context: CodeGenerationContext
    ) -> str:
        """
        Generate if-elif-else code for router node with branches.

        Args:
            workflow: The workflow
            router_node: The router node
            branch_paths: Dict mapping branch_id to list of node IDs in that branch
            node_code_map: Map of node_id to generated code dict
            context: Code generation context

        Returns:
            Generated if-elif-else code block as string
        """
        from dspy_forge.components.logic_templates import RouterTemplate

        # Get router configuration
        router_config = router_node.data.get('router_config') or router_node.data.get('routerConfig', {})
        branches = router_config.get('branches', [])

        if not branches:
            return "        # Router with no branches configured\n"

        # Create template to use helper methods
        template = RouterTemplate(router_node, workflow)

        code_lines = []
        code_lines.append("        # Router branching logic")
        code_lines.append("")

        default_branch = None
        non_default_branches = []

        for branch in branches:
            if branch.get('isDefault') or branch.get('is_default'):
                default_branch = branch
            else:
                non_default_branches.append(branch)

        # Generate if-elif-else structure
        for i, branch in enumerate(non_default_branches):
            branch_id = branch.get('branchId') or branch.get('branch_id')
            condition_config = branch.get('conditionConfig') or branch.get('condition_config', {})
            structured_conditions = condition_config.get('structuredConditions') or condition_config.get('structured_conditions', [])

            # Generate condition expression
            condition_expr = template._generate_condition_expression(structured_conditions)

            # Determine if/elif
            if i == 0:
                code_lines.append(f"        if {condition_expr}:")
            else:
                code_lines.append(f"        elif {condition_expr}:")

            # Add code for nodes in this branch
            branch_node_ids = branch_paths.get(branch_id, [])
            if branch_node_ids:
                for node_id in branch_node_ids:
                    node_code = node_code_map.get(node_id, {})
                    forward_code = node_code.get('forward', '')
                    if forward_code:
                        # Indent the forward code (add 4 more spaces)
                        indented_code = '\n'.join(
                            '    ' + line if line.strip() else line
                            for line in forward_code.split('\n')
                        )
                        code_lines.append(indented_code)
            else:
                code_lines.append("            pass  # No nodes in this branch")

        # Handle default branch
        if default_branch:
            code_lines.append("        else:")
            branch_id = default_branch.get('branchId') or default_branch.get('branch_id')
            branch_node_ids = branch_paths.get(branch_id, [])

            if branch_node_ids:
                for node_id in branch_node_ids:
                    node_code = node_code_map.get(node_id, {})
                    forward_code = node_code.get('forward', '')
                    if forward_code:
                        # Indent the forward code (add 4 more spaces)
                        indented_code = '\n'.join(
                            '    ' + line if line.strip() else line
                            for line in forward_code.split('\n')
                        )
                        code_lines.append(indented_code)
            else:
                code_lines.append("            pass  # No nodes in default branch")

        code_lines.append("")

        return '\n'.join(code_lines)
    


# Global compiler service instance
compiler_service = WorkflowCompilerService()