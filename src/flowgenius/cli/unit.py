"""
FlowGenius Unit Management Commands

This module implements unit-related commands for managing learning progress
within FlowGenius projects.
"""

import click
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

from ..models.config_manager import ConfigManager
from ..models.state_store import StateStore, create_state_store
from ..models.renderer import MarkdownRenderer
from ..models.project import LearningProject


def _find_project_directory() -> Optional[Path]:
    """
    Find the current project directory by looking for project.json.
    
    Returns:
        Path to project directory if found, None otherwise
    """
    current_dir = Path.cwd()
    
    # Check current directory and parent directories
    for path in [current_dir] + list(current_dir.parents):
        project_file = path / "project.json"
        if project_file.exists():
            return path
    
    return None


def _load_project_from_directory(project_dir: Path) -> Optional[LearningProject]:
    """
    Load a LearningProject from a project directory.
    
    Args:
        project_dir: Path to the project directory
        
    Returns:
        LearningProject if successfully loaded, None otherwise
    """
    project_file = project_dir / "project.json"
    
    if not project_file.exists():
        return None
    
    try:
        with open(project_file, 'r') as f:
            project_data = json.load(f)
        
        # Convert datetime strings back to datetime objects
        if 'metadata' in project_data:
            metadata = project_data['metadata']
            if 'created_at' in metadata:
                metadata['created_at'] = datetime.fromisoformat(metadata['created_at'])
            if 'updated_at' in metadata:
                metadata['updated_at'] = datetime.fromisoformat(metadata['updated_at'])
        
        return LearningProject(**project_data)
        
    except (json.JSONDecodeError, TypeError, ValueError):
        return None


@click.group()
def unit() -> None:
    """
    Manage learning units within FlowGenius projects.
    
    These commands help you track progress and manage individual learning units
    within your projects.
    """
    pass


