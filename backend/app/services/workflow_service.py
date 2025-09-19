import uuid
from typing import List, Optional
from datetime import datetime

from app.models.workflow import Workflow
from app.storage.factory import get_storage_backend
from app.services.validation_service import validation_service, WorkflowValidationError
from app.core.logging import get_logger


class WorkflowService:
    def __init__(self):
        self.logger = get_logger(__name__)
        self.logger.info("Workflow service initialized")

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
        """Get a workflow by ID"""
        try:
            storage = await get_storage_backend()
            return await storage.get_workflow(workflow_id)
        except Exception as e:
            self.logger.error(f"Failed to get workflow {workflow_id}: {e}")
            return None

    async def list_workflows(self) -> List[Workflow]:
        """List all workflows"""
        try:
            storage = await get_storage_backend()
            return await storage.list_workflows()
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
                new_id = f"node-{uuid.uuid4()}"
                node['id'] = new_id
                node_id_mapping[old_id] = new_id
            
            # Update edge references
            for edge in new_workflow_data['edges']:
                edge['id'] = f"edge-{uuid.uuid4()}"
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