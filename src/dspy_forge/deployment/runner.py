import os
import mlflow

from typing import Any, Optional
from pkg_resources import get_distribution

from mlflow.models.auth_policy import AuthPolicy, SystemAuthPolicy, UserAuthPolicy
from mlflow.models.resources import DatabricksServingEndpoint

from databricks import agents
from databricks.sdk import WorkspaceClient

from dspy_forge.core.config import settings
from dspy_forge.core.logging import get_logger

logger = get_logger(__name__)

def deploy_agent(
        workflow_id: str,
        agent_file_path: str,
        program_file_path: str,
        model_name: str,
        schema_name: str,
        catalog_name: str,
        auth_policy: tuple[list[Any], list[Any]],
        program_json_path: Optional[str] = None
    ):
    w = WorkspaceClient()
    current_user = w.current_user.me().user_name

    mlflow.set_experiment(
        f"/Users/{current_user}/DSPy-Forge-Experiment-{workflow_id}"
    )

    authentication_kwargs = {}
    if auth_policy[1]:
        # System policy: resources accessed with system credentials
        system_policy = SystemAuthPolicy(
            resources=auth_policy[0]
        )

        # User policy: API scopes for OBO access
        user_policy = UserAuthPolicy(
            api_scopes=auth_policy[1]
        )

        authentication_kwargs["auth_policy"] = AuthPolicy(
            system_auth_policy=system_policy,
            user_auth_policy=user_policy
        )
    else:
        # System Policy: resources accessed with system credentials
        authentication_kwargs["resources"] = auth_policy[0]

    logger.info(f"Using authentication kwargs: {authentication_kwargs}")

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
            artifacts={"program_state_path": program_json_path} if program_json_path else None,
            input_example={"input": [{"role": "user", "content": "Hi, this is a test message."}]},
            **authentication_kwargs
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