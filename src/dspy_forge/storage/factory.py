from typing import Optional

from dspy_forge.storage.base import StorageBackend
from dspy_forge.storage.local import LocalDirectoryStorage
from dspy_forge.storage.databricks import DatabricksVolumeStorage
from dspy_forge.core.config import settings
from dspy_forge.core.logging import get_logger


logger = get_logger(__name__)


class StorageBackendFactory:
    """Factory class for creating workflow storage backends"""
    
    @staticmethod
    def create_storage_backend() -> StorageBackend:
        """
        Create a storage backend based on configuration
        
        Returns:
            Configured storage backend instance
            
        Raises:
            ValueError: If storage backend configuration is invalid
            RuntimeError: If storage backend initialization fails
        """
        backend_type = settings.storage_backend.lower()
        
        logger.info(f"Creating storage backend: {backend_type}")
        
        if backend_type == "local":
            return StorageBackendFactory._create_local_storage()
        elif backend_type == "databricks":
            return StorageBackendFactory._create_databricks_storage()
        else:
            raise ValueError(f"Unsupported storage backend: {backend_type}")
    
    @staticmethod
    def _create_local_storage() -> LocalDirectoryStorage:
        """Create local directory storage backend"""
        storage_path = settings.artifacts_path
        logger.debug(f"Creating local storage with path: {storage_path}")
        return LocalDirectoryStorage(storage_path)
    
    @staticmethod
    def _create_databricks_storage() -> DatabricksVolumeStorage:
        """Create Databricks volume storage backend"""
        volume_path = settings.artifacts_path
        
        if not volume_path:
            raise ValueError(
                "artifacts_path must be configured when using Databricks storage backend"
            )
        
        logger.debug(f"Creating Databricks storage with volume path: {volume_path}")
        
        return DatabricksVolumeStorage(
            volume_path=volume_path
        )


# Global storage backend instance
_storage_backend: Optional[StorageBackend] = None


async def get_storage_backend() -> StorageBackend:
    """
    Get the configured storage backend instance (singleton pattern)
    
    Returns:
        Initialized storage backend instance
    """
    global _storage_backend
    
    if _storage_backend is None:
        _storage_backend = StorageBackendFactory.create_storage_backend()
        
        # Initialize the backend
        success = await _storage_backend.initialize()
        if not success:
            raise RuntimeError("Failed to initialize storage backend")
        
        logger.info("Storage backend initialized successfully")
    
    return _storage_backend


async def reset_storage_backend():
    """Reset the storage backend (useful for testing)"""
    global _storage_backend
    _storage_backend = None