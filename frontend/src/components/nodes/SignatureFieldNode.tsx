import React, { useState } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { Plus, X, Edit3, Database } from 'lucide-react';
import { SignatureFieldNodeData, SignatureField, FieldType } from '../../types/workflow';

const fieldTypes: FieldType[] = ['str', 'int', 'bool', 'float', 'list[str]', 'list[int]', 'dict', 'Any'];

const SignatureFieldNode: React.FC<NodeProps<SignatureFieldNodeData>> = ({ data, selected }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [fields, setFields] = useState<SignatureField[]>(data.fields || []);
  const [isStart, setIsStart] = useState(data.isStart || false);
  const [isEnd, setIsEnd] = useState(data.isEnd || false);

  const addField = () => {
    const newField: SignatureField = {
      name: `field_${fields.length + 1}`,
      type: 'str',
      description: '',
      required: true
    };
    setFields([...fields, newField]);
  };

  const removeField = (index: number) => {
    setFields(fields.filter((_, i) => i !== index));
  };

  const updateField = (index: number, updatedField: Partial<SignatureField>) => {
    const updatedFields = fields.map((field, i) => 
      i === index ? { ...field, ...updatedField } : field
    );
    setFields(updatedFields);
  };

  const handleSave = () => {
    // Update the node data
    data.fields = fields;
    data.isStart = isStart;
    data.isEnd = isEnd;
    setIsEditing(false);
  };

  return (
    <div className={`signature-field-node min-w-[250px] ${selected ? 'node-selected' : ''}`}>
      {/* Handles */}
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

      {/* Header */}
      <div className="flex items-center justify-between p-3 bg-blue-100 border-b border-blue-200">
        <div className="flex items-center space-x-2">
          <Database size={16} className="text-blue-600" />
          <span className="font-medium text-blue-800">Signature Field</span>
        </div>
        <button
          onClick={() => setIsEditing(!isEditing)}
          className="p-1 hover:bg-blue-200 rounded"
        >
          <Edit3 size={14} className="text-blue-600" />
        </button>
      </div>

      {/* Content */}
      <div className="p-3">
        {isEditing ? (
          <div className="space-y-3">
            {/* Node Type Settings */}
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

            {/* Fields */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium">Fields</label>
                <button
                  onClick={addField}
                  className="flex items-center space-x-1 px-2 py-1 bg-blue-500 text-white rounded text-xs hover:bg-blue-600"
                >
                  <Plus size={12} />
                  <span>Add</span>
                </button>
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
                    />
                    <button
                      onClick={() => removeField(index)}
                      className="p-1 text-red-500 hover:bg-red-50 rounded"
                    >
                      <X size={12} />
                    </button>
                  </div>

                  <select
                    value={field.type}
                    onChange={(e) => updateField(index, { type: e.target.value as FieldType })}
                    className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
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
              onClick={handleSave}
              className="w-full px-3 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Save
            </button>
          </div>
        ) : (
          <div className="space-y-2">
            {/* Node Type Indicators */}
            <div className="flex space-x-2">
              {isStart && (
                <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded">Start</span>
              )}
              {isEnd && (
                <span className="px-2 py-1 bg-red-100 text-red-800 text-xs rounded">End</span>
              )}
            </div>

            {/* Fields Display */}
            {fields.length > 0 ? (
              <div className="space-y-1">
                {fields.map((field, index) => (
                  <div key={index} className="flex items-center justify-between text-sm">
                    <span className="font-medium">{field.name}</span>
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