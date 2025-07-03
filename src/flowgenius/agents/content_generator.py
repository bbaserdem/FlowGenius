"""
FlowGenius Content Generator

This module provides the integrated content generation functionality,
combining resource curation and engage task generation for learning units.
"""

import logging
from typing import List, Optional, Dict, Any, Tuple
from openai import OpenAI
from pydantic import BaseModel, Field

from ..models.project import LearningUnit, LearningResource, EngageTask
from ..models.settings import DefaultSettings, FallbackUrls
from .resource_curator import ResourceCuratorAgent, ResourceRequest
from .engage_task_generator import EngageTaskGeneratorAgent, TaskGenerationRequest

# Set up module logger
logger = logging.getLogger(__name__)


class ContentGenerationRequest(BaseModel):
    """Request for complete content generation (resources + tasks) for a unit."""
    unit: LearningUnit
    min_video_resources: int = DefaultSettings.MIN_VIDEO_RESOURCES
    min_reading_resources: int = DefaultSettings.MIN_READING_RESOURCES
    max_total_resources: int = DefaultSettings.MAX_TOTAL_RESOURCES
    num_engage_tasks: int = DefaultSettings.DEFAULT_NUM_TASKS
    difficulty_preference: Optional[str] = None
    focus_on_application: bool = True
    use_obsidian_links: bool = True


class GeneratedContent(BaseModel):
    """Complete generated content for a learning unit."""
    unit_id: str = Field(description="ID of the unit")
    resources: List[LearningResource] = Field(default_factory=list)
    engage_tasks: List[EngageTask] = Field(default_factory=list)
    formatted_resources: List[str] = Field(default_factory=list)
    formatted_tasks: List[str] = Field(default_factory=list)
    generation_success: bool = Field(default=False)
    generation_notes: List[str] = Field(default_factory=list)


