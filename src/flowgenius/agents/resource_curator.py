"""
FlowGenius Resource Curator Agent

This module contains the AI agent responsible for finding and curating 
learning resources (videos, articles, papers) for learning units.
"""

import json
import logging
from typing import List, Optional, Dict, Any, Tuple
from openai import OpenAI
from pydantic import BaseModel, ValidationError

from ..models.project import LearningResource, LearningUnit
from ..models.settings import DefaultSettings, FallbackUrls, get_resource_emoji

# Set up module logger
logger = logging.getLogger(__name__)


class ResourceRequest(BaseModel):
    """Request for resource curation."""
    unit: LearningUnit
    min_video_resources: int = 1
    min_reading_resources: int = 1
    max_total_resources: int = 5
    difficulty_preference: Optional[str] = None


class ResourceData(BaseModel):
    """Pydantic model for validating AI-generated resource data."""
    title: str
    url: str
    type: str
    description: str
    estimated_time: Optional[str] = None
    difficulty_level: Optional[str] = None


class ResourcesResponse(BaseModel):
    """Pydantic model for validating complete AI response."""
    resources: List[ResourceData]


class ResourceCuratorAgent:
    """
    AI agent responsible for curating learning resources for units.
    
    Finds and organizes videos, articles, tutorials, and other learning materials
    that align with unit objectives and learner preferences.
    """
    
    def __init__(self, openai_client: OpenAI, model: str = DefaultSettings.DEFAULT_MODEL) -> None:
        """
        Initialize the resource curator with OpenAI client.
        
        Args:
            openai_client: Configured OpenAI client
            model: OpenAI model to use for resource curation
        """
        self.client = openai_client
        self.model = model
    
    def curate_resources(
        self,
        request: ResourceRequest
    ) -> Tuple[List[LearningResource], bool]:
        """
        Curate learning resources for a specific unit.
        
        Args:
            request: ResourceRequest with unit and requirements
            
        Returns:
            Tuple of (List of curated LearningResource objects, success boolean)
        """
        unit = request.unit
        logger.info(f"Curating resources for unit: {unit.id}")
        
        try:
            # Generate resources using AI with validation
            resources_data, ai_success = self._generate_resources_with_validation(
                unit, request.min_video_resources, request.min_reading_resources, request.max_total_resources
            )
            
            # Convert to LearningResource objects
            resources = []
            for resource_data in resources_data:
                resource = LearningResource(
                    title=resource_data.title,
                    url=resource_data.url,
                    type=resource_data.type,
                    description=resource_data.description,
                    estimated_time=resource_data.estimated_time or self._estimate_time_by_type(resource_data.type)
                )
                resources.append(resource)
            
            # Check if we have sufficient resources, supplement with fallback if needed
            video_count = sum(1 for r in resources if r.type == "video")
            reading_count = sum(1 for r in resources if r.type in ["article", "paper", "documentation"])
            
            # Add fallback resources if needed
            if video_count < request.min_video_resources:
                fallback_videos = self._generate_fallback_videos(request, request.min_video_resources - video_count)
                resources.extend(fallback_videos)
            
            if reading_count < request.min_reading_resources:
                fallback_readings = self._generate_fallback_readings(request, request.min_reading_resources - reading_count)
                resources.extend(fallback_readings)
            
            logger.info(f"Successfully curated {len(resources)} resources for unit {unit.id}")
            return resources, ai_success
            
        except (ValueError, json.JSONDecodeError, ValidationError, TimeoutError) as e:
            logger.error(f"Failed to curate resources for unit {unit.id}: {e}", exc_info=True)
            # Return fallback resources
            fallback_resources = self._create_fallback_resources(request)
            return fallback_resources, False
    
    def _generate_resources_with_validation(
        self,
        unit: LearningUnit,
        min_video_resources: int,
        min_reading_resources: int,
        max_total_resources: int
    ) -> Tuple[List[ResourceData], bool]:
        """
        Generate resources using OpenAI API with proper JSON validation.
        
        Args:
            unit: Learning unit to generate resources for
            min_video_resources: Minimum video resources required
            min_reading_resources: Minimum reading resources required
            max_total_resources: Maximum total resources to generate
            
        Returns:
            Tuple of (List of validated ResourceData objects, success boolean)
        """
        prompt = self._build_resource_prompt(unit, min_video_resources, min_reading_resources, max_total_resources)
        
        # Add JSON schema to the prompt
        json_schema = """
{
    "resources": [
        {
            "title": "Resource Title",
            "url": "https://example.com",
            "type": "video|article|paper|documentation|tutorial",
            "description": "Brief description of the resource",
            "estimated_time": "15-20 min"
        }
    ]
}"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert resource curator who finds the best learning materials for educational content. Focus on reputable, high-quality sources. Always respond with valid JSON."
                    },
                    {
                        "role": "user",
                        "content": f"{prompt}\n\nExpected JSON format:\n{json_schema}"
                    }
                ],
                temperature=0.7,
                max_tokens=DefaultSettings.RESOURCE_GENERATION_MAX_TOKENS,
                response_format={"type": "json_object"}  # Force JSON response
            )
            
            content = response.choices[0].message.content
            
            # Check for None or empty content
            if not content:
                logger.error("AI returned empty content")
                return [], False
                
            content = content.strip()
            logger.debug(f"AI response content: {content[:200]}...")
            
            # Parse and validate JSON response
            try:
                resources_json = json.loads(content)
                logger.debug(f"Parsed JSON structure: {type(resources_json)}")
                
                # Validate with Pydantic
                validated_response = ResourcesResponse(**resources_json)
                logger.info(f"Successfully validated {len(validated_response.resources)} resources")
                return validated_response.resources, True
                
            except (json.JSONDecodeError, ValidationError) as e:
                logger.error(f"AI response validation failed: {e}")
                logger.debug(f"Full AI response: {content}")
                # Return empty list and failure status
                return [], False
                
        except (ValueError, AttributeError) as e:
            logger.error(f"Failed to generate resources: {e}", exc_info=True)
            # Return empty list to trigger fallback
            return [], False
    
    def _build_resource_prompt(
        self,
        unit: LearningUnit,
        min_video_resources: int,
        min_reading_resources: int,
        max_total_resources: int
    ) -> str:
        """
        Build the prompt for generating resources using OpenAI API.
        
        Args:
            unit: Learning unit to generate resources for
            min_video_resources: Minimum video resources required
            min_reading_resources: Minimum reading resources required
            max_total_resources: Maximum total resources to generate
            
        Returns:
            Prompt string for OpenAI API
        """
        prompt = f"""Find learning resources for this unit:

