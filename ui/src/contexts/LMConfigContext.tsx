import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';

export interface LMConfig {
  provider: string;
  modelName: string;
}

interface LMConfigContextType {
  globalLMConfig: LMConfig | null;
  setGlobalLMConfig: (config: LMConfig | null) => void;
  availableProviders: Record<string, boolean>;
  refreshProviderStatus: () => Promise<void>;
}

const LMConfigContext = createContext<LMConfigContextType | undefined>(undefined);

const LM_CONFIG_STORAGE_KEY = 'dspy-forge-lm-config';

export const LMConfigProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [globalLMConfig, setGlobalLMConfigState] = useState<LMConfig | null>(null);
  const [availableProviders, setAvailableProviders] = useState<Record<string, boolean>>({});

  // Load config from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem(LM_CONFIG_STORAGE_KEY);
    if (stored) {
      try {
        const config = JSON.parse(stored);
        setGlobalLMConfigState(config);
      } catch (e) {
        console.error('Failed to parse stored LM config:', e);
      }
    }

    // Fetch available providers from backend
    refreshProviderStatus();
  }, []);

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

  const setGlobalLMConfig = (config: LMConfig | null) => {
    setGlobalLMConfigState(config);
    if (config) {
      localStorage.setItem(LM_CONFIG_STORAGE_KEY, JSON.stringify(config));
    } else {
      localStorage.removeItem(LM_CONFIG_STORAGE_KEY);
    }
  };

  return (
    <LMConfigContext.Provider
      value={{
        globalLMConfig,
        setGlobalLMConfig,
        availableProviders,
        refreshProviderStatus,
      }}
    >
      {children}
    </LMConfigContext.Provider>
  );
};

export const useLMConfig = () => {
  const context = useContext(LMConfigContext);
  if (context === undefined) {
    throw new Error('useLMConfig must be used within an LMConfigProvider');
  }
  return context;
};
