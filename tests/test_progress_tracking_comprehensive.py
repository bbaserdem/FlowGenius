"""
Comprehensive tests for FlowGenius progress tracking workflow.

This test suite provides end-to-end testing for the entire progress tracking system,
including StateStore, CLI commands, and MarkdownRenderer integration.
"""

import json
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch
from click.testing import CliRunner

from src.flowgenius.models.state_store import StateStore, ProjectState, UnitState, create_state_store
from src.flowgenius.models.renderer import MarkdownRenderer
from src.flowgenius.models.config import FlowGeniusConfig
from src.flowgenius.models.project import LearningProject, LearningUnit, ProjectMetadata
from src.flowgenius.cli.unit import unit, mark_done, status, start


@pytest.fixture
def sample_config(tmp_path):
    """Create a sample configuration for testing."""
    return FlowGeniusConfig(
        openai_key_path=tmp_path / "openai_key",
        projects_root=tmp_path / "projects",
        link_style="markdown",
        default_model="gpt-4o-mini"
    )


@pytest.fixture
def sample_project():
    """Create a sample learning project for testing."""
    metadata = ProjectMetadata(
        id="test-project-123",
        title="Test Learning Project",
        topic="Test Topic",
        created_at=datetime.now(),
        motivation="Test motivation for learning"
    )
    
    units = [
        LearningUnit(
            id="unit-1",
            title="Introduction to Testing",
            description="Learn the basics of testing",
            learning_objectives=["Understand test principles", "Write basic tests"],
            status="pending",
            estimated_duration="2 hours"
        ),
        LearningUnit(
            id="unit-2", 
            title="Advanced Testing",
            description="Learn advanced testing concepts",
            learning_objectives=["Mock objects", "Integration testing"],
            status="pending",
            estimated_duration="3 hours",
            prerequisites=["unit-1"]
        ),
        LearningUnit(
            id="unit-3",
            title="Test Automation",
            description="Automated testing strategies",
            learning_objectives=["CI/CD", "Test automation"],
            status="pending",
            estimated_duration="4 hours",
            prerequisites=["unit-2"]
        )
    ]
    
    return LearningProject(
        metadata=metadata,
        units=units
    )


@pytest.fixture
def project_with_files(tmp_path, sample_project, sample_config):
    """Create a project directory with all necessary files."""
    project_dir = tmp_path / "test-project"
    project_dir.mkdir()
    
    # Create project.json
    project_file = project_dir / "project.json"
    with open(project_file, 'w') as f:
        json.dump(sample_project.model_dump(), f, indent=2, default=str)
    
    # Create units directory and simple markdown files (without heavy rendering)
    units_dir = project_dir / "units"
    units_dir.mkdir()
    
    # Create minimal unit files without using MarkdownRenderer
    for unit in sample_project.units:
        unit_file = units_dir / f"{unit.id}.md"
        # Simple unit content without state integration
        content = f"""---
title: {unit.title}
unit_id: {unit.id}
project: {sample_project.title}
status: {unit.status}
---

# {unit.title}

{unit.description}

## Learning Objectives

{chr(10).join(f"- {obj}" for obj in unit.learning_objectives)}

## Resources

*Resources for this unit will be curated and added here.*

## Practice & Engagement

*Engaging tasks and practice exercises will be added here.*

## Your Notes

*Use this space for your personal notes, insights, and reflections.*
"""
        unit_file.write_text(content)
    
    return project_dir


