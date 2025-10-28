"""
Configuration API endpoints.

Provides endpoints for retrieving system configuration and LM provider status.
"""
from fastapi import APIRouter, HTTPException, status
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from dspy_forge.core.lm_config import get_provider_config_status
from dspy_forge.core.logging import get_logger
from dspy_forge.utils.tool_utils import (
    clear_uc_functions_cache,
    get_cache_stats,
    set_cache_ttl
)

router = APIRouter()
logger = get_logger(__name__)


class MCPHeader(BaseModel):
    key: str
    value: str
    isSecret: bool = False
    envVarName: str = ""


class ListMCPToolsRequest(BaseModel):
    url: str
    headers: List[MCPHeader] = []


class ListUCFunctionsRequest(BaseModel):
    catalog: str
    schema: str
    force_reload: bool = False


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
    import os
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    
    if not request.url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MCP server URL is required"
        )
    
    # Build headers dictionary
    headers = {}
    for header in request.headers:
        if header.isSecret and header.envVarName:
            # Use environment variable
            env_value = os.getenv(header.envVarName)
            if env_value:
                headers[header.key] = env_value
            else:
                logger.warning(f"Environment variable {header.envVarName} not found for header {header.key}")
        else:
            # Use literal value
            headers[header.key] = header.value
    
    try:
        tools_data = []
        async with streamablehttp_client(
            url=request.url,
            headers=headers
        ) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tool_list = await session.list_tools()
                
                # Convert to serializable format
                for tool in tool_list.tools:
                    tools_data.append({
                        "name": tool.name,
                        "description": tool.description or "",
                        "inputSchema": tool.inputSchema or {}
                    })
        
        logger.info(f"Successfully listed {len(tools_data)} tools from MCP server: {request.url}")
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
    from databricks.sdk import WorkspaceClient
    from databricks.sdk.service.catalog import FunctionInfo
    
    if not request.catalog or not request.schema:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both catalog and schema are required"
        )
    
    catalog = request.catalog
    schema = request.schema
    force_reload = request.force_reload
    
    try:
        logger.info(f"Listing functions in {catalog}.{schema} (force_reload={force_reload})...")
        
        from dspy_forge.utils.tool_utils import (
            get_workspace_client, 
            extract_function_parameters,
            clear_uc_functions_cache
        )
        
        # If force reload, clear cache for this schema first
        if force_reload:
            clear_uc_functions_cache(catalog, schema)
            logger.info(f"Cleared cache for {catalog}.{schema} due to force_reload")
        
        w = get_workspace_client()
        
        # List all functions in the schema
        functions = list(w.functions.list(catalog_name=catalog, schema_name=schema))
        logger.info(f"Found {len(functions)} functions in {catalog}.{schema}")
        
        # Convert to serializable format
        functions_data = []
        for func in functions:
            full_name = func.full_name or f"{catalog}.{schema}.{func.name}"            
            func_name = func.name or full_name.split('.')[-1]            
            description = func.comment or f"Unity Catalog function: {full_name}"
            args, arg_types, arg_desc = extract_function_parameters(func)
            input_params = {}
            for param_name in args.keys():
                input_params[param_name] = {
                    "type": arg_types.get(param_name, "string"),
                    "comment": arg_desc.get(param_name, "")
                }
            
            functions_data.append({
                "name": func_name,
                "fullName": full_name,
                "description": description,
                "inputParams": input_params
            })
            logger.debug(f"Loaded UC function: {full_name}")
        
        logger.info(f"Successfully loaded {len(functions_data)} UC functions from {catalog}.{schema}")
        return {
            "success": True,
            "functions": functions_data,
            "count": len(functions_data)
        }
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to list UC functions from {catalog}.{schema}: {error_msg}", exc_info=True)
        
        # Provide specific error messages based on error type
        if "NOT_FOUND" in error_msg or "does not exist" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schema '{catalog}.{schema}' not found. Please verify the catalog and schema names."
            )
        elif "PERMISSION_DENIED" in error_msg or "permission" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied to access schema '{catalog}.{schema}'. Please check your access rights."
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


class ClearCacheRequest(BaseModel):
    catalog: Optional[str] = None
    schema: Optional[str] = None


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


class SetCacheTTLRequest(BaseModel):
    ttl_seconds: int


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
