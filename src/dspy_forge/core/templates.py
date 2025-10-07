"""
Base template system for unified workflow execution and code generation.

This module provides the base classes and interfaces that component templates 
must implement to support both execution and code generation.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
from dspy_forge.models.workflow import NodeType


class CodeGenerationContext:
    """Context for code generation tracking"""

    def __init__(self):
        self.signatures_created = set()
        self.node_counts = {}
        self.result_count = 0
        self.signature_names = {}
        self.node_to_var_mapping = {}  # Maps node_id -> instance_var for optimization loading
    
    def get_signature_name(self, signature_key: tuple) -> str:
        """Get or create unique signature name"""
        if signature_key not in self.signature_names:
            module_type_str = signature_key[0]
            existing_count = len([s for s in self.signatures_created if s[0] == module_type_str])
            signature_name = f"{module_type_str}Signature_{existing_count + 1}"
            self.signature_names[signature_key] = signature_name
            self.signatures_created.add(signature_key)
        
        return self.signature_names[signature_key]
    
    def get_node_count(self, node_type: str) -> int:
        """Get and increment node count"""
        self.node_counts[node_type] = self.node_counts.get(node_type, 0) + 1
        return self.node_counts[node_type]
    
    def get_result_count(self) -> int:
        """Get and increment result count"""
        self.result_count += 1
        return self.result_count


class NodeTemplate(ABC):
    """Base template class for workflow nodes"""
    
    def __init__(self, node: Any, workflow: Any):
        self.node = node
        self.workflow = workflow
        self.node_id = node.id
        self.node_type = node.type
        self.node_data = node.data
    
    @abstractmethod
    def initialize(self, context: Any) -> Optional[Any]:
        """
        Initialize and return a component with call/acall interface.

        Args:
            context: Execution context containing workflow state

        Returns:
            Component instance (DSPy module, wrapper, or self) with call() and acall() methods.
            Can be:
            - DSPy module (Predict, ChainOfThought) - has built-in call/acall
            - Wrapper component (retrievers) - custom call/acall
            - Self (logic, signature fields) - implements call/acall
            - None if component cannot be initialized
        """
        pass
    
    @abstractmethod
    def generate_code(self, context: CodeGenerationContext) -> Dict[str, Any]:
        """Generate code for this node
        
        Args:
            context: Code generation context for tracking state
            
        Returns:
            Dict containing:
            - 'signature': Signature class code (if needed)
            - 'instance': Instance creation code
            - 'forward': Forward method code
            - 'dependencies': Required imports/dependencies
            - 'instance_var': Variable name for this instance
        """
        pass
    
    def _get_connected_fields(self, is_input: bool = True) -> List[str]:
        """Get field names from connected signature field nodes and field selector logic nodes"""
        fields = []

        if is_input:
            edges = [edge for edge in self.workflow.edges if edge.target == self.node_id]
        else:
            edges = [edge for edge in self.workflow.edges if edge.source == self.node_id]

        for edge in edges:
            node_id = edge.source if is_input else edge.target
            node = next((n for n in self.workflow.nodes if n.id == node_id), None)

            if node and node.type == NodeType.SIGNATURE_FIELD:
                node_fields = node.data.get('fields', [])
                for field_data in node_fields:
                    field_name = field_data.get('name')
                    if field_name and field_name not in fields:
                        fields.append(field_name)
            elif node and node.type == NodeType.LOGIC:
                # Handle field selector logic nodes
                logic_type = node.data.get('logic_type')
                if logic_type == 'FieldSelector':
                    # Get selected fields from field selector
                    selected_fields = node.data.get('selected_fields', [])
                    field_mappings = node.data.get('field_mappings', {})

                    for field_name in selected_fields:
                        # Use mapped name if provided, otherwise use original name
                        output_name = field_mappings.get(field_name, field_name)
                        if output_name and output_name not in fields:
                            fields.append(output_name)

        return fields
    
    def _get_field_info(self, field_name: str, is_input: bool = True) -> Tuple[str, str, Optional[List[str]]]:
        """Get field type, description, and enum values from connected signature field nodes and field selector logic nodes"""
        if is_input:
            edges = [edge for edge in self.workflow.edges if edge.target == self.node_id]
        else:
            edges = [edge for edge in self.workflow.edges if edge.source == self.node_id]

        for edge in edges:
            node_id = edge.source if is_input else edge.target
            node = next((n for n in self.workflow.nodes if n.id == node_id), None)

            if node and node.type == NodeType.SIGNATURE_FIELD:
                fields = node.data.get('fields', [])
                for field_data in fields:
                    if field_data.get('name') == field_name:
                        field_type = field_data.get('type', 'str')
                        field_desc = field_data.get('description', '')
                        enum_values = field_data.get('enum_values', None)
                        return field_type, field_desc, enum_values
            elif node and node.type == NodeType.LOGIC:
                # Handle field selector logic nodes
                logic_type = node.data.get('logic_type')
                if logic_type == 'FieldSelector':
                    selected_fields = node.data.get('selected_fields', [])
                    field_mappings = node.data.get('field_mappings', {})

                    # Check if this field comes from the field selector
                    for selected_field in selected_fields:
                        output_name = field_mappings.get(selected_field, selected_field)
                        if output_name == field_name:
                            # Trace back to find the original field type from upstream nodes
                            return self._trace_field_info_upstream(node.id, selected_field)

        raise ValueError(
            f"Field '{field_name}' not found in connected SignatureField or FieldSelector nodes for node '{self.node_id}'"
        )

    def _get_field_info_legacy(self, field_name: str, is_input: bool = True) -> Tuple[str, str]:
        """Legacy version that returns 2 values (for backward compatibility)"""
        field_type, field_desc, enum_values = self._get_field_info(field_name, is_input)
        return field_type, field_desc

    def _trace_field_info_upstream(self, field_selector_node_id: str, original_field_name: str) -> Tuple[str, str, Optional[List[str]]]:
        """Trace upstream from field selector to find original field type, description, and enum values"""
        # Find edges coming into the field selector node
        upstream_edges = [edge for edge in self.workflow.edges if edge.target == field_selector_node_id]

        for edge in upstream_edges:
            upstream_node = next((n for n in self.workflow.nodes if n.id == edge.source), None)

            if upstream_node and upstream_node.type == NodeType.SIGNATURE_FIELD:
                fields = upstream_node.data.get('fields', [])
                for field_data in fields:
                    if field_data.get('name') == original_field_name:
                        field_type = field_data.get('type', 'str')
                        field_desc = field_data.get('description', '')
                        enum_values = field_data.get('enum_values', None)
                        return field_type, field_desc, enum_values
            elif upstream_node and upstream_node.type == NodeType.LOGIC:
                # If upstream is another logic node, trace further
                upstream_logic_type = upstream_node.data.get('logic_type')
                if upstream_logic_type == 'FieldSelector':
                    # Recursively trace through nested field selectors
                    upstream_selected_fields = upstream_node.data.get('selected_fields', [])
                    upstream_field_mappings = upstream_node.data.get('field_mappings', {})

                    # Find the original field name in the upstream field selector
                    for upstream_field in upstream_selected_fields:
                        upstream_output = upstream_field_mappings.get(upstream_field, upstream_field)
                        if upstream_output == original_field_name:
                            return self._trace_field_info_upstream(upstream_node.id, upstream_field)

        raise ValueError(
            f"Field '{original_field_name}' not found upstream of FieldSelector node '{field_selector_node_id}'"
        )

    def _convert_ui_type_to_python(self, ui_type: str, enum_values: Optional[List[str]] = None) -> str:
        """Convert UI field type to Python type annotation"""
        if ui_type == 'enum' and enum_values:
            # Generate Literal type hint for enums
            formatted_values = ', '.join([f'"{val}"' for val in enum_values])
            return f'Literal[{formatted_values}]'

        type_mapping = {
            'str': 'str',
            'int': 'int',
            'bool': 'bool',
            'float': 'float',
            'list[str]': 'List[str]',
            'list[int]': 'List[int]',
            'dict': 'Dict',
            'list[dict[str, Any]]': 'List[Dict[str, Any]]',
            'Any': 'Any',
            'enum': 'str'  # Fallback if no enum values provided
        }
        return type_mapping.get(ui_type, 'str')


class TemplateFactory:
    """Factory for creating node templates"""
    
    _template_registry = {}
    
    @classmethod
    def register_template(cls, node_type: NodeType, template_class: type):
        """Register a template class for a node type"""
        cls._template_registry[node_type] = template_class
    
    @classmethod
    def create_template(cls, node: Any, workflow: Any) -> NodeTemplate:
        """Create appropriate template for node type"""
        template_class = cls._template_registry.get(node.type)
        if not template_class:
            raise ValueError(f"No template registered for node type: {node.type}")
        
        return template_class(node, workflow)
    
    @classmethod
    def get_registered_types(cls) -> List[NodeType]:
        """Get list of registered node types"""
        return list(cls._template_registry.keys())