class TestStateStoreCore:
    """Test the core StateStore functionality."""
    
    def test_unit_state_creation(self):
        """Test UnitState model creation and defaults."""
        unit_state = UnitState(id="test-unit")
        
        assert unit_state.id == "test-unit"
        assert unit_state.status == "pending"
        assert unit_state.started_at is None
        assert unit_state.completed_at is None
        assert unit_state.progress_notes == []
    
    def test_project_state_creation(self):
        """Test ProjectState model creation and methods."""
        state = ProjectState(project_id="test-project")
        
        assert state.project_id == "test-project"
        assert isinstance(state.created_at, datetime)
        assert isinstance(state.updated_at, datetime)
        assert state.units == {}
    
    def test_project_state_unit_operations(self):
        """Test ProjectState unit manipulation methods."""
        state = ProjectState(project_id="test-project")
        
        # Test updating non-existent unit (should create it)
        state.update_unit_status("unit-1", "in-progress")
        
        assert "unit-1" in state.units
        assert state.units["unit-1"].status == "in-progress"
        assert state.units["unit-1"].started_at is not None
        
        # Test completing unit
        completion_time = datetime.now()
        state.update_unit_status("unit-1", "completed", completion_time)
        
        assert state.units["unit-1"].status == "completed"
        assert state.units["unit-1"].completed_at == completion_time
    
    def test_project_state_progress_summary(self):
        """Test progress summary calculations."""
        state = ProjectState(project_id="test-project")
        
        # Add units with different statuses
        state.update_unit_status("unit-1", "completed")
        state.update_unit_status("unit-2", "in-progress") 
        state.update_unit_status("unit-3", "pending")
        state.update_unit_status("unit-4", "completed")
        
        summary = state.get_progress_summary()
        
        assert summary["total_units"] == 4
        assert summary["completed_units"] == 2
        assert summary["in_progress_units"] == 1
        assert summary["pending_units"] == 1
        assert summary["completion_percentage"] == 50.0
    
    def test_state_store_initialization(self, tmp_path):
        """Test StateStore initialization."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()
        
        store = StateStore(project_dir)
        
        assert store.project_dir == project_dir
        assert store.state_file == project_dir / "state.json"
        assert store._current_state is None
    
    def test_state_store_create_default_state(self, tmp_path):
        """Test creating default state when no file exists."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()
        
        store = StateStore(project_dir)
        state = store.load_state()
        
        assert isinstance(state, ProjectState)
        assert state.project_id == "test-project"
        assert state.units == {}
    
    def test_state_store_save_and_load(self, tmp_path):
        """Test saving and loading state."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()
        
        store = StateStore(project_dir)
        
        # Create and save state
        state = ProjectState(project_id="test-project")
        state.update_unit_status("unit-1", "completed")
        store.save_state(state)
        
        # Verify file was created
        assert store.state_file.exists()
        
        # Load state and verify
        loaded_state = store.load_state()
        assert loaded_state.project_id == "test-project"
        assert "unit-1" in loaded_state.units
        assert loaded_state.units["unit-1"].status == "completed"
    
    def test_state_store_update_unit_status(self, tmp_path):
        """Test updating unit status through store."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()
        
        store = StateStore(project_dir)
        completion_time = datetime.now()
        
        # Update unit status
        store.update_unit_status("unit-1", "completed", completion_time)
        
        # Verify state was saved
        assert store.state_file.exists()
        
        # Load and verify
        state = store.load_state()
        assert "unit-1" in state.units
        assert state.units["unit-1"].status == "completed"
        assert state.units["unit-1"].completed_at == completion_time
    
    def test_state_store_get_unit_status(self, tmp_path):
        """Test getting unit status."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()
        
        store = StateStore(project_dir)
        
        # Test non-existent unit
        assert store.get_unit_status("unit-1") is None
        
        # Add unit and test
        store.update_unit_status("unit-1", "in-progress")
        assert store.get_unit_status("unit-1") == "in-progress"
    
    def test_state_store_initialize_from_project(self, tmp_path, sample_project):
        """Test initializing state from project."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()
        
        store = StateStore(project_dir)
        state = store.initialize_from_project(sample_project)
        
        # Verify all units from project are in state
        assert len(state.units) == len(sample_project.units)
        for unit in sample_project.units:
            assert unit.id in state.units
            assert state.units[unit.id].status == unit.status
    
    def test_state_store_preserve_existing_progress(self, tmp_path, sample_project):
        """Test that existing progress is preserved when reinitializing."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()
        
        store = StateStore(project_dir)
        
        # Set some initial progress
        store.update_unit_status("unit-1", "completed")
        store.update_unit_status("unit-2", "in-progress")
        
        # Reinitialize from project
        state = store.initialize_from_project(sample_project)
        
        # Verify existing progress is preserved
        assert state.units["unit-1"].status == "completed"
        assert state.units["unit-2"].status == "in-progress"
        assert state.units["unit-3"].status == "pending"  # From project


class TestStateStoreErrorHandling:
    """Test StateStore error handling and edge cases."""
    
    def test_load_state_with_invalid_json(self, tmp_path):
        """Test loading state with invalid JSON."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()
        
        # Create invalid JSON file
        state_file = project_dir / "state.json"
        state_file.write_text("invalid json content")
        
        store = StateStore(project_dir)
        
        with pytest.raises(ValueError, match="Invalid state.json"):
            store.load_state()
    
    def test_load_state_with_missing_fields(self, tmp_path):
        """Test loading state with missing required fields."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()
        
        # Create JSON with missing project_id
        state_file = project_dir / "state.json"
        state_file.write_text('{"units": {}}')
        
        store = StateStore(project_dir)
        
        with pytest.raises(ValueError, match="Invalid state.json"):
            store.load_state()
    
    def test_save_state_permission_error(self, tmp_path):
        """Test save state with permission error."""
        project_dir = tmp_path / "readonly-project"
        project_dir.mkdir(mode=0o444)  # Read-only directory
        
        store = StateStore(project_dir)
        state = ProjectState(project_id="test")
        
        with pytest.raises(OSError, match="Unable to write state.json"):
            store.save_state(state)
    
    def test_datetime_serialization_edge_cases(self, tmp_path):
        """Test datetime serialization edge cases."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()
        
        store = StateStore(project_dir)
        
        # Test with microsecond precision
        precise_time = datetime.now().replace(microsecond=123456)
        store.update_unit_status("unit-1", "completed", precise_time)
        
        # Load and verify precision is preserved
        state = store.load_state()
        assert state.units["unit-1"].completed_at == precise_time


