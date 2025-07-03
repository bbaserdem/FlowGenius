"""
FlowGenius Utilities Module

This module contains shared utility functions used throughout the FlowGenius application.
These functions were extracted from various modules to reduce code duplication and improve maintainability.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Callable
from ruamel.yaml import YAML

from .models.settings import DefaultSettings

# Set up module logger
logger = logging.getLogger(__name__)


# ====================================================================
# Timestamp Utilities
# ====================================================================

def get_timestamp() -> str:
    """
    Get current ISO-formatted timestamp string.
    
    Returns:
        ISO-formatted timestamp string
    """
    return datetime.now().isoformat()


def get_datetime_now() -> datetime:
    """
    Get current datetime object.
    
    Returns:
        Current datetime
    """
    return datetime.now()


# ====================================================================
# Project Directory Utilities
# ====================================================================

def find_project_directory(start_path: Optional[Path] = None) -> Optional[Path]:
    """
    Find the project directory by looking for project.json.
    
    Args:
        start_path: Starting directory to search from (defaults to current directory)
        
    Returns:
        Path to project directory if found, None otherwise
    """
    current_dir = start_path or Path.cwd()
    
    # Check current directory and parent directories
    for path in [current_dir] + list(current_dir.parents):
        project_file = path / DefaultSettings.PROJECT_FILE
        if project_file.exists():
            return path
    
    return None


def ensure_project_structure(project_dir: Path) -> None:
    """
    Ensure all required project directories exist.
    
    Args:
        project_dir: Root project directory
        
    Raises:
        OSError: If directory creation fails due to permissions or other issues
    """
    try:
        directories = [
            project_dir / DefaultSettings.UNITS_DIR,
            project_dir / DefaultSettings.RESOURCES_DIR,
            project_dir / DefaultSettings.NOTES_DIR,
            project_dir / DefaultSettings.DOCS_DIR,
            project_dir / DefaultSettings.REPORTS_DIR,
            project_dir / DefaultSettings.BACKUPS_DIR,
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise OSError(f"Failed to create project directory structure in {project_dir}: {e}") from e


# ====================================================================
# File Loading Utilities
# ====================================================================

def safe_load_json(file_path: Path) -> Optional[Dict[str, Any]]:
    """
    Safely load a JSON file with error handling.
    
    Args:
        file_path: Path to JSON file
        
    Returns:
        Parsed JSON data or None if loading fails
    """
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError, IOError) as e:
        logger.error(f"Failed to load JSON from {file_path}: {e}")
        return None


def safe_save_json(data: Dict[str, Any], file_path: Path, indent: int = 2) -> bool:
    """
    Safely save data to a JSON file with error handling.
    
    Args:
        data: Data to save
        file_path: Path to save to
        indent: JSON indentation level
        
    Returns:
        True if saved successfully, False otherwise
    """
    try:
        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=indent, default=str)
        return True
    except (OSError, IOError, TypeError) as e:
        logger.error(f"Failed to save JSON to {file_path}: {e}")
        return False


def safe_load_yaml(file_path: Path) -> Optional[Dict[str, Any]]:
    """
    Safely load a YAML file with error handling.
    
    Args:
        file_path: Path to YAML file
        
    Returns:
        Parsed YAML data or None if loading fails
    """
    try:
        yaml = YAML()
        yaml.preserve_quotes = DefaultSettings.YAML_PRESERVE_QUOTES
        yaml.width = DefaultSettings.YAML_LINE_WIDTH
        
        with open(file_path, 'r') as f:
            return yaml.load(f)
    except (OSError, IOError, Exception) as e:
        logger.error(f"Failed to load YAML from {file_path}: {e}")
        return None


def safe_load_config() -> Optional[Any]:
    """
    Safely load configuration without hanging on import issues.
    
    Returns:
        Config object if successful, None otherwise
    """
    try:
        # Import these only when needed and with timeout
        from .models.config_manager import ConfigManager
        config_manager = ConfigManager()
        return config_manager.load_config()
    except ImportError as e:
        # If config loading fails for any reason, continue without config
        logger.warning(f"Could not import configuration module: {e}")
        return None
    except (OSError, IOError) as e:
        # If config file is inaccessible
        logger.warning(f"Could not load configuration file: {e}")
        return None


# ====================================================================
# Path Manipulation Utilities
# ====================================================================

def get_unit_file_path(project_dir: Path, unit_id: str) -> Path:
    """
    Get the path to a unit's markdown file.
    
    Args:
        project_dir: Project root directory
        unit_id: Unit identifier
        
    Returns:
        Path to unit markdown file
    """
    return project_dir / DefaultSettings.UNITS_DIR / f"{unit_id}.md"


def get_backup_path(project_dir: Path, backup_type: str, identifier: str) -> Path:
    """
    Get the path for a backup file.
    
    Args:
        project_dir: Project root directory
        backup_type: Type of backup (e.g., 'project', 'unit')
        identifier: Unique identifier for the backup
        
    Returns:
        Path to backup file
    """
    backups_dir = project_dir / DefaultSettings.BACKUPS_DIR
    backups_dir.mkdir(parents=True, exist_ok=True)
    return backups_dir / f"{backup_type}_{identifier}.json"


# ====================================================================
# Validation Utilities
# ====================================================================

def validate_json_response(content: str, expected_structure: type) -> Optional[Any]:
    """
    Validate JSON response against expected structure using Pydantic.
    
    Args:
        content: JSON string to validate
        expected_structure: Pydantic model class for validation
        
    Returns:
        Validated object or None if validation fails
    """
    try:
        if not content:
            logger.error("Empty content provided for validation")
            return None
            
        parsed_data = json.loads(content.strip())
        return expected_structure(**parsed_data)
        
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"JSON validation failed: {e}")
        logger.debug(f"Content that failed validation: {content[:200]}...")
        return None


# ====================================================================
# String Manipulation Utilities
# ====================================================================

def sanitize_filename(filename: str) -> str:
    """
    Sanitize a string to be safe for use as a filename.
    
    Args:
        filename: String to sanitize
        
    Returns:
        Sanitized filename string
    """
    # Remove or replace unsafe characters
    safe_chars = "".join(c if c.isalnum() or c in "-_." else "-" for c in filename)
    # Remove multiple consecutive dashes
    safe_chars = "-".join(part for part in safe_chars.split("-") if part)
    return safe_chars[:255]  # Limit length for filesystem compatibility


def truncate_string(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate a string to a maximum length with suffix.
    
    Args:
        text: String to truncate
        max_length: Maximum length (including suffix)
        suffix: Suffix to add when truncating
        
    Returns:
        Truncated string
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


# ====================================================================
# Error Handling Utilities
# ====================================================================

def safe_execute(func: Callable, *args, default=None, error_message: str = "Operation failed", **kwargs) -> Any:
    """
    Safely execute a function with error handling and logging.
    
    Args:
        func: Function to execute
        *args: Positional arguments for function
        default: Default value to return on error
        error_message: Error message to log
        **kwargs: Keyword arguments for function
        
    Returns:
        Function result or default value on error
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.error(f"{error_message}: {e}", exc_info=True)
        return default 