class ContentGeneratorAgent:
    """
    Integrated content generation agent that combines resource curation 
    and engage task generation for complete learning unit population.
    
    This agent orchestrates both the ResourceCuratorAgent and 
    EngageTaskGeneratorAgent to provide a complete content generation solution.
    """
    
    def __init__(self, openai_client: OpenAI, model: str = DefaultSettings.DEFAULT_MODEL) -> None:
        self.client = openai_client
        self.model = model
        
        # Initialize component agents
        self.resource_curator = ResourceCuratorAgent(openai_client, model)
        self.task_generator = EngageTaskGeneratorAgent(openai_client, model)
    
    def generate_complete_content(self, request: ContentGenerationRequest) -> GeneratedContent:
        """
        Generate complete content (resources + tasks) for a learning unit.
        
        Args:
            request: ContentGenerationRequest with all generation parameters
            
        Returns:
            GeneratedContent with resources, tasks, and formatted outputs
        """
        generation_notes = []
        resources_success = False
        tasks_success = False
        
        try:
            # Step 1: Generate resources
            resource_request = ResourceRequest(
                unit=request.unit,
                min_video_resources=request.min_video_resources,
                min_reading_resources=request.min_reading_resources,
                max_total_resources=request.max_total_resources,
                difficulty_preference=request.difficulty_preference
            )
            
            resources, resources_success = self.resource_curator.curate_resources(resource_request)
            if resources_success:
                generation_notes.append(f"Generated {len(resources)} resources successfully")
            else:
                generation_notes.append(f"Used fallback resources ({len(resources)} resources)")
            
            # Step 2: Generate engage tasks (with resource context)
            task_request = TaskGenerationRequest(
                unit=request.unit,
                resources=resources,  # Provide resources for context
                num_tasks=request.num_engage_tasks,
                difficulty_preference=request.difficulty_preference,
                focus_on_application=request.focus_on_application
            )
            
            engage_tasks, tasks_success = self.task_generator.generate_tasks(task_request)
            if tasks_success:
                generation_notes.append(f"Generated {len(engage_tasks)} engage tasks successfully")
            else:
                generation_notes.append(f"Used fallback tasks ({len(engage_tasks)} tasks)")
            
            # Step 3: Format content for markdown
            formatted_resources = self._format_resources(resources, request.use_obsidian_links)
            formatted_tasks = self._format_tasks(engage_tasks)
            
            # Overall success is True only if both agents succeeded with AI generation
            overall_success = resources_success and tasks_success
            
            return GeneratedContent(
                unit_id=request.unit.id,
                resources=resources,
                engage_tasks=engage_tasks,
                formatted_resources=formatted_resources,
                formatted_tasks=formatted_tasks,
                generation_success=overall_success,
                generation_notes=generation_notes
            )
            
        except (ValueError, TypeError) as e:
            generation_notes.append(f"Error during generation: {str(e)}")
            logger.error(f"Error during content generation: {e}", exc_info=True)
            
            # Fallback generation
            return self._generate_fallback_content(request, generation_notes)
    
    def populate_unit_with_content(self, unit: LearningUnit, request: Optional[ContentGenerationRequest] = None) -> LearningUnit:
        """
        Populate a learning unit with generated resources and tasks in-place.
        
        Args:
            unit: LearningUnit to populate
            request: Optional ContentGenerationRequest, defaults will be used if not provided
            
        Returns:
            The updated LearningUnit with populated content
        """
        if request is None:
            request = ContentGenerationRequest(unit=unit)
        else:
            # Update the request to use the provided unit
            request.unit = unit
        
        # Generate content
        content = self.generate_complete_content(request)
        
        # Populate the unit
        unit.resources = content.resources
        unit.engage_tasks = content.engage_tasks
        
        return unit
    
    def batch_populate_units(self, units: List[LearningUnit], 
                           base_request: Optional[ContentGenerationRequest] = None) -> List[GeneratedContent]:
        """
        Populate multiple learning units with content in batch.
        
        Args:
            units: List of LearningUnit objects to populate
            base_request: Base ContentGenerationRequest to use for all units
            
        Returns:
            List of GeneratedContent results for each unit
        """
        results = []
        
        for unit in units:
            if base_request:
                # Create a copy of the base request for this unit
                unit_request = ContentGenerationRequest(
                    unit=unit,
                    min_video_resources=base_request.min_video_resources,
                    min_reading_resources=base_request.min_reading_resources,
                    max_total_resources=base_request.max_total_resources,
                    num_engage_tasks=base_request.num_engage_tasks,
                    difficulty_preference=base_request.difficulty_preference,
                    focus_on_application=base_request.focus_on_application,
                    use_obsidian_links=base_request.use_obsidian_links
                )
            else:
                unit_request = ContentGenerationRequest(unit=unit)
            
            # Generate and populate
            content = self.generate_complete_content(unit_request)
            unit.resources = content.resources
            unit.engage_tasks = content.engage_tasks
            
            results.append(content)
        
        return results
    
    def _format_resources(self, resources: List[LearningResource], use_obsidian_links: bool = True) -> List[str]:
        """Format resources for markdown output."""
        from .resource_curator import format_resources_for_obsidian
        return format_resources_for_obsidian(resources, use_obsidian_links)
    
    def _format_tasks(self, tasks: List[EngageTask]) -> List[str]:
        """Format engage tasks for markdown output."""
        from .engage_task_generator import format_tasks_for_markdown
        return format_tasks_for_markdown(tasks)
    
    def _generate_fallback_content(self, request: ContentGenerationRequest, 
                                 generation_notes: List[str]) -> GeneratedContent:
        """
        Generate basic fallback content if AI generation fails completely.
        """
        from .engage_task_generator import suggest_task_for_objectives
        
        unit = request.unit
        generation_notes.append("Using fallback content generation")
        
        # Create basic resources
        fallback_resources = [
            LearningResource(
                title=f"{unit.title} - Video Overview",
                url=FallbackUrls.youtube_overview(unit.title),
                type="video",
                description=f"Video overview of {unit.title} concepts",
                estimated_time="15-20 min"
            ),
            LearningResource(
                title=f"{unit.title} - Reference Material",
                url=FallbackUrls.wikipedia_article(unit.title),
                type="article",
                description=f"Reference material for {unit.title}",
                estimated_time="10-15 min"
            )
        ]
        
        # Create basic engage task
        fallback_task = suggest_task_for_objectives(unit.learning_objectives, unit.title)
        
        # Format content
        formatted_resources = self._format_resources(fallback_resources, request.use_obsidian_links)
        formatted_tasks = self._format_tasks([fallback_task])
        
        return GeneratedContent(
            unit_id=unit.id,
            resources=fallback_resources,
            engage_tasks=[fallback_task],
            formatted_resources=formatted_resources,
            formatted_tasks=formatted_tasks,
            generation_success=False,
            generation_notes=generation_notes
        )


def create_content_generator(api_key: Optional[str] = None, model: str = DefaultSettings.DEFAULT_MODEL) -> ContentGeneratorAgent:
    """
    Factory function to create a ContentGeneratorAgent with OpenAI client.
    
    Args:
        api_key: OpenAI API key. If None, will try to get from environment
        model: OpenAI model to use for generation
        
    Returns:
        Configured ContentGeneratorAgent instance
    """
    try:
        if api_key:
            client = OpenAI(api_key=api_key)
        else:
            # OpenAI will automatically look for OPENAI_API_KEY environment variable
            client = OpenAI()
        
        return ContentGeneratorAgent(client, model)
    
    except ImportError as e:
        logger.error(f"Failed to import OpenAI: {e}")
        raise RuntimeError(f"Failed to create ContentGeneratorAgent: OpenAI package not installed") from e
    except Exception as e:
        logger.error(f"Failed to create ContentGeneratorAgent: {e}", exc_info=True)
        raise RuntimeError(f"Failed to create ContentGeneratorAgent: {str(e)}") from e


def generate_unit_content_simple(unit: LearningUnit, 
                                api_key: Optional[str] = None,
                                use_obsidian_links: bool = True) -> GeneratedContent:
    """
    Simple utility function to generate content for a single unit.
    
    Args:
        unit: LearningUnit to generate content for
        api_key: OpenAI API key
        use_obsidian_links: Whether to format links for Obsidian
        
    Returns:
        GeneratedContent with resources and tasks
    """
    generator = create_content_generator(api_key)
    request = ContentGenerationRequest(unit=unit, use_obsidian_links=use_obsidian_links)
    return generator.generate_complete_content(request) 