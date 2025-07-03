"""
FlowGenius Setup Wizard

This module provides an interactive wizard for setting up FlowGenius
configuration and creating the first learning project.
"""

import os
import click
import questionary
from pathlib import Path
from typing import Optional

from ..models.config import FlowGeniusConfig, get_config_path, get_default_projects_root
from ..models.config_manager import ConfigManager
from ..models.settings import DefaultSettings


@click.command()
@click.option(
    '--force',
    is_flag=True,
    help='Overwrite existing configuration without prompting'
)
def wizard(force: bool) -> None:
    """
    Interactive setup wizard for FlowGenius.
    
    Guides you through setting up your FlowGenius configuration,
    including API keys, project directories, and preferences.
    """
    if force:
        # If force flag is used, run the setup wizard without prompting
        result = run_setup_wizard()
        if result:
            click.echo("✅ Setup completed successfully!")
        else:
            click.echo("❌ Setup was cancelled or failed.")
    else:
        # Check if config exists and prompt if needed
        config_manager = ConfigManager()
        if config_manager.config_exists():
            if click.confirm("Configuration already exists. Do you want to overwrite it?"):
                result = run_setup_wizard()
                if result:
                    click.echo("✅ Setup completed successfully!")
                else:
                    click.echo("❌ Setup was cancelled or failed.")
            else:
                click.echo("Setup cancelled. Using existing configuration.")
        else:
            result = run_setup_wizard()
            if result:
                click.echo("✅ Setup completed successfully!")
            else:
                click.echo("❌ Setup was cancelled or failed.")


def run_setup_wizard() -> Optional[FlowGeniusConfig]:
    """
    Run the interactive setup wizard for FlowGenius.
    
    Returns:
        FlowGeniusConfig if setup was completed, None if cancelled
    """
    print("\n🧙‍♂️ Welcome to FlowGenius Setup Wizard!")
    print("Let's get you set up with personalized learning projects.\n")
    
    # Check if configuration already exists
    config_path = get_config_path()
    if config_path.exists():
        overwrite = questionary.confirm(
            "Configuration already exists. Do you want to overwrite it?",
            default=False
        ).ask()
        
        if not overwrite:
            print("Setup cancelled. Using existing configuration.")
            return None
    
    # OpenAI API Key setup
    print("📝 First, let's set up your OpenAI API key...")
    api_key = questionary.password(
        "Enter your OpenAI API key:",
        validate=lambda x: len(x.strip()) > 0 or "API key cannot be empty"
    ).ask()
    
    if not api_key:
        print("Setup cancelled.")
        return None
    
    # Choose model
    print("\n🤖 Choose your preferred AI model...")
    model_choice = questionary.select(
        "Which OpenAI model would you like to use?",
        choices=[
            {"name": "GPT-4o Mini (Recommended - Fast & Cost-effective)", "value": "gpt-4o-mini"},
            {"name": "GPT-4o (Most Capable)", "value": "gpt-4o"},
            {"name": "GPT-4 Turbo (Balanced)", "value": "gpt-4-turbo"},
            {"name": "GPT-3.5 Turbo (Budget-friendly)", "value": "gpt-3.5-turbo"}
        ],
        default=DefaultSettings.DEFAULT_MODEL,
        instruction="Use arrow keys to navigate, Enter to select"
    ).ask()
    
    if not model_choice:
        print("Setup cancelled.")
        return None
    
    # Projects directory setup
    print("\n📁 Where would you like to store your learning projects?")
    default_projects = get_default_projects_root()
    
    use_default_dir = questionary.confirm(
        f"Use default directory: {default_projects}?",
        default=True
    ).ask()
    
    if use_default_dir:
        projects_root = default_projects
    else:
        custom_path = questionary.path(
            "Enter custom projects directory:",
            validate=lambda x: Path(x).parent.exists() or "Parent directory must exist"
        ).ask()
        
        if not custom_path:
            print("Setup cancelled.")
            return None
        
        projects_root = Path(custom_path)
    
    # Create projects directory if it doesn't exist
    projects_root.mkdir(parents=True, exist_ok=True)
    
    # Content preferences
    print("\n⚙️ Let's configure your content preferences...")
    
    units_per_project = questionary.select(
        "How many units per project by default?",
        choices=[
            {"name": "3 units (Quick overview)", "value": 3},
            {"name": "5 units (Comprehensive)", "value": 5},
            {"name": "7 units (Deep dive)", "value": 7}
        ],
        default=3
    ).ask()
    
    if units_per_project is None:
        print("Setup cancelled.")
        return None
    
    focus_application = questionary.confirm(
        "Focus on practical application in tasks?",
        default=True
    ).ask()
    
    # Save API key to file
    key_file = config_path.parent / "openai_key.txt"
    key_file.parent.mkdir(parents=True, exist_ok=True)
    key_file.write_text(api_key.strip())
    key_file.chmod(0o600)  # Secure permissions
    
    # Create configuration
    config = FlowGeniusConfig(
        openai_key_path=key_file,
        default_model=model_choice,
        projects_root=projects_root,
        auto_create_dirs=True,
        default_units_per_project=units_per_project,
        default_unit_duration=DefaultSettings.DEFAULT_UNIT_DURATION,
        min_video_resources=DefaultSettings.MIN_VIDEO_RESOURCES,
        min_reading_resources=DefaultSettings.MIN_READING_RESOURCES,
        max_total_resources=DefaultSettings.MAX_TOTAL_RESOURCES,
        default_tasks_per_unit=DefaultSettings.DEFAULT_NUM_TASKS,
        focus_on_application=focus_application,
        backup_projects=True,
        file_format="markdown"
    )
    
    # Save configuration
    config_manager = ConfigManager()
    success = config_manager.save_config(config)
    
    if success:
        print(f"\n✅ Configuration saved successfully!")
        print(f"📂 Projects will be stored in: {projects_root}")
        print(f"🤖 Using model: {model_choice}")
        print(f"🔑 API key saved securely in: {key_file}")
        
        # Offer to create first project
        create_first = questionary.confirm(
            "\nWould you like to create your first learning project now?",
            default=True
        ).ask()
        
        if create_first:
            print("\n🚀 Great! Run 'flowgenius new <topic>' to create your first project.")
            print("Example: flowgenius new 'Python data science'")
        
        return config
    else:
        print("❌ Failed to save configuration. Please try again.")
        return None


def validate_openai_key(api_key: str) -> bool:
    """
    Validate OpenAI API key format.
    
    Args:
        api_key: API key to validate
        
    Returns:
        True if key format appears valid
    """
    # Basic validation - OpenAI keys start with 'sk-' and are typically 51 chars
    return (
        api_key.startswith('sk-') and 
        len(api_key) >= 20 and
        all(c.isalnum() or c in '-_' for c in api_key)
    )


def check_existing_config() -> bool:
    """
    Check if FlowGenius configuration already exists.
    
    Returns:
        True if configuration exists and is valid
    """
    config_manager = ConfigManager()
    return config_manager.config_exists()


def load_existing_config() -> Optional[FlowGeniusConfig]:
    """
    Load existing FlowGenius configuration.
    
    Returns:
        FlowGeniusConfig if exists and valid, None otherwise
    """
    config_manager = ConfigManager()
    return config_manager.load_config() 