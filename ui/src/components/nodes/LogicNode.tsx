import React, { useState, useEffect } from 'react';
import { Handle, Position, NodeProps, useReactFlow, useNodes, useEdges } from 'reactflow';
import { Edit3, GitMerge, Trash2, Filter, RouteIcon } from 'lucide-react';
import { LogicNodeData, LogicType, SignatureField, SignatureFieldNodeData, RouterBranch, RouterConfig } from '../../types/workflow';
import TraceIndicator from './TraceIndicator';
import ConditionBuilder from '../ConditionBuilder';

const logicTypes: LogicType[] = ['Router', 'Merge', 'FieldSelector'];

const logicIcons: Record<LogicType, React.ReactNode> = {
  'Router': <RouteIcon size={16} className="text-purple-600" />,
  'Merge': <GitMerge size={16} className="text-purple-600" />,
  'FieldSelector': <Filter size={16} className="text-purple-600" />
};

const LogicNode: React.FC<NodeProps<LogicNodeData & { traceData?: any; onTraceClick?: (nodeId: string, traceData: any) => void }>> = ({ data, selected, id }) => {
  const { traceData, onTraceClick, ...nodeData } = data;
  const [isEditing, setIsEditing] = useState(false);
  const [nodeLabel, setNodeLabel] = useState(nodeData.label || nodeData.logicType || 'Logic');
  const [logicType, setLogicType] = useState<LogicType>(nodeData.logicType || 'Router');
  const [routerConfig, setRouterConfig] = useState<RouterConfig>(
    nodeData.routerConfig || {
      branches: []
    }
  );
  const [parameters, setParameters] = useState(nodeData.parameters || {});
  const [selectedFields, setSelectedFields] = useState<string[]>(nodeData.selectedFields || []);
  const [fieldMappings, setFieldMappings] = useState<Record<string, string>>(nodeData.fieldMappings || {});
  const [availableFields, setAvailableFields] = useState<SignatureField[]>([]);
  
  const { deleteElements, setNodes } = useReactFlow();
  const nodes = useNodes();
  const edges = useEdges();

  // Dynamically detect available fields from connected input nodes
  useEffect(() => {
    if (logicType === 'FieldSelector' || logicType === 'Router') {
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

      // Auto-update empty field conditions when fields become available
      if (logicType === 'Router' && uniqueFields.length > 0) {
        setRouterConfig(prev => ({
          ...prev,
          branches: prev.branches.map(branch => ({
            ...branch,
            conditionConfig: {
              ...branch.conditionConfig,
              structuredConditions: (branch.conditionConfig.structuredConditions || []).map(cond =>
                cond.field === '' ? { ...cond, field: uniqueFields[0].name } : cond
              )
            }
          }))
        }));
      }
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
                routerConfig: routerConfig,  // Router configuration with multiple branches
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

  // Router branch management functions
  const addRouterBranch = () => {
    const newBranch: RouterBranch = {
      branchId: `branch_${Date.now()}`,
      label: `Branch ${routerConfig.branches.length + 1}`,
      conditionConfig: {
        mode: 'structured',
        structuredConditions: [
          {
            field: '',
            operator: '==',
            value: '',
            logicalOp: undefined
          }
        ]
      },
      isDefault: false
    };
    setRouterConfig(prev => ({
      ...prev,
      branches: [...prev.branches, newBranch]
    }));
  };

  const removeRouterBranch = (branchId: string) => {
    setRouterConfig(prev => ({
      ...prev,
      branches: prev.branches.filter(b => b.branchId !== branchId)
    }));
  };

  const updateRouterBranch = (branchId: string, updates: Partial<RouterBranch>) => {
    setRouterConfig(prev => ({
      ...prev,
      branches: prev.branches.map(b =>
        b.branchId === branchId ? { ...b, ...updates } : b
      )
    }));
  };

  const setDefaultBranch = (branchId: string) => {
    setRouterConfig(prev => ({
      ...prev,
      branches: prev.branches.map(b => ({
        ...b,
        isDefault: b.branchId === branchId
      }))
    }));
  };

  return (
    <div className={`min-w-[280px] relative bg-white rounded-xl border-2 transition-all duration-200 shadow-soft-lg ${
      selected ? 'border-violet-400 shadow-xl ring-2 ring-violet-200' : 'border-violet-200 hover:border-violet-300'
    }`}>
      {/* Handles */}
      <Handle
        type="target"
        position={Position.Top}
        className="w-3 h-3 bg-violet-500 border-2 border-white shadow-soft"
      />

      {/* Multiple output handles for branching logic */}
      {logicType === 'Router' ? (
        <>
          {/* Dynamic handles for each router branch */}
          {routerConfig.branches.map((branch, index) => {
            const totalBranches = routerConfig.branches.length;
            const position = totalBranches > 1 ? (100 / (totalBranches + 1)) * (index + 1) : 50;
            const colors = [
              'bg-blue-500',
              'bg-green-500',
              'bg-yellow-500',
              'bg-red-500',
              'bg-purple-500',
              'bg-pink-500',
              'bg-indigo-500',
              'bg-teal-500'
            ];
            const color = colors[index % colors.length];

            return (
              <Handle
                key={branch.branchId}
                type="source"
                position={Position.Bottom}
                id={branch.branchId}
                style={{ left: `${position}%` }}
                className={`w-3 h-3 ${color} border-2 border-white shadow-soft`}
              />
            );
          })}
        </>
      ) : (
        <Handle
          type="source"
          position={Position.Bottom}
          className="w-3 h-3 bg-violet-500 border-2 border-white shadow-soft"
        />
      )}

      {/* Header */}
      <div className="flex items-center justify-between p-3.5 bg-gradient-to-r from-violet-50 to-violet-100/50 border-b border-violet-200 rounded-t-xl">
        <div className="flex flex-col flex-1 min-w-0">
          <div className="flex items-center space-x-2">
            <div className="p-1.5 bg-white rounded-lg shadow-sm">
              {logicIcons[logicType] || <RouteIcon size={16} className="text-violet-600" />}
            </div>
            <span className="font-semibold text-violet-900 truncate">{nodeLabel}</span>
          </div>
          <div className="text-xs text-violet-600 font-medium mt-1.5">{logicType}</div>
          <div className="text-xs text-slate-500 font-mono">{id}</div>
        </div>
        <div className="flex items-center space-x-1 ml-2">
          <button
            onClick={(e) => {
              e.stopPropagation();
              setIsEditing(!isEditing);
            }}
            className="p-1.5 hover:bg-violet-200/50 rounded-lg transition-colors"
            title="Edit node"
          >
            <Edit3 size={14} className="text-violet-700" />
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

            {/* Router Branches Configuration */}
            {logicType === 'Router' && (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <label className="block text-sm font-medium">Router Branches</label>
                  <button
                    onClick={addRouterBranch}
                    className="px-2 py-1 bg-purple-500 text-white rounded text-xs hover:bg-purple-600"
                  >
                    Add Branch
                  </button>
                </div>

                <div className="space-y-3 max-h-96 overflow-y-auto">
                  {routerConfig.branches.map((branch, index) => (
                    <div key={branch.branchId} className="border border-gray-300 rounded p-3 space-y-2 bg-gray-50">
                      <div className="flex items-center justify-between">
                        <input
                          type="text"
                          value={branch.label}
                          onChange={(e) => updateRouterBranch(branch.branchId, { label: e.target.value })}
                          placeholder="Branch name"
                          className="flex-1 px-2 py-1 border border-gray-300 rounded text-sm font-medium"
                        />
                        <div className="flex items-center space-x-2 ml-2">
                          <label className="flex items-center text-xs space-x-1">
                            <input
                              type="checkbox"
                              checked={branch.isDefault || false}
                              onChange={(e) => {
                                if (e.target.checked) {
                                  setDefaultBranch(branch.branchId);
                                } else {
                                  updateRouterBranch(branch.branchId, { isDefault: false });
                                }
                              }}
                              className="rounded"
                            />
                            <span>Default</span>
                          </label>
                          <button
                            onClick={() => removeRouterBranch(branch.branchId)}
                            className="p-1 text-red-500 hover:bg-red-50 rounded"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </div>

                      {!branch.isDefault && (
                        <div className="pt-2 border-t border-gray-200">
                          <label className="block text-xs font-medium mb-2 text-gray-700">
                            Condition for {branch.label}:
                          </label>
                          <ConditionBuilder
                            conditions={branch.conditionConfig.structuredConditions || []}
                            onChange={(conditions) =>
                              updateRouterBranch(branch.branchId, {
                                conditionConfig: {
                                  ...branch.conditionConfig,
                                  structuredConditions: conditions
                                }
                              })
                            }
                            availableFields={availableFields}
                          />
                        </div>
                      )}
                    </div>
                  ))}

                  {routerConfig.branches.length === 0 && (
                    <div className="text-sm text-gray-500 p-2 border border-gray-200 rounded text-center">
                      No branches configured. Add at least one branch to enable routing.
                    </div>
                  )}
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
            {/* Router Branches Display */}
            {logicType === 'Router' && (
              <div className="text-sm">
                <div className="font-medium mb-2 flex items-center">
                  <RouteIcon size={12} className="mr-1" />
                  Router Branches ({routerConfig.branches.length})
                </div>
                {routerConfig.branches.length > 0 ? (
                  <div className="space-y-2 max-h-48 overflow-y-auto">
                    {routerConfig.branches.map((branch, index) => {
                      const colors = [
                        'border-blue-300 bg-blue-50',
                        'border-green-300 bg-green-50',
                        'border-yellow-300 bg-yellow-50',
                        'border-red-300 bg-red-50',
                        'border-purple-300 bg-purple-50',
                        'border-pink-300 bg-pink-50',
                        'border-indigo-300 bg-indigo-50',
                        'border-teal-300 bg-teal-50'
                      ];
                      const color = colors[index % colors.length];

                      return (
                        <div key={branch.branchId} className={`p-2 border rounded text-xs ${color}`}>
                          <div className="flex items-center justify-between mb-1">
                            <span className="font-semibold">{branch.label}</span>
                            {branch.isDefault && (
                              <span className="text-xs bg-gray-700 text-white px-2 py-0.5 rounded">
                                Default
                              </span>
                            )}
                          </div>
                          {!branch.isDefault && branch.conditionConfig?.structuredConditions && branch.conditionConfig.structuredConditions.length > 0 && (
                            <div className="mt-1 space-y-0.5">
                              {branch.conditionConfig.structuredConditions.map((cond, idx) => (
                                <div key={idx} className="font-mono text-xs opacity-80">
                                  {idx > 0 && branch.conditionConfig?.structuredConditions![idx - 1].logicalOp && (
                                    <span className="font-bold mr-1">
                                      {branch.conditionConfig?.structuredConditions![idx - 1].logicalOp}
                                    </span>
                                  )}
                                  {cond.field || '(no field)'} {cond.operator} {cond.value !== undefined && cond.value !== null ? JSON.stringify(cond.value) : ''}
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="text-xs text-gray-500">No branches configured</div>
                )}
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

            {logicType !== 'Router' && Object.keys(parameters).length === 0 && selectedFields.length === 0 && (
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