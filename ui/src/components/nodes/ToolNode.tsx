import React, { useState } from 'react';
import { Handle, Position, NodeProps, useReactFlow } from 'reactflow';
import { Edit3, Wrench, Trash2, Plus, X } from 'lucide-react';
import { ToolNodeData, ToolType, MCPHeader } from '../../types/workflow';
import TraceIndicator from './TraceIndicator';

const toolTypes: ToolType[] = ['MCP_TOOL', 'UC_FUNCTION'];

const toolTypeLabels: Record<ToolType, string> = {
  'MCP_TOOL': 'MCP Tool',
  'UC_FUNCTION': 'UC Function'
};

const ToolNode: React.FC<NodeProps<ToolNodeData & { traceData?: any; onTraceClick?: (nodeId: string, traceData: any) => void }>> = ({ data, selected, id }) => {
  const { traceData, onTraceClick, ...nodeData } = data;
  const [isEditing, setIsEditing] = useState(false);
  const [nodeLabel, setNodeLabel] = useState(nodeData.label || nodeData.toolName || 'Tool');
  const [toolType, setToolType] = useState<ToolType>(nodeData.toolType || 'MCP_TOOL');
  const [toolName, setToolName] = useState(nodeData.toolName || '');
  const [description, setDescription] = useState(nodeData.description || '');

  // MCP-specific state
  const [mcpUrl, setMcpUrl] = useState(nodeData.mcpUrl || '');
  const [mcpHeaders, setMcpHeaders] = useState<MCPHeader[]>(nodeData.mcpHeaders || []);

  // UC Function-specific state
  const [catalog, setCatalog] = useState(nodeData.catalog || '');
  const [schema, setSchema] = useState(nodeData.schema || '');
  const [functionName, setFunctionName] = useState(nodeData.functionName || '');
  const parameters = nodeData.parameters || {};

  const { deleteElements, setNodes } = useReactFlow();

  const handleSave = () => {
    // Update the node data immutably using setNodes
    setNodes((nds) =>
      nds.map((node) =>
        node.id === id
          ? {
              ...node,
              data: {
                ...node.data,
                label: nodeLabel,
                toolType: toolType,
                toolName: toolName,
                description: description,
                // MCP fields
                mcpUrl: toolType === 'MCP_TOOL' ? mcpUrl : undefined,
                mcpHeaders: toolType === 'MCP_TOOL' ? mcpHeaders : undefined,
                // UC Function fields
                catalog: toolType === 'UC_FUNCTION' ? catalog : undefined,
                schema: toolType === 'UC_FUNCTION' ? schema : undefined,
                functionName: toolType === 'UC_FUNCTION' ? functionName : undefined,
                parameters: parameters,
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

  const addMcpHeader = () => {
    setMcpHeaders([...mcpHeaders, { key: '', value: '', isSecret: false, envVarName: '' }]);
  };

  const updateMcpHeader = (index: number, field: keyof MCPHeader, value: any) => {
    const newHeaders = [...mcpHeaders];
    newHeaders[index] = { ...newHeaders[index], [field]: value };
    setMcpHeaders(newHeaders);
  };

  const removeMcpHeader = (index: number) => {
    setMcpHeaders(mcpHeaders.filter((_, i) => i !== index));
  };

  return (
    <div className={`min-w-[280px] relative bg-white rounded-xl border-2 transition-all duration-200 shadow-soft-lg ${
      selected ? 'border-purple-400 shadow-xl ring-2 ring-purple-200' : 'border-purple-200 hover:border-purple-300'
    }`}>
      {/* Handles */}
      {/* Tool output handle - connects to ReAct modules */}
      <Handle
        type="source"
        position={Position.Right}
        id="tool-output"
        className="w-3 h-3 bg-purple-500 border-2 border-white shadow-soft"
        style={{ top: '50%' }}
      />

      {/* Header */}
      <div className="flex items-center justify-between p-3.5 bg-gradient-to-r from-purple-50 to-purple-100/50 border-b border-purple-200 rounded-t-xl">
        <div className="flex flex-col flex-1 min-w-0">
          <div className="flex items-center space-x-2">
            <div className="p-1.5 bg-white rounded-lg shadow-sm">
              <Wrench size={16} className="text-purple-600" />
            </div>
            <span className="font-semibold text-purple-900 truncate">{nodeLabel}</span>
          </div>
          <div className="text-xs text-purple-600 font-medium mt-1.5">{toolTypeLabels[toolType]}</div>
          <div className="text-xs text-slate-500 font-mono">{id}</div>
        </div>
        <div className="flex items-center space-x-1 ml-2">
          <button
            onClick={(e) => {
              e.stopPropagation();
              setIsEditing(!isEditing);
            }}
            className="p-1.5 hover:bg-purple-200/50 rounded-lg transition-colors"
            title="Edit node"
          >
            <Edit3 size={14} className="text-purple-700" />
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

            {/* Tool Type Selection */}
            <div>
              <label className="block text-sm font-medium mb-1">Tool Type</label>
              <select
                value={toolType}
                onChange={(e) => setToolType(e.target.value as ToolType)}
                className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
              >
                {toolTypes.map(type => (
                  <option key={type} value={type}>{toolTypeLabels[type]}</option>
                ))}
              </select>
            </div>

            {/* Tool Name */}
            <div>
              <label className="block text-sm font-medium mb-1">
                Tool Name <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={toolName}
                onChange={(e) => setToolName(e.target.value)}
                placeholder="e.g., github_search"
                className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
                required
              />
            </div>

            {/* Description */}
            <div>
              <label className="block text-sm font-medium mb-1">Description</label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Describe what this tool does..."
                className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
                rows={2}
              />
            </div>

            {/* MCP Tool Fields */}
            {toolType === 'MCP_TOOL' && (
              <>
                <div>
                  <label className="block text-sm font-medium mb-1">
                    MCP Server URL <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="url"
                    value={mcpUrl}
                    onChange={(e) => setMcpUrl(e.target.value)}
                    placeholder="https://api.example.com/mcp/"
                    className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
                    required
                  />
                </div>

                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="text-sm font-medium">Headers</label>
                    <button
                      onClick={addMcpHeader}
                      className="flex items-center space-x-1 px-2 py-1 bg-purple-500 text-white rounded text-xs hover:bg-purple-600"
                    >
                      <Plus size={12} />
                      <span>Add</span>
                    </button>
                  </div>

                  <div className="space-y-2 max-h-48 overflow-y-auto">
                    {mcpHeaders.map((header, index) => (
                      <div key={index} className="p-2 bg-gray-50 rounded border border-gray-200">
                        <div className="space-y-1">
                          <input
                            type="text"
                            value={header.key}
                            onChange={(e) => updateMcpHeader(index, 'key', e.target.value)}
                            placeholder="Header key (e.g., Authorization)"
                            className="w-full px-2 py-1 border border-gray-300 rounded text-xs"
                          />
                          <input
                            type="text"
                            value={header.value}
                            onChange={(e) => updateMcpHeader(index, 'value', e.target.value)}
                            placeholder={header.isSecret ? "Value (will use env var)" : "Header value"}
                            className="w-full px-2 py-1 border border-gray-300 rounded text-xs"
                            disabled={header.isSecret}
                          />
                          <div className="flex items-center space-x-2">
                            <label className="flex items-center space-x-1 text-xs">
                              <input
                                type="checkbox"
                                checked={header.isSecret}
                                onChange={(e) => updateMcpHeader(index, 'isSecret', e.target.checked)}
                                className="rounded"
                              />
                              <span>Use secret (env var)</span>
                            </label>
                            {header.isSecret && (
                              <input
                                type="text"
                                value={header.envVarName || ''}
                                onChange={(e) => updateMcpHeader(index, 'envVarName', e.target.value)}
                                placeholder="ENV_VAR_NAME"
                                className="flex-1 px-2 py-1 border border-gray-300 rounded text-xs"
                              />
                            )}
                            <button
                              onClick={() => removeMcpHeader(index)}
                              className="p-1 text-red-500 hover:bg-red-50 rounded"
                            >
                              <X size={14} />
                            </button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            )}

            {/* UC Function Fields */}
            {toolType === 'UC_FUNCTION' && (
              <>
                <div>
                  <label className="block text-sm font-medium mb-1">
                    Catalog <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={catalog}
                    onChange={(e) => setCatalog(e.target.value)}
                    placeholder="main"
                    className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">
                    Schema <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={schema}
                    onChange={(e) => setSchema(e.target.value)}
                    placeholder="default"
                    className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">
                    Function Name <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={functionName}
                    onChange={(e) => setFunctionName(e.target.value)}
                    placeholder="my_function"
                    className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
                    required
                  />
                  <div className="text-xs text-gray-500 mt-1">
                    Full name: {catalog && schema && functionName ? `${catalog}.${schema}.${functionName}` : '(incomplete)'}
                  </div>
                </div>
              </>
            )}

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
            {/* Tool Name Display */}
            {toolName && (
              <div className="text-sm">
                <span className="font-medium">Name:</span>
                <span className="ml-2 text-gray-600">{toolName}</span>
              </div>
            )}

            {/* Description Display */}
            {description && (
              <div className="text-sm">
                <span className="font-medium">Description:</span>
                <div className="mt-1 p-2 bg-gray-50 rounded text-xs">
                  {description}
                </div>
              </div>
            )}

            {/* MCP URL Display */}
            {toolType === 'MCP_TOOL' && mcpUrl && (
              <div className="text-sm">
                <span className="font-medium">MCP URL:</span>
                <div className="mt-1 p-2 bg-gray-50 rounded text-xs break-all">
                  {mcpUrl}
                </div>
              </div>
            )}

            {/* MCP Headers Display */}
            {toolType === 'MCP_TOOL' && mcpHeaders.length > 0 && (
              <div className="text-sm">
                <span className="font-medium">Headers:</span>
                <div className="mt-1 space-y-1">
                  {mcpHeaders.map((header, index) => (
                    <div key={index} className="p-1.5 bg-gray-50 rounded text-xs">
                      <span className="font-mono">{header.key}</span>
                      {header.isSecret && (
                        <span className="ml-2 text-purple-600">→ ${header.envVarName}</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* UC Function Display */}
            {toolType === 'UC_FUNCTION' && catalog && schema && functionName && (
              <div className="text-sm">
                <span className="font-medium">Function:</span>
                <div className="mt-1 p-2 bg-gray-50 rounded text-xs font-mono">
                  {catalog}.{schema}.{functionName}
                </div>
              </div>
            )}

            {!toolName && (
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

export default ToolNode;
