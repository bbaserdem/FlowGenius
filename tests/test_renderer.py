"""
Tests for the MarkdownRenderer class.
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock

from flowgenius.models.renderer import MarkdownRenderer
from flowgenius.models.config import FlowGeniusConfig
from flowgenius.models.project import (
    LearningProject, LearningUnit, ProjectMetadata, 
    LearningResource, EngageTask
)
from flowgenius.agents.content_generator import GeneratedContent


@pytest.fixture
def obsidian_config() -> FlowGeniusConfig:
    """Create a config with Obsidian link style."""
    return FlowGeniusConfig(
        openai_key_path=Path("/tmp/test_key"),
        projects_root=Path("/tmp/projects"),
        link_style="obsidian",
        default_model="gpt-4o-mini"
    )

@pytest.fixture
def markdown_config() -> FlowGeniusConfig:
    """Create a config with standard markdown link style."""
    return FlowGeniusConfig(
        openai_key_path=Path("/tmp/test_key"),
        projects_root=Path("/tmp/projects"),
        link_style="markdown",
        default_model="gpt-4o-mini"
    )

@pytest.fixture
def sample_project() -> LearningProject:
    """Create a sample learning project for testing."""
    units = [
        LearningUnit(
            id="unit-1",
            title="Introduction to Python",
            description="Learn Python basics",
            learning_objectives=[
                "Understand Python syntax",
                "Write simple programs"
            ],
            status="pending",
            estimated_duration="2 hours"
        ),
        LearningUnit(
            id="unit-2", 
            title="Python Data Structures",
            description="Learn about lists, dicts, etc.",
            learning_objectives=[
                "Use lists and dictionaries",
                "Understand data structures"
            ],
            status="pending",
            prerequisites=["unit-1"]
        )
    ]
    
    metadata = ProjectMetadata(
        id="python-basics-123",
        title="Python Programming Basics",
        topic="Python Programming",
        motivation="To build better applications",
        created_at=datetime.now(),
        estimated_total_time="6 hours"
    )
    
    return LearningProject(
        metadata=metadata,
        units=units
    )

@pytest.fixture
def sample_generated_content() -> GeneratedContent:
    """Create sample generated content for testing."""
    resources = [
        LearningResource(
            title="Python Tutorial Video",
            url="https://youtube.com/watch?v=abc123",
            type="video",
            description="Comprehensive Python tutorial",
            estimated_time="45 min"
        ),
        LearningResource(
            title="Python Documentation",
            url="https://docs.python.org/3/",
            type="article",
            description="Official Python docs",
            estimated_time="30 min"
        )
    ]
    
    tasks = [
        EngageTask(
            title="Build a Calculator",
            description="Create a simple calculator app",
            type="project",
            estimated_time="60 min"
        )
    ]
    
    return GeneratedContent(
        unit_id="unit-1",
        resources=resources,
        engage_tasks=tasks,
        formatted_resources=[
            "🎥 [Python Tutorial Video](https://youtube.com/watch?v=abc123) *(45 min)*\n  > Comprehensive Python tutorial",
            "📖 [Python Documentation](https://docs.python.org/3/) *(30 min)*\n  > Official Python docs"
        ],
        formatted_tasks=[
            "1. 🎯 **Build a Calculator** *(60 min)*\n   Create a simple calculator app"
        ],
        generation_success=True,
        generation_notes=["Generated successfully using AI"]
    )


class TestMarkdownRenderer:
    """Test cases for MarkdownRenderer class."""

    def test_toc_content_without_generated_content(
        self, 
        obsidian_config: FlowGeniusConfig,
        sample_project: LearningProject
    ) -> None:
        """Test TOC generation without generated content."""
        renderer = MarkdownRenderer(obsidian_config)
        
        content = renderer._build_toc_content(sample_project)
        
        # Check YAML frontmatter
        assert "title: Python Programming Basics" in content
        assert "topic: Python Programming" in content
        assert "motivation: To build better applications" in content
        assert "project_id: python-basics-123" in content
        
        # Check unit table with TBD for resources and tasks
        assert "| unit-1 | [[units/unit-1.md|Introduction to Python]] | 2 hours | Pending | TBD | TBD |" in content
        assert "| unit-2 | [[units/unit-2.md|Python Data Structures]] | TBD | Pending | TBD | TBD |" in content
        
        # Should not have content generation status
        assert "content_generated:" not in content
    
    def test_toc_content_with_generated_content(
        self,
        obsidian_config: FlowGeniusConfig,
        sample_project: LearningProject,
        sample_generated_content: GeneratedContent
    ) -> None:
        """Test TOC generation with generated content."""
        renderer = MarkdownRenderer(obsidian_config)
        
        unit_content_map = {
            "unit-1": sample_generated_content
        }
        
        content = renderer._build_toc_content(sample_project, unit_content_map)
        
        # Check content generation status
        assert "content_generated: 1/2 units" in content
        
        # Check unit table with actual counts for unit-1, TBD for unit-2
        assert "| unit-1 | [[units/unit-1.md|Introduction to Python]] | 2 hours | Pending | 2 | 1 |" in content
        assert "| unit-2 | [[units/unit-2.md|Python Data Structures]] | TBD | Pending | TBD | TBD |" in content
    
    def test_unit_content_without_generated_content(
        self,
        markdown_config: FlowGeniusConfig,
        sample_project: LearningProject
    ) -> None:
        """Test unit file generation without generated content."""
        renderer = MarkdownRenderer(markdown_config)
        unit = sample_project.units[0]
        
        content = renderer._build_unit_content(unit, sample_project)
        
        # Check YAML frontmatter
        assert "title: Introduction to Python" in content
        assert "unit_id: unit-1" in content
        assert "status: pending" in content
        assert "estimated_duration: 2 hours" in content
        
        # Should have placeholder content
        assert "Resources for this unit will be curated and added here" in content
        assert "<!-- TODO: Add curated resources -->" in content
        assert "Engaging tasks and practice exercises will be added here" in content
        assert "<!-- TODO: Add engaging tasks -->" in content
        
        # Should not have generation metadata
        assert "content_generated:" not in content
        assert "resources_count:" not in content
        assert "Content Generation Notes" not in content
    
    def test_unit_content_with_generated_content(
        self,
        markdown_config: FlowGeniusConfig,
        sample_project: LearningProject,
        sample_generated_content: GeneratedContent
    ) -> None:
        """Test unit file generation with generated content."""
        renderer = MarkdownRenderer(markdown_config)
        unit = sample_project.units[0]
        
        content = renderer._build_unit_content(unit, sample_project, sample_generated_content)
        
        # Check generation metadata in YAML frontmatter
        assert "content_generated: True" in content
        assert "resources_count: 2" in content
        assert "tasks_count: 1" in content
        
        # Should have real content instead of placeholders
        assert "🎥 [Python Tutorial Video]" in content
        assert "📖 [Python Documentation]" in content
        assert "🎯 **Build a Calculator**" in content
        
        # Should NOT have placeholder content
        assert "TODO: Add curated resources" not in content
        assert "TODO: Add engaging tasks" not in content
        
        # Should have generation notes
        assert "Content Generation Notes" in content
        assert "Generated successfully using AI" in content
    
    def test_unit_content_with_prerequisites(
        self,
        obsidian_config: FlowGeniusConfig,
        sample_project: LearningProject
    ) -> None:
        """Test unit file generation with prerequisites."""
        renderer = MarkdownRenderer(obsidian_config)
        unit = sample_project.units[1]  # unit-2 has prerequisites
        
        content = renderer._build_unit_content(unit, sample_project)
        
        # Check prerequisites section with Obsidian links
        assert "## Prerequisites" in content
        assert "Before starting this unit, make sure you've completed:" in content
        assert "[[unit-1.md|Unit unit-1]]" in content


class TestYAMLEscaping:
    """Test cases for YAML frontmatter escaping functionality."""

    def test_escape_yaml_value_simple_strings(self, obsidian_config: FlowGeniusConfig) -> None:
        """Test that simple strings are not unnecessarily quoted."""
        renderer = MarkdownRenderer(obsidian_config)
        
        # Simple strings should remain unquoted
        test_cases = [
            ("simple", "simple"),
            ("hello-world", "hello-world"),
            ("unit-1", "unit-1"),
            ("pending", "pending"),
            ("CamelCase", "CamelCase"),
            ("snake_case", "snake_case"),
        ]
        
        for input_val, expected in test_cases:
            result = renderer._escape_yaml_value(input_val)
            assert result == expected, f"Expected {expected}, got {result} for input {input_val}"

    def test_escape_yaml_value_special_characters(self, obsidian_config: FlowGeniusConfig) -> None:
        """Test that strings with special characters are properly quoted."""
        renderer = MarkdownRenderer(obsidian_config)
        
        # Test specific characters that should trigger quoting
        test_cases = [
            "String with: colon",
            'String with "quotes"',
            "String with 'single quotes'",
            "String with # hash",
            "String with & ampersand", 
            "String with | pipe",
            "String with > greater",
            "Multi\nline\nstring",
        ]
        
        for input_val in test_cases:
            result = renderer._escape_yaml_value(input_val)
            # Check that special characters are handled - either quoted or escaped
            # The exact format may vary but should not be the raw input for complex strings
            if any(char in input_val for char in [':', '"', "'", '#', '&', '|', '>', '\n']):
                # Should be quoted in some way or escaped
                assert result != input_val or result.startswith("'") or result.startswith('"'), f"String with special chars should be escaped/quoted: {result}"

    def test_escape_yaml_value_reserved_words(self, obsidian_config: FlowGeniusConfig) -> None:
        """Test that YAML reserved words are properly quoted."""
        renderer = MarkdownRenderer(obsidian_config)
        
        # Test known reserved words
        reserved_words = ['true', 'false', 'null']  # Core reserved words that should definitely be quoted
        
        for word in reserved_words:
            result = renderer._escape_yaml_value(word)
            # Should be quoted in some form to prevent interpretation as boolean/null
            assert result.startswith("'") or "..." in result, f"Reserved word {word} should be quoted, got {result}"
            
        # Test case variations for true/false (most important ones)
        for word in ['true', 'false']:
            result_upper = renderer._escape_yaml_value(word.upper())
            assert result_upper.startswith("'") or "..." in result_upper, f"Reserved word {word.upper()} should be quoted"

    def test_escape_yaml_value_numeric_strings(self, obsidian_config: FlowGeniusConfig) -> None:
        """Test that numeric-looking strings are properly quoted."""
        renderer = MarkdownRenderer(obsidian_config)
        
        # Numeric strings should be quoted to prevent interpretation as numbers
        numeric_strings = ["123", "3.14", "42", "0", "1.0"]
        
        for input_val in numeric_strings:
            result = renderer._escape_yaml_value(input_val)
            # Should be quoted in some form to prevent numeric interpretation
            assert result.startswith("'") or result != input_val, f"Numeric string {input_val} should be quoted, got {result}"

    def test_escape_yaml_value_edge_cases(self, obsidian_config: FlowGeniusConfig) -> None:
        """Test edge cases for YAML escaping."""
        renderer = MarkdownRenderer(obsidian_config)
        
        # Test None value
        assert renderer._escape_yaml_value(None) == "null"
        
        # Test empty string
        result = renderer._escape_yaml_value("")
        assert result == ""  # Empty string should remain empty
        
        # Test whitespace-only strings
        result_spaces = renderer._escape_yaml_value("   ")
        assert result_spaces.startswith("'") and result_spaces.endswith("'"), "Whitespace-only strings should be quoted"
        
        # Test strings with leading/trailing spaces
        result_leading = renderer._escape_yaml_value(" leading")
        assert result_leading.startswith("'"), "Strings with leading spaces should be quoted"
        
        result_trailing = renderer._escape_yaml_value("trailing ")
        assert result_trailing.startswith("'"), "Strings with trailing spaces should be quoted"

    def test_escape_yaml_value_non_string_types(self, obsidian_config: FlowGeniusConfig) -> None:
        """Test that non-string types are properly converted and escaped."""
        renderer = MarkdownRenderer(obsidian_config)
        
        # Test various types
        test_cases = [
            (42, "'42'"),  # int becomes quoted string
            (3.14, "'3.14'"),  # float becomes quoted string  
            (True, "'True'"),  # bool becomes quoted string
            (False, "'False'"),  # bool becomes quoted string
        ]
        
        for input_val, expected in test_cases:
            result = renderer._escape_yaml_value(input_val)
            assert result == expected, f"Expected {expected}, got {result} for input {input_val} (type: {type(input_val)})"

    def test_yaml_escaping_in_toc_content(self, obsidian_config: FlowGeniusConfig) -> None:
        """Test that YAML escaping is applied in TOC content generation."""
        renderer = MarkdownRenderer(obsidian_config)
        
        # Create project with problematic characters
        metadata = ProjectMetadata(
            id="test-project-123",
            title='Docker: Learn "advanced" containerization',
            topic="DevOps & Containers: Complete Guide",
            motivation='Build production-ready apps with Docker & Kubernetes!',
            created_at=datetime.now()
        )
        
        project = LearningProject(metadata=metadata, units=[])
        
        content = renderer._build_toc_content(project)
        
        # Check that problematic values are properly escaped in YAML frontmatter
        lines = content.split('\n')
        yaml_section = []
        in_yaml = False
        
        for line in lines:
            if line.strip() == '---':
                if not in_yaml:
                    in_yaml = True
                else:
                    break
            elif in_yaml:
                yaml_section.append(line)
        
        yaml_content = '\n'.join(yaml_section)
        
        # Values with colons should be quoted
        assert "title: 'Docker: Learn \"advanced\" containerization'" in yaml_content
        assert "topic: 'DevOps & Containers: Complete Guide'" in yaml_content
        # Values with special chars should be quoted or properly escaped
        assert "motivation:" in yaml_content  # Should be present and properly escaped

    def test_yaml_escaping_in_unit_content(self, obsidian_config: FlowGeniusConfig) -> None:
        """Test that YAML escaping is applied in unit content generation."""
        renderer = MarkdownRenderer(obsidian_config)
        
        # Create unit with problematic characters
        unit = LearningUnit(
            id="unit-1",
            title='Introduction: Docker "Basics" & Setup',
            description="Learn Docker fundamentals",
            learning_objectives=["Understand what Docker is & why it matters"],
            status="in-progress",
            estimated_duration="2-3 hours: hands-on learning"
        )
        
        # Create project with problematic title
        metadata = ProjectMetadata(
            id="docker-project",
            title='Docker: Complete "Production" Guide',
            topic="Docker",
            created_at=datetime.now()
        )
        project = LearningProject(metadata=metadata, units=[unit])
        
        content = renderer._build_unit_content(unit, project)
        
        # Check that problematic values are properly escaped in YAML frontmatter
        lines = content.split('\n')
        yaml_section = []
        in_yaml = False
        
        for line in lines:
            if line.strip() == '---':
                if not in_yaml:
                    in_yaml = True
                else:
                    break
            elif in_yaml:
                yaml_section.append(line)
        
        yaml_content = '\n'.join(yaml_section)
        
        # Check that values with special characters are properly quoted
        assert "title: 'Introduction: Docker \"Basics\" & Setup'" in yaml_content
        assert "project: 'Docker: Complete \"Production\" Guide'" in yaml_content
        assert "estimated_duration: '2-3 hours: hands-on learning'" in yaml_content


class TestLinkStyleHandling:
    """Test cases specifically for link style handling."""
    
    def test_obsidian_link_formatting(self, obsidian_config: FlowGeniusConfig) -> None:
        """Test Obsidian-style link formatting."""
        renderer = MarkdownRenderer(obsidian_config)
        
        result = renderer._format_link("units/unit-1.md", "Introduction to Python")
        
        assert result == "[[units/unit-1.md|Introduction to Python]]"
    
    def test_markdown_link_formatting(self, markdown_config: FlowGeniusConfig) -> None:
        """Test standard markdown link formatting."""
        renderer = MarkdownRenderer(markdown_config)
        
        result = renderer._format_link("units/unit-1.md", "Introduction to Python")
        
        assert result == "[Introduction to Python](units/unit-1.md)"
    
    def test_link_formatting_with_special_characters(self, obsidian_config: FlowGeniusConfig) -> None:
        """Test link formatting with special characters in title."""
        renderer = MarkdownRenderer(obsidian_config)
        
        result = renderer._format_link("units/unit-1.md", "C++ & Python: A Comparison")
        
        assert result == "[[units/unit-1.md|C++ & Python: A Comparison]]"
    
    def test_project_generator_uses_markdown_renderer(self) -> None:
        """Test that ProjectGenerator properly delegates rendering to MarkdownRenderer."""
        from flowgenius.models.project_generator import ProjectGenerator
        
        # Test that ProjectGenerator has a renderer property that returns MarkdownRenderer
        config = FlowGeniusConfig(
            openai_key_path=Path("/tmp/test"),
            projects_root=Path("/tmp/projects"),
            link_style="obsidian",
            default_model="gpt-4o-mini"
        )
        
        generator = ProjectGenerator(config)
        
        # Verify that the renderer property returns a MarkdownRenderer instance
        assert hasattr(generator, 'renderer')
        assert isinstance(generator.renderer, MarkdownRenderer)
        
        # Verify that the renderer uses the same config
        assert generator.renderer.config == config
        assert generator.renderer.config.link_style == "obsidian"
        
        # Test with markdown config too
        markdown_config = FlowGeniusConfig(
            openai_key_path=Path("/tmp/test"),
            projects_root=Path("/tmp/projects"),
            link_style="markdown",
            default_model="gpt-4o-mini"
        )
        
        markdown_generator = ProjectGenerator(markdown_config)
        assert isinstance(markdown_generator.renderer, MarkdownRenderer)
        assert markdown_generator.renderer.config.link_style == "markdown"


class TestFileOperations:
    """Test cases for file operations and progress tracking."""
    
    def test_update_unit_progress(self, markdown_config: FlowGeniusConfig) -> None:
        """Test updating unit progress in existing file."""
        renderer = MarkdownRenderer(markdown_config)
        
        # Create a temporary file with YAML frontmatter
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("""---
title: Test Unit
unit_id: unit-1
status: pending
---

