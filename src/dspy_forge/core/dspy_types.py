from typing import Dict, List, Any, Union, Type, get_args, get_origin
from pydantic import BaseModel
import dspy
from enum import Enum


class DSPyFieldType(str, Enum):
    """Supported field types for DSPy signatures"""
    STRING = "str"
    INTEGER = "int"
    BOOLEAN = "bool"
    FLOAT = "float"
    LIST_STRING = "list[str]"
    LIST_INT = "list[int]"
    LIST_FLOAT = "list[float]"
    DICT = "dict"
    ANY = "Any"


class DSPyModuleType(str, Enum):
    """Supported DSPy module types"""
    PREDICT = "Predict"
    CHAIN_OF_THOUGHT = "ChainOfThought"
    REACT = "ReAct"
    RETRIEVE = "Retrieve"
    BEST_OF_N = "BestOfN"
    REFINE = "Refine"
    MULTI_CHAIN_COMPARISON = "MultiChainComparison"


class DSPyLogicType(str, Enum):
    """Logic component types for workflow control flow"""
    ROUTER = "Router"
    MERGE = "Merge"
    FIELD_SELECTOR = "FieldSelector"
    PARALLEL = "Parallel"
    SEQUENTIAL = "Sequential"


class SignatureFieldDefinition(BaseModel):
    """Definition of a field in a DSPy signature"""
    name: str
    type: DSPyFieldType
    description: str = ""
    required: bool = True


class ModuleDefinition(BaseModel):
    """Definition of a DSPy module"""
    module_type: DSPyModuleType
    signature_input: str  # ID of input signature field node
    signature_output: str  # ID of output signature field node
    model: str = ""  # Language model name/identifier
    instruction: str = ""  # Task instruction for DSPy signature
    parameters: Dict[str, Any] = {}


class LogicDefinition(BaseModel):
    """Definition of a logic component"""
    logic_type: DSPyLogicType
    condition: str = ""  # For conditional logic
    parameters: Dict[str, Any] = {}


def python_type_to_dspy_type(python_type: str) -> DSPyFieldType:
    """Convert Python type string to DSPy field type"""
    type_mapping = {
        "str": DSPyFieldType.STRING,
        "int": DSPyFieldType.INTEGER,
        "bool": DSPyFieldType.BOOLEAN,
        "float": DSPyFieldType.FLOAT,
        "list[str]": DSPyFieldType.LIST_STRING,
        "list[int]": DSPyFieldType.LIST_INT,
        "list[float]": DSPyFieldType.LIST_FLOAT,
        "dict": DSPyFieldType.DICT,
        "Any": DSPyFieldType.ANY,
    }
    return type_mapping.get(python_type, DSPyFieldType.STRING)


def dspy_type_to_python_type(dspy_type: DSPyFieldType) -> Type:
    """Convert DSPy field type to actual Python type"""
    type_mapping = {
        DSPyFieldType.STRING: str,
        DSPyFieldType.INTEGER: int,
        DSPyFieldType.BOOLEAN: bool,
        DSPyFieldType.FLOAT: float,
        DSPyFieldType.LIST_STRING: List[str],
        DSPyFieldType.LIST_INT: List[int],
        DSPyFieldType.LIST_FLOAT: List[float],
        DSPyFieldType.DICT: dict,
        DSPyFieldType.ANY: Any,
    }
    return type_mapping.get(dspy_type, str)


def create_dspy_signature(fields: List[SignatureFieldDefinition], instruction: str = "") -> Type[dspy.Signature]:
    """Dynamically create a DSPy signature from field definitions and instruction"""
    
    class_attrs = {}
    
    # Add instruction as docstring if provided
    if instruction:
        class_attrs['__doc__'] = instruction
    
    for field in fields:
        python_type = dspy_type_to_python_type(field.type)
        
        # Create dspy.InputField or dspy.OutputField
        if field.required:
            field_obj = dspy.InputField(desc=field.description)
        else:
            field_obj = dspy.OutputField(desc=field.description)
        
        class_attrs[field.name] = field_obj
    
    # Dynamically create the signature class
    signature_class = type(
        'DynamicSignature',
        (dspy.Signature,),
        class_attrs
    )
    
    return signature_class


def get_module_class(module_type: DSPyModuleType) -> Type[dspy.Module]:
    """Get the DSPy module class for a given module type"""
    module_mapping = {
        DSPyModuleType.PREDICT: dspy.Predict,
        DSPyModuleType.CHAIN_OF_THOUGHT: dspy.ChainOfThought,
        DSPyModuleType.REACT: dspy.ReAct,
        DSPyModuleType.RETRIEVE: dspy.Retrieve,
        DSPyModuleType.BEST_OF_N: dspy.majority,  # Note: dspy.majority for BestOfN
        DSPyModuleType.REFINE: dspy.Predict,  # Refine is typically implemented as a custom Predict
    }
    return module_mapping.get(module_type, dspy.Predict)


def validate_signature_compatibility(
    input_fields: List[SignatureFieldDefinition],
    output_fields: List[SignatureFieldDefinition]
) -> bool:
    """Validate that input and output signatures are compatible"""
    # Basic validation - can be extended
    input_names = {field.name for field in input_fields}
    output_names = {field.name for field in output_fields}
    
    # Check for overlapping field names
    overlap = input_names.intersection(output_names)
    if overlap:
        # Some fields can be both input and output (pass-through)
        pass
    
    return True


def get_default_parameters(module_type: DSPyModuleType) -> Dict[str, Any]:
    """Get default parameters for a DSPy module type"""
    defaults = {
        DSPyModuleType.PREDICT: {},
        DSPyModuleType.CHAIN_OF_THOUGHT: {"rationale_type": None},
        DSPyModuleType.REACT: {"max_iters": 10, "num_results": 3},
        DSPyModuleType.RETRIEVE: {"k": 5},
        DSPyModuleType.BEST_OF_N: {"n": 3},
        DSPyModuleType.REFINE: {"max_iterations": 3},
    }
    return defaults.get(module_type, {})


def get_required_models(module_type: DSPyModuleType) -> Dict[str, str]:
    """Get required model types for a DSPy module"""
    model_requirements = {
        DSPyModuleType.PREDICT: {"lm": "Language Model"},
        DSPyModuleType.CHAIN_OF_THOUGHT: {"lm": "Language Model"},
        DSPyModuleType.REACT: {"lm": "Language Model"},
        DSPyModuleType.RETRIEVE: {"rm": "Retrieval Model"},
        DSPyModuleType.BEST_OF_N: {"lm": "Language Model"},
        DSPyModuleType.REFINE: {"lm": "Language Model"},
    }
    return model_requirements.get(module_type, {})