"""
FlowGenius Configuration Manager

This module handles reading, writing, and managing FlowGenius configuration files.
"""

import logging
from pathlib import Path
from typing import Optional
from ruamel.yaml import YAML
from .config import FlowGeniusConfig, get_config_path
from .settings import DefaultSettings

# Set up module logger
logger = logging.getLogger(__name__)


class ConfigManager:
    """
    Manages FlowGenius configuration file operations.
    
    Handles reading, writing, and validating configuration files in YAML format.
    """
    
    def __init__(self):
        self.yaml = YAML()
        self.yaml.preserve_quotes = DefaultSettings.YAML_PRESERVE_QUOTES
        self.yaml.width = DefaultSettings.YAML_LINE_WIDTH
    
    def load_config(self) -> Optional[FlowGeniusConfig]:
        """
        Load configuration from the default config file.
        
        Returns:
            FlowGeniusConfig if file exists and is valid, None otherwise
        """
        config_path = get_config_path()
        
        if not config_path.exists():
            return None
            
        try:
            with open(config_path, 'r') as f:
                config_data = self.yaml.load(f)
            
            # Convert string paths back to Path objects
            if config_data:
                if 'openai_key_path' in config_data:
                    config_data['openai_key_path'] = Path(config_data['openai_key_path'])
                if 'projects_root' in config_data:
                    config_data['projects_root'] = Path(config_data['projects_root'])
            
            return FlowGeniusConfig(**config_data) if config_data else None
            
        except Exception as e:
            logger.error(f"Error loading config from {config_path}: {e}", exc_info=True)
            return None
    
    def save_config(self, config: FlowGeniusConfig) -> bool:
        """
        Save configuration to the default config file.
        
        Args:
            config: FlowGeniusConfig object to save
            
        Returns:
            True if saved successfully, False otherwise
        """
        config_path = get_config_path()
        
        try:
            # Ensure config directory exists
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert Path objects to strings for YAML serialization
            config_dict = config.model_dump()
            config_dict['openai_key_path'] = str(config.openai_key_path)
            config_dict['projects_root'] = str(config.projects_root)
            
            with open(config_path, 'w') as f:
                self.yaml.dump(config_dict, f)
            
            logger.info(f"Configuration saved to: {config_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving config to {config_path}: {e}", exc_info=True)
            return False
    
    def config_exists(self) -> bool:
        """
        Check if a configuration file already exists.
        
        Returns:
            True if config file exists, False otherwise
        """
        return get_config_path().exists()
    
    def get_config_path_str(self) -> str:
        """
        Get the configuration file path as a string.
        
        Returns:
            String path to the configuration file
        """
        return str(get_config_path()) 