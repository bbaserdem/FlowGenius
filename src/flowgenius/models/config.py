"""
FlowGenius Configuration Models

This module defines the configuration structure for FlowGenius,
including user preferences and system settings.
"""

from pathlib import Path
from typing import Literal
from pydantic import BaseModel, Field
from platformdirs import user_config_dir


class FlowGeniusConfig(BaseModel):
    """
    Main configuration model for FlowGenius.
    
    Stores user preferences for AI models, file paths, and formatting options.
    """
    
    openai_key_path: Path = Field(
        description="Path to file containing OpenAI API key"
    )
    
    projects_root: Path = Field(
        description="Root directory where learning projects will be stored"
    )
    
    link_style: Literal["obsidian", "markdown"] = Field(
        default="obsidian",
        description="Style of links to use in generated markdown files"
    )
    
    default_model: str = Field(
        default="gpt-4o-mini",
        description="Default OpenAI model to use for content generation"
    )

    class Config:
        """Pydantic model configuration."""
        use_enum_values = True


def get_config_path() -> Path:
    """
    Get the path to the FlowGenius configuration file.
    
    Returns:
        Path to config.yaml in the user's configuration directory
    """
    config_dir = Path(user_config_dir("flowgenius"))
    return config_dir / "config.yaml"


def get_default_projects_root() -> Path:
    """
    Get the default projects root directory.
    
    Returns:
        Default path for storing learning projects
    """
    return Path.home() / "Learning"


def get_default_openai_key_path() -> Path:
    """
    Get the default OpenAI API key file path.
    
    Returns:
        Default path for OpenAI API key file
    """
    return Path.home() / ".openai_api_key" 