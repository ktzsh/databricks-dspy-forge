
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
        Runs the async aforward() in a synchronous context.
        """
        import asyncio

        # Try to get existing event loop, create new one if needed
        try:
            asyncio.get_running_loop()
            # If we're already in an async context, we can't use run_until_complete
            # This should not happen in optimization context, but handle it gracefully
            raise RuntimeError("forward() called from async context - use aforward() instead")
        except RuntimeError:
            # No running loop - create one and run aforward()
            return asyncio.run(self.aforward(**inputs))

    async def aforward(self, **inputs):
        """
        Asynchronous execution for playground/real-time usage.
        This is the main execution implementation.
        """
        # Execute nodes in order
        for node_id in self.execution_order:
            start_time = datetime.now()
            node = next((n for n in self.workflow.nodes if n.id == node_id), None)
            if not node:
                continue

            # Get inputs for this node
            node_inputs = self._get_node_inputs(node_id, inputs)

            try:
                # Execute the node using its component or template
                if node_id in self.components:
                    # Use DSPy component
                    result = self.components[node_id](**node_inputs)
                    outputs = self._extract_outputs(result, node)
                else:
                    # Use template execute method (for logic nodes, etc.)
                    template = TemplateFactory.create_template(node, self.workflow)
                    # Always await since all execute methods are async
                    outputs = await template.execute(node_inputs, self.context)

                # Store outputs in context
                self.context.set_node_output(node_id, outputs)

            except Exception as e:
                logger.error(f"Error executing node {node_id}: {e}", exc_info=True)
                outputs = {'error': str(e)}
                self.context.set_node_output(node_id, outputs)

            # Add trace entry
            execution_time = (datetime.now() - start_time).total_seconds()
            self.context.add_trace_entry(node_id, node.type.value, node_inputs, outputs, execution_time)

        # Get final outputs from end nodes
        end_nodes = find_end_nodes(self.workflow)
        final_outputs = {}
        for end_node_id in end_nodes:
            final_outputs.update(self.context.get_node_output(end_node_id))

        return dspy.Prediction(**final_outputs)

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

    def _extract_outputs(self, result: Any, node: Any) -> Dict[str, Any]:
        """Extract output fields from DSPy result"""
        outputs = {}

        # Get expected output fields from workflow
        template = TemplateFactory.create_template(node, self.workflow)
        output_field_names = template._get_connected_fields(is_input=False)

        # Extract fields from result
        if isinstance(result, dspy.Prediction):
            for field_name in output_field_names:
                if hasattr(result, field_name):
                    outputs[field_name] = getattr(result, field_name)

            # Also check for rationale (CoT)
            if hasattr(result, 'rationale'):
                outputs['rationale'] = result.rationale
        elif isinstance(result, dict):
            outputs = result

        return outputs