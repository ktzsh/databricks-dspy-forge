/**
 * Custom hook for managing expandable list state (expand/collapse, loading, errors)
 */
import { useState, useCallback } from 'react';

interface UseExpandableListResult<T> {
  expandedItems: Set<string>;
  loadingItems: Set<string>;
  itemData: Record<string, T>;
  errors: Record<string, string>;
  toggleItem: (key: string) => void;
  setItemLoading: (key: string, loading: boolean) => void;
  setItemData: (key: string, data: T) => void;
  setItemError: (key: string, error: string | null) => void;
  removeItem: (key: string) => void;
  isExpanded: (key: string) => boolean;
  isLoading: (key: string) => boolean;
  getError: (key: string) => string | null;
  getData: (key: string) => T | undefined;
}

/**
 * Hook for managing expandable list state with loading and error tracking
 */
export function useExpandableList<T = any[]>(): UseExpandableListResult<T> {
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());
  const [loadingItems, setLoadingItems] = useState<Set<string>>(new Set());
  const [itemData, setItemData] = useState<Record<string, T>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});

  const toggleItem = useCallback((key: string) => {
    setExpandedItems(prev => {
      const newSet = new Set(prev);
      if (newSet.has(key)) {
        newSet.delete(key);
      } else {
        newSet.add(key);
      }
      return newSet;
    });
  }, []);

  const setItemLoading = useCallback((key: string, loading: boolean) => {
    setLoadingItems(prev => {
      const newSet = new Set(prev);
      if (loading) {
        newSet.add(key);
      } else {
        newSet.delete(key);
      }
      return newSet;
    });
  }, []);

  const setItemDataCallback = useCallback((key: string, data: T) => {
    setItemData(prev => ({
      ...prev,
      [key]: data
    }));
  }, []);

  const setItemError = useCallback((key: string, error: string | null) => {
    setErrors(prev => {
      const newErrors = { ...prev };
      if (error) {
        newErrors[key] = error;
      } else {
        delete newErrors[key];
      }
      return newErrors;
    });
  }, []);

  const removeItem = useCallback((key: string) => {
    // Remove from all tracking states
    setExpandedItems(prev => {
      const newSet = new Set(prev);
      newSet.delete(key);
      return newSet;
    });
    setLoadingItems(prev => {
      const newSet = new Set(prev);
      newSet.delete(key);
      return newSet;
    });
    setItemData(prev => {
      const newData = { ...prev };
      delete newData[key];
      return newData;
    });
    setErrors(prev => {
      const newErrors = { ...prev };
      delete newErrors[key];
      return newErrors;
    });
  }, []);

  const isExpanded = useCallback((key: string) => expandedItems.has(key), [expandedItems]);
  const isLoading = useCallback((key: string) => loadingItems.has(key), [loadingItems]);
  const getError = useCallback((key: string) => errors[key] || null, [errors]);
  const getData = useCallback((key: string) => itemData[key], [itemData]);

  return {
    expandedItems,
    loadingItems,
    itemData,
    errors,
    toggleItem,
    setItemLoading,
    setItemData: setItemDataCallback,
    setItemError,
    removeItem,
    isExpanded,
    isLoading,
    getError,
    getData
  };
}

