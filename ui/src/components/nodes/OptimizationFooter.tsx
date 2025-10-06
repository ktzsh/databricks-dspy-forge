import React, { useState } from 'react';
import { Sparkles, ChevronDown, ChevronUp } from 'lucide-react';
import { OptimizationData } from '../../types/workflow';

interface OptimizationFooterProps {
  optimizationData: OptimizationData;
}

const OptimizationFooter: React.FC<OptimizationFooterProps> = ({ optimizationData }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const demosCount = optimizationData.demos?.length || 0;

  return (
    <div className="border-t border-emerald-200 bg-gradient-to-r from-emerald-50 to-emerald-100/50">
      {/* Collapsed Header - Always Visible */}
      <button
        onClick={(e) => {
          e.stopPropagation();
          setIsExpanded(!isExpanded);
        }}
        className="w-full px-3 py-2 flex items-center justify-between hover:bg-emerald-100/50 transition-colors"
        title="Click to view optimization details"
      >
        <div className="flex items-center space-x-2">
          <div className="p-1 bg-emerald-500 rounded-md shadow-sm">
            <Sparkles size={12} className="text-white" />
          </div>
          <span className="text-xs font-semibold text-emerald-900">
            Optimized
          </span>
          <span className="text-xs text-emerald-600">
            • {demosCount} demo{demosCount !== 1 ? 's' : ''}
          </span>
        </div>
        <div className="text-emerald-600">
          {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </div>
      </button>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="px-3 pb-3 space-y-3 max-h-96 overflow-y-auto">
          {/* Demos Section */}
          {optimizationData.demos && optimizationData.demos.length > 0 && (
            <div>
              <div className="text-xs font-semibold text-emerald-800 mb-1.5">
                Demos ({demosCount}):
              </div>
              <div className="bg-white rounded-lg p-2 border border-emerald-200">
                <pre className="text-xs text-slate-700 whitespace-pre-wrap font-mono overflow-x-auto">
                  {JSON.stringify(optimizationData.demos, null, 2)}
                </pre>
              </div>
            </div>
          )}

          {/* Signature Section */}
          {optimizationData.signature && (
            <div>
              <div className="text-xs font-semibold text-emerald-800 mb-1.5">
                Signature:
              </div>
              <div className="bg-white rounded-lg p-2 border border-emerald-200">
                <pre className="text-xs text-slate-700 whitespace-pre-wrap font-mono overflow-x-auto">
                  {JSON.stringify(optimizationData.signature, null, 2)}
                </pre>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default OptimizationFooter;
