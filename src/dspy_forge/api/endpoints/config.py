"""
Configuration API endpoints.

Provides endpoints for retrieving system configuration and LM provider status.
"""
from fastapi import APIRouter, HTTPException, status
from typing import Dict, List, Any
from dspy_forge.core.lm_config import get_provider_config_status
from dspy_forge.core.logging import get_logger
from dspy_forge.core.tools import (
    fetch_mcp_tools,
    fetch_uc_functions,
    build_mcp_headers,
)
from dspy_forge.models.api import (
    MCPHeader,
    ListMCPToolsRequest,
    ListUCFunctionsRequest,
    ClearCacheRequest,
    SetCacheTTLRequest,
)
from dspy_forge.utils.tool_utils import (
    clear_uc_functions_cache,
    get_cache_stats,
    set_cache_ttl
)

router = APIRouter()
logger = get_logger(__name__)


@router.get("/lm-providers")
async def get_lm_providers() -> Dict[str, bool]:
    """
    Get the configuration status of all LM providers.

    Returns a dictionary mapping provider name to boolean indicating
    whether that provider is configured (has necessary API keys/credentials).

    Note: This endpoint does NOT return actual API keys, only boolean flags.
    """
    return get_provider_config_status()


@router.post("/mcp-tools")
async def list_mcp_tools(request: ListMCPToolsRequest) -> Dict[str, Any]:
    """
    List tools available from an MCP server.
    
    Args:
        request: MCP server URL and headers
        
    Returns:
        Dictionary containing list of tools with their names, descriptions, and input schemas
    """
    if not request.url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MCP server URL is required"
        )
    
    # Build headers dictionary from request
    headers = build_mcp_headers([h.dict() for h in request.headers])
    
    try:
        # Fetch tools from MCP server 
        tools_data = await fetch_mcp_tools(request.url, headers)
        
        return {
            "success": True,
            "tools": tools_data
        }
    except Exception as e:
        logger.error(f"Failed to list MCP tools from {request.url}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list MCP tools: {str(e)}"
        )


@router.post("/uc-functions")
async def list_uc_functions(request: ListUCFunctionsRequest) -> Dict[str, Any]:
    """
    List functions available from a Unity Catalog schema.
    Uses the same implementation as UCFunctionTemplate.load_tools() for consistency.
    
    Args:
        request: Catalog and schema names
        
    Returns:
        Dictionary containing list of functions with their names, descriptions, and parameters
    """
    if not request.catalog or not request.schema:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both catalog and schema are required"
        )
    
    try:
        # Fetch functions from Unity Catalog
        functions_data = fetch_uc_functions(
            catalog=request.catalog,
            schema=request.schema,
            force_reload=request.force_reload
        )
        
        return {
            "success": True,
            "functions": functions_data,
            "count": len(functions_data)
        }
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to list UC functions from {request.catalog}.{request.schema}: {error_msg}", exc_info=True)
        
        # Provide specific error messages based on error type
        if "NOT_FOUND" in error_msg or "does not exist" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schema '{request.catalog}.{request.schema}' not found. Please verify the catalog and schema names."
            )
        elif "PERMISSION_DENIED" in error_msg or "permission" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied to access schema '{request.catalog}.{request.schema}'. Please check your access rights."
            )
        else:
            # Return the actual error message for debugging
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to list UC functions: {error_msg}"
            )


@router.get("/uc-cache-stats")
async def get_uc_cache_statistics():
    """
    Get statistics about the UC functions cache.
    
    Returns cache information including:
    - Total entries
    - TTL configuration
    - Per-schema details (tool count, age, expiry)
    """
    try:
        stats = get_cache_stats()
        return {
            "success": True,
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cache statistics: {str(e)}"
            )


@router.post("/uc-cache-clear")
async def clear_uc_cache(request: ClearCacheRequest = None):
    """
    Clear UC functions cache.
    
    - If catalog and schema provided: clears specific entry
    - If neither provided: clears entire cache
    """
    try:
        catalog = request.catalog if request else None
        schema = request.schema if request else None
        
        clear_uc_functions_cache(catalog, schema)
        
        if catalog and schema:
            message = f"Cleared cache for {catalog}.{schema}"
        else:
            message = "Cleared entire UC functions cache"
            
        return {
            "success": True,
            "message": message
        }
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear cache: {str(e)}"
        )


@router.post("/uc-cache-ttl")
async def set_uc_cache_ttl(request: SetCacheTTLRequest):
    """
    Set the TTL for UC functions cache.
    """
    try:
        set_cache_ttl(request.ttl_seconds)
        return {
            "success": True,
            "message": f"Set cache TTL to {request.ttl_seconds} seconds"
        }
    except Exception as e:
        logger.error(f"Failed to set cache TTL: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set cache TTL: {str(e)}"
        )
