"""
FlowGenius Data Models

This package contains Pydantic data models and schemas for representing
learning projects, units, resources, and configuration.
"""

from .config import FlowGeniusConfig, get_config_path, get_default_projects_root, get_default_openai_key_path
from .config_manager import ConfigManager
from .project import (
    LearningResource, EngageTask, LearningUnit, ProjectMetadata, LearningProject,
    generate_project_id, generate_unit_id
)
from .project_generator import ProjectGenerator
from .renderer import MarkdownRenderer

__all__ = [
    # Configuration
    "FlowGeniusConfig",
    "ConfigManager", 
    "get_config_path",
    "get_default_projects_root",
    "get_default_openai_key_path",
    
    # Project models
    "LearningResource",
    "EngageTask", 
    "LearningUnit",
    "ProjectMetadata",
    "LearningProject",
    "generate_project_id",
    "generate_unit_id",
    
    # Project generation
    "ProjectGenerator",
    "MarkdownRenderer"
] 