Unit Title: {unit.title}
Description: {unit.description}

Learning Objectives:
{"\n".join(f"- {obj}" for obj in unit.learning_objectives)}
"""
        
        if unit.estimated_duration:
            prompt += f"\nEstimated Unit Duration: {unit.estimated_duration}"
        
        prompt += f"""

Requirements:
- At least {min_video_resources} video resource(s)
- At least {min_reading_resources} reading resource(s) (articles/papers/documentation)
- Maximum {max_total_resources} total resources
"""
        
        prompt += "\n\nReturn valid JSON following the specified structure."
        
        return prompt
    
    def _estimate_time_by_type(self, resource_type: str) -> str:
        """
        Estimate time based on resource type.
        
        Args:
            resource_type: Type of resource
            
        Returns:
            Estimated time for the resource
        """
        time_estimates = {
            "video": "10-20 min",
            "article": "15-25 min",
            "tutorial": "30-45 min",
            "documentation": "20-30 min",
            "book": "60+ min",
            "course": "2-4 hours",
            "podcast": "20-40 min",
            "paper": "30-45 min",
            "guide": "25-35 min",
            "reference": "10-15 min"
        }
        
        # Return specific estimate or default
        return time_estimates.get(resource_type.lower(), "15-20 min")
    
    def _build_system_prompt(self) -> str:
        """
        Build the system prompt for resource curation.
        
        Returns:
            System prompt string
        """
        return """You are an expert learning resource curator who finds the best learning materials for educational content. 
Focus on reputable, high-quality sources. Return responses in valid JSON format with a 'resources' array containing 
objects with title, url, type, description, and estimated_time fields. Include both video and article/reading resources."""
    
    def _build_user_prompt(self, request: ResourceRequest) -> str:
        """
        Build the user prompt for resource curation.
        
        Args:
            request: ResourceRequest with unit and requirements
            
        Returns:
            User prompt string
        """
        unit = request.unit
        prompt = f"""Find learning resources for this unit:

Unit Title: {unit.title}
Description: {unit.description}

Learning Objectives:
{"\n".join(f"- {obj}" for obj in unit.learning_objectives)}
"""
        
        if unit.estimated_duration:
            prompt += f"\nEstimated Unit Duration: {unit.estimated_duration}"
        
        prompt += f"""

