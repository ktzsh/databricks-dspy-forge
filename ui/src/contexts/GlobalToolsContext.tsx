import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';

export interface MCPHeader {
  key: string;
  value: string;
  isSecret: boolean;
  envVarName?: string;
}

export interface MCPServer {
  url: string;
  headers: MCPHeader[];
  selectedTools: string[]; // List of tool names selected to expose globally
}

export interface UCSchema {
  catalog: string;
  schema: string;
  selectedFunctions: string[]; // List of function names selected to expose globally
}

export interface GlobalToolsConfig {
  mcpServers: MCPServer[];
  ucSchemas: UCSchema[];
}

interface GlobalToolsContextType {
  globalToolsConfig: GlobalToolsConfig;
  setGlobalToolsConfig: (config: GlobalToolsConfig) => void;
  updateMCPServers: (servers: MCPServer[]) => void;
  updateUCSchemas: (schemas: UCSchema[]) => void;
}

const GlobalToolsContext = createContext<GlobalToolsContextType | undefined>(undefined);

const GLOBAL_TOOLS_STORAGE_KEY = 'dspy-forge-global-tools';

const DEFAULT_CONFIG: GlobalToolsConfig = {
  mcpServers: [],
  ucSchemas: [],
};

export const GlobalToolsProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [globalToolsConfig, setGlobalToolsConfigState] = useState<GlobalToolsConfig>(DEFAULT_CONFIG);

  // Load config from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem(GLOBAL_TOOLS_STORAGE_KEY);
    if (stored) {
      try {
        const config = JSON.parse(stored);
        setGlobalToolsConfigState(config);
      } catch (e) {
        console.error('Failed to parse stored global tools config:', e);
      }
    }
  }, []);

  const setGlobalToolsConfig = (config: GlobalToolsConfig) => {
    setGlobalToolsConfigState(config);
    localStorage.setItem(GLOBAL_TOOLS_STORAGE_KEY, JSON.stringify(config));
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
    <GlobalToolsContext.Provider
      value={{
        globalToolsConfig,
        setGlobalToolsConfig,
        updateMCPServers,
        updateUCSchemas,
      }}
    >
      {children}
    </GlobalToolsContext.Provider>
  );
};

export const useGlobalTools = () => {
  const context = useContext(GlobalToolsContext);
  if (context === undefined) {
    throw new Error('useGlobalTools must be used within a GlobalToolsProvider');
  }
  return context;
};

