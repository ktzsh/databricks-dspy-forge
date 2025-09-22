"""
Logic component templates.

Handles IfElse, Merge, FieldSelector, and other logic node types.
"""

from typing import Dict, Any
from dspy_forge.core.templates import NodeTemplate, CodeGenerationContext
from dspy_forge.core.dspy_types import DSPyLogicType


class BaseLogicTemplate(NodeTemplate):
    """Base template for logic nodes"""
    
    def _evaluate_condition(self, condition: str, inputs: Dict[str, Any]) -> bool:
        """Evaluate a condition string (simplified implementation)"""
        if not condition:
            return True
        
        try:
            # Replace field names with actual values
            eval_string = condition
            for key, value in inputs.items():
                eval_string = eval_string.replace(key, str(value))
            
            # Basic safety check - only allow simple comparisons
            if any(op in eval_string for op in ['import', 'exec', 'eval', '__']):
                return True  # Default to true for unsafe conditions
            
            return bool(eval(eval_string))
        except:
            return True  # Default to true if evaluation fails


class IfElseTemplate(BaseLogicTemplate):
    """Template for IfElse logic nodes"""
    
    async def execute(self, inputs: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """Execute IfElse logic node"""
        condition = self.node_data.get('condition', '')
        
        # Evaluate condition
        condition_result = self._evaluate_condition(condition, inputs)
        
        return {
            'condition_result': condition_result,
            'branch': 'true' if condition_result else 'false',
            **inputs  # Pass through inputs
        }
    
    def generate_code(self, context: CodeGenerationContext) -> Dict[str, Any]:
        """Generate code for IfElse logic node"""
        condition = self.node_data.get('condition', '')
        instance_var = f"if_else_{context.get_node_count('if_else')}"
        
        # Generate condition evaluation code
        forward_lines = [
            f"        # IfElse logic: {condition}",
            f"        {instance_var}_condition = {repr(condition)}",
            f"        {instance_var}_result = self._evaluate_condition({instance_var}_condition, locals())",
            f"        condition_result = {instance_var}_result",
            f"        branch = 'true' if {instance_var}_result else 'false'"
        ]
        
        return {
            'signature': '',
            'instance': f"        # IfElse logic configured: {condition}",
            'forward': '\n'.join(forward_lines),
            'dependencies': [],
            'instance_var': instance_var
        }


class MergeTemplate(BaseLogicTemplate):
    """Template for Merge logic nodes"""
    
    async def execute(self, inputs: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """Execute Merge logic node (simple merge - combine all inputs)"""
        return inputs
    
    def generate_code(self, context: CodeGenerationContext) -> Dict[str, Any]:
        """Generate code for Merge logic node"""
        instance_var = f"merge_{context.get_node_count('merge')}"
        
        # Simple merge - no additional processing needed
        forward_lines = [
            f"        # Merge logic - pass through all inputs"
        ]
        
        return {
            'signature': '',
            'instance': f"        # Merge logic configured",
            'forward': '\n'.join(forward_lines),
            'dependencies': [],
            'instance_var': instance_var
        }


class FieldSelectorTemplate(BaseLogicTemplate):
    """Template for FieldSelector logic nodes"""
    
    async def execute(self, inputs: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """Execute FieldSelector logic node"""
        selected_fields = self.node_data.get('selectedFields', [])
        field_mappings = self.node_data.get('fieldMappings', {})
        
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
    
    def generate_code(self, context: CodeGenerationContext) -> Dict[str, Any]:
        """Generate code for FieldSelector logic node"""
        selected_fields = self.node_data.get('selectedFields', [])
        field_mappings = self.node_data.get('fieldMappings', {})
        instance_var = f"field_selector_{context.get_node_count('field_selector')}"
        
        # Generate field selection code
        forward_lines = [
            f"        # FieldSelector logic",
            f"        {instance_var}_selected = {selected_fields}",
            f"        {instance_var}_mappings = {field_mappings}",
        ]
        
        if selected_fields:
            forward_lines.extend([
                f"        {instance_var}_outputs = {{}}",
                f"        for field_name in {instance_var}_selected:",
                f"            if field_name in locals():",
                f"                output_name = {instance_var}_mappings.get(field_name, field_name)",
                f"                {instance_var}_outputs[output_name] = locals()[field_name]"
            ])
            # Add output assignments
            for field_name in selected_fields:
                output_name = field_mappings.get(field_name, field_name)
                forward_lines.append(f"        {output_name} = {instance_var}_outputs.get('{output_name}')")
        else:
            forward_lines.append(f"        # No fields selected - pass through all inputs")
        
        return {
            'signature': '',
            'instance': f"        # FieldSelector logic configured: {selected_fields}",
            'forward': '\n'.join(forward_lines),
            'dependencies': [],
            'instance_var': instance_var
        }