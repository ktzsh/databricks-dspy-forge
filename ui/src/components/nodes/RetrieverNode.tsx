import React, { useState } from 'react';
import { Handle, Position, NodeProps, useReactFlow } from 'reactflow';
import { Edit3, Database, Trash2, Settings } from 'lucide-react';
import { RetrieverNodeData, RetrieverType } from '../../types/workflow';
import TraceIndicator from './TraceIndicator';

const retrieverTypes: RetrieverType[] = ['UnstructuredRetrieve', 'StructuredRetrieve'];

const RetrieverNode: React.FC<NodeProps<RetrieverNodeData & { traceData?: any; onTraceClick?: (nodeId: string, traceData: any) => void }>> = ({ data, selected, id }) => {
  const { traceData, onTraceClick, ...nodeData } = data;
  const [isEditing, setIsEditing] = useState(false);
  const [nodeLabel, setNodeLabel] = useState(nodeData.label || nodeData.retrieverType || 'Retriever');
  const [retrieverType, setRetrieverType] = useState<RetrieverType>(nodeData.retrieverType || 'UnstructuredRetrieve');
  // UnstructuredRetrieve fields
  const [catalogName, setCatalogName] = useState(nodeData.catalogName || '');
  const [schemaName, setSchemaName] = useState(nodeData.schemaName || '');
  const [indexName, setIndexName] = useState(nodeData.indexName || '');
  const [contentColumn, setContentColumn] = useState(nodeData.contentColumn || '');
  const [idColumn, setIdColumn] = useState(nodeData.idColumn || '');
  const [embeddingModel, setEmbeddingModel] = useState(nodeData.embeddingModel || '');
  const [queryType, setQueryType] = useState<'HYBRID' | 'ANN'>(nodeData.queryType || 'HYBRID');
  const [numResults, setNumResults] = useState(nodeData.numResults || 3);
  const [scoreThreshold, setScoreThreshold] = useState(nodeData.scoreThreshold || 0.0);
  // StructuredRetrieve fields
  const [genieSpaceId, setGenieSpaceId] = useState(nodeData.genieSpaceId || '');
  const [parameters, setParameters] = useState(nodeData.parameters || {});
  
  const { deleteElements, setNodes } = useReactFlow();

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
                retrieverType: retrieverType,
                // Save UnstructuredRetrieve fields
                catalogName: catalogName,
                schemaName: schemaName,
                indexName: indexName,
                contentColumn: contentColumn,
                idColumn: idColumn,
                embeddingModel: embeddingModel,
                queryType: queryType,
                numResults: numResults,
                scoreThreshold: scoreThreshold,
                // Save StructuredRetrieve fields
                genieSpaceId: genieSpaceId,
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
    <div className={`min-w-[280px] relative bg-white rounded-xl border-2 transition-all duration-200 shadow-soft-lg ${
      selected ? 'border-amber-400 shadow-xl ring-2 ring-amber-200' : 'border-amber-200 hover:border-amber-300'
    }`}>
      {/* Handles */}
      <Handle
        type="target"
        position={Position.Top}
        className="w-3 h-3 bg-amber-500 border-2 border-white shadow-soft"
      />
      <Handle
        type="source"
        position={Position.Bottom}
        className="w-3 h-3 bg-amber-500 border-2 border-white shadow-soft"
      />

      {/* Header */}
      <div className="flex items-center justify-between p-3.5 bg-gradient-to-r from-amber-50 to-amber-100/50 border-b border-amber-200 rounded-t-xl">
        <div className="flex flex-col flex-1 min-w-0">
          <div className="flex items-center space-x-2">
            <div className="p-1.5 bg-white rounded-lg shadow-sm">
              <Database size={16} className="text-amber-600" />
            </div>
            <span className="font-semibold text-amber-900 truncate">{nodeLabel}</span>
          </div>
          <div className="text-xs text-amber-600 font-medium mt-1.5">{retrieverType}</div>
          <div className="text-xs text-slate-500 font-mono">{id}</div>
        </div>
        <div className="flex items-center space-x-1 ml-2">
          <button
            onClick={(e) => {
              e.stopPropagation();
              setIsEditing(!isEditing);
            }}
            className="p-1.5 hover:bg-amber-200/50 rounded-lg transition-colors"
            title="Edit node"
          >
            <Edit3 size={14} className="text-amber-700" />
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
            
            {/* Retriever Type Selection */}
            <div>
              <label className="block text-sm font-medium mb-1">Retriever Type</label>
              <select
                value={retrieverType}
                onChange={(e) => setRetrieverType(e.target.value as RetrieverType)}
                className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
              >
                {retrieverTypes.map(type => (
                  <option key={type} value={type}>{type}</option>
                ))}
              </select>
            </div>

            {/* Conditional Fields based on Retriever Type */}
            {retrieverType === 'UnstructuredRetrieve' && (
              <div className="space-y-2">
                <div>
                  <label className="block text-sm font-medium mb-1">
                    Catalog Name <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={catalogName}
                    onChange={(e) => setCatalogName(e.target.value)}
                    placeholder="Enter catalog name"
                    className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">
                    Schema Name <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={schemaName}
                    onChange={(e) => setSchemaName(e.target.value)}
                    placeholder="Enter schema name"
                    className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">
                    Index Name <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={indexName}
                    onChange={(e) => setIndexName(e.target.value)}
                    placeholder="Enter index name"
                    className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">
                    Content Column <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={contentColumn}
                    onChange={(e) => setContentColumn(e.target.value)}
                    placeholder="Enter content column name"
                    className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">
                    ID Column <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={idColumn}
                    onChange={(e) => setIdColumn(e.target.value)}
                    placeholder="Enter ID column name"
                    className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
                    required
                  />
                </div>
              </div>
            )}

            {retrieverType === 'StructuredRetrieve' && (
              <div>
                <label className="block text-sm font-medium mb-1">
                  Genie Space ID <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={genieSpaceId}
                  onChange={(e) => setGenieSpaceId(e.target.value)}
                  placeholder="Enter Genie Space ID"
                  className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
                  required
                />
              </div>
            )}

            {/* UnstructuredRetrieve specific options */}
            {retrieverType === 'UnstructuredRetrieve' && (
              <>
                {/* Optional Embedding Model */}
                <div>
                  <label className="block text-sm font-medium mb-1">Embedding Model</label>
                  <input
                    type="text"
                    value={embeddingModel}
                    onChange={(e) => setEmbeddingModel(e.target.value)}
                    placeholder="e.g., text-embedding-ada-002"
                    className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
                  />
                </div>

                {/* Query Type */}
                <div>
                  <label className="block text-sm font-medium mb-1">Query Type</label>
                  <select
                    value={queryType}
                    onChange={(e) => setQueryType(e.target.value as 'HYBRID' | 'ANN')}
                    className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
                  >
                    <option value="HYBRID">HYBRID</option>
                    <option value="ANN">ANN</option>
                  </select>
                </div>

                {/* Number of Results */}
                <div>
                  <label className="block text-sm font-medium mb-1">Number of Results</label>
                  <input
                    type="number"
                    value={numResults}
                    onChange={(e) => setNumResults(parseInt(e.target.value) || 3)}
                    min="1"
                    max="100"
                    className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
                  />
                </div>

                {/* Score Threshold */}
                <div>
                  <label className="block text-sm font-medium mb-1">Score Threshold</label>
                  <input
                    type="number"
                    value={scoreThreshold}
                    onChange={(e) => setScoreThreshold(parseFloat(e.target.value) || 0.0)}
                    min="0"
                    max="1"
                    step="0.1"
                    className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
                  />
                </div>
              </>
            )}

            {/* Additional Parameters */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-sm font-medium">Additional Parameters</label>
                <button
                  onClick={addParameter}
                  className="px-2 py-1 bg-orange-500 text-white rounded text-xs hover:bg-orange-600"
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
              className="w-full px-3 py-2 bg-orange-600 text-white rounded hover:bg-orange-700"
            >
              Save
            </button>
          </div>
        ) : (
          <div className="space-y-2">
            {/* Configuration Display */}
            <div className="text-sm space-y-1">
              {retrieverType === 'UnstructuredRetrieve' && (
                <>
                  <div className="flex justify-between">
                    <span className="font-medium">Catalog:</span>
                    <span className="text-gray-600">{catalogName || 'Not set'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="font-medium">Schema:</span>
                    <span className="text-gray-600">{schemaName || 'Not set'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="font-medium">Index:</span>
                    <span className="text-gray-600">{indexName || 'Not set'}</span>
                  </div>
                  {embeddingModel && (
                    <div className="flex justify-between">
                      <span className="font-medium">Model:</span>
                      <span className="text-gray-600">{embeddingModel}</span>
                    </div>
                  )}
                  <div className="flex justify-between">
                    <span className="font-medium">Query Type:</span>
                    <span className="text-gray-600">{queryType}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="font-medium">Results:</span>
                    <span className="text-gray-600">{numResults}</span>
                  </div>
                  {scoreThreshold > 0 && (
                    <div className="flex justify-between">
                      <span className="font-medium">Threshold:</span>
                      <span className="text-gray-600">{scoreThreshold}</span>
                    </div>
                  )}
                </>
              )}
              
              {retrieverType === 'StructuredRetrieve' && (
                <div className="flex justify-between">
                  <span className="font-medium">Genie Space ID:</span>
                  <span className="text-gray-600">{genieSpaceId || 'Not set'}</span>
                </div>
              )}
            </div>

            {/* Additional Parameters Display */}
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

            {retrieverType === 'UnstructuredRetrieve' && !catalogName && !schemaName && !indexName && (
              <div className="text-sm text-gray-500 text-center py-2">
                Configure retriever settings
              </div>
            )}
            
            {retrieverType === 'StructuredRetrieve' && !genieSpaceId && (
              <div className="text-sm text-gray-500 text-center py-2">
                Configure Genie Space ID
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

export default RetrieverNode;