"""
Component templates for workflow nodes.

This package contains individual component implementations that support
both execution and code generation for different node types.
"""

from .signature_field import SignatureFieldTemplate
from .module_templates import PredictTemplate, ChainOfThoughtTemplate
from .retriever_templates import UnstructuredRetrieveTemplate, StructuredRetrieveTemplate
from .logic_templates import IfElseTemplate, MergeTemplate, FieldSelectorTemplate
from . import registry  # This will auto-register all templates

__all__ = [
    'SignatureFieldTemplate',
    'PredictTemplate', 
    'ChainOfThoughtTemplate',
    'UnstructuredRetrieveTemplate',
    'StructuredRetrieveTemplate', 
    'IfElseTemplate',
    'MergeTemplate',
    'FieldSelectorTemplate'
]