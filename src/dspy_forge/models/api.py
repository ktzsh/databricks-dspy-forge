"""
API request and response models.

Pydantic models for API endpoints including configuration, tools, and caching.
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class MCPHeader(BaseModel):
    """Header configuration for MCP server requests."""
    key: str
    value: str
    isSecret: bool = False
    envVarName: str = ""


class ListMCPToolsRequest(BaseModel):
    """Request model for listing MCP tools."""
    url: str
    headers: List[MCPHeader] = []


class ListUCFunctionsRequest(BaseModel):
    """Request model for listing Unity Catalog functions."""
    catalog: str
    schema: str
    force_reload: bool = False


class ClearCacheRequest(BaseModel):
    """Request model for clearing UC functions cache."""
    catalog: Optional[str] = None
    schema: Optional[str] = None


class SetCacheTTLRequest(BaseModel):
    """Request model for setting cache TTL."""
    ttl_seconds: int

