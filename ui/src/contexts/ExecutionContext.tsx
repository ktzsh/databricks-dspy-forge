import React, { createContext, useContext } from 'react';

interface ExecutionData {
  hasTrace: boolean;
  executionTime?: number;
  onTraceClick?: () => void;
}

interface ExecutionContextType {
  getExecutionDataForNode: (nodeId: string) => ExecutionData;
}

const ExecutionContext = createContext<ExecutionContextType | null>(null);

export const ExecutionProvider: React.FC<{
  children: React.ReactNode;
  getExecutionDataForNode: (nodeId: string) => ExecutionData;
}> = ({ children, getExecutionDataForNode }) => {
  return (
    <ExecutionContext.Provider value={{ getExecutionDataForNode }}>
      {children}
    </ExecutionContext.Provider>
  );
};

export const useExecution = () => {
  const context = useContext(ExecutionContext);
  if (!context) {
    return { getExecutionDataForNode: () => ({ hasTrace: false }) };
  }
  return context;
};