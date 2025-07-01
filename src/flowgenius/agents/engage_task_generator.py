"""
FlowGenius Engage Task Generator Agent

This module contains the AI agent responsible for generating engaging, 
active learning tasks for learning units.
"""

import json
from typing import List, Optional, Dict, Any, Tuple
from openai import OpenAI
from pydantic import BaseModel

from ..models.project import EngageTask, LearningUnit, LearningResource


class TaskGenerationRequest(BaseModel):
    """Request for engage task generation."""
    unit: LearningUnit
    resources: Optional[List[LearningResource]] = None
    num_tasks: int = 1
    difficulty_preference: Optional[str] = None
    focus_on_application: bool = True


class EngageTaskGeneratorAgent:
    """
    AI agent for generating engaging, active learning tasks for specific learning units.
    
    Takes a learning unit and its resources to create practical, engaging tasks
    that promote active learning and skill application.
    """
    
    def __init__(self, openai_client: OpenAI, model: str = "gpt-4o-mini") -> None:
        self.client = openai_client
        self.model = model
    
    def generate_tasks(self, request: TaskGenerationRequest) -> Tuple[List[EngageTask], bool]:
        """
        Generate engaging tasks for a specific unit.
        
        Args:
            request: TaskGenerationRequest with unit and task requirements
            
        Returns:
            Tuple of (List of EngageTask objects, success flag indicating if AI generation was used)
        """
        try:
            # Generate tasks using AI
            tasks = self._generate_tasks_with_ai(request)
            
            # Ensure we have at least the requested number of tasks
            if len(tasks) < request.num_tasks:
                tasks.extend(self._generate_fallback_tasks(request, request.num_tasks - len(tasks)))
            
            return tasks[:request.num_tasks], True
            
        except Exception as e:
            # Fallback to basic tasks if AI fails
            return self._create_fallback_tasks(request), False
    
    def generate_tasks_legacy(self, request: TaskGenerationRequest) -> List[EngageTask]:
        """
        Legacy method that returns only tasks for backward compatibility.
        """
        tasks, _ = self.generate_tasks(request)
        return tasks
    
    def _generate_tasks_with_ai(self, request: TaskGenerationRequest) -> List[EngageTask]:
        """
        Use AI to generate appropriate engaging tasks for the unit.
        """
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(request)
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.8,  # Higher creativity for task generation
            max_tokens=1500
        )
        
        # Parse the response
        content = response.choices[0].message.content
        tasks_data = json.loads(content)
        
        # Convert to EngageTask objects
        tasks = []
        for task_data in tasks_data["tasks"]:
            task = EngageTask(
                title=task_data["title"],
                description=task_data["description"],
                type=task_data["type"],
                estimated_time=task_data.get("estimated_time")
            )
            tasks.append(task)
        
        return tasks
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt for the AI."""
        return """You are an expert learning designer who creates engaging, active learning tasks.

Your job is to design specific learning activities that:
1. Promote active engagement with the material (not passive consumption)
2. Help learners apply concepts practically
3. Encourage reflection and deeper thinking
4. Are achievable within a reasonable timeframe
5. Connect to real-world applications

Return your response as valid JSON with this exact structure:
{
  "tasks": [
    {
      "title": "Clear, action-oriented task title",
      "description": "Detailed description of what the learner should do, including specific steps or guidelines",
      "type": "reflection|practice|project|quiz|experiment",
      "estimated_time": "15 min|1 hour|etc"
    }
  ]
}

Task Types Guidelines:
- "reflection": Thoughtful analysis, self-assessment, or deep thinking exercises
- "practice": Hands-on exercises, drills, or skill application
- "project": Creative application, building something, or synthesis activities
- "quiz": Self-testing, knowledge verification, or quick assessments
- "experiment": Try something new, test hypotheses, or explore variations

Design Principles:
- Make tasks specific and actionable
- Include concrete deliverables when appropriate
- Encourage personal application and context
- Balance challenge with achievability
- Promote different learning styles
- Focus on active learning over passive consumption"""

    def _build_user_prompt(self, request: TaskGenerationRequest) -> str:
        """Build the user prompt with the specific unit information."""
        unit = request.unit
        
        prompt = f"""Create engaging learning tasks for this unit:

Unit Title: {unit.title}
Description: {unit.description}

Learning Objectives:
{chr(10).join(f"- {obj}" for obj in unit.learning_objectives)}
"""
        
        if unit.estimated_duration:
            prompt += f"\nEstimated Unit Duration: {unit.estimated_duration}"
        
        # Include resources if available
        if request.resources:
            prompt += "\n\nAvailable Resources:"
            for resource in request.resources:
                prompt += f"\n- {resource.title} ({resource.type}): {resource.description or 'No description'}"
        
        prompt += f"""

Requirements:
- Generate {request.num_tasks} engaging task(s)
- Focus on active learning and practical application
"""
        
        if request.difficulty_preference:
            prompt += f"- Difficulty level: {request.difficulty_preference}"
            
        if request.focus_on_application:
            prompt += "\n- Emphasize real-world application and hands-on practice"
        
        prompt += "\n\nReturn valid JSON following the specified structure."
        
        return prompt
    
    def _generate_fallback_tasks(self, request: TaskGenerationRequest, count: int) -> List[EngageTask]:
        """Generate fallback tasks if AI didn't provide enough."""
        fallback_tasks = []
        unit = request.unit
        
        task_templates = [
            {
                "title": f"Reflect on {unit.title} Applications",
                "description": f"Think about how {unit.title} applies to your personal goals or interests. Write down 3 specific ways you could use these concepts.",
                "type": "reflection",
                "estimated_time": "10 min"
            },
            {
                "title": f"Practice {unit.title} Skills",
                "description": f"Complete a hands-on exercise related to {unit.title}. Apply the key concepts from the learning objectives.",
                "type": "practice", 
                "estimated_time": "20-30 min"
            },
            {
                "title": f"Create a {unit.title} Project",
                "description": f"Design a small project that demonstrates your understanding of {unit.title}. Focus on practical application.",
                "type": "project",
                "estimated_time": "45 min"
            }
        ]
        
        for i in range(count):
            template = task_templates[i % len(task_templates)]
            task = EngageTask(**template)
            fallback_tasks.append(task)
        
        return fallback_tasks
    
    def _create_fallback_tasks(self, request: TaskGenerationRequest) -> List[EngageTask]:
        """
        Create basic fallback tasks if AI generation completely fails.
        """
        unit = request.unit
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
        if request.num_tasks > 1:
            practice_task = EngageTask(
                title=f"Practice {topic} Concepts",
                description=f"Complete a practical exercise that applies the key concepts from {topic}. Focus on hands-on application rather than theoretical knowledge.",
                type="practice",
                estimated_time="20-30 min"
            )
            tasks.append(practice_task)
        
        return tasks[:request.num_tasks]


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