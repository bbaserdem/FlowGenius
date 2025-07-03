"""
FlowGenius Data Models

This package contains Pydantic data models and schemas for representing
learning projects, units, resources, and configuration.
"""

from .config import FlowGeniusConfig, get_config_path, get_config_dir, get_default_projects_root
from .config_manager import ConfigManager
from .project import (
    LearningResource, EngageTask, LearningUnit, ProjectMetadata, LearningProject,
    UserFeedback, RefinementAction,
    generate_project_id, generate_unit_id
)
from .project_generator import ProjectGenerator
from .renderer import MarkdownRenderer
from .settings import DefaultSettings, FallbackUrls, ValidationSettings, get_resource_emoji, get_task_emoji
from .state_store import StateStore, ProjectState, UnitState, create_state_store

__all__ = [
    # Configuration
    "FlowGeniusConfig",
    "ConfigManager", 
    "get_config_path",
    "get_config_dir",
    "get_default_projects_root",
    
    # Settings
    "DefaultSettings",
    "FallbackUrls",
    "ValidationSettings", 
    "get_resource_emoji",
    "get_task_emoji",
    
    # Project models
    "LearningResource",
    "EngageTask", 
    "LearningUnit",
    "ProjectMetadata",
    "LearningProject",
    "UserFeedback",
    "RefinementAction",
    "generate_project_id",
    "generate_unit_id",
    
    # Project generation
    "ProjectGenerator",
    "MarkdownRenderer",
    
    # Progress tracking
    "StateStore",
    "ProjectState", 
    "UnitState",
    "create_state_store"
] 