from typing import Dict, List, Any, Tuple, Optional
import networkx as nx

from dspy_forge.models.workflow import Workflow, NodeType
from dspy_forge.core.dspy_types import DSPyModuleType, DSPyLogicType
from dspy_forge.core.logging import get_logger

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

            if logic_type_enum == DSPyLogicType.ROUTER:
                # Support both snake_case and camelCase for router config
                router_config = node.data.get('router_config') or node.data.get('routerConfig', {})
                branches = router_config.get('branches', []) if router_config else []
                if not branches:
                    errors.append("Router must have at least one branch configured")
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


class OptimizationValidationError(Exception):
    """Raised when optimization validation fails"""
    pass


class OptimizationValidationService:
    """Service for validating optimization configurations"""

    # Define mandatory fields for each optimizer
    OPTIMIZER_REQUIREMENTS = {
        'GEPA': ['auto', 'reflection_lm'],
        'BootstrapFewShotWithRandomSearch': ['max_rounds', 'max_bootstrapped_demos', 'max_labeled_demos', 'num_candidate_programs'],
        'MIPROv2': ['auto', 'task_model', 'prompt_model']
    }

    def validate_optimization_request(
        self,
        optimizer_name: str,
        optimizer_config: Dict[str, str],
        scoring_functions: List[Dict[str, Any]],
        training_data: Dict[str, str],
        validation_data: Dict[str, str]
    ) -> Dict[str, str]:
        """
        Validate optimization request and return field-level errors

        Args:
            optimizer_name: Name of the optimizer
            optimizer_config: Optimizer configuration parameters
            scoring_functions: List of scoring functions
            training_data: Training dataset location
            validation_data: Validation dataset location

        Returns:
            Dictionary mapping field names to error messages
        """
        field_errors = {}

        # Validate optimizer configuration
        field_errors.update(self._validate_optimizer_config(optimizer_name, optimizer_config))

        # Validate scoring functions
        field_errors.update(self._validate_scoring_functions(scoring_functions))

        # Validate dataset locations
        field_errors.update(self._validate_dataset_location(training_data, 'train'))
        field_errors.update(self._validate_dataset_location(validation_data, 'val'))

        return field_errors

    def _validate_optimizer_config(
        self,
        optimizer_name: str,
        optimizer_config: Dict[str, str]
    ) -> Dict[str, str]:
        """Validate optimizer-specific configuration"""
        errors = {}

        # Check mandatory fields for the selected optimizer
        mandatory_fields = self.OPTIMIZER_REQUIREMENTS.get(optimizer_name, [])

        for field in mandatory_fields:
            if field not in optimizer_config:
                errors[f'optimizer_config.{field}'] = f'{field} is required for {optimizer_name}'
            elif not optimizer_config[field]:
                errors[f'optimizer_config.{field}'] = f'{field} cannot be empty'

        # Validate numeric fields if present
        numeric_fields = ['num_rounds', 'num_candidates', 'max_bootstrapped_demos', 'num_candidate_programs']
        for field in numeric_fields:
            if field in optimizer_config:
                try:
                    value = int(optimizer_config[field])
                    if value <= 0:
                        errors[f'optimizer_config.{field}'] = f'{field} must be a positive integer'
                except ValueError:
                    errors[f'optimizer_config.{field}'] = f'{field} must be a valid integer'

        # Validate temperature fields if present
        if 'init_temperature' in optimizer_config:
            try:
                value = float(optimizer_config['init_temperature'])
                if value <= 0 or value > 1:
                    errors['optimizer_config.init_temperature'] = 'init_temperature must be between 0 and 1'
            except ValueError:
                errors['optimizer_config.init_temperature'] = 'init_temperature must be a valid number'

        # Validate GEPA-specific fields
        if 'auto' in optimizer_config:
            valid_auto_values = ['light', 'medium', 'heavy']
            if optimizer_config['auto'] not in valid_auto_values:
                errors['optimizer_config.auto'] = f'auto must be one of: {", ".join(valid_auto_values)}'

        return errors

    def _validate_scoring_functions(
        self,
        scoring_functions: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """Validate scoring functions"""
        errors = {}

        if not scoring_functions:
            errors['scoring_functions'] = 'At least one scoring function is required'
            return errors

        total_weightage = 0

        for i, sf in enumerate(scoring_functions):
            # Validate required fields
            if not sf.get('name'):
                errors[f'scoring_function_{i}_name'] = 'Scoring function name is required'

            if not sf.get('type'):
                errors[f'scoring_function_{i}_type'] = 'Scoring function type is required'
            elif sf['type'] not in ['Correctness', 'Guidelines']:
                errors[f'scoring_function_{i}_type'] = 'Type must be either Correctness or Guidelines'

            # Validate guideline for Guidelines type
            if sf.get('type') == 'Guidelines' and not sf.get('guideline'):
                errors[f'scoring_function_{i}_guideline'] = 'Guideline text is required for Guidelines type'

            # Validate weightage
            try:
                weightage = int(sf.get('weightage', 0))
                if weightage < 0 or weightage > 100:
                    errors[f'scoring_function_{i}_weightage'] = 'Weightage must be between 0 and 100'
                else:
                    total_weightage += weightage
            except (TypeError, ValueError):
                errors[f'scoring_function_{i}_weightage'] = 'Weightage must be a valid integer'

        # Validate total weightage equals 100
        if total_weightage != 100:
            errors['weightage'] = f'Total weightage must equal 100 (current: {total_weightage})'

        return errors

    def _validate_dataset_location(
        self,
        dataset: Dict[str, str],
        prefix: str
    ) -> Dict[str, str]:
        """Validate dataset location (catalog, schema, table)"""
        errors = {}

        if not dataset.get('catalog'):
            errors[f'{prefix}_catalog'] = f'{prefix.capitalize()} catalog is required'

        if not dataset.get('schema'):
            errors[f'{prefix}_schema'] = f'{prefix.capitalize()} schema is required'

        if not dataset.get('table'):
            errors[f'{prefix}_table'] = f'{prefix.capitalize()} table is required'

        return errors

    def get_optimizer_requirements(self, optimizer_name: str) -> List[str]:
        """Get required configuration fields for an optimizer"""
        return self.OPTIMIZER_REQUIREMENTS.get(optimizer_name, [])


# Global validation service instances
validation_service = WorkflowValidationService()
optimization_validation_service = OptimizationValidationService()