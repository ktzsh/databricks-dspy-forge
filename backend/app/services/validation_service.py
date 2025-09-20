from typing import Dict, List, Any, Tuple, Optional
import networkx as nx

from app.models.workflow import Workflow, NodeType
from app.core.dspy_types import DSPyModuleType, DSPyLogicType
from app.core.logging import get_logger

logger = get_logger(__name__)


class WorkflowValidationError(Exception):
    """Raised when workflow validation fails"""
    pass


class WorkflowValidationService:
    """Service for validating workflow structure and integrity"""
    
    def __init__(self):
        self.validation_cache: Dict[str, Tuple[bool, List[str]]] = {}
    
    def validate_workflow(self, workflow: Workflow) -> List[str]:
        """
        Validate workflow structure and return list of errors
        
        Args:
            workflow: The workflow to validate
            
        Returns:
            List of validation error messages
        """
        # Check cache first
        cache_key = self._get_cache_key(workflow)
        if cache_key in self.validation_cache:
            is_valid, errors = self.validation_cache[cache_key]
            return errors
        
        errors = []
        
        try:
            # Structural validation
            errors.extend(self._validate_structure(workflow))
            
            # Connectivity validation  
            errors.extend(self._validate_connectivity(workflow))
            
            # Node-specific validation
            errors.extend(self._validate_nodes(workflow))
            
            # Execution flow validation
            errors.extend(self._validate_execution_flow(workflow))
            
            # Cache the result
            is_valid = len(errors) == 0
            self.validation_cache[cache_key] = (is_valid, errors)
            
            return errors
            
        except Exception as e:
            logger.error(f"Validation failed for workflow {workflow.id}: {e}")
            return [f"Validation error: {str(e)}"]
    
    def validate_for_execution(self, workflow: Workflow) -> List[str]:
        """
        Additional validation specifically for execution readiness
        
        Args:
            workflow: The workflow to validate for execution
            
        Returns:
            List of execution-specific validation errors
        """
        errors = []
        
        # First run standard validation
        errors.extend(self.validate_workflow(workflow))
        
        # Execution-specific checks
        errors.extend(self._validate_execution_readiness(workflow))
        
        return errors
    
    def is_workflow_valid(self, workflow: Workflow) -> bool:
        """Check if workflow is valid (no validation errors)"""
        errors = self.validate_workflow(workflow)
        return len(errors) == 0
    
    def clear_cache(self, workflow_id: str = None):
        """Clear validation cache for specific workflow or all workflows"""
        if workflow_id:
            # Remove specific workflow from cache
            keys_to_remove = [k for k in self.validation_cache.keys() if workflow_id in k]
            for key in keys_to_remove:
                del self.validation_cache[key]
        else:
            # Clear entire cache
            self.validation_cache.clear()
    
    def _get_cache_key(self, workflow: Workflow) -> str:
        """Generate cache key for workflow validation"""
        # Create a simple hash based on workflow structure
        node_data = [(n.id, n.type.value, str(n.data)) for n in workflow.nodes]
        edge_data = [(e.source, e.target) for e in workflow.edges]
        return f"{workflow.id}_{hash(str(node_data + edge_data))}"
    
    def _validate_structure(self, workflow: Workflow) -> List[str]:
        """Validate basic workflow structure"""
        errors = []
        
        # Check for at least one start node
        start_nodes = [
            node for node in workflow.nodes 
            if node.type == NodeType.SIGNATURE_FIELD and (node.data.get('is_start', False) or node.data.get('isStart', False))
        ]
        
        if not start_nodes:
            errors.append("Workflow must have at least one start node")
        
        # Check for at least one end node
        end_nodes = [
            node for node in workflow.nodes 
            if node.type == NodeType.SIGNATURE_FIELD and (node.data.get('is_end', False) or node.data.get('isEnd', False))
        ]
        
        if not end_nodes:
            errors.append("Workflow must have at least one end node")
        
        # Check for duplicate node IDs
        node_ids = [node.id for node in workflow.nodes]
        if len(node_ids) != len(set(node_ids)):
            errors.append("Workflow contains duplicate node IDs")
        
        # Check for duplicate edge IDs
        edge_ids = [edge.id for edge in workflow.edges]
        if len(edge_ids) != len(set(edge_ids)):
            errors.append("Workflow contains duplicate edge IDs")
        
        return errors
    
    def _validate_connectivity(self, workflow: Workflow) -> List[str]:
        """Validate workflow connectivity and graph properties"""
        errors = []
        
        try:
            # Build graph for connectivity check
            graph = self._build_workflow_graph(workflow)
            
            # Check if workflow is connected
            if not nx.is_weakly_connected(graph):
                errors.append("Workflow must be connected (no isolated nodes)")
            
            # Check for cycles (DSPy workflows should be DAGs)
            if not nx.is_directed_acyclic_graph(graph):
                errors.append("Workflow cannot contain cycles")
            
            # Check for orphaned nodes
            for node in workflow.nodes:
                if node.type != NodeType.SIGNATURE_FIELD:
                    continue
                    
                # Start nodes shouldn't have incoming edges (except from other start nodes)
                if node.data.get('is_start', False) or node.data.get('isStart', False):
                    incoming = [e for e in workflow.edges if e.target == node.id]
                    if incoming:
                        non_start_incoming = []
                        for edge in incoming:
                            source_node = next((n for n in workflow.nodes if n.id == edge.source), None)
                            if source_node and not (source_node.data.get('is_start', False) or source_node.data.get('isStart', False)):
                                non_start_incoming.append(edge)
                        if non_start_incoming:
                            errors.append(f"Start node {node.id} has incoming edges from non-start nodes")
                
                # End nodes shouldn't have outgoing edges (except to other end nodes)
                if node.data.get('is_end', False) or node.data.get('isEnd', False):
                    outgoing = [e for e in workflow.edges if e.source == node.id]
                    if outgoing:
                        non_end_outgoing = []
                        for edge in outgoing:
                            target_node = next((n for n in workflow.nodes if n.id == edge.target), None)
                            if target_node and not (target_node.data.get('is_end', False) or target_node.data.get('isEnd', False)):
                                non_end_outgoing.append(edge)
                        if non_end_outgoing:
                            errors.append(f"End node {node.id} has outgoing edges to non-end nodes")
            
        except Exception as e:
            errors.append(f"Graph validation failed: {str(e)}")
        
        return errors
    
    def _validate_nodes(self, workflow: Workflow) -> List[str]:
        """Validate individual nodes"""
        errors = []
        
        for node in workflow.nodes:
            node_errors = self._validate_node(node, workflow)
            errors.extend([f"Node {node.id}: {error}" for error in node_errors])
        
        return errors
    
    def _validate_node(self, node: Any, workflow: Workflow) -> List[str]:
        """Validate individual node"""
        errors = []
        
        if node.type == NodeType.SIGNATURE_FIELD:
            errors.extend(self._validate_signature_field_node(node))
        elif node.type == NodeType.MODULE:
            errors.extend(self._validate_module_node(node))
        elif node.type == NodeType.LOGIC:
            errors.extend(self._validate_logic_node(node))
        elif node.type == NodeType.RETRIEVER:
            errors.extend(self._validate_retriever_node(node))
        else:
            errors.append(f"Unknown node type: {node.type}")
        
        return errors
    
    def _validate_signature_field_node(self, node: Any) -> List[str]:
        """Validate signature field node"""
        errors = []
        
        fields = node.data.get('fields', [])
        if not fields:
            errors.append("Signature field must have at least one field")
        
        for field in fields:
            if not field.get('name'):
                errors.append("Field must have a name")
            if not field.get('type'):
                errors.append("Field must have a type")
        
        return errors
    
    def _validate_module_node(self, node: Any) -> List[str]:
        """Validate module node"""
        errors = []
        
        module_type = node.data.get('module_type')
        if not module_type:
            errors.append("Module must specify a module type")
        else:
            try:
                # Validate module_type is a valid enum value
                DSPyModuleType(module_type)
                
                model = node.data.get('model')
                if not model and module_type != DSPyModuleType.RETRIEVE:
                    errors.append("Module must specify a model")
                    
                instruction = node.data.get('instruction')
                if not instruction:
                    errors.append("Module must specify an instruction")
            except ValueError:
                errors.append(f"Invalid module type: {module_type}")
        
        return errors
    
    def _validate_logic_node(self, node: Any) -> List[str]:
        """Validate logic node"""
        errors = []
        
        logic_type = node.data.get('logic_type')
        if not logic_type:
            errors.append("Logic component must specify a logic type")
        
        try:
            logic_type_enum = DSPyLogicType(logic_type)
            
            if logic_type_enum == DSPyLogicType.IF_ELSE:
                condition = node.data.get('condition')
                if not condition:
                    errors.append("If-Else logic must specify a condition")
            elif logic_type_enum == DSPyLogicType.FIELD_SELECTOR:
                selected_fields = node.data.get('selectedFields', [])
                if not selected_fields:
                    # This is a warning rather than an error - FieldSelector can pass through all fields
                    pass
        except ValueError:
            errors.append(f"Invalid logic type: {logic_type}")
        
        return errors
    
    def _validate_retriever_node(self, node: Any) -> List[str]:
        """Validate retriever node"""
        errors = []
        
        retriever_type = node.data.get('retriever_type')
        if not retriever_type:
            errors.append("Retriever must specify a retriever type")
        else:
            if retriever_type == 'UnstructuredRetrieve':
                # Validate required fields for UnstructuredRetrieve
                required_fields = ['catalog_name', 'schema_name', 'index_name', 'content_column', 'id_column']
                for field in required_fields:
                    if not node.data.get(field):
                        errors.append(f"UnstructuredRetrieve requires {field}")
            elif retriever_type == 'StructuredRetrieve':
                # Validate required fields for StructuredRetrieve
                if not node.data.get('genie_space_id'):
                    errors.append("StructuredRetrieve requires genie_space_id")
            else:
                errors.append(f"Unknown retriever type: {retriever_type}")
        
        return errors
    
    def _validate_execution_flow(self, workflow: Workflow) -> List[str]:
        """Validate execution flow and dependencies"""
        errors = []
        
        try:
            # Check if execution order can be determined
            graph = self._build_workflow_graph(workflow)
            
            try:
                execution_order = list(nx.topological_sort(graph))
                
                # Validate that all nodes can be reached from start nodes
                start_nodes = [
                    node.id for node in workflow.nodes 
                    if node.type == NodeType.SIGNATURE_FIELD and (node.data.get('is_start', False) or node.data.get('isStart', False))
                ]
                
                reachable_nodes = set()
                for start_node in start_nodes:
                    descendants = nx.descendants(graph, start_node)
                    reachable_nodes.update(descendants)
                    reachable_nodes.add(start_node)
                
                all_nodes = set(node.id for node in workflow.nodes)
                unreachable_nodes = all_nodes - reachable_nodes
                
                if unreachable_nodes:
                    errors.append(f"Unreachable nodes: {', '.join(unreachable_nodes)}")
                
            except nx.NetworkXError as e:
                errors.append(f"Cannot determine execution order: {e}")
                
        except Exception as e:
            errors.append(f"Execution flow validation failed: {str(e)}")
        
        return errors
    
    def _validate_execution_readiness(self, workflow: Workflow) -> List[str]:
        """Additional validation for execution readiness"""
        errors = []
        
        # Check that all module nodes have proper connections
        for node in workflow.nodes:
            if node.type == NodeType.MODULE:
                # Check for input connections
                incoming_edges = [e for e in workflow.edges if e.target == node.id]
                if not incoming_edges:
                    errors.append(f"Module node {node.id} has no input connections")
                
                # Check for output connections
                outgoing_edges = [e for e in workflow.edges if e.source == node.id]
                if not outgoing_edges:
                    errors.append(f"Module node {node.id} has no output connections")
        
        return errors
    
    def _build_workflow_graph(self, workflow: Workflow) -> nx.DiGraph:
        """Build NetworkX graph from workflow"""
        graph = nx.DiGraph()
        
        # Add nodes
        for node in workflow.nodes:
            graph.add_node(node.id, data=node.data, type=node.type)
        
        # Add edges
        for edge in workflow.edges:
            graph.add_edge(edge.source, edge.target)
        
        return graph


# Global validation service instance
validation_service = WorkflowValidationService()