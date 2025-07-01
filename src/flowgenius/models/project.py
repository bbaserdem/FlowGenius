"""
FlowGenius Project Models

This module defines the data structures for learning projects, units, and resources.
"""

import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class LearningResource(BaseModel):
    """
    A learning resource (video, article, paper, etc.) for a unit.
    """
    title: str = Field(description="Title of the resource")
    url: str = Field(description="URL to the resource")
    type: Literal["video", "article", "paper", "book", "tutorial", "documentation"] = Field(
        description="Type of resource"
    )
    description: Optional[str] = Field(default=None, description="Brief description of the resource")
    estimated_time: Optional[str] = Field(default=None, description="Estimated time to consume (e.g., '15 min', '2 hours')")


class EngageTask(BaseModel):
    """
    An engaging task for active learning within a unit.
    """
    title: str = Field(description="Title of the task")
    description: str = Field(description="Description of what to do")
    type: Literal["reflection", "practice", "project", "quiz", "experiment"] = Field(
        description="Type of engaging task"
    )
    estimated_time: Optional[str] = Field(default=None, description="Estimated time to complete")


class LearningUnit(BaseModel):
    """
    A single learning unit within a project.
    """
    id: str = Field(description="Unique identifier for the unit")
    title: str = Field(description="Title of the learning unit")
    description: str = Field(description="Description of what this unit covers")
    learning_objectives: List[str] = Field(description="What the learner should achieve")
    resources: List[LearningResource] = Field(default_factory=list, description="Learning resources")
    engage_tasks: List[EngageTask] = Field(default_factory=list, description="Active learning tasks")
    prerequisites: List[str] = Field(default_factory=list, description="IDs of prerequisite units")
    estimated_duration: Optional[str] = Field(default=None, description="Estimated time to complete unit")
    status: Literal["pending", "in-progress", "completed"] = Field(default="pending")


class ProjectMetadata(BaseModel):
    """
    Metadata for a learning project.
    """
    id: str = Field(description="Unique project identifier")
    title: str = Field(description="Human-readable project title")
    topic: str = Field(description="Main learning topic")
    motivation: Optional[str] = Field(default=None, description="Why the user wants to learn this")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    estimated_total_time: Optional[str] = Field(default=None, description="Total estimated learning time")
    difficulty_level: Optional[Literal["beginner", "intermediate", "advanced"]] = Field(default=None)
    tags: List[str] = Field(default_factory=list, description="Topic tags for organization")


class LearningProject(BaseModel):
    """
    A complete learning project with metadata and units.
    """
    metadata: ProjectMetadata = Field(description="Project metadata")
    units: List[LearningUnit] = Field(description="Learning units in order")
    
    @property
    def project_id(self) -> str:
        """Get the project ID."""
        return self.metadata.id
    
    @property
    def title(self) -> str:
        """Get the project title."""
        return self.metadata.title
    
    def get_unit_by_id(self, unit_id: str) -> Optional[LearningUnit]:
        """Get a unit by its ID."""
        for unit in self.units:
            if unit.id == unit_id:
                return unit
        return None
    
    def update_timestamp(self) -> None:
        """Update the last modified timestamp."""
        self.metadata.updated_at = datetime.now()


def generate_project_id(topic: str) -> str:
    """
    Generate a unique project ID from a topic.
    
    Args:
        topic: The learning topic
        
    Returns:
        A unique project ID in format: topic-slug-xxx
    """
    # Create a URL-friendly slug from the topic
    slug = topic.lower()
    slug = "".join(c if c.isalnum() or c in "-_" else "-" for c in slug)
    slug = "-".join(word for word in slug.split("-") if word)  # Remove empty parts
    slug = slug[:50]  # Limit length
    
    # Add a short UUID for uniqueness
    short_uuid = str(uuid.uuid4())[:8]
    
    return f"{slug}-{short_uuid}"


def generate_unit_id(project_id: str, unit_index: int) -> str:
    """
    Generate a unit ID within a project.
    
    Args:
        project_id: The project ID
        unit_index: The zero-based index of the unit
        
    Returns:
        Unit ID in format: unit-{index+1}
    """
    return f"unit-{unit_index + 1}" 