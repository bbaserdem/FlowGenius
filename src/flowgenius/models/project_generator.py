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
from ..agents.project_content_orchestrator import ProjectContentOrchestrator, create_project_orchestrator


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
        self._orchestrator: Optional[ProjectContentOrchestrator] = None
    
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
    
    @property
    def orchestrator(self) -> ProjectContentOrchestrator:
        """Lazy load the content orchestrator."""
        if self._orchestrator is None:
            # Load OpenAI API key
            api_key = self._load_api_key()
            client = OpenAI(api_key=api_key)
            self._orchestrator = ProjectContentOrchestrator(client, self.config.default_model)
        return self._orchestrator
    
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
        
        project = self.scaffolder.create_learning_project(
            topic=topic,
            motivation=motivation,
            target_units=target_units
        )
        
        # Use LangChain orchestrator to generate content for all units
        print("\n🤖 Using LangChain to orchestrate content generation...")
        orchestration_result = self.orchestrator.orchestrate_content_generation(
            project,
            use_obsidian_links=(self.config.link_style == "obsidian"),
            progress_callback=self._progress_callback
        )
        
        # Update project with generated content
        project = orchestration_result.project
        
        # Log orchestration results
        if orchestration_result.generation_notes:
            print("\n📝 Content Generation Notes:")
            for note in orchestration_result.generation_notes:
                print(f"  {note}")
        
        if orchestration_result.errors:
            print("\n⚠️ Content Generation Errors:")
            for error in orchestration_result.errors:
                print(f"  ❌ {error}")
        
        # Create project directory and files
        project_dir = self._create_project_directory(project)
        
        # Write project files with generated content
        self._write_project_files(project, project_dir, orchestration_result.content_map)
        
        return project
    
    def _progress_callback(self, message: str, current: int, total: int) -> None:
        """Progress callback for content generation."""
        print(f"  [{current}/{total}] {message}")
    
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
    
    def _write_project_files(self, project: LearningProject, project_dir: Path, content_map: Optional[dict] = None) -> None:
        """
        Write all project files to the directory using the MarkdownRenderer.
        
        Args:
            project: The learning project with generated content
            project_dir: Directory to write files to
            content_map: Optional map of unit IDs to GeneratedContent
        """
        self.renderer.render_project_files(project, project_dir, unit_content_map=content_map)
    
 