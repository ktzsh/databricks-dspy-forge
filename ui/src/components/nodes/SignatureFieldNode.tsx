import React, { useState } from 'react';
import { Handle, Position, NodeProps, useReactFlow } from 'reactflow';
import { Plus, X, Edit3, Database, Trash2 } from 'lucide-react';
import { SignatureFieldNodeData, SignatureField, FieldType } from '../../types/workflow';

const fieldTypes: FieldType[] = ['str', 'int', 'bool', 'float', 'list[str]', 'list[int]', 'dict', 'list[dict[str, Any]]', 'Any'];

const SignatureFieldNode: React.FC<NodeProps<SignatureFieldNodeData>> = ({ data, selected, id }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [nodeLabel, setNodeLabel] = useState(data.label || 'Signature Field');
  const [fields, setFields] = useState<SignatureField[]>(data.fields || []);
  const [isStart, setIsStart] = useState(data.isStart || false);
  const [isEnd, setIsEnd] = useState(data.isEnd || false);
  const [connectionMode, setConnectionMode] = useState<'whole' | 'field-level'>(data.connectionMode || 'whole');
  const { deleteElements } = useReactFlow();

  // Check if this is the default start node
  const isDefaultStartNode = id === 'default-start-node';

  const addField = () => {
    // Don't allow adding fields to default start node
    if (isDefaultStartNode) return;
    
    const newField: SignatureField = {
      name: `field_${fields.length + 1}`,
      type: 'str',
      description: '',
      required: true
    };
    setFields([...fields, newField]);
  };

  const removeField = (index: number) => {
    // Don't allow removing fields from default start node
    if (isDefaultStartNode) return;
    
    setFields(fields.filter((_, i) => i !== index));
  };

  const updateField = (index: number, updatedField: Partial<SignatureField>) => {
    // For default start node, only allow updating descriptions
    if (isDefaultStartNode) {
      const field = fields[index];
      if (field && (field.name === 'question' || field.name === 'history')) {
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
    // Update the node data
    data.label = nodeLabel;
    data.fields = fields;
    
    // For default start node, don't allow changing start/end status
    if (!isDefaultStartNode) {
      data.isStart = isStart;
      data.isEnd = isEnd;
    }
    
    data.connectionMode = connectionMode;
    setIsEditing(false);
  };

  const handleDelete = () => {
    // Don't allow deleting the default start node
    if (isDefaultStartNode) return;
    
    deleteElements({ nodes: [{ id }] });
  };

  return (
    <div className={`signature-field-node min-w-[250px] ${selected ? 'node-selected' : ''}`}>
      {/* Handles */}
      {connectionMode === 'whole' ? (
        // Whole-node connection mode
        <>
          {!isStart && (
            <Handle
              type="target"
              position={Position.Left}
              className="w-3 h-3 bg-blue-500"
            />
          )}
          {!isEnd && (
            <Handle
              type="source"
              position={Position.Right}
              className="w-3 h-3 bg-blue-500"
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
              position={Position.Left}
              style={{ top: `${120 + index * 40}px` }}
              className="w-2 h-2 bg-blue-500"
              title={`Input: ${field.name} (${field.type})`}
            />
          ))}
          {!isEnd && fields.map((field, index) => (
            <Handle
              key={`source-${field.name}`}
              id={`source-${field.name}`}
              type="source"
              position={Position.Right}
              style={{ top: `${120 + index * 40}px` }}
              className="w-2 h-2 bg-blue-500"
              title={`Output: ${field.name} (${field.type})`}
            />
          ))}
        </>
      )}

      {/* Header */}
      <div className="flex items-center justify-between p-3 bg-blue-100 border-b border-blue-200">
        <div className="flex flex-col">
          <div className="flex items-center space-x-2">
            <Database size={16} className="text-blue-600" />
            <span className="font-medium text-blue-800">{nodeLabel}</span>
          </div>
          <div className="text-xs text-blue-600 opacity-75 mt-1">SignatureField</div>
          <div className="text-xs text-blue-600 opacity-75">{id}</div>
        </div>
        <div className="flex items-center space-x-1">
          <button
            onClick={(e) => {
              e.stopPropagation();
              setIsEditing(!isEditing);
            }}
            className="p-1 hover:bg-blue-200 rounded"
            title="Edit node"
          >
            <Edit3 size={14} className="text-blue-600" />
          </button>
          {!isDefaultStartNode && (
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
                disabled={isDefaultStartNode}
              />
            </div>
            
            {/* Node Type Settings */}
            {!isDefaultStartNode && (
              <div className="flex space-x-4">
                <label className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    checked={isStart}
                    onChange={(e) => setIsStart(e.target.checked)}
                    className="rounded"
                  />
                  <span className="text-sm">Start</span>
                </label>
                <label className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    checked={isEnd}
                    onChange={(e) => setIsEnd(e.target.checked)}
                    className="rounded"
                  />
                  <span className="text-sm">End</span>
                </label>
              </div>
            )}
            
            {isDefaultStartNode && (
              <div className="text-sm text-gray-600 bg-gray-50 p-2 rounded">
                ℹ️ This is the default input field and cannot be modified except for descriptions.
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
                {!isDefaultStartNode && (
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
                <div key={index} className="border border-gray-200 rounded p-2 space-y-2">
                  <div className="flex items-center justify-between">
                    <input
                      type="text"
                      value={field.name}
                      onChange={(e) => updateField(index, { name: e.target.value })}
                      placeholder="Field name"
                      className="flex-1 px-2 py-1 border border-gray-300 rounded text-sm"
                      disabled={isDefaultStartNode}
                    />
                    {!isDefaultStartNode && (
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
                    disabled={isDefaultStartNode}
                  >
                    {fieldTypes.map(type => (
                      <option key={type} value={type}>{type}</option>
                    ))}
                  </select>

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
                  <div key={index} className="flex items-center justify-between text-sm">
                    <div className="flex items-center space-x-2">
                      {connectionMode === 'field-level' && (
                        <div className="w-2 h-2 bg-blue-500 rounded-full" title="Individual connection handle"></div>
                      )}
                      <span className="font-medium">{field.name}</span>
                    </div>
                    <span className="text-gray-500">{field.type}</span>
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
    </div>
  );
};

export default SignatureFieldNode;