@unit.command("mark-done")
@click.argument('unit_id')
@click.option(
    '--completion-date',
    type=click.DateTime(formats=["%Y-%m-%d", "%Y-%m-%d %H:%M:%S"]),
    help='Completion date (defaults to now). Format: YYYY-MM-DD or "YYYY-MM-DD HH:MM:SS"'
)
@click.option(
    '--notes',
    help='Optional notes about the completion'
)
@click.option(
    '--dry-run',
    is_flag=True,
    help='Show what would be updated without making changes'
)
def mark_done(unit_id: str, completion_date: Optional[datetime], notes: Optional[str], dry_run: bool) -> None:
    """
    Mark a learning unit as completed.
    
    This command updates both the state.json file and the corresponding
    markdown file for the specified unit.
    
    Examples:
        flowgenius unit mark-done unit-1
        flowgenius unit mark-done unit-2 --completion-date "2024-01-15"
        flowgenius unit mark-done unit-3 --notes "Great unit, learned a lot!"
    """
    # Find the current project directory
    project_dir = _find_project_directory()
    if not project_dir:
        click.echo("❌ No FlowGenius project found in current directory or parent directories.")
        click.echo("💡 Tip: Navigate to a project directory or run this command from within a project.")
        raise click.Abort()
    
    click.echo(f"📁 Found project: {click.style(str(project_dir.name), fg='cyan', bold=True)}")
    
    # Load the project to verify the unit exists
    project = _load_project_from_directory(project_dir)
    if not project:
        click.echo("❌ Unable to load project.json. The project may be corrupted.")
        raise click.Abort()
    
    # Verify the unit exists
    unit = project.get_unit_by_id(unit_id)
    if not unit:
        click.echo(f"❌ Unit '{unit_id}' not found in this project.")
        click.echo()
        click.echo("Available units:")
        for u in project.units:
            status_emoji = {"pending": "⏸️", "in-progress": "🔄", "completed": "✅"}.get(u.status, "❓")
            click.echo(f"  {status_emoji} {u.id}: {u.title}")
        raise click.Abort()
    
    click.echo(f"📚 Unit: {click.style(unit.title, fg='green')}")
    
    # Load configuration for MarkdownRenderer
    config_manager = ConfigManager()
    config = config_manager.load_config()
    if not config:
        click.echo("❌ No configuration found. Some features may not work correctly.")
        click.echo("💡 Tip: Run 'flowgenius wizard' to set up your configuration.")
        # Continue anyway, as we can still update state.json
    
    # Initialize State Store and MarkdownRenderer
    state_store = create_state_store(project_dir)
    # Ensure state store is initialized with all project units
    state_store.initialize_from_project(project)
    renderer = MarkdownRenderer(config) if config else None
    
    # Set completion date
    if completion_date is None:
        completion_date = datetime.now()
    
    click.echo(f"📅 Completion date: {completion_date.strftime('%Y-%m-%d %H:%M:%S')}")
    
    if notes:
        click.echo(f"📝 Notes: {notes}")
    
    if dry_run:
        click.echo()
        click.echo("🔍 Dry run - showing what would be updated:")
        click.echo(f"  📄 state.json: {unit_id} → completed")
        
        units_dir = project_dir / "units"
        unit_file = units_dir / f"{unit_id}.md"
        if unit_file.exists():
            click.echo(f"  📝 {unit_file.name}: status → completed, completion date updated")
        else:
            click.echo(f"  📝 {unit_file.name}: file not found, would skip markdown update")
        
        click.echo()
        click.echo("💡 Run without --dry-run to apply changes")
        return
    
    # Check current status and warn if already completed
    current_status = state_store.get_unit_status(unit_id)
    if current_status == "completed":
        if not click.confirm(f"⚠️  Unit '{unit_id}' is already marked as completed. Update anyway?"):
            click.echo("Cancelled.")
            return
    
    click.echo()
    
    try:
        # Update state.json
        click.echo("🔄 Updating state.json...")
        state_store.update_unit_status(unit_id, "completed", completion_date)
        click.echo("✅ State updated successfully")
        
        # Update markdown file if it exists and renderer is available
        if renderer:
            units_dir = project_dir / "units"
            unit_file = units_dir / f"{unit_id}.md"
            
            if unit_file.exists():
                click.echo("🔄 Updating unit markdown file...")
                renderer.update_unit_progress(unit_file, "completed", completion_date)
                click.echo("✅ Markdown file updated successfully")
            else:
                click.echo(f"⚠️  Unit file {unit_file.name} not found, skipping markdown update")
        else:
            click.echo("⚠️  No configuration available, skipping markdown update")
        
        # Add notes to state if provided
        if notes:
            click.echo("📝 Adding completion notes...")
            state = state_store.load_state()
            unit_state = state.get_unit_state(unit_id)
            if unit_state:
                unit_state.progress_notes.append(f"Completed: {notes}")
                state_store.save_state(state)
                click.echo("✅ Notes added successfully")
        
        click.echo()
        click.echo("🎉 Unit marked as completed!")
        
        # Show progress summary
        summary = state_store.get_progress_summary()
        completed = summary["completed_units"]
        total = summary["total_units"]
        percentage = summary["completion_percentage"]
        
        click.echo(f"📊 Project progress: {completed}/{total} units completed ({percentage:.1f}%)")
        
        if completed == total:
            click.echo("🏆 Congratulations! You've completed all units in this project!")
        
    except Exception as e:
        click.echo(f"❌ Error updating unit: {e}")
        click.echo("💡 Please check file permissions and try again")
        raise click.Abort()


