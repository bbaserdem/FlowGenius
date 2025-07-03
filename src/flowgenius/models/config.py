"""
FlowGenius Configuration Models

This module contains Pydantic models for FlowGenius configuration management,
including user preferences, API settings, and project defaults.
"""

from pathlib import Path
from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator
from .settings import DefaultSettings


class FlowGeniusConfig(BaseModel):
    """
    Main configuration model for FlowGenius.
    
    Contains all user preferences and settings for the FlowGenius application.
    """
    
    # OpenAI Configuration
    openai_key_path: Path = Field(description="Path to file containing OpenAI API key")
    default_model: str = Field(
        default=DefaultSettings.DEFAULT_MODEL,
        description="Default OpenAI model for content generation"
    )
    
    # Project Settings  
    projects_root: Path = Field(description="Root directory for FlowGenius projects")
    auto_create_dirs: bool = Field(default=True, description="Automatically create project directories")
    
    # Content Generation Preferences
    default_units_per_project: int = Field(default=3, description="Default number of units per project")
    default_unit_duration: str = Field(default="1-2 hours", description="Default estimated unit duration")
    
    # Resource Curation Settings
    min_video_resources: int = Field(default=DefaultSettings.MIN_VIDEO_RESOURCES, description="Minimum video resources per unit")
    min_reading_resources: int = Field(default=DefaultSettings.MIN_READING_RESOURCES, description="Minimum reading resources per unit")
    max_total_resources: int = Field(default=DefaultSettings.MAX_TOTAL_RESOURCES, description="Maximum total resources per unit")
    
    # Task Generation Settings
    default_tasks_per_unit: int = Field(default=DefaultSettings.DEFAULT_NUM_TASKS, description="Default number of tasks per unit")
    focus_on_application: bool = Field(default=True, description="Emphasize practical application in tasks")
    
    # File Management
    backup_projects: bool = Field(default=True, description="Create backups when modifying projects")
    file_format: str = Field(default="markdown", description="Default file format for project files")
    
    # Link Style
    link_style: Literal["obsidian", "markdown"] = "obsidian"
    
    class Config:
        """Pydantic configuration."""
        validate_assignment = True
        arbitrary_types_allowed = True

    @field_validator('openai_key_path', 'projects_root')
    @classmethod
    def validate_paths_exist(cls, v: Path) -> Path:
        """Validate that paths exist."""
        if not v.exists():
            raise ValueError(f"Path does not exist: {v}")
        return v
    
    @field_validator('default_model')
    @classmethod
    def validate_model_name(cls, v: str) -> str:
        """Validate that model name is not empty."""
        if not v.strip():
            raise ValueError("Model name cannot be empty")
        return v.strip()


def get_config_path() -> Path:
    """
    Get the path to the FlowGenius configuration file.
    
    Returns:
        Path to the configuration file
    """
    home = Path.home()
    config_dir = home / ".flowgenius"
    config_dir.mkdir(exist_ok=True)
    return config_dir / "config.yaml"


def get_default_projects_root() -> Path:
    """
    Get the default projects root directory.
    
    Returns:
        Path to the default projects directory
    """
    home = Path.home()
    projects_dir = home / "FlowGenius" / "Projects"
    projects_dir.mkdir(parents=True, exist_ok=True)
    return projects_dir


def create_default_config() -> FlowGeniusConfig:
    """
    Create a default configuration with sensible defaults.
    
    Returns:
        FlowGeniusConfig with default settings
    """
    home = Path.home()
    
    # Create default OpenAI key file path
    key_file = home / ".flowgenius" / "openai_key.txt"
    
    # Create default projects directory
    projects_root = get_default_projects_root()
    
    return FlowGeniusConfig(
        openai_key_path=key_file,
        default_model=DefaultSettings.DEFAULT_MODEL,
        projects_root=projects_root,
        auto_create_dirs=True,
        default_units_per_project=3,
        default_unit_duration=DefaultSettings.DEFAULT_UNIT_DURATION,
        min_video_resources=DefaultSettings.MIN_VIDEO_RESOURCES,
        min_reading_resources=DefaultSettings.MIN_READING_RESOURCES,
        max_total_resources=DefaultSettings.MAX_TOTAL_RESOURCES,
        default_tasks_per_unit=DefaultSettings.DEFAULT_NUM_TASKS,
        focus_on_application=True,
        backup_projects=True,
        file_format="markdown"
    ) 