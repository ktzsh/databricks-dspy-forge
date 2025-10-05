import dspy
import asyncio
import tempfile
import os
import json
import shutil

from datetime import datetime
from typing import Dict, Any, List, Optional

from databricks import sql
from databricks.sdk import WorkspaceClient
from dspy import GEPA, BootstrapFewShotWithRandomSearch, MIPROv2

from dspy_forge.core.config import settings
from dspy_forge.core.logging import get_logger
from dspy_forge.models.workflow import Workflow
from dspy_forge.core.dspy_runtime import CompoundProgram
from dspy_forge.services.execution_service import ExecutionContext
from dspy_forge.storage.factory import get_storage_backend

logger = get_logger(__name__)


class OptimizationService:
    """Service for optimizing DSPy workflows using various optimizers"""

    def __init__(self):
        self.active_optimizations: Dict[str, Dict[str, Any]] = {}

    async def _save_optimization_status(self, optimization_id: str, status: Dict[str, Any]):
        """Save optimization status using storage backend"""
        try:
            storage = await get_storage_backend()
            success = await storage.save_optimization_status(optimization_id, status)
            if success:
                logger.debug(f"Saved optimization status for {optimization_id}")
            else:
                logger.error(f"Failed to save optimization status for {optimization_id}")
        except Exception as e:
            logger.error(f"Failed to save optimization status for {optimization_id}: {e}")

    async def _load_optimization_status(self, optimization_id: str) -> Optional[Dict[str, Any]]:
        """Load optimization status using storage backend"""
        try:
            storage = await get_storage_backend()
            status = await storage.get_optimization_status(optimization_id)
            if status:
                logger.debug(f"Loaded optimization status for {optimization_id}")
            else:
                logger.debug(f"No status file found for optimization {optimization_id}")
            return status
        except Exception as e:
            logger.error(f"Failed to load optimization status for {optimization_id}: {e}")
            return None

    async def _load_dataset_from_uc(self, catalog: str, schema: str, table: str) -> List[dspy.Example]:
        """Load dataset from Unity Catalog table using Databricks SQL connector"""
        table_name = f"{catalog}.{schema}.{table}"
        logger.info(f"Loading dataset from {table_name}")

        # Check if warehouse ID is configured
        if not settings.databricks_warehouse_id:
            error_msg = (
                "DATABRICKS_WAREHOUSE_ID is not configured. "
                "Please set the environment variable to a valid SQL warehouse ID for optimization to work."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        def _load_data_sync():
            """Synchronous function to load data from UC table"""
            try:
                # Get Databricks connection parameters
                w = WorkspaceClient()
                config = w.config

                # Build http_path from warehouse ID
                http_path = f"/sql/1.0/warehouses/{settings.databricks_warehouse_id}"
                logger.info(f"Using SQL warehouse ID: {settings.databricks_warehouse_id}")

                # Create connection
                connection = sql.connect(
                    server_hostname=config.host,
                    http_path=http_path,
                    access_token=config.token
                )

                cursor = connection.cursor()

                # Query the table
                query = f"SELECT inputs, expectations FROM {table_name}"
                logger.debug(f"Executing query: {query}")
                cursor.execute(query)

                # Fetch all rows
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]

                cursor.close()
                connection.close()

                logger.info(f"Loaded {len(rows)} rows from {table_name}")

                # Convert rows to list of dicts
                data = []
                for row in rows:
                    row_dict = dict(zip(columns, row))
                    if len(row_dict["inputs"]["messages"]) > 1:
                        raise NotImplementedError("Multi-turn chat history is not supported yet.")

                    row_dict = {
                        "question": row_dict["inputs"]["messages"][-1]["content"],
                        "history": "",
                        "answer": list(row_dict["expectations"]["expected_facts"])
                    }
                    data.append(row_dict)

                input_columns = ["question", "history"]

                return data, input_columns

            except Exception as e:
                logger.error(f"Failed to load data from {table_name}: {e}")
                raise

        try:
            # Run the synchronous database operation in a thread pool
            data, input_columns = await asyncio.to_thread(_load_data_sync)

            # Convert to dspy.Example objects
            examples = []
            for row_dict in data:
                # Create dspy.Example with all fields
                example = dspy.Example(**row_dict)

                # Mark input fields using .with_inputs()
                example = example.with_inputs(*input_columns)

                examples.append(example)

            logger.info(f"Created {len(examples)} dspy.Example objects from {table_name}")
            return examples

        except Exception as e:
            logger.error(f"Failed to load dataset from {table_name}: {e}")
            raise

    def _create_scoring_metric(self, scoring_functions: List[Dict[str, Any]]) -> callable:
        """Create a composite scoring metric from scoring function configurations"""

        def metric(example, pred, trace=None):  # noqa: ARG001
            """Composite metric that combines multiple scoring functions"""
            total_score = 0.0
            feedback_parts = []

            for sf in scoring_functions:
                sf_type = sf['type']
                sf_name = sf['name']
                weightage = sf['weightage'] / 100.0  # Convert to 0-1 scale

                if sf_type == 'Correctness':
                    # Use MLflow's is_correct judge
                    from mlflow.genai.judges import is_correct

                    # Get expected facts from example
                    expected_facts = example.answer

                    # Get response from prediction
                    response = pred.answer

                    # Get query from example
                    query = example.question

                    feedback = is_correct(
                        request=query,
                        response=response,
                        expected_facts=expected_facts,
                        model="databricks",
                    )

                    score = 1.0 if feedback.value == "yes" else 0.0
                    total_score += score * weightage
                    feedback_parts.append(f"Correctness metric {sf_name} with ({weightage}/1 weight): {feedback.rationale}")


                elif sf_type == 'Guidelines':
                    # Use MLflow's guideline-based judge
                    from mlflow.genai.judges import meets_guidelines

                    guideline = sf.get('guideline', '')

                    # Get response from prediction
                    response = pred.answer

                    feedback = meets_guidelines(
                        guidelines=guideline,
                        context={"response": response},
                        model="databricks",
                    )

                    score = 1.0 if feedback.value == "yes" else 0.0
                    total_score += score * weightage
                    feedback_parts.append(f"Guideline follow score{sf_name} with ({weightage}/1 weight): {feedback.rationale}")

            return dspy.Prediction(
                score=total_score,
                feedback=" | ".join(feedback_parts)
            )

        return metric

    def _create_optimizer(
        self,
        optimizer_name: str,
        optimizer_config: Dict[str, str],
        metric: callable
    ):
        """Create optimizer instance based on configuration"""

        if optimizer_name == 'BootstrapFewShotWithRandomSearch':
            # Parse config parameters with defaults
            max_rounds = int(optimizer_config.get('max_rounds', 1))
            max_bootstrapped_demos = int(optimizer_config.get('max_bootstrapped_demos', 4))
            max_labeled_demos = int(optimizer_config.get('max_labeled_demos', 16))
            num_candidate_programs = int(optimizer_config.get('num_candidate_programs', 16))
            num_threads = int(optimizer_config.get('num_threads', 4))

            return BootstrapFewShotWithRandomSearch(
                metric=metric,
                max_rounds=max_rounds,
                max_bootstrapped_demos=max_bootstrapped_demos,
                max_labeled_demos=max_labeled_demos,
                num_candidate_programs=num_candidate_programs,
                num_threads=num_threads
            )

        elif optimizer_name == 'GEPA':
            # Parse config parameters with defaults
            auto = optimizer_config.get('auto', 'light')
            num_threads = int(optimizer_config.get('num_threads', 1))
            track_stats = optimizer_config.get('track_stats', 'true').lower() == 'true'
            use_merge = optimizer_config.get('use_merge', 'false').lower() == 'true'
            reflection_lm_model = optimizer_config.get('reflection_lm', 'databricks/databricks-llama-4-maverick')

            reflection_lm = dspy.LM(
                model=reflection_lm_model,
                temperature=1.0,
                max_tokens=8192
            )

            return GEPA(
                metric=metric,
                auto=auto,
                num_threads=num_threads,
                track_stats=track_stats,
                use_merge=use_merge,
                reflection_lm=reflection_lm
            )

        elif optimizer_name == 'MIPROv2':
            # Parse config parameters with defaults
            num_candidates = int(optimizer_config.get('num_candidates', 10))
            init_temperature = float(optimizer_config.get('init_temperature', 0.7))
            num_threads = int(optimizer_config.get('num_threads', 4))

            return MIPROv2(
                metric=metric,
                num_candidates=num_candidates,
                init_temperature=init_temperature,
                num_threads=num_threads
            )

        else:
            raise ValueError(f"Unknown optimizer: {optimizer_name}")

    async def optimize_workflow_async(
        self,
        workflow: Workflow,
        optimizer_name: str,
        optimizer_config: Dict[str, str],
        scoring_functions: List[Dict[str, Any]],
        training_data: Dict[str, str],
        validation_data: Dict[str, str],
        optimization_id: str
    ):
        """Execute workflow optimization asynchronously"""
        try:
            status = {
                "status": "initializing",
                "message": "Initializing optimization",
                "started_at": datetime.now().isoformat(),
                "workflow_id": workflow.id,
                "optimizer_name": optimizer_name
            }
            await self._save_optimization_status(optimization_id, status)

            # Step 1: Load datasets from Unity Catalog
            status.update({
                "status": "loading_data",
                "message": "Loading training and validation datasets"
            })
            await self._save_optimization_status(optimization_id, status)

            logger.info(f"Loading training dataset from {training_data['catalog']}.{training_data['schema']}.{training_data['table']}")
            trainset = await self._load_dataset_from_uc(
                training_data['catalog'],
                training_data['schema'],
                training_data['table']
            )

            logger.info(f"Loading validation dataset from {validation_data['catalog']}.{validation_data['schema']}.{validation_data['table']}")
            valset = await self._load_dataset_from_uc(
                validation_data['catalog'],
                validation_data['schema'],
                validation_data['table']
            )

            # Step 2: Create CompoundProgram from workflow IR
            status.update({
                "status": "building_program",
                "message": "Building DSPy program"
            })
            await self._save_optimization_status(optimization_id, status)

            logger.info(f"Creating CompoundProgram for workflow {workflow.id}")

            # Create a temporary execution context for program creation
            # Note: We use empty input data since we're just building the structure
            temp_context = ExecutionContext(workflow, {})
            program = CompoundProgram(workflow, temp_context)

            # Step 3: Create scoring metric
            logger.info(f"Creating composite scoring metric with {len(scoring_functions)} functions")
            metric = self._create_scoring_metric(scoring_functions)

            # Step 4: Create optimizer
            logger.info(f"Creating {optimizer_name} optimizer with config: {optimizer_config}")
            optimizer = self._create_optimizer(optimizer_name, optimizer_config, metric)

            # Step 5: Run optimization
            status.update({
                "status": "optimizing",
                "message": "Running optimization process"
            })
            await self._save_optimization_status(optimization_id, status)

            logger.info(f"Starting optimization for workflow {workflow.id}")

            # Run optimization based on optimizer type
            if optimizer_name in ['BootstrapFewShotWithRandomSearch', 'MIPROv2']:
                optimized_program = optimizer.compile(
                    program,
                    trainset=trainset,
                )
            elif optimizer_name == 'GEPA':
                optimized_program = optimizer.compile(
                    program,
                    trainset=trainset,
                    valset=valset,
                )
            else:
                raise ValueError(f"Unknown optimizer type: {optimizer_name}")

            # Step 6: Save optimized program
            status.update({
                "status": "saving_results",
                "message": "Saving optimized program"
            })
            await self._save_optimization_status(optimization_id, status)

            logger.info(f"Saving optimized program for workflow {workflow.id}")

            # Save optimized program to storage
            storage = await get_storage_backend()

            # Create temp directory for optimized program
            # Note: DSPy's save with save_program=True requires a directory, not a file
            temp_dir = tempfile.mkdtemp()

            try:
                # Save optimized program to temp directory (includes architecture and state)
                # Using save_program=True to save the complete program, not just state
                optimized_program.save(temp_dir, save_program=True)

                # DSPy saves to program.json in the directory when save_program=True
                state_file = os.path.join(temp_dir, "program.json")

                if os.path.exists(state_file):
                    with open(state_file, 'r') as f:
                        optimized_content = f.read()
                else:
                    # Fallback: If program.json doesn't exist, save the state dict as JSON
                    logger.warning("program.json not found in temp directory, saving state dict directly")
                    state_dict = optimized_program.dump_state()
                    optimized_content = json.dumps(state_dict, indent=2, default=str)

                # Save to storage backend
                optimized_path = f"workflows/{workflow.id}/optimized_program.json"
                success = await storage.save_file(optimized_path, optimized_content)

                if not success:
                    raise RuntimeError("Failed to save optimized program")

                logger.info(f"Saved optimized program to {optimized_path}")

            finally:
                # Clean up temp directory
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)

            # Success - update status
            status.update({
                "status": "completed",
                "message": "Optimization completed successfully",
                "completed_at": datetime.now().isoformat(),
                "optimized_program_path": optimized_path
            })
            await self._save_optimization_status(optimization_id, status)

            logger.info(f"Successfully optimized workflow {workflow.id} with {optimizer_name}")

        except Exception as e:
            error_msg = f"Optimization failed: {str(e)}"
            logger.error(f"Optimization failed for {optimization_id}: {error_msg}", exc_info=True)

            status.update({
                "status": "failed",
                "message": error_msg,
                "completed_at": datetime.now().isoformat()
            })
            await self._save_optimization_status(optimization_id, status)

    async def get_optimization_status(self, optimization_id: str) -> Optional[Dict[str, Any]]:
        """Get optimization status by ID"""
        return await self._load_optimization_status(optimization_id)


# Global optimization service instance
optimization_service = OptimizationService()
