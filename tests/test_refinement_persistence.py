"""
Tests for the Refinement Persistence component.
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch
from typing import Any

from flowgenius.models.refinement_persistence import (
    RefinementPersistence,
    RefinementBackup,
    RefinementHistory
)
from flowgenius.agents.unit_refinement_engine import RefinementResult


class TestRefinementPersistence:
    """Test cases for RefinementPersistence."""

    def test_init(self) -> None:
        """Test refinement persistence initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            persistence = RefinementPersistence(project_dir)
            
            assert persistence.project_dir == project_dir
            assert persistence.backups_dir == project_dir / ".refinement_backups"

    def test_create_backup(self, sample_learning_unit: Any) -> None:
        """Test creating a backup of project files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            
            # Create a mock project.json file
            project_file = project_dir / "project.json"
            project_data = {
                "project_name": "Test Project",
                "units": [sample_learning_unit.model_dump()]
            }
            project_file.write_text(json.dumps(project_data, indent=2))
            
            persistence = RefinementPersistence(project_dir)
            
            with patch('uuid.uuid4') as mock_uuid:
                mock_uuid.return_value.hex = "12345678"
                
                backup = persistence.create_backup("User refinement")
                
                assert backup is not None
                assert backup.backup_reason == "User refinement"
