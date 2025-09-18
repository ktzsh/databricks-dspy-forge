import os
import json
import aiofiles
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from app.storage.base import WorkflowStorageBackend
from app.models.workflow import Workflow
from app.core.logging import get_logger


class LocalDirectoryStorage(WorkflowStorageBackend):
    """Local directory storage backend for workflows"""
    
    def __init__(self, storage_path: str):
        """
        Initialize local directory storage
        
        Args:
            storage_path: Path to the directory where workflows will be stored
        """
        self.storage_path = Path(storage_path)
        self.logger = get_logger(__name__)
        
    async def initialize(self) -> bool:
        """Initialize the storage directory"""
        try:
            self.storage_path.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Initialized local directory storage at: {self.storage_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize local directory storage: {e}")
            return False
    
    def _get_workflow_file_path(self, workflow_id: str) -> Path:
        """Get the file path for a workflow"""
        return self.storage_path / f"{workflow_id}.json"
    
    async def save_workflow(self, workflow: Workflow) -> bool:
        """Save a workflow to local directory"""
        try:
            file_path = self._get_workflow_file_path(workflow.id)
            workflow_data = workflow.model_dump()
            
            # Convert datetime objects to strings for JSON serialization
            workflow_json = json.dumps(workflow_data, indent=2, default=str)
            
            async with aiofiles.open(file_path, 'w') as f:
                await f.write(workflow_json)
            
            self.logger.debug(f"Saved workflow {workflow.id} to {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save workflow {workflow.id}: {e}")
            return False
    
    async def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Get a workflow from local directory"""
        try:
            file_path = self._get_workflow_file_path(workflow_id)
            
            if not file_path.exists():
                return None
            
            async with aiofiles.open(file_path, 'r') as f:
                content = await f.read()
                workflow_data = json.loads(content)
                return Workflow(**workflow_data)
        except Exception as e:
            self.logger.error(f"Failed to get workflow {workflow_id}: {e}")
            return None
    
    async def list_workflows(self) -> List[Workflow]:
        """List all workflows from local directory"""
        workflows = []
        
        try:
            if not self.storage_path.exists():
                return workflows
            
            for file_path in self.storage_path.glob("*.json"):
                try:
                    async with aiofiles.open(file_path, 'r') as f:
                        content = await f.read()
                        workflow_data = json.loads(content)
                        workflow = Workflow(**workflow_data)
                        workflows.append(workflow)
                except Exception as e:
                    self.logger.warning(f"Failed to load workflow from {file_path}: {e}")
                    continue
            
            # Sort by updated_at in descending order
            workflows.sort(key=lambda w: w.updated_at, reverse=True)
            
        except Exception as e:
            self.logger.error(f"Failed to list workflows: {e}")
        
        return workflows
    
    async def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow from local directory"""
        try:
            file_path = self._get_workflow_file_path(workflow_id)
            
            if not file_path.exists():
                return False
            
            file_path.unlink()
            self.logger.debug(f"Deleted workflow {workflow_id} from {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete workflow {workflow_id}: {e}")
            return False
    
    async def workflow_exists(self, workflow_id: str) -> bool:
        """Check if a workflow exists in local directory"""
        file_path = self._get_workflow_file_path(workflow_id)
        return file_path.exists()
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on local directory storage"""
        try:
            # Check if directory exists and is writable
            if not self.storage_path.exists():
                return {
                    "status": "unhealthy",
                    "message": "Storage directory does not exist",
                    "path": str(self.storage_path)
                }
            
            if not os.access(self.storage_path, os.W_OK):
                return {
                    "status": "unhealthy", 
                    "message": "Storage directory is not writable",
                    "path": str(self.storage_path)
                }
            
            # Count workflows
            workflow_count = len(list(self.storage_path.glob("*.json")))
            
            return {
                "status": "healthy",
                "message": "Local directory storage is operational",
                "path": str(self.storage_path),
                "workflow_count": workflow_count,
                "free_space_gb": round(os.statvfs(self.storage_path).f_bavail * 
                                     os.statvfs(self.storage_path).f_frsize / (1024**3), 2)
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"Health check failed: {str(e)}",
                "path": str(self.storage_path)
            }