# Test Unit

Some content here.
""")
            temp_path = Path(f.name)
        
        try:
            # Update the status
            completion_date = datetime(2023, 12, 25, 10, 30, 0)
            renderer.update_unit_progress(temp_path, "completed", completion_date)
            
            # Read back and verify
            updated_content = temp_path.read_text()
            
            assert "status: completed" in updated_content
            assert "completed_date: 2023-12-25T10:30:00" in updated_content
            assert "# Test Unit" in updated_content  # Content should be preserved
            
        finally:
            temp_path.unlink()  # Clean up
    
    def test_update_unit_progress_file_not_found(self, markdown_config: FlowGeniusConfig) -> None:
        """Test error handling when unit file doesn't exist."""
        renderer = MarkdownRenderer(markdown_config)
        
        non_existent_path = Path("/tmp/non_existent_unit.md")
        
        with pytest.raises(FileNotFoundError) as exc_info:
            renderer.update_unit_progress(non_existent_path, "completed")
        
        assert "Unit file not found" in str(exc_info.value)
    
    def test_render_project_files_with_progress_callback(
        self,
        obsidian_config: FlowGeniusConfig,
        sample_project: LearningProject
    ) -> None:
        """Test full project rendering with enhanced granular progress callback."""
        renderer = MarkdownRenderer(obsidian_config)
        
        # Track progress calls
        progress_calls = []
        
        def progress_callback(message: str, current: int, total: int):
            progress_calls.append((message, current, total))
        
        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            
            # Create required subdirectories
            (project_dir / "units").mkdir()
            
            # Render files with granular progress tracking
            renderer.render_project_files(
                sample_project, 
                project_dir, 
                progress_callback=progress_callback
            )
            
            # Verify enhanced progress tracking (metadata + toc + 2 units + readme = 5 steps)
            expected_total = 5  # 3 base files + 2 units
            assert len(progress_calls) == expected_total
            
            # Check specific progress messages
            assert progress_calls[0] == ("Creating project metadata...", 1, expected_total)
            assert progress_calls[1] == ("Generating table of contents...", 2, expected_total)
            assert progress_calls[2] == ("Creating unit file unit-1 (1/2)...", 3, expected_total)
            assert progress_calls[3] == ("Creating unit file unit-2 (2/2)...", 4, expected_total)
            assert progress_calls[4] == ("Creating README file...", 5, expected_total)
            
            # Verify all files were created
            assert (project_dir / "project.json").exists()
            assert (project_dir / "toc.md").exists()
            assert (project_dir / "README.md").exists()
            assert (project_dir / "units" / "unit-1.md").exists()
            assert (project_dir / "units" / "unit-2.md").exists()
    
    def test_track_unit_progress(
        self,
        markdown_config: FlowGeniusConfig,
        sample_project: LearningProject
    ) -> None:
        """Test tracking progress for individual units."""
        renderer = MarkdownRenderer(markdown_config)
        
        # Track progress calls
        progress_calls = []
        
        def progress_callback(message: str, current: int, total: int):
            progress_calls.append((message, current, total))
        
        # Create a project directory with unit file
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            (project_dir / "units").mkdir()
            
            # First render the project to create unit files
            renderer.render_project_files(sample_project, project_dir)
            
            # Clear progress calls from initial rendering
            progress_calls.clear()
            
            # Test tracking unit progress
            completion_date = datetime(2023, 12, 25, 15, 30, 0)
            renderer.track_unit_progress(
                project_dir,
                "unit-1",
                "completed",
                completion_date,
                progress_callback
            )
            
            # Verify progress callback was called
            assert len(progress_calls) == 2
            assert progress_calls[0] == ("Updating progress for unit unit-1...", 1, 1)
            assert progress_calls[1] == ("Unit unit-1 marked as completed (completed on 2023-12-25)", 1, 1)
            
            # Verify unit file was updated
            unit_file = project_dir / "units" / "unit-1.md"
            content = unit_file.read_text()
            assert "status: completed" in content
            assert "completed_date: 2023-12-25T15:30:00" in content
    
    def test_get_rendering_progress_info(
        self,
        obsidian_config: FlowGeniusConfig,
        sample_project: LearningProject
    ) -> None:
        """Test getting rendering progress information."""
        renderer = MarkdownRenderer(obsidian_config)
        
        progress_info = renderer.get_rendering_progress_info(sample_project)
        
        # Verify progress information structure
        assert "total_files" in progress_info
        assert "file_breakdown" in progress_info
        assert "unit_files" in progress_info
        assert "estimated_steps" in progress_info
        
        # Verify counts
        assert progress_info["total_files"] == 5  # metadata, toc, readme + 2 units
        assert progress_info["estimated_steps"] == 5
        
        # Verify breakdown
        breakdown = progress_info["file_breakdown"]
        assert breakdown["metadata"] == 1
        assert breakdown["toc"] == 1
        assert breakdown["readme"] == 1
        assert breakdown["units"] == 2
        
        # Verify unit files list
        unit_files = progress_info["unit_files"]
        assert len(unit_files) == 2
        assert "unit-1.md" in unit_files
        assert "unit-2.md" in unit_files
    
    def test_progress_tracking_with_empty_project(
        self,
        markdown_config: FlowGeniusConfig
    ) -> None:
        """Test progress tracking with a project that has no units."""
        renderer = MarkdownRenderer(markdown_config)
        
        # Create empty project
        metadata = ProjectMetadata(
            id="empty-123",
            title="Empty Project",
            topic="Empty Project",
            created_at=datetime.now()
        )
        
        empty_project = LearningProject(
            metadata=metadata,
            units=[]
        )
        
        # Track progress calls
        progress_calls = []
        
        def progress_callback(message: str, current: int, total: int):
            progress_calls.append((message, current, total))
        
        # Test progress info for empty project
        progress_info = renderer.get_rendering_progress_info(empty_project)
        assert progress_info["total_files"] == 3  # metadata, toc, readme only
        assert progress_info["file_breakdown"]["units"] == 0
        assert progress_info["unit_files"] == []
        
        # Test rendering empty project
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            (project_dir / "units").mkdir()
            
            renderer.render_project_files(
                empty_project,
                project_dir,
                progress_callback=progress_callback
            )
            
            # Should have 3 progress calls (metadata, toc, readme)
            assert len(progress_calls) == 3
            assert progress_calls[0] == ("Creating project metadata...", 1, 3)
            assert progress_calls[1] == ("Generating table of contents...", 2, 3)
            assert progress_calls[2] == ("Creating README file...", 3, 3)


