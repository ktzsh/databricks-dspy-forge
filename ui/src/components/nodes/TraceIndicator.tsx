import React from 'react';
import { Activity } from 'lucide-react';

interface TraceIndicatorProps {
  hasTrace: boolean;
  executionTime?: number;
  onClick: (e: React.MouseEvent) => void;
}

const TraceIndicator: React.FC<TraceIndicatorProps> = ({
  hasTrace,
  executionTime,
  onClick
}) => {
  if (!hasTrace) return null;

  return (
    <button
      onClick={(e) => {
        e.stopPropagation();
        onClick(e);
      }}
      className="absolute -top-2 -right-2 w-6 h-6 bg-blue-500 hover:bg-blue-600 text-white rounded-full flex items-center justify-center shadow-md transition-colors duration-200 z-10"
      title={`View trace${executionTime ? ` (${executionTime.toFixed(3)}s)` : ''}`}
    >
      <Activity size={12} />
    </button>
  );
};

export default TraceIndicator;