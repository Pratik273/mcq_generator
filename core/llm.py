import logging
from functools import lru_cache
from typing import Optional
from langchain_openai import AzureChatOpenAI
from config import AZURE_API_KEY, AZURE_API_BASE, AZURE_DEPLOYMENT_NAME, AZURE_API_VERSION

logger = logging.getLogger("mcq_generator")


class LLMConnectionError(Exception):
    """Custom exception for LLM connection issues."""
    pass


@lru_cache(maxsize=1)
def get_llm_client() -> AzureChatOpenAI:
    """
    Create and cache the Azure Chat OpenAI client with enhanced error handling.

    Returns:
        AzureChatOpenAI: Configured Azure OpenAI client

    Raises:
        LLMConnectionError: If client configuration fails
    """
    try:
        # Validate configuration
        _validate_azure_config()

        # Create client with optimized settings
        client = AzureChatOpenAI(
            azure_deployment=AZURE_DEPLOYMENT_NAME,
            openai_api_version=AZURE_API_VERSION,
            azure_endpoint=AZURE_API_BASE,
            api_key=AZURE_API_KEY,
            temperature=0.7,  # Balanced creativity and consistency
            max_tokens=4000,  # Sufficient for comprehensive responses
            request_timeout=60,  # Reasonable timeout
            max_retries=3,  # Retry failed requests
            streaming=False,  # Disable streaming for stability
        )

        logger.info(
            f"Azure OpenAI client initialized successfully - "
            f"Deployment: {AZURE_DEPLOYMENT_NAME}, Version: {AZURE_API_VERSION}"
        )

        return client

    except Exception as e:
        error_msg = f"Failed to initialize Azure OpenAI client: {str(e)}"
        logger.error(error_msg)
        raise LLMConnectionError(error_msg)


def _validate_azure_config() -> None:
    """
    Validate Azure OpenAI configuration parameters.

    Raises:
        LLMConnectionError: If configuration is invalid
    """
    required_configs = {
        "AZURE_API_KEY": AZURE_API_KEY,
        "AZURE_API_BASE": AZURE_API_BASE,
        "AZURE_DEPLOYMENT_NAME": AZURE_DEPLOYMENT_NAME,
        "AZURE_API_VERSION": AZURE_API_VERSION
    }

    missing_configs = [
        key for key, value in required_configs.items()
        if not value or value.strip() == ""
    ]

    if missing_configs:
        error_msg = f"Missing required Azure OpenAI configuration: {', '.join(missing_configs)}"
        logger.error(error_msg)
        raise LLMConnectionError(error_msg)

    # Validate API base URL format
    if not AZURE_API_BASE.startswith(("http://", "https://")):
        error_msg = "AZURE_API_BASE must be a valid URL starting with http:// or https://"
        logger.error(error_msg)
        raise LLMConnectionError(error_msg)

    # Validate API version format
    if not AZURE_API_VERSION.replace("-", "").replace(".", "").isalnum():
        error_msg = "AZURE_API_VERSION has invalid format"
        logger.error(error_msg)
        raise LLMConnectionError(error_msg)

    logger.debug("Azure OpenAI configuration validated successfully")


async def test_llm_connection() -> bool:
    """
    Test the LLM connection with a simple request.

    Returns:
        bool: True if connection is successful, False otherwise
    """
    try:
        client = get_llm_client()

        # Simple test prompt
        test_response = await client.ainvoke("Hello, please respond with 'Connection successful'")

        if test_response and hasattr(test_response, 'content'):
            logger.info("LLM connection test successful")
            return True
        else:
            logger.warning("LLM connection test returned unexpected response")
            return False

    except Exception as e:
        logger.error(f"LLM connection test failed: {e}")
        return False


def get_llm_info() -> dict:
    """
    Get information about the current LLM configuration.

    Returns:
        dict: LLM configuration information
    """
    try:
        client = get_llm_client()

        return {
            "provider": "Azure OpenAI",
            "deployment": AZURE_DEPLOYMENT_NAME,
            "api_version": AZURE_API_VERSION,
            "endpoint": AZURE_API_BASE.split(".openai.azure.com")[0] + ".openai.azure.com",  # Mask full endpoint
            "temperature": client.temperature,
            "max_tokens": getattr(client, 'max_tokens', 'default'),
            "timeout": client.request_timeout,
            "max_retries": getattr(client, 'max_retries', 'default'),
            "status": "configured"
        }

    except Exception as e:
        logger.error(f"Error getting LLM info: {e}")
        return {
            "provider": "Azure OpenAI",
            "status": "error",
            "error": str(e)
        }


def clear_llm_cache() -> None:
    """
    Clear the LLM client cache. Useful for configuration updates.
    """
    try:
        get_llm_client.cache_clear()
        logger.info("LLM client cache cleared successfully")
    except Exception as e:
        logger.error(f"Error clearing LLM cache: {e}")


# Enhanced client factory for different use cases
def get_creative_llm_client() -> AzureChatOpenAI:
    """
    Get an LLM client optimized for creative content generation.

    Returns:
        AzureChatOpenAI: Client with higher temperature for creativity
    """
    try:
        _validate_azure_config()

        client = AzureChatOpenAI(
            azure_deployment=AZURE_DEPLOYMENT_NAME,
            openai_api_version=AZURE_API_VERSION,
            azure_endpoint=AZURE_API_BASE,
            api_key=AZURE_API_KEY,
            temperature=0.9,  # Higher creativity
            max_tokens=4000,
            request_timeout=90,  # Longer timeout for creative tasks
            max_retries=2,
            streaming=False
        )

        logger.debug("Creative LLM client initialized")
        return client

    except Exception as e:
        error_msg = f"Failed to initialize creative LLM client: {str(e)}"
        logger.error(error_msg)
        raise LLMConnectionError(error_msg)


def get_precise_llm_client() -> AzureChatOpenAI:
    """
    Get an LLM client optimized for precise, factual responses.

    Returns:
        AzureChatOpenAI: Client with lower temperature for precision
    """
    try:
        _validate_azure_config()

        client = AzureChatOpenAI(
            azure_deployment=AZURE_DEPLOYMENT_NAME,
            openai_api_version=AZURE_API_VERSION,
            azure_endpoint=AZURE_API_BASE,
            api_key=AZURE_API_KEY,
            temperature=0.3,  # Lower temperature for precision
            max_tokens=3000,
            request_timeout=45,
            max_retries=3,
            streaming=False
        )

        logger.debug("Precise LLM client initialized")
        return client

    except Exception as e:
        error_msg = f"Failed to initialize precise LLM client: {str(e)}"
        logger.error(error_msg)
        raise LLMConnectionError(error_msg)