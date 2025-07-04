"""
FlowGenius Project Content Orchestrator

This module provides LangChain-based orchestration for generating
content (resources and tasks) for all units in a learning project.
"""

import logging
import os
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass

from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_openai import ChatOpenAI
from langchain.chains import LLMChain
from pydantic import BaseModel, Field

from ..models.project import LearningProject, LearningUnit
from ..models.settings import DefaultSettings
from .content_generator import ContentGeneratorAgent, ContentGenerationRequest, GeneratedContent

# Set up module logger
logger = logging.getLogger(__name__)


class ContentGenerationPlan(BaseModel):
    """Plan for content generation across units."""
    unit_priorities: List[str] = Field(description="Unit IDs in priority order")
    resource_requirements: Dict[str, int] = Field(description="Resource requirements per unit")
    task_requirements: Dict[str, int] = Field(description="Task requirements per unit")
    difficulty_mapping: Dict[str, str] = Field(description="Difficulty level per unit")
    generation_strategy: str = Field(description="Overall generation strategy")
    special_considerations: List[str] = Field(description="Special considerations for content")


@dataclass
class OrchestrationResult:
    """Result of the content orchestration process."""
    project: LearningProject
    content_map: Dict[str, GeneratedContent]
    success: bool
    generation_notes: List[str]
    errors: List[str]


