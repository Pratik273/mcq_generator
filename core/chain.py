import logging
from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnablePassthrough
from core.llm import get_llm_client
from langchain_community.tools import DuckDuckGoSearchRun
logger = logging.getLogger("mcq_generator")

def _search_educational_videos(topic: str, count: int = 3) -> list:
    """
    Search for real educational videos using DuckDuckGo search.

    Args:
        topic: The topic to search videos for
        count: Number of videos to find

    Returns:
        list: List of video references with real URLs
    """
    try:
        search = DuckDuckGoSearchRun()

        # Search for educational videos
        search_queries = [
            f"{topic} tutorial youtube",
            f"{topic} course video",
            f"learn {topic} video tutorial"
        ]

        videos = []
        for query in search_queries[:count]:
            try:
                results = search.run(query)
                # Parse results and extract video information
                # This is a simplified version - you might need to enhance parsing
                if "youtube.com" in results or "coursera.org" in results:
                    videos.append({
                        "title": f"{topic.title()} Educational Video",
                        "url": "https://www.youtube.com/results?search_query=" + topic.replace(" ", "+"),
                        "duration": "30:00",
                        "difficulty_level": "intermediate",
                        "description": f"Educational content about {topic}"
                    })
            except Exception as e:
                logger.warning(f"Search failed for query {query}: {e}")
                continue

        return videos if videos else _get_fallback_videos(topic)

    except Exception as e:
        logger.error(f"Failed to search for videos: {e}")
        return _get_fallback_videos(topic)

def _get_fallback_videos(topic: str) -> list:
    """Provide fallback video suggestions when search fails."""
    return [
        {
            "title": f"{topic.title()} - Khan Academy",
            "url": f"https://www.khanacademy.org/search?search_again=1&search_query={topic.replace(' ', '%20')}",
            "duration": "Variable",
            "difficulty_level": "basic",
            "description": f"Khan Academy resources for {topic}"
        },
        {
            "title": f"{topic.title()} - Coursera Courses",
            "url": f"https://www.coursera.org/search?query={topic.replace(' ', '%20')}",
            "duration": "Variable",
            "difficulty_level": "intermediate",
            "description": f"Professional courses on {topic}"
        },
        {
            "title": f"{topic.title()} - YouTube Learning",
            "url": f"https://www.youtube.com/results?search_query={topic.replace(' ', '+')}+tutorial",
            "duration": "Variable",
            "difficulty_level": "mixed",
            "description": f"YouTube tutorials and educational content about {topic}"
        }
    ]

def create_mcq_chain():
    """
    Create the LangChain chain for generating MCQs with roadmap and video references.

    Returns:
        Runnable: LangChain runnable chain for MCQ generation
    """
    try:
        llm = get_llm_client()

        system_template = _get_system_template()
        prompt = ChatPromptTemplate.from_template(system_template)
        json_parser = JsonOutputParser()

        def process_chain_input(inputs):
            """Process inputs and handle video search if needed."""
            result = {
                "topic": inputs.get("topic"),
                "username": inputs.get("username"),
                "difficulty": inputs.get("difficulty"),
                "question_count": inputs.get("question_count"),
                "include_roadmap": inputs.get("include_roadmap"),
                "include_videos": inputs.get("include_videos"),
            }
            return result

        def post_process_output(output):
            """Post-process the LLM output to add real video references."""
            if isinstance(output, dict) and output.get("include_videos") and "<<SEARCH_VIDEOS>>" in str(output):
                topic = output.get("topic", "")
                videos = _search_educational_videos(topic)
                # Replace the placeholder with actual video data
                if "reference_videos" in output:
                    output["reference_videos"] = videos
            return output

        chain = (
            process_chain_input
            | prompt
            | llm
            | json_parser
            | post_process_output
        )

        logger.info("MCQ generation chain created successfully")
        return chain

    except Exception as e:
        logger.error(f"Failed to create MCQ chain: {str(e)}")
        raise

