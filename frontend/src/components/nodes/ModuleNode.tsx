import React, { useState } from 'react';
import { Handle, Position, NodeProps, useReactFlow } from 'reactflow';
import { Edit3, Brain, Settings, Trash2 } from 'lucide-react';
import { ModuleNodeData, ModuleType } from '../../types/workflow';

const moduleTypes: ModuleType[] = [
  'Predict',
  'ChainOfThought',
  'ReAct',
  'Retrieve',
  'BestOfN',
  'Refine'
];

const moduleIcons: Record<ModuleType, React.ReactNode> = {
  'Predict': <Brain size={16} className="text-green-600" />,
  'ChainOfThought': <Brain size={16} className="text-blue-600" />,
  'ReAct': <Brain size={16} className="text-purple-600" />,
  'Retrieve': <Brain size={16} className="text-orange-600" />,
  'BestOfN': <Brain size={16} className="text-red-600" />,
  'Refine': <Brain size={16} className="text-indigo-600" />
};

const ModuleNode: React.FC<NodeProps<ModuleNodeData>> = ({ data, selected, id }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [moduleType, setModuleType] = useState<ModuleType>(data.moduleType || 'Predict');
  const [model, setModel] = useState(data.model || '');
  const [instruction, setInstruction] = useState(data.instruction || '');
  const [parameters, setParameters] = useState(data.parameters || {});
  const { deleteElements } = useReactFlow();

  const handleSave = () => {
    data.moduleType = moduleType;
    data.model = model;
    data.instruction = instruction;
    data.parameters = parameters;
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

  return (
    <div className={`module-node min-w-[250px] ${selected ? 'node-selected' : ''}`}>
      {/* Handles */}
      <Handle
        type="target"
        position={Position.Left}
        className="w-3 h-3 bg-green-500"
      />
      <Handle
        type="source"
        position={Position.Right}
        className="w-3 h-3 bg-green-500"
      />

      {/* Header */}
      <div className="flex items-center justify-between p-3 bg-green-100 border-b border-green-200">
        <div className="flex items-center space-x-2">
          {moduleIcons[moduleType] || <Brain size={16} className="text-green-600" />}
          <span className="font-medium text-green-800">{moduleType}</span>
        </div>
        <div className="flex items-center space-x-1">
          <button
            onClick={() => setIsEditing(!isEditing)}
            className="p-1 hover:bg-green-200 rounded"
            title="Edit node"
          >
            <Edit3 size={14} className="text-green-600" />
          </button>
          <button
            onClick={handleDelete}
            className="p-1 hover:bg-red-200 rounded"
            title="Delete node"
          >
            <Trash2 size={14} className="text-red-600" />
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="p-3">
        {isEditing ? (
          <div className="space-y-3">
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
              <label className="block text-sm font-medium mb-1">Model</label>
              <input
                type="text"
                value={model}
                onChange={(e) => setModel(e.target.value)}
                placeholder="e.g., gpt-3.5-turbo, claude-3"
                className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
              />
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

            <button
              onClick={handleSave}
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

            {!model && !instruction && Object.keys(parameters).length === 0 && (
              <div className="text-sm text-gray-500 text-center py-2">
                No configuration
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default ModuleNode;