/**
 * Custom hook for managing cached tool/function data with TTL
 */
import { useState, useCallback } from 'react';

interface CacheEntry<T> {
  data: T;
  timestamp: number;
}

interface UseToolCacheResult<T> {
  getCached: (key: string) => T | null;
  setCache: (key: string, data: T) => void;
  clearCache: (key?: string) => void;
}


export function useToolCache<T = any[]>(ttlMs: number = 5 * 60 * 1000): UseToolCacheResult<T> {
  const [cache, setCache] = useState<Record<string, CacheEntry<T>>>({});

  const getCached = useCallback((key: string): T | null => {
    const cached = cache[key];
    if (!cached) return null;

    const age = Date.now() - cached.timestamp;
    if (age >= ttlMs) {
      // Cache expired
      return null;
    }

    return cached.data;
  }, [cache, ttlMs]);

  const setCacheEntry = useCallback((key: string, data: T) => {
    setCache(prev => ({
      ...prev,
      [key]: { data, timestamp: Date.now() }
    }));
  }, []);

  const clearCache = useCallback((key?: string) => {
    if (key) {
      setCache(prev => {
        const newCache = { ...prev };
        delete newCache[key];
        return newCache;
      });
    } else {
      setCache({});
    }
  }, []);

  return {
    getCached,
    setCache: setCacheEntry,
    clearCache
  };
}

