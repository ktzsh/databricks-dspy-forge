"""
Signature field component template.

Handles pass-through validation for input/output signature fields.
"""

from typing import Dict, Any
from app.core.templates import NodeTemplate, CodeGenerationContext


class SignatureFieldTemplate(NodeTemplate):
    """Template for signature field nodes"""
    
    async def execute(self, inputs: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """Execute signature field node (pass-through with validation)"""
        fields = self.node_data.get('fields', [])
        outputs = {}
        
        is_start = self.node_data.get('is_start', False) or self.node_data.get('isStart', False)
        is_end = self.node_data.get('is_end', False) or self.node_data.get('isEnd', False)
        
        # For start nodes, validate that required fields are present
        # For end nodes, just pass through whatever is available
        for field_data in fields:
            field_name = field_data.get('name')
            required = field_data.get('required', True)
            
            if field_name in inputs:
                outputs[field_name] = inputs[field_name]
            elif required and is_start:
                raise ValueError(f"Required field '{field_name}' not found in inputs for start node")
        
        # If no outputs were generated for an end node, pass through all inputs
        if is_end and not outputs:
            outputs = inputs.copy()
        
        return outputs
    
    def generate_code(self, context: CodeGenerationContext) -> Dict[str, Any]:
        """Generate code for signature field node (no executable code needed)"""
        return {
            'signature': '',
            'instance': '',
            'forward': '',
            'dependencies': [],
            'instance_var': ''
        }