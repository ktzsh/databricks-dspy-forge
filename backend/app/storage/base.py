from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.models.workflow import Workflow


class WorkflowStorageBackend(ABC):
    """Abstract base class for workflow storage backends"""
    
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