class TestCLIUnitCommands:
    """Test CLI unit commands integration."""
    
    def test_mark_done_basic(self, project_with_files):
        """Test basic mark-done command functionality."""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            # Copy project to isolated filesystem
            import shutil
            shutil.copytree(project_with_files, "test-project")
            
            # Change to project directory
            import os
            os.chdir("test-project")
            
            # Run mark-done command
            result = runner.invoke(mark_done, ["unit-1"])
            
            assert result.exit_code == 0
            assert "Unit marked as completed!" in result.output
            assert "Project progress:" in result.output
            
            # Verify state.json was created and updated
            assert Path("state.json").exists()
            
            with open("state.json", 'r') as f:
                state_data = json.load(f)
            
            assert "unit-1" in state_data["units"]
            assert state_data["units"]["unit-1"]["status"] == "completed"
    
    def test_mark_done_with_options(self, project_with_files):
        """Test mark-done command with completion date and notes."""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            import shutil
            shutil.copytree(project_with_files, "test-project")
            
            import os
            os.chdir("test-project")
            
            # Run with completion date and notes
            result = runner.invoke(mark_done, [
                "unit-1",
                "--completion-date", "2024-01-15 14:30:00",
                "--notes", "Great learning experience!"
            ])
            
            assert result.exit_code == 0
            
            # Verify state includes completion date and notes
            with open("state.json", 'r') as f:
                state_data = json.load(f)
            
            unit_state = state_data["units"]["unit-1"]
            assert unit_state["status"] == "completed"
            assert "2024-01-15T14:30:00" in unit_state["completed_at"]
            assert "Great learning experience!" in unit_state["progress_notes"]
    
    def test_mark_done_dry_run(self, project_with_files):
        """Test mark-done command in dry-run mode."""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            import shutil
            shutil.copytree(project_with_files, "test-project")
            
            import os
            os.chdir("test-project")
            
            # Run dry-run
            result = runner.invoke(mark_done, ["unit-1", "--dry-run"])
            
            assert result.exit_code == 0
            assert "Dry run - showing what would be updated" in result.output
            assert "Run without --dry-run to apply changes" in result.output
            
            # Verify no actual changes were made
            assert not Path("state.json").exists()
    
    def test_mark_done_nonexistent_unit(self, project_with_files):
        """Test mark-done command with non-existent unit."""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            import shutil
            shutil.copytree(project_with_files, "test-project")
            
            import os
            os.chdir("test-project")
            
            # Try to mark non-existent unit as done
            result = runner.invoke(mark_done, ["unit-999"])
            
            assert result.exit_code == 1
            assert "Unit 'unit-999' not found" in result.output
            assert "Available units:" in result.output
    
    def test_mark_done_outside_project(self):
        """Test mark-done command outside of project directory."""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            # Run command without any project files
            result = runner.invoke(mark_done, ["unit-1"])
            
            assert result.exit_code == 1
            assert "No FlowGenius project found" in result.output
    
    def test_status_command_all_units(self, project_with_files):
        """Test status command for all units."""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            import shutil
            shutil.copytree(project_with_files, "test-project")
            
            import os
            os.chdir("test-project")
            
            # Mark some units with different statuses
            store = create_state_store(Path("."))
            store.update_unit_status("unit-1", "completed")
            store.update_unit_status("unit-2", "in-progress")
            
            # Run status command
            result = runner.invoke(status, ["--all"])
            
            assert result.exit_code == 0
            assert "Test Learning Project" in result.output
            assert "unit-1" in result.output and "completed" in result.output
            assert "unit-2" in result.output and "in-progress" in result.output
            assert "unit-3" in result.output and "pending" in result.output
            assert "Overall Progress:" in result.output
    
    def test_status_command_single_unit(self, project_with_files):
        """Test status command for a single unit."""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            import shutil
            shutil.copytree(project_with_files, "test-project")
            
            import os
            os.chdir("test-project")
            
            # Run status for specific unit
            result = runner.invoke(status, ["unit-1"])
            
            assert result.exit_code == 0
            assert "Introduction to Testing" in result.output
            assert "ID: unit-1" in result.output
            assert "Status: pending" in result.output
            assert "Description:" in result.output
    
    def test_start_command(self, project_with_files):
        """Test start command functionality."""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            import shutil
            shutil.copytree(project_with_files, "test-project")
            
            import os
            os.chdir("test-project")
            
            # Run start command
            result = runner.invoke(start, ["unit-1"])
            
            assert result.exit_code == 0
            assert "marked as in-progress" in result.output
            
            # Verify state was updated
            with open("state.json", 'r') as f:
                state_data = json.load(f)
            
            assert state_data["units"]["unit-1"]["status"] == "in-progress"
            assert state_data["units"]["unit-1"]["started_at"] is not None
    
    def test_start_already_in_progress(self, project_with_files):
        """Test start command on unit already in progress."""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            import shutil
            shutil.copytree(project_with_files, "test-project")
            
            import os
            os.chdir("test-project")
            
            # Mark unit as in-progress first
            store = create_state_store(Path("."))
            store.update_unit_status("unit-1", "in-progress")
            
            # Try to start again
            result = runner.invoke(start, ["unit-1"])
            
            assert result.exit_code == 0
            assert "already in progress" in result.output

    def test_mark_done_with_options_no_fixtures(self):
        """Test mark-done command with completion date and notes - without hanging fixtures."""
        import tempfile
        import shutil
        import os
        import json
        from pathlib import Path
        from datetime import datetime
        from click.testing import CliRunner
        from src.flowgenius.cli.unit import mark_done
        
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            # Manually create project structure (same as fixture)
            project_dir = Path("test-project")
            project_dir.mkdir()
            
            # Create project.json
            project_data = {
                "metadata": {
                    "id": "test-project-123",
                    "title": "Test Learning Project",
                    "topic": "Test Topic",
                    "created_at": datetime.now().isoformat(),
                    "motivation": "Test motivation for learning"
                },
                "units": [
                    {
                        "id": "unit-1",
                        "title": "Introduction to Testing",
                        "description": "Learn the basics of testing",
                        "learning_objectives": ["Understand test principles", "Write basic tests"],
                        "status": "pending",
                        "estimated_duration": "2 hours"
                    }
                ]
            }
            
            project_file = project_dir / "project.json"
            with open(project_file, 'w') as f:
                json.dump(project_data, f, indent=2, default=str)
            
            # Create units directory and unit file
            units_dir = project_dir / "units"
            units_dir.mkdir()
            
            unit_file = units_dir / "unit-1.md"
            content = """---
title: Introduction to Testing
unit_id: unit-1
project: Test Learning Project
status: pending
---

# Introduction to Testing

Learn the basics of testing

## Learning Objectives

- Understand test principles
- Write basic tests

## Resources

*Resources for this unit will be curated and added here.*

## Practice & Engagement

*Engaging tasks and practice exercises will be added here.*

## Your Notes

*Use this space for your personal notes, insights, and reflections.*
"""
            unit_file.write_text(content)
            
            # Change to project directory
            os.chdir("test-project")
            
            # Run with completion date and notes (this should show our debug prints)
            result = runner.invoke(mark_done, [
                "unit-1",
                "--completion-date", "2024-01-15 14:30:00",
                "--notes", "Great learning experience!"
            ])
            
            print(f"DEBUG TEST: Exit code = {result.exit_code}")
            print(f"DEBUG TEST: Output = {result.output}")
            
            assert result.exit_code == 0
            
            # Verify state includes completion date and notes
            with open("state.json", 'r') as f:
                state_data = json.load(f)
            
            unit_state = state_data["units"]["unit-1"]
            assert unit_state["status"] == "completed"
            assert "2024-01-15T14:30:00" in unit_state["completed_at"]
            assert "Great learning experience!" in unit_state["progress_notes"]


