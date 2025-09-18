import json
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.files import FileInfo

from app.storage.base import WorkflowStorageBackend
from app.models.workflow import Workflow
from app.core.logging import get_logger


class DatabricksVolumeStorage(WorkflowStorageBackend):
    """Databricks Unity Catalog Volume storage backend for workflows"""
    
    def __init__(self, volume_path: str, host: Optional[str] = None, token: Optional[str] = None):
        """
        Initialize Databricks volume storage
        
        Args:
            volume_path: Path to the Unity Catalog volume (e.g., '/Volumes/catalog/schema/volume/workflows')
            host: Databricks workspace host (if not provided, will use env vars)
            token: Databricks access token (if not provided, will use env vars)
        """
        self.volume_path = volume_path.rstrip('/')
        self.logger = get_logger(__name__)
        
        # Initialize Databricks workspace client
        client_kwargs = {}
        if host:
            client_kwargs['host'] = host
        if token:
            client_kwargs['token'] = token
            
        try:
            self.client = WorkspaceClient(**client_kwargs)
        except Exception as e:
            self.logger.error(f"Failed to initialize Databricks client: {e}")
            raise
    
    async def initialize(self) -> bool:
        """Initialize the volume storage (ensure volume path exists)"""
        try:
            # Run in thread pool since databricks SDK is synchronous
            loop = asyncio.get_event_loop()
            
            def _check_and_create_volume_path():
                try:
                    # Try to list the volume directory to check if it exists
                    self.client.files.list_directory_contents(self.volume_path)
                    self.logger.info(f"Volume path exists: {self.volume_path}")
                    return True
                except Exception as e:
                    # If directory doesn't exist, we can't create it via API
                    # Unity Catalog volumes must be created through SQL or UI
                    self.logger.error(f"Volume path does not exist or is not accessible: {self.volume_path}")
                    self.logger.error(f"Please ensure the Unity Catalog volume exists: {e}")
                    return False
            
            result = await loop.run_in_executor(None, _check_and_create_volume_path)
            
            if result:
                self.logger.info(f"Initialized Databricks volume storage at: {self.volume_path}")
            
            return result
        except Exception as e:
            self.logger.error(f"Failed to initialize Databricks volume storage: {e}")
            return False
    
    def _get_workflow_file_path(self, workflow_id: str) -> str:
        """Get the file path for a workflow in the volume"""
        return f"{self.volume_path}/{workflow_id}.json"
    
    async def save_workflow(self, workflow: Workflow) -> bool:
        """Save a workflow to Databricks volume"""
        try:
            file_path = self._get_workflow_file_path(workflow.id)
            workflow_data = workflow.model_dump()
            
            # Convert datetime objects to strings for JSON serialization
            workflow_json = json.dumps(workflow_data, indent=2, default=str)
            
            # Run in thread pool since databricks SDK is synchronous
            loop = asyncio.get_event_loop()
            
            def _save_file():
                # Upload file content to volume
                self.client.files.upload(
                    file_path=file_path,
                    contents=workflow_json.encode('utf-8'),
                    overwrite=True
                )
                return True
            
            await loop.run_in_executor(None, _save_file)
            
            self.logger.debug(f"Saved workflow {workflow.id} to volume: {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save workflow {workflow.id} to volume: {e}")
            return False
    
    async def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Get a workflow from Databricks volume"""
        try:
            file_path = self._get_workflow_file_path(workflow_id)
            
            # Run in thread pool since databricks SDK is synchronous
            loop = asyncio.get_event_loop()
            
            def _get_file():
                try:
                    # Download file content from volume
                    response = self.client.files.download(file_path)
                    return response.contents.decode('utf-8')
                except Exception:
                    # File doesn't exist
                    return None
            
            content = await loop.run_in_executor(None, _get_file)
            
            if content is None:
                return None
            
            workflow_data = json.loads(content)
            return Workflow(**workflow_data)
            
        except Exception as e:
            self.logger.error(f"Failed to get workflow {workflow_id} from volume: {e}")
            return None
    
    async def list_workflows(self) -> List[Workflow]:
        """List all workflows from Databricks volume"""
        workflows = []
        
        try:
            # Run in thread pool since databricks SDK is synchronous
            loop = asyncio.get_event_loop()
            
            def _list_files():
                try:
                    # List all files in the volume directory
                    file_infos = list(self.client.files.list_directory_contents(self.volume_path))
                    return [f for f in file_infos if f.name.endswith('.json')]
                except Exception as e:
                    self.logger.error(f"Failed to list volume directory: {e}")
                    return []
            
            json_files = await loop.run_in_executor(None, _list_files)
            
            # Load each workflow file
            for file_info in json_files:
                try:
                    workflow_id = file_info.name[:-5]  # Remove .json extension
                    workflow = await self.get_workflow(workflow_id)
                    if workflow:
                        workflows.append(workflow)
                except Exception as e:
                    self.logger.warning(f"Failed to load workflow from {file_info.path}: {e}")
                    continue
            
            # Sort by updated_at in descending order
            workflows.sort(key=lambda w: w.updated_at, reverse=True)
            
        except Exception as e:
            self.logger.error(f"Failed to list workflows from volume: {e}")
        
        return workflows
    
    async def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow from Databricks volume"""
        try:
            file_path = self._get_workflow_file_path(workflow_id)
            
            # Run in thread pool since databricks SDK is synchronous
            loop = asyncio.get_event_loop()
            
            def _delete_file():
                try:
                    self.client.files.delete(file_path)
                    return True
                except Exception:
                    # File doesn't exist
                    return False
            
            result = await loop.run_in_executor(None, _delete_file)
            
            if result:
                self.logger.debug(f"Deleted workflow {workflow_id} from volume: {file_path}")
            
            return result
        except Exception as e:
            self.logger.error(f"Failed to delete workflow {workflow_id} from volume: {e}")
            return False
    
    async def workflow_exists(self, workflow_id: str) -> bool:
        """Check if a workflow exists in Databricks volume"""
        try:
            file_path = self._get_workflow_file_path(workflow_id)
            
            # Run in thread pool since databricks SDK is synchronous
            loop = asyncio.get_event_loop()
            
            def _check_file():
                try:
                    self.client.files.get_metadata(file_path)
                    return True
                except Exception:
                    return False
            
            return await loop.run_in_executor(None, _check_file)
        except Exception:
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on Databricks volume storage"""
        try:
            # Run in thread pool since databricks SDK is synchronous
            loop = asyncio.get_event_loop()
            
            def _health_check():
                try:
                    # Check if we can access the volume
                    file_infos = list(self.client.files.list_directory_contents(self.volume_path))
                    
                    # Count JSON workflow files
                    workflow_count = len([f for f in file_infos if f.name.endswith('.json')])
                    
                    return {
                        "status": "healthy",
                        "message": "Databricks volume storage is operational",
                        "volume_path": self.volume_path,
                        "workflow_count": workflow_count,
                        "total_files": len(file_infos)
                    }
                except Exception as e:
                    return {
                        "status": "unhealthy",
                        "message": f"Cannot access Databricks volume: {str(e)}",
                        "volume_path": self.volume_path
                    }
            
            return await loop.run_in_executor(None, _health_check)
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"Health check failed: {str(e)}",
                "volume_path": self.volume_path
            }