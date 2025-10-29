import React, { useState } from 'react';
import { Handle, Position, NodeProps, useReactFlow } from 'reactflow';
import { Edit3, Brain, Settings, Trash2, Sparkles } from 'lucide-react';
import { ModuleNodeData, ModuleType } from '../../types/workflow';
import TraceIndicator from './TraceIndicator';
import OptimizationFooter from './OptimizationFooter';
import { useGlobalConfig } from '../../contexts/GlobalConfigContext';

const moduleTypes: ModuleType[] = [
  'Predict',
  'ChainOfThought',
  'ReAct',
  'BestOfN',
  'Refine'
];

const moduleIcons: Record<ModuleType, React.ReactNode> = {
  'Predict': <Brain size={16} className="text-green-600" />,
  'ChainOfThought': <Brain size={16} className="text-blue-600" />,
  'ReAct': <Brain size={16} className="text-purple-600" />,
  'BestOfN': <Brain size={16} className="text-red-600" />,
  'Refine': <Brain size={16} className="text-indigo-600" />
};

const ModuleNode: React.FC<NodeProps<ModuleNodeData & { traceData?: any; onTraceClick?: (nodeId: string, traceData: any) => void }>> = ({ data, selected, id }) => {
  const { traceData, onTraceClick, ...nodeData } = data;
  const [isEditing, setIsEditing] = useState(false);
  const [nodeLabel, setNodeLabel] = useState(nodeData.label || nodeData.moduleType || 'Module');
  const [moduleType, setModuleType] = useState<ModuleType>(nodeData.moduleType || 'Predict');
  const [model, setModel] = useState(nodeData.model || '');
  const [instruction, setInstruction] = useState(nodeData.instruction || '');
  const [parameters, setParameters] = useState(nodeData.parameters || {});
  const [useGlobalMCPServers, setUseGlobalMCPServers] = useState(nodeData.useGlobalMCPServers || false);
  const [useGlobalUCFunctions, setUseGlobalUCFunctions] = useState(nodeData.useGlobalUCFunctions || false);
  const { deleteElements, setNodes } = useReactFlow();
  const { globalLMConfig } = useGlobalConfig();

  const handleSave = () => {
    // Update the node data immutably using setNodes to ensure React Flow detects the change
    setNodes((nds) =>
      nds.map((node) =>
        node.id === id
          ? {
              ...node,
              data: {
                ...node.data,
                label: nodeLabel,
                moduleType: moduleType,
                model: model,
                instruction: instruction,
                parameters: parameters,
                useGlobalMCPServers: useGlobalMCPServers,
                useGlobalUCFunctions: useGlobalUCFunctions,
              }
            }
          : node
      )
    );
    setIsEditing(false);
  };

  const handleDelete = () => {
    deleteElements({ nodes: [{ id }] });
  };

  const updateParameter = (key: string, value: any) => {
    setParameters(prev => ({ ...prev, [key]: value }));
  };

  const removeParameter = (key: string) => {
    const newParams = { ...parameters };
    delete newParams[key];
    setParameters(newParams);
  };

  const addParameter = () => {
    const key = `param_${Object.keys(parameters).length + 1}`;
    updateParameter(key, '');
  };

  const applyGlobalConfig = () => {
    if (globalLMConfig) {
      setModel(globalLMConfig.modelName);
    }
  };

  // Check if this is a ReAct module to show tool handle
  const isReActModule = moduleType === 'ReAct';

  return (
    <div className={`min-w-[280px] relative bg-white rounded-xl border-2 transition-all duration-200 shadow-soft-lg ${
      selected ? 'border-emerald-400 shadow-xl ring-2 ring-emerald-200' : 'border-emerald-200 hover:border-emerald-300'
    }`}>
      {/* Handles */}
      <Handle
        type="target"
        position={Position.Top}
        className="w-3 h-3 bg-emerald-500 border-2 border-white shadow-soft"
      />

      {/* Special handle for tools (left side) - only for ReAct */}
      {isReActModule && (
        <Handle
          type="target"
          position={Position.Left}
          id="tools"
          className="w-3 h-3 bg-purple-500 border-2 border-white shadow-soft"
          style={{ top: '50%' }}
        />
      )}

      <Handle
        type="source"
        position={Position.Bottom}
        className="w-3 h-3 bg-emerald-500 border-2 border-white shadow-soft"
      />

      {/* Header */}
      <div className="flex items-center justify-between p-3.5 bg-gradient-to-r from-emerald-50 to-emerald-100/50 border-b border-emerald-200 rounded-t-xl">
        <div className="flex flex-col flex-1 min-w-0">
          <div className="flex items-center space-x-2">
            <div className="p-1.5 bg-white rounded-lg shadow-sm">
              {moduleIcons[moduleType] || <Brain size={16} className="text-emerald-600" />}
            </div>
            <span className="font-semibold text-emerald-900 truncate">{nodeLabel}</span>
          </div>
          <div className="text-xs text-emerald-600 font-medium mt-1.5">{moduleType}</div>
          <div className="text-xs text-slate-500 font-mono">{id}</div>
        </div>
        <div className="flex items-center space-x-1 ml-2">
          <button
            onClick={(e) => {
              e.stopPropagation();
              setIsEditing(!isEditing);
            }}
            className="p-1.5 hover:bg-emerald-200/50 rounded-lg transition-colors"
            title="Edit node"
          >
            <Edit3 size={14} className="text-emerald-700" />
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              handleDelete();
            }}
            className="p-1.5 hover:bg-coral-100 rounded-lg transition-colors"
            title="Delete node"
          >
            <Trash2 size={14} className="text-coral-600" />
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="p-3">
        {isEditing ? (
          <div className="space-y-3">
            {/* Node Name */}
            <div>
              <label className="block text-sm font-medium mb-1">Node Name</label>
              <input
                type="text"
                value={nodeLabel}
                onChange={(e) => setNodeLabel(e.target.value)}
                placeholder="Enter node name"
                className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
              />
            </div>
            
            {/* Module Type Selection */}
            <div>
              <label className="block text-sm font-medium mb-1">Module Type</label>
              <select
                value={moduleType}
                onChange={(e) => setModuleType(e.target.value as ModuleType)}
                className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
              >
                {moduleTypes.map(type => (
                  <option key={type} value={type}>{type}</option>
                ))}
              </select>
            </div>

            {/* Model Selection */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="block text-sm font-medium">Model</label>
                {globalLMConfig && (
                  <button
                    onClick={applyGlobalConfig}
                    className="flex items-center space-x-1 px-2 py-0.5 text-xs bg-emerald-50 text-emerald-700 rounded hover:bg-emerald-100 transition-colors"
                    type="button"
                  >
                    <Sparkles size={12} />
                    <span>Use Global</span>
                  </button>
                )}
              </div>
              <input
                type="text"
                value={model}
                onChange={(e) => setModel(e.target.value)}
                placeholder="e.g., databricks/databricks-claude-sonnet-4-5"
                className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
              />
              <div className="text-xs text-gray-500 mt-1">
                Format: provider/model-name (openai/gpt-4, databricks/claude-sonnet)
              </div>
              {globalLMConfig && (
                <div className="text-xs text-emerald-600 mt-1">
                  Global: {globalLMConfig.modelName}
                </div>
              )}
            </div>

            {/* Instruction */}
            <div>
              <label className="block text-sm font-medium mb-1">
                Instruction <span className="text-red-500">*</span>
              </label>
              <textarea
                value={instruction}
                onChange={(e) => setInstruction(e.target.value)}
                placeholder="Describe the task this module should perform..."
                className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
                rows={3}
                required
              />
              <div className="text-xs text-gray-500 mt-1">
                This will be used as the instruction for the DSPy signature
              </div>
            </div>

            {/* Parameters */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-sm font-medium">Parameters</label>
                <button
                  onClick={addParameter}
                  className="px-2 py-1 bg-green-500 text-white rounded text-xs hover:bg-green-600"
                >
                  Add
                </button>
              </div>
              
              <div className="space-y-2 max-h-32 overflow-y-auto">
                {Object.entries(parameters).map(([key, value]) => (
                  <div key={key} className="flex items-center space-x-2">
                    <input
                      type="text"
                      value={key}
                      onChange={(e) => {
                        const newKey = e.target.value;
                        const newParams = { ...parameters };
                        delete newParams[key];
                        newParams[newKey] = value;
                        setParameters(newParams);
                      }}
                      placeholder="Parameter name"
                      className="flex-1 px-2 py-1 border border-gray-300 rounded text-sm"
                    />
                    <input
                      type="text"
                      value={value as string}
                      onChange={(e) => updateParameter(key, e.target.value)}
                      placeholder="Value"
                      className="flex-1 px-2 py-1 border border-gray-300 rounded text-sm"
                    />
                    <button
                      onClick={() => removeParameter(key)}
                      className="p-1 text-red-500 hover:bg-red-50 rounded"
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
            </div>

            {/* Global Tools Configuration - Only for ReAct modules */}
            {moduleType === 'ReAct' && (
              <div className="border-t border-gray-200 pt-3 space-y-3">
                <div className="text-sm font-medium text-gray-700 mb-2">Global Tools</div>
                
                {/* Use Global MCP Servers */}
                <label className="flex items-start space-x-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={useGlobalMCPServers}
                    onChange={(e) => setUseGlobalMCPServers(e.target.checked)}
                    className="mt-0.5 rounded border-gray-300 text-purple-600 focus:ring-purple-500"
                  />
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-gray-900">Use Global MCP Servers</span>
                    </div>
                    <p className="text-xs text-gray-500 mt-0.5">
                      Load tools from MCP servers configured in Global Configuration
                    </p>
                  </div>
                </label>

                {/* Use Global UC Functions */}
                <label className="flex items-start space-x-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={useGlobalUCFunctions}
                    onChange={(e) => setUseGlobalUCFunctions(e.target.checked)}
                    className="mt-0.5 rounded border-gray-300 text-green-600 focus:ring-green-500"
                  />
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-gray-900">Use Global UC Functions</span>
                    </div>
                    <p className="text-xs text-gray-500 mt-0.5">
                      Load functions from UC schemas configured in Global Configuration
                    </p>
                  </div>
                </label>
              </div>
            )}

            <button
              onClick={(e) => {
                e.stopPropagation();
                handleSave();
              }}
              className="w-full px-3 py-2 bg-green-600 text-white rounded hover:bg-green-700"
            >
              Save
            </button>
          </div>
        ) : (
          <div className="space-y-2">
            {/* Model Display */}
            {model && (
              <div className="text-sm">
                <span className="font-medium">Model:</span>
                <span className="ml-2 text-gray-600">{model}</span>
              </div>
            )}

            {/* Instruction Display */}
            {instruction && (
              <div className="text-sm">
                <span className="font-medium">Instruction:</span>
                <div className="mt-1 p-2 bg-gray-50 rounded text-xs">
                  {instruction}
                </div>
              </div>
            )}

            {/* Parameters Display */}
            {Object.keys(parameters).length > 0 && (
              <div className="text-sm">
                <div className="font-medium mb-1 flex items-center">
                  <Settings size={12} className="mr-1" />
                  Parameters
                </div>
                <div className="space-y-1 max-h-20 overflow-y-auto">
                  {Object.entries(parameters).map(([key, value]) => (
                    <div key={key} className="flex justify-between">
                      <span className="text-gray-600">{key}:</span>
                      <span className="font-mono text-xs">{String(value)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Global Tools Display - Only for ReAct modules */}
            {moduleType === 'ReAct' && (useGlobalMCPServers || useGlobalUCFunctions) && (
              <div className="text-sm">
                <div className="font-medium mb-1">Global Tools</div>
                <div className="space-y-1">
                  {useGlobalMCPServers && (
                    <div className="flex items-center text-xs text-purple-600">
                      <span className="mr-1">✓</span>
                      <span>Using Global MCP Servers</span>
                    </div>
                  )}
                  {useGlobalUCFunctions && (
                    <div className="flex items-center text-xs text-green-600">
                      <span className="mr-1">✓</span>
                      <span>Using Global UC Functions</span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {!model && !instruction && Object.keys(parameters).length === 0 && !useGlobalMCPServers && !useGlobalUCFunctions && (
              <div className="text-sm text-gray-500 text-center py-2">
                No configuration
              </div>
            )}
          </div>
        )}
      </div>

      {/* Optimization Footer */}
      {nodeData.optimization_data && (
        <OptimizationFooter optimizationData={nodeData.optimization_data} />
      )}

      {/* Trace Indicator */}
      {traceData && (
        <TraceIndicator
          hasTrace={true}
          executionTime={traceData.execution_time}
          onClick={(e) => {
            e.stopPropagation();
            onTraceClick?.(id, traceData);
          }}
        />
      )}
    </div>
  );
};

export default ModuleNode;