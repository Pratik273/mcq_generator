import logging
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import uvicorn

from api.routes import router as mcq_router
from config import (
    APP_NAME, APP_VERSION, APP_DESCRIPTION, DEBUG, HOST, PORT,
    CORS_ORIGINS, CORS_METHODS, CORS_HEADERS, LOG_LEVEL, LOG_FORMAT,
    validate_config, log_startup_info
)

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("mcq_generator.log") if DEBUG else logging.NullHandler()
    ]
)

logger = logging.getLogger("mcq_generator")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown events.

    Args:
        app: FastAPI application instance
    """
    # Startup
    logger.info("=== MCQ Generator API Starting ===")

    # Validate configuration
    if not validate_config():
        logger.critical("Configuration validation failed")
        sys.exit(1)

    # Log startup information
    log_startup_info()

    # Test LLM connection
    try:
        from core.llm import get_llm_client
        get_llm_client()
        logger.info("LLM connection verified successfully")
    except Exception as e:
        logger.error(f"LLM connection failed: {e}")
        if not DEBUG:
            logger.critical("LLM connection is required for production")
            sys.exit(1)

    logger.info("=== MCQ Generator API Started Successfully ===")

    yield

    # Shutdown
    logger.info("=== MCQ Generator API Shutting Down ===")


# Create FastAPI application
app = FastAPI(
    title=APP_NAME,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs" if DEBUG else None,
    redoc_url="/redoc" if DEBUG else None,
    openapi_url="/openapi.json" if DEBUG else None,
    debug=DEBUG
)

# Security middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"] if DEBUG else ["localhost", "127.0.0.1"]
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=CORS_METHODS,
    allow_headers=CORS_HEADERS,
    expose_headers=["X-Request-ID"]
)


# Request ID middleware for tracing
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add unique request ID for tracing."""
    import uuid
    request_id = str(uuid.uuid4())[:8]

    # Add to request state
    request.state.request_id = request_id

    # Process request
    response = await call_next(request)

    # Add to response headers
    response.headers["X-Request-ID"] = request_id

    return response


# Logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log HTTP requests with timing information."""
    import time

    start_time = time.time()
    request_id = getattr(request.state, 'request_id', 'unknown')

    # Log request start
    logger.info(
        f"[{request_id}] {request.method} {request.url.path} - "
        f"Client: {request.client.host if request.client else 'unknown'}"
    )

    try:
        response = await call_next(request)

        # Log response
        process_time = time.time() - start_time
        logger.info(
            f"[{request_id}] Response: {response.status_code} - "
            f"Time: {process_time:.3f}s"
        )

        return response

    except Exception as e:
        process_time = time.time() - start_time
        logger.error(
            f"[{request_id}] Request failed: {str(e)} - "
            f"Time: {process_time:.3f}s"
        )
        raise


# Global exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors."""
    request_id = getattr(request.state, 'request_id', 'unknown')

    logger.warning(f"[{request_id}] Validation error: {exc}")

    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation Error",
            "message": "Request data validation failed",
            "details": exc.errors(),
            "request_id": request_id
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    request_id = getattr(request.state, 'request_id', 'unknown')

    logger.error(f"[{request_id}] HTTP {exc.status_code}: {exc.detail}")

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP Error",
            "message": exc.detail,
            "status_code": exc.status_code,
            "request_id": request_id
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    request_id = getattr(request.state, 'request_id', 'unknown')

    logger.error(f"[{request_id}] Unexpected error: {str(exc)}", exc_info=True)

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred" if not DEBUG else str(exc),
            "request_id": request_id
        }
    )


# Root endpoint
@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint with basic API information."""
    from config import get_config_info

    config = get_config_info()
    return {
        "service": config["app"]["name"],
        "version": config["app"]["version"],
        "description": config["app"]["description"],
        "status": "operational",
        "docs_url": "/docs" if DEBUG else "Documentation disabled in production",
        "health_check": "/api/v1/health",
        "endpoints": {
            "generate_mcq": "/api/v1/generate-mcq",
            "health": "/api/v1/health",
            "readiness": "/api/v1/health/ready",
            "liveness": "/api/v1/health/live",
            "stats": "/api/v1/generate-mcq/stats"
        }
    }


# Include API routes
app.include_router(mcq_router)


# Development server configuration
if __name__ == "__main__":
    logger.info("Starting development server...")

    uvicorn.run(
        "main:app",
        host=HOST,
        port=PORT,
        reload=DEBUG,
        log_level=LOG_LEVEL.lower(),
        access_log=DEBUG,
        reload_dirs=["./"] if DEBUG else None,
        reload_excludes=["*.log", "__pycache__", ".git"] if DEBUG else None
    )