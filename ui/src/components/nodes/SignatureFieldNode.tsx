import React, { useState, useEffect } from 'react';
import { Handle, Position, NodeProps, useReactFlow, useNodes, useEdges } from 'reactflow';
import { Plus, X, Edit3, Database, Trash2 } from 'lucide-react';
import { SignatureFieldNodeData, SignatureField, FieldType } from '../../types/workflow';
import TraceIndicator from './TraceIndicator';

const fieldTypes: FieldType[] = ['str', 'int', 'bool', 'float', 'dict', 'list[str]', 'list[int]', 'list[dict[str, Any]]', 'enum'];

const SignatureFieldNode: React.FC<NodeProps<SignatureFieldNodeData & { traceData?: any; onTraceClick?: (nodeId: string, traceData: any) => void }>> = ({ data, selected, id }) => {
  const { traceData, onTraceClick, ...nodeData } = data;
  const [isEditing, setIsEditing] = useState(false);
  const [nodeLabel, setNodeLabel] = useState(nodeData.label || 'Signature Field');
  const [fields, setFields] = useState<SignatureField[]>(nodeData.fields || []);
  const [isStart, setIsStart] = useState(nodeData.isStart || false);
  const [isEnd, setIsEnd] = useState(nodeData.isEnd || false);
  const [connectionMode, setConnectionMode] = useState<'whole' | 'field-level'>(nodeData.connectionMode || 'whole');
  const [enumInputs, setEnumInputs] = useState<Record<number, string>>({});
  const { deleteElements, setNodes } = useReactFlow();
  const nodes = useNodes();
  const edges = useEdges();

  // Check if this is a default node (start or end)
  const isDefaultStartNode = id === 'default-start-node';
  const isDefaultEndNode = id === 'default-end-node';
  const isDefaultNode = isDefaultStartNode || isDefaultEndNode;

  // Sync local state with node data when it changes (for auto-generated fields)
  useEffect(() => {
    setFields(nodeData.fields || []);
  }, [nodeData.fields]);

  // Check if this signature field is connected to a ChainOfThought module
  const isConnectedToChainOfThought = () => {
    const incomingEdges = edges.filter(edge => edge.target === id);
    return incomingEdges.some(edge => {
      const sourceNode = nodes.find(n => n.id === edge.source);
      return sourceNode?.type === 'module' && (sourceNode.data as any)?.moduleType === 'ChainOfThought';
    });
  };

  const addField = () => {
    // Don't allow adding fields to default nodes
    if (isDefaultNode) return;

    const newField: SignatureField = {
      name: `field_${fields.length + 1}`,
      type: 'str',
      description: '',
      required: true,
      enumValues: []
    };
    setFields([...fields, newField]);
  };

  const removeField = (index: number) => {
    // Don't allow removing fields from default nodes
    if (isDefaultNode) return;
    
    // Don't allow removing the rationale field if connected to ChainOfThought
    const field = fields[index];
    if (field?.name === 'reasoning' && isConnectedToChainOfThought()) {
      return;
    }
    
    setFields(fields.filter((_, i) => i !== index));
  };

  const updateField = (index: number, updatedField: Partial<SignatureField>) => {
    // For default nodes, only allow updating descriptions
    if (isDefaultNode) {
      const field = fields[index];
      // For default start node fields or default end node answer field
      if (field && (field.name === 'question' || field.name === 'history' || field.name === 'answer')) {
        // Only allow description changes
        const allowedUpdates: Partial<SignatureField> = {};
        if (updatedField.description !== undefined) {
          allowedUpdates.description = updatedField.description;
        }
        const updatedFields = fields.map((field, i) =>
          i === index ? { ...field, ...allowedUpdates } : field
        );
        setFields(updatedFields);
      }
      return;
    }
    
    const updatedFields = fields.map((field, i) => 
      i === index ? { ...field, ...updatedField } : field
    );
    setFields(updatedFields);
  };

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
                fields: fields,
                connectionMode: connectionMode,
                // Don't allow modifying isStart/isEnd for any field nodes
              }
            }
          : node
      )
    );
    setIsEditing(false);
  };

  const handleDelete = () => {
    // Don't allow deleting the default nodes
    if (isDefaultNode) return;
    
    deleteElements({ nodes: [{ id }] });
  };

  return (
    <div className={`min-w-[280px] relative bg-white rounded-xl border-2 transition-all duration-200 shadow-soft-lg ${
      selected ? 'border-sky-400 shadow-xl ring-2 ring-sky-200' : 'border-sky-200 hover:border-sky-300'
    }`}>
      {/* Handles */}
      {connectionMode === 'whole' ? (
        // Whole-node connection mode
        <>
          {!isStart && (
            <Handle
              type="target"
              position={Position.Top}
              className="w-3 h-3 bg-sky-500 border-2 border-white shadow-soft"
            />
          )}
          {!isEnd && (
            <Handle
              type="source"
              position={Position.Bottom}
              className="w-3 h-3 bg-sky-500 border-2 border-white shadow-soft"
            />
          )}
        </>
      ) : (
        // Field-level connection mode
        <>
          {!isStart && fields.map((field, index) => (
            <Handle
              key={`target-${field.name}`}
              id={`target-${field.name}`}
              type="target"
              position={Position.Top}
              style={{ left: `${50 + index * 40}px` }}
              className="w-2 h-2 bg-blue-500"
              title={`Input: ${field.name} (${field.type})`}
            />
          ))}
          {!isEnd && fields.map((field, index) => (
            <Handle
              key={`source-${field.name}`}
              id={`source-${field.name}`}
              type="source"
              position={Position.Bottom}
              style={{ left: `${50 + index * 40}px` }}
              className="w-2 h-2 bg-blue-500"
              title={`Output: ${field.name} (${field.type})`}
            />
          ))}
        </>
      )}

      {/* Header */}
      <div className="flex items-center justify-between p-3.5 bg-gradient-to-r from-sky-50 to-sky-100/50 border-b border-sky-200 rounded-t-xl">
        <div className="flex flex-col flex-1 min-w-0">
          <div className="flex items-center space-x-2">
            <div className="p-1.5 bg-white rounded-lg shadow-sm">
              <Database size={16} className="text-sky-600" />
            </div>
            <span className="font-semibold text-sky-900 truncate">{nodeLabel}</span>
          </div>
          <div className="text-xs text-sky-600 font-medium mt-1.5">SignatureField</div>
          <div className="text-xs text-slate-500 font-mono">{id}</div>
        </div>
        <div className="flex items-center space-x-1 ml-2">
          <button
            onClick={(e) => {
              e.stopPropagation();
              setIsEditing(!isEditing);
            }}
            className="p-1.5 hover:bg-sky-200/50 rounded-lg transition-colors"
            title="Edit node"
          >
            <Edit3 size={14} className="text-sky-700" />
          </button>
          {!isDefaultNode && (
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
          )}
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
                disabled={isDefaultNode}
              />
            </div>
            
            {/* Node Type Settings - Hidden for all field nodes */}
            
            {isDefaultNode && (
              <div className="text-sm text-gray-600 bg-gray-50 p-2 rounded">
                This is a default {isDefaultStartNode ? 'input' : 'output'} field and cannot be modified except for descriptions.
              </div>
            )}

            {/* Connection Mode Settings */}
            <div>
              <label className="block text-sm font-medium mb-1">Connection Mode</label>
              <select
                value={connectionMode}
                onChange={(e) => setConnectionMode(e.target.value as 'whole' | 'field-level')}
                className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
              >
                <option value="whole">Whole Node (Simple)</option>
                <option value="field-level">Field Level (Advanced)</option>
              </select>
              <div className="text-xs text-gray-500 mt-1">
                {connectionMode === 'whole' 
                  ? 'Connect entire signature as one unit'
                  : 'Connect individual fields separately'
                }
              </div>
            </div>

            {/* Fields */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium">Fields</label>
                {!isDefaultNode && (
                  <button
                    onClick={addField}
                    className="flex items-center space-x-1 px-2 py-1 bg-blue-500 text-white rounded text-xs hover:bg-blue-600"
                  >
                    <Plus size={12} />
                    <span>Add</span>
                  </button>
                )}
              </div>

              {fields.map((field, index) => (
                <div key={index} className={`border rounded p-2 space-y-2 ${
                  field.name === 'reasoning' && isConnectedToChainOfThought() 
                    ? 'border-blue-300 bg-blue-50' 
                    : 'border-gray-200'
                }`}>
                  {field.name === 'reasoning' && isConnectedToChainOfThought() && (
                    <div className="text-xs text-blue-600 font-medium flex items-center">
                      Auto-generated for ChainOfThought
                    </div>
                  )}
                  <div className="flex items-center justify-between">
                    <input
                      type="text"
                      value={field.name}
                      onChange={(e) => updateField(index, { name: e.target.value })}
                      placeholder="Field name"
                      className="flex-1 px-2 py-1 border border-gray-300 rounded text-sm"
                      disabled={isDefaultNode || (field.name === 'reasoning' && isConnectedToChainOfThought())}
                    />
                    {!isDefaultNode && !(field.name === 'reasoning' && isConnectedToChainOfThought()) && (
                      <button
                        onClick={() => removeField(index)}
                        className="p-1 text-red-500 hover:bg-red-50 rounded"
                      >
                        <X size={12} />
                      </button>
                    )}
                  </div>

                  <select
                    value={field.type}
                    onChange={(e) => updateField(index, { type: e.target.value as FieldType })}
                    className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
                    disabled={isDefaultNode || (field.name === 'reasoning' && isConnectedToChainOfThought())}
                  >
                    {fieldTypes.map(type => (
                      <option key={type} value={type}>{type}</option>
                    ))}
                  </select>

                  {field.type === 'enum' && (
                    <div className="space-y-2">
                      <label className="text-xs font-medium text-gray-700">Enum Values (comma-separated)</label>
                      <input
                        type="text"
                        value={enumInputs[index] ?? field.enumValues?.join(', ') ?? ''}
                        onChange={(e) => {
                          setEnumInputs({ ...enumInputs, [index]: e.target.value });
                        }}
                        onBlur={(e) => {
                          const values = e.target.value.split(',').map(v => v.trim()).filter(v => v);
                          updateField(index, { enumValues: values });
                          const newEnumInputs = { ...enumInputs };
                          delete newEnumInputs[index];
                          setEnumInputs(newEnumInputs);
                        }}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') {
                            const values = e.currentTarget.value.split(',').map(v => v.trim()).filter(v => v);
                            updateField(index, { enumValues: values });
                            const newEnumInputs = { ...enumInputs };
                            delete newEnumInputs[index];
                            setEnumInputs(newEnumInputs);
                          }
                        }}
                        placeholder="e.g., pending, approved, rejected"
                        className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
                        disabled={isDefaultNode}
                      />
                      {field.enumValues && field.enumValues.length > 0 && (
                        <div className="flex flex-wrap gap-1">
                          {field.enumValues.map((value, vIdx) => (
                            <span key={vIdx} className="px-2 py-0.5 bg-blue-100 text-blue-800 text-xs rounded">
                              {value}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  <input
                    type="text"
                    value={field.description || ''}
                    onChange={(e) => updateField(index, { description: e.target.value })}
                    placeholder="Description"
                    className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
                  />

                  <label className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      checked={field.required}
                      onChange={(e) => updateField(index, { required: e.target.checked })}
                      className="rounded"
                    />
                    <span className="text-sm">Required</span>
                  </label>
                </div>
              ))}
            </div>

            <button
              onClick={(e) => {
                e.stopPropagation();
                handleSave();
              }}
              className="w-full px-3 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Save
            </button>
          </div>
        ) : (
          <div className="space-y-2">
            {/* Node Type Indicators */}
            <div className="flex space-x-2 flex-wrap">
              {isStart && (
                <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded">Start</span>
              )}
              {isEnd && (
                <span className="px-2 py-1 bg-red-100 text-red-800 text-xs rounded">End</span>
              )}
              {connectionMode === 'field-level' && (
                <span className="px-2 py-1 bg-purple-100 text-purple-800 text-xs rounded">Field-Level</span>
              )}
            </div>

            {/* Fields Display */}
            {fields.length > 0 ? (
              <div className="space-y-1">
                {fields.map((field, index) => (
                  <div key={index} className={`text-sm`}>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        {connectionMode === 'field-level' && (
                          <div className="w-2 h-2 bg-blue-500 rounded-full" title="Individual connection handle"></div>
                        )}
                        <span className="font-medium">{field.name}</span>
                        {field.name === 'reasoning' && isConnectedToChainOfThought()}
                      </div>
                      <span className="text-gray-500">{field.type}</span>
                    </div>
                    {field.type === 'enum' && field.enumValues && field.enumValues.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-1 ml-4">
                        {field.enumValues.map((value, vIdx) => (
                          <span key={vIdx} className="px-1.5 py-0.5 bg-blue-50 text-blue-700 text-xs rounded">
                            {value}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-sm text-gray-500 text-center py-2">
                No fields defined
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

export default SignatureFieldNode;