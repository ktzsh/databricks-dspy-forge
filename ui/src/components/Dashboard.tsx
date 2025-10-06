import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Search, Loader } from 'lucide-react';
import WorkflowCard from './WorkflowCard';
import WorkflowDetailsModal from './WorkflowDetailsModal';
import ToastContainer from './ToastContainer';
import { useWorkflowData } from '../hooks/useWorkflowData';
import { WorkflowCardData } from '../types/dashboard';
import { useToast } from '../hooks/useToast';

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const { workflows, loading, refreshWorkflows } = useWorkflowData();
  const { toasts, removeToast, showSuccess, showError } = useToast();

  const [searchQuery, setSearchQuery] = useState('');
  const [filterStatus, setFilterStatus] = useState<'all' | 'optimized' | 'deployed' | 'none'>('all');
  const [selectedWorkflow, setSelectedWorkflow] = useState<WorkflowCardData | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<{ id: string; name: string } | null>(null);

  // Filter workflows based on search and filter
  const filteredWorkflows = workflows.filter(workflow => {
    // Search filter
    const matchesSearch = workflow.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         workflow.description?.toLowerCase().includes(searchQuery.toLowerCase());

    if (!matchesSearch) return false;

    // Status filter
    if (filterStatus === 'all') return true;
    if (filterStatus === 'optimized') return workflow.latestOptimization?.status === 'completed';
    if (filterStatus === 'deployed') return workflow.latestDeployment?.status === 'completed';
    if (filterStatus === 'none') return !workflow.latestOptimization && !workflow.latestDeployment;

    return true;
  });

  const handleCreateWorkflow = () => {
    navigate('/workflow/new');
  };

  const handleDeleteWorkflow = async (workflowId: string) => {
    const workflow = workflows.find(w => w.id === workflowId);
    if (!workflow) return;

    setDeleteConfirm({ id: workflowId, name: workflow.name });
  };

  const confirmDelete = async () => {
    if (!deleteConfirm) return;

    try {
      const response = await fetch(`/api/v1/workflows/${deleteConfirm.id}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        showSuccess('Workflow Deleted', `"${deleteConfirm.name}" has been deleted`);
        refreshWorkflows();
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
        showSuccess('Workflow Duplicated', `Copy of "${workflowName}" has been created`);
        refreshWorkflows();
      } else {
        showError('Duplicate Failed', 'Could not duplicate workflow');
      }
    } catch (error) {
      showError('Network Error', 'Unable to duplicate workflow');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      <ToastContainer toasts={toasts} onRemove={removeToast} />

      {/* Hero Section */}
      <div className="max-w-5xl mx-auto px-6 pt-20 pb-12">
        <div className="text-center mb-12">
          <div className="flex items-center justify-center space-x-3 mb-4">
            <div className="w-12 h-12 bg-gradient-to-br from-brand-600 to-brand-700 rounded-xl flex items-center justify-center shadow-brand">
              <span className="text-white font-bold text-lg">DF</span>
            </div>
            <h1 className="text-4xl font-bold text-white">
              DSPy Forge
            </h1>
          </div>
          <p className="text-slate-300 text-lg">Build • Optimize • Deploy</p>
        </div>

        {/* Search Bar */}
        <div className="max-w-2xl mx-auto mb-12">
          <div className="relative">
            <Search size={20} className="absolute left-4 top-1/2 transform -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search workflows..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-12 pr-4 py-3 bg-slate-800/50 border border-slate-700 rounded-xl text-white placeholder-slate-400 focus:ring-2 focus:ring-brand-500 focus:border-transparent transition-all"
            />
            <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value as any)}
                className="pl-3 pr-8 py-1.5 bg-slate-700 border border-slate-600 rounded-lg text-slate-200 text-sm focus:ring-2 focus:ring-brand-500 focus:border-transparent appearance-none cursor-pointer"
              >
                <option value="all">All</option>
                <option value="optimized">Optimized</option>
                <option value="deployed">Deployed</option>
                <option value="none">Unprocessed</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Workflows Section */}
      <div className="max-w-7xl mx-auto px-6 pb-12">

        {loading ? (
          <div className="flex items-center justify-center py-24">
            <Loader size={48} className="text-brand-500 animate-spin" />
          </div>
        ) : (
          <>
            {/* Workflow Cards Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {/* New Workflow Card - Always First */}
              <div
                onClick={handleCreateWorkflow}
                className="bg-gradient-to-br from-brand-600/10 to-brand-700/10 border-2 border-dashed border-brand-600/30 rounded-xl p-8 flex flex-col items-center justify-center cursor-pointer hover:border-brand-500/50 hover:bg-brand-600/20 transition-all duration-200 group"
              >
                <div className="w-16 h-16 bg-brand-600/20 rounded-full flex items-center justify-center mb-4 group-hover:bg-brand-600/30 transition-colors">
                  <Plus size={32} className="text-brand-500 group-hover:text-brand-400" />
                </div>
                <h3 className="text-lg font-semibold text-slate-200 mb-2">Create New Workflow</h3>
                <p className="text-sm text-slate-400 text-center">
                  Start building your AI workflow
                </p>
              </div>

              {/* Existing Workflows */}
              {filteredWorkflows.map(workflow => (
                <WorkflowCard
                  key={workflow.id}
                  workflow={workflow}
                  onDelete={handleDeleteWorkflow}
                  onDuplicate={handleDuplicateWorkflow}
                  onShowDetails={setSelectedWorkflow}
                />
              ))}
            </div>

            {/* Empty State for Search */}
            {filteredWorkflows.length === 0 && workflows.length > 0 && (
              <div className="text-center py-16">
                <Search size={64} className="mx-auto text-slate-600 mb-6" />
                <h3 className="text-xl font-semibold text-slate-300 mb-2">No Workflows Found</h3>
                <p className="text-slate-400 mb-6">
                  No workflows match your search criteria. Try adjusting your search or filters.
                </p>
                <button
                  onClick={() => {
                    setSearchQuery('');
                    setFilterStatus('all');
                  }}
                  className="text-brand-400 hover:text-brand-300 font-medium"
                >
                  Clear Filters
                </button>
              </div>
            )}
          </>
        )}
      </div>

      {/* Workflow Details Modal */}
      {selectedWorkflow && (
        <WorkflowDetailsModal
          workflow={selectedWorkflow}
          onClose={() => setSelectedWorkflow(null)}
        />
      )}

      {/* Delete Confirmation Dialog */}
      {deleteConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center z-50 backdrop-blur-sm">
          <div className="bg-slate-800 border border-slate-700 rounded-lg shadow-xl max-w-md w-full mx-4">
            <div className="p-6">
              <h3 className="text-lg font-semibold text-slate-100 mb-2">
                Delete Workflow
              </h3>
              <p className="text-slate-400 mb-6">
                Are you sure you want to delete "{deleteConfirm.name}"? This action cannot be undone.
              </p>
              <div className="flex justify-end space-x-3">
                <button
                  onClick={() => setDeleteConfirm(null)}
                  className="px-4 py-2 text-slate-300 bg-slate-700 border border-slate-600 rounded-md hover:bg-slate-600 transition-colors"
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

export default Dashboard;
