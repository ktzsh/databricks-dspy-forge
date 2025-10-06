import { Workflow } from './workflow';

export interface OptimizationStatus {
  optimization_id: string;
  status: 'queued' | 'initializing' | 'loading_data' | 'building_program' | 'optimizing' | 'saving_results' | 'completed' | 'failed';
  message: string;
  optimizer_name: string;
  started_at: string;
  completed_at?: string;
  workflow_id: string;
  optimized_program_path?: string;
}

export interface DeploymentStatus {
  deployment_id: string;
  status: 'validating' | 'compiling' | 'deploying' | 'completed' | 'failed';
  message: string;
  model_name: string;
  catalog_name: string;
  schema_name: string;
  started_at: string;
  completed_at?: string;
  workflow_id: string;
  endpoint_url?: string;
  review_app_url?: string;
}

export interface WorkflowHistory {
  workflow_id: string;
  workflow: Workflow;
  optimizations: OptimizationStatus[];
  deployments: DeploymentStatus[];
}

export interface WorkflowCardData extends Workflow {
  latestOptimization?: OptimizationStatus;
  latestDeployment?: DeploymentStatus;
  optimizationCount: number;
  deploymentCount: number;
}
