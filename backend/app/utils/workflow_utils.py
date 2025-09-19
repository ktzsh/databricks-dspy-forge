from typing import Dict, List
import networkx as nx

from app.models.workflow import Workflow, NodeType
from app.core.dspy_types import (
    SignatureFieldDefinition, 
    ModuleDefinition, 
    LogicDefinition,
    DSPyFieldType,
    DSPyModuleType,
    DSPyLogicType
)
from app.services.validation_service import validation_service, WorkflowValidationError


def validate_workflow(workflow: Workflow) -> List[str]:
    """Validate workflow structure and return list of errors - delegates to validation service"""
    return validation_service.validate_workflow(workflow)


def build_workflow_graph(workflow: Workflow) -> nx.DiGraph:
    """Build NetworkX graph from workflow"""
    graph = nx.DiGraph()
    
    # Add nodes
    for node in workflow.nodes:
        graph.add_node(node.id, data=node.data, type=node.type)
    
    # Add edges
    for edge in workflow.edges:
        graph.add_edge(edge.source, edge.target)
    
    return graph


def get_execution_order(workflow: Workflow) -> List[str]:
    """Get topological order for workflow execution"""
    graph = build_workflow_graph(workflow)
    
    try:
        return list(nx.topological_sort(graph))
    except nx.NetworkXError as e:
        raise WorkflowValidationError(f"Cannot determine execution order: {e}")


def get_node_dependencies(workflow: Workflow, node_id: str) -> List[str]:
    """Get list of node IDs that this node depends on"""
    graph = build_workflow_graph(workflow)
    return list(graph.predecessors(node_id))


def get_node_dependents(workflow: Workflow, node_id: str) -> List[str]:
    """Get list of node IDs that depend on this node"""
    graph = build_workflow_graph(workflow)
    return list(graph.successors(node_id))


def extract_signature_fields(workflow: Workflow) -> Dict[str, SignatureFieldDefinition]:
    """Extract all signature field definitions from workflow"""
    signatures = {}
    
    for node in workflow.nodes:
        if node.type == NodeType.SIGNATURE_FIELD:
            fields = []
            for field_data in node.data.get('fields', []):
                field = SignatureFieldDefinition(
                    name=field_data.get('name', ''),
                    type=DSPyFieldType(field_data.get('type', 'str')),
                    description=field_data.get('description', ''),
                    required=field_data.get('required', True)
                )
                fields.append(field)
            
            signatures[node.id] = fields
    
    return signatures


def extract_modules(workflow: Workflow) -> Dict[str, ModuleDefinition]:
    """Extract all module definitions from workflow"""
    modules = {}
    
    for node in workflow.nodes:
        if node.type == NodeType.MODULE:
            # Find input and output signature nodes
            input_node = None
            output_node = None
            
            for edge in workflow.edges:
                if edge.target == node.id:
                    # This is an input to the module
                    input_node = edge.source
                elif edge.source == node.id:
                    # This is an output from the module
                    output_node = edge.target
            
            if input_node and output_node:
                module = ModuleDefinition(
                    module_type=DSPyModuleType(node.data.get('module_type')),
                    signature_input=input_node,
                    signature_output=output_node,
                    model=node.data.get('model', ''),
                    parameters=node.data.get('parameters', {})
                )
                modules[node.id] = module
    
    return modules


def extract_logic_components(workflow: Workflow) -> Dict[str, LogicDefinition]:
    """Extract all logic component definitions from workflow"""
    logic_components = {}
    
    for node in workflow.nodes:
        if node.type == NodeType.LOGIC:
            logic = LogicDefinition(
                logic_type=DSPyLogicType(node.data.get('logic_type')),
                condition=node.data.get('condition', ''),
                parameters=node.data.get('parameters', {})
            )
            logic_components[node.id] = logic
    
    return logic_components


def find_start_nodes(workflow: Workflow) -> List[str]:
    """Find all start nodes in the workflow"""
    start_nodes = []
    
    for node in workflow.nodes:
        if (node.type == NodeType.SIGNATURE_FIELD and 
            (node.data.get('is_start', False) or node.data.get('isStart', False))):
            start_nodes.append(node.id)
    
    return start_nodes


def find_end_nodes(workflow: Workflow) -> List[str]:
    """Find all end nodes in the workflow"""
    end_nodes = []
    
    for node in workflow.nodes:
        if (node.type == NodeType.SIGNATURE_FIELD and 
            (node.data.get('is_end', False) or node.data.get('isEnd', False))):
            end_nodes.append(node.id)
    
    return end_nodes


def get_workflow_inputs(workflow: Workflow) -> Dict[str, List[SignatureFieldDefinition]]:
    """Get all input signatures for the workflow"""
    inputs = {}
    start_nodes = find_start_nodes(workflow)
    
    for node_id in start_nodes:
        node = next((n for n in workflow.nodes if n.id == node_id), None)
        if node and node.type == NodeType.SIGNATURE_FIELD:
            fields = []
            for field_data in node.data.get('fields', []):
                field = SignatureFieldDefinition(
                    name=field_data.get('name', ''),
                    type=DSPyFieldType(field_data.get('type', 'str')),
                    description=field_data.get('description', ''),
                    required=field_data.get('required', True)
                )
                fields.append(field)
            inputs[node_id] = fields
    
    return inputs


def get_workflow_outputs(workflow: Workflow) -> Dict[str, List[SignatureFieldDefinition]]:
    """Get all output signatures for the workflow"""
    outputs = {}
    end_nodes = find_end_nodes(workflow)
    
    for node_id in end_nodes:
        node = next((n for n in workflow.nodes if n.id == node_id), None)
        if node and node.type == NodeType.SIGNATURE_FIELD:
            fields = []
            for field_data in node.data.get('fields', []):
                field = SignatureFieldDefinition(
                    name=field_data.get('name', ''),
                    type=DSPyFieldType(field_data.get('type', 'str')),
                    description=field_data.get('description', ''),
                    required=field_data.get('required', True)
                )
                fields.append(field)
            outputs[node_id] = fields
    
    return outputs