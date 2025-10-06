import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Edit3, Copy, Trash2, MoreVertical, Clock, Calendar, Zap, Cloud, Hash } from 'lucide-react';
import { WorkflowCardData } from '../types/dashboard';
import { useToast } from '../hooks/useToast';

interface WorkflowCardProps {
  workflow: WorkflowCardData;
  onDelete: (workflowId: string) => void;
  onDuplicate: (workflowId: string, workflowName: string) => void;
  onShowDetails: (workflow: WorkflowCardData) => void;
}

const WorkflowCard: React.FC<WorkflowCardProps> = ({ workflow, onDelete, onDuplicate, onShowDetails }) => {
  const navigate = useNavigate();
  const { showSuccess } = useToast();
  const [showActions, setShowActions] = useState(false);

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  const getStatusBadge = (
    status: string | undefined,
    type: 'optimization' | 'deployment'
  ) => {
    if (!status) {
      return (
        <span className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-slate-700/50 text-slate-400">
          <span className="w-1.5 h-1.5 rounded-full bg-slate-500 mr-1.5"></span>
          {type === 'optimization' ? 'Not optimized' : 'Not deployed'}
        </span>
      );
    }

    const isOptimizing = ['queued', 'initializing', 'loading_data', 'building_program', 'optimizing', 'saving_results'].includes(status);
    const isDeploying = ['validating', 'compiling', 'deploying'].includes(status);
    const isCompleted = status === 'completed';
    const isFailed = status === 'failed';

    let bgColor = 'bg-slate-700/50';
    let textColor = 'text-slate-400';
    let dotColor = 'bg-slate-500';
    let label = status;

    if (isOptimizing || isDeploying) {
      bgColor = 'bg-blue-500/20';
      textColor = 'text-blue-400';
      dotColor = 'bg-blue-500';
      label = type === 'optimization' ? 'Optimizing...' : 'Deploying...';
    } else if (isCompleted) {
      bgColor = 'bg-emerald-500/20';
      textColor = 'text-emerald-400';
      dotColor = 'bg-emerald-500';
      label = type === 'optimization' ? 'Optimized' : 'Deployed';
    } else if (isFailed) {
      bgColor = 'bg-red-500/20';
      textColor = 'text-red-400';
      dotColor = 'bg-red-500';
      label = 'Failed';
    }

    return (
      <span className={`inline-flex items-center px-2 py-1 rounded-md text-xs font-medium ${bgColor} ${textColor}`}>
        <span className={`w-1.5 h-1.5 rounded-full ${dotColor} mr-1.5 ${isOptimizing || isDeploying ? 'animate-pulse' : ''}`}></span>
        {label}
      </span>
    );
  };

  const handleOpenWorkflow = () => {
    navigate(`/workflow/${workflow.id}`);
  };

  const handleDuplicate = (e: React.MouseEvent) => {
    e.stopPropagation();
    onDuplicate(workflow.id, workflow.name);
    setShowActions(false);
  };

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    onDelete(workflow.id);
    setShowActions(false);
  };

  return (
    <div
      className="bg-slate-800/50 border border-slate-700 rounded-xl shadow-sm hover:shadow-lg hover:border-slate-600 transition-all duration-200 overflow-hidden cursor-pointer group backdrop-blur-sm"
      onClick={() => onShowDetails(workflow)}
    >
      {/* Card Content */}
      <div className="p-5">
        {/* Header */}
        <div className="flex items-start justify-between mb-3">
          <div className="flex-1 min-w-0">
            <h3 className="text-lg font-semibold text-slate-100 truncate group-hover:text-brand-400 transition-colors">
              {workflow.name}
            </h3>
            {workflow.description && (
              <p className="text-sm text-slate-400 mt-1 line-clamp-2">
                {workflow.description}
              </p>
            )}
          </div>

          {/* Actions Menu */}
          <div className="relative ml-3">
            <button
              onClick={(e) => {
                e.stopPropagation();
                setShowActions(!showActions);
              }}
              className="p-1.5 rounded-md hover:bg-slate-700 transition-colors"
            >
              <MoreVertical size={18} className="text-slate-400" />
            </button>

            {showActions && (
              <>
                <div
                  className="fixed inset-0 z-10"
                  onClick={(e) => {
                    e.stopPropagation();
                    setShowActions(false);
                  }}
                />
                <div className="absolute right-0 mt-1 w-48 bg-slate-800 rounded-lg shadow-lg border border-slate-700 py-1 z-20">
                  <button
                    onClick={handleOpenWorkflow}
                    className="w-full px-4 py-2 text-left text-sm text-slate-200 hover:bg-slate-700 flex items-center"
                  >
                    <Edit3 size={14} className="mr-2" />
                    Open Workflow
                  </button>
                  <button
                    onClick={handleDuplicate}
                    className="w-full px-4 py-2 text-left text-sm text-slate-200 hover:bg-slate-700 flex items-center"
                  >
                    <Copy size={14} className="mr-2" />
                    Duplicate
                  </button>
                  <button
                    onClick={handleDelete}
                    className="w-full px-4 py-2 text-left text-sm text-red-400 hover:bg-red-500/10 flex items-center"
                  >
                    <Trash2 size={14} className="mr-2" />
                    Delete
                  </button>
                </div>
              </>
            )}
          </div>
        </div>

        {/* Status Badges */}
        <div className="flex flex-wrap gap-2 mb-4">
          <div className="flex items-center">
            <Zap size={14} className="text-slate-500 mr-1" />
            {getStatusBadge(workflow.latestOptimization?.status, 'optimization')}
          </div>
          <div className="flex items-center">
            <Cloud size={14} className="text-slate-500 mr-1" />
            {getStatusBadge(workflow.latestDeployment?.status, 'deployment')}
          </div>
        </div>

        {/* Metadata */}
        <div className="flex items-center justify-between text-xs text-slate-500">
          <div className="flex items-center space-x-4">
            <span className="flex items-center">
              <Hash size={12} className="mr-1" />
              {workflow.nodes.length} nodes
            </span>
            {workflow.optimizationCount > 0 && (
              <span className="flex items-center">
                <Zap size={12} className="mr-1" />
                {workflow.optimizationCount} run{workflow.optimizationCount !== 1 ? 's' : ''}
              </span>
            )}
            {workflow.deploymentCount > 0 && (
              <span className="flex items-center">
                <Cloud size={12} className="mr-1" />
                {workflow.deploymentCount} deploy{workflow.deploymentCount !== 1 ? 's' : ''}
              </span>
            )}
          </div>
        </div>

        {/* Timestamps */}
        <div className="mt-3 pt-3 border-t border-slate-700 flex items-center justify-between text-xs text-slate-500">
          <div className="flex items-center">
            <Calendar size={12} className="mr-1" />
            Created {formatDate(workflow.createdAt)}
          </div>
          <div className="flex items-center">
            <Clock size={12} className="mr-1" />
            Updated {formatDate(workflow.updatedAt)}
          </div>
        </div>
      </div>

      {/* Quick Action Button */}
      <div className="bg-slate-700/30 px-5 py-3 border-t border-slate-700 group-hover:bg-brand-500/10 transition-colors">
        <button
          onClick={(e) => {
            e.stopPropagation();
            handleOpenWorkflow();
          }}
          className="w-full text-sm font-medium text-slate-300 group-hover:text-brand-400 flex items-center transition-colors"
        >
          <Edit3 size={14} className="mr-1.5" />
          Open Workflow
          <span className="ml-auto text-slate-500 group-hover:text-brand-400">→</span>
        </button>
      </div>
    </div>
  );
};

export default WorkflowCard;
