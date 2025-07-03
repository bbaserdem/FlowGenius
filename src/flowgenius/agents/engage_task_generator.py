"""
FlowGenius Engage Task Generator Agent

This module contains the AI agent responsible for generating engaging, 
active learning tasks for learning units.
"""

import json
import logging
from typing import List, Optional, Dict, Any, Tuple
from openai import OpenAI
from pydantic import BaseModel, ValidationError

from ..models.project import EngageTask, LearningUnit, LearningResource
from ..models.settings import DefaultSettings, get_task_emoji

# Set up module logger
logger = logging.getLogger(__name__)


class TaskGenerationRequest(BaseModel):
    """Request for engage task generation."""
    unit: LearningUnit
    resources: Optional[List[LearningResource]] = None
    num_tasks: int = 1
    difficulty_preference: Optional[str] = None
    focus_on_application: bool = True


class TaskData(BaseModel):
    """Pydantic model for validating AI-generated task data."""
    title: str
    type: str
    description: str
    estimated_time: Optional[str] = None
    difficulty_level: Optional[str] = None


class TasksResponse(BaseModel):
    """Pydantic model for validating complete AI response."""
    tasks: List[TaskData]


class EngageTaskGeneratorAgent:
    """
    AI agent responsible for generating engaging, active learning tasks.
    
    Creates hands-on activities, reflection questions, practice exercises, 
    and projects that help learners actively engage with the material.
    """
    
    def __init__(self, openai_client: OpenAI, model: str = DefaultSettings.DEFAULT_MODEL) -> None:
        """
        Initialize the task generator with OpenAI client.
        
        Args:
            openai_client: Configured OpenAI client
            model: OpenAI model to use for task generation
        """
        self.client = openai_client
        self.model = model
    
    def generate_tasks(
        self,
        request: TaskGenerationRequest
    ) -> Tuple[List[EngageTask], bool]:
        """
        Generate engaging tasks for a specific learning unit.
        
        Args:
            request: TaskGenerationRequest with unit and generation parameters.
            
        Returns:
            A tuple containing a list of generated EngageTask objects and a boolean indicating success.
        """
        unit = request.unit
        logger.info(f"Generating {request.num_tasks} tasks for unit: {unit.id}")
        
        try:
            # Generate tasks using AI with validation
            tasks_data = self._generate_tasks_with_validation(
                unit, request.resources, request.num_tasks, request.focus_on_application
            )
            
            if not tasks_data:
                # Fallback if AI generation returns nothing
                return self._create_fallback_tasks(unit, request.num_tasks), False

            # Convert to EngageTask objects
            tasks = []
            for i, task_data in enumerate(tasks_data):
                task = EngageTask(
                    title=task_data.title,
                    description=task_data.description,
                    type=task_data.type,
                    estimated_time=task_data.estimated_time or self._estimate_time_by_type(task_data.type)
                )
                tasks.append(task)
            
            logger.info(f"Successfully generated {len(tasks)} tasks for unit {unit.id}")
            return tasks, True
            
        except (ValueError, json.JSONDecodeError, TimeoutError) as e:
            logger.error(f"Failed to generate tasks for unit {unit.id}: {e}", exc_info=True)
            # Return fallback tasks
            return self._create_fallback_tasks(unit, request.num_tasks), False
    
    def _generate_tasks_with_validation(
        self,
        unit: LearningUnit,
        resources: Optional[List[LearningResource]],
        num_tasks: int,
        focus_on_application: bool
    ) -> List[TaskData]:
        """
        Generate tasks using OpenAI API with proper JSON validation.
        
        Args:
            unit: Learning unit to generate tasks for
            resources: Optional list of resources for context
            num_tasks: Number of tasks to generate
            focus_on_application: Whether to focus on practical application
            
        Returns:
            List of validated TaskData objects
        """
        prompt = self._build_task_prompt(unit, resources, num_tasks, focus_on_application)
        
        # Add JSON schema to the prompt
        json_schema = """
{
    "tasks": [
        {
            "title": "Task Title",
            "type": "reflection|practice|project|quiz|experiment",
            "description": "What the learner should do - include any step-by-step instructions here",
            "estimated_time": "15-30 min"
        }
    ]
}"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert instructional designer who creates engaging, hands-on learning activities. Focus on active learning and practical application. Always respond with valid JSON."
                    },
                    {
                        "role": "user",
                        "content": f"{prompt}\n\nExpected JSON format:\n{json_schema}"
                    }
                ],
                temperature=DefaultSettings.TASK_GENERATION_TEMPERATURE,
                max_tokens=DefaultSettings.TASK_GENERATION_MAX_TOKENS,
                response_format={"type": "json_object"}  # Force JSON response
            )
            
            content = response.choices[0].message.content
            
            # Check for None or empty content
            if not content:
                logger.error("AI returned empty content")
                return []
                
            content = content.strip()
            logger.debug(f"AI response content: {content[:200]}...")
            
            # Parse and validate JSON response
            try:
                tasks_json = json.loads(content)
                logger.debug(f"Parsed JSON structure: {type(tasks_json)}")
                
                # Validate with Pydantic
                validated_response = TasksResponse(**tasks_json)
                logger.info(f"Successfully validated {len(validated_response.tasks)} tasks")
                return validated_response.tasks
                
            except (json.JSONDecodeError, ValidationError) as e:
                logger.error(f"Pydantic validation failed: {e}")
                logger.debug(f"Full AI response: {content}")
                raise
                
        except (json.JSONDecodeError, ValidationError) as e:
            logger.error(f"Failed to generate tasks: {e}", exc_info=True)
            # Return empty list to trigger fallback
            return []
    
    def _build_task_prompt(
        self,
        unit: LearningUnit,
        resources: Optional[List[LearningResource]],
        num_tasks: int,
        focus_on_application: bool
    ) -> str:
        """
        Build the prompt for generating tasks using OpenAI API.
        
        Args:
            unit: Learning unit to generate tasks for
            resources: Optional list of resources for context
            num_tasks: Number of tasks to generate
            focus_on_application: Whether to focus on practical application
            
        Returns:
            Prompt string for generating tasks
        """
        prompt = f"""Create engaging learning tasks for this unit:

