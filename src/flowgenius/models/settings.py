"""
FlowGenius Centralized Settings

This module contains all centralized configuration constants and default values
used throughout the FlowGenius application.
"""

from typing import Dict, Any


class DefaultSettings:
    """
    Centralized default settings for FlowGenius.
    
    This class contains all hardcoded values that were previously scattered
    throughout the codebase, providing a single source of truth for configuration.
    """
    
    # AI Model Configuration
    DEFAULT_MODEL = "gpt-4o-mini"
    
    # YAML Configuration
    YAML_LINE_WIDTH = 120  # Reduced from 4096 for better readability
    YAML_PRESERVE_QUOTES = True
    
    # Directory Names
    UNITS_DIR = "units"
    RESOURCES_DIR = "resources"
    NOTES_DIR = "notes"
    DOCS_DIR = "docs"
    REPORTS_DIR = "reports"
    BACKUPS_DIR = "backups"
    
    # File Names
    PROJECT_FILE = "project.json"
    STATE_FILE = "state.json"
    CONFIG_FILE = "config.yaml"
    TOC_FILE = "toc.md"
    README_FILE = "README.md"
    
    # Fallback URL Patterns
    YOUTUBE_SEARCH_BASE = "https://youtube.com/search?q={query}"
    WIKIPEDIA_BASE = "https://en.wikipedia.org/wiki/{title}"
    
    # Resource Generation Defaults
    MIN_VIDEO_RESOURCES = 1
    MIN_READING_RESOURCES = 1
    MAX_TOTAL_RESOURCES = 5
    DEFAULT_NUM_TASKS = 1
    
    # Task Time Estimates
    DEFAULT_VIDEO_TIME = "15-20 min"
    DEFAULT_ARTICLE_TIME = "10-15 min"
    DEFAULT_REFLECTION_TIME = "10-15 min"
    DEFAULT_PRACTICE_TIME = "20-30 min"
    DEFAULT_PROJECT_TIME = "45 min"
    
    # Emoji Mappings for Resource Types
    RESOURCE_TYPE_EMOJIS: Dict[str, str] = {
        "video": "🎥",
        "article": "📖",
        "paper": "📄",
        "tutorial": "🛠️",
        "documentation": "📋",
        "default": "📎"
    }
    
    # Emoji Mappings for Task Types  
    TASK_TYPE_EMOJIS: Dict[str, str] = {
        "reflection": "🤔",
        "practice": "🛠️",
        "project": "🎯",
        "quiz": "❓",
        "experiment": "🧪",
        "default": "📝"
    }
    
    # OpenAI Model Configuration
    DEFAULT_TEMPERATURE = 0.7
    DEFAULT_MAX_TOKENS = 3000
    TASK_GENERATION_TEMPERATURE = 0.8  # Higher creativity for tasks
    TASK_GENERATION_MAX_TOKENS = 1500
    RESOURCE_GENERATION_MAX_TOKENS = 2000
    
    # Session and ID Generation
    SESSION_ID_LENGTH = 8
    
    # Logging Configuration
    DEFAULT_LOG_LEVEL = "INFO"
    
    # Unit Duration Estimates
    DEFAULT_UNIT_DURATION = "1-2 hours"
    CORE_UNIT_DURATION = "2-3 hours"
    ADVANCED_UNIT_DURATION = "2-4 hours"


class FallbackUrls:
    """
    Centralized fallback URL generators for when AI generation fails.
    """
    
    @staticmethod
    def youtube_search(query: str) -> str:
        """Generate YouTube search URL for a given query."""
        clean_query = query.replace(' ', '+')
        return DefaultSettings.YOUTUBE_SEARCH_BASE.format(query=clean_query)
    
    @staticmethod
    def youtube_tutorial(topic: str) -> str:
        """Generate YouTube tutorial search URL."""
        return FallbackUrls.youtube_search(f"{topic}_tutorial")
    
    @staticmethod
    def youtube_introduction(topic: str) -> str:
        """Generate YouTube introduction search URL."""
        return FallbackUrls.youtube_search(f"{topic}_introduction")
    
    @staticmethod
    def youtube_overview(topic: str) -> str:
        """Generate YouTube overview search URL."""
        return FallbackUrls.youtube_search(f"{topic}_overview")
    
    @staticmethod
    def youtube_tutorial_part(topic: str, part_number: int) -> str:
        """Generate YouTube tutorial search URL for a specific part."""
        return FallbackUrls.youtube_search(f"{topic}_tutorial_part_{part_number}")
    
    @staticmethod
    def wikipedia_article(title: str) -> str:
        """Generate Wikipedia article URL for a given title."""
        clean_title = title.replace(' ', '_')
        return DefaultSettings.WIKIPEDIA_BASE.format(title=clean_title)
    
    @staticmethod
    def wikipedia_guide(topic: str, guide_number: int) -> str:
        """Generate Wikipedia guide URL for a specific guide number."""
        clean_topic = topic.replace(' ', '_')
        return DefaultSettings.WIKIPEDIA_BASE.format(title=f"{clean_topic}_guide_{guide_number}")


class ValidationSettings:
    """
    Settings related to validation and error handling.
    """
    
    # Validation timeouts
    DEFAULT_TIMEOUT = 30  # seconds
    
    # Retry settings
    DEFAULT_RETRY_COUNT = 3
    RETRY_DELAY = 1  # seconds
    
    # JSON validation
    MAX_JSON_SIZE = 1024 * 1024  # 1MB
    
    # Content validation
    MIN_TITLE_LENGTH = 3
    MAX_TITLE_LENGTH = 200
    MIN_DESCRIPTION_LENGTH = 10
    MAX_DESCRIPTION_LENGTH = 1000


def get_resource_emoji(resource_type: str) -> str:
    """
    Get emoji for a resource type.
    
    Args:
        resource_type: Type of resource
        
    Returns:
        Appropriate emoji string
    """
    return DefaultSettings.RESOURCE_TYPE_EMOJIS.get(
        resource_type.lower(), 
        DefaultSettings.RESOURCE_TYPE_EMOJIS["default"]
    )


def get_task_emoji(task_type: str) -> str:
    """
    Get emoji for a task type.
    
    Args:
        task_type: Type of task
        
    Returns:
        Appropriate emoji string
    """
    return DefaultSettings.TASK_TYPE_EMOJIS.get(
        task_type.lower(),
        DefaultSettings.TASK_TYPE_EMOJIS["default"]
    ) 