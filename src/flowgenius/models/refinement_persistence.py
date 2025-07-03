"""
FlowGenius Refinement Persistence

This module handles persisting refined learning units back to files,
including project.json updates and markdown file regeneration.
"""

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel, Field

from .project import LearningProject, LearningUnit
from .state_store import StateStore, create_state_store
from .renderer import MarkdownRenderer
from ..agents.unit_refinement_engine import RefinementResult

# Set up module logger
logger = logging.getLogger(__name__)


class RefinementBackup(BaseModel):
    """Information about a refinement backup."""
    backup_id: str = Field(description="Unique backup identifier")
    original_project_path: Path = Field(description="Path to original project.json backup")
    backup_timestamp: datetime = Field(description="When backup was created")
    refinement_summary: str = Field(description="Summary of refinements")
    # Reason provided by the user for triggering the backup (optional).
    backup_reason: Optional[str] = Field(default=None, description="Reason backup was created")


class RefinementHistory(BaseModel):
    """History of refinements for a project."""
    project_id: str = Field(description="Project identifier")
    refinements: List[Dict[str, Any]] = Field(default_factory=list, description="List of refinement records")
    last_backup: Optional[RefinementBackup] = Field(default=None, description="Most recent backup")


class RefinementPersistence:
    """
    Handles saving refined learning units back to project files.
    
    This class manages the persistence of refinement changes, including
    backing up original files, updating project.json, and regenerating
    markdown files.
    """
    
    def __init__(self, project_dir: Path, renderer: Optional[MarkdownRenderer] = None) -> None:
        """
        Initialize refinement persistence.
        
        Args:
            project_dir: Path to the project directory
            renderer: Optional MarkdownRenderer for updating markdown files
        """
        self.project_dir = Path(project_dir)
        self.project_file = self.project_dir / "project.json"
        self.history_file = self.project_dir / ".refinement_history.json"
        self.backups_dir = self.project_dir / ".refinement_backups"
        self.renderer = renderer
        self.state_store = create_state_store(project_dir)
        
        # Ensure directories exist
        self.backups_dir.mkdir(exist_ok=True)
    
    def save_refined_project(self, project: LearningProject, 
                           refinement_results: List[RefinementResult],
                           create_backup: bool = True) -> Dict[str, Any]:
        """
        Save a refined project back to files.
        
        Args:
            project: Refined LearningProject to save
            refinement_results: List of RefinementResult objects
            create_backup: Whether to create a backup before saving
            
        Returns:
            Dictionary with save operation results
        """
        save_results = {
            "project_saved": False,
            "markdown_updated": False,
            "backup_created": False,
            "state_updated": False,
            "errors": [],
            "backup_info": None
        }
        
        try:
            # Create backup if requested
            if create_backup:
                backup_info = self._create_backup(refinement_results)
                save_results["backup_created"] = True
                save_results["backup_info"] = backup_info
            
            # Save project.json
            self._save_project_json(project)
            save_results["project_saved"] = True
            
            # Update markdown files if renderer available
            if self.renderer:
                self._update_markdown_files(project, refinement_results)
                save_results["markdown_updated"] = True
            
            # Update refinement history
            self._update_refinement_history(project, refinement_results)
            
            # Update state tracking
            self._update_refinement_state(refinement_results)
            save_results["state_updated"] = True
            
            # Ensure markdown reflects any status changes tracked in state.json
            if self.renderer:
                try:
                    self.renderer.sync_with_state(project, self.project_dir)
                except (OSError, IOError) as e:
                    # Non-fatal – keep going even if sync fails
                    logger.warning(f"Failed to sync markdown with state: {e}")
            
        except (OSError, IOError) as e:
            save_results["errors"].append(f"Error saving refined project: {str(e)}")
            logger.error(f"Error saving refined project: {e}", exc_info=True)
        
        return save_results
    
    def restore_from_backup(self, backup_id: str) -> Dict[str, Any]:
        """
        Restore project from a specific backup.
        
        Args:
            backup_id: ID of the backup to restore
            
        Returns:
            Dictionary with restore operation results
        """
        restore_results = {
            "restored": False,
            "errors": []
        }
        
        try:
            # Find backup file
            backup_file = self.backups_dir / f"project_{backup_id}.json"
            
            if not backup_file.exists():
                restore_results["errors"].append(f"Backup {backup_id} not found")
                return restore_results
            
            # Restore project.json
            shutil.copy2(backup_file, self.project_file)
            restore_results["restored"] = True
            
        except (OSError, IOError, shutil.Error) as e:
            restore_results["errors"].append(f"Error restoring backup: {str(e)}")
            logger.error(f"Error restoring backup: {e}", exc_info=True)
        
        return restore_results
    
    def get_refinement_history(self) -> RefinementHistory:
        """Get the refinement history for the project."""
        if not self.history_file.exists():
            # Create default history
            project_id = self.project_dir.name
            return RefinementHistory(project_id=project_id)
        
        try:
            with open(self.history_file, 'r') as f:
                history_data = json.load(f)
            
            # Convert datetime strings back to datetime objects
            if 'last_backup' in history_data and history_data['last_backup']:
                backup_data = history_data['last_backup']
                if 'backup_timestamp' in backup_data:
                    backup_data['backup_timestamp'] = datetime.fromisoformat(backup_data['backup_timestamp'])
                if 'original_project_path' in backup_data:
                    backup_data['original_project_path'] = Path(backup_data['original_project_path'])
            
            return RefinementHistory(**history_data)
            
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            # Return default history if file is corrupted
            logger.warning(f"Failed to load refinement history: {e}")
            project_id = self.project_dir.name
            return RefinementHistory(project_id=project_id)
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """List all available backups."""
        backups = []
        
        if not self.backups_dir.exists():
            return backups
        
        for backup_file in self.backups_dir.glob("project_*.json"):
            backup_id = backup_file.stem.replace("project_", "")
            backup_info = {
                "backup_id": backup_id,
                "file_path": backup_file,
                "created": datetime.fromtimestamp(backup_file.stat().st_mtime),
                "size": backup_file.stat().st_size
            }
            backups.append(backup_info)
        
        # Sort by creation time (newest first)
        backups.sort(key=lambda b: b["created"], reverse=True)
        
        return backups
    
    def _create_backup(self, refinement_results: List[RefinementResult]) -> RefinementBackup:
        """Create a backup of the current project."""
        timestamp = datetime.now()
        backup_id = timestamp.strftime("%Y%m%d_%H%M%S")
        backup_file = self.backups_dir / f"project_{backup_id}.json"
        
        # Copy current project.json to backup
        if self.project_file.exists():
            shutil.copy2(self.project_file, backup_file)
        
        # Create backup info
        refinement_summary = self._create_refinement_summary(refinement_results)
        
        return RefinementBackup(
            backup_id=backup_id,
            original_project_path=backup_file,
            backup_timestamp=timestamp,
            refinement_summary=refinement_summary
        )
    
    def _save_project_json(self, project: LearningProject) -> None:
        """Save the project to project.json file."""
        # Update the project's timestamp
        project.update_timestamp()
        
        # Convert to dictionary for JSON serialization
        project_dict = project.model_dump()
        
        # Convert datetime objects to ISO format strings
        if 'metadata' in project_dict:
            metadata = project_dict['metadata']
            if 'created_at' in metadata:
                metadata['created_at'] = project.metadata.created_at.isoformat()
            if 'updated_at' in metadata:
                metadata['updated_at'] = project.metadata.updated_at.isoformat()
        
        # Write to file
        with open(self.project_file, 'w') as f:
            json.dump(project_dict, f, indent=2)
    
    def _update_markdown_files(self, project: LearningProject, refinement_results: List[RefinementResult]) -> None:
        """Update markdown files for refined units."""
        if not self.renderer:
            return
        
        # Get units that were modified
        modified_units = set()
        for result in refinement_results:
            if result.success and result.modified_components:
                modified_units.add(result.unit_id)
        
        # Regenerate markdown files for modified units
        units_dir = self.project_dir / "units"
        if units_dir.exists():
            for unit_id in modified_units:
                unit_file = units_dir / f"{unit_id}.md"
                if unit_file.exists():
                    # Find the unit in the project
                    unit = project.get_unit_by_id(unit_id)
                    if unit:
                        # Regenerate the unit markdown file
                        self.renderer.render_unit_file(unit, unit_file)
    
    def _update_refinement_history(self, project: LearningProject, refinement_results: List[RefinementResult]) -> None:
        """Update the refinement history."""
        history = self.get_refinement_history()
        
        # Create refinement record
        refinement_record = {
            "timestamp": datetime.now().isoformat(),
            "project_id": project.project_id,
            "results": [
                {
                    "unit_id": result.unit_id,
                    "actions_applied": result.actions_applied,
                    "modified_components": result.modified_components,
                    "success": result.success,
                    "summary": result.summary
                }
                for result in refinement_results
            ],
            "total_units_refined": len([r for r in refinement_results if r.success]),
            "total_actions_applied": sum(len(r.actions_applied) for r in refinement_results)
        }
        
        # Add to history
        history.refinements.append(refinement_record)
        
        # Keep only last 50 refinements to avoid file bloat
        if len(history.refinements) > 50:
            history.refinements = history.refinements[-50:]
        
        # Save history
        history_dict = history.model_dump()
        
        # Convert datetime/Path objects for JSON serialization
        if history_dict.get('last_backup'):
            backup_data = history_dict['last_backup']
            if 'backup_timestamp' in backup_data:
                backup_data['backup_timestamp'] = history.last_backup.backup_timestamp.isoformat()
            if 'original_project_path' in backup_data:
                backup_data['original_project_path'] = str(history.last_backup.original_project_path)
        
        with open(self.history_file, 'w') as f:
            json.dump(history_dict, f, indent=2)
    
    def _update_refinement_state(self, refinement_results: List[RefinementResult]) -> None:
        """Update state tracking for refinement activity."""
        try:
            state = self.state_store.load_state()
            
            # Add refinement tracking to state (extend StateStore if needed)
            refinement_timestamp = datetime.now()
            
            for result in refinement_results:
                if result.success:
                    # Get unit state
                    unit_state = state.get_unit_state(result.unit_id)
                    if unit_state:
                        # Add a progress note about refinement
                        refinement_note = f"Unit refined: {result.summary}"
                        unit_state.progress_notes.append(refinement_note)
            
            # Update overall state timestamp
            state.updated_at = refinement_timestamp
            
            # Save updated state
            self.state_store.save_state(state)
            
        except (OSError, IOError, ValueError) as e:
            # Don't fail the entire operation if state update fails
            logger.warning(f"Failed to update refinement state: {e}")
    
    def _create_refinement_summary(self, refinement_results: List[RefinementResult]) -> str:
        """Create a summary of refinement results."""
        if not refinement_results:
            return "No refinements applied"
        
        successful_results = [r for r in refinement_results if r.success]
        total_actions = sum(len(r.actions_applied) for r in successful_results)
        
        summary_parts = [
            f"Refined {len(successful_results)} units",
            f"Applied {total_actions} refinement actions"
        ]
        
        if len(refinement_results) > len(successful_results):
            failed_count = len(refinement_results) - len(successful_results)
            summary_parts.append(f"{failed_count} units had errors")
        
        return "; ".join(summary_parts)

    # ---------------------------------------------------------------------
    # Public helpers
    # ---------------------------------------------------------------------

    def create_backup(self, backup_reason: str, refinement_results: Optional[List[RefinementResult]] = None) -> RefinementBackup:  # noqa: D401
        """Create a backup of the current project in a public-facing API.

        This wrapper exists primarily for unit-test convenience. It delegates to
        the internal ``_create_backup`` method while attaching the *reason* to
        the returned ``RefinementBackup`` instance so callers can inspect it.

        Args:
            backup_reason: Short description for why the backup is being taken.
            refinement_results: Optional list of refinement results to include
                in the backup summary.  Defaults to an empty list, allowing the
                method to be used outside the refinement flow (e.g. manual
                backups).

        Returns:
            RefinementBackup enriched with the supplied ``backup_reason``.
        """
        if refinement_results is None:
            refinement_results = []

        backup = self._create_backup(refinement_results)
        # Attach the user-supplied reason. Using ``model_copy`` keeps the model
        # immutable by default while returning an updated instance.
        backup_dict = backup.model_dump()
        backup_dict["backup_reason"] = backup_reason
        return RefinementBackup(**backup_dict)


def create_refinement_persistence(project_dir: Path, renderer: Optional[MarkdownRenderer] = None) -> RefinementPersistence:
    """
    Factory function to create a RefinementPersistence instance.
    
    Args:
        project_dir: Path to the project directory
        renderer: Optional MarkdownRenderer for markdown updates
        
    Returns:
        Configured RefinementPersistence instance
    """
    return RefinementPersistence(project_dir, renderer) 