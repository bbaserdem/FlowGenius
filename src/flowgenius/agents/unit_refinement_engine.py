"""
FlowGenius Unit Refinement Engine

This module contains the core AI agent for iterative unit refinement
based on user feedback and content generation.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from openai import OpenAI
from pydantic import BaseModel, Field

from ..models.project import LearningUnit, LearningResource, EngageTask
from ..models.settings import DefaultSettings
from .content_generator import ContentGeneratorAgent, ContentGenerationRequest
from .resource_curator import ResourceCuratorAgent, ResourceRequest
from .engage_task_generator import EngageTaskGeneratorAgent, TaskGenerationRequest

# Set up module logger
logger = logging.getLogger(__name__)


class RefinementResult(BaseModel):
    """Result of unit refinement process."""
    unit_id: str = Field(description="ID of the unit that was refined")
    refined_unit: Optional[LearningUnit] = Field(default=None, description="The refined learning unit")
    changes_made: List[str] = Field(default_factory=list, description="List of changes applied")
    reasoning: str = Field(default="", description="Explanation of refinement decisions")
    success: bool = Field(description="Whether refinement was successful")
    updated_components: List[str] = Field(default_factory=list, description="Components of the unit that were updated")
    agent_responses: Dict[str, Any] = Field(default_factory=dict, description="Raw responses from sub-agents")
    errors: List[str] = Field(default_factory=list, description="Errors encountered during refinement")

    @property
    def applied_actions(self) -> List[str]:
        """Get applied actions (alias for changes_made for backward compatibility)."""
        return self.changes_made

    @property
    def summary(self) -> str:
        """Get summary (alias for reasoning for backward compatibility)."""
        return self.reasoning


class UnitRefinementEngine:
    """
    Core engine for iterative unit refinement based on user feedback.
    
    This agent processes user feedback and refines learning units to better
    meet learner needs and objectives.
    """
    
    def __init__(self, openai_client: OpenAI, model: str = DefaultSettings.DEFAULT_MODEL) -> None:
        """
        Initialize the refinement engine with OpenAI client.
        
        Args:
            openai_client: Configured OpenAI client
            model: OpenAI model to use for refinement
        """
        self.client = openai_client
        self.model = model
        self.refinement_history: List[Dict[str, Any]] = []
        
        self.content_generator = ContentGeneratorAgent(self.client, self.model)
        self.resource_curator = ResourceCuratorAgent(self.client, self.model)
        self.task_generator = EngageTaskGeneratorAgent(self.client, self.model)

    def apply_refinement(self, unit: LearningUnit, processed_feedback) -> 'RefinementResult':
        """
        Apply refinement actions to a learning unit based on processed feedback.
        
        This is the primary method for modifying a learning unit. It orchestrates
        calls to various sub-agents based on the requested refinement actions.
        
        Args:
            unit: LearningUnit to refine
            processed_feedback: ProcessedFeedback object with refinement actions
            
        Returns:
            RefinementResult with the refined unit and metadata
        """
        logger.info(f"Applying refinement to unit {unit.id} with {len(processed_feedback.refinement_actions)} actions")
        
        refined_unit = unit.model_copy(deep=True)
        changes_made: List[str] = []
        updated_components: List[str] = []
        agent_responses: Dict[str, Any] = {}
        errors: List[str] = []

        for action in processed_feedback.refinement_actions:
            try:
                if action.action_type == "add_resources":
                    new_resources, agent_response = self._add_resources_to_unit(refined_unit, action)
                    agent_responses["add_resources"] = agent_response
                    if agent_response.get("success"):
                        refined_unit.resources.extend(new_resources)
                        changes_made.append(f"Added {len(new_resources)} new resources.")
                        updated_components.append("resources")
                    else:
                        errors.append(f"Failed to add resources: {agent_response.get('error', 'Unknown error')}")

                elif action.action_type == "add_tasks":
                    new_tasks, agent_response = self._add_tasks_to_unit(refined_unit, action)
                    agent_responses["add_tasks"] = agent_response
                    if agent_response.get("success"):
                        refined_unit.engage_tasks.extend(new_tasks)
                        task_word = "task" if len(new_tasks) == 1 else "tasks"
                        changes_made.append(f"Added {len(new_tasks)} new engage {task_word}.")
                        updated_components.append("engage_tasks")
                    else:
                        errors.append(f"Failed to add tasks: {agent_response.get('error', 'Unknown error')}")
                    
                elif action.action_type in ["clarify_content", "reduce_difficulty", "increase_difficulty", "general_review"]:
                    refined_content, agent_response = self._update_unit_content(refined_unit, action)
                    agent_responses[action.action_type] = agent_response
                    if agent_response.get("success"):
                        refined_unit.title = refined_content.get("title", refined_unit.title)
                        refined_unit.description = refined_content.get("description", refined_unit.description)
                        changes_made.append(f"Updated content based on '{action.action_type}' feedback.")
                        updated_components.append("content")
                    else:
                        errors.append(f"Failed to update content: {agent_response.get('error', 'Unknown error')}")

            except Exception as e:
                error_msg = f"Error applying action '{action.action_type}': {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg, exc_info=True)

        success = not errors
        reasoning = f"Applied {len(changes_made)} changes with {len(errors)} errors."

        # Record the refinement attempt in history
        self._record_refinement(unit, processed_feedback.summary, changes_made, reasoning)

        return RefinementResult(
            unit_id=unit.id,
            refined_unit=refined_unit,
            changes_made=changes_made,
            reasoning=reasoning,
            success=success,
            updated_components=list(set(updated_components)),
            agent_responses=agent_responses,
            errors=errors,
        )

    def _record_refinement(self, unit: LearningUnit, feedback: str, changes_made: List[str], reasoning: str) -> None:
        """
        Record refinement in history for tracking and analysis.
        """
        refinement_record = {
            "timestamp": datetime.now().isoformat(),
            "unit_id": unit.id,
            "unit_title": unit.title,
            "feedback": feedback,
            "changes_made": changes_made,
            "reasoning": reasoning
        }
        self.refinement_history.append(refinement_record)
        logger.debug(f"Recorded refinement for unit {unit.id}")
    
    def get_refinement_history(self, unit_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get refinement history, optionally filtered by unit ID.
        """
        if unit_id:
            return [record for record in self.refinement_history if record["unit_id"] == unit_id]
        return self.refinement_history.copy()
    
    def clear_history(self) -> None:
        """Clear all refinement history."""
        self.refinement_history.clear()
        logger.info("Cleared refinement history")
    
    def _add_resources_to_unit(self, unit: LearningUnit, action) -> Tuple[List[LearningResource], Dict[str, Any]]:
        """Add resources to unit using resource curator."""
        try:
            request = ResourceRequest(
                unit=unit,
                min_video_resources=action.details.get("count", 1),
                min_reading_resources=action.details.get("count", 1),
                max_total_resources=action.details.get("count", 2)
            )
            resources, success = self.resource_curator.curate_resources(request)
            return resources, {"success": success, "count": len(resources)}
        except Exception as e:
            logger.error(f"Failed to add resources: {e}")
            return [], {"success": False, "error": str(e)}
    
    def _add_tasks_to_unit(self, unit: LearningUnit, action) -> Tuple[List[EngageTask], Dict[str, Any]]:
        """Add tasks to unit using task generator."""
        try:
            num_tasks = action.details.get("count", 1)
            
            # Create a proper request
            request = TaskGenerationRequest(
                unit=unit,
                resources=unit.resources,
                num_tasks=num_tasks,
                difficulty_preference=action.details.get("difficulty", None),
                focus_on_application=True
            )
            
            # Generate tasks
            tasks, success = self.task_generator.generate_tasks(request)
            
            return tasks, {"success": success, "count": len(tasks)}
        except Exception as e:
            logger.error(f"Failed to add tasks: {e}")
            return [], {"success": False, "error": str(e)}
    
    def _update_unit_content(self, unit: LearningUnit, action) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Update unit content using the ContentGeneratorAgent."""
        try:
            # Create a request with the full unit
            request = ContentGenerationRequest(
                unit=unit,
                min_video_resources=1,
                min_reading_resources=1,
                max_total_resources=5,
                num_engage_tasks=1,
                difficulty_preference=action.details.get("difficulty", None)
            )
            
            # Generate new content
            generated_content = self.content_generator.generate_complete_content(request)
            
            if generated_content.generation_success:
                # For content updates, we only want to update the description (and possibly title)
                # based on the action type
                refined_content = {
                    "title": unit.title,  # Keep original title unless specifically changed
                    "description": unit.description  # Will be updated based on feedback
                }
                
                # Apply specific updates based on action type
                if action.action_type == "reduce_difficulty":
                    refined_content["description"] = f"[Simplified for beginners] {unit.description}"
                elif action.action_type == "increase_difficulty":
                    refined_content["description"] = f"[Advanced level] {unit.description}"
                elif action.action_type == "clarify_content":
                    refined_content["description"] = f"[Clarified] {unit.description}"
                
                return refined_content, {"success": True, "result": refined_content}
            else:
                return {}, {"success": False, "error": "Content generation failed."}
        except Exception as e:
            logger.error(f"Failed to update content via ContentGeneratorAgent: {e}", exc_info=True)
            return {}, {"success": False, "error": str(e)}

    def batch_apply_refinements(self, units: List[LearningUnit], feedback_list: List) -> List[RefinementResult]:
        """
        Apply refinements to multiple units with their corresponding feedback.
        """
        results = []
        for unit, feedback in zip(units, feedback_list):
            try:
                result = self.apply_refinement(unit, feedback)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to apply refinement to unit {unit.id}: {e}")
                error_result = RefinementResult(
                    unit_id=unit.id,
                    refined_unit=unit,
                    reasoning=f"Batch refinement failed: {str(e)}",
                    success=False,
                    errors=[f"Batch refinement failed: {str(e)}"]
                )
                results.append(error_result)
        return results


def create_unit_refinement_engine(api_key: Optional[str] = None, model: str = DefaultSettings.DEFAULT_MODEL) -> UnitRefinementEngine:
    """
    Factory function to create a UnitRefinementEngine with proper OpenAI client setup.
    """
    try:
        client = OpenAI(api_key=api_key) if api_key else OpenAI()
        return UnitRefinementEngine(client, model)
    except Exception as e:
        raise RuntimeError(f"Failed to create UnitRefinementEngine: {str(e)}")