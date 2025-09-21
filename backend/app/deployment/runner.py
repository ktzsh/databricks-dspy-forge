import mlflow

from typing import Any
from databricks import agents
from pkg_resources import get_distribution
from mlflow.pyfunc import ResponsesAgent

mlflow.set_registry_uri("databricks-uc")


def main(
        model_name: str,
        schema_name: str,
        catalog_name:str ,
        resources: list[Any]
    ):
    with mlflow.start_run():
        logged_agent_info = mlflow.pyfunc.log_model(
            name="agent",
            python_model="agent.py",
            extra_pip_requirements=[
                f"databricks-ai-bridge=={get_distribution('databricks-ai-bridge').version}",
                f"databricks-sdk=={get_distribution('databricks-sdk').version}",
                f"dspy=={get_distribution('dspy').version}",
                f"databricks-agents=={get_distribution('databricks-agents').version}",
                f"mlflow=={get_distribution('mlflow').version}"
            ],
            resources=resources,
        )
    
    uc_registered_model_info = mlflow.register_model(
        model_uri=logged_agent_info.model_uri,
        name=f"{catalog_name}.{schema_name}.{model_name}",
    )

    agents.deploy(
        f"{catalog_name}.{schema_name}.{model_name}",
        uc_registered_model_info.version,
    )