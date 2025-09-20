from pydantic_settings import BaseSettings
from typing import Optional, Literal


class Settings(BaseSettings):
    app_name: str = "DSPy Workflow Builder"
    debug: bool = False
    api_prefix: str = "/api/v1"
    
    # Logging settings
    log_level: str = "INFO"
    log_file: Optional[str] = "./logs/app.log"
    
    # Debug settings
    debug_compiler: bool = True
    artifacts_path: str = "./artifacts"
    
    # Workflow storage configuration
    storage_backend: Literal["local", "databricks"] = "local"
    
    # Local storage settings
    local_storage_path: str = "./artifacts/workflows"
    
    # Databricks storage settings
    databricks_volume_path: Optional[str] = None
    
    # Databricks settings
    databricks_host: Optional[str] = None
    databricks_token: Optional[str] = None
    
    # DSPy LLM settings
    dspy_model: str = "openai/gpt-3.5-turbo"
    dspy_api_key: Optional[str] = None
    dspy_api_base: Optional[str] = None
    
    # CORS settings
    allowed_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    class Config:
        env_file = ".env"


settings = Settings()