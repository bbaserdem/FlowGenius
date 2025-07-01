"""
FlowGenius Markdown Renderer

This module provides dedicated rendering functionality for generating
markdown files with integrated content from resource and task generation agents.
"""

from pathlib import Path
from typing import List, Optional, Dict, Any
import json
from datetime import datetime

from .config import FlowGeniusConfig
from .project import LearningProject, LearningUnit, LearningResource, EngageTask
from ..agents.content_generator import GeneratedContent


class MarkdownRenderer:
    """
    Dedicated renderer for generating markdown files from FlowGenius projects.
    
    Handles:
    - Table of contents (toc.md) generation
    - Individual unit files (unitXX.md) with integrated content
    - README files for projects
    - Progress tracking and status updates
    - Link style configuration (Obsidian vs standard markdown)
    """
    
    def __init__(self, config: FlowGeniusConfig) -> None:
        """
        Initialize the renderer with configuration.
        
        Args:
            config: FlowGenius configuration object
        """
        self.config = config
    
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
            progress_callback: Optional callback for progress updates
        """
        files_to_create = ["metadata", "toc", "units", "readme"]
        total_files = len(files_to_create)
        
        for i, file_type in enumerate(files_to_create, 1):
            if progress_callback:
                progress_callback(f"Creating {file_type} files...", i, total_files)
            
            if file_type == "metadata":
                self._write_metadata_file(project, project_dir)
            elif file_type == "toc":
                self._write_toc_file(project, project_dir, unit_content_map)
            elif file_type == "units":
                self._write_unit_files(project, project_dir, unit_content_map)
            elif file_type == "readme":
                self._write_readme_file(project, project_dir)
    
    def render_unit_file(
        self, 
        unit: LearningUnit, 
        project: LearningProject,
        output_path: Path,
        generated_content: Optional[GeneratedContent] = None
    ) -> None:
        """
        Render a single unit file with optional generated content.
        
        Args:
            unit: The learning unit to render
            project: The parent project for context
            output_path: Where to save the unit file
            generated_content: Optional curated resources and tasks
        """
        content = self._build_unit_content(unit, project, generated_content)
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
                updated_lines.append(f"status: {new_status}")
            else:
                updated_lines.append(line)
        
        unit_file_path.write_text('\n'.join(updated_lines))
    
    def _write_metadata_file(self, project: LearningProject, project_dir: Path) -> None:
        """Write project metadata as JSON."""
        metadata_file = project_dir / "project.json"
        metadata_dict = project.model_dump()
        
        with open(metadata_file, 'w') as f:
            json.dump(metadata_dict, f, indent=2, default=str)
    
    def _write_toc_file(
        self, 
        project: LearningProject, 
        project_dir: Path,
        unit_content_map: Optional[Dict[str, GeneratedContent]] = None
    ) -> None:
        """Write the table of contents markdown file."""
        toc_file = project_dir / "toc.md"
        content = self._build_toc_content(project, unit_content_map)
        toc_file.write_text(content)
    
    def _build_toc_content(
        self, 
        project: LearningProject,
        unit_content_map: Optional[Dict[str, GeneratedContent]] = None
    ) -> str:
        """Build the table of contents markdown content."""
        lines = []
        
        # YAML frontmatter
        lines.extend([
            "---",
            f"title: {project.title}",
            f"topic: {project.metadata.topic}",
            f"created: {project.metadata.created_at.isoformat()}",
            f"project_id: {project.project_id}",
        ])
        
        if project.metadata.motivation:
            lines.append(f"motivation: {project.metadata.motivation}")
        
        if project.metadata.estimated_total_time:
            lines.append(f"estimated_time: {project.metadata.estimated_total_time}")
        
        # Add content generation status if available
        if unit_content_map:
            generated_units = len([u for u in unit_content_map.values() if u.generation_success])
            total_units = len(project.units)
            lines.append(f"content_generated: {generated_units}/{total_units} units")
        
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
            content = self._build_unit_content(unit, project, generated_content)
            unit_file.write_text(content)
    
    def _build_unit_content(
        self, 
        unit: LearningUnit, 
        project: LearningProject,
        generated_content: Optional[GeneratedContent] = None
    ) -> str:
        """Build the content for a unit markdown file."""
        lines = []
        
        # YAML frontmatter
        lines.extend([
            "---",
            f"title: {unit.title}",
            f"unit_id: {unit.id}",
            f"project: {project.title}",
            f"status: {unit.status}",
        ])
        
        if unit.estimated_duration:
            lines.append(f"estimated_duration: {unit.estimated_duration}")
        
        if unit.prerequisites:
            lines.append(f"prerequisites: {unit.prerequisites}")
        
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
        
        content = f"""# {project.title}

{project.metadata.topic} learning project created with FlowGenius.

## Quick Start

1. 📖 **Read the overview**: Check out [`toc.md`](toc.md) for the complete learning plan
2. 🚀 **Start learning**: Begin with [Unit 1]({self._format_link(f"units/{project.units[0].id}.md", project.units[0].title)})
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