"""
FlowGenius Topic Scaffolder Agent

This module contains the AI agent responsible for creating structured learning plans
from freeform learning goals and motivations.
"""

import json
from typing import List, Optional
from openai import OpenAI
from pydantic import BaseModel

from ..models.project import (
    LearningProject, ProjectMetadata, LearningUnit,
    generate_project_id, generate_unit_id
)


class ScaffoldingRequest(BaseModel):
    """Request for topic scaffolding."""
    topic: str
    motivation: Optional[str] = None
    target_units: int = 3
    difficulty_preference: Optional[str] = None


class TopicScaffolderAgent:
    """
    AI agent for scaffolding learning topics into structured units.
    
    Takes a freeform learning goal and creates a structured learning plan
    with learning units, objectives, and progression.
    """
    
    def __init__(self, openai_client: OpenAI, model: str = "gpt-4o-mini"):
        self.client = openai_client
        self.model = model
    
    def scaffold_topic(self, request: ScaffoldingRequest) -> LearningProject:
        """
        Scaffold a learning topic into a structured project.
        
        Args:
            request: ScaffoldingRequest with topic and optional motivation
            
        Returns:
            LearningProject with generated units and structure
        """
        # Generate project metadata
        project_id = generate_project_id(request.topic)
        title = self._generate_project_title(request.topic, request.motivation)
        
        metadata = ProjectMetadata(
            id=project_id,
            title=title,
            topic=request.topic,
            motivation=request.motivation
        )
        
        # Generate learning units using AI
        units = self._generate_learning_units(request)
        
        return LearningProject(metadata=metadata, units=units)
    
    def _generate_project_title(self, topic: str, motivation: Optional[str]) -> str:
        """Generate a clear, engaging project title."""
        if motivation:
            return f"Learn {topic.title()}: {motivation.capitalize()}"
        return f"Learn {topic.title()}"
    
    def _generate_learning_units(self, request: ScaffoldingRequest) -> List[LearningUnit]:
        """
        Use AI to generate structured learning units for the topic.
        """
        # Create the prompt for the AI
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(request)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=3000
            )
            
            # Parse the response
            content = response.choices[0].message.content
            units_data = json.loads(content)
            
            # Convert to LearningUnit objects
            units = []
            for i, unit_data in enumerate(units_data["units"]):
                unit_id = generate_unit_id(request.topic, i)
                
                unit = LearningUnit(
                    id=unit_id,
                    title=unit_data["title"],
                    description=unit_data["description"],
                    learning_objectives=unit_data["learning_objectives"],
                    prerequisites=unit_data.get("prerequisites", []),
                    estimated_duration=unit_data.get("estimated_duration")
                )
                units.append(unit)
            
            return units
            
        except Exception as e:
            # Fallback to basic structure if AI fails
            return self._create_fallback_units(request)
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt for the AI."""
        return """You are an expert learning designer who creates structured, engaging learning plans.

Your job is to take a learning topic and break it down into logical, progressive learning units that:
1. Build upon each other in a logical sequence
2. Have clear, achievable learning objectives
3. Are appropriately scoped for focused learning sessions
4. Follow proven pedagogical principles

Return your response as valid JSON with this exact structure:
{
  "units": [
    {
      "title": "Clear, engaging unit title",
      "description": "1-2 sentence description of what this unit covers",
      "learning_objectives": [
        "Specific, measurable learning objective 1",
        "Specific, measurable learning objective 2"
      ],
      "prerequisites": ["unit-1"],  // IDs of prerequisite units, empty for first unit
      "estimated_duration": "2-3 hours"  // Realistic time estimate
    }
  ]
}

Guidelines:
- Create 3-5 units typically
- Start with fundamentals, build to application
- Each unit should be completable in one focused session
- Learning objectives should be specific and measurable
- Use action verbs (understand, apply, create, analyze)
- Consider different learning styles and approaches
- Make it engaging and practical"""

    def _build_user_prompt(self, request: ScaffoldingRequest) -> str:
        """Build the user prompt with the specific request."""
        prompt = f"Create a structured learning plan for: {request.topic}"
        
        if request.motivation:
            prompt += f"\n\nLearner's motivation: {request.motivation}"
        
        prompt += f"\n\nGenerate {request.target_units} learning units."
        
        if request.difficulty_preference:
            prompt += f"\n\nDifficulty level: {request.difficulty_preference}"
        
        prompt += "\n\nRemember to return valid JSON following the specified structure."
        
        return prompt
    
    def _create_fallback_units(self, request: ScaffoldingRequest) -> List[LearningUnit]:
        """
        Create basic fallback units if AI generation fails.
        """
        topic = request.topic
        
        units = [
            LearningUnit(
                id="unit-1",
                title=f"Introduction to {topic.title()}",
                description=f"Get familiar with the basics and foundations of {topic}",
                learning_objectives=[
                    f"Understand what {topic} is and why it's important",
                    "Identify key concepts and terminology",
                    "Set clear learning goals for your journey"
                ],
                estimated_duration="1-2 hours"
            ),
            LearningUnit(
                id="unit-2", 
                title=f"Core Concepts of {topic.title()}",
                description=f"Dive deeper into the fundamental concepts of {topic}",
                learning_objectives=[
                    "Master the core principles and concepts",
                    "Apply basic techniques and methods",
                    "Practice with hands-on examples"
                ],
                prerequisites=["unit-1"],
                estimated_duration="2-3 hours"
            ),
            LearningUnit(
                id="unit-3",
                title=f"Practical Application of {topic.title()}",
                description=f"Apply your knowledge of {topic} to real-world scenarios",
                learning_objectives=[
                    "Complete practical exercises and projects",
                    "Integrate concepts into a cohesive understanding",
                    "Plan next steps for continued learning"
                ],
                prerequisites=["unit-2"],
                estimated_duration="2-4 hours"
            )
        ]
        
        return units[:request.target_units] 