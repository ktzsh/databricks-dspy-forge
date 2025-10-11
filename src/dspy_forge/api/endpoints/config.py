"""
Configuration API endpoints.

Provides endpoints for retrieving system configuration and LM provider status.
"""
from fastapi import APIRouter
from typing import Dict
from dspy_forge.core.lm_config import get_provider_config_status

router = APIRouter()


@router.get("/lm-providers")
async def get_lm_providers() -> Dict[str, bool]:
    """
    Get the configuration status of all LM providers.

    Returns a dictionary mapping provider name to boolean indicating
    whether that provider is configured (has necessary API keys/credentials).

    Note: This endpoint does NOT return actual API keys, only boolean flags.
    """
    return get_provider_config_status()
