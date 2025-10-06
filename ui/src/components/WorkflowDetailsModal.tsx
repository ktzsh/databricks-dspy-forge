import React, { useState, useEffect } from 'react';
import { X, Zap, Cloud, Calendar, Clock, ExternalLink, FileText, Hash, CheckCircle, XCircle, Loader } from 'lucide-react';
import { WorkflowCardData, WorkflowHistory } from '../types/dashboard';

interface WorkflowDetailsModalProps {
  workflow: WorkflowCardData;
  onClose: () => void;
}

const WorkflowDetailsModal: React.FC<WorkflowDetailsModalProps> = ({ workflow, onClose }) => {
  const [activeTab, setActiveTab] = useState<'overview' | 'optimizations' | 'deployments'>('overview');
  const [history, setHistory] = useState<WorkflowHistory | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        setLoading(true);
        const response = await fetch(`/api/v1/workflows/${workflow.id}/history`);
        if (response.ok) {
          const data = await response.json();
          setHistory(data);
        }
      } catch (error) {
        console.error('Failed to fetch workflow history:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchHistory();
  }, [workflow.id]);

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  const formatDuration = (startAt: string, completedAt?: string) => {
    if (!completedAt) return 'In progress...';

    const start = new Date(startAt).getTime();
    const end = new Date(completedAt).getTime();
    const durationMs = end - start;
    const seconds = Math.floor(durationMs / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);

    if (hours > 0) return `${hours}h ${minutes % 60}m`;
    if (minutes > 0) return `${minutes}m ${seconds % 60}s`;
    return `${seconds}s`;
  };

  const getStatusIcon = (status: string) => {
    if (status === 'completed') {
      return <CheckCircle size={16} className="text-emerald-500" />;
    } else if (status === 'failed') {
      return <XCircle size={16} className="text-red-500" />;
    } else {
      return <Loader size={16} className="text-blue-500 animate-spin" />;
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
      <div className="bg-slate-800 border border-slate-700 rounded-xl shadow-2xl max-w-4xl w-full max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-slate-700">
          <div>
            <h2 className="text-2xl font-bold text-slate-100">{workflow.name}</h2>
            {workflow.description && (
              <p className="text-sm text-slate-400 mt-1">{workflow.description}</p>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
          >
            <X size={24} className="text-slate-400" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-slate-700 px-6">
          <button
            onClick={() => setActiveTab('overview')}
            className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'overview'
                ? 'border-brand-500 text-brand-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            Overview
          </button>
          <button
            onClick={() => setActiveTab('optimizations')}
            className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors flex items-center ${
              activeTab === 'optimizations'
                ? 'border-brand-500 text-brand-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Zap size={16} className="mr-1.5" />
            Optimizations ({workflow.optimizationCount})
          </button>
          <button
            onClick={() => setActiveTab('deployments')}
            className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors flex items-center ${
              activeTab === 'deployments'
                ? 'border-brand-500 text-brand-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Cloud size={16} className="mr-1.5" />
            Deployments ({workflow.deploymentCount})
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader size={32} className="text-orange-500 animate-spin" />
            </div>
          ) : (
            <>
              {/* Overview Tab */}
              {activeTab === 'overview' && (
                <div className="space-y-6">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="bg-slate-700/30 rounded-lg p-4 border border-slate-700">
                      <div className="flex items-center text-sm text-slate-400 mb-1">
                        <Hash size={14} className="mr-1" />
                        Nodes
                      </div>
                      <div className="text-2xl font-bold text-slate-100">{workflow.nodes.length}</div>
                    </div>
                    <div className="bg-slate-700/30 rounded-lg p-4 border border-slate-700">
                      <div className="flex items-center text-sm text-slate-400 mb-1">
                        <FileText size={14} className="mr-1" />
                        Connections
                      </div>
                      <div className="text-2xl font-bold text-slate-100">{workflow.edges.length}</div>
                    </div>
                    <div className="bg-slate-700/30 rounded-lg p-4 border border-slate-700">
                      <div className="flex items-center text-sm text-slate-400 mb-1">
                        <Zap size={14} className="mr-1" />
                        Optimizations
                      </div>
                      <div className="text-2xl font-bold text-slate-100">{workflow.optimizationCount}</div>
                    </div>
                    <div className="bg-slate-700/30 rounded-lg p-4 border border-slate-700">
                      <div className="flex items-center text-sm text-slate-400 mb-1">
                        <Cloud size={14} className="mr-1" />
                        Deployments
                      </div>
                      <div className="text-2xl font-bold text-slate-100">{workflow.deploymentCount}</div>
                    </div>
                  </div>

                  <div className="space-y-3">
                    <div className="flex items-center text-sm">
                      <Calendar size={14} className="text-slate-500 mr-2" />
                      <span className="text-slate-400">Created:</span>
                      <span className="ml-2 font-medium text-slate-200">{formatDate(workflow.createdAt)}</span>
                    </div>
                    <div className="flex items-center text-sm">
                      <Clock size={14} className="text-slate-500 mr-2" />
                      <span className="text-slate-400">Last Updated:</span>
                      <span className="ml-2 font-medium text-slate-200">{formatDate(workflow.updatedAt)}</span>
                    </div>
                  </div>

                  {workflow.latestOptimization && (
                    <div className="border border-emerald-500/30 bg-emerald-500/10 rounded-lg p-4">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-semibold text-emerald-400">Latest Optimization</span>
                        {getStatusIcon(workflow.latestOptimization.status)}
                      </div>
                      <p className="text-sm text-emerald-300">
                        {workflow.latestOptimization.optimizer_name} - {workflow.latestOptimization.message}
                      </p>
                    </div>
                  )}

                  {workflow.latestDeployment && (
                    <div className="border border-blue-500/30 bg-blue-500/10 rounded-lg p-4">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-semibold text-blue-400">Latest Deployment</span>
                        {getStatusIcon(workflow.latestDeployment.status)}
                      </div>
                      <p className="text-sm text-blue-300">
                        {workflow.latestDeployment.catalog_name}.{workflow.latestDeployment.schema_name}.{workflow.latestDeployment.model_name}
                      </p>
                      {workflow.latestDeployment.endpoint_url && (
                        <a
                          href={workflow.latestDeployment.endpoint_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-blue-400 hover:text-blue-300 flex items-center mt-1"
                        >
                          View Endpoint <ExternalLink size={12} className="ml-1" />
                        </a>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* Optimizations Tab */}
              {activeTab === 'optimizations' && (
                <div className="space-y-3">
                  {history?.optimizations && history.optimizations.length > 0 ? (
                    history.optimizations.map((opt, index) => (
                      <div key={opt.optimization_id} className="border border-slate-700 rounded-lg p-4 bg-slate-700/20 hover:border-slate-600 transition-colors">
                        <div className="flex items-start justify-between mb-2">
                          <div>
                            <div className="flex items-center space-x-2">
                              {getStatusIcon(opt.status)}
                              <span className="font-semibold text-slate-200">
                                {opt.optimizer_name}
                              </span>
                              {index === 0 && (
                                <span className="px-2 py-0.5 bg-brand-500/20 text-brand-400 text-xs font-medium rounded">
                                  Latest
                                </span>
                              )}
                            </div>
                            <p className="text-sm text-slate-400 mt-1">{opt.message}</p>
                          </div>
                          <span className="text-xs text-slate-500 whitespace-nowrap ml-4">
                            {formatDuration(opt.started_at, opt.completed_at)}
                          </span>
                        </div>
                        <div className="flex items-center justify-between text-xs text-slate-500 mt-3 pt-3 border-t border-slate-700">
                          <span>Started: {formatDate(opt.started_at)}</span>
                          {opt.completed_at && <span>Completed: {formatDate(opt.completed_at)}</span>}
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="text-center py-12">
                      <Zap size={48} className="mx-auto text-slate-600 mb-4" />
                      <p className="text-slate-400">No optimization runs yet</p>
                      <p className="text-sm text-slate-500 mt-1">Optimize this workflow to improve its performance</p>
                    </div>
                  )}
                </div>
              )}

              {/* Deployments Tab */}
              {activeTab === 'deployments' && (
                <div className="space-y-3">
                  {history?.deployments && history.deployments.length > 0 ? (
                    history.deployments.map((dep, index) => (
                      <div key={dep.deployment_id} className="border border-slate-700 rounded-lg p-4 bg-slate-700/20 hover:border-slate-600 transition-colors">
                        <div className="flex items-start justify-between mb-2">
                          <div>
                            <div className="flex items-center space-x-2">
                              {getStatusIcon(dep.status)}
                              <span className="font-semibold text-slate-200">
                                {dep.model_name}
                              </span>
                              {index === 0 && (
                                <span className="px-2 py-0.5 bg-brand-500/20 text-brand-400 text-xs font-medium rounded">
                                  Latest
                                </span>
                              )}
                            </div>
                            <p className="text-sm text-slate-400 mt-1">
                              {dep.catalog_name}.{dep.schema_name}.{dep.model_name}
                            </p>
                            <p className="text-sm text-slate-500 mt-1">{dep.message}</p>
                          </div>
                          <span className="text-xs text-slate-500 whitespace-nowrap ml-4">
                            {formatDuration(dep.started_at, dep.completed_at)}
                          </span>
                        </div>
                        {(dep.endpoint_url || dep.review_app_url) && (
                          <div className="flex items-center space-x-3 mt-3 pt-3 border-t border-slate-700">
                            {dep.endpoint_url && (
                              <a
                                href={dep.endpoint_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-xs text-blue-600 hover:text-blue-800 flex items-center"
                              >
                                View Endpoint <ExternalLink size={12} className="ml-1" />
                              </a>
                            )}
                            {dep.review_app_url && (
                              <a
                                href={dep.review_app_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-xs text-blue-600 hover:text-blue-800 flex items-center"
                              >
                                Review App <ExternalLink size={12} className="ml-1" />
                              </a>
                            )}
                          </div>
                        )}
                        <div className="text-xs text-slate-500 mt-2">
                          Started: {formatDate(dep.started_at)}
                          {dep.completed_at && ` • Completed: ${formatDate(dep.completed_at)}`}
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="text-center py-12">
                      <Cloud size={48} className="mx-auto text-slate-600 mb-4" />
                      <p className="text-slate-400">No deployments yet</p>
                      <p className="text-sm text-slate-500 mt-1">Deploy this workflow to make it accessible</p>
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end px-6 py-4 border-t border-slate-700 bg-slate-900/50">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-slate-300 bg-slate-700 border border-slate-600 rounded-md hover:bg-slate-600 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default WorkflowDetailsModal;
