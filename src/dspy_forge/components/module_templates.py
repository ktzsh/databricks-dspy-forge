"""
DSPy module component templates.

Handles Predict, ChainOfThought, and other DSPy module types.
"""
import dspy

from typing import Dict, Any, List, Literal, get_type_hints
from dspy_forge.core.templates import NodeTemplate, CodeGenerationContext
from dspy_forge.core.dspy_types import DSPyModuleType
from dspy_forge.core.logging import get_logger
from dspy_forge.core.lm_config import parse_model_name

logger = get_logger(__name__)

class BaseModuleTemplate(NodeTemplate):
    """Base template for DSPy module nodes"""
    
    def _create_dynamic_signature(self, instruction: str):
        """Create dynamic signature class for execution"""
        # Get field information
        input_fields = self._get_connected_fields(is_input=True)
        output_fields = self._get_connected_fields(is_input=False)
        
        # Build class attributes dictionary
        class_attrs = {}
        
        # Add docstring
        class_attrs['__annotations__'] = {}
        if instruction:
            class_attrs['__doc__'] = instruction
        
        # Add input fields
        for field_name in input_fields:
            field_type, field_desc, enum_values = self._get_field_info(field_name, is_input=True)
            python_type = self._convert_ui_type_to_python_actual(field_type, enum_values)
            class_attrs['__annotations__'][field_name] = python_type
            if field_desc:
                class_attrs[field_name] = dspy.InputField(desc=field_desc)
            else:
                class_attrs[field_name] = dspy.InputField()

        # Add module-specific fields to class_attrs
        self._add_module_specific_fields_to_dict(class_attrs)

        # Add output fields
        for field_name in output_fields:
            if isinstance(self, ChainOfThoughtTemplate) and field_name == 'reasoning':
                # Let reasoning be autoadded by dspy we only show it in UI
                continue
            field_type, field_desc, enum_values = self._get_field_info(field_name, is_input=False)
            python_type = self._convert_ui_type_to_python_actual(field_type, enum_values)
            class_attrs['__annotations__'][field_name] = python_type
            if field_desc:
                class_attrs[field_name] = dspy.OutputField(desc=field_desc)
            else:
                class_attrs[field_name] = dspy.OutputField()
        
        # Create the class with proper field definitions
        DynamicSignature = type('DynamicSignature', (dspy.Signature,), class_attrs)
        
        return DynamicSignature
    
    def _add_module_specific_fields(self, signature_class):
        """Add module-specific fields to signature - override in subclasses"""
        pass
    
    def _add_module_specific_fields_to_dict(self, class_attrs: dict):
        """Add module-specific fields to class attributes dict - override in subclasses"""
        pass
    
    def _generate_signature_code(self, signature_name: str, instruction: str, 
                               input_fields: List[str], output_fields: List[str]) -> str:
        """Generate signature class code"""
        lines = [f"class {signature_name}(dspy.Signature):"]
        
        if instruction:
            lines.append(f'    """{instruction}"""')
        
        # Add input fields
        for field_name in input_fields:
            field_type, field_desc, enum_values = self._get_field_info(field_name, is_input=True)
            python_type = self._convert_ui_type_to_python(field_type, enum_values)
            if field_desc:
                lines.append(f"    {field_name}: {python_type} = dspy.InputField(desc='{field_desc}')")
            else:
                lines.append(f"    {field_name}: {python_type} = dspy.InputField()")

        # Add module-specific signature fields
        self._add_signature_specific_fields(lines)

        # Add output fields
        for field_name in output_fields:
            if isinstance(self, ChainOfThoughtTemplate) and field_name == 'reasoning':
                # Let reasoning be autoadded by dspy we only show it in UI
                continue
            field_type, field_desc, enum_values = self._get_field_info(field_name, is_input=False)
            python_type = self._convert_ui_type_to_python(field_type, enum_values)
            if field_desc:
                lines.append(f"    {field_name}: {python_type} = dspy.OutputField(desc='{field_desc}')")
            else:
                lines.append(f"    {field_name}: {python_type} = dspy.OutputField()")
        
        return '\n'.join(lines)
    
    def _add_signature_specific_fields(self, lines: List[str]):
        """Add module-specific fields to signature code - override in subclasses"""
        pass
    
    def generate_code(self, context: CodeGenerationContext) -> Dict[str, Any]:
        """Generate code for DSPy module node"""
        module_type_str = self.node_data.get('module_type', 'Unknown')
        model_name = self.node_data.get('model', '')
        instruction = self.node_data.get('instruction', '')
        
        # Get input and output fields
        input_fields = self._get_connected_fields(is_input=True)
        output_fields = self._get_connected_fields(is_input=False)
        
        # Generate unique signature name
        signature_key = (module_type_str, tuple(input_fields), tuple(output_fields), instruction)
        signature_name = context.get_signature_name(signature_key)
        
        # Generate signature class code
        signature_code = self._generate_signature_code(signature_name, instruction, input_fields, output_fields)
        
        # Generate instance code
        node_count = context.get_node_count(module_type_str)
        instance_var = f"{module_type_str.lower()}_{node_count}"

        # Store mapping for optimization loading
        context.node_to_var_mapping[self.node_id] = instance_var

        instance_code = self._generate_instance_code(instance_var, signature_name)
        
        # Generate forward method code
        input_args = ", ".join([f"{field}={field}" for field in input_fields])
        result_var = f"result_{context.get_result_count()}"

        forward_lines = []
        if model_name and model_name != 'default':
            # Import create_lm helper at the top of generated code
            context.add_import("from dspy_forge.core.lm_config import create_lm")
            forward_lines.append(f"        with dspy.context(lm=create_lm('{model_name}')):")
            forward_lines.append(f"            {result_var} = self.{instance_var}({input_args})")
        else:
            forward_lines.append(f"        {result_var} = self.{instance_var}({input_args})")

        # Extract output fields
        for field in output_fields:
            forward_lines.append(f"        {field} = {result_var}.{field}")
        forward_lines[-1] += "\n"

        forward_code = '\n'.join(forward_lines)
        
        return {
            'signature': signature_code,
            'instance': instance_code,
            'forward': forward_code,
            'dependencies': [],
            'instance_var': instance_var,
            'signature_name': signature_name
        }
    
    def _generate_instance_code(self, instance_var: str, signature_name: str) -> str:
        """Generate instance creation code - override in subclasses"""
        module_type_str = self.node_data.get('module_type', 'Unknown')
        return f"        self.{instance_var} = dspy.{module_type_str}({signature_name})"


