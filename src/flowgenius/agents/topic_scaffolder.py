"""
FlowGenius Topic Scaffolder Agent

This module contains the AI agent responsible for creating structured learning plans
from freeform learning goals and motivations.
"""

import json
import logging
from typing import List, Optional
from openai import OpenAI
from pydantic import BaseModel, ValidationError

from ..models.project import (
    LearningProject, ProjectMetadata, LearningUnit,
    generate_project_id, generate_unit_id
)
from ..models.settings import DefaultSettings

# Set up module logger
logger = logging.getLogger(__name__)


class ScaffoldingRequest(BaseModel):
    """Request for topic scaffolding."""
    topic: str
    motivation: Optional[str] = None
    target_units: int = 3
    difficulty_preference: Optional[str] = None


class UnitData(BaseModel):
    """Pydantic model for validating AI-generated unit data."""
    title: str
    description: str
    learning_objectives: List[str]
    estimated_duration: Optional[str] = None
    prerequisites: Optional[List[str]] = None
    status: str = "pending"


class UnitsResponse(BaseModel):
    """Pydantic model for validating complete AI response."""
    units: List[UnitData]


class TopicScaffolderAgent:
    """
    AI agent that creates structured learning plans from freeform goals.
    """
    
    def __init__(self, openai_client: OpenAI, model: str = DefaultSettings.DEFAULT_MODEL):
        """
        Initialize the scaffolder with OpenAI client.
        
        Args:
            openai_client: Configured OpenAI client
            model: OpenAI model to use for generation
        """
        self.client = openai_client
        self.model = model
    
    def create_learning_project(
        self,
        topic: str,
        motivation: Optional[str] = None,
        target_units: int = 3,
        estimated_total_time: Optional[str] = None
    ) -> LearningProject:
        """
        Create a complete learning project from a topic and motivation.
        
        Args:
            topic: The subject or topic to learn
            motivation: Why the user wants to learn this (optional)
            target_units: Number of learning units to create
            estimated_total_time: Total estimated time for the project
            
        Returns:
            Complete LearningProject with structured units
        """
        logger.info(f"Creating learning project for topic: {topic}")
        
        try:
            # Generate learning units using AI
            units_data = self._generate_learning_units(topic, motivation, target_units)
            
            # Create learning units from the generated data
            units = []
            for i, unit_data in enumerate(units_data):
                unit_id = generate_unit_id(i + 1)
                
                unit = LearningUnit(
                    id=unit_id,
                    title=unit_data.title,
                    description=unit_data.description,
                    learning_objectives=unit_data.learning_objectives,
                    estimated_duration=unit_data.estimated_duration,
                    prerequisites=unit_data.prerequisites or [],
                    status=unit_data.status
                )
                units.append(unit)
            
            # Create project metadata
            metadata = ProjectMetadata(
                topic=topic,
                motivation=motivation,
                estimated_total_time=estimated_total_time or self._estimate_total_time(units)
            )
            
            # Create and return the complete project
            project = LearningProject(
                project_id=generate_project_id(),
                title=f"Learning {topic}",
                metadata=metadata,
                units=units
            )
            
            logger.info(f"Successfully created project with {len(units)} units")
            return project
            
        except Exception as e:
            logger.error(f"Failed to create learning project: {e}", exc_info=True)
            # Return a basic fallback project
            return self._create_fallback_project(topic, motivation, target_units)
    
    def _generate_learning_units(
        self,
        topic: str,
        motivation: Optional[str],
        target_units: int
    ) -> List[UnitData]:
        """
        Generate learning units using OpenAI API with proper validation.
        
        Args:
            topic: The subject to learn
            motivation: User's motivation (optional)
            target_units: Number of units to generate
            
        Returns:
            List of validated UnitData objects
        """
        prompt = self._build_scaffolding_prompt(topic, motivation, target_units)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert learning designer. Create structured, progressive learning units that build upon each other logically."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            content = response.choices[0].message.content.strip()
            logger.debug(f"AI response content: {content[:200]}...")
            
            # Parse and validate JSON response
            try:
                units_json = json.loads(content)
                logger.debug(f"Parsed JSON structure: {type(units_json)}")
                
                # Validate with Pydantic
                validated_response = UnitsResponse(**units_json)
                logger.info(f"Successfully validated {len(validated_response.units)} units")
                return validated_response.units
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing failed: {e}")
                raise
            except ValidationError as e:
                logger.error(f"Pydantic validation failed: {e}")
                raise
                
        except Exception as e:
            logger.error(f"Failed to generate units: {e}", exc_info=True)
            # Return fallback units
            return self._create_fallback_units(topic, target_units)
    
    def _build_scaffolding_prompt(self, topic: str, motivation: Optional[str], target_units: int) -> str:
        """Build the scaffolding prompt for the AI."""
        prompt = f"Create a structured learning plan for: {topic}"
        
        if motivation:
            prompt += f"\n\nLearner's motivation: {motivation}"
        
        prompt += f"\n\nGenerate {target_units} learning units."
        
        if self.difficulty_preference:
            prompt += f"\n\nDifficulty level: {self.difficulty_preference}"
        
        prompt += "\n\nRemember to return valid JSON following the specified structure."
        
        return prompt
    
    def _create_fallback_project(self, topic: str, motivation: Optional[str], target_units: int) -> LearningProject:
        """
        Create a basic fallback project if AI generation fails.
        """
        logger.warning(f"Creating fallback project for topic: {topic}")
        
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
        
        return LearningProject(
            project_id=generate_project_id(),
            title=f"Learning {topic}",
            metadata=ProjectMetadata(
                topic=topic,
                motivation=motivation,
                estimated_total_time=self._estimate_total_time(units)
            ),
            units=units[:target_units]
        )
    
    def _estimate_total_time(self, units: List[LearningUnit]) -> str:
        """Estimate the total time required to complete the project."""
        total_time = sum(unit.estimated_duration for unit in units)
        return f"{total_time:.2f} hours"
    
    def _create_fallback_units(self, topic: str, target_units: int) -> List[LearningUnit]:
        """
        Create basic fallback units if AI generation fails.
        """
        logger.warning(f"Creating fallback units for topic: {topic}")
        
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
        
        return units[:target_units] 