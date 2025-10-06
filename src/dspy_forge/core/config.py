import os
import mlflow

from pydantic_settings import BaseSettings
from typing import Optional, Literal

from databricks.sdk import WorkspaceClient


def configure_databricks_auth(settings):
    # Set Databricks SDK environment variables from settings
    if settings.databricks_config_profile:
        os.environ["MLFLOW_ENABLE_DB_SDK"] = "true"
        os.environ["DATABRICKS_CONFIG_PROFILE"] = settings.databricks_config_profile
    elif settings.databricks_host and settings.databricks_token:
        os.environ["MLFLOW_ENABLE_DB_SDK"] = "true"
        os.environ["DATABRICKS_HOST"] = settings.databricks_host
        os.environ["DATABRICKS_TOKEN"] = settings.databricks_token
    elif (os.environ.get("DATABRICKS_CLIENT_ID", None) and 
        os.environ.get("DATABRICKS_CLIENT_SECRET", None)):
        # App is running on Databricks Apps
        pass
    else:
        raise ValueError("Databricks configuration not provided in environment variables.")
    
def configure_managed_mlflow():
    if profile_name := os.environ.get("DATABRICKS_CONFIG_PROFILE", None):
        mlflow.set_tracking_uri(f"databricks://{profile_name}")
        mlflow.set_registry_uri(f"databricks-uc://{profile_name}")
    else:
        mlflow.set_tracking_uri("databricks")
        mlflow.set_registry_uri("databricks-uc")

class Settings(BaseSettings):
    app_name: str = "DSPy Workflow Builder"
    debug: bool = False
    api_prefix: str = "/api/v1"
    
    # Logging settings
    log_level: str = "INFO"
    log_file: Optional[str] = None # "./logs/app.log"
        
    # Storage settings
    storage_backend: Literal["local", "databricks"] = "local"
    artifacts_path: str = "./artifacts/"
    # artifacts_path: str = "/Volumes/users/kshitiz_sharma/dspy_forge_artifacts"
    
    # Databricks settings
    databricks_config_profile: Optional[str] = None
    databricks_host: Optional[str] = None
    databricks_token: Optional[str] = None
    databricks_warehouse_id: Optional[str] = None
    
    # CORS settings
    allowed_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    class Config:
        env_file = ".env"


settings = Settings()

configure_databricks_auth(settings)
configure_managed_mlflow()