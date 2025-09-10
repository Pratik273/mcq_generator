import time
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from models import MCQRequest, MCQResponse, HealthCheckResponse
from core.chain import create_mcq_chain
from core.validation import validate_mcq_json, validate_request_data, MCQValidationError
from core.llm import get_llm_client
from config import (
    APP_NAME,
    APP_VERSION,
    APP_DESCRIPTION,
    MAX_QUESTIONS_PER_REQUEST,
    MIN_QUESTIONS_PER_REQUEST,
    SUPPORTED_DIFFICULTIES,
    REQUEST_TIMEOUT,
    AVERAGE_GENERATION_TIME
)
# Configure logger
logger = logging.getLogger("mcq_generator")

# Create router with proper tags and metadata
router = APIRouter(
    prefix="/api/v1",
    tags=["MCQ Generator"],
    responses={
        500: {"description": "Internal server error"},
        400: {"description": "Bad request"},
        422: {"description": "Validation error"}
    }
)


async def verify_llm_connection():
    """Dependency to verify LLM connection before processing requests."""
    try:
        llm_client = get_llm_client()
        return llm_client
    except Exception as e:
        logger.error(f"LLM connection failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service temporarily unavailable"
        )


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="Health Check",
    description="Check the health status of the MCQ Generator API and its dependencies",
    responses={
        200: {
            "description": "Service is healthy",
            "model": HealthCheckResponse
        },
        503: {"description": "Service unavailable"}
    }
)
async def health_check():
    """
    Comprehensive health check endpoint that verifies all service dependencies.

    Returns:
        HealthCheckResponse: Detailed health status including dependency checks
    """
    start_time = time.time()

    try:
        # Check LLM connection
        dependencies = {}

        try:
            llm_client = get_llm_client()
            dependencies["azure_openai"] = "connected"
            logger.debug("Azure OpenAI connection verified")
        except Exception as e:
            dependencies["azure_openai"] = f"error: {str(e)[:50]}"
            logger.error(f"Azure OpenAI connection failed: {e}")

        # Check LangChain functionality
        try:
            from core.chain import create_mcq_chain
            create_mcq_chain()
            dependencies["langchain"] = "operational"
            logger.debug("LangChain chain creation verified")
        except Exception as e:
            dependencies["langchain"] = f"error: {str(e)[:50]}"
            logger.error(f"LangChain chain creation failed: {e}")

        # Determine overall status
        overall_status = "healthy" if all(
            not dep.startswith("error") for dep in dependencies.values()
        ) else "degraded"

        response = HealthCheckResponse(
            status=overall_status,
            service="MCQ Generator API",
            version="1.0.0",
            timestamp=datetime.now().isoformat(),
            dependencies=dependencies
        )

        response_time = time.time() - start_time
        logger.info(f"Health check completed in {response_time:.3f}s - Status: {overall_status}")

        if overall_status == "degraded":
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content=response.dict()
            )

        return response

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "service": "MCQ Generator API",
                "version": "1.0.0",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
        )


@router.get(
    "/health/ready",
    summary="Readiness Check",
    description="Quick readiness check for load balancers and orchestrators"
)
async def readiness_check():
    """
    Lightweight readiness check for container orchestration.

    Returns:
        dict: Simple ready/not ready status
    """
    try:
        # Quick dependency checks
        get_llm_client()
        return {"status": "ready", "timestamp": datetime.now().isoformat()}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not ready"
        )


@router.get(
    "/health/live",
    summary="Liveness Check",
    description="Basic liveness check to verify the service is running"
)
async def liveness_check():
    """
    Basic liveness check for container orchestration.

    Returns:
        dict: Simple alive status
    """
    return {
        "status": "alive",
        "service": "MCQ Generator API",
        "timestamp": datetime.now().isoformat()
    }


