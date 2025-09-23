from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any

from dspy_forge.models.workflow import Workflow


class StorageBackend(ABC):
    """Abstract base class for unified storage backends (workflows, deployments, artifacts)"""
    
    @abstractmethod
    async def save_workflow(self, workflow: Workflow) -> bool:
        """
        Save a workflow to the storage backend
        
        Args:
            workflow: The workflow to save
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """
        Retrieve a workflow by ID
        
        Args:
            workflow_id: The workflow ID
            
        Returns:
            The workflow if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def list_workflows(self) -> List[Workflow]:
        """
        List all workflows
        
        Returns:
            List of all workflows
        """
        pass
    
    @abstractmethod
    async def delete_workflow(self, workflow_id: str) -> bool:
        """
        Delete a workflow by ID
        
        Args:
            workflow_id: The workflow ID
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def workflow_exists(self, workflow_id: str) -> bool:
        """
        Check if a workflow exists
        
        Args:
            workflow_id: The workflow ID
            
        Returns:
            True if exists, False otherwise
        """
        pass
    
    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the storage backend (create directories, validate connection, etc.)
        
        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check of the storage backend

        Returns:
            Dictionary with health status information
        """
        pass

    # Deployment artifact management
    @abstractmethod
    async def save_deployment_status(self, deployment_id: str, status: Dict[str, Any]) -> bool:
        """
        Save deployment status

        Args:
            deployment_id: The deployment ID
            status: Status information to save

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    async def get_deployment_status(self, deployment_id: str) -> Optional[Dict[str, Any]]:
        """
        Get deployment status

        Args:
            deployment_id: The deployment ID

        Returns:
            Status information if found, None otherwise
        """
        pass

    @abstractmethod
    async def save_compiled_workflow(self, workflow_id: str, code: str, filename: str = "program.py") -> bool:
        """
        Save compiled workflow code

        Args:
            workflow_id: The workflow ID
            code: The compiled code to save
            filename: Name of the file to save (default: program.py)

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    async def get_compiled_workflow(self, workflow_id: str, filename: str = "program.py") -> Optional[str]:
        """
        Get compiled workflow code

        Args:
            workflow_id: The workflow ID
            filename: Name of the file to retrieve (default: program.py)

        Returns:
            The compiled code if found, None otherwise
        """
        pass

    @abstractmethod
    async def save_file(self, path: str, content: str) -> bool:
        """
        Save arbitrary file content

        Args:
            path: Relative path within storage (e.g., "workflows/abc123/agent.py")
            content: File content to save

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    async def get_file(self, path: str) -> Optional[str]:
        """
        Get arbitrary file content

        Args:
            path: Relative path within storage

        Returns:
            File content if found, None otherwise
        """
        pass

    @abstractmethod
    async def copy_file(self, src_path: str, dest_path: str) -> bool:
        """
        Copy file within storage

        Args:
            src_path: Source path (can be absolute for local files)
            dest_path: Destination path within storage

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    async def file_exists(self, path: str) -> bool:
        """
        Check if file exists

        Args:
            path: Relative path within storage

        Returns:
            True if exists, False otherwise
        """
        pass


# Backward compatibility alias
WorkflowStorageBackend = StorageBackend