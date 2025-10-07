"""
Logic component templates.

Handles Router, Merge, FieldSelector, and other logic node types.
"""

from typing import Dict, Any, List, Union
from dspy_forge.core.templates import NodeTemplate, CodeGenerationContext
from dspy_forge.core.dspy_types import DSPyLogicType
from dspy_forge.core.logging import get_logger
from dspy_forge.models.workflow import ComparisonOperator

logger = get_logger(__name__)

class BaseLogicTemplate(NodeTemplate):
    """Base template for logic nodes"""

    def _safe_evaluate_operator(self, field_value: Any, operator: str, compare_value: Any) -> bool:
        """Safely evaluate a single operator comparison"""
        try:
            if operator == "==":
                return field_value == compare_value
            elif operator == "!=":
                return field_value != compare_value
            elif operator == ">":
                return float(field_value) > float(compare_value)
            elif operator == "<":
                return float(field_value) < float(compare_value)
            elif operator == ">=":
                return float(field_value) >= float(compare_value)
            elif operator == "<=":
                return float(field_value) <= float(compare_value)
            elif operator == "contains":
                return str(compare_value) in str(field_value)
            elif operator == "not_contains":
                return str(compare_value) not in str(field_value)
            elif operator == "in":
                if isinstance(compare_value, (list, tuple, set)):
                    return field_value in compare_value
                return str(field_value) in str(compare_value)
            elif operator == "not_in":
                if isinstance(compare_value, (list, tuple, set)):
                    return field_value not in compare_value
                return str(field_value) not in str(compare_value)
            elif operator == "startswith":
                return str(field_value).startswith(str(compare_value))
            elif operator == "endswith":
                return str(field_value).endswith(str(compare_value))
            elif operator == "is_empty":
                return not field_value or (isinstance(field_value, (list, dict, str)) and len(field_value) == 0)
            elif operator == "is_not_empty":
                return bool(field_value) and (not isinstance(field_value, (list, dict, str)) or len(field_value) > 0)
            else:
                logger.warning(f"Unknown operator: {operator}, defaulting to True")
                return True
        except Exception as e:
            logger.warning(f"Error evaluating condition: {e}, defaulting to True")
            return True

    def _evaluate_structured_conditions(self, conditions: List[Dict[str, Any]], inputs: Dict[str, Any]) -> bool:
        """Evaluate structured conditions safely"""
        if not conditions:
            return True

        result = True
        current_logical_op = None

        for condition in conditions:
            field_name = condition.get('field', '')
            operator = condition.get('operator', '==')
            compare_value = condition.get('value')
            logical_op = condition.get('logical_op')

            # Get field value from inputs
            field_value = inputs.get(field_name)

            # Evaluate this condition
            condition_result = self._safe_evaluate_operator(field_value, operator, compare_value)

            # Combine with previous result using logical operator
            if current_logical_op == 'AND':
                result = result and condition_result
            elif current_logical_op == 'OR':
                result = result or condition_result
            else:
                # First condition
                result = condition_result

            # Set logical operator for next iteration
            current_logical_op = logical_op

        return result

    def _evaluate_condition(self, condition_config: Dict[str, Any], inputs: Dict[str, Any]) -> bool:
        """Evaluate condition using structured format only"""
        if not condition_config:
            return True

        # Only support structured format
        if isinstance(condition_config, dict):
            conditions = condition_config.get('structured_conditions', [])
            return self._evaluate_structured_conditions(conditions, inputs)

        return True


