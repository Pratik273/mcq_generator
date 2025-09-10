import os
import logging
from typing import Optional
from dotenv import load_dotenv
load_dotenv()  # Automatically loads variables from .env
logger = logging.getLogger("mcq_generator")

# Azure OpenAI Configuration
# AZURE_API_KEY = os.getenv("AZURE_API_KEY", "3b3d56fe7c6c4809bdc73a725008b4ac")
# AZURE_API_BASE = os.getenv("AZURE_API_BASE", "https://autobugopenai.openai.azure.com/")
# AZURE_DEPLOYMENT_NAME = os.getenv("AZURE_DEPLOYMENT_NAME", "gpt-4o")
# AZURE_API_VERSION = os.getenv("AZURE_API_VERSION", "2025-01-01-preview")
AZURE_API_KEY = "3b3d56fe7c6c4809bdc73a725008b4ac"
AZURE_API_BASE = "https://autobugopenai.openai.azure.com/"
AZURE_DEPLOYMENT_NAME = "gpt-4o"
AZURE_API_VERSION = "2025-01-01-preview"

print("KEYS ARE HERE",AZURE_API_KEY, AZURE_API_BASE, AZURE_DEPLOYMENT_NAME, AZURE_API_VERSION)
# Application Configuration
APP_NAME = os.getenv("APP_NAME", "MCQ Generator API")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
APP_DESCRIPTION = os.getenv("APP_DESCRIPTION", "AI-powered MCQ generation with learning resources Tool")
AVERAGE_GENERATION_TIME= os.getenv("AVERAGE_GENERATION_TIME", "50")
# Server Configuration
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# API Configuration
API_PREFIX = os.getenv("API_PREFIX", "/api/v1")
MAX_QUESTIONS_PER_REQUEST = int(os.getenv("MAX_QUESTIONS_PER_REQUEST", "50"))
MIN_QUESTIONS_PER_REQUEST = int(os.getenv("MIN_QUESTIONS_PER_REQUEST", "5"))
DEFAULT_QUESTION_COUNT = int(os.getenv("DEFAULT_QUESTION_COUNT", "20"))

# Timeout Configuration
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "120"))  # seconds
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "60"))  # seconds

# CORS Configuration
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
CORS_METHODS = os.getenv("CORS_METHODS", "GET,POST,PUT,DELETE,OPTIONS").split(",")
CORS_HEADERS = os.getenv("CORS_HEADERS", "*").split(",")

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = os.getenv(
    "LOG_FORMAT",
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Rate Limiting Configuration
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "false").lower() == "true"
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "10"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))  # seconds

# Cache Configuration
CACHE_ENABLED = os.getenv("CACHE_ENABLED", "false").lower() == "true"
CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))  # seconds

# Health Check Configuration
HEALTH_CHECK_TIMEOUT = int(os.getenv("HEALTH_CHECK_TIMEOUT", "10"))  # seconds

# Feature Flags
ENABLE_ROADMAP = os.getenv("ENABLE_ROADMAP", "true").lower() == "true"
ENABLE_REFERENCE_VIDEOS = os.getenv("ENABLE_REFERENCE_VIDEOS", "true").lower() == "true"
ENABLE_DETAILED_LOGGING = os.getenv("ENABLE_DETAILED_LOGGING", "false").lower() == "true"

# Validation Configuration
MAX_TOPIC_LENGTH = int(os.getenv("MAX_TOPIC_LENGTH", "200"))
MAX_USERNAME_LENGTH = int(os.getenv("MAX_USERNAME_LENGTH", "50"))
MIN_USERNAME_LENGTH = int(os.getenv("MIN_USERNAME_LENGTH", "2"))

# Default Values
DEFAULT_DIFFICULTY = os.getenv("DEFAULT_DIFFICULTY", "mixed")
SUPPORTED_DIFFICULTIES = ["basic", "intermediate", "advanced", "mixed"]


