"""
FlowGenius Data Models

This package contains Pydantic data models and schemas for representing
learning projects, units, resources, and configuration.
"""

from .config import FlowGeniusConfig, get_config_path, get_default_projects_root, get_default_openai_key_path
from .config_manager import ConfigManager

__all__ = [
    "FlowGeniusConfig",
    "ConfigManager", 
    "get_config_path",
    "get_default_projects_root",
    "get_default_openai_key_path"
] 