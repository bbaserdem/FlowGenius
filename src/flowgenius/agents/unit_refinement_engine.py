"""
FlowGenius Unit Refinement Engine

This module coordinates existing agents using LangChain to apply refinement
actions to learning units based on processed user feedback.
"""

from typing import Dict, List, Optional, Any, Tuple
from openai import OpenAI
from pydantic import BaseModel, Field
from langchain_core.prompts import PromptTemplate

from .feedback_processor import ProcessedFeedback, RefinementAction
from .content_generator import ContentGeneratorAgent, ContentGenerationRequest
from .resource_curator import ResourceCuratorAgent, ResourceRequest
from .engage_task_generator import EngageTaskGeneratorAgent, TaskGenerationRequest
from ..models.project import LearningUnit


class RefinementResult(BaseModel):
    """Result of a unit refinement operation."""
    unit_id: str = Field(description="ID of the refined unit")
    actions_applied: List[str] = Field(description="List of successfully applied actions")
    errors: List[str] = Field(default_factory=list, description="Any errors encountered")
    modified_components: List[str] = Field(description="Components that were modified")
    success: bool = Field(description="Whether refinement was successful")
    summary: str = Field(description="Summary of changes made")


class UnitRefinementEngine:
    """
    Coordinates existing agents using LangChain to apply refinement actions to learning units.
    
    This engine takes processed feedback with refinement actions and orchestrates
    the appropriate agents to modify units accordingly.
    """
    
    def __init__(self, openai_client: OpenAI, model: str = "gpt-4o-mini") -> None:
        """
        Initialize the refinement engine.
        
        Args:
            openai_client: OpenAI client for AI operations
            model: OpenAI model to use for refinement coordination
        """
        self.client = openai_client
        self.model = model
        
        # Initialize component agents
        self.content_generator = ContentGeneratorAgent(openai_client, model)
        self.resource_curator = ResourceCuratorAgent(openai_client, model)
        self.task_generator = EngageTaskGeneratorAgent(openai_client, model)
        
        # Refinement coordination prompt
        self.coordination_prompt = PromptTemplate(
            input_variables=["action_type", "target_component", "action_details", "unit_context"],
            template="""
            You are coordinating a refinement action for a learning unit.
            
            Action Type: {action_type}
            Target Component: {target_component}
            Action Details: {action_details}
            
            Current Unit Context:
            {unit_context}
            
            Based on this refinement action, provide specific instructions for modifying the unit.
            Focus on actionable changes that will address the user's feedback.
            """
        )
    
    def refine_unit(self, unit: LearningUnit, processed_feedback: ProcessedFeedback) -> RefinementResult:
        """
        Apply refinement actions to a learning unit.
        
        Args:
            unit: LearningUnit to refine
            processed_feedback: ProcessedFeedback containing refinement actions
            
        Returns:
            RefinementResult with details of applied changes
        """
        actions_applied = []
        errors = []
        modified_components = []
        
        # Sort actions by priority (highest first)
        sorted_actions = sorted(
            processed_feedback.refinement_actions, 
            key=lambda a: a.priority, 
            reverse=True
        )
        
        for action in sorted_actions:
            try:
                result = self._apply_refinement_action(unit, action)
                if result:
                    actions_applied.append(action.action_type)
                    if action.target_component not in modified_components:
                        modified_components.append(action.target_component)
                else:
                    errors.append(f"Failed to apply action: {action.action_type}")
                    
            except Exception as e:
                errors.append(f"Error applying {action.action_type}: {str(e)}")
        
        success = len(actions_applied) > 0 and len(errors) == 0
        summary = self._generate_refinement_summary(actions_applied, modified_components, errors)
        
        return RefinementResult(
            unit_id=unit.id,
            actions_applied=actions_applied,
            errors=errors,
            modified_components=modified_components,
            success=success,
            summary=summary
        )
    
    def batch_refine_units(self, units: List[LearningUnit], feedback_list: List[ProcessedFeedback]) -> List[RefinementResult]:
        """
        Refine multiple units based on their respective feedback.
        
        Args:
            units: List of LearningUnit objects to refine
            feedback_list: List of ProcessedFeedback objects
            
        Returns:
            List of RefinementResult objects
        """
        results = []
        
        # Create lookup for feedback by unit_id
        feedback_by_unit = {pf.unit_id: pf for pf in feedback_list}
        
        for unit in units:
            if unit.id in feedback_by_unit:
                result = self.refine_unit(unit, feedback_by_unit[unit.id])
                results.append(result)
        
        return results
    
    def _apply_refinement_action(self, unit: LearningUnit, action: RefinementAction) -> bool:
        """
        Apply a specific refinement action to a unit.
        
        Args:
            unit: LearningUnit to modify
            action: RefinementAction to apply
            
        Returns:
            True if action was successfully applied, False otherwise
        """
        try:
            if action.action_type == "add_resources":
                return self._add_resources(unit, action)
            elif action.action_type == "replace_resources":
                return self._replace_resources(unit, action)
            elif action.action_type == "add_tasks":
                return self._add_tasks(unit, action)
            elif action.action_type == "simplify_tasks":
                return self._simplify_tasks(unit, action)
            elif action.action_type == "reduce_difficulty":
                return self._reduce_difficulty(unit, action)
            elif action.action_type == "increase_difficulty":
                return self._increase_difficulty(unit, action)
            elif action.action_type == "clarify_content":
                return self._clarify_content(unit, action)
            elif action.action_type == "general_review":
                return self._general_review(unit, action)
            else:
                return False
                
        except Exception:
            return False
    
    def _add_resources(self, unit: LearningUnit, action: RefinementAction) -> bool:
        """Add additional resources to the unit."""
        try:
            resource_count = action.details.get("count", 2)
            resource_types = action.details.get("resource_types", ["video", "article"])
            
            # Create resource request
            resource_request = ResourceRequest(
                unit=unit,
                min_video_resources=1 if "video" in resource_types else 0,
                min_reading_resources=1 if "article" in resource_types else 0,
                max_total_resources=resource_count
            )
            
            # Generate new resources
            new_resources, success = self.resource_curator.curate_resources(resource_request)
            
            if success and new_resources:
                # Add only the new resources (avoid duplicates)
                existing_titles = {r.title for r in unit.resources}
                for resource in new_resources:
                    if resource.title not in existing_titles:
                        unit.resources.append(resource)
                return True
            
            return False
            
        except Exception:
            return False
    
    def _replace_resources(self, unit: LearningUnit, action: RefinementAction) -> bool:
        """Replace existing resources with better alternatives."""
        try:
            replace_count = action.details.get("replace_count", 1)
            
            if len(unit.resources) == 0:
                return self._add_resources(unit, action)
            
            # Create resource request for replacements
            resource_request = ResourceRequest(
                unit=unit,
                max_total_resources=replace_count + 1
            )
            
            # Generate new resources
            new_resources, success = self.resource_curator.curate_resources(resource_request)
            
            if success and new_resources:
                # Replace first resource with new one
                if len(new_resources) > 0:
                    unit.resources[0] = new_resources[0]
                return True
            
            return False
            
        except Exception:
            return False
    
    def _add_tasks(self, unit: LearningUnit, action: RefinementAction) -> bool:
        """Add more engaging tasks to the unit."""
        try:
            task_count = action.details.get("count", 1)
            task_types = action.details.get("task_types", ["practice", "reflection"])
            
            # Create task request
            task_request = TaskGenerationRequest(
                unit=unit,
                resources=unit.resources,
                num_tasks=task_count,
                focus_on_application=True
            )
            
            # Generate new tasks
            new_tasks, success = self.task_generator.generate_tasks(task_request)
            
            if success and new_tasks:
                # Add new tasks to unit
                existing_titles = {t.title for t in unit.engage_tasks}
                for task in new_tasks:
                    if task.title not in existing_titles:
                        unit.engage_tasks.append(task)
                return True
            
            return False
            
        except Exception:
            return False
    
    def _simplify_tasks(self, unit: LearningUnit, action: RefinementAction) -> bool:
        """Make existing tasks easier or more accessible."""
        try:
            if not unit.engage_tasks:
                return True  # Nothing to simplify
            
            # Modify task descriptions to be simpler
            for task in unit.engage_tasks:
                if "complex" in task.description.lower():
                    task.description = task.description.replace("complex", "simple")
                if "advanced" in task.description.lower():
                    task.description = task.description.replace("advanced", "basic")
                
                # Add helpful guidance
                if not task.description.endswith("."):
                    task.description += "."
                task.description += " Take your time and don't worry about perfect results."
            
            return True
            
        except Exception:
            return False
    
    def _reduce_difficulty(self, unit: LearningUnit, action: RefinementAction) -> bool:
        """Reduce complexity and add more scaffolding."""
        try:
            # Simplify unit description
            if "advanced" in unit.description.lower():
                unit.description = unit.description.replace("advanced", "introductory")
            if "complex" in unit.description.lower():
                unit.description = unit.description.replace("complex", "basic")
            
            # Add scaffolding to learning objectives
            scaffolding_objectives = [
                "Understand the basic concepts before diving deeper",
                "Review prerequisite knowledge as needed"
            ]
            
            # Add scaffolding objectives if not already present
            for obj in scaffolding_objectives:
                if obj not in unit.learning_objectives:
                    unit.learning_objectives.insert(0, obj)
            
            return True
            
        except Exception:
            return False
    
    def _increase_difficulty(self, unit: LearningUnit, action: RefinementAction) -> bool:
        """Add more challenging elements and advanced concepts."""
        try:
            # Enhance unit description
            if "basic" in unit.description.lower():
                unit.description = unit.description.replace("basic", "comprehensive")
            if "simple" in unit.description.lower():
                unit.description = unit.description.replace("simple", "advanced")
            
            # Add advanced learning objectives
            advanced_objectives = [
                "Apply concepts to real-world scenarios",
                "Analyze complex examples and edge cases",
                "Synthesize knowledge from multiple sources"
            ]
            
            # Add advanced objectives if not already present
            for obj in advanced_objectives:
                if obj not in unit.learning_objectives:
                    unit.learning_objectives.append(obj)
            
            return True
            
        except Exception:
            return False
    
    def _clarify_content(self, unit: LearningUnit, action: RefinementAction) -> bool:
        """Clarify unit description and learning objectives."""
        try:
            # Enhance description clarity
            if not unit.description.endswith("."):
                unit.description += "."
            
            if "this unit" not in unit.description.lower():
                unit.description = f"This unit covers {unit.description.lower()}"
            
            # Add clarity to learning objectives
            clarity_phrases = [
                "Clearly understand",
                "Demonstrate knowledge of",
                "Explain the concepts of"
            ]
            
            # Enhance objectives for clarity
            for i, obj in enumerate(unit.learning_objectives):
                if not any(phrase in obj for phrase in clarity_phrases):
                    if not obj.startswith(("Understand", "Learn", "Master", "Apply")):
                        unit.learning_objectives[i] = f"Understand {obj.lower()}"
            
            return True
            
        except Exception:
            return False
    
    def _general_review(self, unit: LearningUnit, action: RefinementAction) -> bool:
        """Perform a general review and improvement of unit content."""
        try:
            # Add more comprehensive description if it's too short
            if len(unit.description.split()) < 10:
                unit.description += " This unit provides a comprehensive introduction to the topic with practical examples and hands-on activities."
            
            # Ensure minimum number of learning objectives
            if len(unit.learning_objectives) < 3:
                unit.learning_objectives.append("Apply learned concepts in practical situations")
                unit.learning_objectives.append("Demonstrate understanding through examples")
            
            return True
            
        except Exception:
            return False
    
    def _generate_refinement_summary(self, actions_applied: List[str], modified_components: List[str], errors: List[str]) -> str:
        """Generate a summary of the refinement process."""
        if not actions_applied and not errors:
            return "No refinement actions were needed."
        
        summary_parts = []
        
        if actions_applied:
            summary_parts.append(f"Applied {len(actions_applied)} refinement actions")
            if modified_components:
                summary_parts.append(f"Modified components: {', '.join(modified_components)}")
        
        if errors:
            summary_parts.append(f"Encountered {len(errors)} errors during refinement")
        
        return "; ".join(summary_parts)


def create_unit_refinement_engine(api_key: Optional[str] = None, model: str = "gpt-4o-mini") -> UnitRefinementEngine:
    """
    Factory function to create a UnitRefinementEngine with OpenAI client.
    
    Args:
        api_key: OpenAI API key. If None, will try to get from environment
        model: OpenAI model to use for refinement coordination
        
    Returns:
        Configured UnitRefinementEngine instance
    """
    try:
        if api_key:
            client = OpenAI(api_key=api_key)
        else:
            client = OpenAI()
        
        return UnitRefinementEngine(client, model)
    
    except Exception as e:
        raise RuntimeError(f"Failed to create UnitRefinementEngine: {str(e)}") 