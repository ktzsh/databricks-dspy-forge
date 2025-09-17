from typing import Dict, List, Any, Tuple, Optional
import networkx as nx
from collections import defaultdict, deque

from app.models.workflow import Workflow, SignatureFieldNode, ModuleNode, LogicNode, NodeType
from app.core.dspy_types import (
    SignatureFieldDefinition, 
    ModuleDefinition, 
    LogicDefinition,
    DSPyFieldType,
    DSPyModuleType,
    DSPyLogicType
)


class WorkflowValidationError(Exception):
    """Raised when workflow validation fails"""
    pass


def validate_workflow(workflow: Workflow) -> List[str]:
    """Validate workflow structure and return list of errors"""
    errors = []
    
    # Check for at least one start node
    start_nodes = [
        node for node in workflow.nodes 
        if node.type == NodeType.SIGNATURE_FIELD and node.data.get('is_start', False)
    ]
    
    if not start_nodes:
        errors.append("Workflow must have at least one start node")
    
    # Check for at least one end node
    end_nodes = [
        node for node in workflow.nodes 
        if node.type == NodeType.SIGNATURE_FIELD and node.data.get('is_end', False)
    ]
    
    if not end_nodes:
        errors.append("Workflow must have at least one end node")
    
    # Build graph for connectivity check
    graph = build_workflow_graph(workflow)
    
    # Check if workflow is connected
    if not nx.is_weakly_connected(graph):
        errors.append("Workflow must be connected (no isolated nodes)")
    
    # Check for cycles (DSPy workflows should be DAGs)
    if not nx.is_directed_acyclic_graph(graph):
        errors.append("Workflow cannot contain cycles")
    
    # Validate individual nodes
    for node in workflow.nodes:
        node_errors = validate_node(node, workflow)
        errors.extend([f"Node {node.id}: {error}" for error in node_errors])
    
    return errors


def validate_node(node: Any, workflow: Workflow) -> List[str]:
    """Validate individual node"""
    errors = []
    
    if node.type == NodeType.SIGNATURE_FIELD:
        # Validate signature field
        fields = node.data.get('fields', [])
        if not fields:
            errors.append("Signature field must have at least one field")
        
        for field in fields:
            if not field.get('name'):
                errors.append("Field must have a name")
            if not field.get('type'):
                errors.append("Field must have a type")
    
    elif node.type == NodeType.MODULE:
        # Validate module
        module_type = node.data.get('module_type')
        if not module_type:
            errors.append("Module must specify a module type")
        
        model = node.data.get('model')
        if not model and module_type != DSPyModuleType.RETRIEVE:
            errors.append("Module must specify a model")
    
    elif node.type == NodeType.LOGIC:
        # Validate logic component
        logic_type = node.data.get('logic_type')
        if not logic_type:
            errors.append("Logic component must specify a logic type")
        
        if logic_type == DSPyLogicType.IF_ELSE:
            condition = node.data.get('condition')
            if not condition:
                errors.append("If-Else logic must specify a condition")
    
    return errors


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
            node.data.get('is_start', False)):
            start_nodes.append(node.id)
    
    return start_nodes


def find_end_nodes(workflow: Workflow) -> List[str]:
    """Find all end nodes in the workflow"""
    end_nodes = []
    
    for node in workflow.nodes:
        if (node.type == NodeType.SIGNATURE_FIELD and 
            node.data.get('is_end', False)):
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