class RouterTemplate(BaseLogicTemplate):
    """Template for Router logic nodes with multiple branches"""

    def initialize(self, context: Any):
        """Return self to provide call/acall interface"""
        return self

    def call(self, **inputs) -> Dict[str, Any]:
        """Synchronous execution - evaluate branches in order and route to first match"""
        router_config = self.node_data.get('router_config', {})
        branches = router_config.get('branches', [])

        matched_branch = None
        default_branch = None

        # Evaluate each branch in order
        for branch in branches:
            if branch.get('is_default', False):
                default_branch = branch.get('branch_id', 'default')
                continue

            condition_config = branch.get('condition_config', {})
            if self._evaluate_condition(condition_config, inputs):
                matched_branch = branch.get('branch_id')
                break

        # Use matched branch or fall back to default
        selected_branch = matched_branch or default_branch or 'default'

        return {
            'branch': selected_branch,
            'matched_branch': matched_branch,
            **inputs
        }

    async def acall(self, **inputs) -> Dict[str, Any]:
        """Async execution - logic is sync anyway"""
        return self.call(**inputs)

    def generate_code(self, context: CodeGenerationContext) -> Dict[str, Any]:
        """Generate code for Router logic node - returns empty as router is handled specially in compiler"""
        instance_var = f"router_{context.get_node_count('router')}"

        context.node_to_var_mapping[self.node_id] = instance_var

        # Router nodes are handled specially in compiler_service.py
        # They generate if-elif-else blocks wrapping branch node code
        return {
            'signature': '',
            'instance': '',
            'forward': '',
            'dependencies': [],
            'instance_var': instance_var
        }

    def _generate_condition_expression(self, conditions: List[Dict[str, Any]]) -> str:
        """Generate Python boolean expression from structured conditions"""
        if not conditions:
            return "True"

        expr_parts = []
        for i, condition in enumerate(conditions):
            field = condition.get('field', '')
            operator = condition.get('operator', '==')
            value = condition.get('value')
            logical_op = condition.get('logical_op')

            # Generate comparison expression
            if operator == "==":
                comp_expr = f"{field} == {repr(value)}"
            elif operator == "!=":
                comp_expr = f"{field} != {repr(value)}"
            elif operator == ">":
                comp_expr = f"{field} > {value}"
            elif operator == "<":
                comp_expr = f"{field} < {value}"
            elif operator == ">=":
                comp_expr = f"{field} >= {value}"
            elif operator == "<=":
                comp_expr = f"{field} <= {value}"
            elif operator == "contains":
                comp_expr = f"{repr(value)} in str({field})"
            elif operator == "not_contains":
                comp_expr = f"{repr(value)} not in str({field})"
            elif operator == "in":
                comp_expr = f"{field} in {repr(value)}"
            elif operator == "not_in":
                comp_expr = f"{field} not in {repr(value)}"
            elif operator == "startswith":
                comp_expr = f"str({field}).startswith({repr(value)})"
            elif operator == "endswith":
                comp_expr = f"str({field}).endswith({repr(value)})"
            elif operator == "is_empty":
                comp_expr = f"not {field}"
            elif operator == "is_not_empty":
                comp_expr = f"bool({field})"
            else:
                comp_expr = "True"

            # Add to expression with logical operator
            if i == 0:
                expr_parts.append(comp_expr)
            else:
                prev_logical_op = conditions[i-1].get('logical_op', 'AND')
                if prev_logical_op == 'OR':
                    expr_parts.append(f" or {comp_expr}")
                else:  # AND
                    expr_parts.append(f" and {comp_expr}")

        return ''.join(expr_parts)


class MergeTemplate(BaseLogicTemplate):
    """Template for Merge logic nodes"""

    def initialize(self, context: Any):
        """Return self to provide call/acall interface"""
        return self

    def call(self, **inputs) -> Dict[str, Any]:
        """Synchronous execution - merge all inputs"""
        return inputs

    async def acall(self, **inputs) -> Dict[str, Any]:
        """Async execution - logic is sync anyway"""
        return self.call(**inputs)
    
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

    def initialize(self, context: Any):
        """Return self to provide call/acall interface"""
        return self

    def call(self, **inputs) -> Dict[str, Any]:
        """Synchronous execution"""
        selected_fields = self.node_data.get('selected_fields', [])
        field_mappings = self.node_data.get('field_mappings', {})

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

    async def acall(self, **inputs) -> Dict[str, Any]:
        """Async execution - logic is sync anyway"""
        return self.call(**inputs)
    
    def generate_code(self, context: CodeGenerationContext) -> Dict[str, Any]:
        """Generate code for FieldSelector logic node"""
        selected_fields = self.node_data.get('selected_fields', [])
        field_mappings = self.node_data.get('field_mappings', {})
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
            'forward': '\n'.join(forward_lines) + "\n",
            'dependencies': [],
            'instance_var': instance_var
        }