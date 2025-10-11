import os
import mlflow

from pydantic_settings import BaseSettings
from typing import Optional, Literal

from databricks.sdk import WorkspaceClient
from dspy_forge.core.logging import get_logger

logger = get_logger(__name__)

def configure_databricks_auth(settings):
    # Set Databricks SDK environment variables from settings
    if settings.databricks_config_profile:
        os.environ["MLFLOW_ENABLE_DB_SDK"] = "true"
        os.environ["DATABRICKS_CONFIG_PROFILE"] = settings.databricks_config_profile
        mlflow.set_tracking_uri(f"databricks://{settings.databricks_config_profile}")
        mlflow.set_registry_uri(f"databricks-uc://{settings.databricks_config_profile}")
    elif settings.databricks_host and settings.databricks_token:
        os.environ["MLFLOW_ENABLE_DB_SDK"] = "true"
        os.environ["DATABRICKS_HOST"] = settings.databricks_host
        os.environ["DATABRICKS_TOKEN"] = settings.databricks_token
        mlflow.set_tracking_uri("databricks")
        mlflow.set_registry_uri("databricks-uc")
    elif (os.environ.get("DATABRICKS_CLIENT_ID", None) and 
        os.environ.get("DATABRICKS_CLIENT_SECRET", None)):
        os.environ["MLFLOW_ENABLE_DB_SDK"] = "true"
        mlflow.set_tracking_uri("databricks")
        mlflow.set_registry_uri("databricks-uc")
    else:
        logger.info(
            "Databricks integration is not configured."
        )
        # raise ValueError(
        #     "Databricks configuration is missing. Please provide either DATABRICKS_CONFIG_PROFILE or DATABRICKS_HOST and DATABRICKS_TOKEN in .env file."
        # )

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

    # LM Provider settings (for non-Databricks models)
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    custom_lm_api_base: Optional[str] = None
    custom_lm_api_key: Optional[str] = None

    # CORS settings
    allowed_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    class Config:
        env_file = ".env"


settings = Settings()

configure_databricks_auth(settings)