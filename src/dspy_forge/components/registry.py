"""
Component template registry.

Automatically registers all component templates with the TemplateFactory.
"""

from dspy_forge.core.templates import TemplateFactory
from dspy_forge.models.workflow import NodeType, ModuleType, RetrieverType, LogicType

# Import all component templates
from .signature_field import SignatureFieldTemplate
from .module_templates import PredictTemplate, ChainOfThoughtTemplate
from .retriever_templates import UnstructuredRetrieveTemplate, StructuredRetrieveTemplate
from .logic_templates import RouterTemplate, MergeTemplate, FieldSelectorTemplate


def register_all_templates():
    """Register all component templates with the TemplateFactory"""
    
    # Register signature field template
    TemplateFactory.register_template(NodeType.SIGNATURE_FIELD, SignatureFieldTemplate)
    
    # Register module templates - we'll need a dispatcher for different module types
    TemplateFactory.register_template(NodeType.MODULE, ModuleTemplateDispatcher)
    
    # Register retriever templates - we'll need a dispatcher for different retriever types
    TemplateFactory.register_template(NodeType.RETRIEVER, RetrieverTemplateDispatcher)
    
    # Register logic templates - we'll need a dispatcher for different logic types
    TemplateFactory.register_template(NodeType.LOGIC, LogicTemplateDispatcher)


class ModuleTemplateDispatcher:
    """Dispatcher for different module template types"""

    def __init__(self, node, workflow):
        module_type = node.data.get('module_type')

        if module_type == ModuleType.PREDICT.value:
            self._template = PredictTemplate(node, workflow)
        elif module_type == ModuleType.CHAIN_OF_THOUGHT.value:
            self._template = ChainOfThoughtTemplate(node, workflow)
        else:
            # Default to PredictTemplate for unknown types
            self._template = PredictTemplate(node, workflow)

    def initialize(self, context):
        """Initialize returns DSPy component with built-in call/acall"""
        return self._template.initialize(context)

    def generate_code(self, context):
        return self._template.generate_code(context)

class RetrieverTemplateDispatcher:
    """Dispatcher for different retriever template types"""

    def __init__(self, node, workflow):
        retriever_type = node.data.get('retriever_type')

        if retriever_type == RetrieverType.UNSTRUCTURED_RETRIEVE.value:
            self._template = UnstructuredRetrieveTemplate(node, workflow)
        elif retriever_type == RetrieverType.STRUCTURED_RETRIEVE.value:
            self._template = StructuredRetrieveTemplate(node, workflow)
        else:
            # Default to UnstructuredRetrieveTemplate for unknown types
            self._template = UnstructuredRetrieveTemplate(node, workflow)

    def initialize(self, context):
        """Initialize returns wrapper component with call/acall"""
        return self._template.initialize(context)

    def generate_code(self, context):
        return self._template.generate_code(context)


class LogicTemplateDispatcher:
    """Dispatcher for different logic template types"""

    def __init__(self, node, workflow):
        logic_type = node.data.get('logic_type')

        if logic_type == LogicType.ROUTER.value:
            self._template = RouterTemplate(node, workflow)
        elif logic_type == LogicType.MERGE.value:
            self._template = MergeTemplate(node, workflow)
        elif logic_type == LogicType.FIELD_SELECTOR.value:
            self._template = FieldSelectorTemplate(node, workflow)
        else:
            # Default to MergeTemplate for unknown types
            self._template = MergeTemplate(node, workflow)

    def initialize(self, context):
        """Initialize returns self (template) with call/acall"""
        return self._template.initialize(context)

    def generate_code(self, context):
        return self._template.generate_code(context)


# Auto-register all templates when this module is imported
register_all_templates()