class PredictTemplate(BaseModuleTemplate):
    """Template for Predict module nodes"""

    def initialize(self, context: Any):
        """
        Initialize Predict module as a DSPy component.
        Returns a DSPy.Predict instance which has built-in call() and acall() methods.
        """
        instruction = self.node_data.get('instruction', '')
        signature_class = self._create_dynamic_signature(instruction)
        return dspy.Predict(signature_class)
    
    def _generate_instance_code(self, instance_var: str, signature_name: str) -> str:
        """Generate Predict instance creation code"""
        return f"        self.{instance_var} = dspy.Predict({signature_name})"


class ChainOfThoughtTemplate(BaseModuleTemplate):
    """Template for ChainOfThought module nodes"""

    def initialize(self, context: Any):
        """
        Initialize ChainOfThought module as a DSPy component.
        Returns a DSPy.ChainOfThought instance which has built-in call() and acall() methods.
        """
        instruction = self.node_data.get('instruction', '')
        signature_class = self._create_dynamic_signature(instruction)
        return dspy.ChainOfThought(signature_class)

    def _generate_instance_code(self, instance_var: str, signature_name: str) -> str:
        """Generate ChainOfThought instance creation code"""
        return f"        self.{instance_var} = dspy.ChainOfThought({signature_name})"


