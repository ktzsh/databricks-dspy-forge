import os
import shutil
import json

from datetime import datetime
from typing import Dict, Any, List, Optional

from mlflow.models.resources import (
    DatabricksFunction,
    DatabricksGenieSpace,
    DatabricksSQLWarehouse,
    DatabricksTable,
    DatabricksServingEndpoint,
    DatabricksVectorSearchIndex,
)

from app.models.workflow import Workflow, NodeType
from app.services.validation_service import validation_service
from app.services.compiler_service import compiler_service
from app.core.config import settings
from app.core.logging import get_logger
from app.deployment.runner import deploy_agent

logger = get_logger(__name__)


class DeploymentService:
    """Service for deploying workflows to Databricks as agent endpoints"""
    
    def __init__(self):
        self.status_dir = os.path.join(settings.artifacts_path, "deployments")
        os.makedirs(self.status_dir, exist_ok=True)
    
    def _save_deployment_status(self, deployment_id: str, status: Dict[str, Any]):
        """Save deployment status to file"""
        try:
            status_file = os.path.join(self.status_dir, f"{deployment_id}.json")
            with open(status_file, 'w') as f:
                json.dump(status, f, indent=2)
            logger.debug(f"Saved deployment status for {deployment_id}")
        except Exception as e:
            logger.error(f"Failed to save deployment status for {deployment_id}: {e}")
    
    def _load_deployment_status(self, deployment_id: str) -> Optional[Dict[str, Any]]:
        """Load deployment status from file"""
        try:
            status_file = os.path.join(self.status_dir, f"{deployment_id}.json")
            if os.path.exists(status_file):
                with open(status_file, 'r') as f:
                    status = json.load(f)
                logger.debug(f"Loaded deployment status for {deployment_id}")
                return status
            else:
                logger.debug(f"No status file found for deployment {deployment_id}")
                return None
        except Exception as e:
            logger.error(f"Failed to load deployment status for {deployment_id}: {e}")
            return None
    
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
            self._save_deployment_status(deployment_id, status)
            
            # Step 1: Validate workflow
            logger.info(f"Validating workflow {workflow.id}")
            errors = validation_service.validate_workflow(workflow)
            if errors:
                status.update({
                    "status": "failed",
                    "message": f"Validation failed: {'; '.join(errors)}",
                    "completed_at": datetime.now().isoformat()
                })
                self._save_deployment_status(deployment_id, status)
                return
            
            # Step 2: Compile workflow
            status.update({
                "status": "compiling",
                "message": "Compiling workflow to DSPy code"
            })
            self._save_deployment_status(deployment_id, status)
            
            logger.info(f"Compiling workflow {workflow.id}")
            workflow_code = compiler_service.compile_workflow_to_code(workflow)
            
            # Step 3: Create deployment directory and save code
            artifacts_dir = os.path.join(settings.artifacts_path, "workflows", workflow.id)
            os.makedirs(artifacts_dir, exist_ok=True)
            
            # Write program.py
            program_path = os.path.join(artifacts_dir, "program.py")
            with open(program_path, 'w') as f:
                f.write(f"# DSPy Workflow: {workflow.id}\n")
                f.write(f"# Generated at: {datetime.now().isoformat()}\n\n")
                f.write(workflow_code)
            
            logger.info(f"Saved workflow code to {program_path}")
            
            # Step 4: Copy agent.py
            agent_source = os.path.join(os.path.dirname(__file__), "..", "deployment", "agent.py")
            agent_dest = os.path.join(artifacts_dir, "agent.py")
            shutil.copy2(agent_source, agent_dest)
            
            logger.info(f"Copied agent.py to {agent_dest}")
            
            # Step 5: Generate resource list
            resources = self._generate_resource_list(workflow)
            
            # Step 6: Deploy using runner
            status.update({
                "status": "deploying",
                "message": "Deploying to Databricks"
            })
            self._save_deployment_status(deployment_id, status)
            
            logger.info(f"Starting Databricks deployment for {model_name}")            
            
            # Call the deployment
            deploy_agent(
                agent_file_path=agent_dest,
                program_file_path=program_path,
                model_name=model_name,
                catalog_name=catalog_name,
                schema_name=schema_name,
                resources=resources
            )
            
            # Success - update status
            endpoint_url = f"https://databricks.com/serving-endpoints/{catalog_name}.{schema_name}.{model_name}"
            status.update({
                "status": "completed",
                "message": "Deployment completed successfully",
                "completed_at": datetime.now().isoformat(),
                "endpoint_url": endpoint_url,
                "resources": resources
            })
            self._save_deployment_status(deployment_id, status)
            
            logger.info(f"Successfully deployed workflow {workflow.id} as {catalog_name}.{schema_name}.{model_name}")
            
        except Exception as e:
            error_msg = f"Deployment failed: {str(e)}"
            logger.error(f"Deployment failed for {deployment_id}: {error_msg}", exc_info=True)
            
            status.update({
                "status": "failed",
                "message": error_msg,
                "completed_at": datetime.now().isoformat()
            })
            self._save_deployment_status(deployment_id, status)
    
    def get_deployment_status(self, deployment_id: str) -> Optional[Dict[str, Any]]:
        """Get deployment status by ID"""
        return self._load_deployment_status(deployment_id)
    
    def _generate_resource_list(self, workflow: Workflow) -> List[Dict[str, Any]]:
        """Generate list of resources based on workflow components"""
        resources = []
        
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
                    models_used.add(model_name)
            
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
                    space_id = node_data.get('space_id')
                    if space_id:
                        structured_spaces.add(space_id)
        
        # Create resource entries
        for model in models_used:
            resources.append(
                DatabricksServingEndpoint(endpoint_name=model)
            )
        
        for catalog, schema, index_name in unstructured_indices:
            resources.append(
                DatabricksVectorSearchIndex(index_name=f"{catalog}.{schema}.{index_name}")
            )
        
        for space_id in structured_spaces:
            resources.append(
                DatabricksGenieSpace(space_id=space_id)
            )
        
        logger.info(f"Generated {len(resources)} resources for deployment")
        logger.debug(f"Resources: {resources}")
        
        return resources


# Global deployment service instance
deployment_service = DeploymentService()