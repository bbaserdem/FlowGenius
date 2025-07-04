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

from ..models.config import FlowGeniusConfig, get_config_path, get_config_dir, get_default_projects_root
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
    
    # OpenAI API Key file path setup
    print("📝 First, let's set up your OpenAI API key file path...")
    print("💡 Tip: Store your API key in a file like ~/.secrets/openai_api_key or ~/.openai_api_key")
    print("   Make sure the file has restrictive permissions (chmod 600)\n")
    
    # Suggest default paths
    default_paths = [
        Path.home() / ".secrets" / "openai_api_key",
        Path.home() / ".openai_api_key",
        get_config_dir() / "openai_key.txt"
    ]
    
    existing_paths = [p for p in default_paths if p.exists()]
    
    if existing_paths:
        # Found existing API key files
        choices = [{"name": str(p), "value": str(p)} for p in existing_paths]
        choices.append({"name": "Enter custom path", "value": "custom"})
        
        api_key_path_choice = questionary.select(
            "Found existing API key file(s). Select one:",
            choices=choices
        ).ask()
        
        if not api_key_path_choice:
            print("Setup cancelled.")
            return None
            
        if api_key_path_choice == "custom":
            api_key_path = questionary.path(
                "Enter the path to your OpenAI API key file:",
                validate=validate_api_key_file
            ).ask()
        else:
            api_key_path = api_key_path_choice
    else:
        # No existing files found, ask for path
        api_key_path = questionary.path(
            "Enter the path to your OpenAI API key file:",
            validate=validate_api_key_file
        ).ask()
    
    if not api_key_path:
        print("Setup cancelled.")
        return None
    
    api_key_path = Path(api_key_path).expanduser()
    
    # Validate the API key in the file
    try:
        api_key_content = api_key_path.read_text().strip()
        if not validate_openai_key(api_key_content):
            print(f"❌ Invalid API key format in {api_key_path}")
            create_new = questionary.confirm(
                "Would you like to create a new API key file?",
                default=True
            ).ask()
            
            if create_new:
                api_key_path = create_api_key_file()
                if not api_key_path:
                    return None
            else:
                return None
    except Exception as e:
        print(f"❌ Error reading API key file: {e}")
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
    
    # Create configuration
    config = FlowGeniusConfig(
        openai_key_path=api_key_path,
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
        print(f"🔑 API key file: {api_key_path}")
        
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


def create_api_key_file() -> Optional[Path]:
    """
    Create a new API key file with proper permissions.
    
    Returns:
        Path to the created file, or None if cancelled
    """
    print("\n🔑 Let's create a new API key file...")
    
    # Ask for file location
    default_path = get_config_dir() / "openai_key.txt"
    file_path = questionary.path(
        f"Where to save the API key file? (default: {default_path}):",
        default=str(default_path)
    ).ask()
    
    if not file_path:
        return None
    
    file_path = Path(file_path).expanduser()
    
    # Ask for API key
    api_key = questionary.password(
        "Enter your OpenAI API key:",
        validate=lambda x: validate_openai_key(x.strip()) or "Invalid API key format. Should start with 'sk-'"
    ).ask()
    
    if not api_key:
        return None
    
    # Create directory if needed
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Save API key with restrictive permissions
    file_path.write_text(api_key.strip())
    file_path.chmod(0o600)
    
    print(f"✅ API key saved to: {file_path}")
    print(f"🔒 File permissions set to 600 (owner read/write only)")
    
    return file_path


def validate_api_key_file(path: str) -> bool:
    """
    Validate that the API key file exists and is readable.
    
    Args:
        path: Path to the API key file
        
    Returns:
        True if valid, or error message if not
    """
    try:
        p = Path(path).expanduser()
        if not p.exists():
            return f"File does not exist: {path}"
        if not p.is_file():
            return f"Not a file: {path}"
        if not os.access(p, os.R_OK):
            return f"File is not readable: {path}"
        
        # Check file permissions (warn if too permissive)
        mode = p.stat().st_mode & 0o777
        if mode != 0o600:
            print(f"⚠️  Warning: File permissions are {oct(mode)}. Consider running: chmod 600 {path}")
        
        return True
    except Exception as e:
        return f"Error: {e}"


def validate_openai_key(api_key: str) -> bool:
    """
    Validate the OpenAI API key format.
    
    Args:
        api_key: The API key to validate
        
    Returns:
        True if the API key appears to be valid, False otherwise
    """
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