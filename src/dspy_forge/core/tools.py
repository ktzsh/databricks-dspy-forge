"""
Core tools functionality for MCP and Unity Catalog integrations.

This module contains logic for discovering and listing tools from:
- MCP (Model Context Protocol) servers
- Unity Catalog function schemas
"""
import os
from typing import Dict, List, Any
from dspy_forge.core.logging import get_logger

logger = get_logger(__name__)


async def fetch_mcp_tools(url: str, headers: Dict[str, str]) -> List[Dict[str, Any]]:
    """
    Fetch tools available from an MCP server.
    
    Args:
        url: MCP server URL
        headers: HTTP headers for authentication/configuration
        
    Returns:
        List of tools with their names, descriptions, and input schemas
        
    Raises:
        Exception: If connection or tool listing fails
    """
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    
    tools_data = []
    async with streamablehttp_client(
        url=url,
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
    
    logger.info(f"Successfully fetched {len(tools_data)} tools from MCP server: {url}")
    return tools_data


def fetch_uc_functions(catalog: str, schema: str, force_reload: bool = False) -> List[Dict[str, Any]]:
    """
    Fetch functions available from a Unity Catalog schema.
    
    Args:
        catalog: UC catalog name
        schema: UC schema name
        force_reload: If True, clears cache before fetching
        
    Returns:
        List of functions with their names, descriptions, and parameters
        
    Raises:
        Exception: If UC connection or function listing fails
    """
    from dspy_forge.utils.tool_utils import (
        get_workspace_client, 
        extract_function_parameters,
        clear_uc_functions_cache
    )
    
    logger.info(f"Fetching functions from {catalog}.{schema} (force_reload={force_reload})...")
    
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
    
    logger.info(f"Successfully fetched {len(functions_data)} UC functions from {catalog}.{schema}")
    return functions_data


def build_mcp_headers(headers_config: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    Build HTTP headers for MCP requests, resolving environment variables for secrets.
    
    Args:
        headers_config: List of header configurations with keys, values, and secret flags
        
    Returns:
        Dictionary of resolved HTTP headers
    """
    headers = {}
    for header in headers_config:
        key = header.get("key") or header.get("header_key")
        value = header.get("value") or header.get("header_value", "")
        is_secret = header.get("isSecret") or header.get("is_secret", False)
        env_var_name = header.get("envVarName") or header.get("env_var_name", "")
        
        if is_secret and env_var_name:
            # Use environment variable
            env_value = os.getenv(env_var_name)
            if env_value:
                headers[key] = env_value
            else:
                logger.warning(f"Environment variable {env_var_name} not found for header {key}")
        else:
            # Use literal value
            headers[key] = value
    
    return headers

