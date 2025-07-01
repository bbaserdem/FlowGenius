"""
FlowGenius Configuration Wizard

This module implements the interactive configuration wizard for FlowGenius.
"""

from pathlib import Path
import click
from ..models.config import (
    FlowGeniusConfig,
    get_default_projects_root,
    get_default_openai_key_path
)
from ..models.config_manager import ConfigManager


@click.command()
@click.option(
    '--force',
    is_flag=True,
    help='Overwrite existing configuration without prompting'
)
def wizard(force: bool):
    """
    Interactive configuration wizard for FlowGenius.
    
    Guides you through setting up your FlowGenius configuration,
    including API keys, project directories, and preferences.
    """
    config_manager = ConfigManager()
    
    # Check if config already exists
    if config_manager.config_exists() and not force:
        if not click.confirm(
            f"Configuration already exists at {config_manager.get_config_path_str()}. "
            "Do you want to overwrite it?"
        ):
            click.echo("Configuration setup cancelled.")
            return
    
    click.echo("🧙 Welcome to the FlowGenius Configuration Wizard!")
    click.echo("Let's set up your FlowGenius environment.\n")
    
    # Prompt for OpenAI API key path
    default_key_path = get_default_openai_key_path()
    openai_key_path = click.prompt(
        "Path to your OpenAI API key file",
        default=str(default_key_path),
        type=click.Path(path_type=Path)
    )
    
    # Validate API key file exists
    if not openai_key_path.exists():
        if click.confirm(f"API key file doesn't exist at {openai_key_path}. Continue anyway?"):
            click.echo(f"⚠️  Remember to create your API key file at {openai_key_path}")
        else:
            click.echo("Configuration setup cancelled.")
            return
    
    # Prompt for projects root directory
    default_projects_root = get_default_projects_root()
    projects_root = click.prompt(
        "Root directory for your learning projects",
        default=str(default_projects_root),
        type=click.Path(path_type=Path)
    )
    
    # Create projects directory if it doesn't exist
    if not projects_root.exists():
        if click.confirm(f"Create projects directory at {projects_root}?"):
            try:
                projects_root.mkdir(parents=True, exist_ok=True)
                click.echo(f"✅ Created projects directory: {projects_root}")
            except Exception as e:
                click.echo(f"❌ Failed to create directory: {e}")
                return
    
    # Prompt for link style
    link_style = click.prompt(
        "Link style for markdown files",
        default="obsidian",
        type=click.Choice(['obsidian', 'markdown'], case_sensitive=False)
    )
    
    # Prompt for default model
    default_model = click.prompt(
        "Default OpenAI model for content generation",
        default="gpt-4o-mini",
        type=str
    )
    
    # Create configuration object
    try:
        config = FlowGeniusConfig(
            openai_key_path=openai_key_path,
            projects_root=projects_root,
            link_style=link_style.lower(),
            default_model=default_model
        )
    except Exception as e:
        click.echo(f"❌ Invalid configuration: {e}")
        return
    
    # Save configuration
    if config_manager.save_config(config):
        click.echo("\n🎉 Configuration saved successfully!")
        click.echo(f"📁 Config location: {config_manager.get_config_path_str()}")
        click.echo("\nYou're ready to start using FlowGenius!")
        click.echo("Try: flowgenius new \"learn Python data structures\"")
    else:
        click.echo("❌ Failed to save configuration.")


def validate_path_exists(ctx, param, value):
    """
    Validate that a given path exists.
    
    Args:
        ctx: Click context
        param: Click parameter
        value: Path value to validate
        
    Returns:
        Path if valid
        
    Raises:
        click.BadParameter: If path doesn't exist
    """
    if value and not Path(value).exists():
        raise click.BadParameter(f"Path does not exist: {value}")
    return Path(value) if value else None 