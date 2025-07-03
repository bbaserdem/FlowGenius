"""
FlowGenius Unit Refinement Engine

This module contains the core AI agent for iterative unit refinement
based on user feedback and content generation using LangChain orchestration.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from openai import OpenAI
from pydantic import BaseModel, Field

from ..models.project import LearningUnit, LearningResource, EngageTask, UserFeedback
from ..models.settings import DefaultSettings
from .content_generator import ContentGeneratorAgent, ContentGenerationRequest
from .resource_curator import ResourceCuratorAgent, ResourceRequest
from .engage_task_generator import EngageTaskGeneratorAgent, TaskGenerationRequest
from .feedback_processor import FeedbackProcessor, RefinementRecommendation, RefinementAction
from ..utils import get_timestamp

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
    
    This agent processes user feedback using LangChain and refines learning units 
    to better meet learner needs and objectives.
    """
    
    def __init__(self, openai_client: OpenAI, model: str = DefaultSettings.DEFAULT_MODEL) -> None:
        """
        Initialize the refinement engine with OpenAI client and LangChain components.
        
        Args:
            openai_client: Configured OpenAI client
            model: OpenAI model to use for refinement
        """
        self.client = openai_client
        self.model = model
        self.refinement_history: List[Dict[str, Any]] = []
        
        # Initialize sub-agents
        self.content_generator = ContentGeneratorAgent(self.client, self.model)
        self.resource_curator = ResourceCuratorAgent(self.client, self.model)
        self.task_generator = EngageTaskGeneratorAgent(self.client, self.model)
        
        # Initialize LangChain-based feedback processor
        self.feedback_processor = FeedbackProcessor(self.model)

    def apply_refinement(self, unit: LearningUnit, feedback: UserFeedback) -> 'RefinementResult':
        """
        Apply refinement to a learning unit based on user feedback using LangChain.
        
        This method uses the FeedbackProcessor to analyze feedback and generate
        refinement recommendations, then orchestrates sub-agents to apply changes.
        
        Args:
            unit: LearningUnit to refine
            feedback: UserFeedback object to process
            
        Returns:
            RefinementResult with the refined unit and metadata
        """
        logger.info(f"Applying refinement to unit {unit.id} based on feedback")
        
        # Use LangChain to analyze feedback and get recommendation
        recommendation = self.feedback_processor.analyze_feedback(feedback, unit)
        logger.info(f"LangChain recommendation: {recommendation.action} with priority {recommendation.priority}")
        
        refined_unit = unit.model_copy(deep=True)
        changes_made: List[str] = []
        updated_components: List[str] = []
        agent_responses: Dict[str, Any] = {}
        errors: List[str] = []

        try:
            # Map LangChain recommendation to refinement actions
            if recommendation.action == RefinementAction.ADD_CONTENT:
                # Add resources based on the recommendation
                new_resources, agent_response = self._add_resources_to_unit(
                    refined_unit, 
                    recommendation
                )
                agent_responses["add_resources"] = agent_response
                if agent_response.get("success"):
                    refined_unit.resources.extend(new_resources)
                    changes_made.append(f"Added {len(new_resources)} new resources based on feedback.")
                    updated_components.append("resources")
                else:
                    errors.append(f"Failed to add resources: {agent_response.get('error', 'Unknown error')}")

            elif recommendation.action == RefinementAction.ADD_EXAMPLES:
                # Add engage tasks as examples
                new_tasks, agent_response = self._add_tasks_to_unit(
                    refined_unit, 
                    recommendation
                )
                agent_responses["add_tasks"] = agent_response
                if agent_response.get("success"):
                    refined_unit.engage_tasks.extend(new_tasks)
                    task_word = "task" if len(new_tasks) == 1 else "tasks"
                    changes_made.append(f"Added {len(new_tasks)} new engage {task_word} as examples.")
                    updated_components.append("engage_tasks")
                else:
                    errors.append(f"Failed to add tasks: {agent_response.get('error', 'Unknown error')}")
                    
            elif recommendation.action in [RefinementAction.CLARIFY_CONTENT, 
                                         RefinementAction.SIMPLIFY_CONTENT,
                                         RefinementAction.EXPAND_CONTENT]:
                # Update content based on recommendation
                refined_content, agent_response = self._update_unit_content(
                    refined_unit, 
                    recommendation
                )
                agent_responses[recommendation.action.value] = agent_response
                if agent_response.get("success"):
                    refined_unit.title = refined_content.get("title", refined_unit.title)
                    refined_unit.description = refined_content.get("description", refined_unit.description)
                    changes_made.append(f"Updated content: {recommendation.reasoning}")
                    updated_components.append("content")
                else:
                    errors.append(f"Failed to update content: {agent_response.get('error', 'Unknown error')}")
                    
            elif recommendation.action == RefinementAction.NO_ACTION:
                changes_made.append("No changes needed based on feedback analysis.")
                
            else:
                # For other actions, log but don't fail
                logger.warning(f"Unhandled refinement action: {recommendation.action}")
                changes_made.append(f"Acknowledged feedback: {recommendation.reasoning}")

        except Exception as e:
            error_msg = f"Error applying refinement: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg, exc_info=True)

        success = len(errors) == 0
        reasoning = recommendation.reasoning
        if errors:
            reasoning += f" However, encountered {len(errors)} errors during execution."

        # Record the refinement attempt in history
        self._record_refinement(unit, feedback.feedback_text, changes_made, reasoning)

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
            "timestamp": get_timestamp(),
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
    
    def _add_resources_to_unit(self, unit: LearningUnit, recommendation: RefinementRecommendation) -> Tuple[List[LearningResource], Dict[str, Any]]:
        """Add resources to unit using resource curator based on LangChain recommendation."""
        try:
            # Determine resource count from recommendation
            count = 2  # Default
            if "video" in " ".join(recommendation.specific_changes).lower():
                count = 3  # More if specifically requesting videos
                
            request = ResourceRequest(
                unit=unit,
                min_video_resources=1,
                min_reading_resources=1,
                max_total_resources=count
            )
            resources, success = self.resource_curator.curate_resources(request)
            return resources, {"success": success, "count": len(resources)}
        except Exception as e:
            logger.error(f"Failed to add resources: {e}", exc_info=True)
            return [], {"success": False, "error": str(e)}
    
    def _add_tasks_to_unit(self, unit: LearningUnit, recommendation: RefinementRecommendation) -> Tuple[List[EngageTask], Dict[str, Any]]:
        """Add tasks to unit using task generator based on LangChain recommendation."""
        try:
            # Determine task count and type from recommendation
            num_tasks = 2  # Default
            if "practice" in " ".join(recommendation.specific_changes).lower():
                num_tasks = 3
                
            request = TaskGenerationRequest(
                unit=unit,
                resources=unit.resources,
                num_tasks=num_tasks,
                focus_on_application=True
            )
            
            tasks, success = self.task_generator.generate_tasks(request)
            return tasks, {"success": success, "count": len(tasks)}
        except Exception as e:
            logger.error(f"Failed to add tasks: {e}", exc_info=True)
            return [], {"success": False, "error": str(e)}
    
    def _update_unit_content(self, unit: LearningUnit, recommendation: RefinementRecommendation) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Update unit content using the ContentGeneratorAgent based on LangChain recommendation."""
        try:
            # Create a request with the full unit
            request = ContentGenerationRequest(
                unit=unit,
                min_video_resources=1,
                min_reading_resources=1,
                max_total_resources=5,
                num_engage_tasks=1
            )
            
            # Generate new content
            generated_content = self.content_generator.generate_complete_content(request)
            
            if generated_content.generation_success:
                # Apply specific updates based on recommendation
                refined_content = {
                    "title": unit.title,  # Keep original title
                    "description": unit.description  # Will be updated
                }
                
                # Apply specific updates based on action type
                if recommendation.action == RefinementAction.SIMPLIFY_CONTENT:
                    refined_content["description"] = f"[Simplified] {unit.description}"
                elif recommendation.action == RefinementAction.CLARIFY_CONTENT:
                    refined_content["description"] = f"[Clarified] {unit.description}"
                elif recommendation.action == RefinementAction.EXPAND_CONTENT:
                    refined_content["description"] = f"[Expanded] {unit.description}"
                
                return refined_content, {"success": True, "result": refined_content}
            else:
                return {}, {"success": False, "error": "Content generation failed."}
        except Exception as e:
            logger.error(f"Failed to update content: {e}", exc_info=True)
            return {}, {"success": False, "error": str(e)}

    def batch_apply_refinements(self, units: List[LearningUnit], feedbacks: List[UserFeedback]) -> List[RefinementResult]:
        """
        Apply refinements to multiple units with their corresponding feedback.
        
        Uses LangChain to process each feedback and apply appropriate refinements.
        """
        results = []
        for unit, feedback in zip(units, feedbacks):
            try:
                result = self.apply_refinement(unit, feedback)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to apply refinement to unit {unit.id}: {e}", exc_info=True)
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
    except ImportError as e:
        logger.error(f"Failed to import OpenAI: {e}")
        raise RuntimeError(f"Failed to create UnitRefinementEngine: OpenAI package not installed") from e
    except Exception as e:
        logger.error(f"Failed to create UnitRefinementEngine: {e}", exc_info=True)
        raise RuntimeError(f"Failed to create UnitRefinementEngine: {str(e)}") from e