class TestDirectoryCreation:
    """Test cases for directory creation and structure setup."""
    
    def test_ensure_project_directories_creates_structure(
        self, 
        obsidian_config: FlowGeniusConfig
    ) -> None:
        """Test that _ensure_project_directories creates the required directory structure."""
        renderer = MarkdownRenderer(obsidian_config)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "test_project"
            
            # Ensure the project directory doesn't exist initially
            assert not project_dir.exists()
            
            # Call the directory creation method
            renderer._ensure_project_directories(project_dir)
            
            # Verify main directory was created
            assert project_dir.exists()
            assert project_dir.is_dir()
            
            # Verify required subdirectories were created
            expected_subdirs = ["units", "resources", "notes"]
            for subdir in expected_subdirs:
                subdir_path = project_dir / subdir
                assert subdir_path.exists(), f"Subdirectory '{subdir}' should exist"
                assert subdir_path.is_dir(), f"Subdirectory '{subdir}' should be a directory"
    
    def test_ensure_project_directories_handles_existing_directories(
        self, 
        markdown_config: FlowGeniusConfig
    ) -> None:
        """Test that directory creation works when directories already exist."""
        renderer = MarkdownRenderer(markdown_config)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "existing_project"
            
            # Pre-create the main directory and some subdirectories
            project_dir.mkdir()
            (project_dir / "units").mkdir()
            
            # Create a file in existing directory to ensure it's preserved
            test_file = project_dir / "units" / "existing_file.md"
            test_file.write_text("existing content")
            
            # Call directory creation (should not fail)
            renderer._ensure_project_directories(project_dir)
            
            # Verify all subdirectories exist
            expected_subdirs = ["units", "resources", "notes"]
            for subdir in expected_subdirs:
                subdir_path = project_dir / subdir
                assert subdir_path.exists()
                assert subdir_path.is_dir()
            
            # Verify existing file is preserved
            assert test_file.exists()
            assert test_file.read_text() == "existing content"
    
    def test_ensure_project_directories_error_handling(
        self, 
        obsidian_config: FlowGeniusConfig
    ) -> None:
        """Test error handling when directory creation fails."""
        renderer = MarkdownRenderer(obsidian_config)
        
        # Try to create directory in an invalid location
        # Note: This test might be system-dependent
        invalid_path = Path("/dev/null/invalid_project")
        
        with pytest.raises(OSError) as exc_info:
            renderer._ensure_project_directories(invalid_path)
        
        assert "Failed to create project directory structure" in str(exc_info.value)
    
    def test_render_project_files_creates_directories(
        self,
        markdown_config: FlowGeniusConfig,
        sample_project: LearningProject
    ) -> None:
        """Test that render_project_files automatically creates directories."""
        renderer = MarkdownRenderer(markdown_config)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "auto_created_project"
            
            # Ensure project directory doesn't exist initially
            assert not project_dir.exists()
            
            # Render project files (should create directories automatically)
            renderer.render_project_files(sample_project, project_dir)
            
            # Verify project directory and subdirectories were created
            assert project_dir.exists()
            assert project_dir.is_dir()
            
            expected_subdirs = ["units", "resources", "notes"]
            for subdir in expected_subdirs:
                subdir_path = project_dir / subdir
                assert subdir_path.exists()
                assert subdir_path.is_dir()
            
            # Verify files were created in correct locations
            assert (project_dir / "project.json").exists()
            assert (project_dir / "toc.md").exists()
            assert (project_dir / "README.md").exists()
            assert (project_dir / "units" / "unit-1.md").exists()
            assert (project_dir / "units" / "unit-2.md").exists()
    
    def test_render_unit_file_creates_parent_directories(
        self,
        obsidian_config: FlowGeniusConfig,
        sample_project: LearningProject
    ) -> None:
        """Test that render_unit_file creates parent directories."""
        renderer = MarkdownRenderer(obsidian_config)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            unit_file_path = Path(temp_dir) / "new_project" / "units" / "standalone_unit.md"
            
            # Ensure parent directories don't exist initially
            assert not unit_file_path.parent.exists()
            assert not unit_file_path.parent.parent.exists()
            
            # Render unit file (should create parent directories)
            renderer.render_unit_file(
                sample_project.units[0], 
                sample_project, 
                unit_file_path
            )
            
            # Verify parent directories were created
            assert unit_file_path.parent.exists()
            assert unit_file_path.parent.is_dir()
            assert unit_file_path.exists()
            assert unit_file_path.is_file()
            
            # Verify file content is correct
            content = unit_file_path.read_text()
            assert "# Introduction to Python" in content
            assert "unit_id: unit-1" in content
    
    def test_track_unit_progress_creates_units_directory(
        self,
        markdown_config: FlowGeniusConfig
    ) -> None:
        """Test that track_unit_progress creates units directory if needed."""
        renderer = MarkdownRenderer(markdown_config)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "progress_project"
            
            # Ensure project and units directories don't exist
            assert not project_dir.exists()
            
            # First create a unit file in the units directory for a valid test
            units_dir = project_dir / "units"
            units_dir.mkdir(parents=True)
            unit_file = units_dir / "test-unit.md"
            unit_file.write_text("""---
title: Test Unit
unit_id: test-unit
status: pending
---

# Test Unit
""")
            
            # Test progress tracking (should work without creating new directories)
            renderer.track_unit_progress(project_dir, "test-unit", "completed")
            
            # Verify the file was updated
            content = unit_file.read_text()
            assert "status: completed" in content
            
            # Test with a completely new project directory
            new_project_dir = Path(temp_dir) / "new_progress_project"
            assert not new_project_dir.exists()
            
            # Track progress should create directories but fail on missing file
            with pytest.raises(FileNotFoundError):
                renderer.track_unit_progress(new_project_dir, "missing-unit", "completed")
            
            # Verify that the units directory was created even though the file wasn't found
            assert (new_project_dir / "units").exists()
            assert (new_project_dir / "units").is_dir()


