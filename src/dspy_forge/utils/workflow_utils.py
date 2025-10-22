from typing import Dict, List
import networkx as nx

from dspy_forge.models.workflow import Workflow, NodeType
from dspy_forge.core.dspy_types import (
    SignatureFieldDefinition, 
    ModuleDefinition, 
    LogicDefinition,
    DSPyFieldType,
    DSPyModuleType,
    DSPyLogicType
)
from dspy_forge.services.validation_service import validation_service, WorkflowValidationError


def validate_workflow(workflow: Workflow) -> List[str]:
    """Validate workflow structure and return list of errors - delegates to validation service"""
    return validation_service.validate_workflow(workflow)


def build_workflow_graph(workflow: Workflow, exclude_tool_edges: bool = False) -> nx.DiGraph:
    """
    Build NetworkX graph from workflow

    Args:
        workflow: The workflow to build graph from
        exclude_tool_edges: If True, exclude edges where targetHandle='tools'
                          (these are tool connections to ReAct, not data flow)

    Returns:
        NetworkX directed graph
    """
    graph = nx.DiGraph()

    # Add nodes
    for node in workflow.nodes:
        graph.add_node(node.id, data=node.data, type=node.type)

    # Add edges
    for edge in workflow.edges:
        # Skip tool connection edges if requested
        if exclude_tool_edges and edge.targetHandle == 'tools':
            continue
        graph.add_edge(edge.source, edge.target)

    return graph


def get_execution_order(workflow: Workflow) -> List[str]:
    """
    Get topological order for workflow execution.

    Tool nodes are excluded from the main execution order as they are
    loaded by ReAct nodes, not executed in the main flow.
    """
    # Build graph excluding tool connection edges
    graph = build_workflow_graph(workflow, exclude_tool_edges=True)

    try:
        # Get topological sort
        topo_order = list(nx.topological_sort(graph))

        # Filter out tool nodes from execution order
        # Tool nodes are not executed in the main flow
        execution_order = [
            node_id for node_id in topo_order
            if not any(n.id == node_id and n.type == NodeType.TOOL for n in workflow.nodes)
        ]

        return execution_order, graph
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


def identify_router_nodes(workflow: Workflow) -> List[str]:
    """Identify all router nodes in the workflow"""
    router_nodes = []

    for node in workflow.nodes:
        if node.type == NodeType.LOGIC:
            logic_type = node.data.get('logic_type')
            if logic_type == 'Router':
                router_nodes.append(node.id)

    return router_nodes


def get_nodes_in_branch(workflow: Workflow, router_node_id: str, branch_id: str) -> List[str]:
    """
    Get all nodes reachable from a specific branch of a router node.

    Args:
        workflow: The workflow
        router_node_id: ID of the router node
        branch_id: ID of the branch to trace

    Returns:
        List of node IDs in this branch path (excluding the router itself)
    """
    # Find edges from router with this branch_id as sourceHandle
    branch_edges = [
        edge for edge in workflow.edges
        if edge.source == router_node_id and edge.sourceHandle == branch_id
    ]

    if not branch_edges:
        return []

    # Build a set of all nodes directly connected to router branches (for merge detection)
    router_node = next((n for n in workflow.nodes if n.id == router_node_id), None)
    if router_node:
        router_config = router_node.data.get('router_config') or router_node.data.get('routerConfig', {})
        all_branch_ids = {b.get('branchId') or b.get('branch_id') for b in router_config.get('branches', [])}
    else:
        all_branch_ids = set()

    # Collect all nodes reachable from this branch using BFS
    visited = set()
    queue = [edge.target for edge in branch_edges]
    branch_nodes = []

    while queue:
        node_id = queue.pop(0)

        if node_id in visited:
            continue

        # Check if this node is a merge point before adding it
        # A merge point receives edges from multiple branches
        incoming_to_node = [e for e in workflow.edges if e.target == node_id]
        source_branch_ids = set()

        for inc_edge in incoming_to_node:
            # Check if edge comes directly from router with a branch handle
            if inc_edge.source == router_node_id and inc_edge.sourceHandle in all_branch_ids:
                source_branch_ids.add(inc_edge.sourceHandle)

        # If node receives from multiple branches directly, it's a merge point - stop here
        if len(source_branch_ids) > 1:
            continue

        visited.add(node_id)
        branch_nodes.append(node_id)

        # Find outgoing edges from this node
        outgoing_edges = [edge for edge in workflow.edges if edge.source == node_id]

        for edge in outgoing_edges:
            target = edge.target

            if target not in visited and target not in queue:
                # Before adding to queue, check if it's a potential merge point
                incoming_to_target = [e for e in workflow.edges if e.target == target]
                target_source_branches = set()

                for inc_edge in incoming_to_target:
                    if inc_edge.source == router_node_id and inc_edge.sourceHandle in all_branch_ids:
                        target_source_branches.add(inc_edge.sourceHandle)

                # If target receives from multiple branches, don't add it
                if len(target_source_branches) <= 1:
                    queue.append(target)

    return branch_nodes


