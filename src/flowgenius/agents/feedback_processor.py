"""
FlowGenius Feedback Processor

This module processes user feedback to determine specific refinement actions
for learning units using LangChain for intelligent interpretation.
"""

import logging
import os
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from pydantic import BaseModel, Field

from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_openai import ChatOpenAI

from .conversation_manager import UserFeedback
from ..models.project import LearningUnit
from ..models.settings import DefaultSettings

# Set up module logger
logger = logging.getLogger(__name__)


class RefinementAction(str, Enum):
    """Types of refinement actions that can be taken."""
    ADD_CONTENT = "add_content"
    REMOVE_CONTENT = "remove_content"
    MODIFY_CONTENT = "modify_content"
    REORDER_CONTENT = "reorder_content"
    CLARIFY_CONTENT = "clarify_content"
    EXPAND_CONTENT = "expand_content"
    SIMPLIFY_CONTENT = "simplify_content"
    ADD_EXAMPLES = "add_examples"
    UPDATE_RESOURCES = "update_resources"
    ADJUST_DIFFICULTY = "adjust_difficulty"
    NO_ACTION = "no_action"


class RefinementRecommendation(BaseModel):
    """Structured recommendation for unit refinement based on feedback."""
    action: RefinementAction = Field(description="The type of refinement action to take")
    priority: str = Field(description="Priority level: high, medium, or low")
    target_section: Optional[str] = Field(default=None, description="Specific section to refine")
    specific_changes: List[str] = Field(default_factory=list, description="List of specific changes to make")
    reasoning: str = Field(description="Explanation of why this refinement is recommended")
    estimated_impact: str = Field(description="Expected impact on learning effectiveness")