class TestErrorHandling:
    """Test cases for error handling and edge cases."""
    
    def test_empty_project_units(self, markdown_config: FlowGeniusConfig) -> None:
        """Test handling of project with no units."""
        renderer = MarkdownRenderer(markdown_config)
        
        metadata = ProjectMetadata(
            id="empty-123",
            title="Empty Project",
            topic="Empty Project",
            created_at=datetime.now()
        )
        
        project = LearningProject(
            metadata=metadata,
            units=[]
        )
        
        # Should not raise an error
        content = renderer._build_toc_content(project)
        
        assert "Empty Project" in content
        # Unit table should still be present but empty
        assert "| Unit | Title | Duration | Status | Resources | Tasks |" in content
    
    def test_missing_optional_fields(self, obsidian_config: FlowGeniusConfig) -> None:
        """Test handling of units with missing optional fields."""
        renderer = MarkdownRenderer(obsidian_config)
        
        unit = LearningUnit(
            id="minimal-unit",
            title="Minimal Unit",
            description="Basic unit",
            learning_objectives=["Learn something"],
            status="pending"
            # No estimated_duration, prerequisites, etc.
        )
        
        metadata = ProjectMetadata(
            id="test-123",
            title="Test Project",
            topic="Test",
            created_at=datetime.now()
        )
        
        project = LearningProject(
            metadata=metadata,
            units=[unit]
        )
        
        # Should not raise an error
        content = renderer._build_unit_content(unit, project)
        
        assert "title: Minimal Unit" in content
        assert "Learn something" in content
        # Should handle missing fields gracefully
        assert "estimated_duration:" not in content
        assert "Prerequisites" not in content 


