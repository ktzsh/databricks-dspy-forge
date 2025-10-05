import os
import json
import aiofiles
import shutil
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from dspy_forge.storage.base import StorageBackend
from dspy_forge.models.workflow import Workflow
from dspy_forge.core.logging import get_logger


class LocalDirectoryStorage(StorageBackend):
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
        return self.storage_path / "workflows" / f"{workflow_id}.json"
    
    async def save_workflow(self, workflow: Workflow) -> bool:
        """Save a workflow to local directory"""
        try:
            file_path = self._get_workflow_file_path(workflow.id)
            file_path.parent.mkdir(parents=True, exist_ok=True)

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
            workflows_dir = self.storage_path / "workflows"
            if not workflows_dir.exists():
                return workflows

            for file_path in workflows_dir.glob("*.json"):
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
            workflows_dir = self.storage_path / "workflows"
            workflow_count = len(list(workflows_dir.glob("*.json"))) if workflows_dir.exists() else 0

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

    # Deployment artifact management
    async def save_deployment_status(self, deployment_id: str, status: Dict[str, Any]) -> bool:
        """Save deployment status to deployments directory"""
        try:
            deployments_dir = self.storage_path / "deployments"
            deployments_dir.mkdir(parents=True, exist_ok=True)

            status_file = deployments_dir / f"{deployment_id}.json"
            status_json = json.dumps(status, indent=2, default=str)

            async with aiofiles.open(status_file, 'w') as f:
                await f.write(status_json)

            self.logger.debug(f"Saved deployment status for {deployment_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save deployment status for {deployment_id}: {e}")
            return False

    async def get_deployment_status(self, deployment_id: str) -> Optional[Dict[str, Any]]:
        """Get deployment status from deployments directory"""
        try:
            deployments_dir = self.storage_path / "deployments"
            status_file = deployments_dir / f"{deployment_id}.json"

            if not status_file.exists():
                return None

            async with aiofiles.open(status_file, 'r') as f:
                content = await f.read()
                return json.loads(content)
        except Exception as e:
            self.logger.error(f"Failed to get deployment status for {deployment_id}: {e}")
            return None

    async def save_compiled_workflow(self, workflow_id: str, code: str, filename: str = "program.py") -> bool:
        """Save compiled workflow code to workflows directory"""
        try:
            workflow_dir = self.storage_path / "workflows" / workflow_id
            workflow_dir.mkdir(parents=True, exist_ok=True)

            code_file = workflow_dir / filename

            async with aiofiles.open(code_file, 'w') as f:
                await f.write(code)

            self.logger.debug(f"Saved compiled workflow {workflow_id} to {code_file}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save compiled workflow {workflow_id}: {e}")
            return False

    async def get_compiled_workflow(self, workflow_id: str, filename: str = "program.py") -> Optional[str]:
        """Get compiled workflow code from workflows directory"""
        try:
            workflow_dir = self.storage_path / "workflows" / workflow_id
            code_file = workflow_dir / filename

            if not code_file.exists():
                return None

            async with aiofiles.open(code_file, 'r') as f:
                return await f.read()
        except Exception as e:
            self.logger.error(f"Failed to get compiled workflow {workflow_id}: {e}")
            return None

    async def save_file(self, path: str, content: str) -> bool:
        """Save arbitrary file content"""
        try:
            file_path = self.storage_path / path
            file_path.parent.mkdir(parents=True, exist_ok=True)

            async with aiofiles.open(file_path, 'w') as f:
                await f.write(content)

            self.logger.debug(f"Saved file to {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save file {path}: {e}")
            return False

    async def get_file(self, path: str) -> Optional[str]:
        """Get arbitrary file content"""
        try:
            file_path = self.storage_path / path

            if not file_path.exists():
                return None

            async with aiofiles.open(file_path, 'r') as f:
                return await f.read()
        except Exception as e:
            self.logger.error(f"Failed to get file {path}: {e}")
            return None

    async def copy_file(self, src_path: str, dest_path: str) -> bool:
        """Copy file within storage or from external source"""
        try:
            # If src_path is absolute, treat as external file
            if os.path.isabs(src_path):
                src = Path(src_path)
            else:
                src = self.storage_path / src_path

            dest = self.storage_path / dest_path
            dest.parent.mkdir(parents=True, exist_ok=True)

            # Use shutil for synchronous copy, then return True
            shutil.copy2(str(src), str(dest))

            self.logger.debug(f"Copied file from {src} to {dest}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to copy file from {src_path} to {dest_path}: {e}")
            return False

    async def file_exists(self, path: str) -> bool:
        """Check if file exists"""
        file_path = self.storage_path / path
        return file_path.exists()

    async def save_optimization_status(self, optimization_id: str, status: Dict[str, Any]) -> bool:
        """Save optimization status to optimizations directory"""
        try:
            optimizations_dir = self.storage_path / "optimizations"
            optimizations_dir.mkdir(parents=True, exist_ok=True)

            status_file = optimizations_dir / f"{optimization_id}.json"
            status_json = json.dumps(status, indent=2, default=str)

            async with aiofiles.open(status_file, 'w') as f:
                await f.write(status_json)

            self.logger.debug(f"Saved optimization status for {optimization_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save optimization status for {optimization_id}: {e}")
            return False

    async def get_optimization_status(self, optimization_id: str) -> Optional[Dict[str, Any]]:
        """Get optimization status from optimizations directory"""
        try:
            optimizations_dir = self.storage_path / "optimizations"
            status_file = optimizations_dir / f"{optimization_id}.json"

            if not status_file.exists():
                return None

            async with aiofiles.open(status_file, 'r') as f:
                content = await f.read()
                return json.loads(content)
        except Exception as e:
            self.logger.error(f"Failed to get optimization status for {optimization_id}: {e}")
            return None