"""
FlowGenius State Store

This module provides functionality to manage learning progress state in project directories
via state.json files. It tracks unit completion status, progress timestamps, and integrates
with the existing project models.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Literal, Any
from pydantic import BaseModel, Field

from .project import LearningProject, LearningUnit


class UnitState(BaseModel):
    """
    State information for a single learning unit.
    """
    id: str = Field(description="Unit identifier")
    status: Literal["pending", "in-progress", "completed"] = Field(default="pending")
    started_at: Optional[datetime] = Field(default=None, description="When the unit was started")
    completed_at: Optional[datetime] = Field(default=None, description="When the unit was completed")
    progress_notes: List[str] = Field(default_factory=list, description="Optional progress notes")
    

class ProjectState(BaseModel):
    """
    Complete state information for a learning project.
    """
    project_id: str = Field(description="Project identifier")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    units: Dict[str, UnitState] = Field(default_factory=dict, description="Unit states by unit ID")
    
    def get_unit_state(self, unit_id: str) -> Optional[UnitState]:
        """Get state for a specific unit."""
        return self.units.get(unit_id)
    
    def update_unit_status(
        self, 
        unit_id: str, 
        status: Literal["pending", "in-progress", "completed"],
        completion_date: Optional[datetime] = None
    ) -> None:
        """Update the status of a specific unit."""
        if unit_id not in self.units:
            self.units[unit_id] = UnitState(id=unit_id)
        
        unit_state = self.units[unit_id]
        old_status = unit_state.status
        unit_state.status = status
        
        # Update timestamps based on status changes
        if old_status == "pending" and status == "in-progress":
            unit_state.started_at = datetime.now()
        elif status == "completed":
            unit_state.completed_at = completion_date or datetime.now()
            if unit_state.started_at is None:
                unit_state.started_at = unit_state.completed_at
        
        self.updated_at = datetime.now()
    
    def get_progress_summary(self) -> Dict[str, Any]:
        """Get a summary of progress across all units."""
        total_units = len(self.units)
        completed_units = sum(1 for unit in self.units.values() if unit.status == "completed")
        in_progress_units = sum(1 for unit in self.units.values() if unit.status == "in-progress")
        
        return {
            "total_units": total_units,
            "completed_units": completed_units,
            "in_progress_units": in_progress_units,
            "pending_units": total_units - completed_units - in_progress_units,
            "completion_percentage": (completed_units / total_units * 100) if total_units > 0 else 0
        }


class StateStore:
    """
    Manages learning progress state in project directories via state.json files.
    
    This class provides functionality to track unit completion status, maintain
    progress timestamps, and integrate with existing project models and markdown files.
    """
    
    def __init__(self, project_dir: Path) -> None:
        """
        Initialize a StateStore for a specific project directory.
        
        Args:
            project_dir: Path to the project directory containing state.json
        """
        self.project_dir = Path(project_dir)
        self.state_file = self.project_dir / "state.json"
        self._current_state: Optional[ProjectState] = None
    
    def load_state(self) -> ProjectState:
        """
        Load project state from state.json file.
        
        Returns:
            ProjectState object, either loaded from file or newly created
            
        Raises:
            ValueError: If state.json exists but contains invalid data
        """
        if not self.state_file.exists():
            # Create default state if file doesn't exist
            return self._create_default_state()
        
        try:
            with open(self.state_file, 'r') as f:
                state_data = json.load(f)
            
            # Convert datetime strings back to datetime objects
            if 'created_at' in state_data:
                state_data['created_at'] = datetime.fromisoformat(state_data['created_at'])
            if 'updated_at' in state_data:
                state_data['updated_at'] = datetime.fromisoformat(state_data['updated_at'])
            
            for unit_id, unit_data in state_data.get('units', {}).items():
                if 'started_at' in unit_data and unit_data['started_at']:
                    unit_data['started_at'] = datetime.fromisoformat(unit_data['started_at'])
                if 'completed_at' in unit_data and unit_data['completed_at']:
                    unit_data['completed_at'] = datetime.fromisoformat(unit_data['completed_at'])
            
            self._current_state = ProjectState(**state_data)
            return self._current_state
            
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            raise ValueError(f"Invalid state.json file in {self.project_dir}: {e}")
    
    def save_state(self, state: Optional[ProjectState] = None) -> None:
        """
        Save project state to state.json file.
        
        Args:
            state: ProjectState to save, or None to save current state
            
        Raises:
            OSError: If unable to write to state.json file
        """
        if state is None:
            state = self._current_state or self.load_state()
        
        # Ensure project directory exists
        self.project_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Convert to dict with datetime serialization
            state_dict = state.model_dump()
            
            # Convert datetime objects to ISO format strings
            if state_dict.get('created_at'):
                state_dict['created_at'] = state.created_at.isoformat()
            if state_dict.get('updated_at'):
                state_dict['updated_at'] = state.updated_at.isoformat()
            
            for unit_id, unit_data in state_dict.get('units', {}).items():
                if unit_data.get('started_at'):
                    unit_data['started_at'] = state.units[unit_id].started_at.isoformat()
                if unit_data.get('completed_at'):
                    unit_data['completed_at'] = state.units[unit_id].completed_at.isoformat()
            
            with open(self.state_file, 'w') as f:
                json.dump(state_dict, f, indent=2)
            
            self._current_state = state
            
        except OSError as e:
            raise OSError(f"Unable to write state.json to {self.project_dir}: {e}")
    
    def update_unit_status(
        self,
        unit_id: str,
        status: Literal["pending", "in-progress", "completed"],
        completion_date: Optional[datetime] = None
    ) -> None:
        """
        Update the status of a specific unit and save to file.
        
        Args:
            unit_id: ID of the unit to update
            status: New status for the unit
            completion_date: Optional completion timestamp
        """
        state = self.load_state()
        state.update_unit_status(unit_id, status, completion_date)
        self.save_state(state)
    
    def get_unit_status(self, unit_id: str) -> Optional[str]:
        """
        Get the current status of a specific unit.
        
        Args:
            unit_id: ID of the unit to check
            
        Returns:
            Current status of the unit, or None if unit not found
        """
        state = self.load_state()
        unit_state = state.get_unit_state(unit_id)
        return unit_state.status if unit_state else None
    
    def initialize_from_project(self, project: LearningProject) -> ProjectState:
        """
        Initialize state.json from a LearningProject, preserving existing progress.
        
        Args:
            project: LearningProject to initialize state from
            
        Returns:
            The initialized ProjectState
        """
        # Load existing state or create new one
        if self.state_file.exists():
            try:
                state = self.load_state()
            except ValueError:
                # If existing state is invalid, create new one
                state = self._create_default_state(project.project_id)
        else:
            state = self._create_default_state(project.project_id)
        
        # Add any new units from the project that aren't in state
        for unit in project.units:
            if unit.id not in state.units:
                state.units[unit.id] = UnitState(
                    id=unit.id,
                    status=unit.status  # Use status from project model
                )
        
        # Save the initialized state
        self.save_state(state)
        return state
    
    def get_progress_summary(self) -> Dict[str, Any]:
        """
        Get a summary of progress across all units.
        
        Returns:
            Dictionary with progress statistics
        """
        state = self.load_state()
        return state.get_progress_summary()
    
    def _create_default_state(self, project_id: Optional[str] = None) -> ProjectState:
        """
        Create a default ProjectState.
        
        Args:
            project_id: Optional project ID, defaults to directory name
            
        Returns:
            New ProjectState with default values
        """
        if project_id is None:
            project_id = self.project_dir.name
        
        return ProjectState(project_id=project_id)


def create_state_store(project_dir: Path) -> StateStore:
    """
    Factory function to create a StateStore for a project directory.
    
    Args:
        project_dir: Path to the project directory
        
    Returns:
        Configured StateStore instance
    """
    return StateStore(project_dir) 