@router.post(
    "/generate-mcq",
    response_model=MCQResponse,
    summary="Generate MCQ Questions",
    description="""
    Generate multiple-choice questions with optional learning roadmap and reference videos.

    This endpoint creates comprehensive educational content including:
    - Customizable number of MCQ questions (5-50)
    - Learning roadmap with sequential steps
    - Reference video links for additional learning
    - Metadata about the generation process
    """,
    responses={
        200: {
            "description": "MCQs generated successfully",
            "model": MCQResponse
        },
        400: {"description": "Invalid request parameters"},
        422: {"description": "Request validation failed"},
        500: {"description": "MCQ generation failed"},
        503: {"description": "AI service unavailable"}
    }
)
async def generate_mcq(
    request: MCQRequest,
    llm_client=Depends(verify_llm_connection)
):
    """
    Generate MCQ questions with enhanced educational content.

    Args:
        request: MCQ generation request with validated parameters
        llm_client: Verified LLM client dependency

    Returns:
        MCQResponse: Generated MCQs with optional roadmap and video references

    Raises:
        HTTPException: For various error conditions with appropriate status codes
    """
    # Log request initiation
    logger.info(
        f"MCQ generation requested - User: {request.username}, "
        f"Topic: {request.topic}, Difficulty: {request.difficulty}, "
        f"Count: {request.question_count}"
    )

    start_time = time.time()
    generation_metadata = {
        "request_timestamp": datetime.now().isoformat(),
        "username": request.username,
        "topic": request.topic
    }

    try:
        # Validate request data
        request_dict = request.dict()
        validated_request = validate_request_data(request_dict)

        # Create and invoke the MCQ generation chain
        chain = create_mcq_chain()

        # Execute chain with timeout protection
        try:
            raw_result = await asyncio.wait_for(
                asyncio.to_thread(chain.invoke, validated_request),
                timeout=120  # 2 minute timeout
            )
        except asyncio.TimeoutError:
            logger.error("MCQ generation timed out")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="MCQ generation timed out. Please try with a smaller question count."
            )

        # Validate and process the generated content
        try:
            mcq_data = validate_mcq_json(raw_result)

            # Add generation timing to metadata
            generation_time = time.time() - start_time
            mcq_data["metadata"]["generation_time_seconds"] = round(generation_time, 2)
            mcq_data["metadata"].update(generation_metadata)

            # Log successful generation
            questions_count = len(mcq_data.get("questions", []))
            roadmap_count = len(mcq_data.get("roadmap", []))
            videos_count = len(mcq_data.get("reference_videos", []))

            logger.info(
                f"Successfully generated content in {generation_time:.2f}s - "
                f"Questions: {questions_count}, Roadmap steps: {roadmap_count}, "
                f"Videos: {videos_count}"
            )

            return MCQResponse(**mcq_data)

        except MCQValidationError as e:
            logger.error(f"MCQ validation error: {e}")
            logger.debug(f"Raw LLM response: {str(raw_result)[:500]}...")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error processing generated content: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected validation error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error processing generated content"
            )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except MCQValidationError as e:
        logger.error(f"Request validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        generation_time = time.time() - start_time
        logger.error(f"Unexpected error during MCQ generation: {e}")
        logger.debug(f"Generation failed after {generation_time:.2f}s")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during MCQ generation"
        )


@router.get(
    "/generate-mcq/stats",
    summary="Generation Statistics",
    description="Get statistics about MCQ generation performance and usage"
)
async def get_generation_stats():
    """
    Get statistics about the MCQ generation service.

    Returns:
        dict: Service statistics and performance metrics
    """
    try:
        stats = {
            "service_info": {
                "name": APP_NAME,
                "version": APP_VERSION,
                "uptime": "Available via health check",
                "description": APP_DESCRIPTION
            },
            "capabilities": {
                "max_questions_per_request": MAX_QUESTIONS_PER_REQUEST,
                "min_questions_per_request": MIN_QUESTIONS_PER_REQUEST,
                "supported_difficulties": SUPPORTED_DIFFICULTIES,
                "features": [
                    "Multiple Choice Questions",
                    "Learning Roadmaps",
                    "Reference Videos",
                    "Detailed Explanations",
                    "Difficulty Levels",
                    "Topic Categorization"
                ]
            },
            "performance": {
                "average_generation_time": AVERAGE_GENERATION_TIME,
                "timeout_limit": f"{REQUEST_TIMEOUT} seconds",
                "concurrent_requests": "Supported"
            },
            "timestamp": datetime.now().isoformat()
        }

        return stats

    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving service statistics"
        )

# Legacy endpoint for backward compatibility (optional)
@router.get("/")
async def root():
    """Health check endpoint for backward compatibility."""
    return {
        "status": "healthy",
        "service": "MCQ Generator API",
        "message": "Use /api/v1/health for detailed health check"
    }


# Batch generation endpoint (optional advanced feature)
@router.post(
    "/generate-mcq/batch",
    summary="Batch MCQ Generation",
    description="Generate MCQs for multiple topics in a single request"
)
async def generate_mcq_batch(
    requests: list[MCQRequest],
    llm_client=Depends(verify_llm_connection)
):
    """
    Generate MCQs for multiple topics in batch.

    Args:
        requests: List of MCQ generation requests
        llm_client: Verified LLM client dependency

    Returns:
        dict: Batch generation results with individual responses
    """
    if len(requests) > 5:  # Limit batch size
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 5 requests allowed in batch"
        )

    logger.info(f"Batch MCQ generation requested for {len(requests)} topics")
    start_time = time.time()
    results = []

    for i, request in enumerate(requests):
        try:
            # Reuse the single generation logic
            response = await generate_mcq(request, llm_client)
            results.append({
                "request_index": i,
                "status": "success",
                "data": response.dict()
            })
        except HTTPException as e:
            results.append({
                "request_index": i,
                "status": "error",
                "error": e.detail,
                "status_code": e.status_code
            })
        except Exception as e:
            logger.error(f"Batch request {i} failed: {e}")
            results.append({
                "request_index": i,
                "status": "error",
                "error": "Unexpected error occurred"
            })

    total_time = time.time() - start_time
    successful_requests = sum(1 for r in results if r["status"] == "success")

    logger.info(f"Batch generation completed in {total_time:.2f}s - {successful_requests}/{len(requests)} successful")

    return {
        "batch_id": f"batch_{int(time.time())}",
        "total_requests": len(requests),
        "successful_requests": successful_requests,
        "failed_requests": len(requests) - successful_requests,
        "total_processing_time": round(total_time, 2),
        "results": results,
        "timestamp": datetime.now().isoformat()
    }