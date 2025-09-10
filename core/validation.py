import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import ValidationError
from models import MCQResponse, MCQQuestion, RoadmapStep, ReferenceVideo

logger = logging.getLogger("mcq_generator")


class MCQValidationError(Exception):
    """Custom exception for MCQ validation errors."""
    pass


def validate_mcq_json(mcq_json_str: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate and fix the MCQ JSON structure with comprehensive error handling.

    Args:
        mcq_json_str: JSON string or dict representing MCQ data

    Returns:
        Dict[str, Any]: Validated and corrected MCQ data

    Raises:
        MCQValidationError: If the JSON structure is invalid or required fields are missing
    """
    try:
        # Parse JSON if string
        mcq_data = _parse_json_input(mcq_json_str)

        # Validate and fix basic structure
        mcq_data = _validate_basic_structure(mcq_data)

        # Validate questions
        mcq_data["questions"] = _validate_questions(mcq_data.get("questions", []))

        # Validate roadmap if present
        if mcq_data.get("roadmap"):
            mcq_data["roadmap"] = _validate_roadmap(mcq_data["roadmap"])

        # Validate reference videos if present
        if mcq_data.get("reference_videos"):
            mcq_data["reference_videos"] = _validate_reference_videos(mcq_data["reference_videos"])

        # Add/update metadata
        mcq_data["metadata"] = _generate_metadata(mcq_data)

        # Final validation using Pydantic model
        try:
            validated_response = MCQResponse(**mcq_data)
            logger.info(f"Successfully validated MCQ data with {len(mcq_data['questions'])} questions")
            return validated_response.dict()
        except ValidationError as e:
            logger.warning(f"Pydantic validation issues: {e}")
            # Return the manually validated data if Pydantic fails
            return mcq_data

    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        raise MCQValidationError(f"Invalid JSON format: {e}")
    except Exception as e:
        logger.error(f"Validation error: {e}")
        raise MCQValidationError(f"Error validating MCQ data: {e}")


def _parse_json_input(mcq_json_str: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Parse JSON input and handle various formats."""
    if isinstance(mcq_json_str, dict):
        return mcq_json_str
    elif isinstance(mcq_json_str, str):
        # Try to clean common JSON formatting issues
        cleaned_json = mcq_json_str.strip()
        if cleaned_json.startswith('```json'):
            cleaned_json = cleaned_json[7:]
        if cleaned_json.endswith('```'):
            cleaned_json = cleaned_json[:-3]
        return json.loads(cleaned_json.strip())
    else:
        raise MCQValidationError(f"Invalid input type: {type(mcq_json_str)}")


def _validate_basic_structure(mcq_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and add basic required fields."""
    required_fields = ["username", "topic", "timestamp", "questions"]

    for field in required_fields:
        if field not in mcq_data:
            if field == "timestamp":
                mcq_data[field] = datetime.now().isoformat()
                logger.info("Added missing timestamp")
            else:
                raise MCQValidationError(f"Missing required field: {field}")

    # Ensure questions is a list
    if not isinstance(mcq_data["questions"], list):
        raise MCQValidationError("'questions' must be an array")

    return mcq_data


def _validate_questions(questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Validate and fix question data."""
    validated_questions = []

    for i, question in enumerate(questions):
        try:
            # Add question_id if missing
            if "question_id" not in question:
                question["question_id"] = i + 1

            # Validate required fields
            required_fields = ["question_text", "explanation", "options", "difficulty"]
            for field in required_fields:
                if field not in question:
                    raise MCQValidationError(
                        f"Question {question.get('question_id', i+1)} missing field: {field}"
                    )

            # Validate options
            question["options"] = _validate_question_options(
                question.get("options", []),
                question.get("question_id", i+1)
            )

            # Add topic_area if missing
            if "topic_area" not in question:
                question["topic_area"] = "General"

            validated_questions.append(question)

        except Exception as e:
            logger.error(f"Error validating question {i+1}: {e}")
            # Skip invalid questions but log the error
            continue

    if len(validated_questions) == 0:
        raise MCQValidationError("No valid questions found")

    return validated_questions


def _validate_question_options(options: List[Dict[str, Any]], question_id: int) -> List[Dict[str, Any]]:
    """Validate and fix question options."""
    if not isinstance(options, list):
        raise MCQValidationError(f"Question {question_id}: 'options' must be an array")

    if len(options) != 4:
        logger.warning(f"Question {question_id}: Expected 4 options, got {len(options)}")
        # Try to pad or trim options
        if len(options) < 4:
            while len(options) < 4:
                options.append({"option": f"Option {len(options) + 1}", "is_correct": False})
        elif len(options) > 4:
            options = options[:4]

    # Validate correct answer count
    correct_options = [opt for opt in options if opt.get("is_correct", False)]

    if len(correct_options) != 1:
        logger.warning(
            f"Question {question_id}: Expected 1 correct option, got {len(correct_options)}. Auto-correcting..."
        )
        # Reset all to false first
        for opt in options:
            opt["is_correct"] = False

        # Set first option as correct if no correct option exists
        if not correct_options:
            options[0]["is_correct"] = True
        else:
            # Keep the first correct option, make others false
            first_correct_index = next(
                i for i, opt in enumerate(options)
                if any(co.get("option") == opt.get("option") for co in correct_options)
            )
            options[first_correct_index]["is_correct"] = True

    return options


def _validate_roadmap(roadmap: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Validate roadmap data."""
    if not isinstance(roadmap, list):
        logger.warning("Roadmap must be a list, converting to empty list")
        return []

    validated_roadmap = []
    for i, step in enumerate(roadmap):
        try:
            # Add step_number if missing
            if "step_number" not in step:
                step["step_number"] = i + 1

            # Validate required fields
            required_fields = ["title", "description", "estimated_duration"]
            for field in required_fields:
                if field not in step or not step[field]:
                    logger.warning(f"Roadmap step {i+1} missing or empty field: {field}")
                    continue

            # Ensure prerequisites is a list
            if "prerequisites" not in step:
                step["prerequisites"] = []
            elif not isinstance(step["prerequisites"], list):
                step["prerequisites"] = []

            validated_roadmap.append(step)

        except Exception as e:
            logger.error(f"Error validating roadmap step {i+1}: {e}")
            continue

    return validated_roadmap


def _validate_reference_videos(videos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Validate reference video data."""
    if not isinstance(videos, list):
        logger.warning("Reference videos must be a list, converting to empty list")
        return []

    validated_videos = []
    for i, video in enumerate(videos):
        try:
            # Validate required fields
            required_fields = ["title", "url", "difficulty_level"]
            for field in required_fields:
                if field not in video or not video[field]:
                    logger.warning(f"Video {i+1} missing or empty field: {field}")
                    continue

            # Validate URL format
            if not video["url"].startswith(("http://", "https://")):
                logger.warning(f"Video {i+1} has invalid URL format")
                continue

            # Set default duration if missing
            if "duration" not in video:
                video["duration"] = "Unknown"

            # Set default description if missing
            if "description" not in video:
                video["description"] = "Educational video content"

            validated_videos.append(video)

        except Exception as e:
            logger.error(f"Error validating video {i+1}: {e}")
            continue

    return validated_videos


def _generate_metadata(mcq_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate metadata for the MCQ response."""
    questions = mcq_data.get("questions", [])

    # Calculate difficulty distribution
    difficulty_dist = {}
    for question in questions:
        difficulty = question.get("difficulty", "unknown")
        difficulty_dist[difficulty] = difficulty_dist.get(difficulty, 0) + 1

    metadata = {
        "total_questions": len(questions),
        "difficulty_distribution": difficulty_dist,
        "has_roadmap": bool(mcq_data.get("roadmap")),
        "has_reference_videos": bool(mcq_data.get("reference_videos")),
        "roadmap_steps": len(mcq_data.get("roadmap", [])),
        "reference_video_count": len(mcq_data.get("reference_videos", [])),
        "validation_timestamp": datetime.now().isoformat()
    }

    # Add existing metadata if present
    existing_metadata = mcq_data.get("metadata", {})
    metadata.update(existing_metadata)

    return metadata


def validate_request_data(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate incoming request data.

    Args:
        request_data: Request data dictionary

    Returns:
        Dict[str, Any]: Validated request data

    Raises:
        MCQValidationError: If request data is invalid
    """
    try:
        # Check required fields
        required_fields = ["username", "topic"]
        for field in required_fields:
            if field not in request_data or not request_data[field]:
                raise MCQValidationError(f"Missing or empty required field: {field}")

        # Validate username format
        username = request_data["username"]
        if not username.replace("_", "").replace("-", "").isalnum():
            raise MCQValidationError("Username must contain only alphanumeric characters, hyphens, and underscores")

        # Set defaults
        request_data.setdefault("difficulty", "mixed")
        request_data.setdefault("question_count", 20)
        request_data.setdefault("include_roadmap", True)
        request_data.setdefault("include_videos", True)

        # Validate question count
        question_count = request_data.get("question_count", 20)
        if not isinstance(question_count, int) or question_count < 5 or question_count > 50:
            request_data["question_count"] = 20
            logger.warning("Invalid question_count, defaulting to 20")

        return request_data

    except Exception as e:
        logger.error(f"Request validation error: {e}")
        raise MCQValidationError(f"Invalid request data: {e}")