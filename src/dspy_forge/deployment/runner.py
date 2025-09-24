import mlflow

from typing import Any
from pkg_resources import get_distribution

from databricks import agents
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()
        
# Get current user information
current_user = w.current_user.me().user_name

mlflow.set_tracking_uri("databricks")
mlflow.set_registry_uri("databricks-uc")

def deploy_agent(
        workflow_id: str,
        agent_file_path: str,
        program_file_path: str,
        model_name: str,
        schema_name: str,
        catalog_name:str ,
        resources: list[Any]
    ):
    mlflow.set_experiment(f"/Users/{current_user}/DSPy-Forge-Experiment-{workflow_id}")
    with mlflow.start_run():
        logged_agent_info = mlflow.pyfunc.log_model(
            name="model",
            python_model=agent_file_path,
            pip_requirements=[
                f"databricks-ai-bridge=={get_distribution('databricks-ai-bridge').version}",
                f"databricks-sdk=={get_distribution('databricks-sdk').version}",
                f"dspy=={get_distribution('dspy').version}",
                f"databricks-agents=={get_distribution('databricks-agents').version}",
                f"mlflow=={get_distribution('mlflow').version}",
                f"pandas=={get_distribution('pandas').version}",
                f"databricks-connect=={get_distribution('databricks-connect').version}",
            ],
            registered_model_name=f"{catalog_name}.{schema_name}.{model_name}",
            code_paths=[program_file_path],
            input_example={"input": [{"role": "user", "content": "Hi, this is a test message."}]},
            resources=resources,
        )
    
    uc_registered_model_info = mlflow.register_model(
        model_uri=logged_agent_info.model_uri,
        name=f"{catalog_name}.{schema_name}.{model_name}",
    )

    deployment_info = agents.deploy(
        model_name=f"{catalog_name}.{schema_name}.{model_name}",
        model_version=uc_registered_model_info.version,
        scale_to_zero=True,
        endpoint_name=f"agents_{model_name}"
    )
    return deployment_info