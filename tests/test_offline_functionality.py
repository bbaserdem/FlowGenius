"""
Test Offline Functionality

This module tests that FlowGenius operates correctly without internet connectivity,
except for OpenAI API calls which are expected to fail gracefully in offline mode.
"""

import os
import json
import pytest
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock
import socket
from datetime import datetime

from flowgenius.models import (
    FlowGeniusConfig, ConfigManager, LearningProject, LearningUnit,
    ProjectMetadata, StateStore, MarkdownRenderer
)
from flowgenius.models.project_generator import ProjectGenerator
from flowgenius.models.refinement_persistence import RefinementPersistence
from flowgenius.utils import safe_save_json, safe_load_json, ensure_project_structure, get_datetime_now


class TestOfflineFunctionality:
    """Test suite for offline functionality verification."""
    
    @pytest.fixture
    def mock_config(self, tmp_path):
        """Create a test configuration with local paths."""
        key_file = tmp_path / "test_api_key"
        key_file.write_text("sk-test-key-for-offline-testing")
        key_file.chmod(0o600)
        
        projects_root = tmp_path / "projects"
        projects_root.mkdir(exist_ok=True)
        
        return FlowGeniusConfig(
            openai_key_path=key_file,
            projects_root=projects_root,
            default_model="gpt-4o-mini",
            link_style="markdown"
        )
    
    @pytest.fixture
    def sample_project(self):
        """Create a sample learning project for testing."""
        metadata = ProjectMetadata(
            id="test-project-001",
            title="Test Project",
            topic="Test Learning Topic",
            motivation="Testing offline functionality",
            created_at=get_datetime_now(),
            updated_at=get_datetime_now(),
            difficulty_level="beginner",
            estimated_total_time="3 hours"
        )
        
        return LearningProject(
            metadata=metadata,
            units=[
                LearningUnit(
                    id="unit-1",
                    title="Test Unit 1",
                    description="First test unit",
                    learning_objectives=["Objective 1", "Objective 2"]
                ),
                LearningUnit(
                    id="unit-2", 
                    title="Test Unit 2",
                    description="Second test unit",
                    learning_objectives=["Objective 3", "Objective 4"]
                )
            ]
        )
    
    def test_config_manager_offline(self, mock_config, tmp_path):
        """Test ConfigManager works without network access."""
        # Simulate offline by mocking socket operations
        with patch('socket.socket') as mock_socket:
            mock_socket.side_effect = socket.error("Network is unreachable")
            
            # Save and load configuration
            config_path = tmp_path / ".config" / "flowgenius" / "config.yaml"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            manager = ConfigManager()
            
            # These operations should work offline
            assert manager.save_config(mock_config) is True
            loaded_config = manager.load_config()
            
            assert loaded_config is not None
            assert str(loaded_config.openai_key_path) == str(mock_config.openai_key_path)
            assert str(loaded_config.projects_root) == str(mock_config.projects_root)
    
    def test_local_file_operations(self, tmp_path):
        """Test all file operations work offline."""
        # Test JSON save/load
        test_data = {"key": "value", "nested": {"data": [1, 2, 3]}}
        json_path = tmp_path / "test.json"
        
        assert safe_save_json(test_data, json_path) is True
        loaded_data = safe_load_json(json_path)
        assert loaded_data == test_data
        
        # Test project structure creation
        project_dir = tmp_path / "test_project"
        ensure_project_structure(project_dir)
        
        # Verify all directories were created
        assert project_dir.exists()
        assert (project_dir / "units").exists()
        assert (project_dir / "resources").exists()
        assert (project_dir / "notes").exists()
    
    def test_state_store_offline(self, tmp_path, sample_project):
        """Test StateStore operations work offline."""
        project_dir = tmp_path / sample_project.project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        
        # Create and use state store
        state_store = StateStore(project_dir)
        
        # Load initial state (should create default)
        state = state_store.load_state()
        assert state.project_id == project_dir.name
        
        # Update unit status
        state_store.update_unit_status("unit-1", "in-progress")
        state_store.update_unit_status("unit-1", "completed")
        
        # Verify persistence
        new_store = StateStore(project_dir)
        loaded_state = new_store.load_state()
        assert loaded_state.units["unit-1"].status == "completed"
    
    def test_markdown_renderer_offline(self, mock_config, tmp_path, sample_project):
        """Test MarkdownRenderer works offline."""
        project_dir = tmp_path / sample_project.project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        
        renderer = MarkdownRenderer(mock_config)
        
        # Generate all markdown files
        renderer.render_project_files(sample_project, project_dir)
        
        # Verify files were created
        assert (project_dir / "toc.md").exists()
        assert (project_dir / "README.md").exists()
        assert (project_dir / "units" / "unit-1.md").exists()
        assert (project_dir / "units" / "unit-2.md").exists()
        
        # Verify content
        toc_content = (project_dir / "toc.md").read_text()
        assert "Test Project" in toc_content
        assert "Test Unit 1" in toc_content
    
    def test_refinement_persistence_offline(self, tmp_path, sample_project):
        """Test refinement persistence works offline."""
        project_dir = tmp_path / sample_project.project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        
        # Save initial project
        project_file = project_dir / "project.json"
        safe_save_json(sample_project.model_dump(), project_file)
        
        # Create refinement persistence
        persistence = RefinementPersistence(project_dir)
        
        # Test backup creation
        from flowgenius.agents.unit_refinement_engine import RefinementResult
        refinement_results = [
            RefinementResult(
                unit_id="unit-1",
                success=True,
                changes_made=["Updated objectives"],
                summary="Refined unit 1"
            )
        ]
        
        # Save refined project
        save_results = persistence.save_refined_project(
            sample_project,
            refinement_results,
            create_backup=True
        )
        
        assert save_results["project_saved"] is True
        assert save_results["backup_created"] is True
        
        # Verify backup exists
        backups = persistence.list_backups()
        assert len(backups) > 0
    
    def test_project_listing_offline(self, mock_config, tmp_path, sample_project):
        """Test project listing works offline."""
        # Create multiple project directories
        for i in range(3):
            project_dir = mock_config.projects_root / f"test-project-{i:03d}"
            project_dir.mkdir(parents=True, exist_ok=True)
            
            # Add project.json
            project_data = sample_project.model_dump()
            project_data["metadata"]["id"] = f"test-project-{i:03d}"
            project_data["metadata"]["title"] = f"Test Project {i}"
            
            # Convert datetime to ISO format for JSON
            project_data["metadata"]["created_at"] = sample_project.metadata.created_at.isoformat()
            project_data["metadata"]["updated_at"] = sample_project.metadata.updated_at.isoformat()
            
            safe_save_json(project_data, project_dir / "project.json")
        
        # List projects (this should work offline)
        projects = []
        for project_dir in mock_config.projects_root.iterdir():
            if project_dir.is_dir() and (project_dir / "project.json").exists():
                projects.append(project_dir.name)
        
        assert len(projects) == 3
        assert "test-project-000" in projects
    
    @patch('flowgenius.models.project_generator.OpenAI')
    def test_openai_calls_fail_gracefully_offline(self, mock_openai_class, mock_config):
        """Test that OpenAI API calls fail gracefully when offline."""
        # Configure mock to simulate network error
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("Network error: Unable to connect")
        mock_openai_class.return_value = mock_client
        
        # Try to use project generator (which needs OpenAI)
        generator = ProjectGenerator(mock_config)
        
        # Mock the scaffolder to raise network error
        mock_scaffolder = Mock()
        mock_scaffolder.scaffold_topic.side_effect = Exception("Network error: Unable to connect")
        generator._scaffolder = mock_scaffolder
        
        # This should raise an error since it requires network
        with pytest.raises(Exception) as exc_info:
            generator.create_project("Test Topic")
        
        assert "Network error" in str(exc_info.value)
    
    def test_api_key_loading_offline(self, mock_config):
        """Test API key loading from file works offline."""
        # Write test key
        test_key = "sk-test-offline-key-12345"
        mock_config.openai_key_path.write_text(test_key)
        mock_config.openai_key_path.chmod(0o600)
        
        # Load key
        loaded_key = mock_config.openai_key_path.read_text().strip()
        assert loaded_key == test_key
        
        # Verify permissions
        stats = mock_config.openai_key_path.stat()
        assert oct(stats.st_mode)[-3:] == "600"
    
    def test_home_manager_config_generation(self, tmp_path):
        """Test that home-manager config files work offline."""
        # Simulate home-manager config generation
        config_data = {
            "openai_key_path": str(tmp_path / ".secrets" / "openai_key"),
            "projects_root": str(tmp_path / "Learning"),
            "link_style": "obsidian",
            "default_model": "gpt-4o-mini"
        }
        
        config_file = tmp_path / ".config" / "flowgenius" / "config.yaml"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Use ruamel.yaml to maintain formatting
        from ruamel.yaml import YAML
        yaml = YAML()
        yaml.preserve_quotes = True
        yaml.width = 120
        
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        # Verify file was created
        assert config_file.exists()
        
        # Load and verify
        with open(config_file, 'r') as f:
            loaded = yaml.load(f)
        
        assert loaded["openai_key_path"] == config_data["openai_key_path"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 