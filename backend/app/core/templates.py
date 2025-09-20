"""
Base template system for unified workflow execution and code generation.

This module provides the base classes and interfaces that component templates 
must implement to support both execution and code generation.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
from app.models.workflow import NodeType


class CodeGenerationContext:
    """Context for code generation tracking"""
    
    def __init__(self):
        self.signatures_created = set()
        self.node_counts = {}
        self.result_count = 0
        self.signature_names = {}
    
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
    async def execute(self, inputs: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """Execute the node with given inputs
        
        Args:
            inputs: Input data for the node
            context: Execution context containing workflow state
            
        Returns:
            Dict containing the execution results
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
        """Get field names from connected signature field nodes"""
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
        
        return fields
    
    def _get_field_info(self, field_name: str, is_input: bool = True) -> Tuple[str, str]:
        """Get field type and description from connected signature field nodes"""
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
                        return field_type, field_desc
        
        return 'str', ''
    
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