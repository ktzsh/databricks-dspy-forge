import React, { useState, useEffect } from 'react';
import { Handle, Position, NodeProps, useReactFlow, useNodes, useEdges } from 'reactflow';
import { Edit3, GitBranch, GitMerge, Trash2, Filter } from 'lucide-react';
import { LogicNodeData, LogicType, SignatureField, SignatureFieldNodeData } from '../../types/workflow';
import TraceIndicator from './TraceIndicator';

const logicTypes: LogicType[] = ['IfElse', 'Merge', 'FieldSelector'];

const logicIcons: Record<LogicType, React.ReactNode> = {
  'IfElse': <GitBranch size={16} className="text-purple-600" />,
  'Merge': <GitMerge size={16} className="text-purple-600" />,
  'FieldSelector': <Filter size={16} className="text-purple-600" />
};

const LogicNode: React.FC<NodeProps<LogicNodeData & { traceData?: any; onTraceClick?: (nodeId: string, traceData: any) => void }>> = ({ data, selected, id }) => {
  const { traceData, onTraceClick, ...nodeData } = data;
  const [isEditing, setIsEditing] = useState(false);
  const [nodeLabel, setNodeLabel] = useState(nodeData.label || nodeData.logicType || 'Logic');
  const [logicType, setLogicType] = useState<LogicType>(nodeData.logicType || 'IfElse');
  const [condition, setCondition] = useState(nodeData.condition || '');
  const [parameters, setParameters] = useState(nodeData.parameters || {});
  const [selectedFields, setSelectedFields] = useState<string[]>(nodeData.selectedFields || []);
  const [fieldMappings, setFieldMappings] = useState<Record<string, string>>(nodeData.fieldMappings || {});
  const [availableFields, setAvailableFields] = useState<SignatureField[]>([]);
  
  const { deleteElements, setNodes } = useReactFlow();
  const nodes = useNodes();
  const edges = useEdges();

  // Dynamically detect available fields from connected input nodes
  useEffect(() => {
    if (logicType === 'FieldSelector') {
      const inputEdges = edges.filter(edge => edge.target === id);
      const allFields: SignatureField[] = [];

      inputEdges.forEach(edge => {
        const sourceNode = nodes.find(node => node.id === edge.source);
        if (sourceNode && sourceNode.type === 'signature_field') {
          const nodeData = sourceNode.data as SignatureFieldNodeData;
          const nodeFields = nodeData?.fields || [];
          allFields.push(...nodeFields);
        }
      });

      // Remove duplicates based on field name
      const uniqueFields = allFields.filter((field, index, self) => 
        index === self.findIndex(f => f.name === field.name)
      );

      setAvailableFields(uniqueFields);
    }
  }, [logicType, nodes, edges, id]);

  const handleSave = () => {
    // Update the node data immutably using setNodes to ensure React Flow detects the change
    setNodes((nds) =>
      nds.map((node) =>
        node.id === id
          ? {
              ...node,
              data: {
                ...nodeData,
                label: nodeLabel,
                logicType: logicType,
                condition: condition,
                parameters: parameters,
                selectedFields: selectedFields,
                fieldMappings: fieldMappings,
                traceData,
                onTraceClick
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

  const toggleFieldSelection = (fieldName: string) => {
    setSelectedFields(prev => 
      prev.includes(fieldName) 
        ? prev.filter(f => f !== fieldName)
        : [...prev, fieldName]
    );
  };

  const updateFieldMapping = (originalName: string, newName: string) => {
    setFieldMappings(prev => ({
      ...prev,
      [originalName]: newName
    }));
  };

  const removeFieldMapping = (fieldName: string) => {
    setFieldMappings(prev => {
      const { [fieldName]: removed, ...rest } = prev;
      return rest;
    });
  };

  return (
    <div className={`logic-node min-w-[250px] relative ${selected ? 'node-selected' : ''}`}>
      {/* Handles */}
      <Handle
        type="target"
        position={Position.Top}
        className="w-3 h-3 bg-purple-500"
      />
      
      {/* Multiple output handles for branching logic */}
      {logicType === 'IfElse' ? (
        <>
          <Handle
            type="source"
            position={Position.Bottom}
            id="true"
            style={{ left: '30%' }}
            className="w-3 h-3 bg-green-500"
          />
          <Handle
            type="source"
            position={Position.Bottom}
            id="false"
            style={{ left: '70%' }}
            className="w-3 h-3 bg-red-500"
          />
        </>
      ) : (
        <Handle
          type="source"
          position={Position.Bottom}
          className="w-3 h-3 bg-purple-500"
        />
      )}

      {/* Header */}
      <div className="flex items-center justify-between p-3 bg-purple-100 border-b border-purple-200">
        <div className="flex flex-col">
          <div className="flex items-center space-x-2">
            {logicIcons[logicType] || <GitBranch size={16} className="text-purple-600" />}
            <span className="font-medium text-purple-800">{nodeLabel}</span>
          </div>
          <div className="text-xs text-purple-600 opacity-75 mt-1">{logicType}</div>
          <div className="text-xs text-purple-600 opacity-75">{id}</div>
        </div>
        <div className="flex items-center space-x-1">
          <button
            onClick={(e) => {
              e.stopPropagation();
              setIsEditing(!isEditing);
            }}
            className="p-1 hover:bg-purple-200 rounded"
            title="Edit node"
          >
            <Edit3 size={14} className="text-purple-600" />
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              handleDelete();
            }}
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

            {/* Field Selection (for FieldSelector) */}
            {logicType === 'FieldSelector' && (
              <div>
                <label className="block text-sm font-medium mb-2">Field Selection</label>
                {availableFields.length > 0 ? (
                  <div className="space-y-2 max-h-32 overflow-y-auto">
                    {availableFields.map((field) => (
                      <div key={field.name} className="border border-gray-200 rounded p-2">
                        <div className="flex items-center space-x-2 mb-2">
                          <input
                            type="checkbox"
                            checked={selectedFields.includes(field.name)}
                            onChange={() => toggleFieldSelection(field.name)}
                            className="rounded"
                          />
                          <span className="text-sm font-medium">{field.name}</span>
                          <span className="text-xs text-gray-500">({field.type})</span>
                        </div>
                        
                        {selectedFields.includes(field.name) && (
                          <div className="flex items-center space-x-2">
                            <label className="text-xs text-gray-600">Rename to:</label>
                            <input
                              type="text"
                              value={fieldMappings[field.name] || ''}
                              onChange={(e) => updateFieldMapping(field.name, e.target.value)}
                              placeholder="Optional new name"
                              className="flex-1 px-2 py-1 border border-gray-300 rounded text-xs"
                            />
                            {fieldMappings[field.name] && (
                              <button
                                onClick={() => removeFieldMapping(field.name)}
                                className="text-red-500 hover:text-red-700 text-xs"
                              >
                                Clear
                              </button>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-sm text-gray-500 p-2 border border-gray-200 rounded">
                    {edges.some(edge => edge.target === id) 
                      ? "No fields available from connected nodes. Ensure connected nodes have fields defined."
                      : "No input fields detected. Connect this node to a SignatureField to see available fields."
                    }
                  </div>
                )}
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
              onClick={(e) => {
                e.stopPropagation();
                handleSave();
              }}
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

            {/* Field Selection Display */}
            {logicType === 'FieldSelector' && (
              <div className="text-sm">
                <div className="font-medium mb-1 flex items-center">
                  <Filter size={12} className="mr-1" />
                  Selected Fields
                </div>
                {selectedFields.length > 0 ? (
                  <div className="space-y-1 max-h-20 overflow-y-auto">
                    {selectedFields.map((fieldName) => (
                      <div key={fieldName} className="flex justify-between items-center">
                        <span className="text-gray-600">{fieldName}</span>
                        {fieldMappings[fieldName] && (
                          <span className="text-xs text-blue-600">
                            → {fieldMappings[fieldName]}
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-xs text-gray-500">No fields selected</div>
                )}
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

            {!condition && Object.keys(parameters).length === 0 && selectedFields.length === 0 && (
              <div className="text-sm text-gray-500 text-center py-2">
                No configuration
              </div>
            )}
          </div>
        )}
      </div>

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

export default LogicNode;