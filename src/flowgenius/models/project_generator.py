"""
FlowGenius Project Generator

This module handles creating learning projects, including directory structure
and markdown file generation.
"""

import json
from pathlib import Path
from typing import Optional
from openai import OpenAI

from .config import FlowGeniusConfig
from .project import LearningProject
from ..agents.topic_scaffolder import TopicScaffolderAgent, ScaffoldingRequest


class ProjectGenerator:
    """
    Handles the complete process of generating learning projects.
    
    Creates project directories, generates learning structure via AI,
    and writes markdown files.
    """
    
    def __init__(self, config: FlowGeniusConfig):
        self.config = config
        self._scaffolder: Optional[TopicScaffolderAgent] = None
    
    @property
    def scaffolder(self) -> TopicScaffolderAgent:
        """Lazy load the scaffolder agent."""
        if self._scaffolder is None:
            # Load OpenAI API key
            api_key = self._load_api_key()
            client = OpenAI(api_key=api_key)
            self._scaffolder = TopicScaffolderAgent(client, self.config.default_model)
        return self._scaffolder
    
    def create_project(
        self, 
        topic: str, 
        motivation: Optional[str] = None,
        target_units: int = 3
    ) -> LearningProject:
        """
        Create a complete learning project.
        
        Args:
            topic: The learning topic
            motivation: Optional motivation for learning
            target_units: Number of learning units to generate
            
        Returns:
            Created LearningProject
        """
        # Generate the project structure
        request = ScaffoldingRequest(
            topic=topic,
            motivation=motivation,
            target_units=target_units
        )
        
        project = self.scaffolder.scaffold_topic(request)
        
        # Create project directory and files
        project_dir = self._create_project_directory(project)
        self._write_project_files(project, project_dir)
        
        return project
    
    def _load_api_key(self) -> str:
        """Load the OpenAI API key from the configured path."""
        key_path = Path(self.config.openai_key_path).expanduser()
        
        if not key_path.exists():
            raise FileNotFoundError(
                f"OpenAI API key file not found at {key_path}. "
                f"Run 'flowgenius wizard' to configure."
            )
        
        return key_path.read_text().strip()
    
    def _create_project_directory(self, project: LearningProject) -> Path:
        """Create the project directory structure."""
        projects_root = Path(self.config.projects_root).expanduser()
        project_dir = projects_root / project.project_id
        
        # Create directory
        project_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        (project_dir / "units").mkdir(exist_ok=True)
        (project_dir / "resources").mkdir(exist_ok=True)
        (project_dir / "notes").mkdir(exist_ok=True)
        
        return project_dir
    
    def _write_project_files(self, project: LearningProject, project_dir: Path):
        """Write all project files to the directory."""
        # Write project metadata
        self._write_metadata_file(project, project_dir)
        
        # Write table of contents
        self._write_toc_file(project, project_dir)
        
        # Write individual unit files
        self._write_unit_files(project, project_dir)
        
        # Write README
        self._write_readme_file(project, project_dir)
    
    def _write_metadata_file(self, project: LearningProject, project_dir: Path):
        """Write project metadata as JSON."""
        metadata_file = project_dir / "project.json"
        
        # Convert to dict for JSON serialization
        metadata_dict = project.model_dump()
        
        with open(metadata_file, 'w') as f:
            json.dump(metadata_dict, f, indent=2, default=str)
    
    def _write_toc_file(self, project: LearningProject, project_dir: Path):
        """Write the table of contents markdown file."""
        toc_file = project_dir / "toc.md"
        
        # Build the table of contents content
        content = self._build_toc_content(project)
        
        toc_file.write_text(content)
    
    def _build_toc_content(self, project: LearningProject) -> str:
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
        
        lines.extend([
            "---",
            "",
            f"# {project.title}",
            ""
        ])
        
        if project.metadata.motivation:
            lines.extend([
                "## Why This Topic?",
                f"{project.metadata.motivation}",
                ""
            ])
        
        # Learning units table
        lines.extend([
            "## Learning Units",
            "",
            "| Unit | Title | Duration | Status |",
            "|------|-------|----------|--------|"
        ])
        
        for unit in project.units:
            unit_link = self._format_link(f"units/{unit.id}.md", unit.title)
            duration = unit.estimated_duration or "TBD"
            status = unit.status.title()
            
            lines.append(f"| {unit.id} | {unit_link} | {duration} | {status} |")
        
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
            f"1. Start with {self._format_link(f'units/{project.units[0].id}.md', project.units[0].title)}",
            "2. Complete the learning objectives for each unit",
            "3. Take notes in the `notes/` directory",
            "4. Track your progress by updating unit status",
            "",
            "Happy learning! 🚀"
        ])
        
        return "\n".join(lines)
    
    def _write_unit_files(self, project: LearningProject, project_dir: Path):
        """Write individual unit markdown files."""
        units_dir = project_dir / "units"
        
        for unit in project.units:
            unit_file = units_dir / f"{unit.id}.md"
            content = self._build_unit_content(unit, project)
            unit_file.write_text(content)
    
    def _build_unit_content(self, unit, project: LearningProject) -> str:
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
        
        lines.extend([
            "---",
            "",
            f"# {unit.title}",
            "",
            unit.description,
            ""
        ])
        
        # Learning objectives
        lines.extend([
            "## Learning Objectives",
            "",
            "By the end of this unit, you will be able to:",
            ""
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
                ""
            ])
            
            for prereq in unit.prerequisites:
                prereq_link = self._format_link(f"{prereq}.md", f"Unit {prereq}")
                lines.append(f"- {prereq_link}")
            
            lines.append("")
        
        # Resources section (placeholder)
        lines.extend([
            "## Resources",
            "",
            "*Resources for this unit will be curated and added here.*",
            "",
            "<!-- TODO: Add curated resources -->",
            ""
        ])
        
        # Engaging tasks section (placeholder)
        lines.extend([
            "## Practice & Engagement",
            "",
            "*Engaging tasks and practice exercises will be added here.*",
            "",
            "<!-- TODO: Add engaging tasks -->",
            ""
        ])
        
        # Notes section
        lines.extend([
            "## Your Notes",
            "",
            "*Use this space for your personal notes, insights, and reflections.*",
            "",
            ""
        ])
        
        return "\n".join(lines)
    
    def _write_readme_file(self, project: LearningProject, project_dir: Path):
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