"""
FlowGenius: AI-assisted learning assistant that eliminates research paralysis.

FlowGenius helps you create structured, adaptive learning plans from freeform
learning goals, saving everything as local Markdown files for long-term retention.
"""

from .cli.main import main
from .utils import (
    get_timestamp,
    get_datetime_now,
    find_project_directory,
    ensure_project_structure,
    safe_load_json,
    safe_save_json,
    safe_load_yaml,
    safe_load_config,
    get_unit_file_path,
    get_backup_path,
    validate_json_response,
    sanitize_filename,
    truncate_string,
    safe_execute
)

__version__ = "0.5.15"
__all__ = [
    "main",
    # Utils functions
    "get_timestamp",
    "get_datetime_now",
    "find_project_directory",
    "ensure_project_structure",
    "safe_load_json",
    "safe_save_json",
    "safe_load_yaml",
    "safe_load_config",
    "get_unit_file_path",
    "get_backup_path",
    "validate_json_response",
    "sanitize_filename",
    "truncate_string",
    "safe_execute",
]