@unit.command("status")
@click.argument('unit_id', required=False)
@click.option(
    '--all',
    is_flag=True,
    help='Show status for all units'
)
def status(unit_id: Optional[str], all: bool) -> None:
    """
    Show the status of learning units.
    
    Examples:
        flowgenius unit status unit-1     # Show status for specific unit
        flowgenius unit status --all      # Show status for all units
    """
    # Find the current project directory
    project_dir = _find_project_directory()
    if not project_dir:
        click.echo("❌ No FlowGenius project found in current directory or parent directories.")
        raise click.Abort()
    
    # Load the project
    project = _load_project_from_directory(project_dir)
    if not project:
        click.echo("❌ Unable to load project.json.")
        raise click.Abort()
    
    # Initialize State Store
    state_store = create_state_store(project_dir)
    # Ensure state store is initialized with all project units
    state_store.initialize_from_project(project)
    
    if all or unit_id is None:
        # Show all units
        click.echo(f"📁 Project: {click.style(project.title, fg='cyan', bold=True)}")
        click.echo()
        
        for unit in project.units:
            current_status = state_store.get_unit_status(unit.id) or unit.status
            status_emoji = {"pending": "⏸️", "in-progress": "🔄", "completed": "✅"}.get(current_status, "❓")
            
            click.echo(f"{status_emoji} {click.style(unit.id, fg='blue')}: {unit.title}")
            click.echo(f"   Status: {current_status}")
            
            # Show completion date if completed
            if current_status == "completed":
                state = state_store.load_state()
                unit_state = state.get_unit_state(unit.id)
                if unit_state and unit_state.completed_at:
                    click.echo(f"   Completed: {unit_state.completed_at.strftime('%Y-%m-%d %H:%M:%S')}")
            
            click.echo()
        
        # Show overall progress
        summary = state_store.get_progress_summary()
        click.echo(f"📊 Overall Progress: {summary['completed_units']}/{summary['total_units']} units completed ({summary['completion_percentage']:.1f}%)")
        
    else:
        # Show specific unit
        unit = project.get_unit_by_id(unit_id)
        if not unit:
            click.echo(f"❌ Unit '{unit_id}' not found.")
            raise click.Abort()
        
        current_status = state_store.get_unit_status(unit_id) or unit.status
        status_emoji = {"pending": "⏸️", "in-progress": "🔄", "completed": "✅"}.get(current_status, "❓")
        
        click.echo(f"{status_emoji} {click.style(unit.title, fg='green', bold=True)}")
        click.echo(f"ID: {unit.id}")
        click.echo(f"Status: {current_status}")
        click.echo(f"Description: {unit.description}")
        
        if unit.estimated_duration:
            click.echo(f"Estimated Duration: {unit.estimated_duration}")
        
        # Show timestamps if available
        state = state_store.load_state()
        unit_state = state.get_unit_state(unit_id)
        if unit_state:
            if unit_state.started_at:
                click.echo(f"Started: {unit_state.started_at.strftime('%Y-%m-%d %H:%M:%S')}")
            if unit_state.completed_at:
                click.echo(f"Completed: {unit_state.completed_at.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Show notes if any
            if unit_state.progress_notes:
                click.echo("Notes:")
                for note in unit_state.progress_notes:
                    click.echo(f"  • {note}")


@unit.command("start")
@click.argument('unit_id')
def start(unit_id: str) -> None:
    """
    Mark a learning unit as in-progress.
    
    Example:
        flowgenius unit start unit-1
    """
    # Find the current project directory
    project_dir = _find_project_directory()
    if not project_dir:
        click.echo("❌ No FlowGenius project found in current directory or parent directories.")
        raise click.Abort()
    
    # Load the project to verify the unit exists
    project = _load_project_from_directory(project_dir)
    if not project:
        click.echo("❌ Unable to load project.json.")
        raise click.Abort()
    
    # Verify the unit exists
    unit = project.get_unit_by_id(unit_id)
    if not unit:
        click.echo(f"❌ Unit '{unit_id}' not found in this project.")
        raise click.Abort()
    
    # Initialize State Store
    state_store = create_state_store(project_dir)
    # Ensure state store is initialized with all project units
    state_store.initialize_from_project(project)
    
    # Check current status
    current_status = state_store.get_unit_status(unit_id)
    if current_status == "in-progress":
        click.echo(f"ℹ️  Unit '{unit_id}' is already in progress.")
        return
    elif current_status == "completed":
        if not click.confirm(f"⚠️  Unit '{unit_id}' is already completed. Mark as in-progress anyway?"):
            return
    
    try:
        # Update state.json
        state_store.update_unit_status(unit_id, "in-progress")
        
        click.echo(f"🔄 Unit '{unit.title}' marked as in-progress!")
        
        # Show progress summary
        summary = state_store.get_progress_summary()
        click.echo(f"📊 Project progress: {summary['completed_units']}/{summary['total_units']} units completed, {summary['in_progress_units']} in progress")
        
    except Exception as e:
        click.echo(f"❌ Error updating unit: {e}")
        raise click.Abort() 