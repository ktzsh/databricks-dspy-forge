import React, { useState, useEffect } from 'react';
import { Play, Edit3, Copy, Trash2, Download, Calendar, Clock } from 'lucide-react';
import { WorkflowNode, WorkflowEdge } from '../types/workflow';
import { useToast } from '../hooks/useToast';

interface SavedWorkflow {
  id: string;
  name: string;
  description: string;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  created_at: string;
  updated_at: string;
}

interface WorkflowListProps {
  onLoadWorkflow: (workflow: SavedWorkflow) => void;
  onClose: () => void;
}

const WorkflowList: React.FC<WorkflowListProps> = ({ onLoadWorkflow, onClose }) => {
  const [workflows, setWorkflows] = useState<SavedWorkflow[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedWorkflow, setSelectedWorkflow] = useState<string | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<{workflowId: string, workflowName: string} | null>(null);
  const { showSuccess, showError } = useToast();

  useEffect(() => {
    fetchWorkflows();
  }, []);

  const fetchWorkflows = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/v1/workflows/');
      
      if (response.ok) {
        const data = await response.json();
        setWorkflows(data);
      } else {
        showError('Failed to Load', 'Could not fetch workflows from server');
      }
    } catch (error) {
      showError('Network Error', 'Unable to connect to server');
    } finally {
      setLoading(false);
    }
  };

  const handleLoadWorkflow = (workflow: SavedWorkflow) => {
    onLoadWorkflow(workflow);
    onClose();
    showSuccess('Workflow Loaded', `"${workflow.name}" has been loaded successfully`);
  };

  const handleDeleteWorkflow = async (workflowId: string, workflowName: string) => {
    setDeleteConfirm({ workflowId, workflowName });
  };

  const confirmDelete = async () => {
    if (!deleteConfirm) return;

    try {
      const response = await fetch(`/api/v1/workflows/${deleteConfirm.workflowId}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        setWorkflows(prev => prev.filter(w => w.id !== deleteConfirm.workflowId));
        showSuccess('Workflow Deleted', `"${deleteConfirm.workflowName}" has been deleted`);
      } else {
        showError('Delete Failed', 'Could not delete workflow');
      }
    } catch (error) {
      showError('Network Error', 'Unable to delete workflow');
    } finally {
      setDeleteConfirm(null);
    }
  };

  const handleDuplicateWorkflow = async (workflowId: string, workflowName: string) => {
    try {
      const response = await fetch(`/api/v1/workflows/${workflowId}/duplicate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ new_name: `${workflowName} (Copy)` }),
      });

      if (response.ok) {
        await fetchWorkflows(); // Refresh the list
        showSuccess('Workflow Duplicated', `Copy of "${workflowName}" has been created`);
      } else {
        showError('Duplicate Failed', 'Could not duplicate workflow');
      }
    } catch (error) {
      showError('Network Error', 'Unable to duplicate workflow');
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  const getWorkflowStats = (workflow: SavedWorkflow) => {
    const nodeCount = workflow.nodes.length;
    const edgeCount = workflow.edges.length;
    return `${nodeCount} nodes, ${edgeCount} connections`;
  };

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-8 max-w-md">
          <div className="flex items-center space-x-3">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
            <span>Loading workflows...</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[80vh] m-4">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">Load Workflow</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <span className="sr-only">Close</span>
            ✕
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(80vh-140px)]">
          {workflows.length === 0 ? (
            <div className="text-center py-12">
              <div className="text-gray-400 mb-4">
                <Download size={48} className="mx-auto" />
              </div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">No Workflows Found</h3>
              <p className="text-gray-600">
                You haven't saved any workflows yet. Create and save a workflow to see it here.
              </p>
            </div>
          ) : (
            <div className="grid gap-4">
              {workflows.map((workflow) => (
                <div
                  key={workflow.id}
                  className={`
                    border rounded-lg p-4 transition-all cursor-pointer
                    ${selectedWorkflow === workflow.id 
                      ? 'border-blue-500 bg-blue-50' 
                      : 'border-gray-200 hover:border-gray-300'
                    }
                  `}
                  onClick={() => setSelectedWorkflow(workflow.id)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <h3 className="text-lg font-medium text-gray-900 truncate">
                        {workflow.name}
                      </h3>
                      {workflow.description && (
                        <p className="text-sm text-gray-600 mt-1 line-clamp-2">
                          {workflow.description}
                        </p>
                      )}
                      
                      <div className="flex items-center space-x-4 mt-3 text-sm text-gray-500">
                        <div className="flex items-center space-x-1">
                          <Calendar size={14} />
                          <span>Created: {formatDate(workflow.created_at)}</span>
                        </div>
                        <div className="flex items-center space-x-1">
                          <Clock size={14} />
                          <span>Updated: {formatDate(workflow.updated_at)}</span>
                        </div>
                      </div>
                      
                      <div className="text-sm text-gray-500 mt-1">
                        {getWorkflowStats(workflow)}
                      </div>
                    </div>

                    <div className="flex items-center space-x-2 ml-4">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleLoadWorkflow(workflow);
                        }}
                        className="p-2 text-blue-600 hover:bg-blue-100 rounded-md transition-colors"
                        title="Load workflow"
                      >
                        <Edit3 size={16} />
                      </button>
                      
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDuplicateWorkflow(workflow.id, workflow.name);
                        }}
                        className="p-2 text-green-600 hover:bg-green-100 rounded-md transition-colors"
                        title="Duplicate workflow"
                      >
                        <Copy size={16} />
                      </button>
                      
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteWorkflow(workflow.id, workflow.name);
                        }}
                        className="p-2 text-red-600 hover:bg-red-100 rounded-md transition-colors"
                        title="Delete workflow"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        {workflows.length > 0 && selectedWorkflow && (
          <div className="flex items-center justify-between p-6 border-t border-gray-200 bg-gray-50">
            <div className="text-sm text-gray-600">
              Click a workflow to select it, then use the action buttons to load, duplicate, or delete.
            </div>
            <div className="flex space-x-3">
              <button
                onClick={onClose}
                className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  const workflow = workflows.find(w => w.id === selectedWorkflow);
                  if (workflow) handleLoadWorkflow(workflow);
                }}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
              >
                Load Selected
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Delete Confirmation Dialog */}
      {deleteConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-60">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
            <div className="p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Delete Workflow
              </h3>
              <p className="text-gray-600 mb-6">
                Are you sure you want to delete "{deleteConfirm.workflowName}"? This action cannot be undone.
              </p>
              <div className="flex justify-end space-x-3">
                <button
                  onClick={() => setDeleteConfirm(null)}
                  className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={confirmDelete}
                  className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors"
                >
                  Delete
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default WorkflowList;