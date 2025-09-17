import React, { useState } from 'react';
import { Handle, Position, NodeProps, useReactFlow } from 'reactflow';
import { Edit3, GitBranch, GitMerge, Trash2 } from 'lucide-react';
import { LogicNodeData, LogicType } from '../../types/workflow';

const logicTypes: LogicType[] = ['IfElse', 'Merge'];

const logicIcons: Record<LogicType, React.ReactNode> = {
  'IfElse': <GitBranch size={16} className="text-purple-600" />,
  'Merge': <GitMerge size={16} className="text-purple-600" />
};

const LogicNode: React.FC<NodeProps<LogicNodeData>> = ({ data, selected, id }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [logicType, setLogicType] = useState<LogicType>(data.logicType || 'IfElse');
  const [condition, setCondition] = useState(data.condition || '');
  const [parameters, setParameters] = useState(data.parameters || {});
  const { deleteElements } = useReactFlow();

  const handleSave = () => {
    data.logicType = logicType;
    data.condition = condition;
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
    <div className={`logic-node min-w-[250px] ${selected ? 'node-selected' : ''}`}>
      {/* Handles */}
      <Handle
        type="target"
        position={Position.Left}
        className="w-3 h-3 bg-purple-500"
      />
      
      {/* Multiple output handles for branching logic */}
      {logicType === 'IfElse' ? (
        <>
          <Handle
            type="source"
            position={Position.Right}
            id="true"
            style={{ top: '30%' }}
            className="w-3 h-3 bg-green-500"
          />
          <Handle
            type="source"
            position={Position.Right}
            id="false"
            style={{ top: '70%' }}
            className="w-3 h-3 bg-red-500"
          />
        </>
      ) : (
        <Handle
          type="source"
          position={Position.Right}
          className="w-3 h-3 bg-purple-500"
        />
      )}

      {/* Header */}
      <div className="flex items-center justify-between p-3 bg-purple-100 border-b border-purple-200">
        <div className="flex items-center space-x-2">
          {logicIcons[logicType] || <GitBranch size={16} className="text-purple-600" />}
          <span className="font-medium text-purple-800">{logicType}</span>
        </div>
        <div className="flex items-center space-x-1">
          <button
            onClick={() => setIsEditing(!isEditing)}
            className="p-1 hover:bg-purple-200 rounded"
            title="Edit node"
          >
            <Edit3 size={14} className="text-purple-600" />
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
            {/* Logic Type Selection */}
            <div>
              <label className="block text-sm font-medium mb-1">Logic Type</label>
              <select
                value={logicType}
                onChange={(e) => setLogicType(e.target.value as LogicType)}
                className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
              >
                {logicTypes.map(type => (
                  <option key={type} value={type}>{type}</option>
                ))}
              </select>
            </div>

            {/* Condition (for IfElse) */}
            {logicType === 'IfElse' && (
              <div>
                <label className="block text-sm font-medium mb-1">Condition</label>
                <textarea
                  value={condition}
                  onChange={(e) => setCondition(e.target.value)}
                  placeholder="e.g., output.confidence > 0.8"
                  className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
                  rows={2}
                />
                <div className="text-xs text-gray-500 mt-1">
                  Use field names from input signature
                </div>
              </div>
            )}

            {/* Parameters */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-sm font-medium">Parameters</label>
                <button
                  onClick={addParameter}
                  className="px-2 py-1 bg-purple-500 text-white rounded text-xs hover:bg-purple-600"
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
              className="w-full px-3 py-2 bg-purple-600 text-white rounded hover:bg-purple-700"
            >
              Save
            </button>
          </div>
        ) : (
          <div className="space-y-2">
            {/* Condition Display */}
            {logicType === 'IfElse' && condition && (
              <div className="text-sm">
                <span className="font-medium">Condition:</span>
                <div className="mt-1 p-2 bg-gray-50 rounded text-xs font-mono">
                  {condition}
                </div>
              </div>
            )}

            {/* Output Labels for IfElse */}
            {logicType === 'IfElse' && (
              <div className="text-xs space-y-1">
                <div className="flex justify-between items-center">
                  <span>True path:</span>
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                </div>
                <div className="flex justify-between items-center">
                  <span>False path:</span>
                  <div className="w-2 h-2 bg-red-500 rounded-full"></div>
                </div>
              </div>
            )}

            {/* Parameters Display */}
            {Object.keys(parameters).length > 0 && (
              <div className="text-sm">
                <div className="font-medium mb-1">Parameters</div>
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

            {!condition && Object.keys(parameters).length === 0 && (
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

export default LogicNode;