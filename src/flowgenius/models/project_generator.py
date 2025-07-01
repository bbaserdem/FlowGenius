"""
FlowGenius Project Generator

This module handles creating learning projects, including directory structure
and markdown file generation.
"""

from pathlib import Path
from typing import Optional
from openai import OpenAI

from .config import FlowGeniusConfig
from .project import LearningProject
from .renderer import MarkdownRenderer
from ..agents.topic_scaffolder import TopicScaffolderAgent, ScaffoldingRequest


class ProjectGenerator:
    """
    Handles the complete process of generating learning projects.
    
    Creates project directories, generates learning structure via AI,
    and delegates markdown file generation to MarkdownRenderer.
    """
    
    def __init__(self, config: FlowGeniusConfig) -> None:
        self.config = config
        self._scaffolder: Optional[TopicScaffolderAgent] = None
        self._renderer: Optional[MarkdownRenderer] = None
    
    @property
    def scaffolder(self) -> TopicScaffolderAgent:
        """Lazy load the scaffolder agent."""
        if self._scaffolder is None:
            # Load OpenAI API key
            api_key = self._load_api_key()
            client = OpenAI(api_key=api_key)
            self._scaffolder = TopicScaffolderAgent(client, self.config.default_model)
        return self._scaffolder
    
    @property
    def renderer(self) -> MarkdownRenderer:
        """Lazy load the markdown renderer."""
        if self._renderer is None:
            self._renderer = MarkdownRenderer(self.config)
        return self._renderer
    
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
    
    def _write_project_files(self, project: LearningProject, project_dir: Path) -> None:
        """Write all project files to the directory using the MarkdownRenderer."""
        self.renderer.render_project_files(project, project_dir)
    
 