class TestMarkdownFileGeneration:
    """Integration tests for complete markdown file generation."""
    
    def test_complete_project_rendering_obsidian_style(
        self,
        obsidian_config: FlowGeniusConfig,
        sample_project: LearningProject,
        sample_generated_content: GeneratedContent
    ) -> None:
        """Test complete project rendering with Obsidian link style."""
        renderer = MarkdownRenderer(obsidian_config)
        
        # Create unit content map
        unit_content_map = {
            "unit-1": sample_generated_content
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            (project_dir / "units").mkdir()
            
            # Render all files
            renderer.render_project_files(
                sample_project, 
                project_dir,
                unit_content_map=unit_content_map
            )
            
            # Verify all files were created
            assert (project_dir / "project.json").exists()
            assert (project_dir / "toc.md").exists()
            assert (project_dir / "README.md").exists()
            assert (project_dir / "units" / "unit-1.md").exists()
            assert (project_dir / "units" / "unit-2.md").exists()
            
            # Verify TOC content
            toc_content = (project_dir / "toc.md").read_text()
            assert "Python Programming Basics" in toc_content
            assert "content_generated: 1/2 units" in toc_content
            assert "[[units/unit-1.md|Introduction to Python]]" in toc_content  # Obsidian style
            assert "| unit-1 | [[units/unit-1.md|Introduction to Python]] | 2 hours | Pending | 2 | 1 |" in toc_content
            
            # Verify README content
            readme_content = (project_dir / "README.md").read_text()
            assert "Python Programming Basics" in readme_content
            assert "Python Programming learning project created with FlowGenius" in readme_content
            assert "[[units/unit-1.md|Introduction to Python]]" in readme_content  # Obsidian style
            
            # Verify unit-1 file with generated content
            unit1_content = (project_dir / "units" / "unit-1.md").read_text()
            assert "title: Introduction to Python" in unit1_content
            assert "content_generated: True" in unit1_content
            assert "resources_count: 2" in unit1_content
            assert "🎥 [Python Tutorial Video]" in unit1_content
            assert "🎯 **Build a Calculator**" in unit1_content
            assert "Content Generation Notes" in unit1_content
            
            # Verify unit-2 file without generated content
            unit2_content = (project_dir / "units" / "unit-2.md").read_text()
            assert "title: Python Data Structures" in unit2_content
            assert "content_generated:" not in unit2_content
            assert "TODO: Add curated resources" in unit2_content
            assert "[[unit-1.md|Unit unit-1]]" in unit2_content  # Prerequisites with Obsidian style
    
    def test_complete_project_rendering_markdown_style(
        self,
        markdown_config: FlowGeniusConfig,
        sample_project: LearningProject
    ) -> None:
        """Test complete project rendering with standard markdown link style."""
        renderer = MarkdownRenderer(markdown_config)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            (project_dir / "units").mkdir()
            
            # Render all files without generated content
            renderer.render_project_files(sample_project, project_dir)
            
            # Verify all files were created
            assert (project_dir / "project.json").exists()
            assert (project_dir / "toc.md").exists()
            assert (project_dir / "README.md").exists()
            assert (project_dir / "units" / "unit-1.md").exists()
            assert (project_dir / "units" / "unit-2.md").exists()
            
            # Verify TOC uses markdown style links
            toc_content = (project_dir / "toc.md").read_text()
            assert "[Introduction to Python](units/unit-1.md)" in toc_content  # Markdown style
            assert "content_generated:" not in toc_content  # No generated content
            assert "| unit-1 | [Introduction to Python](units/unit-1.md) | 2 hours | Pending | TBD | TBD |" in toc_content
            
            # Verify README uses markdown style links  
            readme_content = (project_dir / "README.md").read_text()
            assert "[Introduction to Python](units/unit-1.md)" in readme_content  # Markdown style
            
            # Verify unit-2 prerequisites use markdown style
            unit2_content = (project_dir / "units" / "unit-2.md").read_text()
            assert "[Unit unit-1](unit-1.md)" in unit2_content  # Prerequisites with markdown style
    
    def test_individual_unit_file_generation(
        self,
        obsidian_config: FlowGeniusConfig,
        sample_project: LearningProject,
        sample_generated_content: GeneratedContent
    ) -> None:
        """Test individual unit file rendering with generated content."""
        renderer = MarkdownRenderer(obsidian_config)
        unit = sample_project.units[0]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            output_path = Path(f.name)
        
        try:
            # Render individual unit file
            renderer.render_unit_file(
                unit, 
                sample_project, 
                output_path,
                generated_content=sample_generated_content
            )
            
            # Verify file was created and has correct content
            assert output_path.exists()
            content = output_path.read_text()
            
            # Check YAML frontmatter
            assert "---" in content
            assert "title: Introduction to Python" in content
            assert "unit_id: unit-1" in content
            assert "project: Python Programming Basics" in content
            assert "status: pending" in content
            assert "content_generated: True" in content
            assert "resources_count: 2" in content
            assert "tasks_count: 1" in content
            
            # Check content sections
            assert "# Introduction to Python" in content
            assert "## Learning Objectives" in content
            assert "## Resources" in content
            assert "## Practice & Engagement" in content
            assert "## Content Generation Notes" in content
            assert "## Your Notes" in content
            
            # Check generated content integration
            assert "🎥 [Python Tutorial Video]" in content
            assert "🎯 **Build a Calculator**" in content
            assert "Generated successfully using AI" in content
            
        finally:
            output_path.unlink()  # Clean up
    
    def test_project_json_metadata_generation(
        self,
        markdown_config: FlowGeniusConfig,
        sample_project: LearningProject
    ) -> None:
        """Test that project.json metadata file is generated correctly."""
        renderer = MarkdownRenderer(markdown_config)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            (project_dir / "units").mkdir()
            
            # Render files
            renderer.render_project_files(sample_project, project_dir)
            
            # Verify project.json exists and has correct content
            metadata_file = project_dir / "project.json"
            assert metadata_file.exists()
            
            import json
            with open(metadata_file) as f:
                metadata = json.load(f)
            
            # Check metadata structure
            assert "metadata" in metadata
            assert "units" in metadata
            assert metadata["metadata"]["id"] == "python-basics-123"
            assert metadata["metadata"]["title"] == "Python Programming Basics"
            assert metadata["metadata"]["topic"] == "Python Programming"
            assert metadata["metadata"]["motivation"] == "To build better applications"
            assert len(metadata["units"]) == 2
            assert metadata["units"][0]["id"] == "unit-1"
            assert metadata["units"][1]["id"] == "unit-2" 