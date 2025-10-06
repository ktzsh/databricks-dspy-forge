
import dspy

from typing import Dict, Any, List, Optional
from datetime import datetime

from dspy_forge.core.logging import get_logger
from dspy_forge.utils.workflow_utils import (
    get_execution_order,
    find_start_nodes,
    find_end_nodes,
    get_node_dependencies,
)
from dspy_forge.core.templates import TemplateFactory
from dspy_forge.models.workflow import Workflow, WorkflowExecution
from dspy_forge.components import registry  # This will auto-register all templates

logger = get_logger(__name__)

class CompoundProgram(dspy.Module):
    """Dynamic compound program that encapsulates the entire workflow"""

    def __init__(self, workflow: Workflow, context: Any):
        super().__init__()
        self.workflow = workflow
        self.context = context
        self.components = {}
        self.execution_order = get_execution_order(workflow)

        # Initialize all components
        self._initialize_components()

    def _initialize_components(self):
        """Initialize all workflow components as DSPy modules"""
        for node_id in self.execution_order:
            node = next((n for n in self.workflow.nodes if n.id == node_id), None)
            if not node:
                continue

            # Create template for this node
            template = TemplateFactory.create_template(node, self.workflow)

            # Initialize component if it has an initialize method
            if hasattr(template, 'initialize'):
                component = template.initialize(self.context)
                if component:
                    self.components[node_id] = component

    def forward(self, **inputs):
        """
        Synchronous execution for DSPy optimizers.
        Uses component.call() methods directly.
        """
        for node_id in self.execution_order:
            start_time = datetime.now()
            node = next((n for n in self.workflow.nodes if n.id == node_id), None)
            if not node:
                continue

            node_inputs = self._get_node_inputs(node_id, inputs)

            try:
                if isinstance(self.components[node_id], dspy.primitives.module.Module):
                    model_name = node.data.get('model')
                    with dspy.context(lm=dspy.LM(f'databricks/{model_name}')):
                        result = self.components[node_id](**node_inputs)
                else:
                    result = self.components[node_id].call(**node_inputs)

                self._process_node_result(node_id, node, node_inputs, start_time, result)
            except Exception as e:
                self._handle_node_error(node_id, node, node_inputs, start_time, e)

        return self._get_final_outputs()

    async def aforward(self, **inputs):
        """
        Asynchronous execution for playground/real-time usage.
        Uses component.acall() methods.
        """
        for node_id in self.execution_order:
            start_time = datetime.now()
            node = next((n for n in self.workflow.nodes if n.id == node_id), None)
            if not node:
                continue

            node_inputs = self._get_node_inputs(node_id, inputs)

            try:
                if isinstance(self.components[node_id], dspy.primitives.module.Module):
                    model_name = node.data.get('model', '')
                    # Use model-specific context for DSPy modules
                    with dspy.context(lm=dspy.LM(f'databricks/{model_name}')):
                        result = await self.components[node_id].acall(**node_inputs)
                else:
                    # Use default LM or no context
                    result = await self.components[node_id].acall(**node_inputs)

                self._process_node_result(node_id, node, node_inputs, start_time, result)
            except Exception as e:
                self._handle_node_error(node_id, node, node_inputs, start_time, e)

        return self._get_final_outputs()

    def _get_node_inputs(self, node_id: str, initial_inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Get inputs for a node from its dependencies"""
        dependencies = get_node_dependencies(self.workflow, node_id)

        # Check if this is a start node
        start_nodes = find_start_nodes(self.workflow)
        if node_id in start_nodes:
            return initial_inputs

        # Get inputs from previous node outputs
        inputs = {}
        incoming_edges = [edge for edge in self.workflow.edges if edge.target == node_id]

        for edge in incoming_edges:
            source_outputs = self.context.get_node_output(edge.source)

            if edge.sourceHandle and edge.targetHandle:
                # Field-level connection
                source_field = edge.sourceHandle.replace('source-', '')
                target_field = edge.targetHandle.replace('target-', '')

                if source_field in source_outputs:
                    inputs[target_field] = source_outputs[source_field]
            else:
                # Whole-node connection
                inputs.update(source_outputs)

        # Fallback to legacy behavior
        if not incoming_edges:
            for dep_node_id in dependencies:
                dep_outputs = self.context.get_node_output(dep_node_id)
                inputs.update(dep_outputs)

        return inputs

    def _process_node_result(self, node_id: str, node: Any, node_inputs: Dict[str, Any],
                             start_time: datetime, result: Any) -> Dict[str, Any]:
        """Process result from node execution (common logic for forward/aforward)"""
        outputs = self._extract_outputs_from_call(result, node)
        self.context.set_node_output(node_id, outputs)
        execution_time = (datetime.now() - start_time).total_seconds()
        self.context.add_trace_entry(node_id, node.type.value, node_inputs, outputs, execution_time)
        return outputs

    def _handle_node_error(self, node_id: str, node: Any, node_inputs: Dict[str, Any],
                          start_time: datetime, error: Exception) -> Dict[str, Any]:
        """Handle error during node execution (common logic for forward/aforward)"""
        logger.error(f"Error executing node {node_id}: {error}", exc_info=True)
        outputs = {'error': str(error)}
        self.context.set_node_output(node_id, outputs)
        execution_time = (datetime.now() - start_time).total_seconds()
        self.context.add_trace_entry(node_id, node.type.value, node_inputs, outputs, execution_time)
        return outputs

    def _get_final_outputs(self) -> dspy.Prediction:
        """Extract final outputs from end nodes (common logic for forward/aforward)"""
        end_nodes = find_end_nodes(self.workflow)
        final_outputs = {}
        for end_node_id in end_nodes:
            final_outputs.update(self.context.get_node_output(end_node_id))
        return dspy.Prediction(**final_outputs)

    def _extract_outputs_from_call(self, result: Any, node: Any) -> Dict[str, Any]:
        """
        Extract output fields from component call/acall result.
        Handles both DSPy Prediction objects and plain dicts.
        """
        # If result is a dict, return as-is (from logic/signature field components)
        if isinstance(result, dict):
            return result

        # If result is a DSPy Prediction, extract all fields
        if isinstance(result, dspy.Prediction):
            outputs = {}

            # Get expected output fields from workflow
            template = TemplateFactory.create_template(node, self.workflow)
            output_field_names = template._template._get_connected_fields(is_input=False)

            # Extract expected fields
            for field_name in output_field_names:
                if hasattr(result, field_name):
                    outputs[field_name] = getattr(result, field_name)

            # Also extract special fields (rationale for CoT, etc.)
            if hasattr(result, 'rationale'):
                outputs['rationale'] = result.rationale

            # For retrievers, extract additional fields
            for attr in ['context', 'passages', 'query', 'sql_query', 'query_description', 'conversation_id']:
                if hasattr(result, attr) and attr not in outputs:
                    outputs[attr] = getattr(result, attr)

            return outputs

        # Fallback: convert to dict
        return {'result': str(result)}