class FeedbackProcessor:
    """
    Processes user feedback to determine specific refinement actions for learning units.
    
    This class analyzes feedback using LangChain to extract actionable insights.
    """
    
    def __init__(self, model_name: str = DefaultSettings.DEFAULT_MODEL) -> None:
        """
        Initialize the feedback processor with LangChain components.
        
        Args:
            model_name: Name of the OpenAI model to use
        """
        self.model_name = model_name
        self.chat_model = ChatOpenAI(model=model_name, temperature=0.3)
        self.refinement_cache: Dict[str, RefinementRecommendation] = {}
        
        # Set up output parser for structured responses
        self.output_parser = JsonOutputParser(pydantic_object=RefinementRecommendation)
        
        # Create prompt template with LangChain
        self.prompt = PromptTemplate(
            input_variables=["feedback_text", "unit_title", "unit_content", "format_instructions"],
            template="""
You are an AI learning assistant analyzing user feedback to recommend specific refinements for a learning unit.

Learning Unit: {unit_title}
Current Content Summary: {unit_content}

User Feedback:
{feedback_text}

Analyze this feedback and provide a structured recommendation for improving the learning unit.

{format_instructions}

Focus on:
1. Understanding the user's core concern or suggestion
2. Identifying the most impactful refinement action
3. Providing specific, actionable changes
4. Explaining the reasoning behind your recommendation
5. Estimating the impact on learning effectiveness

Remember to be specific and practical in your recommendations.
"""
        )
        
        # Create the analysis chain
        self.analysis_chain = self.prompt | self.chat_model | self.output_parser
    
    def analyze_feedback(self, feedback: UserFeedback, unit: LearningUnit) -> RefinementRecommendation:
        """
        Analyze user feedback to generate refinement recommendations using LangChain.
        
        Args:
            feedback: User feedback to analyze
            unit: Learning unit being refined
            
        Returns:
            Structured refinement recommendation
        """
        try:
            # Prepare unit content summary
            unit_content = self._summarize_unit_content(unit)
            
            # Get format instructions from the parser
            format_instructions = self.output_parser.get_format_instructions()
            
            # Run the analysis chain
            recommendation = self.analysis_chain.invoke({
                "feedback_text": feedback.feedback_text,
                "unit_title": unit.title,
                "unit_content": unit_content,
                "format_instructions": format_instructions
            })
            
            # Ensure it's a proper RefinementRecommendation object
            if isinstance(recommendation, dict):
                recommendation = RefinementRecommendation(**recommendation)
            
            return recommendation
            
        except Exception as e:
            logger.error(f"Error analyzing feedback with LangChain: {e}", exc_info=True)
            return self._analyze_feedback_fallback(feedback, unit)
    
    def _summarize_unit_content(self, unit: LearningUnit) -> str:
        """
        Create a summary of the unit content for analysis.
        
        Args:
            unit: Learning unit to summarize
            
        Returns:
            Summary string
        """
        summary_parts = [
            f"Description: {unit.description}",
            f"Learning Objectives: {len(unit.learning_objectives)} objectives",
        ]
        
        if unit.resources:
            summary_parts.append(f"Resources: {len(unit.resources)} resources")
            
        if unit.engage_tasks:
            summary_parts.append(f"Tasks: {len(unit.engage_tasks)} engage tasks")
            
        if unit.estimated_duration:
            summary_parts.append(f"Duration: {unit.estimated_duration}")
        
        return "\n".join(summary_parts)
    
    def _analyze_feedback_fallback(self, feedback: UserFeedback, unit: LearningUnit) -> RefinementRecommendation:
        """
        Fallback analysis when LLM is not available.
        
        Args:
            feedback: User feedback to analyze
            unit: Learning unit being refined
            
        Returns:
            Basic refinement recommendation
        """
        # Simple keyword-based analysis
        feedback_lower = feedback.feedback_text.lower()
        
        action = RefinementAction.NO_ACTION
        priority = "medium"
        specific_changes = []
        reasoning = "Analyzed based on keyword patterns in feedback"
        
        if any(word in feedback_lower for word in ["add", "more", "include", "missing"]):
            action = RefinementAction.ADD_CONTENT
            specific_changes = ["Add more content based on user feedback"]
            reasoning = "User indicated content is missing or insufficient"
        elif any(word in feedback_lower for word in ["remove", "delete", "too much", "unnecessary"]):
            action = RefinementAction.REMOVE_CONTENT
            specific_changes = ["Remove excessive content"]
            reasoning = "User indicated some content is unnecessary"
        elif any(word in feedback_lower for word in ["confusing", "unclear", "don't understand"]):
            action = RefinementAction.CLARIFY_CONTENT
            specific_changes = ["Clarify confusing sections"]
            reasoning = "User found content unclear or confusing"
        elif any(word in feedback_lower for word in ["example", "demonstrate", "show"]):
            action = RefinementAction.ADD_EXAMPLES
            specific_changes = ["Add practical examples"]
            reasoning = "User requested examples or demonstrations"
        
        return RefinementRecommendation(
            action=action,
            priority=priority,
            target_section=None,
            specific_changes=specific_changes,
            reasoning=reasoning,
            estimated_impact="Medium - Based on keyword analysis"
        )
    
    def process_feedback_batch(self, feedbacks: List[UserFeedback], unit: LearningUnit) -> List[RefinementRecommendation]:
        """
        Process multiple feedback items for a unit.
        
        Args:
            feedbacks: List of feedback to process
            unit: Learning unit being refined
            
        Returns:
            List of refinement recommendations
        """
        recommendations = []
        
        for feedback in feedbacks:
            try:
                recommendation = self.analyze_feedback(feedback, unit)
                recommendations.append(recommendation)
            except Exception as e:
                logger.error(f"Error processing feedback {feedback.feedback_text[:50]}...: {e}")
                continue
        
        return recommendations
    
    def prioritize_recommendations(self, recommendations: List[RefinementRecommendation]) -> List[RefinementRecommendation]:
        """
        Prioritize and deduplicate recommendations.
        
        Args:
            recommendations: List of recommendations to prioritize
            
        Returns:
            Prioritized list of recommendations
        """
        # Sort by priority
        priority_order = {"high": 0, "medium": 1, "low": 2}
        sorted_recs = sorted(
            recommendations,
            key=lambda r: priority_order.get(r.priority, 3)
        )
        
        # Simple deduplication by action type
        seen_actions = set()
        unique_recs = []
        
        for rec in sorted_recs:
            if rec.action not in seen_actions or rec.priority == "high":
                unique_recs.append(rec)
                seen_actions.add(rec.action)
        
        return unique_recs


def create_feedback_processor(api_key: Optional[str] = None, model: str = DefaultSettings.DEFAULT_MODEL) -> FeedbackProcessor:
    """
    Factory function to create a FeedbackProcessor with LangChain.
    
    Args:
        api_key: OpenAI API key. If None, will try to get from environment
        model: OpenAI model to use for analysis
        
    Returns:
        Configured FeedbackProcessor instance
    """
    try:
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key
        elif "OPENAI_API_KEY" not in os.environ:
            raise RuntimeError("OpenAI API key not provided and OPENAI_API_KEY environment variable not set")
        
        return FeedbackProcessor(model)
    
    except ImportError as e:
        logger.error(f"Failed to import required packages: {e}")
        raise RuntimeError(f"Failed to create FeedbackProcessor: Required packages not installed") from e
    except Exception as e:
        logger.error(f"Failed to create FeedbackProcessor: {e}", exc_info=True)
        raise RuntimeError(f"Failed to create FeedbackProcessor: {str(e)}") from e 