Unit Title: {unit.title}
Description: {unit.description}

Learning Objectives:
{"\n".join(f"- {obj}" for obj in unit.learning_objectives)}
"""
        
        if unit.estimated_duration:
            prompt += f"\nEstimated Unit Duration: {unit.estimated_duration}"
        
        # Include resources if available
        if resources:
            prompt += "\n\nAvailable Resources:"
            for resource in resources:
                prompt += f"\n- {resource.title} ({resource.type}): {resource.description or 'No description'}"
        
        prompt += f"""

Requirements:
- Generate {num_tasks} engaging task(s)
- Focus on active learning and practical application
"""
        
        if focus_on_application:
            prompt += "\n- Emphasize real-world application and hands-on practice"
        
        prompt += "\n\nReturn valid JSON following the specified structure."
        
        return prompt
    
    def _estimate_time_by_type(self, task_type: str) -> str:
        """
        Estimate task time based on task type.
        
        Args:
            task_type: Type of task
            
        Returns:
            Estimated time for the task
        """
        time_estimates = {
            "practice": "20-30 min",
            "reflection": "10-15 min",
            "project": "45-60 min",
            "exercise": "15-25 min",
            "quiz": "10-20 min",
            "discussion": "15-20 min",
            "research": "30-45 min",
            "hands-on": "25-40 min",
            "review": "15-20 min",
            "application": "30-45 min"
        }
        
        # Return specific estimate or default
        return time_estimates.get(task_type.lower(), "20-30 min")
    
    def _create_fallback_tasks(self, unit: LearningUnit, num_tasks: int) -> List[EngageTask]:
        """
        Create basic fallback tasks if AI generation completely fails.
        """
        topic = unit.title
        
        tasks = []
        
        # Always create at least one reflection task
        reflection_task = EngageTask(
            title=f"Reflect on {topic} Learning",
            description=f"After studying {topic}, write a brief reflection on what you learned and how you might apply it. Consider the key concepts and your personal learning goals.",
            type="reflection",
            estimated_time="10-15 min"
        )
        tasks.append(reflection_task)
        
        # Add practice task if more tasks needed
        if num_tasks > 1:
            practice_task = EngageTask(
                title=f"Practice {topic} Concepts",
                description=f"Complete a practical exercise that applies the key concepts from {topic}. Focus on hands-on application rather than theoretical knowledge.",
                type="practice",
                estimated_time="20-30 min"
            )
            tasks.append(practice_task)
        
        return tasks[:num_tasks]


def format_tasks_for_markdown(tasks: List[EngageTask]) -> List[str]:
    """
    Format engage tasks as markdown for inclusion in unit files.
    
    Args:
        tasks: List of EngageTask objects
        
    Returns:
        List of formatted markdown strings
    """
    formatted = []
    
    for i, task in enumerate(tasks, 1):
        # Add task type emoji for visual distinction
        type_emoji = {
            "reflection": "🤔",
            "practice": "🛠️",
            "project": "🎯",
            "quiz": "❓", 
            "experiment": "🧪"
        }
        
        emoji = type_emoji.get(task.type, "📝")
        
        # Format as numbered task with emoji
        formatted_task = f"{i}. {emoji} **{task.title}**"
        
        if task.estimated_time:
            formatted_task += f" *({task.estimated_time})*"
        
        formatted_task += f"\n   {task.description}"
        
        formatted.append(formatted_task)
    
    return formatted


def suggest_task_for_objectives(objectives: List[str], topic: str) -> EngageTask:
    """
    Suggest a simple engage task based on learning objectives without AI.
    
    Args:
        objectives: List of learning objective strings
        topic: The topic/title of the unit
        
    Returns:
        A basic EngageTask appropriate for the objectives
    """
    # Analyze objectives to determine best task type
    objective_text = " ".join(objectives).lower()
    
    if any(word in objective_text for word in ["apply", "use", "implement", "create", "build"]):
        return EngageTask(
            title=f"Apply {topic} in Practice",
            description=f"Choose one of the learning objectives and create a practical example or mini-project that demonstrates your understanding. Focus on real-world application.",
            type="project",
            estimated_time="30-45 min"
        )
    elif any(word in objective_text for word in ["analyze", "evaluate", "compare", "assess"]):
        return EngageTask(
            title=f"Analyze {topic} Concepts",
            description=f"Select two key concepts from the learning objectives and write a brief analysis comparing them or explaining their relationship.",
            type="reflection",
            estimated_time="15-20 min"
        )
    elif any(word in objective_text for word in ["practice", "exercise", "solve", "calculate"]):
        return EngageTask(
            title=f"Practice {topic} Skills",
            description=f"Complete practical exercises related to the learning objectives. Focus on hands-on application of the concepts.",
            type="practice",
            estimated_time="20-30 min"
        )
    else:
        return EngageTask(
            title=f"Reflect on {topic} Learning",
            description=f"After reviewing the material, reflect on how the learning objectives connect to your goals and interests. Write down key insights.",
            type="reflection", 
            estimated_time="10-15 min"
        ) 