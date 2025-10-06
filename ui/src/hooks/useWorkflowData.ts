import { useState, useEffect, useCallback } from 'react';
import { WorkflowCardData, WorkflowHistory } from '../types/dashboard';
import { useToast } from './useToast';

export const useWorkflowData = () => {
  const [workflows, setWorkflows] = useState<WorkflowCardData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { showError } = useToast();

  const fetchWorkflows = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch all workflows
      const response = await fetch('/api/v1/workflows/');

      if (!response.ok) {
        throw new Error('Failed to fetch workflows');
      }

      const workflowsData = await response.json();

      // Fetch history for each workflow in parallel
      const workflowsWithHistory = await Promise.all(
        workflowsData.map(async (workflow: any) => {
          try {
            const historyResponse = await fetch(`/api/v1/workflows/${workflow.id}/history`);

            if (!historyResponse.ok) {
              console.warn(`Failed to fetch history for workflow ${workflow.id}`);
              return {
                ...workflow,
                latestOptimization: undefined,
                latestDeployment: undefined,
                optimizationCount: 0,
                deploymentCount: 0
              };
            }

            const history: WorkflowHistory = await historyResponse.json();

            return {
              ...workflow,
              latestOptimization: history.optimizations?.[0],
              latestDeployment: history.deployments?.[0],
              optimizationCount: history.optimizations?.length || 0,
              deploymentCount: history.deployments?.length || 0
            } as WorkflowCardData;
          } catch (err) {
            console.error(`Error fetching history for workflow ${workflow.id}:`, err);
            return {
              ...workflow,
              latestOptimization: undefined,
              latestDeployment: undefined,
              optimizationCount: 0,
              deploymentCount: 0
            };
          }
        })
      );

      setWorkflows(workflowsWithHistory);
    } catch (err: any) {
      const errorMessage = err.message || 'Failed to load workflows';
      setError(errorMessage);
      showError('Load Failed', errorMessage);
    } finally {
      setLoading(false);
    }
  }, [showError]);

  useEffect(() => {
    fetchWorkflows();
  }, [fetchWorkflows]);

  const refreshWorkflows = useCallback(() => {
    fetchWorkflows();
  }, [fetchWorkflows]);

  return {
    workflows,
    loading,
    error,
    refreshWorkflows
  };
};