class ProjectContentOrchestrator:
    """
    LangChain-based orchestrator for generating content across all units in a project.
    
    This orchestrator uses LangChain to intelligently plan and execute
    content generation for each unit, considering dependencies and context.
    """
    
    def __init__(self, openai_client, model: str = DefaultSettings.DEFAULT_MODEL):
        """
        Initialize the orchestrator with LangChain components.
        
        Args:
            openai_client: OpenAI client for API access
            model: Model to use for orchestration
        """
        self.openai_client = openai_client
        self.model = model
        
        # Initialize LangChain components
        if openai_client and hasattr(openai_client, 'api_key'):
            os.environ["OPENAI_API_KEY"] = openai_client.api_key
        
        self.chat_model = ChatOpenAI(model=model, temperature=0.3)
        self.content_generator = ContentGeneratorAgent(openai_client, model)
        
        # Set up planning chain
        self.planning_prompt = PromptTemplate(
            input_variables=["project_topic", "project_motivation", "units_summary", "total_units"],
            template="""
You are an AI curriculum designer planning content generation for a learning project.

Project Topic: {project_topic}
Learner's Motivation: {project_motivation}
Total Units: {total_units}

Units Summary:
{units_summary}

Create a comprehensive content generation plan that considers:
1. The logical progression of units and their dependencies
2. Appropriate resource counts (videos/articles) for each unit's complexity
3. Suitable task counts based on unit objectives
4. Difficulty levels that match the progression
5. Special considerations for content generation

Provide a structured plan for generating high-quality learning content.

Return a JSON object with:
- unit_priorities: List of unit IDs in the order they should be processed
- resource_requirements: Dict mapping unit ID to number of resources needed (2-5)
- task_requirements: Dict mapping unit ID to number of tasks needed (1-3)
- difficulty_mapping: Dict mapping unit ID to difficulty ("beginner", "intermediate", "advanced")
- generation_strategy: Overall strategy description
- special_considerations: List of special considerations
"""
        )
        
        # Output parser for structured response
        self.plan_parser = JsonOutputParser(pydantic_object=ContentGenerationPlan)
        
        # Create planning chain
        self.planning_chain = self.planning_prompt | self.chat_model | self.plan_parser
    
    def orchestrate_content_generation(
        self, 
        project: LearningProject,
        use_obsidian_links: bool = True,
        progress_callback: Optional[callable] = None
    ) -> OrchestrationResult:
        """
        Orchestrate content generation for all units in a project using LangChain.
        
        Args:
            project: The learning project to generate content for
            use_obsidian_links: Whether to format links for Obsidian
            progress_callback: Optional callback for progress updates
            
        Returns:
            OrchestrationResult with the enhanced project and generation metadata
        """
        logger.info(f"Starting LangChain orchestration for project: {project.metadata.title}")
        
        generation_notes = []
        errors = []
        content_map = {}
        
        try:
            # Step 1: Create content generation plan using LangChain
            plan = self._create_generation_plan(project)
            generation_notes.append(f"Created generation plan: {plan.generation_strategy}")
            
            # Step 2: Execute content generation based on the plan
            total_units = len(project.units)
            
            for idx, unit_id in enumerate(plan.unit_priorities):
                # Find the unit
                unit = next((u for u in project.units if u.id == unit_id), None)
                if not unit:
                    logger.warning(f"Unit {unit_id} not found in project")
                    continue
                
                # Update progress
                if progress_callback:
                    progress_callback(f"Generating content for {unit.title}", idx + 1, total_units)
                
                # Create content request based on plan
                request = ContentGenerationRequest(
                    unit=unit,
                    min_video_resources=1,
                    min_reading_resources=1,
                    max_total_resources=plan.resource_requirements.get(unit_id, 4),
                    num_engage_tasks=plan.task_requirements.get(unit_id, 2),
                    difficulty_preference=plan.difficulty_mapping.get(unit_id, "intermediate"),
                    focus_on_application=True,
                    use_obsidian_links=use_obsidian_links
                )
                
                # Generate content
                try:
                    content = self.content_generator.generate_complete_content(request)
                    content_map[unit_id] = content
                    
                    # Update unit with generated content
                    unit.resources = content.resources
                    unit.engage_tasks = content.engage_tasks
                    
                    if content.generation_success:
                        generation_notes.append(f"✅ Generated content for {unit.title}")
                    else:
                        generation_notes.append(f"⚠️ Used fallback content for {unit.title}")
                        
                except Exception as e:
                    logger.error(f"Failed to generate content for unit {unit_id}: {e}")
                    errors.append(f"Unit {unit_id}: {str(e)}")
                    
                    # Create minimal fallback content
                    from .engage_task_generator import suggest_task_for_objectives
                    from ..models.settings import FallbackUrls
                    from ..models.project import LearningResource
                    
                    # Basic fallback resources
                    unit.resources = [
                        LearningResource(
                            title=f"{unit.title} Overview",
                            url=FallbackUrls.youtube_search(unit.title),
                            type="video",
                            description="Search for relevant videos",
                            estimated_time="20-30 min"
                        )
                    ]
                    
                    # Basic fallback task
                    unit.engage_tasks = [suggest_task_for_objectives(unit.learning_objectives, unit.title)]
                    
                    content_map[unit_id] = GeneratedContent(
                        unit_id=unit_id,
                        resources=unit.resources,
                        engage_tasks=unit.engage_tasks,
                        formatted_resources=[],
                        formatted_tasks=[],
                        generation_success=False,
                        generation_notes=["Fallback content due to generation error"]
                    )
            
            # Step 3: Add special considerations to notes
            if plan.special_considerations:
                generation_notes.extend([f"💡 {note}" for note in plan.special_considerations])
            
            # Determine overall success
            success = len(errors) == 0 and len(content_map) == len(project.units)
            
            return OrchestrationResult(
                project=project,
                content_map=content_map,
                success=success,
                generation_notes=generation_notes,
                errors=errors
            )
            
        except Exception as e:
            logger.error(f"Orchestration failed: {e}", exc_info=True)
            errors.append(f"Orchestration error: {str(e)}")
            
            # Return project with minimal content
            return OrchestrationResult(
                project=project,
                content_map=content_map,
                success=False,
                generation_notes=generation_notes,
                errors=errors
            )
    
    def _create_generation_plan(self, project: LearningProject) -> ContentGenerationPlan:
        """
        Create a content generation plan using LangChain.
        
        Args:
            project: The learning project to plan for
            
        Returns:
            ContentGenerationPlan with priorities and requirements
        """
        # Prepare units summary
        units_summary = []
        for unit in project.units:
            summary = f"- {unit.id}: {unit.title}"
            if unit.prerequisites:
                summary += f" (requires: {', '.join(unit.prerequisites)})"
            if unit.learning_objectives:
                summary += f"\n  Objectives: {len(unit.learning_objectives)} objectives"
            units_summary.append(summary)
        
        try:
            # Generate plan using LangChain
            plan = self.planning_chain.invoke({
                "project_topic": project.metadata.topic,
                "project_motivation": project.metadata.motivation or "General learning",
                "units_summary": "\n".join(units_summary),
                "total_units": len(project.units)
            })
            
            # Validate and adjust plan
            if isinstance(plan, dict):
                plan = ContentGenerationPlan(**plan)
            
            # Ensure all units are included
            unit_ids = [u.id for u in project.units]
            for unit_id in unit_ids:
                if unit_id not in plan.unit_priorities:
                    plan.unit_priorities.append(unit_id)
                if unit_id not in plan.resource_requirements:
                    plan.resource_requirements[unit_id] = 3
                if unit_id not in plan.task_requirements:
                    plan.task_requirements[unit_id] = 2
                if unit_id not in plan.difficulty_mapping:
                    plan.difficulty_mapping[unit_id] = "intermediate"
            
            return plan
            
        except Exception as e:
            logger.error(f"Failed to create generation plan: {e}")
            
            # Fallback plan
            unit_ids = [u.id for u in project.units]
            return ContentGenerationPlan(
                unit_priorities=unit_ids,
                resource_requirements={uid: 3 for uid in unit_ids},
                task_requirements={uid: 2 for uid in unit_ids},
                difficulty_mapping={uid: "intermediate" for uid in unit_ids},
                generation_strategy="Sequential generation with default parameters",
                special_considerations=["Using fallback plan due to planning error"]
            )


def create_project_orchestrator(api_key: Optional[str] = None, model: str = DefaultSettings.DEFAULT_MODEL) -> ProjectContentOrchestrator:
    """
    Factory function to create a ProjectContentOrchestrator.
    
    Args:
        api_key: OpenAI API key
        model: Model to use for orchestration
        
    Returns:
        Configured ProjectContentOrchestrator instance
    """
    try:
        from openai import OpenAI
        
        if api_key:
            client = OpenAI(api_key=api_key)
        else:
            # Will use OPENAI_API_KEY from environment
            client = OpenAI()
        
        return ProjectContentOrchestrator(client, model)
        
    except Exception as e:
        logger.error(f"Failed to create orchestrator: {e}")
        raise RuntimeError(f"Failed to create ProjectContentOrchestrator: {str(e)}") from e 