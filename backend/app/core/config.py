from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    app_name: str = "DSPy Workflow Builder"
    debug: bool = False
    api_prefix: str = "/api/v1"
    
    # Workflow storage
    workflows_storage_path: str = "./workflows"
    
    # MLflow settings
    mlflow_tracking_uri: Optional[str] = None
    mlflow_experiment_name: str = "dspy-workflows"
    
    # Databricks settings
    databricks_host: Optional[str] = None
    databricks_token: Optional[str] = None
    
    # CORS settings
    allowed_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    class Config:
        env_file = ".env"


settings = Settings()