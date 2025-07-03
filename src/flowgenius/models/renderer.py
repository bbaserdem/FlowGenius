"""
FlowGenius Markdown Renderer

This module provides dedicated rendering functionality for generating
markdown files with integrated content from resource and task generation agents.
Enhanced with state.json integration for accurate progress tracking.
"""

from pathlib import Path
from typing import List, Optional, Dict, Any
import json
from datetime import datetime
from ruamel.yaml import YAML
from io import StringIO
import logging

from .config import FlowGeniusConfig
from .project import LearningProject, LearningUnit, LearningResource, EngageTask
from .state_store import StateStore, create_state_store
from ..agents.content_generator import GeneratedContent
from .settings import DefaultSettings
from ..utils import safe_save_json, ensure_project_structure

# Set up module logger
logger = logging.getLogger(__name__)

class MarkdownRenderer:
    """
    Dedicated renderer for generating markdown files from FlowGenius projects.
    
    Handles:
    - Table of contents (toc.md) generation
    - Individual unit files (unitXX.md) with integrated content
    - README files for projects
    - Progress tracking and status updates with state.json integration
    - Link style configuration (Obsidian vs standard markdown)
    """
    
    def __init__(self, config: FlowGeniusConfig) -> None:
        """
        Initialize the renderer with configuration.
        
        Args:
            config: FlowGenius configuration object
        """
        self.config = config
        self._cached_state_stores: Dict[str, StateStore] = {}
    
    def _get_state_store(self, project_dir: Path) -> StateStore:
        """
        Get or create a StateStore instance for the given project directory.
        Caches instances to avoid recreating them.
        
        Args:
            project_dir: Project directory path
            
        Returns:
            StateStore instance for the project
        """
        project_key = str(project_dir)
        if project_key not in self._cached_state_stores:
            self._cached_state_stores[project_key] = StateStore(project_dir)
        return self._cached_state_stores[project_key]
    
    def _get_unit_state_info(self, unit: LearningUnit, project_dir: Path) -> Dict[str, Any]:
        """
        Get unit state information from the state store.
        
        Args:
            unit: The learning unit
            project_dir: Project directory path
            
        Returns:
            Dictionary with state information including status, timestamps, notes
        """
        try:
            state_store = self._get_state_store(project_dir)
            
            # Load existing state if available
            try:
                state = state_store.load_state()
            except (OSError, IOError, ValueError) as e:
                # No existing state, return default
                logger.debug(f"No existing state found: {e}")
                return {
                    "status": unit.status,
                    "started_at": None,
                    "completed_at": None,
                    "progress_notes": []
                }
            
            # Get unit state from loaded state
            if unit.id in state.units:
                unit_state = state.units[unit.id]
                return {
                    "status": unit_state.status,
                    "started_at": unit_state.started_at,
                    "completed_at": unit_state.completed_at,
                    "progress_notes": unit_state.progress_notes
                }
            else:
                # Unit not in state, return default
                return {
                    "status": unit.status,
                    "started_at": None,
                    "completed_at": None,
                    "progress_notes": []
                }
        except (OSError, IOError, AttributeError) as e:
            # Fall back to unit data if state is not available
            logger.debug(f"Failed to get unit state info: {e}")
            return {
                "status": unit.status,
                "started_at": None,
                "completed_at": None,
                "progress_notes": []
            }
    
    def sync_with_state(self, project: LearningProject, project_dir: Path) -> None:
        """
        Synchronize project unit statuses with the state store.
        Updates the project in-memory to reflect current state and re-renders unit files.
        
        Args:
            project: Learning project to sync
            project_dir: Project directory containing state
        """
        try:
            state_store = self._get_state_store(project_dir)
            state_store.initialize_from_project(project)
            
            # Update unit statuses from state
            for unit in project.units:
                try:
                    unit_state = state_store.get_unit_state(unit.id)
                    unit.status = unit_state.status
                except (KeyError, AttributeError) as e:
                    # Keep original status if state is not available
                    logger.debug(f"Unit {unit.id} not found in state: {e}")
            
            # Re-render unit files with updated state
            self._write_unit_files(project, project_dir)
            
            # Also update TOC to reflect progress
            self._write_toc_file(project, project_dir)
            
        except (OSError, IOError, ValueError) as e:
            # If state sync fails, continue with original project data
            logger.warning(f"Failed to sync with state: {e}")
    
    def render_project_files_with_state(
        self, 
        project: LearningProject, 
        project_dir: Path,
        unit_content_map: Optional[Dict[str, GeneratedContent]] = None,
        progress_callback: Optional[callable] = None
    ) -> None:
        """
        Render project files with state integration.
        First syncs the project with current state, then renders all files.
        
        Args:
            project: The learning project to render
            project_dir: Directory where files should be created
            unit_content_map: Optional mapping of unit IDs to generated content
            progress_callback: Optional callback for progress updates
        """
        # Sync with state before rendering
        self.sync_with_state(project, project_dir)
        
        # Now render with updated state
        self.render_project_files(project, project_dir, unit_content_map, progress_callback)
    
    def _escape_yaml_value(self, value: Any) -> str:
        """
        Properly escape and quote YAML values when needed.
        
        Args:
            value: Value to escape
            
        Returns:
            Properly escaped YAML string
        """
        if value is None:
            return "null"
        
        value = str(value)
        
        # Check if the value needs quoting
        needs_quoting = (
            ':' in value or
            '"' in value or
            "'" in value or
            '#' in value or
            '&' in value or  # Add ampersand to the list
            '|' in value or  # Add pipe anywhere in string
            '>' in value or  # Add greater than anywhere in string
            '\n' in value or  # Add newline check
            value.startswith(('!', '&', '*', '[', ']', '{', '}', '|', '>', '@', '`')) or
            value.startswith(' ') or
            value.endswith(' ') or
            value.lower() in ['true', 'false', 'null', 'yes', 'no', 'on', 'off'] or
            (value.replace('.', '').replace('-', '').isdigit() and '.' in value) or  # looks like a number
            value.isdigit()  # is a number
        )
        
        if needs_quoting:
            # Use ruamel.yaml to properly escape the string
            yaml = YAML()
            yaml.preserve_quotes = DefaultSettings.YAML_PRESERVE_QUOTES
            yaml.width = DefaultSettings.YAML_LINE_WIDTH
            stream = StringIO()
            yaml.dump(value, stream)
            return stream.getvalue().strip()
        
        return value
    
    def render_project_files(
        self, 
        project: LearningProject, 
        project_dir: Path,
        unit_content_map: Optional[Dict[str, GeneratedContent]] = None,
        progress_callback: Optional[callable] = None
    ) -> None:
        """
        Render all project files to the specified directory.
        
        Args:
            project: The learning project to render
            project_dir: Directory where files should be created
            unit_content_map: Optional mapping of unit IDs to generated content
            progress_callback: Optional callback for progress updates (message, current, total)
        """
        # Ensure project directory structure exists
        self._ensure_project_directories(project_dir)
        
        # Calculate total steps (metadata, toc, readme + individual units)
        total_steps = 3 + len(project.units)  # metadata, toc, readme + each unit
        current_step = 0
        
        # Step 1: Write metadata
        current_step += 1
        if progress_callback:
            progress_callback("Creating project metadata...", current_step, total_steps)
        self._write_metadata_file(project, project_dir)
        
        # Step 2: Write TOC
        current_step += 1
        if progress_callback:
            progress_callback("Generating table of contents...", current_step, total_steps)
        self._write_toc_file(project, project_dir, unit_content_map)
        
        # Step 3: Write individual unit files with granular progress
        for i, unit in enumerate(project.units, 1):
            current_step += 1
            if progress_callback:
                progress_callback(f"Creating unit file {unit.id} ({i}/{len(project.units)})...", current_step, total_steps)
            
            unit_file = project_dir / "units" / f"{unit.id}.md"
            generated_content = unit_content_map.get(unit.id) if unit_content_map else None
            content = self._build_unit_content(unit, project, generated_content, project_dir)
            unit_file.write_text(content)
        
        # Final step: Write README
        current_step += 1
        if progress_callback:
            progress_callback("Creating README file...", current_step, total_steps)
        self._write_readme_file(project, project_dir)
    
    def render_unit_file(
        self, 
        unit: LearningUnit, 
        project: LearningProject,
        output_path: Path,
        generated_content: Optional[GeneratedContent] = None,
        project_dir: Optional[Path] = None
    ) -> None:
        """
        Render a single unit file with optional generated content and state integration.
        
        Args:
            unit: The learning unit to render
            project: The parent project for context
            output_path: Where to save the unit file
            generated_content: Optional curated resources and tasks
            project_dir: Optional project directory for state integration
        """
        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # If project_dir not provided, try to infer it from output_path
        if project_dir is None:
            project_dir = output_path.parent.parent
        
        content = self._build_unit_content(unit, project, generated_content, project_dir)
        output_path.write_text(content)
    
    def update_unit_progress(
        self,
        unit_file_path: Path,
        new_status: str,
        completion_date: Optional[datetime] = None
    ) -> None:
        """
        Update the status in an existing unit file's YAML frontmatter.
        
        Args:
            unit_file_path: Path to the unit markdown file
            new_status: New status value
            completion_date: Optional completion timestamp
        """
        if not unit_file_path.exists():
            raise FileNotFoundError(f"Unit file not found: {unit_file_path}")
        
        content = unit_file_path.read_text()
        
        # Simple YAML frontmatter update
        lines = content.split('\n')
        in_frontmatter = False
        updated_lines = []
        
        for line in lines:
            if line.strip() == '---':
                if not in_frontmatter:
                    in_frontmatter = True
                else:
                    # End of frontmatter
                    if completion_date and new_status.lower() == 'completed':
                        updated_lines.append(f"completed_date: {completion_date.isoformat()}")
                    in_frontmatter = False
                updated_lines.append(line)
            elif in_frontmatter and line.startswith('status:'):
                updated_lines.append(f"status: {self._escape_yaml_value(new_status)}")
            else:
                updated_lines.append(line)
        
        unit_file_path.write_text('\n'.join(updated_lines))
    
    def _write_metadata_file(self, project: LearningProject, project_dir: Path) -> None:
        """Write project metadata as JSON."""
        metadata_file = project_dir / "project.json"
        metadata_dict = project.model_dump()
        
        safe_save_json(metadata_dict, metadata_file)
    
    def _write_toc_file(
        self, 
        project: LearningProject, 
        project_dir: Path,
        unit_content_map: Optional[Dict[str, GeneratedContent]] = None
    ) -> None:
        """Write the table of contents markdown file."""
        toc_file = project_dir / "toc.md"
        content = self._build_toc_content(project, unit_content_map, project_dir)
        toc_file.write_text(content)
    
    def _build_toc_content(
        self, 
        project: LearningProject,
        unit_content_map: Optional[Dict[str, GeneratedContent]] = None,
        project_dir: Optional[Path] = None
    ) -> str:
        """Build the table of contents markdown content with state integration."""
        lines = []
        
        # Get progress summary from state if available
        progress_summary = None
        if project_dir:
            try:
                state_store = self._get_state_store(project_dir)
                state_store.initialize_from_project(project)
                progress_summary = state_store.get_progress_summary()
            except Exception:
                pass
        
        # YAML frontmatter
        lines.extend([
            "---",
            f"title: {self._escape_yaml_value(project.title)}",
            f"topic: {self._escape_yaml_value(project.metadata.topic)}",
            f"created: {project.metadata.created_at.isoformat()}",
            f"project_id: {self._escape_yaml_value(project.project_id)}",
        ])
        
        if project.metadata.motivation:
            lines.append(f"motivation: {self._escape_yaml_value(project.metadata.motivation)}")
        
        if project.metadata.estimated_total_time:
            lines.append(f"estimated_time: {self._escape_yaml_value(project.metadata.estimated_total_time)}")
        
        # Add content generation status if available
        if unit_content_map:
            generated_units = len([u for u in unit_content_map.values() if u.generation_success])
            total_units = len(project.units)
            lines.append(f"content_generated: {generated_units}/{total_units} units")
        
        # Add progress summary from state if available
        if progress_summary:
            lines.append(f"progress: {progress_summary['completed_units']}/{progress_summary['total_units']} completed ({progress_summary['completion_percentage']:.1f}%)")
        
        lines.extend([
            "---",
            "",
            f"# {project.title}",
            "",
        ])
        
        if project.metadata.motivation:
            lines.extend([
                "## Why This Topic?",
                f"{project.metadata.motivation}",
                "",
            ])
        
        # Learning units table
        lines.extend([
            "## Learning Units",
            "",
            "| Unit | Title | Duration | Status | Resources | Tasks |",
            "|------|-------|----------|--------|-----------|-------|"
        ])
        
        for unit in project.units:
            unit_link = self._format_link(f"units/{unit.id}.md", unit.title)
            duration = unit.estimated_duration or "TBD"
            
            # Use state data for status if available
            if project_dir:
                state_info = self._get_unit_state_info(unit, project_dir)
                status = state_info["status"].title()
            else:
                status = unit.status.title()
            
            # Add resource and task counts if available
            resources_count = "TBD"
            tasks_count = "TBD"
            
            if unit_content_map and unit.id in unit_content_map:
                content = unit_content_map[unit.id]
                if content.generation_success:
                    resources_count = str(len(content.resources))
                    tasks_count = str(len(content.engage_tasks))
            
            lines.append(f"| {unit.id} | {unit_link} | {duration} | {status} | {resources_count} | {tasks_count} |")
        
        lines.extend([
            "",
            "## Project Structure",
            "",
            "```",
            f"{project.project_id}/",
            "├── toc.md              # This file - project overview",
            "├── README.md           # Quick start guide", 
            "├── project.json        # Project metadata",
            "├── state.json          # Progress tracking state",
            "├── units/              # Learning unit files",
        ])
        
        for unit in project.units:
            lines.append(f"│   ├── {unit.id}.md")
        
        lines.extend([
            "├── resources/          # Additional learning materials",
            "└── notes/              # Your personal notes and progress",
            "```",
            "",
            "## Getting Started",
            "",
        ])
        
        if project.units:
            lines.extend([
                f"1. Start with {self._format_link(f'units/{project.units[0].id}.md', project.units[0].title)}",
                "2. Complete the learning objectives for each unit",
                "3. Take notes in the `notes/` directory",
                "4. Track your progress by updating unit status",
            ])
        else:
            lines.extend([
                "1. This project currently has no learning units",
                "2. Add some units to get started with your learning journey",
            ])
        
        lines.extend([
            "",
            "Happy learning! 🚀"
        ])
        
        return "\n".join(lines)
    
    def _write_unit_files(
        self, 
        project: LearningProject, 
        project_dir: Path,
        unit_content_map: Optional[Dict[str, GeneratedContent]] = None
    ) -> None:
        """Write individual unit markdown files."""
        units_dir = project_dir / "units"
        
        for unit in project.units:
            unit_file = units_dir / f"{unit.id}.md"
            generated_content = unit_content_map.get(unit.id) if unit_content_map else None
            content = self._build_unit_content(unit, project, generated_content, project_dir)
            unit_file.write_text(content)
    
    def _build_unit_content(
        self, 
        unit: LearningUnit, 
        project: LearningProject,
        generated_content: Optional[GeneratedContent] = None,
        project_dir: Optional[Path] = None
    ) -> str:
        """Build the content for a unit markdown file with state integration."""
        lines = []
        
        # Get state information if project_dir is provided
        state_info = None
        if project_dir:
            state_info = self._get_unit_state_info(unit, project_dir)
        
        # Use state data or fall back to unit data
        current_status = state_info["status"] if state_info else unit.status
        completed_at = state_info["completed_at"] if state_info else None
        started_at = state_info["started_at"] if state_info else None
        
        # YAML frontmatter
        lines.extend([
            "---",
            f"title: {self._escape_yaml_value(unit.title)}",
            f"unit_id: {self._escape_yaml_value(unit.id)}",
            f"project: {self._escape_yaml_value(project.title)}",
            f"status: {self._escape_yaml_value(current_status)}",
        ])
        
        if unit.estimated_duration:
            lines.append(f"estimated_duration: {self._escape_yaml_value(unit.estimated_duration)}")
        
        if unit.prerequisites:
            lines.append(f"prerequisites: {self._escape_yaml_value(unit.prerequisites)}")
        
        # Add state-based timestamps if available
        if started_at:
            lines.append(f"started_date: {started_at.isoformat()}")
        if completed_at:
            lines.append(f"completed_date: {completed_at.isoformat()}")
        
        # Add content generation metadata
        if generated_content:
            lines.append(f"content_generated: {generated_content.generation_success}")
            if generated_content.generation_success:
                lines.append(f"resources_count: {len(generated_content.resources)}")
                lines.append(f"tasks_count: {len(generated_content.engage_tasks)}")
        
        lines.extend([
            "---",
            "",
            f"# {unit.title}",
            "",
            unit.description,
            "",
        ])
        
        # Learning objectives
        lines.extend([
            "## Learning Objectives",
            "",
            "By the end of this unit, you will be able to:",
            "",
        ])
        
        for objective in unit.learning_objectives:
            lines.append(f"- {objective}")
        
        lines.append("")
        
        # Prerequisites (if any)
        if unit.prerequisites:
            lines.extend([
                "## Prerequisites",
                "",
                "Before starting this unit, make sure you've completed:",
                "",
            ])
            
            for prereq in unit.prerequisites:
                prereq_link = self._format_link(f"{prereq}.md", f"Unit {prereq}")
                lines.append(f"- {prereq_link}")
            
            lines.append("")
        
        # Resources section - enhanced with generated content
        lines.extend([
            "## Resources",
            "",
        ])
        
        if generated_content and generated_content.generation_success and generated_content.formatted_resources:
            for resource in generated_content.formatted_resources:
                lines.append(resource)
            lines.append("")
        else:
            lines.extend([
                "*Resources for this unit will be curated and added here.*",
                "",
                "<!-- TODO: Add curated resources -->",
                "",
            ])
        
        # Engaging tasks section - enhanced with generated content
        lines.extend([
            "## Practice & Engagement",
            "",
        ])
        
        if generated_content and generated_content.generation_success and generated_content.formatted_tasks:
            for task in generated_content.formatted_tasks:
                lines.append(task)
            lines.append("")
        else:
            lines.extend([
                "*Engaging tasks and practice exercises will be added here.*",
                "",
                "<!-- TODO: Add engaging tasks -->",
                "",
            ])
        
        # Generation notes (if any)
        if generated_content and generated_content.generation_notes:
            lines.extend([
                "## Content Generation Notes",
                "",
                "*Notes from the content generation process:*",
                "",
            ])
            for note in generated_content.generation_notes:
                lines.append(f"- {note}")
            lines.append("")
        
        # Progress notes from state (if any)
        if state_info and state_info["progress_notes"]:
            lines.extend([
                "## Progress Notes",
                "",
                "*Notes from your learning progress:*",
                "",
            ])
            for note in state_info["progress_notes"]:
                lines.append(f"- {note}")
            lines.append("")
        
        # Notes section
        lines.extend([
            "## Your Notes",
            "",
            "*Use this space for your personal notes, insights, and reflections.*",
            "",
            "",
        ])
        
        return "\n".join(lines)
    
    def _write_readme_file(self, project: LearningProject, project_dir: Path) -> None:
        """Write a README file for the project."""
        readme_file = project_dir / "README.md"
        
        # Handle empty projects gracefully
        if project.units:
            start_instruction = f"2. 🚀 **Start learning**: Begin with {self._format_link(f'units/{project.units[0].id}.md', project.units[0].title)}"
        else:
            start_instruction = "2. 📋 **Add units**: This project needs learning units to get started"
        
        content = f"""# {project.title}

{project.metadata.topic} learning project created with FlowGenius.

## Quick Start

1. 📖 **Read the overview**: Check out [`toc.md`](toc.md) for the complete learning plan
{start_instruction}
3. 📝 **Take notes**: Use the `notes/` directory for your thoughts and progress
4. 🔄 **Track progress**: Update unit status as you complete them

## Project Structure

- `toc.md` - Complete project overview and table of contents
- `units/` - Individual learning unit files  
- `resources/` - Additional learning materials
- `notes/` - Your personal notes and progress
- `project.json` - Project metadata

---
*Generated by FlowGenius - eliminating research paralysis through structured learning*
"""
        
        readme_file.write_text(content)
    
    def _format_link(self, path: str, title: str) -> str:
        """Format a link based on the configured link style."""
        if self.config.link_style == "obsidian":
            return f"[[{path}|{title}]]"
        else:  # markdown
            return f"[{title}]({path})"
    
    def _ensure_project_directories(self, project_dir: Path) -> None:
        """
        Ensure that the necessary project directory structure exists.
        
        Creates the main project directory and required subdirectories:
        - units/ for learning unit markdown files
        - resources/ for additional learning materials  
        - notes/ for user notes and progress tracking
        
        Args:
            project_dir: Path to the project directory
            
        Raises:
            OSError: If directory creation fails due to permissions or other issues
        """
        ensure_project_structure(project_dir)
    
    def track_unit_progress(
        self,
        project_dir: Path,
        unit_id: str,
        new_status: str,
        completion_date: Optional[datetime] = None,
        progress_callback: Optional[callable] = None
    ) -> None:
        """
        Track and update progress for a specific unit.
        
        Args:
            project_dir: Project directory containing unit files
            unit_id: ID of the unit to update
            new_status: New status for the unit
            completion_date: Optional completion timestamp
            progress_callback: Optional callback for progress updates
        """
        # Ensure units directory exists
        units_dir = project_dir / "units"
        units_dir.mkdir(parents=True, exist_ok=True)
        
        unit_file_path = units_dir / f"{unit_id}.md"
        
        if progress_callback:
            progress_callback(f"Updating progress for unit {unit_id}...", 1, 1)
        
        self.update_unit_progress(unit_file_path, new_status, completion_date)
        
        if progress_callback:
            status_message = f"Unit {unit_id} marked as {new_status}"
            if completion_date:
                status_message += f" (completed on {completion_date.strftime('%Y-%m-%d')})"
            progress_callback(status_message, 1, 1)
    
    def get_rendering_progress_info(self, project: LearningProject) -> Dict[str, Any]:
        """
        Get information about what will be rendered for progress estimation.
        
        Args:
            project: The learning project
            
        Returns:
            Dictionary with rendering progress information
        """
        return {
            "total_files": 3 + len(project.units),  # metadata, toc, readme + units
            "file_breakdown": {
                "metadata": 1,
                "toc": 1, 
                "readme": 1,
                "units": len(project.units)
            },
            "unit_files": [f"{unit.id}.md" for unit in project.units],
            "estimated_steps": 3 + len(project.units)
        }

    def write_markdown_to_file(self, file_path: Path, content: str) -> None:
        """
        Write markdown content to a file, creating parent directories if needed.
        
        Args:
            file_path: Target file path
            content: Markdown content to write
            
        Raises:
            OSError: If file cannot be written
        """
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        except (OSError, IOError) as e:
            logger.error(f"Failed to write markdown file {file_path}: {e}")
            raise 