def _get_system_template() -> str:
    return """You are an expert educational content generator specializing in creating comprehensive learning materials.

Generate {question_count} multiple-choice questions (MCQs) on the topic of "{topic}" for user "{username}".

The difficulty level should be "{difficulty}".
Include roadmap: {include_roadmap}
Include reference videos: {include_videos}

**STRICT GUIDELINES:**

1. **MCQ Requirements:**
   - Each question must have exactly 4 options with only ONE correct answer
   - Include detailed explanation for the correct answer (50-150 words)
   - Assign appropriate difficulty level (basic, intermediate, advanced)
   - Ensure questions cover different aspects of the topic
   - Make questions clear, unambiguous, and technically accurate
   - Include specific topic_area for each question

2. **Roadmap Requirements (if include_roadmap is True):**
   - Create 5-8 sequential learning steps
   - Each step should have: step_number, title, description, estimated_duration, prerequisites
   - Cover the complete learning journey from beginner to advanced
   - Provide realistic time estimates
   - Include practical prerequisites

3. **Reference Videos Requirements (if include_videos is True):**
   - Provide 3-5 educational video references
   - Include: title, url, duration, difficulty_level, description
   - Mix different difficulty levels (basic, intermediate, advanced)
   - Focus on real educational platforms and search URLs
   - Suggest relevant learning resources

**JSON STRUCTURE - Follow this EXACTLY:**

{{
  "username": "{username}",
  "topic": "{topic}",
  "timestamp": "2024-01-15T10:30:00.123456",
  "questions": [
    {{
      "question_id": 1,
      "question_text": "Your question here?",
      "explanation": "Detailed explanation of why the correct answer is correct and why others are wrong",
      "options": [
        {{ "option": "Option A text", "is_correct": false }},
        {{ "option": "Option B text", "is_correct": true }},
        {{ "option": "Option C text", "is_correct": false }},
        {{ "option": "Option D text", "is_correct": false }}
      ],
      "difficulty": "basic|intermediate|advanced",
      "topic_area": "Specific subtopic"
    }}
  ],
  "roadmap": [
    {{
      "step_number": 1,
      "title": "Step Title",
      "description": "Detailed description of what to learn",
      "estimated_duration": "X weeks/days",
      "prerequisites": ["Prerequisite 1", "Prerequisite 2"]
    }}
  ],
  "reference_videos": "<<SEARCH_VIDEOS>>",
  "metadata": {{
    "generation_time_seconds": 0,
    "difficulty_distribution": {{}},
    "total_questions": {question_count}
  }}
}}

**CRITICAL REQUIREMENTS:**
- Generate EXACTLY {question_count} questions
- If include_roadmap is False, set "roadmap": null
- If include_videos is False, set "reference_videos": null
- Your response must be ONLY valid JSON, no additional text
- Use search-based URLs for educational content discovery

Generate comprehensive, high-quality educational content that provides real learning value."""

def create_roadmap_chain():
    """
    Create a specialized chain for generating learning roadmaps.

    Returns:
        Runnable: LangChain runnable chain for roadmap generation
    """
    try:
        llm = get_llm_client()

        roadmap_template = """You are an expert curriculum designer. Create a comprehensive learning roadmap for the topic: "{topic}".

Generate 5-8 sequential learning steps that take a complete beginner to an advanced level.

For each step, provide:
- Sequential step number
- Clear, actionable title
- Detailed description (100-200 words)
- Realistic time estimate
- Specific prerequisites

Return valid JSON matching this structure:
{{
  "roadmap": [
    {{
      "step_number": 1,
      "title": "Foundation Step",
      "description": "Detailed description...",
      "estimated_duration": "2-3 weeks",
      "prerequisites": ["Basic computer literacy"]
    }}
  ]
}}"""

        prompt = ChatPromptTemplate.from_template(roadmap_template)
        json_parser = JsonOutputParser()

        chain = (
            {"topic": RunnablePassthrough()}
            | prompt
            | llm
            | json_parser
        )

        logger.info("Roadmap generation chain created successfully")
        return chain

    except Exception as e:
        logger.error(f"Failed to create roadmap chain: {str(e)}")
        raise


def create_video_references_chain():
    """
    Create a specialized chain for generating video references.

    Returns:
        Runnable: LangChain runnable chain for video reference generation
    """
    try:
        llm = get_llm_client()

        video_template = """You are an expert educational content curator. Find 3-5 high-quality video references for the topic: "{topic}".

Provide a mix of beginner, intermediate, and advanced content.

For each video, provide:
- Descriptive title
- Realistic educational platform URL
- Estimated duration
- Difficulty level
- Brief description of content

Return valid JSON matching this structure:
{{
  "reference_videos": [
    {{
      "title": "Comprehensive Video Title",
      "url": "https://www.youtube.com/watch?v=realistic_id",
      "duration": "25:30",
      "difficulty_level": "basic",
      "description": "Brief description of video content and learning outcomes"
    }}
  ]
}}"""

        prompt = ChatPromptTemplate.from_template(video_template)
        json_parser = JsonOutputParser()

        chain = (
            {"topic": RunnablePassthrough()}
            | prompt
            | llm
            | json_parser
        )

        logger.info("Video references chain created successfully")
        return chain

    except Exception as e:
        logger.error(f"Failed to create video references chain: {str(e)}")
        raise