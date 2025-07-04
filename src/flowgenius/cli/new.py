"""
FlowGenius New Project Command

This module implements the 'flowgenius new' command for creating learning projects.
"""

import logging
import click
from pathlib import Path

from ..models.config_manager import ConfigManager
from ..models.project_generator import ProjectGenerator

# Set up module logger
logger = logging.getLogger(__name__)


@click.command()
@click.option(
    '--topic',
    prompt='What do you want to learn?',
    help='Learning topic or subject'
)
@click.option(
    '--motivation',
    prompt='Why do you want to learn this? (optional)',
    default='',
    help='Your motivation for learning this topic'
)
@click.option(
    '--units',
    prompt='How many learning units would you like?',
    default=3,
    type=int,
    help='Number of learning units to generate (default: 3)'
)
@click.option(
    '--open-project',
    is_flag=True,
    help='Open the project directory after creation'
)
def new(topic: str, motivation: str, units: int, open_project: bool) -> None:
    """
    Create a new learning project.
    
    This command will generate a structured learning plan for your topic,
    complete with learning units, objectives, and organized markdown files.
    """
    # Load configuration
    config_manager = ConfigManager()
    config = config_manager.load_config()
    
    if not config:
        click.echo("❌ No configuration found. Please run 'flowgenius wizard' first.")
        raise click.Abort()
    
    try:
        # Initialize project generator
        generator = ProjectGenerator(config)
        
        # Show what we're about to do
        click.echo(f"\n🎯 Creating learning project for: {click.style(topic, fg='cyan', bold=True)}")
        
        if motivation.strip():
            click.echo(f"💭 Motivation: {motivation}")
        
        click.echo(f"📚 Target units: {units}")
        click.echo()
        
        # Generate the project
        with click.progressbar(
            length=3,
            label='🤖 Generating learning plan',
            show_eta=False
        ) as bar:
            bar.update(1)  # Start
            project = generator.create_project(
                topic=topic,
                motivation=motivation.strip() if motivation.strip() else None,
                target_units=units
            )
            bar.update(2)  # AI generation complete
            bar.update(3)  # Files written
        
        # Success message
        click.echo()
        click.echo("✅ Project created successfully!")
        click.echo()
        
        # Show project details
        project_path = Path(config.projects_root) / project.project_id
        click.echo(f"📁 Project location: {click.style(str(project_path), fg='green')}")
        click.echo(f"🏷️  Project ID: {project.project_id}")
        click.echo()
        
        # Show generated units
        click.echo("📚 Generated learning units:")
        for i, unit in enumerate(project.units, 1):
            click.echo(f"  {i}. {unit.title}")
            if unit.estimated_duration:
                click.echo(f"     Duration: {unit.estimated_duration}")
        
        click.echo()
        
        # Getting started instructions
        click.echo("🚀 Getting started:")
        click.echo(f"  1. cd {project_path}")
        click.echo("  2. Read toc.md for the complete overview")
        click.echo(f"  3. Start with units/{project.units[0].id}.md")
        click.echo()
        
        # Handle opening project
        if open_project:
            _open_project_directory(project_path)
        else:
            click.echo("💡 Tip: Use --open-project flag to automatically open the project directory")
        
        click.echo(f"Happy learning! 🌟")
        
    except FileNotFoundError as e:
        click.echo(f"❌ Configuration error: {e}")
        click.echo("💡 Tip: Run 'flowgenius wizard' to set up your configuration")
        raise click.Abort()
    
    except (ValueError, TypeError) as e:
        click.echo(f"❌ Error creating project: {e}")
        click.echo("💡 Tip: Check your configuration and API key")
        logger.error(f"Error creating project: {e}", exc_info=True)
        raise click.Abort()


def _open_project_directory(project_path: Path) -> None:
    """
    Open the project directory in the default file manager.
    """
    import subprocess
    import sys
    
    try:
        if sys.platform == "darwin":  # macOS
            subprocess.run(["open", str(project_path)], check=True)
        elif sys.platform == "linux":  # Linux
            subprocess.run(["xdg-open", str(project_path)], check=True)
        elif sys.platform == "win32":  # Windows
            subprocess.run(["explorer", str(project_path)], check=True)
        
        click.echo(f"📂 Opened project directory in file manager")
        
    except subprocess.CalledProcessError:
        click.echo(f"💡 Could not open directory automatically. Navigate to: {project_path}")
    except FileNotFoundError:
        click.echo(f"💡 File manager not found. Navigate to: {project_path}")


# Alternative interface for users who prefer to specify everything upfront
@click.command()
@click.argument('topic')
@click.option(
    '--motivation',
    help='Why you want to learn this topic'
)
@click.option(
    '--units',
    default=3,
    type=int,
    help='Number of learning units to generate'
)
@click.option(
    '--open-project',
    is_flag=True,
    help='Open the project directory after creation'
)
def create(topic: str, motivation: str, units: int, open_project: bool) -> None:
    """
    Create a new learning project (non-interactive).
    
    Example: flowgenius create "guitar theory" --motivation="improve my compositions"
    """
    # Call the main new function with the provided arguments
    # We need to simulate the click context
    ctx = click.get_current_context()
    ctx.invoke(new, 
               topic=topic, 
               motivation=motivation or '', 
               units=units, 
               open_project=open_project) 