def validate_config() -> bool:
    """
    Validate the application configuration.

    Returns:
        bool: True if configuration is valid, False otherwise
    """
    errors = []

    # Check required Azure OpenAI configuration
    if not AZURE_API_KEY:
        errors.append("AZURE_API_KEY is required")

    if not AZURE_API_BASE:
        errors.append("AZURE_API_BASE is required")
    elif not AZURE_API_BASE.startswith(("http://", "https://")):
        errors.append("AZURE_API_BASE must be a valid URL")

    if not AZURE_DEPLOYMENT_NAME:
        errors.append("AZURE_DEPLOYMENT_NAME is required")

    # Validate numeric configurations
    if MAX_QUESTIONS_PER_REQUEST <= MIN_QUESTIONS_PER_REQUEST:
        errors.append("MAX_QUESTIONS_PER_REQUEST must be greater than MIN_QUESTIONS_PER_REQUEST")

    if DEFAULT_QUESTION_COUNT < MIN_QUESTIONS_PER_REQUEST or DEFAULT_QUESTION_COUNT > MAX_QUESTIONS_PER_REQUEST:
        errors.append("DEFAULT_QUESTION_COUNT must be within the min/max range")

    if REQUEST_TIMEOUT <= 0:
        errors.append("REQUEST_TIMEOUT must be positive")

    if LLM_TIMEOUT <= 0:
        errors.append("LLM_TIMEOUT must be positive")

    # Validate difficulty setting
    if DEFAULT_DIFFICULTY not in SUPPORTED_DIFFICULTIES:
        errors.append(f"DEFAULT_DIFFICULTY must be one of: {SUPPORTED_DIFFICULTIES}")

    # Log validation results
    if errors:
        for error in errors:
            logger.error(f"Configuration error: {error}")
        return False
    else:
        logger.info("Configuration validation passed")
        return True


def get_config_info() -> dict:
    """
    Get current configuration information (safe for logging).

    Returns:
        dict: Configuration information with sensitive data masked
    """
    return {
        "app": {
            "name": APP_NAME,
            "version": APP_VERSION,
            "description": APP_DESCRIPTION,
            "debug": DEBUG
        },
        "server": {
            "host": HOST,
            "port": PORT,
            "api_prefix": API_PREFIX
        },
        "azure_openai": {
            "deployment": AZURE_DEPLOYMENT_NAME,
            "api_version": AZURE_API_VERSION,
            "endpoint": AZURE_API_BASE.split(".openai.azure.com")[0] + ".openai.azure.com" if AZURE_API_BASE else "not_set",
            "api_key_configured": bool(AZURE_API_KEY)
        },
        "limits": {
            "max_questions": MAX_QUESTIONS_PER_REQUEST,
            "min_questions": MIN_QUESTIONS_PER_REQUEST,
            "default_questions": DEFAULT_QUESTION_COUNT,
            "request_timeout": REQUEST_TIMEOUT,
            "llm_timeout": LLM_TIMEOUT
        },
        "features": {
            "roadmap_enabled": ENABLE_ROADMAP,
            "reference_videos_enabled": ENABLE_REFERENCE_VIDEOS,
            "rate_limiting": RATE_LIMIT_ENABLED,
            "caching": CACHE_ENABLED,
            "detailed_logging": ENABLE_DETAILED_LOGGING
        },
        "cors": {
            "origins": CORS_ORIGINS,
            "methods": CORS_METHODS
        }
    }


def log_startup_info():
    """Log important configuration information at startup."""
    config_info = get_config_info()

    logger.info(f"Starting {config_info['app']['name']} v{config_info['app']['version']}")
    logger.info(f"Server will run on {config_info['server']['host']}:{config_info['server']['port']}")
    logger.info(f"API prefix: {config_info['server']['api_prefix']}")
    logger.info(f"Azure OpenAI deployment: {config_info['azure_openai']['deployment']}")
    logger.info(f"Question limits: {config_info['limits']['min_questions']}-{config_info['limits']['max_questions']}")

    if DEBUG:
        logger.warning("DEBUG mode is enabled - not suitable for production")

    # Log feature status
    features = config_info['features']
    enabled_features = [key for key, value in features.items() if value]
    if enabled_features:
        logger.info(f"Enabled features: {', '.join(enabled_features)}")


# Environment-specific configurations
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()

if ENVIRONMENT == "production":
    # Production-specific settings
    DEBUG = False
    LOG_LEVEL = "WARNING"
    ENABLE_DETAILED_LOGGING = False
elif ENVIRONMENT == "staging":
    # Staging-specific settings
    DEBUG = False
    LOG_LEVEL = "INFO"
elif ENVIRONMENT == "development":
    # Development-specific settings
    DEBUG = True
    LOG_LEVEL = "DEBUG"
    ENABLE_DETAILED_LOGGING = True

# Validate configuration on import
if not validate_config():
    logger.critical("Configuration validation failed - application may not work correctly")
else:
    logger.debug("Configuration loaded successfully")