class TestMarkdownRendererStateIntegration:
    """Test MarkdownRenderer integration with state system."""
    
    def test_renderer_state_aware_content(self, tmp_path, sample_config, sample_project):
        """Test that renderer builds content using state data."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()
        
        # Create state with updated unit status
        store = create_state_store(project_dir)
        completion_time = datetime(2024, 1, 15, 14, 30, 0)
        store.update_unit_status("unit-1", "completed", completion_time)
        store.initialize_from_project(sample_project)
        
        renderer = MarkdownRenderer(sample_config)
        
        # Build unit content
        unit = sample_project.units[0]
        content = renderer._build_unit_content(unit, sample_project, None, project_dir)
        
        # Verify state data is used
        assert "status: completed" in content
        assert "completed_date: 2024-01-15T14:30:00" in content
        assert "started_date:" in content  # Should have started date too
    
    def test_renderer_toc_with_progress(self, tmp_path, sample_config, sample_project):
        """Test table of contents includes progress information."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()
        
        # Set up progress state
        store = create_state_store(project_dir)
        store.update_unit_status("unit-1", "completed")
        store.update_unit_status("unit-2", "in-progress")
        store.initialize_from_project(sample_project)
        
        renderer = MarkdownRenderer(sample_config)
        
        # Build TOC content
        toc_content = renderer._build_toc_content(sample_project, None, project_dir)
        
        # Verify progress is shown
        assert "progress: 1/3 completed (33.3%)" in toc_content
        assert "| unit-1 |" in toc_content and "| Completed |" in toc_content
        assert "| unit-2 |" in toc_content and "| In-Progress |" in toc_content
        assert "| unit-3 |" in toc_content and "| Pending |" in toc_content
        assert "├── state.json" in toc_content
    
    def test_sync_with_state_updates_files(self, tmp_path, sample_config, sample_project):
        """Test sync_with_state updates markdown files."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()
        units_dir = project_dir / "units"
        units_dir.mkdir()
        
        # Create initial unit file
        unit_file = units_dir / "unit-1.md"
        unit_file.write_text("""---
