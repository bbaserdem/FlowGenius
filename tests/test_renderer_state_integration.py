"""
Test suite for MarkdownRenderer state integration functionality.

Tests that the MarkdownRenderer properly integrates with state.json
to reflect current unit progress in rendered markdown files.
"""

import json
import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

from src.flowgenius.models.renderer import MarkdownRenderer
from src.flowgenius.models.config import FlowGeniusConfig
from src.flowgenius.models.project import LearningProject, LearningUnit, ProjectMetadata
from src.flowgenius.models.state_store import StateStore, UnitState, ProjectState


@pytest.fixture
def sample_config(tmp_path):
    """Create a sample configuration for testing."""
    with patch('pathlib.Path.exists', return_value=True):
        return FlowGeniusConfig(
            openai_key_path=tmp_path / "openai_key",
            projects_root=tmp_path / "projects",
            link_style="markdown"
        )


@pytest.fixture
def sample_project():
    """Create a sample learning project for testing."""
    metadata = ProjectMetadata(
        id="test-project",
        title="Test Project",
        topic="Test Topic",
        created_at=datetime.now(),
        motivation="Test motivation"
    )
    
    units = [
        LearningUnit(
            id="unit-1",
            title="First Unit",
            description="First unit description",
            learning_objectives=["Learn basics"],
            status="pending"
        ),
        LearningUnit(
            id="unit-2", 
            title="Second Unit",
            description="Second unit description",
            learning_objectives=["Learn advanced topics"],
            status="pending"
        )
    ]
    
    return LearningProject(
        metadata=metadata,
        units=units
    )


def test_renderer_state_awareness(tmp_path, sample_config, sample_project):
    """Test that MarkdownRenderer uses state.json data for unit status."""
    # Create a project directory with state.json
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()
    
    # Create state.json with updated unit status
    state_data = {
        "project_id": "test-project",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "units": {
            "unit-1": {
                "id": "unit-1",
                "status": "completed",
                "started_at": "2024-01-01T10:00:00",
                "completed_at": "2024-01-02T15:30:00",
                "progress_notes": ["Great learning experience!"]
            },
            "unit-2": {
                "id": "unit-2", 
                "status": "in-progress",
                "started_at": "2024-01-03T09:00:00",
                "completed_at": None,
                "progress_notes": ["Making good progress"]
            }
        }
    }
    
    state_file = project_dir / "state.json"
    with open(state_file, 'w') as f:
        json.dump(state_data, f, indent=2)
    
    # Initialize renderer
    renderer = MarkdownRenderer(sample_config)
    
    # Test state-aware unit content building
    unit1 = sample_project.units[0]  # Originally "pending"
    content = renderer._build_unit_content(unit1, sample_project, None, project_dir)
    
    # Verify that content uses state data instead of project model
    assert "status: completed" in content
    assert "started_date: 2024-01-01T10:00:00" in content
    assert "completed_date: 2024-01-02T15:30:00" in content
    assert "Great learning experience!" in content
    assert "## Progress Notes" in content


def test_renderer_toc_state_integration(tmp_path, sample_config, sample_project):
    """Test that table of contents reflects state.json progress."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()
    
    # Create state.json with progress
    state_data = {
        "project_id": "test-project",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "units": {
            "unit-1": {
                "id": "unit-1",
                "status": "completed",
                "started_at": None,
                "completed_at": "2024-01-02T15:30:00",
                "progress_notes": []
            },
            "unit-2": {
                "id": "unit-2",
                "status": "pending", 
                "started_at": None,
                "completed_at": None,
                "progress_notes": []
            }
        }
    }
    
    state_file = project_dir / "state.json"
    with open(state_file, 'w') as f:
        json.dump(state_data, f, indent=2)
    
    # Initialize renderer
    renderer = MarkdownRenderer(sample_config)
    
    # Build TOC content with state integration
    toc_content = renderer._build_toc_content(sample_project, None, project_dir)
    
    # Verify state integration in TOC
    assert "progress: 1/2 completed (50.0%)" in toc_content
    assert "| unit-1 |" in toc_content and "| Completed |" in toc_content
    assert "| unit-2 |" in toc_content and "| Pending |" in toc_content
    assert "├── state.json          # Progress tracking state" in toc_content


def test_sync_with_state_functionality(tmp_path, sample_config, sample_project):
    """Test the sync_with_state method updates markdown files."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()
    units_dir = project_dir / "units"
    units_dir.mkdir()
    
    # Create initial unit markdown files
    unit1_file = units_dir / "unit-1.md"
    unit1_file.write_text("""---
title: First Unit
unit_id: unit-1
project: Test Project
status: pending
---

# First Unit

Content here.
""")
    
    # Create state.json with updated status
    state_data = {
        "project_id": "test-project",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "units": {
            "unit-1": {
                "id": "unit-1",
                "status": "completed",
                "started_at": None,
                "completed_at": "2024-01-02T15:30:00",
                "progress_notes": []
            }
        }
    }
    
    state_file = project_dir / "state.json"
    with open(state_file, 'w') as f:
        json.dump(state_data, f, indent=2)
    
    # Initialize renderer and sync
    renderer = MarkdownRenderer(sample_config)
    renderer.sync_with_state(sample_project, project_dir)
    
    # Verify the markdown file was updated
    updated_content = unit1_file.read_text()
    assert "status: completed" in updated_content
    assert "completed_date: 2024-01-02T15:30:00" in updated_content


def test_render_project_files_with_state(tmp_path, sample_config, sample_project):
    """Test the render_project_files_with_state method."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()
    
    # Create state.json with test data BEFORE rendering
    state_data = {
        "project_id": "test-project",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "units": {
            "unit-1": {
                "id": "unit-1",
                "status": "completed",
                "started_at": None,
                "completed_at": "2024-01-02T15:30:00",
                "progress_notes": ["Completed successfully"]
            }
        }
    }
    
    state_file = project_dir / "state.json"
    with open(state_file, 'w') as f:
        json.dump(state_data, f, indent=2)
    
    # Initialize renderer
    renderer = MarkdownRenderer(sample_config)
    
    # Render project files with state
    renderer.render_project_files_with_state(sample_project, project_dir)
    
    # Verify files were created with state data
    assert (project_dir / "toc.md").exists()
    assert (project_dir / "units" / "unit-1.md").exists()
    assert (project_dir / "state.json").exists()
    
    # Check that unit file contains state data
    unit_content = (project_dir / "units" / "unit-1.md").read_text()
    assert "status: completed" in unit_content
    assert "completed_date: 2024-01-02T15:30:00" in unit_content
    assert "Completed successfully" in unit_content


def test_fallback_to_project_model_when_no_state(tmp_path, sample_config, sample_project):
    """Test that renderer falls back to project model when state.json doesn't exist."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()
    
    # Initialize renderer (no state.json file)
    renderer = MarkdownRenderer(sample_config)
    
    # Build unit content without state
    unit1 = sample_project.units[0]
    content = renderer._build_unit_content(unit1, sample_project, None, project_dir)
    
    # Should use project model data
    assert "status: pending" in content  # Original status from project model
    assert "started_date:" not in content  # No state timestamps
    assert "completed_date:" not in content 