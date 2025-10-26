import json
import asyncio
import os
import io
from typing import List, Optional, Dict, Any

from databricks.sdk import WorkspaceClient

from dspy_forge.storage.base import StorageBackend
from dspy_forge.models.workflow import Workflow
from dspy_forge.core.logging import get_logger


class DatabricksVolumeStorage(StorageBackend):
    """Databricks Unity Catalog Volume storage backend for workflows"""
    
    def __init__(self, volume_path: str):
        """
        Initialize Databricks volume storage
        
        Args:
            volume_path: Path to the Unity Catalog volume (e.g., '/Volumes/catalog/schema/volume/workflows')
            host: Databricks workspace host (if not provided, will use env vars)
            token: Databricks access token (if not provided, will use env vars)
        """
        self.volume_path = volume_path.rstrip('/')
        self.logger = get_logger(__name__)
            
        try:
            self.client = WorkspaceClient()
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
        return f"{self.volume_path}/workflows/{workflow_id}.json"
    
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
                # Wrap bytes in BytesIO to make it a file-like object
                content_io = io.BytesIO(workflow_json.encode('utf-8'))
                self.client.files.upload(
                    file_path=file_path,
                    content=content_io,
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
                    return response.contents.read()
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
                    # List all files in the workflows directory
                    workflows_path = f"{self.volume_path}/workflows"
                    file_infos = list(self.client.files.list_directory_contents(workflows_path, page_size=1000))
                    return [f for f in file_infos if f.name.endswith('.json')]
                except Exception as e:
                    self.logger.error(f"Failed to list volume workflows directory: {e}")
                    return []
            
            self.logger.info(f"Looking for workflows in volume path: {self.volume_path}/workflows")
            json_files = await loop.run_in_executor(None, _list_files)
            
            # Load each workflow file
            for file_info in json_files:
                try:
                    workflow_id = file_info.name[:-5]  # Remove .json extension
                    self.logger.info(f"Workflow id: {workflow_id}")
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

    # Deployment artifact management
    async def save_deployment_status(self, deployment_id: str, status: Dict[str, Any]) -> bool:
        """Save deployment status to deployments directory in volume"""
        try:
            file_path = f"{self.volume_path}/deployments/{deployment_id}.json"
            status_json = json.dumps(status, indent=2, default=str)

            # Run in thread pool since databricks SDK is synchronous
            loop = asyncio.get_event_loop()

            def _save_file():
                # Wrap bytes in BytesIO to make it a file-like object
                content_io = io.BytesIO(status_json.encode('utf-8'))
                self.client.files.upload(
                    file_path=file_path,
                    content=content_io,
                    overwrite=True
                )
                return True

            await loop.run_in_executor(None, _save_file)

            self.logger.debug(f"Saved deployment status for {deployment_id} to volume")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save deployment status for {deployment_id} to volume: {e}")
            return False

    async def get_deployment_status(self, deployment_id: str) -> Optional[Dict[str, Any]]:
        """Get deployment status from deployments directory in volume"""
        try:
            file_path = f"{self.volume_path}/deployments/{deployment_id}.json"

            # Run in thread pool since databricks SDK is synchronous
            loop = asyncio.get_event_loop()

            def _get_file():
                try:
                    response = self.client.files.download(file_path)
                    return response.contents.read()
                except Exception:
                    return None

            content = await loop.run_in_executor(None, _get_file)

            if content is None:
                return None

            return json.loads(content)
        except Exception as e:
            self.logger.error(f"Failed to get deployment status for {deployment_id} from volume: {e}")
            return None

    async def save_compiled_workflow(self, workflow_id: str, code: str, filename: str = "program.py") -> bool:
        """Save compiled workflow code to workflows directory in volume"""
        try:
            file_path = f"{self.volume_path}/workflows/{workflow_id}/{filename}"

            # Run in thread pool since databricks SDK is synchronous
            loop = asyncio.get_event_loop()

            def _save_file():
                # Wrap bytes in BytesIO to make it a file-like object
                content_io = io.BytesIO(code.encode('utf-8'))
                self.client.files.upload(
                    file_path=file_path,
                    content=content_io,
                    overwrite=True
                )
                return True

            await loop.run_in_executor(None, _save_file)

            self.logger.debug(f"Saved compiled workflow {workflow_id} to volume: {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save compiled workflow {workflow_id} to volume: {e}")
            return False

    async def get_compiled_workflow(self, workflow_id: str, filename: str = "program.py") -> Optional[str]:
        """Get compiled workflow code from workflows directory in volume"""
        try:
            file_path = f"{self.volume_path}/workflows/{workflow_id}/{filename}"

            # Run in thread pool since databricks SDK is synchronous
            loop = asyncio.get_event_loop()

            def _get_file():
                try:
                    response = self.client.files.download(file_path)
                    return response.contents.read()
                except Exception:
                    return None

            content = await loop.run_in_executor(None, _get_file)
            return content
        except Exception as e:
            self.logger.error(f"Failed to get compiled workflow {workflow_id} from volume: {e}")
            return None

    async def save_file(self, path: str, content: str) -> bool:
        """Save arbitrary file content to volume"""
        try:
            file_path = f"{self.volume_path}/{path}"

            # Run in thread pool since databricks SDK is synchronous
            loop = asyncio.get_event_loop()

            def _save_file():
                # Wrap bytes in BytesIO to make it a file-like object
                content_io = io.BytesIO(content.encode('utf-8'))
                self.client.files.upload(
                    file_path=file_path,
                    content=content_io,
                    overwrite=True
                )
                return True

            await loop.run_in_executor(None, _save_file)

            self.logger.debug(f"Saved file to volume: {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save file {path} to volume: {e}")
            return False

    async def get_file(self, path: str) -> Optional[str]:
        """Get arbitrary file content from volume"""
        try:
            file_path = f"{self.volume_path}/{path}"

            # Run in thread pool since databricks SDK is synchronous
            loop = asyncio.get_event_loop()

            def _get_file():
                try:
                    response = self.client.files.download(file_path)
                    return response.contents.read()
                except Exception:
                    return None

            return await loop.run_in_executor(None, _get_file)
        except Exception as e:
            self.logger.error(f"Failed to get file {path} from volume: {e}")
            return None

    async def copy_file(self, src_path: str, dest_path: str) -> bool:
        """Copy file to volume (from external source or within volume)"""
        try:
            # Read source file content
            if os.path.isabs(src_path) and os.path.exists(src_path):
                # External file
                with open(src_path, 'r') as f:
                    content = f.read()
            else:
                # File within volume
                content = await self.get_file(src_path)
                if content is None:
                    self.logger.error(f"Source file {src_path} not found in volume")
                    return False

            # Save to destination
            return await self.save_file(dest_path, content)
        except Exception as e:
            self.logger.error(f"Failed to copy file from {src_path} to {dest_path}: {e}")
            return False

    async def file_exists(self, path: str) -> bool:
        """Check if file exists in volume"""
        try:
            file_path = f"{self.volume_path}/{path}"

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

    async def save_optimization_status(self, optimization_id: str, status: Dict[str, Any]) -> bool:
        """Save optimization status to volume"""
        try:
            file_path = f"{self.volume_path}/optimizations/{optimization_id}.json"
            status_json = json.dumps(status, indent=2, default=str)

            # Run in thread pool since databricks SDK is synchronous
            loop = asyncio.get_event_loop()

            def _save_file():
                # Wrap bytes in BytesIO to make it a file-like object
                content_io = io.BytesIO(status_json.encode('utf-8'))
                self.client.files.upload(
                    file_path=file_path,
                    content=content_io,
                    overwrite=True
                )
                return True

            await loop.run_in_executor(None, _save_file)

            self.logger.debug(f"Saved optimization status for {optimization_id} to volume")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save optimization status for {optimization_id}: {e}")
            return False

    async def get_optimization_status(self, optimization_id: str) -> Optional[Dict[str, Any]]:
        """Get optimization status from volume"""
        try:
            file_path = f"{self.volume_path}/optimizations/{optimization_id}.json"

            # Run in thread pool since databricks SDK is synchronous
            loop = asyncio.get_event_loop()

            def _read_file():
                try:
                    with self.client.files.download(file_path).contents as f:
                        content = f.read()
                    return content.decode('utf-8')
                except Exception:
                    return None

            content = await loop.run_in_executor(None, _read_file)

            if content:
                return json.loads(content)
            return None
        except Exception as e:
            self.logger.error(f"Failed to get optimization status for {optimization_id}: {e}")
            return None

    async def list_workflow_optimizations(self, workflow_id: str) -> List[Dict[str, Any]]:
        """List all optimization runs for a workflow in volume"""
        optimizations = []
        try:
            optimizations_dir = f"{self.volume_path}/optimizations"

            # Run in thread pool since databricks SDK is synchronous
            loop = asyncio.get_event_loop()

            def _list_files():
                try:
                    # List all files in optimizations directory
                    files = self.client.files.list_directory_contents(optimizations_dir)
                    # Filter files matching pattern: opt_{workflow_id}_*.json
                    prefix = f"opt_{workflow_id}"
                    matching_files = []
                    for file_info in files:
                        if file_info.path.endswith('.json') and prefix in file_info.path:
                            matching_files.append(file_info.path)
                    return matching_files
                except Exception:
                    return []

            file_paths = await loop.run_in_executor(None, _list_files)

            # Load each file
            for file_path in file_paths:
                try:
                    def _read_file():
                        try:
                            with self.client.files.download(file_path).contents as f:
                                content = f.read()
                            return content.decode('utf-8')
                        except Exception:
                            return None

                    content = await loop.run_in_executor(None, _read_file)

                    if content:
                        optimization_data = json.loads(content)
                        # Extract optimization_id from file path
                        filename = file_path.split('/')[-1]
                        optimization_data['optimization_id'] = filename.replace('.json', '')
                        optimizations.append(optimization_data)
                except Exception as e:
                    self.logger.warning(f"Failed to load optimization from {file_path}: {e}")
                    continue

            # Sort by started_at in descending order (most recent first)
            optimizations.sort(key=lambda o: o.get('started_at', ''), reverse=True)

        except Exception as e:
            self.logger.error(f"Failed to list optimizations for workflow {workflow_id}: {e}")

        return optimizations

    async def list_workflow_deployments(self, workflow_id: str) -> List[Dict[str, Any]]:
        """List all deployments for a workflow in volume"""
        deployments = []
        try:
            deployments_dir = f"{self.volume_path}/deployments"

            # Run in thread pool since databricks SDK is synchronous
            loop = asyncio.get_event_loop()

            def _list_files():
                try:
                    # List all files in deployments directory
                    files = self.client.files.list_directory_contents(deployments_dir)
                    # Filter files matching pattern: deploy_{workflow_id}_*.json
                    prefix = f"deploy_{workflow_id}_"
                    matching_files = []
                    for file_info in files:
                        if file_info.path.endswith('.json') and prefix in file_info.path:
                            matching_files.append(file_info.path)
                    return matching_files
                except Exception:
                    return []

            file_paths = await loop.run_in_executor(None, _list_files)

            # Load each file
            for file_path in file_paths:
                try:
                    def _read_file():
                        try:
                            with self.client.files.download(file_path).contents as f:
                                content = f.read()
                            return content.decode('utf-8')
                        except Exception:
                            return None

                    content = await loop.run_in_executor(None, _read_file)

                    if content:
                        deployment_data = json.loads(content)
                        # Extract deployment_id from file path
                        filename = file_path.split('/')[-1]
                        deployment_data['deployment_id'] = filename.replace('.json', '')
                        deployments.append(deployment_data)
                except Exception as e:
                    self.logger.warning(f"Failed to load deployment from {file_path}: {e}")
                    continue

            # Sort by started_at in descending order (most recent first)
            deployments.sort(key=lambda d: d.get('started_at', ''), reverse=True)

        except Exception as e:
            self.logger.error(f"Failed to list deployments for workflow {workflow_id}: {e}")

        return deployments