import os
import json
import uuid
from typing import List, Optional
from datetime import datetime

from app.models.workflow import Workflow
from app.core.config import settings
from app.utils.workflow_utils import validate_workflow, WorkflowValidationError
from app.core.logging import get_logger


class WorkflowService:
    def __init__(self):
        self.storage_path = settings.workflows_storage_path
        self.logger = get_logger(__name__)
        os.makedirs(self.storage_path, exist_ok=True)
        self.logger.info(f"Workflow storage initialized at: {self.storage_path}")

    def _get_workflow_file_path(self, workflow_id: str) -> str:
        """Get the file path for a workflow"""
        return os.path.join(self.storage_path, f"{workflow_id}.json")

    def create_workflow(self, workflow_data: dict) -> Workflow:
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
            errors = validate_workflow(workflow)
            if errors:
                self.logger.warning(f"Workflow validation failed for {workflow.id}: {errors}")
                raise WorkflowValidationError(f"Workflow validation failed: {'; '.join(errors)}")
            
            # Save to file
            file_path = self._get_workflow_file_path(workflow.id)
            self.logger.debug(f"Saving workflow to: {file_path}")
            with open(file_path, 'w') as f:
                json.dump(workflow.model_dump(), f, indent=2, default=str)
            
            self.logger.info(f"Successfully created workflow: {workflow.id}")
            return workflow
        except Exception as e:
            self.logger.error(f"Failed to create workflow: {str(e)}", exc_info=True)
            raise

    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Get a workflow by ID"""
        file_path = self._get_workflow_file_path(workflow_id)
        
        if not os.path.exists(file_path):
            return None
        
        try:
            with open(file_path, 'r') as f:
                workflow_data = json.load(f)
                return Workflow(**workflow_data)
        except Exception:
            return None

    def list_workflows(self) -> List[Workflow]:
        """List all workflows"""
        workflows = []
        
        if not os.path.exists(self.storage_path):
            return workflows
        
        for filename in os.listdir(self.storage_path):
            if filename.endswith('.json'):
                file_path = os.path.join(self.storage_path, filename)
                try:
                    with open(file_path, 'r') as f:
                        workflow_data = json.load(f)
                        workflows.append(Workflow(**workflow_data))
                except Exception:
                    continue
        
        # Sort by updated_at in descending order
        return sorted(workflows, key=lambda w: w.updated_at, reverse=True)

    def update_workflow(self, workflow_id: str, workflow_data: dict) -> Optional[Workflow]:
        """Update an existing workflow"""
        file_path = self._get_workflow_file_path(workflow_id)
        
        if not os.path.exists(file_path):
            return None
        
        # Preserve ID and created_at
        workflow_data['id'] = workflow_id
        workflow_data['updated_at'] = datetime.now()
        
        # Get existing workflow to preserve created_at
        existing_workflow = self.get_workflow(workflow_id)
        if existing_workflow:
            workflow_data['created_at'] = existing_workflow.created_at
        
        # Create updated workflow object
        workflow = Workflow(**workflow_data)
        
        # Validate workflow
        errors = validate_workflow(workflow)
        if errors:
            raise WorkflowValidationError(f"Workflow validation failed: {'; '.join(errors)}")
        
        # Save to file
        with open(file_path, 'w') as f:
            json.dump(workflow.model_dump(), f, indent=2, default=str)
        
        return workflow

    def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow"""
        file_path = self._get_workflow_file_path(workflow_id)
        
        if not os.path.exists(file_path):
            return False
        
        try:
            os.remove(file_path)
            return True
        except Exception:
            return False

    def duplicate_workflow(self, workflow_id: str, new_name: Optional[str] = None) -> Optional[Workflow]:
        """Duplicate an existing workflow"""
        original_workflow = self.get_workflow(workflow_id)
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
        
        return self.create_workflow(new_workflow_data)


# Global service instance
workflow_service = WorkflowService()