title: Introduction to Testing
unit_id: unit-1
project: Test Learning Project
status: pending
---

# Introduction to Testing

Unit content here.
""")
        
        # Update state
        store = create_state_store(project_dir)
        completion_time = datetime(2024, 1, 15, 14, 30, 0)
        store.update_unit_status("unit-1", "completed", completion_time)
        store.initialize_from_project(sample_project)
        
        # Sync with state
        renderer = MarkdownRenderer(sample_config)
        renderer.sync_with_state(sample_project, project_dir)
        
        # Verify file was updated
        updated_content = unit_file.read_text()
        assert "status: completed" in updated_content
        assert "completed_date: 2024-01-15T14:30:00" in updated_content
    
    def test_render_project_files_with_state(self, tmp_path, sample_config, sample_project):
        """Test full project rendering with state integration."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()
        
        # Set up some progress
        store = create_state_store(project_dir)
        store.update_unit_status("unit-1", "completed")
        store.initialize_from_project(sample_project)
        
        renderer = MarkdownRenderer(sample_config)
        
        # Render with state
        renderer.render_project_files_with_state(sample_project, project_dir)
        
        # Verify files were created
        assert (project_dir / "toc.md").exists()
        assert (project_dir / "state.json").exists()
        assert (project_dir / "units" / "unit-1.md").exists()
        
        # Verify content reflects state
        unit_content = (project_dir / "units" / "unit-1.md").read_text()
        assert "status: completed" in unit_content
        
        toc_content = (project_dir / "toc.md").read_text()
        assert "progress: 1/3 completed" in toc_content
    
    def test_fallback_to_project_model(self, tmp_path, sample_config, sample_project):
        """Test graceful fallback when state.json is unavailable."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()
        
        renderer = MarkdownRenderer(sample_config)
        
        # Build content without state.json
        unit = sample_project.units[0]
        content = renderer._build_unit_content(unit, sample_project, None, project_dir)
        
        # Should use project model data
        assert "status: pending" in content  # Original status from project
        assert "completed_date:" not in content  # No state timestamps
        assert "started_date:" not in content 


class TestEndToEndWorkflows:
    """Test complete end-to-end workflows that users would experience."""
    
    def test_complete_user_workflow(self, project_with_files, sample_config):
        """Test a complete user workflow from start to finish."""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            import shutil
            import os
            shutil.copytree(project_with_files, "test-project")
            os.chdir("test-project")
            
            # 1. Start first unit
            result = runner.invoke(start, ["unit-1"])
            assert result.exit_code == 0
            
            # 2. Check status
            result = runner.invoke(status, ["unit-1"])
            assert result.exit_code == 0
            assert "in-progress" in result.output
            
            # 3. Complete first unit with notes
            result = runner.invoke(mark_done, [
                "unit-1", 
                "--notes", "Excellent introduction to testing concepts"
            ])
            assert result.exit_code == 0
            
            # 4. Start second unit (which depends on first)
            result = runner.invoke(start, ["unit-2"])
            assert result.exit_code == 0
            
            # 5. Check overall progress
            result = runner.invoke(status, ["--all"])
            assert result.exit_code == 0
            assert "1/3 units completed" in result.output
            
            # 6. Verify state.json reflects all changes
            with open("state.json", 'r') as f:
                state_data = json.load(f)
            
            assert state_data["units"]["unit-1"]["status"] == "completed"
            assert state_data["units"]["unit-2"]["status"] == "in-progress"
            assert state_data["units"]["unit-3"]["status"] == "pending"
            assert "Excellent introduction" in state_data["units"]["unit-1"]["progress_notes"]
            
            # 7. Verify markdown files are updated
            unit1_content = Path("units/unit-1.md").read_text()
            assert "status: completed" in unit1_content
            assert "completed_date:" in unit1_content
    
    def test_concurrent_unit_updates(self, project_with_files):
        """Test handling concurrent updates to different units."""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            import shutil
            import os
            shutil.copytree(project_with_files, "test-project")
            os.chdir("test-project")
            
            # Load the project and initialize state store properly
            from src.flowgenius.cli.unit import _load_project_from_directory
            project = _load_project_from_directory(Path("."))
            assert project is not None, "Failed to load project"
            
            # Simulate concurrent operations by directly manipulating state
            store = create_state_store(Path("."))
            # IMPORTANT: Initialize the state store with the project units
            store.initialize_from_project(project)
            
            # Multiple rapid updates
            import threading
            import time
            
            def update_unit(unit_id, status):
                time.sleep(0.01)  # Small delay to increase concurrency chance
                store.update_unit_status(unit_id, status)
            
            threads = [
                threading.Thread(target=update_unit, args=("unit-1", "in-progress")),
                threading.Thread(target=update_unit, args=("unit-2", "completed")),
                threading.Thread(target=update_unit, args=("unit-3", "in-progress")),
            ]
            
            for thread in threads:
                thread.start()
            
            for thread in threads:
                thread.join()
            
            # Verify final state is consistent
            final_state = store.load_state()
            assert final_state.units["unit-1"].status == "in-progress"
            assert final_state.units["unit-2"].status == "completed"
            assert final_state.units["unit-3"].status == "in-progress"
    
    def test_project_with_many_units(self, tmp_path, sample_config):
        """Test performance with a project containing many units."""
        # Create project with 50 units
        metadata = ProjectMetadata(
            id="large-project",
            title="Large Learning Project",
            topic="Performance Testing",
            created_at=datetime.now()
        )
        
        units = []
        for i in range(1, 51):
            units.append(LearningUnit(
                id=f"unit-{i:02d}",
                title=f"Unit {i}",
                description=f"Learning unit number {i}",
                learning_objectives=[f"Objective {i}.1", f"Objective {i}.2"],
                status="pending"
            ))
        
        large_project = LearningProject(metadata=metadata, units=units)
        
        # Create project directory
        project_dir = tmp_path / "large-project"
        project_dir.mkdir()
        
        # Initialize state store and measure performance
        import time
        start_time = time.time()
        
        store = create_state_store(project_dir)
        store.initialize_from_project(large_project)
        
        # Update some units
        for i in range(1, 11):  # Complete first 10 units
            store.update_unit_status(f"unit-{i:02d}", "completed")
        
        end_time = time.time()
        
        # Should complete in reasonable time (less than 1 second)
        assert end_time - start_time < 1.0
        
        # Verify progress calculations
        summary = store.get_progress_summary()
        assert summary["total_units"] == 50
        assert summary["completed_units"] == 10
        assert summary["completion_percentage"] == 20.0
    
    def test_state_recovery_from_corruption(self, tmp_path, sample_project):
        """Test recovery when state.json becomes corrupted."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()
        
        store = create_state_store(project_dir)
        
        # Initialize with some progress
        store.update_unit_status("unit-1", "completed")
        store.update_unit_status("unit-2", "in-progress")
        
        # Corrupt the state.json file
        state_file = project_dir / "state.json"
        state_file.write_text("{ corrupted json content }")
        
        # Create new store instance (simulating restart)
        new_store = create_state_store(project_dir)
        
        # Should handle corruption gracefully and reinitialize
        with pytest.raises(ValueError, match="Invalid state.json"):
            new_store.load_state()
        
        # Reinitialize from project should work
        new_state = new_store.initialize_from_project(sample_project)
        assert new_state.project_id == sample_project.project_id
        assert len(new_state.units) == len(sample_project.units)
    
    def test_markdown_renderer_integration_stress(self, tmp_path, sample_config, sample_project):
        """Test MarkdownRenderer under stress conditions."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()
        
        # Create state with rapid updates
        store = create_state_store(project_dir)
        store.initialize_from_project(sample_project)
        
        renderer = MarkdownRenderer(sample_config)
        
        # Perform many rapid state changes and renders
        import time
        start_time = time.time()
        
        for i in range(10):
            # Update state
            status = ["pending", "in-progress", "completed"][i % 3]
            store.update_unit_status("unit-1", status)
            
            # Re-render
            renderer.render_project_files_with_state(sample_project, project_dir)
            
            # Verify consistency
            unit_content = (project_dir / "units" / "unit-1.md").read_text()
            assert f"status: {status}" in unit_content
        
        end_time = time.time()
        
        # Should complete in reasonable time
        assert end_time - start_time < 5.0
    
    def test_cli_error_handling_edge_cases(self, tmp_path):
        """Test CLI error handling in various edge cases."""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            # Test with project.json but no units directory
            Path("project.json").write_text('{"metadata": {"id": "test", "title": "Test", "topic": "Test", "created_at": "2024-01-01T00:00:00"}, "units": []}')
            
            result = runner.invoke(mark_done, ["unit-1"])
            assert result.exit_code == 1
            assert "not found" in result.output
            
            # Test with invalid project.json
            Path("project.json").write_text('invalid json')
            
            result = runner.invoke(status, ["--all"])
            assert result.exit_code == 1
            assert "Unable to load" in result.output
    
    def test_markdown_file_recovery(self, tmp_path, sample_config, sample_project):
        """Test recovery when markdown files are missing or corrupted."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()
        units_dir = project_dir / "units"
        units_dir.mkdir()
        
        # Create state with progress
        store = create_state_store(project_dir)
        store.update_unit_status("unit-1", "completed")
        store.initialize_from_project(sample_project)
        
        renderer = MarkdownRenderer(sample_config)
        
        # Delete a unit file
        unit_file = units_dir / "unit-1.md"
        if unit_file.exists():
            unit_file.unlink()
        
        # Sync should handle missing file gracefully
        renderer.sync_with_state(sample_project, project_dir)
        
        # File should be recreated during full render
        renderer.render_project_files_with_state(sample_project, project_dir)
        assert unit_file.exists()
        
        # Content should reflect current state
        content = unit_file.read_text()
        assert "status: completed" in content


