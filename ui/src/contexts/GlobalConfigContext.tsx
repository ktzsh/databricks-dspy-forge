import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { loadFromLocalStorage, saveToLocalStorage, removeFromLocalStorage } from '../utils/storage';

// LM Configuration types
export interface LMConfig {
  provider: string;
  modelName: string;
}

// Tools Configuration types
export interface MCPHeader {
  key: string;
  value: string;
  isSecret: boolean;
  envVarName?: string;
}

export interface MCPServer {
  url: string;
  headers: MCPHeader[];
  selectedTools: string[];
}

export interface UCSchema {
  catalog: string;
  schema: string;
  selectedFunctions: string[];
}

export interface GlobalToolsConfig {
  mcpServers: MCPServer[];
  ucSchemas: UCSchema[];
}

// Combined context type
export interface GlobalConfigContextType {
  // LM Config
  globalLMConfig: LMConfig | null;
  setGlobalLMConfig: (config: LMConfig | null) => void;
  availableProviders: Record<string, boolean>;
  refreshProviderStatus: () => Promise<void>;
  
  // Tools Config
  globalToolsConfig: GlobalToolsConfig;
  setGlobalToolsConfig: (config: GlobalToolsConfig) => void;
  updateMCPServers: (servers: MCPServer[]) => void;
  updateUCSchemas: (schemas: UCSchema[]) => void;
}

const GlobalConfigContext = createContext<GlobalConfigContextType | undefined>(undefined);

const LM_CONFIG_STORAGE_KEY = 'dspy-forge-lm-config';
const GLOBAL_TOOLS_STORAGE_KEY = 'dspy-forge-global-tools';

const DEFAULT_TOOLS_CONFIG: GlobalToolsConfig = {
  mcpServers: [],
  ucSchemas: [],
};

export const GlobalConfigProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  // LM Config state
  const [globalLMConfig, setGlobalLMConfigState] = useState<LMConfig | null>(null);
  const [availableProviders, setAvailableProviders] = useState<Record<string, boolean>>({});
  
  // Tools Config state
  const [globalToolsConfig, setGlobalToolsConfigState] = useState<GlobalToolsConfig>(DEFAULT_TOOLS_CONFIG);

  // Fetch LM provider availability from backend (server-side API keys status)
  const refreshProviderStatus = async () => {
    try {
      const response = await fetch('/api/v1/config/lm-providers');
      if (response.ok) {
        const providers = await response.json();
        setAvailableProviders(providers);
      }
    } catch (error) {
      console.error('Failed to fetch provider status:', error);
    }
  };

  // Load configs from localStorage and fetch provider status on mount
  useEffect(() => {
    // Load LM config from localStorage
    const lmConfig = loadFromLocalStorage<LMConfig | null>(LM_CONFIG_STORAGE_KEY, null);
    if (lmConfig) {
      setGlobalLMConfigState(lmConfig);
    }

    // Load Tools config from localStorage
    const toolsConfig = loadFromLocalStorage<GlobalToolsConfig>(GLOBAL_TOOLS_STORAGE_KEY, DEFAULT_TOOLS_CONFIG);
    setGlobalToolsConfigState(toolsConfig);

    // Fetch provider status from backend on mount
    refreshProviderStatus();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const setGlobalLMConfig = (config: LMConfig | null) => {
    setGlobalLMConfigState(config);
    if (config) {
      saveToLocalStorage(LM_CONFIG_STORAGE_KEY, config);
    } else {
      removeFromLocalStorage(LM_CONFIG_STORAGE_KEY);
    }
  };

  const setGlobalToolsConfig = (config: GlobalToolsConfig) => {
    setGlobalToolsConfigState(config);
    saveToLocalStorage(GLOBAL_TOOLS_STORAGE_KEY, config);
  };

  const updateMCPServers = (servers: MCPServer[]) => {
    const newConfig = {
      ...globalToolsConfig,
      mcpServers: servers,
    };
    setGlobalToolsConfig(newConfig);
  };

  const updateUCSchemas = (schemas: UCSchema[]) => {
    const newConfig = {
      ...globalToolsConfig,
      ucSchemas: schemas,
    };
    setGlobalToolsConfig(newConfig);
  };

  return (
    <GlobalConfigContext.Provider
      value={{
        globalLMConfig,
        setGlobalLMConfig,
        availableProviders,
        refreshProviderStatus,
        globalToolsConfig,
        setGlobalToolsConfig,
        updateMCPServers,
        updateUCSchemas,
      }}
    >
      {children}
    </GlobalConfigContext.Provider>
  );
};

export const useGlobalConfig = (): GlobalConfigContextType => {
  const context = useContext(GlobalConfigContext);
  if (context === undefined) {
    throw new Error('useGlobalConfig must be used within a GlobalConfigProvider');
  }
  return context;
};

