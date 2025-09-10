from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum


class DifficultyLevel(str, Enum):
    """Enumeration for difficulty levels."""
    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    MIXED = "mixed"


class MCQOption(BaseModel):
    """Model for MCQ option with validation."""
    option: str = Field(..., description="The option text", min_length=1, max_length=500)
    is_correct: bool = Field(..., description="Whether this option is correct")

    class Config:
        schema_extra = {
            "example": {
                "option": "Python is an interpreted language",
                "is_correct": True
            }
        }


class RoadmapStep(BaseModel):
    """Model for learning roadmap steps."""
    step_number: int = Field(..., description="Sequential step number", ge=1)
    title: str = Field(..., description="Step title", min_length=1, max_length=200)
    description: str = Field(..., description="Step description", min_length=1, max_length=1000)
    estimated_duration: str = Field(..., description="Estimated time to complete this step")
    prerequisites: List[str] = Field(default=[], description="Prerequisites for this step")

    class Config:
        schema_extra = {
            "example": {
                "step_number": 1,
                "title": "Python Basics",
                "description": "Learn Python syntax and basic programming concepts",
                "estimated_duration": "2-3 weeks",
                "prerequisites": ["Basic computer knowledge"]
            }
        }


class ReferenceVideo(BaseModel):
    """Model for reference video links."""
    title: str = Field(..., description="Video title", min_length=1, max_length=200)
    url: str = Field(..., description="Video URL")
    duration: Optional[str] = Field(None, description="Video duration")
    difficulty_level: DifficultyLevel = Field(..., description="Video difficulty level")
    description: Optional[str] = Field(None, description="Video description", max_length=500)

    @validator('url')
    def validate_url(cls, v):
        """Validate URL format."""
        if not v.startswith(('http://', 'https://')):
            raise ValueError('URL must start with http:// or https://')
        return v

    class Config:
        schema_extra = {
            "example": {
                "title": "Python Programming Tutorial for Beginners",
                "url": "https://www.youtube.com/watch?v=example",
                "duration": "45:30",
                "difficulty_level": "basic",
                "description": "Comprehensive introduction to Python programming"
            }
        }


class MCQQuestion(BaseModel):
    """Model for MCQ question with enhanced validation."""
    question_id: int = Field(..., description="Unique identifier for the question", ge=1)
    question_text: str = Field(..., description="The question text", min_length=10, max_length=1000)
    explanation: str = Field(..., description="Explanation of the correct answer", min_length=10, max_length=2000)
    options: List[MCQOption] = Field(..., description="List of options for the question", min_items=4, max_items=4)
    difficulty: DifficultyLevel = Field(..., description="Question difficulty level")
    topic_area: Optional[str] = Field(None, description="Specific topic area within the main topic")

    @validator('options')
    def validate_options(cls, v):
        """Validate that exactly one option is correct."""
        correct_count = sum(1 for option in v if option.is_correct)
        if correct_count != 1:
            raise ValueError('Exactly one option must be marked as correct')
        return v

    class Config:
        schema_extra = {
            "example": {
                "question_id": 1,
                "question_text": "What is the output of print(type([]))?",
                "explanation": "The type() function returns the class type of an object. For an empty list [], it returns <class 'list'>",
                "options": [
                    {"option": "<class 'list'>", "is_correct": True},
                    {"option": "<class 'array'>", "is_correct": False},
                    {"option": "<class 'tuple'>", "is_correct": False},
                    {"option": "<class 'dict'>", "is_correct": False}
                ],
                "difficulty": "basic",
                "topic_area": "Data Types"
            }
        }


class MCQRequest(BaseModel):
    """Request model for MCQ generation with enhanced validation."""
    username: str = Field(
        ...,
        description="Username of the person requesting MCQs",
        min_length=2,
        max_length=50,
        pattern=r'^[a-zA-Z0-9_-]+$'
    )
    topic: str = Field(
        ...,
        description="Topic or area for which MCQs need to be generated",
        min_length=2,
        max_length=200
    )
    difficulty: DifficultyLevel = Field(
        DifficultyLevel.MIXED,
        description="Difficulty level for the MCQs"
    )
    question_count: Optional[int] = Field(
        20,
        description="Number of questions to generate",
        ge=5,
        le=50
    )
    include_roadmap: bool = Field(
        True,
        description="Whether to include learning roadmap"
    )
    include_videos: bool = Field(
        True,
        description="Whether to include reference videos"
    )

    class Config:
        schema_extra = {
            "example": {
                "username": "john_doe",
                "topic": "Python Programming Basics",
                "difficulty": "mixed",
                "question_count": 20,
                "include_roadmap": True,
                "include_videos": True
            }
        }


class MCQResponse(BaseModel):
    """Response model for MCQ generation with enhanced fields."""
    username: str = Field(..., description="Username of the person who requested the MCQs")
    topic: str = Field(..., description="Topic for which MCQs were generated")
    timestamp: str = Field(..., description="ISO timestamp when MCQs were generated")
    questions: List[MCQQuestion] = Field(..., description="List of generated MCQ questions")
    roadmap: Optional[List[RoadmapStep]] = Field(None, description="Learning roadmap for the topic")
    reference_videos: Optional[List[ReferenceVideo]] = Field(None, description="Reference video links")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the generation process"
    )

    class Config:
        schema_extra = {
            "example": {
                "username": "john_doe",
                "topic": "Python Programming Basics",
                "timestamp": "2024-01-15T10:30:00.123456",
                "questions": [],
                "roadmap": [],
                "reference_videos": [],
                "metadata": {
                    "generation_time_seconds": 2.45,
                    "difficulty_distribution": {"basic": 8, "intermediate": 10, "advanced": 2},
                    "total_questions": 20
                }
            }
        }


class HealthCheckResponse(BaseModel):
    """Response model for health check endpoints."""
    status: str = Field(..., description="Service status")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    timestamp: str = Field(..., description="Current timestamp")
    dependencies: Dict[str, str] = Field(default_factory=dict, description="Status of dependencies")

    class Config:
        schema_extra = {
            "example": {
                "status": "healthy",
                "service": "MCQ Generator API",
                "version": "1.0.0",
                "timestamp": "2024-01-15T10:30:00.123456",
                "dependencies": {
                    "azure_openai": "connected",
                    "langchain": "operational"
                }
            }
        }