Requirements:
- At least {request.min_video_resources} video resource(s)
- At least {request.min_reading_resources} reading resource(s) (articles/papers/documentation)
- Maximum {request.max_total_resources} total resources
"""
        
        if request.difficulty_preference:
            prompt += f"- Difficulty level: {request.difficulty_preference}"
        
        prompt += "\n\nReturn valid JSON following the specified structure."
        
        return prompt
    
    def _generate_fallback_videos(self, request: ResourceRequest, count: int) -> List[LearningResource]:
        """
        Generate fallback video resources.
        
        Args:
            request: ResourceRequest with unit context
            count: Number of videos to generate
            
        Returns:
            List of fallback video resources
        """
        topic = request.unit.title
        videos = []
        
        for i in range(count):
            video = LearningResource(
                title=f"Introduction to {topic} - Part {i+1}",
                url=FallbackUrls.youtube_tutorial_part(topic, i+1),
                type="video",
                description=f"Video tutorial about {topic}",
                estimated_time="15-20 min"
            )
            videos.append(video)
        
        return videos
    
    def _generate_fallback_readings(self, request: ResourceRequest, count: int) -> List[LearningResource]:
        """
        Generate fallback reading resources.
        
        Args:
            request: ResourceRequest with unit context
            count: Number of readings to generate
            
        Returns:
            List of fallback reading resources
        """
        topic = request.unit.title
        readings = []
        
        for i in range(count):
            article = LearningResource(
                title=f"{topic} - Guide {i+1}",
                url=FallbackUrls.wikipedia_guide(topic, i+1),
                type="article",
                description=f"Comprehensive guide about {topic}",
                estimated_time="10-15 min"
            )
            readings.append(article)
        
        return readings
    
    def _create_fallback_resources(self, request: ResourceRequest) -> List[LearningResource]:
        """
        Create basic fallback resources if AI generation completely fails.
        
        Args:
            request: ResourceRequest with requirements
            
        Returns:
            List of fallback resources
        """
        resources = []
        
        # Add required video resources
        videos = self._generate_fallback_videos(request, request.min_video_resources)
        resources.extend(videos)
        
        # Add required reading resources
        readings = self._generate_fallback_readings(request, request.min_reading_resources)
        resources.extend(readings)
        
        return resources
    
    def _create_fallback_resources_for_unit(self, unit: LearningUnit) -> List[LearningResource]:
        """
        Create basic fallback resources for a unit (legacy method).
        
        Args:
            unit: LearningUnit to create resources for
            
        Returns:
            List of fallback resources
        """
        topic = unit.title
        
        resources = []
        
        # Add video resources
        for i in range(DefaultSettings.MIN_VIDEO_RESOURCES):
            video = LearningResource(
                title=f"Introduction to {topic}",
                url=FallbackUrls.youtube_introduction(topic),
                type="video",
                description=f"Introductory video about {topic}",
                estimated_time="15-20 min"
            )
            resources.append(video)
        
        # Add reading resources
        for i in range(DefaultSettings.MIN_READING_RESOURCES):
            article = LearningResource(
                title=f"{topic} - Overview",
                url=FallbackUrls.wikipedia_article(topic),
                type="article", 
                description=f"Comprehensive overview of {topic}",
                estimated_time="10-15 min"
            )
            resources.append(article)
        
        return resources


def format_resources_for_obsidian(resources: List[LearningResource], use_obsidian_links: bool = True) -> List[str]:
    """
    Format resources as markdown links compatible with Obsidian.
    
    Args:
        resources: List of LearningResource objects
        use_obsidian_links: Whether to use Obsidian-style formatting
        
    Returns:
        List of formatted markdown strings
    """
    formatted = []
    
    for resource in resources:
        if use_obsidian_links:
            # Obsidian-style external link: [title](url)
            link = f"[{resource.title}]({resource.url})"
        else:
            # Standard markdown link
            link = f"[{resource.title}]({resource.url})"
        
        # Add type emoji for visual distinction
        emoji = get_resource_emoji(resource.type)
        formatted_resource = f"{emoji} {link}"
        
        if resource.estimated_time:
            formatted_resource += f" *({resource.estimated_time})*"
        
        if resource.description:
            formatted_resource += f"\n  > {resource.description}"
        
        formatted.append(formatted_resource)
    
    return formatted 