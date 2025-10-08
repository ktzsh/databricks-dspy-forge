import os
import json
import shutil
import tempfile
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

from mlflow.models.resources import (
    DatabricksFunction,
    DatabricksGenieSpace,
    DatabricksSQLWarehouse,
    DatabricksTable,
    DatabricksServingEndpoint,
    DatabricksVectorSearchIndex,
)

from dspy_forge.models.workflow import Workflow, NodeType
from dspy_forge.services.validation_service import validation_service
from dspy_forge.services.compiler_service import compiler_service
from dspy_forge.storage.factory import get_storage_backend
from dspy_forge.core.logging import get_logger
from dspy_forge.deployment.runner import deploy_agent

logger = get_logger(__name__)


class DeploymentService:
    """Service for deploying workflows to Databricks as agent endpoints"""

    def __init__(self):
        self._temp_dir = None

    async def _save_deployment_status(self, deployment_id: str, status: Dict[str, Any]):
        """Save deployment status using storage backend"""
        try:
            storage = await get_storage_backend()
            success = await storage.save_deployment_status(deployment_id, status)
            if success:
                logger.debug(f"Saved deployment status for {deployment_id}")
            else:
                logger.error(f"Failed to save deployment status for {deployment_id}")
        except Exception as e:
            logger.error(f"Failed to save deployment status for {deployment_id}: {e}")

    async def _load_deployment_status(self, deployment_id: str) -> Optional[Dict[str, Any]]:
        """Load deployment status using storage backend"""
        try:
            storage = await get_storage_backend()
            status = await storage.get_deployment_status(deployment_id)
            if status:
                logger.debug(f"Loaded deployment status for {deployment_id}")
            else:
                logger.debug(f"No status file found for deployment {deployment_id}")
            return status
        except Exception as e:
            logger.error(f"Failed to load deployment status for {deployment_id}: {e}")
            return None

    async def _get_local_file_path(self, storage, path: str) -> str:
        """Get local file path for deployment, creating temp file if using remote storage"""
        from dspy_forge.storage.local import LocalDirectoryStorage

        if isinstance(storage, LocalDirectoryStorage):
            # For local storage, return direct path
            full_path = storage.storage_path / path
            return str(full_path)
        else:
            # For remote storage, create temp file in shared temp directory
            content = await storage.get_file(path)
            if content is None:
                raise RuntimeError(f"File not found in storage: {path}")

            # Create shared temp directory if it doesn't exist
            if self._temp_dir is None:
                self._temp_dir = tempfile.mkdtemp()
                logger.debug(f"Created shared temporary directory {self._temp_dir}")

            original_filename = Path(path).name
            temp_file_path = os.path.join(self._temp_dir, original_filename)

            if isinstance(content, bytes):
                with open(temp_file_path, 'wb') as f:
                    f.write(content)
            else:
                with open(temp_file_path, 'w') as f:
                    f.write(content)

            logger.debug(f"Created temporary file {temp_file_path} for {path}")
            return temp_file_path
    
    async def deploy_workflow_async(
        self, 
        workflow: Workflow, 
        model_name: str, 
        catalog_name: str, 
        schema_name: str, 
        deployment_id: str
    ):
        """Deploy workflow asynchronously"""
        try:
            status = {
                "status": "validating",
                "message": "Validating workflow",
                "started_at": datetime.now().isoformat(),
                "workflow_id": workflow.id,
                "model_name": model_name,
                "catalog_name": catalog_name,
                "schema_name": schema_name
            }
            await self._save_deployment_status(deployment_id, status)
            
            # Step 1: Validate workflow
            logger.info(f"Validating workflow {workflow.id}")
            errors = validation_service.validate_workflow(workflow)
            if errors:
                status.update({
                    "status": "failed",
                    "message": f"Validation failed: {'; '.join(errors)}",
                    "completed_at": datetime.now().isoformat()
                })
                await self._save_deployment_status(deployment_id, status)
                return
            
            # Step 2: Compile workflow
            status.update({
                "status": "compiling",
                "message": "Compiling workflow to DSPy code"
            })
            await self._save_deployment_status(deployment_id, status)
            
            logger.info(f"Compiling workflow {workflow.id}")
            workflow_code, node_mapping = compiler_service.compile_workflow_to_code(workflow)

            # Step 3: Save compiled workflow code using storage backend
            storage = await get_storage_backend()

            # Add header to workflow code
            workflow_code_with_header = f"# DSPy Workflow: {workflow.id}\n"
            workflow_code_with_header += f"# Generated at: {datetime.now().isoformat()}\n\n"
            workflow_code_with_header += workflow_code

            # Save program.py
            success = await storage.save_compiled_workflow(workflow.id, workflow_code_with_header, "program.py")
            if not success:
                raise RuntimeError("Failed to save compiled workflow code")

            logger.info(f"Saved compiled workflow code for {workflow.id}")

            # Step 4: Copy agent.py
            agent_source = os.path.join(os.path.dirname(__file__), "..", "deployment", "agent.py")

            # Read agent.py and save to storage
            with open(agent_source, 'r') as f:
                agent_content = f.read()

            success = await storage.save_file(f"workflows/{workflow.id}/agent.py", agent_content)
            if not success:
                raise RuntimeError("Failed to save agent.py")

            logger.info(f"Copied agent.py for workflow {workflow.id}")

            # Step 4b: Transform program.json if it exists
            transformed_program_json_path = None
            program_json_content = await storage.get_file(f"workflows/{workflow.id}/program.json")

            if program_json_content:
                logger.info(f"Found program.json for workflow {workflow.id}, transforming for deployment")

                # Parse program.json
                program_data = json.loads(program_json_content)

                # Transform keys from node IDs to variable names
                transformed_data = {}
                for key, value in program_data.items():
                    if key.startswith("components['") and key.endswith("']"):
                        # Extract node ID from key like "components['node-123']"
                        node_id = key.split("'")[1]
                        var_name = node_mapping[node_id]
                        transformed_data[var_name] = value
                    else:
                        # Keep non-component keys as-is (e.g., metadata)
                        transformed_data[key] = value

                # TODO FIXME Hack since components implements retrievers incorrectly 
                # so when saving they are not saved into program.json
                for key, value in node_mapping.items():
                    if value.startswith("retriever"):
                        transformed_data[value] = {
                            "traces": [],
                            "train": [],
                            "demos": [],
                            "signature": {},
                            "lm": None
                        }

                # Create temp directory if needed
                if self._temp_dir is None:
                    self._temp_dir = tempfile.mkdtemp()

                # Save transformed program.json to temp file
                transformed_program_json_path = os.path.join(self._temp_dir, "program.json")
                with open(transformed_program_json_path, 'w') as f:
                    json.dump(transformed_data, f, indent=2)

                logger.info(f"Created transformed program.json at {transformed_program_json_path}")

            # Step 5: Generate resource list
            system_policy, user_policy = self._generate_resource_list(workflow)

            # Step 6: Deploy using runner
            status.update({
                "status": "deploying",
                "message": "Deploying to Databricks"
            })
            await self._save_deployment_status(deployment_id, status)

            logger.info(f"Starting Databricks deployment for {model_name}")

            # Get file paths for deployment - check if storage is local or create temp files
            agent_file_path = await self._get_local_file_path(storage, f"workflows/{workflow.id}/agent.py")
            program_file_path = await self._get_local_file_path(storage, f"workflows/{workflow.id}/program.py")

            # Call the deployment
            deployment_info = deploy_agent(
                workflow_id=workflow.id,
                agent_file_path=agent_file_path,
                program_file_path=program_file_path,
                program_json_path=transformed_program_json_path,
                model_name=model_name,
                catalog_name=catalog_name,
                schema_name=schema_name,
                auth_policy=(system_policy, user_policy)
            )
            logger.debug(f"Deployment info: {deployment_info}")
            
            # Success - update status
            status.update({
                "status": "completed",
                "message": "Deployment completed successfully",
                "completed_at": datetime.now().isoformat(),
                "endpoint_url": deployment_info.endpoint_url,
                "review_app_url": deployment_info.review_app_url
            })
            await self._save_deployment_status(deployment_id, status)
            
            logger.info(f"Successfully deployed workflow {workflow.id} as {catalog_name}.{schema_name}.{model_name}")

        except Exception as e:
            error_msg = f"Deployment failed: {str(e)}"
            logger.error(f"Deployment failed for {deployment_id}: {error_msg}", exc_info=True)

            status.update({
                "status": "failed",
                "message": error_msg,
                "completed_at": datetime.now().isoformat()
            })
            await self._save_deployment_status(deployment_id, status)

        finally:
            # Cleanup temp directory
            if self._temp_dir and os.path.exists(self._temp_dir):
                try:
                    shutil.rmtree(self._temp_dir)
                    logger.info(f"Cleaned up temporary directory {self._temp_dir}")
                    self._temp_dir = None
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp directory: {e}")
    
    async def get_deployment_status(self, deployment_id: str) -> Optional[Dict[str, Any]]:
        """Get deployment status by ID"""
        return await self._load_deployment_status(deployment_id)
    
    def _generate_resource_list(self, workflow: Workflow) -> List[Dict[str, Any]]:
        """Generate list of resources based on workflow components"""
        user_resource_scopes = []
        system_resources = []
        
        # Track unique resources
        models_used = set()
        embedding_models_used = set()
        unstructured_indices = set()
        structured_spaces = set()
        
        for node in workflow.nodes:
            node_data = node.data or {}
            
            # Extract model information
            if node.type == NodeType.MODULE:
                model_name = node_data.get('model')
                if model_name:
                    models_used.add(model_name.split("/")[-1])
            
            # Extract retriever information
            if node.type == NodeType.RETRIEVER:
                retriever_type = node_data.get('retriever_type')
                
                if retriever_type == 'UnstructuredRetrieve':
                    # Extract unstructured index info
                    catalog = node_data.get('catalog_name')
                    schema = node_data.get('schema_name') 
                    index_name = node_data.get('index_name')
                    embedding_model = node_data.get('embedding_model')
                    
                    if catalog and schema and index_name:
                        unstructured_indices.add((catalog, schema, index_name))
                    if embedding_model:
                        models_used.add(embedding_model)
                
                elif retriever_type == 'StructuredRetrieve':
                    # Extract structured space info  
                    space_id = node_data.get('genie_space_id')
                    if space_id:
                        structured_spaces.add(space_id)
        
        # Create resource entries
        for model in models_used:
            system_resources.append(
                DatabricksServingEndpoint(endpoint_name=model)
            )
        
        for catalog, schema, index_name in unstructured_indices:
            system_resources.append(
                DatabricksVectorSearchIndex(index_name=f"{catalog}.{schema}.{index_name}")
            )
        
        for space_id in structured_spaces:
            system_resources.append(
                DatabricksGenieSpace(genie_space_id=space_id)
            )
            user_resource_scopes.extend(
                [
                    "dashboards.genie",
                    "sql.warehouses",
                    "sql.statement-execution"
                ]
            )
        
        logger.info(f"Generated {len(system_resources)} system resources and {len(user_resource_scopes)} user resource scopes for deployment")
        logger.debug(f"System Resources: {system_resources}")
        logger.debug(f"User Resource Scopes: {user_resource_scopes}")
        
        return system_resources, user_resource_scopes


# Global deployment service instance
deployment_service = DeploymentService()