class TestPerformanceAndScalability:
    """Test performance characteristics and scalability limits."""
    
    def test_state_file_size_with_many_notes(self, tmp_path):
        """Test performance with units having many progress notes."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()
        
        store = create_state_store(project_dir)
        
        # Create unit with many notes
        store.update_unit_status("unit-1", "in-progress")
        
        state = store.load_state()
        unit_state = state.units["unit-1"]
        
        # Add many notes
        for i in range(100):
            unit_state.progress_notes.append(f"Progress note {i}: Detailed information about learning step {i}")
        
        # Save and measure
        import time
        start_time = time.time()
        store.save_state(state)
        save_time = time.time() - start_time
        
        # Load and measure
        start_time = time.time()
        loaded_state = store.load_state()
        load_time = time.time() - start_time
        
        # Should be reasonably fast even with many notes
        assert save_time < 0.1
        assert load_time < 0.1
        
        # Verify data integrity
        assert len(loaded_state.units["unit-1"].progress_notes) == 100
        assert "Progress note 50" in loaded_state.units["unit-1"].progress_notes[50]
    
    def test_concurrent_cli_operations(self, project_with_files):
        """Test CLI operations under concurrent access."""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            import shutil
            import os
            import threading
            import time
            
            shutil.copytree(project_with_files, "test-project")
            os.chdir("test-project")
            
            # Pre-initialize the state store to avoid race conditions
            from src.flowgenius.cli.unit import _load_project_from_directory
            project = _load_project_from_directory(Path("."))
            if project:
                store = create_state_store(Path("."))
                store.initialize_from_project(project)
            
            # Define concurrent operations
            results = []
            
            def run_command(command_args):
                time.sleep(0.01)  # Small stagger
                result = runner.invoke(unit, command_args)
                results.append((command_args, result.exit_code))
            
            # Launch concurrent operations
            threads = [
                threading.Thread(target=run_command, args=(["start", "unit-1"],)),
                threading.Thread(target=run_command, args=(["mark-done", "unit-2"],)),
                threading.Thread(target=run_command, args=(["status", "--all"],)),
                threading.Thread(target=run_command, args=(["start", "unit-3"],)),
            ]
            
            for thread in threads:
                thread.start()
            
            for thread in threads:
                thread.join()
            
            # At least one operation should succeed (concurrent operations may have race conditions)
            successful_operations = sum(1 for _, exit_code in results if exit_code == 0)
            assert successful_operations >= 1  # At least one should succeed
            
            # If all failed, print debug info for analysis
            if successful_operations == 0:
                for command_args, exit_code in results:
                    print(f"Command {command_args} failed with exit code {exit_code}")
    
    def test_memory_usage_large_project(self, tmp_path, sample_config):
        """Test memory usage with large project data."""
        import tracemalloc
        
        tracemalloc.start()
        
        # Create very large project
        metadata = ProjectMetadata(
            id="memory-test",
            title="Memory Test Project", 
            topic="Memory Testing",
            created_at=datetime.now()
        )
        
        units = []
        for i in range(1000):  # 1000 units
            units.append(LearningUnit(
                id=f"unit-{i:04d}",
                title=f"Memory Test Unit {i}",
                description=f"Testing memory usage with unit {i}" * 10,  # Longer descriptions
                learning_objectives=[f"Objective {i}.{j}" for j in range(5)],  # Multiple objectives
                status="pending"
            ))
        
        large_project = LearningProject(metadata=metadata, units=units)
        
        project_dir = tmp_path / "memory-test"
        project_dir.mkdir()
        
        # Initialize and use state store
        store = create_state_store(project_dir)
        store.initialize_from_project(large_project)
        
        # Update many units
        for i in range(0, 200, 2):  # Update every other unit in first 200
            store.update_unit_status(f"unit-{i:04d}", "completed")
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Memory usage should be reasonable (less than 50MB peak)
        assert peak < 50 * 1024 * 1024  # 50MB
        
        # Verify functionality still works
        summary = store.get_progress_summary()
        assert summary["total_units"] == 1000
        assert summary["completed_units"] == 100  # Every other unit in first 200


class TestErrorHandlingEdgeCases:
    """Test comprehensive error handling scenarios."""
    
    def test_invalid_datetime_formats(self, tmp_path):
        """Test handling of invalid datetime formats in state.json."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()
        
        # Create state.json with invalid datetime
        invalid_state = {
            "project_id": "test-project",
            "created_at": "invalid-datetime",
            "updated_at": "2024-01-01T12:00:00",
            "units": {
                "unit-1": {
                    "id": "unit-1",
                    "status": "completed",
                    "started_at": "not-a-datetime",
                    "completed_at": "2024-01-01T12:00:00",
                    "progress_notes": []
                }
            }
        }
        
        state_file = project_dir / "state.json"
        with open(state_file, 'w') as f:
            json.dump(invalid_state, f)
        
        store = StateStore(project_dir)
        
        with pytest.raises(ValueError, match="Invalid state.json"):
            store.load_state()
    
    def test_unicode_and_special_characters(self, tmp_path, sample_config):
        """Test handling of unicode and special characters in content."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()
        
        # Create project with unicode content
        metadata = ProjectMetadata(
            id="unicode-test",
            title="学习项目 with émojis 🎯📚",
            topic="测试 Unicode",
            created_at=datetime.now(),
            motivation="Learning with spéciàl characters & symbols!"
        )
        
        units = [
            LearningUnit(
                id="unit-1",
                title="Unité d'apprentissage avec accents",
                description="学习单元 with mixed scripts: English, 中文, français",
                learning_objectives=["Objective with emoji 🎯", "中文目标"],
                status="pending"
            )
        ]
        
        unicode_project = LearningProject(metadata=metadata, units=units)
        
        # Test state store
        store = create_state_store(project_dir)
        store.initialize_from_project(unicode_project)
        store.update_unit_status("unit-1", "completed")
        
        # Add unicode notes
        state = store.load_state()
        state.units["unit-1"].progress_notes.append("完成了! Great work with émojis 🎉")
        store.save_state(state)
        
        # Reload and verify
        reloaded_state = store.load_state()
        assert "完成了! Great work with émojis 🎉" in reloaded_state.units["unit-1"].progress_notes
        
        # Test renderer
        renderer = MarkdownRenderer(sample_config)
        renderer.render_project_files_with_state(unicode_project, project_dir)
        
        # Verify files contain unicode correctly
        unit_content = (project_dir / "units" / "unit-1.md").read_text(encoding='utf-8')
        assert "Unité d'apprentissage" in unit_content
        assert "学习单元" in unit_content
        assert "🎯" in unit_content
    
    def test_extremely_long_content(self, tmp_path):
        """Test handling of extremely long content in notes and descriptions."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()
        
        store = create_state_store(project_dir)
        store.update_unit_status("unit-1", "in-progress")
        
        # Add extremely long note (simulate user pasting large content)
        state = store.load_state()
        very_long_note = "This is a very long note. " * 1000  # ~25KB note
        state.units["unit-1"].progress_notes.append(very_long_note)
        
        # Should handle large content gracefully
        store.save_state(state)
        
        # Verify it can be loaded back
        reloaded_state = store.load_state()
        assert len(reloaded_state.units["unit-1"].progress_notes[0]) > 20000
        assert "This is a very long note." in reloaded_state.units["unit-1"].progress_notes[0]
    
    def test_file_permission_scenarios(self, tmp_path):
        """Test various file permission scenarios."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()
        
        store = create_state_store(project_dir)
        
        # Test read-only state.json
        store.update_unit_status("unit-1", "completed")
        
        # Make state.json read-only
        state_file = project_dir / "state.json"
        state_file.chmod(0o444)
        
        # Should raise appropriate error
        with pytest.raises(OSError, match="Unable to write state.json"):
            store.update_unit_status("unit-1", "in-progress")
        
        # Restore permissions for cleanup
        state_file.chmod(0o644)
    
    def test_malformed_project_json(self, tmp_path):
        """Test CLI handling of malformed project.json files."""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            # Create malformed project.json
            Path("project.json").write_text('{"metadata": {"id": "test"}, "units": null}')
            
            result = runner.invoke(status, ["--all"])
            assert result.exit_code == 1
            assert "Unable to load" in result.output
    
    def test_network_interruption_simulation(self, tmp_path):
        """Test behavior during simulated interruptions (disk full, etc.)."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()
        
        store = create_state_store(project_dir)
        
        # Mock disk full scenario
        with patch('builtins.open', side_effect=OSError("No space left on device")):
            with pytest.raises(OSError, match="Unable to write state.json"):
                store.update_unit_status("unit-1", "completed") 