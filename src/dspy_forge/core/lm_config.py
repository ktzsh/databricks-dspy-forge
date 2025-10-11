"""
LM Configuration Helper

Provides utilities for creating DSPy LM instances with proper authentication
for different providers (Databricks, OpenAI, Anthropic, Gemini, custom).
"""
import dspy
import os
from typing import Optional, Dict, Any
from dspy_forge.core.config import settings
from dspy_forge.core.logging import get_logger

logger = get_logger(__name__)


class LMProvider:
    """Supported LM providers"""
    DATABRICKS = "databricks"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    CUSTOM = "custom"


def parse_model_name(model_name: str) -> tuple[str, str]:
    """
    Parse model name to extract provider and actual model name.

    Format: provider/model_name
    Examples:
        - "databricks/databricks-claude-sonnet-4-5" -> ("databricks", "databricks-claude-sonnet-4-5")
        - "openai/gpt-4" -> ("openai", "gpt-4")
        - "anthropic/claude-3-sonnet" -> ("anthropic", "claude-3-sonnet")
        - "gemini/gemini-pro" -> ("gemini", "gemini-pro")
        - "my-model" -> ("databricks", "my-model")  # Default to databricks for backward compatibility

    Args:
        model_name: Model name string with optional provider prefix

    Returns:
        Tuple of (provider, model_name)
    """
    if not model_name:
        return LMProvider.DATABRICKS, ""

    if "/" in model_name:
        parts = model_name.split("/", 1)
        provider = parts[0].lower()
        actual_model = parts[1]
        return provider, actual_model

    # Default to Databricks for backward compatibility
    return LMProvider.DATABRICKS, model_name


def is_databricks_configured() -> bool:
    """Check if Databricks authentication is configured"""
    return bool(
        settings.databricks_config_profile or
        (settings.databricks_host and settings.databricks_token) or
        (os.environ.get("DATABRICKS_CLIENT_ID") and
         os.environ.get("DATABRICKS_CLIENT_SECRET"))
    )


def get_provider_config_status() -> Dict[str, bool]:
    """
    Get configuration status for all supported providers.

    Returns:
        Dictionary mapping provider name to boolean indicating if configured
    """
    return {
        LMProvider.DATABRICKS: is_databricks_configured(),
        LMProvider.OPENAI: bool(settings.openai_api_key),
        LMProvider.ANTHROPIC: bool(settings.anthropic_api_key),
        LMProvider.GEMINI: bool(settings.gemini_api_key),
        LMProvider.CUSTOM: bool(settings.custom_lm_api_base and settings.custom_lm_api_key),
    }


def create_lm(model_name: str, **kwargs) -> dspy.LM:
    """
    Create a DSPy LM instance with proper configuration based on provider.

    Args:
        model_name: Model name in format "provider/model" or just "model" (defaults to Databricks)
        **kwargs: Additional arguments to pass to dspy.LM()

    Returns:
        Configured dspy.LM instance

    Raises:
        ValueError: If provider is not configured or model_name is invalid
    """
    if not model_name:
        raise ValueError("model_name cannot be empty")

    provider, actual_model = parse_model_name(model_name)

    logger.debug(f"Creating LM for provider='{provider}', model='{actual_model}'")

    # Databricks provider
    if provider == LMProvider.DATABRICKS:
        if not is_databricks_configured():
            logger.warning(
                "Databricks is not configured. Model may fail at runtime. "
                "Please configure DATABRICKS_CONFIG_PROFILE or DATABRICKS_HOST/DATABRICKS_TOKEN."
            )
        # For Databricks, DSPy uses ambient credentials
        return dspy.LM(model=f"{LMProvider.DATABRICKS}/{actual_model}", **kwargs)

    # OpenAI provider
    elif provider == LMProvider.OPENAI:
        if not settings.openai_api_key:
            raise ValueError(
                "OpenAI API key not configured. "
                "Please set OPENAI_API_KEY in your .env file."
            )
        return dspy.LM(
            model=f"{LMProvider.OPENAI}/{actual_model}",
            api_key=settings.openai_api_key,
            **kwargs
        )

    # Anthropic provider
    elif provider == LMProvider.ANTHROPIC:
        if not settings.anthropic_api_key:
            raise ValueError(
                "Anthropic API key not configured. "
                "Please set ANTHROPIC_API_KEY in your .env file."
            )
        return dspy.LM(
            model=f"{LMProvider.ANTHROPIC}/{actual_model}",
            api_key=settings.anthropic_api_key,
            **kwargs
        )

    # Gemini provider
    elif provider == LMProvider.GEMINI:
        if not settings.gemini_api_key:
            raise ValueError(
                "Gemini API key not configured. "
                "Please set GEMINI_API_KEY in your .env file."
            )
        return dspy.LM(
            model=f"{LMProvider.GEMINI}/{actual_model}",
            api_key=settings.gemini_api_key,
            **kwargs
        )

    # Custom provider
    elif provider == LMProvider.CUSTOM or provider not in [
        LMProvider.DATABRICKS,
        LMProvider.OPENAI,
        LMProvider.ANTHROPIC,
        LMProvider.GEMINI
    ]:
        # For custom or unknown providers, require both api_base and api_key
        if not settings.custom_lm_api_base or not settings.custom_lm_api_key:
            raise ValueError(
                f"Custom provider '{provider}' requires both CUSTOM_LM_API_BASE and "
                f"CUSTOM_LM_API_KEY to be set in your .env file."
            )
        return dspy.LM(
            model=f"{provider}/{actual_model}",
            api_base=settings.custom_lm_api_base,
            api_key=settings.custom_lm_api_key,
            **kwargs
        )

    else:
        raise ValueError(f"Unsupported provider: {provider}")


def validate_model_config(model_name: str) -> tuple[bool, Optional[str]]:
    """
    Validate that a model configuration is valid and the provider is configured.

    Args:
        model_name: Model name to validate

    Returns:
        Tuple of (is_valid, error_message). error_message is None if valid.
    """
    if not model_name:
        return False, "Model name cannot be empty"

    provider, actual_model = parse_model_name(model_name)

    if not actual_model:
        return False, f"Invalid model name format: '{model_name}'"

    provider_status = get_provider_config_status()

    # Map provider string to status
    if provider == LMProvider.DATABRICKS and not provider_status[LMProvider.DATABRICKS]:
        return False, "Databricks is not configured. Please configure your Databricks credentials."
    elif provider == LMProvider.OPENAI and not provider_status[LMProvider.OPENAI]:
        return False, "OpenAI API key not configured."
    elif provider == LMProvider.ANTHROPIC and not provider_status[LMProvider.ANTHROPIC]:
        return False, "Anthropic API key not configured."
    elif provider == LMProvider.GEMINI and not provider_status[LMProvider.GEMINI]:
        return False, "Gemini API key not configured."
    elif provider not in [LMProvider.DATABRICKS, LMProvider.OPENAI, LMProvider.ANTHROPIC, LMProvider.GEMINI]:
        # Custom provider
        if not provider_status[LMProvider.CUSTOM]:
            return False, f"Custom provider '{provider}' requires CUSTOM_LM_API_BASE and CUSTOM_LM_API_KEY."

    return True, None