class ReActTemplate(BaseModuleTemplate):
    """Template for ReAct module nodes with tool support"""

    def _get_connected_tools(self):
        """Get tool nodes connected to this ReAct module via tool handles"""
        from dspy_forge.models.workflow import NodeType
        from dspy_forge.components.tool_templates import MCPToolTemplate, UCFunctionTemplate

        tools = []
        # Find edges coming into this node's 'tools' handle
        # Tool connections use targetHandle='tools' to distinguish from regular data flow
        incoming_edges = [
            edge for edge in self.workflow.edges
            if edge.target == self.node_id and edge.targetHandle == 'tools'
        ]

        for edge in incoming_edges:
            source_node = next((n for n in self.workflow.nodes if n.id == edge.source), None)
            if source_node and source_node.type == NodeType.TOOL:
                # Support both snake_case (backend) and camelCase (frontend)
                tool_type = source_node.data.get('tool_type') or source_node.data.get('toolType')
                if tool_type == 'MCP_TOOL':
                    template = MCPToolTemplate(source_node, self.workflow)
                    tools.append(('mcp', template, source_node.id))
                elif tool_type == 'UC_FUNCTION':
                    template = UCFunctionTemplate(source_node, self.workflow)
                    tools.append(('uc', template, source_node.id))

        return tools

    def initialize(self, context: Any):
        """
        Initialize ReAct module as a DSPy component.
        Returns a DSPy.ReAct instance with tools loaded (from context for MCP, directly for UC).
        """
        instruction = self.node_data.get('instruction', '')
        signature_class = self._create_dynamic_signature(instruction)

        # Load tools from connected tool nodes
        tools_list = []
        connected_tools = self._get_connected_tools()

        logger.info(f"ReAct module {self.node_id} has {len(connected_tools)} connected tool nodes")

        # Load each tool using the template's load_tools() method, passing context
        for tool_type, tool_template, tool_node_id in connected_tools:
            try:
                # Call the template's load_tools() method with context
                # For MCP tools, this retrieves pre-loaded tools from context
                # For UC Function tools, this loads them synchronously
                loaded_tools = tool_template.load_tools(context)
                tools_list.extend(loaded_tools)
                logger.info(f"Loaded {len(loaded_tools)} tools from {tool_type} tool node {tool_node_id}")
            except Exception as e:
                logger.error(f"Failed to load {tool_type} tool from node {tool_node_id}: {e}")

        # Load global tools if requested
        global_tools = context.get_loaded_tools(f"global_{self.node_id}")
        if global_tools:
            tools_list.extend(global_tools)
            logger.info(f"Added {len(global_tools)} global tools to ReAct module {self.node_id}")

        logger.info(f"ReAct module {self.node_id} loaded {len(tools_list)} total tools")

        # Create ReAct instance with tools
        react_instance = dspy.ReAct(signature_class, tools=tools_list, max_iters=3)

        return react_instance

    def _add_signature_specific_fields_to_dict(self, class_attrs: dict):
        """Add tools field to signature for ReAct"""
        # ReAct modules should have a tools field in their signature
        # This allows the LLM to see available tools
        pass

    def _generate_instance_code(self, instance_var: str, signature_name: str) -> str:
        """Generate ReAct instance creation code with tool loading"""
        connected_tools = self._get_connected_tools()

        if not connected_tools:
            # No tools connected, simple ReAct
            return f"        self.{instance_var} = dspy.ReAct({signature_name}, max_iters=3)"

        # With tools, we need to load them first and then instantiate ReAct
        # Tool loading happens in __init__, so we generate the instance code
        # that uses the loaded tools
        tool_var_names = [f"tools_{instance_var}_{i}" for i in range(len(connected_tools))]

        # Flatten all tool lists into a single list
        instance_code = f"        # ReAct with {len(connected_tools)} tool source(s)\n"
        instance_code += f"        all_tools = []\n"
        for tool_var in tool_var_names:
            instance_code += f"        all_tools.extend(self.{tool_var})\n"
        instance_code += f"        self.{instance_var} = dspy.ReAct({signature_name}, tools=all_tools, max_iters=3)"

        return instance_code

    def generate_code(self, context: CodeGenerationContext) -> Dict[str, Any]:
        """Generate code for ReAct module with tools"""
        # Get base code generation
        base_result = super().generate_code(context)

        # Add tool-specific imports and initialization
        connected_tools = self._get_connected_tools()

        if connected_tools:
            # Add tool loading methods
            context.add_import("import os")
            context.add_import("from dspy_forge.core.logging import get_logger")
            context.add_import("logger = get_logger(__name__)")

            tool_methods = []
            tool_init_calls = []  # Calls in __init__ to load tools

            for i, (tool_type, tool_template, tool_node_id) in enumerate(connected_tools):
                tool_var = f"tools_{base_result['instance_var']}_{i}"
                tool_config = tool_template.get_tool_config()

                # Generate tool loading method code
                method_code = tool_template.generate_tool_loading_method(f"{base_result['instance_var']}_{i}")
                tool_methods.append(method_code)

                if tool_type == 'mcp':
                    # MCP tools are loaded async, so we need to handle that
                    tool_init_calls.append(f"        # MCP tools for {tool_config.get('tool_name', 'unknown')} will be loaded async")
                    tool_init_calls.append(f"        self.{tool_var} = []  # Placeholder, loaded via await _load_{base_result['instance_var']}_{i}_tools()")
                elif tool_type == 'uc':
                    # UC tools are sync
                    tool_init_calls.append(f"        self.{tool_var} = self._load_{base_result['instance_var']}_{i}_tools()")

            # Add tool loading to class definition
            base_result['tool_methods'] = tool_methods
            base_result['tool_init_calls'] = tool_init_calls

        return base_result