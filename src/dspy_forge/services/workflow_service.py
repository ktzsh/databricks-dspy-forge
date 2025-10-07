import uuid
import time
import random
import string
import json
from typing import List, Optional
from datetime import datetime

from dspy_forge.models.workflow import Workflow
from dspy_forge.storage.factory import get_storage_backend
from dspy_forge.services.validation_service import validation_service, WorkflowValidationError
from dspy_forge.core.logging import get_logger


def generate_node_id() -> str:
    """Generate consistent node ID matching frontend format: node-{timestamp}-{random}"""
    timestamp = int(time.time() * 1000)  # milliseconds like Date.now()
    random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=5))
    return f"node-{timestamp}-{random_suffix}"


def generate_edge_id() -> str:
    """Generate consistent edge ID matching frontend format: edge-{timestamp}-{random}"""
    timestamp = int(time.time() * 1000)  # milliseconds like Date.now()
    random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=5))
    return f"edge-{timestamp}-{random_suffix}"


class WorkflowService:
    def __init__(self):
        self.logger = get_logger(__name__)
        self.logger.info("Workflow service initialized")

    async def _enrich_workflow_with_optimization_data(self, workflow: Workflow) -> Workflow:
        """
        Enrich a workflow with optimization data from program.json if available.

        Args:
            workflow: The workflow to enrich

        Returns:
            Workflow with optimization data merged into node data, or original workflow if no optimization data exists
        """
        try:
            storage = await get_storage_backend()

            # Check if program.json exists for this workflow
            program_json_path = f"workflows/{workflow.id}/program.json"
            program_content = await storage.get_file(program_json_path)

            if not program_content:
                return workflow

            # Parse program.json
            program_data = json.loads(program_content)
            self.logger.debug(f"Found program.json for workflow {workflow.id}")

            # Merge optimization data into workflow nodes
            workflow_dict = workflow.model_dump()

            for node in workflow_dict.get('nodes', []):
                node_id = node.get('id')
                # Look for component data matching this node ID
                component_key = f"components['{node_id}']"

                if component_key in program_data:
                    component_data = program_data[component_key]

                    # Add optimization data to node
                    node['data']['optimization_data'] = {
                        'demos': component_data.get('demos', []),
                        'signature': component_data.get('signature', {}),
                        'has_optimization': True
                    }

                    self.logger.debug(f"Merged optimization data for node {node_id}")

            # Create new Workflow object with enriched data
            return Workflow(**workflow_dict)

        except json.JSONDecodeError as e:
            self.logger.warning(f"Failed to parse program.json for workflow {workflow.id}: {e}")
            return workflow
        except Exception as e:
            self.logger.warning(f"Failed to merge optimization data for workflow {workflow.id}: {e}")
            return workflow

    async def create_workflow(self, workflow_data: dict) -> Workflow:
        """Create a new workflow"""
        try:
            # Generate ID if not provided
            if 'id' not in workflow_data or not workflow_data['id']:
                workflow_data['id'] = str(uuid.uuid4())
            
            self.logger.debug(f"Creating workflow with ID: {workflow_data['id']}")
            
            # Set timestamps
            workflow_data['created_at'] = datetime.now()
            workflow_data['updated_at'] = datetime.now()
            
            # Create workflow object
            workflow = Workflow(**workflow_data)
            
            # Validate workflow
            self.logger.debug(f"Validating workflow: {workflow.id}")
            errors = validation_service.validate_workflow(workflow)
            if errors:
                self.logger.warning(f"Workflow validation failed for {workflow.id}: {errors}")
                raise WorkflowValidationError(f"Workflow validation failed: {'; '.join(errors)}")
            
            # Save using storage backend
            storage = await get_storage_backend()
            success = await storage.save_workflow(workflow)
            
            if not success:
                raise RuntimeError("Failed to save workflow to storage")
            
            self.logger.info(f"Successfully created workflow: {workflow.id}")
            return workflow
        except Exception as e:
            self.logger.error(f"Failed to create workflow: {str(e)}", exc_info=True)
            raise

    async def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Get a workflow by ID, enriched with optimization data if available"""
        try:
            storage = await get_storage_backend()
            workflow = await storage.get_workflow(workflow_id)

            if not workflow:
                return None

            # Enrich with optimization data if available
            return await self._enrich_workflow_with_optimization_data(workflow)

        except Exception as e:
            self.logger.error(f"Failed to get workflow {workflow_id}: {e}")
            return None

    async def list_workflows(self) -> List[Workflow]:
        """List all workflows, enriched with optimization data if available"""
        try:
            storage = await get_storage_backend()
            workflows = await storage.list_workflows()

            # Enrich each workflow with optimization data if available
            enriched_workflows = []
            for workflow in workflows:
                enriched_workflow = await self._enrich_workflow_with_optimization_data(workflow)
                enriched_workflows.append(enriched_workflow)

            return enriched_workflows
        except Exception as e:
            self.logger.error(f"Failed to list workflows: {e}")
            return []

    async def update_workflow(self, workflow_id: str, workflow_data: dict) -> Optional[Workflow]:
        """Update an existing workflow"""
        try:
            storage = await get_storage_backend()
            
            # Check if workflow exists
            existing_workflow = await storage.get_workflow(workflow_id)
            if not existing_workflow:
                return None
            
            # Preserve ID and created_at
            workflow_data['id'] = workflow_id
            workflow_data['updated_at'] = datetime.now()
            workflow_data['created_at'] = existing_workflow.created_at

            for node in workflow_data.get("nodes", []):
                if node["data"].get("optimization_data", None):
                    node["data"].pop("optimization_data")
            
            # Create updated workflow object
            workflow = Workflow(**workflow_data)
            
            # Validate workflow
            errors = validation_service.validate_workflow(workflow)
            if errors:
                raise WorkflowValidationError(f"Workflow validation failed: {'; '.join(errors)}")
            
            # Save using storage backend
            success = await storage.save_workflow(workflow)
            
            if not success:
                raise RuntimeError("Failed to save updated workflow to storage")
            
            self.logger.info(f"Successfully updated workflow: {workflow.id}")
            return workflow
        except Exception as e:
            self.logger.error(f"Failed to update workflow {workflow_id}: {e}")
            raise

    async def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow"""
        try:
            storage = await get_storage_backend()
            success = await storage.delete_workflow(workflow_id)
            
            if success:
                self.logger.info(f"Successfully deleted workflow: {workflow_id}")
            
            return success
        except Exception as e:
            self.logger.error(f"Failed to delete workflow {workflow_id}: {e}")
            return False

    async def duplicate_workflow(self, workflow_id: str, new_name: Optional[str] = None) -> Optional[Workflow]:
        """Duplicate an existing workflow"""
        try:
            original_workflow = await self.get_workflow(workflow_id)
            if not original_workflow:
                return None
            
            # Create new workflow data
            new_workflow_data = original_workflow.model_dump()
            new_workflow_data['id'] = str(uuid.uuid4())
            new_workflow_data['name'] = new_name or f"{original_workflow.name} (Copy)"
            
            # Update node IDs to avoid conflicts
            node_id_mapping = {}
            for node in new_workflow_data['nodes']:
                old_id = node['id']
                # Preserve default-start-node ID or generate new consistent ID
                if old_id == 'default-start-node':
                    new_id = 'default-start-node'
                else:
                    new_id = generate_node_id()
                node['id'] = new_id
                node_id_mapping[old_id] = new_id
            
            # Update edge references with consistent IDs
            for edge in new_workflow_data['edges']:
                edge['id'] = generate_edge_id()
                edge['source'] = node_id_mapping.get(edge['source'], edge['source'])
                edge['target'] = node_id_mapping.get(edge['target'], edge['target'])
            
            return await self.create_workflow(new_workflow_data)
        except Exception as e:
            self.logger.error(f"Failed to duplicate workflow {workflow_id}: {e}")
            return None
            
    async def get_storage_health(self) -> dict:
        """Get storage backend health status"""
        try:
            storage = await get_storage_backend()
            return await storage.health_check()
        except Exception as e:
            self.logger.error(f"Failed to get storage health: {e}")
            return {
                "status": "unhealthy",
                "message": f"Storage health check failed: {str(e)}"
            }


# Global service instance
workflow_service = WorkflowService()