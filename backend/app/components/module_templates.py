"""
DSPy module component templates.

Handles Predict, ChainOfThought, and other DSPy module types.
"""
import dspy

from typing import Dict, Any, List
from app.core.templates import NodeTemplate, CodeGenerationContext
from app.core.dspy_types import DSPyModuleType
from app.core.logging import get_logger

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
        if instruction:
            class_attrs['__doc__'] = instruction
        
        # Add input fields
        for field_name in input_fields:
            field_type, field_desc = self._get_field_info(field_name, is_input=True)
            if field_desc:
                class_attrs[field_name] = dspy.InputField(desc=field_desc)
            else:
                class_attrs[field_name] = dspy.InputField()
        
        # Add module-specific fields to class_attrs
        self._add_module_specific_fields_to_dict(class_attrs)
        
        # Add output fields
        for field_name in output_fields:
            field_type, field_desc = self._get_field_info(field_name, is_input=False)
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
            field_type, field_desc = self._get_field_info(field_name, is_input=True)
            python_type = self._convert_ui_type_to_python(field_type)
            if field_desc:
                lines.append(f"    {field_name}: {python_type} = dspy.InputField(desc='{field_desc}')")
            else:
                lines.append(f"    {field_name}: {python_type} = dspy.InputField()")
        
        # Add module-specific signature fields
        self._add_signature_specific_fields(lines)
        
        # Add output fields
        for field_name in output_fields:
            field_type, field_desc = self._get_field_info(field_name, is_input=False)
            python_type = self._convert_ui_type_to_python(field_type)
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
        instance_code = self._generate_instance_code(instance_var, signature_name)
        
        # Generate forward method code
        input_args = ", ".join([f"{field}={field}" for field in input_fields])
        result_var = f"result_{context.get_result_count()}"
        
        forward_lines = []
        if model_name and model_name != 'default':
            forward_lines.append(f"        with dspy.context(lm=dspy.LM('databricks/{model_name}')):")
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
    
    async def execute(self, inputs: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """Execute Predict module node"""
        instruction = self.node_data.get('instruction', '')
        model_name = self.node_data.get('model', '')
        
        # Create dynamic signature
        signature_class = self._create_dynamic_signature(instruction)
        
        # Create and execute predictor
        predictor = dspy.Predict(signature_class)
        
        # Execute with model context if specified
        if model_name and model_name != 'default':
            try:
                with dspy.context(lm=dspy.LM(f'databricks/{model_name}')):
                    result = predictor(**inputs)
            except Exception as e:
                logger.warning(f"Failed to use model {model_name}, falling back to default: {e}")
                result = predictor(**inputs)
        else:
            result = predictor(**inputs)
        
        # Extract actual output fields from DSPy result
        output_fields = {}
        
        # Approach 1: Direct attribute access - get field names from workflow IR
        output_field_names = self._get_connected_fields(is_input=False)
        logger.debug(f"Output fields from workflow IR: {output_field_names}")
        
        for field_name in output_field_names:
            if hasattr(result, field_name):
                field_value = getattr(result, field_name)
                logger.debug(f"Found field {field_name}: {repr(field_value)} (type: {type(field_value)})")
                if field_value is not None and field_value != "":
                    output_fields[field_name] = field_value
            else:
                logger.debug(f"Field {field_name} NOT found in result object")
        
        logger.debug(f"Final output_fields: {output_fields}")
        return output_fields
    
    def _generate_instance_code(self, instance_var: str, signature_name: str) -> str:
        """Generate Predict instance creation code"""
        return f"        self.{instance_var} = dspy.Predict({signature_name})"


class ChainOfThoughtTemplate(BaseModuleTemplate):
    """Template for ChainOfThought module nodes"""
    
    async def execute(self, inputs: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """Execute ChainOfThought module node"""
        instruction = self.node_data.get('instruction', '')
        model_name = self.node_data.get('model', '')
        
        # Create dynamic signature
        signature_class = self._create_dynamic_signature(instruction)
        
        # Create and execute chain of thought
        cot = dspy.ChainOfThought(signature_class)
        
        # Execute with model context if specified
        if model_name and model_name != 'default':
            try:
                with dspy.context(lm=dspy.LM(f'databricks/{model_name}')):
                    result = cot(**inputs)
            except Exception as e:
                logger.warning(f"Failed to use model {model_name}, falling back to default: {e}")
                result = cot(**inputs)
        else:
            result = cot(**inputs)
        
        # Extract actual output fields from DSPy result
        output_fields = {}
        
        # Approach 1: Direct attribute access - get field names from workflow IR
        output_field_names = self._get_connected_fields(is_input=False)
        logger.debug(f"CoT output fields from workflow IR: {output_field_names}")

        # Add rationale for chain of thought
        all_field_names = ['rationale'] + output_field_names
        
        logger.debug(f"Expected CoT output fields: {all_field_names}")
        logger.debug(f"CoT result has attributes: {[attr for attr in dir(result) if hasattr(result, attr) and not attr.startswith('_')]}")
        
        for field_name in all_field_names:
            if hasattr(result, field_name):
                field_value = getattr(result, field_name)
                logger.debug(f"Found CoT field {field_name}: {repr(field_value)} (type: {type(field_value)})")
                if field_value is not None and field_value != "":
                    output_fields[field_name] = field_value
            else:
                logger.debug(f"CoT field {field_name} NOT found in result object")
        
        logger.debug(f"Final CoT output_fields: {output_fields}")
        return output_fields
    
    def _add_module_specific_fields(self, signature_class):
        """Add rationale field for chain of thought"""
        setattr(signature_class, 'rationale', dspy.OutputField(desc="Step-by-step reasoning"))
    
    def _add_module_specific_fields_to_dict(self, class_attrs: dict):
        """Add rationale field to class attributes dict"""
        class_attrs['rationale'] = dspy.OutputField(desc="Step-by-step reasoning")
    
    def _add_signature_specific_fields(self, lines: List[str]):
        """Add rationale field to signature code"""
        lines.append("    rationale = dspy.OutputField(desc='Step-by-step reasoning')")
    
    def _generate_instance_code(self, instance_var: str, signature_name: str) -> str:
        """Generate ChainOfThought instance creation code"""
        return f"        self.{instance_var} = dspy.ChainOfThought({signature_name})"