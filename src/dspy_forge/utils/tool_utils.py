"""
Shared utilities for MCP and UC tool loading.

This module provides singleton clients and shared functions to eliminate
code duplication and improve performance across the codebase.
"""
import time
from typing import Dict, List, Any, Tuple
from databricks.sdk import WorkspaceClient
from unitycatalog.ai.core.databricks import DatabricksFunctionClient
from dspy_forge.core.logging import get_logger

logger = get_logger(__name__)

# Singleton pattern for expensive clients
_workspace_client = None
_uc_function_client = None

# Function cache with TTL for UC functions
# Key: "catalog.schema", Value: (tools_list, timestamp)
_uc_functions_cache: Dict[str, Tuple[List, float]] = {}
_cache_ttl = 2 * 60  # 2 minutes TTL (configurable, reduced from 10 for fresher data)


def get_workspace_client() -> WorkspaceClient:
    """
    Get or create singleton WorkspaceClient.
    
    Returns:
        WorkspaceClient: Singleton instance of Databricks workspace client
    """
    global _workspace_client
    if _workspace_client is None:
        logger.debug("Initializing singleton WorkspaceClient")
        _workspace_client = WorkspaceClient()
    return _workspace_client


def get_uc_function_client() -> DatabricksFunctionClient:
    """
    Get or create singleton DatabricksFunctionClient.
    
    Returns:
        DatabricksFunctionClient: Singleton instance of UC function client
    """
    global _uc_function_client
    if _uc_function_client is None:
        logger.debug("Initializing singleton DatabricksFunctionClient")
        _uc_function_client = DatabricksFunctionClient()
    return _uc_function_client


def extract_function_parameters(func) -> Tuple[Dict, Dict, Dict]:
    """
    Extract parameters from UC function metadata.
    
    Args:
        func: Function info object from Databricks SDK
        
    Returns:
        Tuple of (args, arg_types, arg_desc) dictionaries
    """
    args = {}
    arg_types = {}
    arg_desc = {}
    
    if func.input_params:
        try:
            for param in func.input_params.parameters:
                param_name = param.name
                args[param_name] = None  # Default value
                arg_types[param_name] = param.type_name or 'string'
                arg_desc[param_name] = param.comment or f"Parameter: {param_name}"
        except Exception as e:
            logger.warning(f"Failed to parse function parameters: {e}")
    
    return args, arg_types, arg_desc


def load_uc_functions_from_schema(catalog: str, schema: str, use_cache: bool = True) -> List:
    """
    Load ALL UC functions from a schema with caching.
    
    This is the single source of truth for UC function loading across the codebase.
    Uses singleton clients and caching for maximum performance.
    
    Args:
        catalog: Unity Catalog catalog name
        schema: Unity Catalog schema name
        use_cache: Whether to use cached results (default: True)
        
    Returns:
        List of DSPy Tool objects
    """
    from dspy.adapters.types.tool import Tool as DSPyTool
    
    if not all([catalog, schema]):
        logger.error(f"Missing required fields: catalog={catalog}, schema={schema}")
        return []
    
    # Check cache first
    cache_key = f"{catalog}.{schema}"
    if use_cache and cache_key in _uc_functions_cache:
        cached_tools, cached_time = _uc_functions_cache[cache_key]
        age = time.time() - cached_time
        
        if age < _cache_ttl:
            logger.info(f"Using cached UC functions for {cache_key} (age: {age:.1f}s)")
            return cached_tools
        else:
            logger.debug(f"Cache expired for {cache_key} (age: {age:.1f}s > TTL: {_cache_ttl}s)")
    
    try:
        # Use singleton clients (performance optimization)
        client = get_uc_function_client()
        w = get_workspace_client()
        
        logger.info(f"Listing functions in {catalog}.{schema}...")
        functions = list(w.functions.list(catalog_name=catalog, schema_name=schema))
        logger.info(f"Found {len(functions)} functions in {catalog}.{schema}")
        
        tools = []
        for func in functions:
            full_name = func.full_name or f"{catalog}.{schema}.{func.name}"
            
            # Use shared parameter extraction utility
            args, arg_types, arg_desc = extract_function_parameters(func)
            
            # Create wrapper function with closure to capture func name
            def make_wrapper(func_name):
                def uc_function_wrapper(**kwargs):
                    try:
                        result = client.execute_function(func_name, kwargs)
                        return result
                    except Exception as e:
                        logger.error(f"Error executing UC function {func_name}: {e}")
                        raise
                return uc_function_wrapper
            
            # Create DSPy tool with function metadata and parsed parameters
            tool = DSPyTool(
                func=make_wrapper(full_name),
                name=func.name or full_name.split('.')[-1],
                desc=func.comment or f"Unity Catalog function: {full_name}",
                args=args,
                arg_types=arg_types,
                arg_desc=arg_desc
            )
            tools.append(tool)
            logger.debug(f"Loaded UC function: {full_name} with {len(args)} parameters")
        
        logger.info(f"Successfully loaded {len(tools)} UC functions from {catalog}.{schema}")
        
        # Cache the results
        _uc_functions_cache[cache_key] = (tools, time.time())
        logger.debug(f"Cached UC functions for {cache_key} (TTL: {_cache_ttl}s)")
        
        return tools
        
    except Exception as e:
        logger.error(f"Failed to load UC functions from {catalog}.{schema}: {e}", exc_info=True)
        return []


def clear_uc_functions_cache(catalog: str = None, schema: str = None):
    """
    Clear UC functions cache.
    
    Args:
        catalog: Optional catalog name to clear specific entry
        schema: Optional schema name to clear specific entry
        
    If both provided, clears specific entry. If neither, clears entire cache.
    """
    global _uc_functions_cache
    
    if catalog and schema:
        cache_key = f"{catalog}.{schema}"
        if cache_key in _uc_functions_cache:
            del _uc_functions_cache[cache_key]
            logger.debug(f"Cleared cache for {cache_key}")
    else:
        _uc_functions_cache.clear()
        logger.debug("Cleared entire UC functions cache")


def set_cache_ttl(ttl_seconds: int):
    """
    Set the TTL for UC functions cache.
    
    Args:
        ttl_seconds: Time to live in seconds
    """
    global _cache_ttl
    _cache_ttl = ttl_seconds
    logger.info(f"Set UC functions cache TTL to {ttl_seconds}s")


def get_cache_stats() -> Dict[str, Any]:
    """
    Get statistics about the UC functions cache.
    
    Returns:
        Dictionary with cache statistics
    """
    current_time = time.time()
    stats = {
        'total_entries': len(_uc_functions_cache),
        'ttl_seconds': _cache_ttl,
        'entries': []
    }
    
    for key, (tools, cached_time) in _uc_functions_cache.items():
        age = current_time - cached_time
        stats['entries'].append({
            'schema': key,
            'tool_count': len(tools),
            'age_seconds': age,
            'expires_in_seconds': max(0, _cache_ttl - age),
            'is_valid': age < _cache_ttl
        })
    
    return stats


def reset_clients():
    """
    Reset singleton clients (useful for testing or re-initialization).
    """
    global _workspace_client, _uc_function_client
    _workspace_client = None
    _uc_function_client = None
    logger.debug("Reset singleton clients")

