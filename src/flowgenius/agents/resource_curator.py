"""
FlowGenius Resource Curator Agent

This module contains the AI agent responsible for finding and curating 
learning resources (videos, articles, papers) for learning units.
"""

import json
from typing import List, Optional, Dict, Any
from openai import OpenAI
from pydantic import BaseModel

from ..models.project import LearningResource, LearningUnit


class ResourceRequest(BaseModel):
    """Request for resource curation."""
    unit: LearningUnit
    min_video_resources: int = 1
    min_reading_resources: int = 1
    max_total_resources: int = 5
    difficulty_preference: Optional[str] = None


class ResourceCuratorAgent:
    """
    AI agent for curating learning resources for specific learning units.
    
    Takes a learning unit and generates appropriate video and reading resources
    that align with the unit's learning objectives and content.
    """
    
    def __init__(self, openai_client: OpenAI, model: str = "gpt-4o-mini"):
        self.client = openai_client
        self.model = model
    
    def curate_resources(self, request: ResourceRequest) -> List[LearningResource]:
        """
        Curate learning resources for a specific unit.
        
        Args:
            request: ResourceRequest with unit and resource requirements
            
        Returns:
            List of LearningResource objects with videos and readings
        """
        try:
            # Generate resources using AI
            resources = self._generate_resources_with_ai(request)
            
            # Validate that we meet minimum requirements
            video_count = sum(1 for r in resources if r.type == "video")
            reading_count = sum(1 for r in resources if r.type in ["article", "paper", "documentation"])
            
            if video_count < request.min_video_resources:
                resources.extend(self._generate_fallback_videos(request, request.min_video_resources - video_count))
            
            if reading_count < request.min_reading_resources:
                resources.extend(self._generate_fallback_readings(request, request.min_reading_resources - reading_count))
            
            return resources[:request.max_total_resources]
            
        except Exception as e:
            # Fallback to basic resources if AI fails
            return self._create_fallback_resources(request)
    
    def _generate_resources_with_ai(self, request: ResourceRequest) -> List[LearningResource]:
        """
        Use AI to generate appropriate resources for the unit.
        """
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(request)
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        # Parse the response
        content = response.choices[0].message.content
        resources_data = json.loads(content)
        
        # Convert to LearningResource objects
        resources = []
        for resource_data in resources_data["resources"]:
            resource = LearningResource(
                title=resource_data["title"],
                url=resource_data["url"],
                type=resource_data["type"],
                description=resource_data.get("description"),
                estimated_time=resource_data.get("estimated_time")
            )
            resources.append(resource)
        
        return resources
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt for the AI."""
        return """You are an expert learning resource curator who finds high-quality, relevant learning materials.

Your job is to recommend specific learning resources (videos, articles, papers, tutorials) that:
1. Directly support the learning objectives of the unit
2. Are from reputable sources and creators
3. Have appropriate difficulty levels
4. Provide diverse perspectives and learning styles
5. Include both video and text-based resources

Return your response as valid JSON with this exact structure:
{
  "resources": [
    {
      "title": "Specific, descriptive title of the resource",
      "url": "https://example.com/resource-url",
      "type": "video|article|paper|tutorial|documentation",
      "description": "Brief description of what this resource covers and why it's valuable",
      "estimated_time": "15 min|2 hours|etc"
    }
  ]
}

Guidelines:
- Include a mix of videos and reading materials
- Prioritize well-known educational platforms (YouTube channels, Khan Academy, Coursera, academic papers, etc.)
- Ensure URLs are realistic and follow proper format
- Estimate time accurately for consumption
- Make descriptions specific and helpful
- Focus on quality over quantity
- Include resources for different learning preferences"""

    def _build_user_prompt(self, request: ResourceRequest) -> str:
        """Build the user prompt with the specific unit information."""
        unit = request.unit
        
        prompt = f"""Find learning resources for this unit:

Unit Title: {unit.title}
Description: {unit.description}

Learning Objectives:
{chr(10).join(f"- {obj}" for obj in unit.learning_objectives)}
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
        """Generate fallback video resources if AI didn't provide enough."""
        fallback_videos = []
        unit = request.unit
        
        for i in range(count):
            video = LearningResource(
                title=f"{unit.title} - Video Tutorial {i + 1}",
                url=f"https://youtube.com/search?q={unit.title.replace(' ', '+')}_tutorial",
                type="video",
                description=f"Video tutorial covering {unit.title} concepts",
                estimated_time="20-30 min"
            )
            fallback_videos.append(video)
        
        return fallback_videos
    
    def _generate_fallback_readings(self, request: ResourceRequest, count: int) -> List[LearningResource]:
        """Generate fallback reading resources if AI didn't provide enough."""
        fallback_readings = []
        unit = request.unit
        
        for i in range(count):
            reading = LearningResource(
                title=f"{unit.title} - Reference Article {i + 1}",
                url=f"https://en.wikipedia.org/wiki/{unit.title.replace(' ', '_')}",
                type="article",
                description=f"Reference material covering {unit.title} fundamentals",
                estimated_time="10-15 min"
            )
            fallback_readings.append(reading)
        
        return fallback_readings
    
    def _create_fallback_resources(self, request: ResourceRequest) -> List[LearningResource]:
        """
        Create basic fallback resources if AI generation completely fails.
        """
        unit = request.unit
        topic = unit.title
        
        resources = []
        
        # Add video resources
        for i in range(request.min_video_resources):
            video = LearningResource(
                title=f"Introduction to {topic}",
                url=f"https://youtube.com/search?q={topic.replace(' ', '+')}_introduction",
                type="video",
                description=f"Introductory video about {topic}",
                estimated_time="15-20 min"
            )
            resources.append(video)
        
        # Add reading resources
        for i in range(request.min_reading_resources):
            article = LearningResource(
                title=f"{topic} - Overview",
                url=f"https://en.wikipedia.org/wiki/{topic.replace(' ', '_')}",
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
        type_emoji = {
            "video": "🎥",
            "article": "📖", 
            "paper": "📄",
            "tutorial": "🛠️",
            "documentation": "📋"
        }
        
        emoji = type_emoji.get(resource.type, "📎")
        formatted_resource = f"{emoji} {link}"
        
        if resource.estimated_time:
            formatted_resource += f" *({resource.estimated_time})*"
        
        if resource.description:
            formatted_resource += f"\n  > {resource.description}"
        
        formatted.append(formatted_resource)
    
    return formatted 