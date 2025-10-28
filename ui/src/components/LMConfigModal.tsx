import React, { useState, useEffect } from 'react';
import { X, Check, AlertCircle } from 'lucide-react';
import { useLMConfig } from '../contexts/LMConfigContext';
import { useToast } from '../hooks/useToast';
import ToastContainer from './ToastContainer';

interface LMConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const PROVIDER_OPTIONS = [
  { value: 'databricks', label: 'Databricks', requiresKey: false },
  { value: 'openai', label: 'OpenAI', requiresKey: true },
  { value: 'anthropic', label: 'Anthropic', requiresKey: true },
  { value: 'gemini', label: 'Gemini (Google)', requiresKey: true },
  { value: 'custom', label: 'Custom Provider', requiresKey: true },
];

const LMConfigModal: React.FC<LMConfigModalProps> = ({ isOpen, onClose }) => {
  const { globalLMConfig, setGlobalLMConfig, availableProviders } = useLMConfig();
  const { toasts, removeToast, showSuccess, showWarning } = useToast();
  const [selectedProvider, setSelectedProvider] = useState<string>('databricks');
  const [modelName, setModelName] = useState<string>('');

  useEffect(() => {
    if (globalLMConfig) {
      setSelectedProvider(globalLMConfig.provider);
      setModelName(globalLMConfig.modelName);
    } else {
      // Default to databricks if available, otherwise first available provider
      const defaultProvider = availableProviders['databricks']
        ? 'databricks'
        : Object.keys(availableProviders).find(p => availableProviders[p]) || 'databricks';
      setSelectedProvider(defaultProvider);
      setModelName('');
    }
  }, [globalLMConfig, availableProviders]);

  if (!isOpen) return null;

  const handleSave = () => {
    if (!modelName.trim()) {
      showWarning('Model name required', 'Please enter a model name');
      return;
    }

    // Format: provider/model
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
    onClose();
  };

  const isProviderConfigured = (provider: string) => {
    return availableProviders[provider] === true;
  };

  const getProviderInfo = (provider: string) => {
    const providerConfig = PROVIDER_OPTIONS.find(p => p.value === provider);
    if (!providerConfig) return null;

    const isConfigured = isProviderConfigured(provider);

    if (providerConfig.value === 'databricks') {
      return {
        statusText: isConfigured ? 'Configured' : 'Not configured',
        statusColor: isConfigured ? 'text-green-600' : 'text-yellow-600',
        helperText: isConfigured
          ? 'Databricks credentials are configured'
          : 'Databricks credentials not found. Configure DATABRICKS_CONFIG_PROFILE or DATABRICKS_HOST/TOKEN in .env',
      };
    }

    if (!providerConfig.requiresKey) {
      return {
        statusText: 'Available',
        statusColor: 'text-green-600',
        helperText: '',
      };
    }

    return {
      statusText: isConfigured ? 'API Key Configured' : 'API Key Required',
      statusColor: isConfigured ? 'text-green-600' : 'text-red-600',
      helperText: isConfigured
        ? `${providerConfig.label} API key is configured on the server`
        : `${providerConfig.label} API key not found. Configure ${provider.toUpperCase()}_API_KEY in .env on the server`,
    };
  };

  const selectedProviderInfo = getProviderInfo(selectedProvider);
  const isSelectedProviderConfigured = isProviderConfigured(selectedProvider);

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <ToastContainer toasts={toasts} onRemove={removeToast} />
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">Global LM Configuration</h2>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-100 rounded transition-colors"
          >
            <X size={20} className="text-gray-500" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-6">
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
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
            >
              {PROVIDER_OPTIONS.map((provider) => {
                const configured = isProviderConfigured(provider.value);
                return (
                  <option key={provider.value} value={provider.value}>
                    {provider.label}
                    {provider.requiresKey && !configured ? ' (API Key Required)' : ''}
                    {configured ? ' ✓' : ''}
                  </option>
                );
              })}
            </select>

            {/* Provider Status */}
            {selectedProviderInfo && (
              <div className="mt-2 space-y-1">
                <div className="flex items-center space-x-2">
                  {isSelectedProviderConfigured ? (
                    <Check size={16} className={selectedProviderInfo.statusColor} />
                  ) : (
                    <AlertCircle size={16} className={selectedProviderInfo.statusColor} />
                  )}
                  <span className={`text-sm font-medium ${selectedProviderInfo.statusColor}`}>
                    {selectedProviderInfo.statusText}
                  </span>
                </div>
                {selectedProviderInfo.helperText && (
                  <p className="text-xs text-gray-600 ml-6">
                    {selectedProviderInfo.helperText}
                  </p>
                )}
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
              placeholder={
                selectedProvider === 'databricks'
                  ? 'e.g., databricks-claude-sonnet-4-5'
                  : selectedProvider === 'openai'
                  ? 'e.g., gpt-4'
                  : selectedProvider === 'anthropic'
                  ? 'e.g., claude-3-sonnet'
                  : selectedProvider === 'gemini'
                  ? 'e.g., gemini-pro'
                  : 'e.g., my-model'
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
            />
            <p className="mt-1 text-xs text-gray-500">
              Enter just the model name. The full format will be: <strong>{selectedProvider}/{modelName || 'model-name'}</strong>
            </p>
          </div>

          {/* Current Config Display */}
          {globalLMConfig && (
            <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
              <p className="text-sm font-medium text-gray-700 mb-1">Current Global Configuration:</p>
              <p className="text-sm text-gray-900 font-mono">{globalLMConfig.modelName}</p>
            </div>
          )}

          {/* Warning for unconfigured providers */}
          {!isSelectedProviderConfigured && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <div className="flex items-start space-x-2">
                <AlertCircle size={18} className="text-yellow-600 mt-0.5" />
                <div className="text-sm text-yellow-800">
                  <p className="font-medium">Provider Not Configured</p>
                  <p className="mt-1">
                    This provider requires API keys to be configured on the backend server.
                    Models using this provider will fail at runtime unless the keys are configured.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-between p-6 border-t border-gray-200">
          <button
            onClick={handleClear}
            className="px-4 py-2 text-red-700 bg-red-50 rounded-md hover:bg-red-100 transition-colors"
          >
            Clear Config
          </button>
          <div className="flex space-x-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={!modelName.trim()}
              className="px-4 py-2 bg-emerald-600 text-white rounded-md hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Save
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LMConfigModal;
