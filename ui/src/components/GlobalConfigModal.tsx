import React, { useState, useEffect } from 'react';
import { X, Check, AlertCircle, Plus, ChevronDown, ChevronUp, Trash2, Wrench, Database } from 'lucide-react';
import { useLMConfig } from '../contexts/LMConfigContext';
import { useGlobalTools, MCPServer, UCSchema, MCPHeader } from '../contexts/GlobalToolsContext';
import { useToast } from '../hooks/useToast';
import ToastContainer from './ToastContainer';

interface GlobalConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialTab?: 'lm' | 'mcp' | 'uc';
}

type TabType = 'lm' | 'mcp' | 'uc';

const PROVIDER_OPTIONS = [
  { value: 'databricks', label: 'Databricks', requiresKey: false },
  { value: 'openai', label: 'OpenAI', requiresKey: true },
  { value: 'anthropic', label: 'Anthropic', requiresKey: true },
  { value: 'gemini', label: 'Gemini (Google)', requiresKey: true },
  { value: 'custom', label: 'Custom Provider', requiresKey: true },
];

const GlobalConfigModal: React.FC<GlobalConfigModalProps> = ({ isOpen, onClose, initialTab = 'lm' }) => {
  const [activeTab, setActiveTab] = useState<TabType>(initialTab);
  const { toasts, removeToast, showSuccess, showWarning, showError } = useToast();
  const { globalToolsConfig } = useGlobalTools();
  
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <ToastContainer toasts={toasts} onRemove={removeToast} />
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-2xl font-semibold text-gray-900">Global Configuration</h2>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-100 rounded transition-colors"
          >
            <X size={24} className="text-gray-500" />
          </button>
        </div>

        {/* Tabs */}
        <div className="border-b border-gray-200">
          <nav className="flex space-x-8 px-6" aria-label="Tabs">
            <button
              onClick={() => setActiveTab('lm')}
              className={`
                py-4 px-1 inline-flex items-center gap-2 border-b-2 font-medium text-sm
                ${activeTab === 'lm'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }
              `}
            >
              <Database size={18} />
              Language Model
            </button>
            <button
              onClick={() => setActiveTab('mcp')}
              className={`
                py-4 px-1 inline-flex items-center gap-2 border-b-2 font-medium text-sm
                ${activeTab === 'mcp'
                  ? 'border-purple-500 text-purple-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }
              `}
            >
              <Wrench size={18} />
              MCP Tools
              {globalToolsConfig.mcpServers.length > 0 && (
                <span className="ml-2 px-2 py-0.5 bg-purple-100 text-purple-700 text-xs rounded-full">
                  {globalToolsConfig.mcpServers.length}
                </span>
              )}
            </button>
            <button
              onClick={() => setActiveTab('uc')}
              className={`
                py-4 px-1 inline-flex items-center gap-2 border-b-2 font-medium text-sm
                ${activeTab === 'uc'
                  ? 'border-green-500 text-green-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }
              `}
            >
              <Database size={18} />
              UC Functions
              {globalToolsConfig.ucSchemas.length > 0 && (
                <span className="ml-2 px-2 py-0.5 bg-green-100 text-green-700 text-xs rounded-full">
                  {globalToolsConfig.ucSchemas.length}
                </span>
              )}
            </button>
          </nav>
        </div>

        {/* Tab Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {activeTab === 'lm' && <LMConfigTab onClose={onClose} showSuccess={showSuccess} showWarning={showWarning} />}
          {activeTab === 'mcp' && <MCPToolsTab showSuccess={showSuccess} showWarning={showWarning} />}
          {activeTab === 'uc' && <UCFunctionsTab showSuccess={showSuccess} showWarning={showWarning} />}
        </div>
      </div>
    </div>
  );
};

// LM Configuration Tab Component
interface LMConfigTabProps {
  onClose: () => void;
  showSuccess: (title: string, message?: string, duration?: number) => void;
  showWarning: (title: string, message?: string, duration?: number) => void;
}

const LMConfigTab: React.FC<LMConfigTabProps> = ({ onClose, showSuccess, showWarning }) => {
  const { globalLMConfig, setGlobalLMConfig, availableProviders } = useLMConfig();
  const [selectedProvider, setSelectedProvider] = useState<string>('databricks');
  const [modelName, setModelName] = useState<string>('');

  useEffect(() => {
    if (globalLMConfig) {
      setSelectedProvider(globalLMConfig.provider);
      setModelName(globalLMConfig.modelName);
    } else {
      const defaultProvider = availableProviders['databricks']
        ? 'databricks'
        : Object.keys(availableProviders).find(p => availableProviders[p]) || 'databricks';
      setSelectedProvider(defaultProvider);
      setModelName('');
    }
  }, [globalLMConfig, availableProviders]);

  const handleSave = () => {
    if (!modelName.trim()) {
      showWarning('Model name required', 'Please enter a model name');
      return;
    }

    const fullModelName = `${selectedProvider}/${modelName.trim()}`;
    setGlobalLMConfig({
      provider: selectedProvider,
      modelName: fullModelName,
    });

    showSuccess('Configuration saved', 'Global LM configuration updated successfully');
    onClose();
  };

  const handleClear = () => {
    setGlobalLMConfig(null);
    setSelectedProvider('databricks');
    setModelName('');
  };

  const isProviderConfigured = (provider: string) => {
    return availableProviders[provider] === true;
  };

  const getProviderInfo = (provider: string) => {
    const option = PROVIDER_OPTIONS.find(opt => opt.value === provider);
    if (!option) return { label: provider, requiresKey: true };
    return option;
  };

  const isSelectedProviderConfigured = isProviderConfigured(selectedProvider);

  return (
    <div className="space-y-6">
      {/* Info Box */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start space-x-2">
          <AlertCircle size={18} className="text-blue-600 mt-0.5" />
          <div className="text-sm text-blue-800">
            <p className="font-medium mb-1">About Global LM Configuration</p>
            <p>
              Set a default model that will be auto-filled when creating new DSPy module nodes.
              You can still override the model at the node level if needed.
            </p>
            <p className="mt-2">
              <strong>Format:</strong> provider/model-name (e.g., openai/gpt-4, databricks/claude-sonnet-4-5)
            </p>
          </div>
        </div>
      </div>

      {/* Provider Selection */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Provider
        </label>
        <select
          value={selectedProvider}
          onChange={(e) => setSelectedProvider(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
          {PROVIDER_OPTIONS.map(option => (
            <option key={option.value} value={option.value}>
              {option.label}
              {!isProviderConfigured(option.value) && option.requiresKey ? ' (API key required)' : ''}
            </option>
          ))}
        </select>

        {/* Provider Status */}
        {!isSelectedProviderConfigured && getProviderInfo(selectedProvider).requiresKey && (
          <div className="mt-2 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
            <p className="text-sm text-yellow-800">
              ⚠️ This provider requires an API key to be set in environment variables.
            </p>
          </div>
        )}
      </div>

      {/* Model Name */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Model Name
        </label>
        <input
          type="text"
          value={modelName}
          onChange={(e) => setModelName(e.target.value)}
          placeholder="e.g., gpt-4, claude-3-5-sonnet-20241022"
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
        <p className="mt-1 text-xs text-gray-500">
          Enter just the model name. The full format will be: {selectedProvider}/{modelName || 'model-name'}
        </p>
      </div>

      {/* Current Configuration */}
      {globalLMConfig && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <div className="flex items-center space-x-2 mb-2">
            <Check size={18} className="text-green-600" />
            <span className="font-medium text-green-800">Current Configuration</span>
          </div>
          <p className="text-sm text-green-700 font-mono">
            {globalLMConfig.modelName}
          </p>
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center justify-between pt-4 border-t border-gray-200">
        <button
          onClick={handleClear}
          className="px-4 py-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
        >
          Clear Configuration
        </button>
        <div className="flex items-center space-x-3">
          <button
            onClick={onClose}
            className="px-6 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Save LM Config
          </button>
        </div>
      </div>
    </div>
  );
};

// MCP Tools Tab Component
interface MCPToolsTabProps {
  showSuccess: (title: string, message?: string, duration?: number) => void;
  showWarning: (title: string, message?: string, duration?: number) => void;
}

const MCPToolsTab: React.FC<MCPToolsTabProps> = ({ showSuccess, showWarning }) => {
  const { globalToolsConfig, updateMCPServers } = useGlobalTools();
  const [servers, setServers] = useState<MCPServer[]>(globalToolsConfig.mcpServers);
  const [newServerUrl, setNewServerUrl] = useState('');
  const [expandedServers, setExpandedServers] = useState<Set<string>>(new Set());
  const [loadingServers, setLoadingServers] = useState<Set<string>>(new Set());
  const [serverTools, setServerTools] = useState<Record<string, any[]>>({});
  const [serverErrors, setServerErrors] = useState<Record<string, string>>({});
  
  // Cache for tool data with TTL (5 minutes)
  const [functionCache, setFunctionCache] = useState<Record<string, {
    data: any[];
    timestamp: number;
  }>>({});
  const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

  useEffect(() => {
    setServers(globalToolsConfig.mcpServers);
  }, [globalToolsConfig.mcpServers]);

  const handleAddServer = async () => {
    if (!newServerUrl.trim()) {
      showWarning('Server URL required', 'Please enter a server URL');
      return;
    }

    const newServer: MCPServer = {
      url: newServerUrl.trim(),
      headers: [],
      selectedTools: [],
    };

    const updatedServers = [...servers, newServer];
    setServers(updatedServers);
    setNewServerUrl('');

    // Auto-expand so user can configure headers and load tools
    setExpandedServers(new Set([...Array.from(expandedServers), newServer.url]));
    showSuccess('Server added', 'MCP server added successfully. Configure headers and load tools below.');
  };

  const loadToolsFromServer = async (server: MCPServer, forceReload: boolean = false) => {
    const cacheKey = `mcp:${server.url}`;
    
    // Check cache first (unless force reload)
    if (!forceReload && functionCache[cacheKey]) {
      const cached = functionCache[cacheKey];
      if (Date.now() - cached.timestamp < CACHE_TTL) {
        setServerTools(prev => ({ ...prev, [server.url]: cached.data }));
        return;
      }
    }
    
    setLoadingServers(new Set([...Array.from(loadingServers), server.url]));
    
    // Clear previous error for this server
    setServerErrors(prev => {
      const newErrors = { ...prev };
      delete newErrors[server.url];
      return newErrors;
    });

    try {
      // Call backend API to list tools from MCP server
      const response = await fetch('/api/v1/config/mcp-tools', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          url: server.url,
          headers: server.headers || []
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to load tools');
      }

      const data = await response.json();
      setServerTools({
        ...serverTools,
        [server.url]: data.tools || [],
      });
    } catch (error) {
      console.error('Failed to load tools:', error);
      // Store error in state instead of showing alert
      setServerErrors(prev => ({
        ...prev,
        [server.url]: error instanceof Error ? error.message : 'Unknown error occurred'
      }));
    } finally {
      setLoadingServers(prev => {
        const newSet = new Set(prev);
        newSet.delete(server.url);
        return newSet;
      });
    }
  };

  const toggleServer = (url: string) => {
    const newExpanded = new Set(expandedServers);
    if (newExpanded.has(url)) {
      newExpanded.delete(url);
    } else {
      newExpanded.add(url);
      // Load tools if not loaded yet
      const server = servers.find(s => s.url === url);
      if (server && !serverTools[url]) {
        loadToolsFromServer(server);
      }
    }
    setExpandedServers(newExpanded);
  };

  const handleRemoveServer = (url: string) => {
    setServers(servers.filter(s => s.url !== url));
    setExpandedServers(prev => {
      const newSet = new Set(prev);
      newSet.delete(url);
      return newSet;
    });
    setServerTools(prev => {
      const newTools = { ...prev };
      delete newTools[url];
      return newTools;
    });
  };

  const handleToggleTool = (serverUrl: string, toolName: string) => {
    setServers(servers.map(server => {
      if (server.url === serverUrl) {
        const selectedTools = server.selectedTools.includes(toolName)
          ? server.selectedTools.filter(t => t !== toolName)
          : [...server.selectedTools, toolName];
        return { ...server, selectedTools };
      }
      return server;
    }));
  };

  const handleSelectAll = (serverUrl: string) => {
    const tools = serverTools[serverUrl] || [];
    setServers(servers.map(server => {
      if (server.url === serverUrl) {
        return { ...server, selectedTools: tools.map(t => t.name) };
      }
      return server;
    }));
  };

  const handleDeselectAll = (serverUrl: string) => {
    setServers(servers.map(server => {
      if (server.url === serverUrl) {
        return { ...server, selectedTools: [] };
      }
      return server;
    }));
  };

  const handleSave = () => {
    updateMCPServers(servers);
    showSuccess('Configuration saved', 'MCP servers saved successfully!');
  };

  return (
    <div className="space-y-6">
      {/* Info Box */}
      <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
        <div className="flex items-start space-x-2">
          <AlertCircle size={18} className="text-purple-600 mt-0.5" />
          <div className="text-sm text-purple-800">
            <p className="font-medium mb-1">About MCP Tool Configuration</p>
            <p>
              Configure MCP servers and select which tools to make available globally. These tools can then be
              used in ReAct nodes across all workflows.
            </p>
            <p className="mt-2">
              <strong>Note:</strong> Tools are loaded when you add a server. Select only the tools you want to expose.
            </p>
          </div>
        </div>
      </div>

      {/* Add MCP Server */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">Add MCP Server</label>
        <div className="flex gap-2">
          <input
            type="url"
            value={newServerUrl}
            onChange={(e) => setNewServerUrl(e.target.value)}
            placeholder="https://api.example.com/mcp"
            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            onKeyPress={(e) => {
              if (e.key === 'Enter') {
                handleAddServer();
              }
            }}
          />
          <button
            onClick={handleAddServer}
            className="px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors flex items-center gap-2"
          >
            <Plus size={18} />
            Add Server
          </button>
        </div>
      </div>

      {/* Server List */}
      <div className="space-y-3">
        {servers.map((server) => (
          <div key={server.url} className="border border-gray-200 rounded-lg overflow-hidden">
            {/* Server Header */}
            <div className="bg-gray-50 p-4 flex items-center justify-between">
              <div className="flex items-center gap-3 flex-1">
                <button
                  onClick={() => toggleServer(server.url)}
                  className="p-1 hover:bg-gray-200 rounded transition-colors"
                >
                  {expandedServers.has(server.url) ? (
                    <ChevronUp size={20} />
                  ) : (
                    <ChevronDown size={20} />
                  )}
                </button>
                <div>
                  <p className="font-mono text-sm font-medium text-gray-900">{server.url}</p>
                  <p className="text-xs text-gray-500">
                    {serverTools[server.url] ? (
                      `Tools (${server.selectedTools.length}/${serverTools[server.url].length} selected)`
                    ) : server.selectedTools.length > 0 ? (
                      `${server.selectedTools.length} tool${server.selectedTools.length !== 1 ? 's' : ''} selected`
                    ) : (
                      'Click "Load Tools" below'
                    )}
                  </p>
                </div>
              </div>
              <button
                onClick={() => handleRemoveServer(server.url)}
                className="p-2 text-red-600 hover:bg-red-50 rounded transition-colors"
                title="Remove server"
              >
                <Trash2 size={18} />
              </button>
            </div>

            {/* Expanded Content */}
            {expandedServers.has(server.url) && (
              <div className="p-4 border-t border-gray-200 space-y-4">
                {/* Headers Section */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="text-sm font-medium text-gray-700">Headers (for authentication)</label>
                    <button
                      onClick={() => {
                        const updatedServers = servers.map(s => {
                          if (s.url === server.url) {
                            return {
                              ...s,
                              headers: [...s.headers, { key: '', value: '', isSecret: false, envVarName: '' }]
                            };
                          }
                          return s;
                        });
                        setServers(updatedServers);
                      }}
                      className="flex items-center space-x-1 px-2 py-1 bg-purple-500 text-white rounded text-xs hover:bg-purple-600"
                    >
                      <Plus size={12} />
                      <span>Add Header</span>
                    </button>
                  </div>

                  {server.headers.length > 0 && (
                    <div className="space-y-2 max-h-48 overflow-y-auto">
                      {server.headers.map((header, index) => (
                        <div key={index} className="p-2 bg-gray-50 rounded border border-gray-200">
                          <div className="space-y-1">
                            <input
                              type="text"
                              value={header.key}
                              onChange={(e) => {
                                const updatedServers = servers.map(s => {
                                  if (s.url === server.url) {
                                    const newHeaders = [...s.headers];
                                    newHeaders[index] = { ...newHeaders[index], key: e.target.value };
                                    return { ...s, headers: newHeaders };
                                  }
                                  return s;
                                });
                                setServers(updatedServers);
                              }}
                              placeholder="Header key (e.g., Authorization)"
                              className="w-full px-2 py-1 border border-gray-300 rounded text-xs"
                            />
                            <input
                              type="text"
                              value={header.value}
                              onChange={(e) => {
                                const updatedServers = servers.map(s => {
                                  if (s.url === server.url) {
                                    const newHeaders = [...s.headers];
                                    newHeaders[index] = { ...newHeaders[index], value: e.target.value };
                                    return { ...s, headers: newHeaders };
                                  }
                                  return s;
                                });
                                setServers(updatedServers);
                              }}
                              placeholder={header.isSecret ? "Value (will use env var)" : "Header value (e.g., Bearer token123)"}
                              className="w-full px-2 py-1 border border-gray-300 rounded text-xs"
                              disabled={header.isSecret}
                            />
                            <div className="flex items-center space-x-2">
                              <label className="flex items-center space-x-1 text-xs">
                                <input
                                  type="checkbox"
                                  checked={header.isSecret}
                                  onChange={(e) => {
                                    const updatedServers = servers.map(s => {
                                      if (s.url === server.url) {
                                        const newHeaders = [...s.headers];
                                        newHeaders[index] = { ...newHeaders[index], isSecret: e.target.checked };
                                        return { ...s, headers: newHeaders };
                                      }
                                      return s;
                                    });
                                    setServers(updatedServers);
                                  }}
                                  className="rounded"
                                />
                                <span>Use secret (env var)</span>
                              </label>
                              {header.isSecret && (
                                <input
                                  type="text"
                                  value={header.envVarName || ''}
                                  onChange={(e) => {
                                    const updatedServers = servers.map(s => {
                                      if (s.url === server.url) {
                                        const newHeaders = [...s.headers];
                                        newHeaders[index] = { ...newHeaders[index], envVarName: e.target.value };
                                        return { ...s, headers: newHeaders };
                                      }
                                      return s;
                                    });
                                    setServers(updatedServers);
                                  }}
                                  placeholder="ENV_VAR_NAME"
                                  className="flex-1 px-2 py-1 border border-gray-300 rounded text-xs"
                                />
                              )}
                              <button
                                onClick={() => {
                                  const updatedServers = servers.map(s => {
                                    if (s.url === server.url) {
                                      return { ...s, headers: s.headers.filter((_, i) => i !== index) };
                                    }
                                    return s;
                                  });
                                  setServers(updatedServers);
                                }}
                                className="p-1 text-red-500 hover:bg-red-50 rounded"
                              >
                                <X size={14} />
                              </button>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                  
                  <button
                    onClick={() => loadToolsFromServer(server, serverTools[server.url] !== undefined)}
                    className="mt-2 w-full px-3 py-1.5 bg-purple-100 text-purple-700 rounded text-sm hover:bg-purple-200 transition-colors"
                  >
                    {serverTools[server.url] ? 'Reload Tools' : 'Load Tools'}
                  </button>
                </div>

                {/* Tools Section */}
                {serverErrors[server.url] ? (
                  <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                    <div className="flex items-start space-x-2">
                      <AlertCircle size={18} className="text-red-600 mt-0.5 flex-shrink-0" />
                      <div className="flex-1">
                        <p className="text-sm font-medium text-red-800">Failed to load tools</p>
                        <p className="text-xs text-red-600 mt-1">{serverErrors[server.url]}</p>
                        <button
                          onClick={() => loadToolsFromServer(server, true)}
                          className="mt-2 text-xs text-red-700 hover:text-red-800 font-medium underline"
                        >
                          Try again
                        </button>
                      </div>
                    </div>
                  </div>
                ) : loadingServers.has(server.url) ? (
                  <div className="text-center py-8 text-gray-500">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600 mx-auto mb-2"></div>
                    Loading tools...
                  </div>
                ) : serverTools[server.url] ? (
                  <>
                    <div className="flex items-center justify-between mb-3">
                      <p className="text-sm font-medium text-gray-700">
                        Tools ({server.selectedTools.length}/{serverTools[server.url]?.length || 0} selected)
                      </p>
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleSelectAll(server.url)}
                          className="text-xs text-purple-600 hover:text-purple-700 font-medium"
                        >
                          Select All
                        </button>
                        <span className="text-gray-300">|</span>
                        <button
                          onClick={() => handleDeselectAll(server.url)}
                          className="text-xs text-purple-600 hover:text-purple-700 font-medium"
                        >
                          Deselect All
                        </button>
                      </div>
                    </div>

                    <div className="space-y-2 max-h-64 overflow-y-auto">
                      {(serverTools[server.url] || []).map((tool) => (
                        <label
                          key={tool.name}
                          className="flex items-start space-x-3 p-3 hover:bg-gray-50 rounded-lg cursor-pointer"
                        >
                          <input
                            type="checkbox"
                            checked={server.selectedTools.includes(tool.name)}
                            onChange={() => handleToggleTool(server.url, tool.name)}
                            className="mt-1 rounded border-gray-300 text-purple-600 focus:ring-purple-500"
                          />
                          <div className="flex-1">
                            <p className="text-sm font-medium text-gray-900">{tool.name}</p>
                            <p className="text-xs text-gray-500">{tool.description}</p>
                          </div>
                        </label>
                      ))}
                    </div>
                  </>
                ) : (
                  <div className="text-center py-8 text-gray-400">
                    <p className="text-sm">Configure headers (if needed) and click "Load Tools" to fetch available tools</p>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}

        {servers.length === 0 && (
          <div className="text-center py-12 text-gray-500">
            <Wrench size={48} className="mx-auto mb-3 text-gray-300" />
            <p>No MCP servers configured</p>
            <p className="text-sm mt-1">Add a server above to get started</p>
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="flex justify-between pt-4 border-t border-gray-200">
        <button
          onClick={() => setServers([])}
          className="px-4 py-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
        >
          Clear MCP Servers
        </button>
        <button
          onClick={handleSave}
          className="px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
        >
          Save MCP Servers
        </button>
      </div>
    </div>
  );
};

// UC Functions Tab Component
interface UCFunctionsTabProps {
  showSuccess: (title: string, message?: string, duration?: number) => void;
  showWarning: (title: string, message?: string, duration?: number) => void;
}

const UCFunctionsTab: React.FC<UCFunctionsTabProps> = ({ showSuccess, showWarning }) => {
  const { globalToolsConfig, updateUCSchemas } = useGlobalTools();
  const [schemas, setSchemas] = useState<UCSchema[]>(globalToolsConfig.ucSchemas);
  const [newCatalog, setNewCatalog] = useState('');
  const [newSchema, setNewSchema] = useState('');
  const [expandedSchemas, setExpandedSchemas] = useState<Set<string>>(new Set());
  const [loadingSchemas, setLoadingSchemas] = useState<Set<string>>(new Set());
  const [schemaFunctions, setSchemaFunctions] = useState<Record<string, any[]>>({});
  const [schemaErrors, setSchemaErrors] = useState<Record<string, string>>({});
  
  // Cache for function data with TTL (5 minutes)
  const [functionCache, setFunctionCache] = useState<Record<string, {
    data: any[];
    timestamp: number;
  }>>({});
  const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

  useEffect(() => {
    setSchemas(globalToolsConfig.ucSchemas);
  }, [globalToolsConfig.ucSchemas]);

  const handleAddSchema = async () => {
    if (!newCatalog.trim() || !newSchema.trim()) {
      showWarning('Catalog and schema required', 'Please enter both catalog and schema');
      return;
    }

    const schemaKey = `${newCatalog.trim()}.${newSchema.trim()}`;
    
    // Check if already exists
    if (schemas.some(s => `${s.catalog}.${s.schema}` === schemaKey)) {
      showWarning('Schema already added', 'This schema is already in your configuration');
      return;
    }

    const newSchemaConfig: UCSchema = {
      catalog: newCatalog.trim(),
      schema: newSchema.trim(),
      selectedFunctions: [],
    };

    const updatedSchemas = [...schemas, newSchemaConfig];
    setSchemas(updatedSchemas);
    setNewCatalog('');
    setNewSchema('');

    // Auto-expand and load functions
    setExpandedSchemas(new Set([...Array.from(expandedSchemas), schemaKey]));
    await loadFunctionsFromSchema(newSchemaConfig);
    showSuccess('Schema added', 'Unity Catalog schema added successfully. Loading functions...');
  };

  const loadFunctionsFromSchema = async (schema: UCSchema, forceReload: boolean = false) => {
    const schemaKey = `${schema.catalog}.${schema.schema}`;
    const cacheKey = `uc:${schemaKey}`;
    
    // Check cache first (unless force reload)
    if (!forceReload && functionCache[cacheKey]) {
      const cached = functionCache[cacheKey];
      if (Date.now() - cached.timestamp < CACHE_TTL) {
        setSchemaFunctions(prev => ({ ...prev, [schemaKey]: cached.data }));
        return;
      }
    }
    
    setLoadingSchemas(new Set([...Array.from(loadingSchemas), schemaKey]));
    
    // Clear previous error for this schema
    setSchemaErrors(prev => {
      const newErrors = { ...prev };
      delete newErrors[schemaKey];
      return newErrors;
    });

    try {
      // Call backend API to list functions from UC schema
      const response = await fetch('/api/v1/config/uc-functions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          catalog: schema.catalog,
          schema: schema.schema,
          force_reload: forceReload
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to load functions');
      }

      const data = await response.json();
      const functions = data.functions || [];
      
      setSchemaFunctions({
        ...schemaFunctions,
        [schemaKey]: functions,
      });
      
      // Update cache
      setFunctionCache(prev => ({
        ...prev,
        [cacheKey]: { data: functions, timestamp: Date.now() }
      }));
    } catch (error) {
      console.error('Failed to load functions:', error);
      // Store error in state instead of showing alert
      setSchemaErrors(prev => ({
        ...prev,
        [schemaKey]: error instanceof Error ? error.message : 'Unknown error occurred'
      }));
    } finally {
      setLoadingSchemas(prev => {
        const newSet = new Set(prev);
        newSet.delete(schemaKey);
        return newSet;
      });
    }
  };

  const toggleSchema = (schemaKey: string) => {
    const newExpanded = new Set(expandedSchemas);
    if (newExpanded.has(schemaKey)) {
      newExpanded.delete(schemaKey);
    } else {
      newExpanded.add(schemaKey);
      // Don't auto-load - let user click "Load Functions" button
      // This gives more control and clarity
    }
    setExpandedSchemas(newExpanded);
  };

  const handleRemoveSchema = (schemaKey: string) => {
    setSchemas(schemas.filter(s => `${s.catalog}.${s.schema}` !== schemaKey));
    setExpandedSchemas(prev => {
      const newSet = new Set(prev);
      newSet.delete(schemaKey);
      return newSet;
    });
    setSchemaFunctions(prev => {
      const newFuncs = { ...prev };
      delete newFuncs[schemaKey];
      return newFuncs;
    });
  };

  const handleToggleFunction = (schemaKey: string, functionName: string) => {
    setSchemas(schemas.map(schema => {
      if (`${schema.catalog}.${schema.schema}` === schemaKey) {
        const selectedFunctions = schema.selectedFunctions.includes(functionName)
          ? schema.selectedFunctions.filter(f => f !== functionName)
          : [...schema.selectedFunctions, functionName];
        return { ...schema, selectedFunctions };
      }
      return schema;
    }));
  };

  const handleSelectAll = (schemaKey: string) => {
    const functions = schemaFunctions[schemaKey] || [];
    setSchemas(schemas.map(schema => {
      if (`${schema.catalog}.${schema.schema}` === schemaKey) {
        return { ...schema, selectedFunctions: functions.map(f => f.name) };
      }
      return schema;
    }));
  };

  const handleDeselectAll = (schemaKey: string) => {
    setSchemas(schemas.map(schema => {
      if (`${schema.catalog}.${schema.schema}` === schemaKey) {
        return { ...schema, selectedFunctions: [] };
      }
      return schema;
    }));
  };

  const handleSave = () => {
    updateUCSchemas(schemas);
    showSuccess('Configuration saved', 'UC schemas saved successfully!');
  };

  return (
    <div className="space-y-6">
      {/* Info Box */}
      <div className="bg-green-50 border border-green-200 rounded-lg p-4">
        <div className="flex items-start space-x-2">
          <AlertCircle size={18} className="text-green-600 mt-0.5" />
          <div className="text-sm text-green-800">
            <p className="font-medium mb-1">About UC Function Configuration</p>
            <p>
              Configure Unity Catalog schemas and select which functions to make available globally. These functions
              can then be used in ReAct nodes across all workflows.
            </p>
            <p className="mt-2">
              <strong>Note:</strong> Functions are loaded when you add a schema. Select only the functions you want to expose.
            </p>
          </div>
        </div>
      </div>

      {/* Add UC Schema */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">Add UC Schema</label>
        <div className="flex gap-2">
          <input
            type="text"
            value={newCatalog}
            onChange={(e) => setNewCatalog(e.target.value)}
            placeholder="Catalog (e.g., main)"
            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
          />
          <input
            type="text"
            value={newSchema}
            onChange={(e) => setNewSchema(e.target.value)}
            placeholder="Schema (e.g., ml_functions)"
            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
            onKeyPress={(e) => {
              if (e.key === 'Enter') {
                handleAddSchema();
              }
            }}
          />
          <button
            onClick={handleAddSchema}
            className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors flex items-center gap-2"
          >
            <Plus size={18} />
            Add Schema
          </button>
        </div>
      </div>

      {/* Schema List */}
      <div className="space-y-3">
        {schemas.map((schema) => {
          const schemaKey = `${schema.catalog}.${schema.schema}`;
          return (
            <div key={schemaKey} className="border border-gray-200 rounded-lg overflow-hidden">
              {/* Schema Header */}
              <div className="bg-gray-50 p-4 flex items-center justify-between">
                <div className="flex items-center gap-3 flex-1">
                  <button
                    onClick={() => toggleSchema(schemaKey)}
                    className="p-1 hover:bg-gray-200 rounded transition-colors"
                  >
                    {expandedSchemas.has(schemaKey) ? (
                      <ChevronUp size={20} />
                    ) : (
                      <ChevronDown size={20} />
                    )}
                  </button>
                  <div>
                    <p className="font-mono text-sm font-medium text-gray-900">{schemaKey}</p>
                  <div className="flex items-center justify-between">
                    <p className="text-xs text-gray-500">
                      {schemaFunctions[schemaKey] ? (
                        `Functions (${schema.selectedFunctions.length}/${schemaFunctions[schemaKey].length} selected)`
                      ) : schema.selectedFunctions.length > 0 ? (
                        `${schema.selectedFunctions.length} function${schema.selectedFunctions.length !== 1 ? 's' : ''} selected`
                      ) : (
                        'Click "Load Functions" below'
                      )}
                    </p>
                  </div>
                  </div>
                </div>
                <button
                  onClick={() => handleRemoveSchema(schemaKey)}
                  className="p-2 text-red-600 hover:bg-red-50 rounded transition-colors"
                  title="Remove schema"
                >
                  <Trash2 size={18} />
                </button>
              </div>

              {/* Expanded Content */}
              {expandedSchemas.has(schemaKey) && (
                <div className="p-4 border-t border-gray-200">
                  {/* Load/Reload Functions Button */}
                  <button
                    onClick={() => loadFunctionsFromSchema(schema, schemaFunctions[schemaKey] !== undefined)}
                    className="w-full px-3 py-1.5 bg-green-100 text-green-700 rounded text-sm hover:bg-green-200 transition-colors mb-3"
                    disabled={loadingSchemas.has(schemaKey)}
                  >
                    {loadingSchemas.has(schemaKey) 
                      ? 'Loading...' 
                      : schemaFunctions[schemaKey] 
                        ? 'Reload Functions' 
                        : 'Load Functions'}
                  </button>

                  {schemaErrors[schemaKey] ? (
                    <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                      <div className="flex items-start space-x-2">
                        <AlertCircle size={18} className="text-red-600 mt-0.5 flex-shrink-0" />
                        <div className="flex-1">
                          <p className="text-sm font-medium text-red-800">Failed to load functions</p>
                          <p className="text-xs text-red-600 mt-1">{schemaErrors[schemaKey]}</p>
                          <button
                            onClick={() => loadFunctionsFromSchema(schema, true)}
                            className="mt-2 text-xs text-red-700 hover:text-red-800 font-medium underline"
                          >
                            Try again
                          </button>
                        </div>
                      </div>
                    </div>
                  ) : loadingSchemas.has(schemaKey) ? (
                    <div className="text-center py-8 text-gray-500">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-600 mx-auto mb-2"></div>
                      Loading functions...
                    </div>
                  ) : schemaFunctions[schemaKey] ? (
                    <>
                      <div className="flex items-center justify-between mb-3">
                        <p className="text-sm font-medium text-gray-700">
                          Functions ({schema.selectedFunctions.length}/{schemaFunctions[schemaKey].length} selected)
                        </p>
                        <div className="flex gap-2">
                          <button
                            onClick={() => handleSelectAll(schemaKey)}
                            className="text-xs text-green-600 hover:text-green-700 font-medium"
                          >
                            Select All
                          </button>
                          <span className="text-gray-300">|</span>
                          <button
                            onClick={() => handleDeselectAll(schemaKey)}
                            className="text-xs text-green-600 hover:text-green-700 font-medium"
                          >
                            Deselect All
                          </button>
                        </div>
                      </div>

                      <div className="space-y-2 max-h-64 overflow-y-auto">
                        {(schemaFunctions[schemaKey] || []).map((func) => (
                          <label
                            key={func.name}
                            className="flex items-start space-x-3 p-3 hover:bg-gray-50 rounded-lg cursor-pointer"
                          >
                            <input
                              type="checkbox"
                              checked={schema.selectedFunctions.includes(func.name)}
                              onChange={() => handleToggleFunction(schemaKey, func.name)}
                              className="mt-1 rounded border-gray-300 text-green-600 focus:ring-green-500"
                            />
                            <div className="flex-1">
                              <p className="text-sm font-medium text-gray-900">{func.name}</p>
                              <p className="text-xs text-gray-500">{func.description}</p>
                            </div>
                          </label>
                        ))}
                      </div>
                    </>
                  ) : (
                    <div className="text-center py-8 text-gray-400">
                      <p className="text-sm">Click the chevron above to load functions from this schema</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}

        {schemas.length === 0 && (
          <div className="text-center py-12 text-gray-500">
            <Database size={48} className="mx-auto mb-3 text-gray-300" />
            <p>No UC schemas configured</p>
            <p className="text-sm mt-1">Add a schema above to get started</p>
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="flex justify-between pt-4 border-t border-gray-200">
        <button
          onClick={() => setSchemas([])}
          className="px-4 py-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
        >
          Clear UC Schemas
        </button>
        <button
          onClick={handleSave}
          className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
        >
          Save UC Schemas
        </button>
      </div>
    </div>
  );
};

export default GlobalConfigModal;