def get_branch_paths(workflow: Workflow, router_node_id: str) -> Dict[str, List[str]]:
    """
    Get all branch paths from a router node.

    Args:
        workflow: The workflow
        router_node_id: ID of the router node

    Returns:
        Dict mapping branch_id to list of node IDs in that branch
    """
    router_node = next((n for n in workflow.nodes if n.id == router_node_id), None)

    if not router_node:
        return {}

    # Get router configuration (support both snake_case and camelCase)
    router_config = router_node.data.get('router_config') or router_node.data.get('routerConfig', {})
    branches = router_config.get('branches', [])

    branch_paths = {}

    for branch in branches:
        branch_id = branch.get('branchId') or branch.get('branch_id')
        if branch_id:
            branch_paths[branch_id] = get_nodes_in_branch(workflow, router_node_id, branch_id)

    return branch_paths


def find_branch_merge_point(workflow: Workflow, router_node_id: str) -> str:
    """
    Find the merge point where branches from a router converge.

    Args:
        workflow: The workflow
        router_node_id: ID of the router node

    Returns:
        Node ID of the merge point, or None if branches don't merge
    """
    branch_paths = get_branch_paths(workflow, router_node_id)

    if len(branch_paths) < 2:
        return None

    # Get all branch node sets
    branch_node_sets = [set(nodes) for nodes in branch_paths.values()]

    # Find nodes that appear in multiple branch paths
    # Or find nodes that have incoming edges from multiple branches
    router_node = next((n for n in workflow.nodes if n.id == router_node_id), None)
    if not router_node:
        return None

    router_config = router_node.data.get('router_config') or router_node.data.get('routerConfig', {})
    all_branch_ids = [b.get('branchId') or b.get('branch_id') for b in router_config.get('branches', [])]

    # Check all nodes to find merge point
    all_nodes_in_branches = set()
    for nodes in branch_paths.values():
        all_nodes_in_branches.update(nodes)

    # Find first node (in topological order) that has incoming edges from multiple branches
    graph = build_workflow_graph(workflow)
    try:
        topo_order = list(nx.topological_sort(graph))
    except nx.NetworkXError:
        return None

    for node_id in topo_order:
        if node_id == router_node_id:
            continue

        # Check if this node receives edges from multiple branches
        incoming_edges = [e for e in workflow.edges if e.target == node_id]
        source_branches = set()

        for edge in incoming_edges:
            # Direct edge from router
            if edge.source == router_node_id and edge.sourceHandle in all_branch_ids:
                source_branches.add(edge.sourceHandle)
            # Edge from node in a branch
            else:
                for branch_id, branch_nodes in branch_paths.items():
                    if edge.source in branch_nodes:
                        source_branches.add(branch_id)
                        break

        if len(source_branches) > 1:
            return node_id

    return None