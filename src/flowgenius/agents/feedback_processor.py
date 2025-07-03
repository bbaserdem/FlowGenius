"""
FlowGenius Feedback Processor

This module processes user feedback to determine specific refinement actions
for learning units, interfacing with LangChain for intelligent interpretation.
"""

from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from openai import OpenAI
from pydantic import BaseModel, Field
from langchain_core.prompts import PromptTemplate

from .conversation_manager import UserFeedback
from ..models.project import LearningUnit


class FeedbackCategory(str, Enum):
    """Categories of feedback for refinement."""
    CONTENT = "content"
    RESOURCES = "resources"
    TASKS = "tasks"
    DIFFICULTY = "difficulty"
    STRUCTURE = "structure"
    OBJECTIVES = "objectives"
    GENERAL = "general"


class RefinementAction(BaseModel):
    """Represents a specific action to refine a unit."""
    action_type: str = Field(description="Type of refinement action")
    target_component: str = Field(description="What component to modify")
    description: str = Field(description="Description of the action")
    priority: int = Field(description="Priority level (1-5)")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional details")


class ProcessedFeedback(BaseModel):
    """Structured analysis of user feedback with refinement actions."""
    unit_id: str = Field(description="ID of the unit being refined")
    original_feedback: UserFeedback = Field(description="Original feedback")
    categories: List[FeedbackCategory] = Field(description="Identified feedback categories")
    sentiment: str = Field(description="Overall sentiment: positive, negative, neutral")
    confidence: float = Field(description="Confidence in analysis (0-1)")
    refinement_actions: List[RefinementAction] = Field(description="Specific actions to take")
    summary: str = Field(description="Summary of required changes")


class FeedbackProcessor:
    """
    Processes user feedback to determine specific refinement actions for learning units.
    
    This class analyzes feedback using AI to extract actionable insights and
    interfaces with LangChain for intelligent interpretation.
    """
    
    def __init__(self, openai_client: OpenAI, model: str = "gpt-4o-mini") -> None:
        """
        Initialize the feedback processor.
        
        Args:
            openai_client: OpenAI client for AI processing
            model: OpenAI model to use for analysis
        """
        self.client = openai_client
        self.model = model
        
        # Prompt template for feedback analysis
        self.analysis_prompt = PromptTemplate(
            input_variables=["feedback_text", "unit_context"],
            template="""
            You are an expert learning experience analyst. Analyze the following user feedback 
            about a learning unit and determine specific refinement actions.

            Unit Context:
            {unit_context}

            User Feedback:
            {feedback_text}

            Please analyze this feedback and provide:
            1. The main categories of feedback (content, resources, tasks, difficulty, structure, objectives)
            2. Specific actionable changes needed
            3. Priority level for each change (1=low, 5=critical)
            4. Overall sentiment (positive, negative, neutral)

            Format your response as structured analysis focusing on actionable improvements.
            """
        )
    
    def process_feedback(self, feedback: UserFeedback, unit: LearningUnit) -> ProcessedFeedback:
        """
        Process user feedback and generate refinement actions.
        
        Args:
            feedback: UserFeedback object to analyze
            unit: LearningUnit being refined
            
        Returns:
            ProcessedFeedback with analysis and actions
        """
        # Prepare unit context
        unit_context = self._format_unit_context(unit)
        
        # Analyze feedback with AI
        analysis = self._analyze_feedback_with_ai(feedback.feedback_text, unit_context)
        
        # Extract categories
        categories = self._extract_categories(feedback.feedback_text)
        
        # Generate refinement actions
        actions = self._generate_refinement_actions(feedback, unit, analysis)
        
        # Determine sentiment and confidence
        sentiment = self._analyze_sentiment(feedback.feedback_text)
        confidence = self._calculate_confidence(feedback, analysis)
        
        # Create summary
        summary = self._generate_summary(actions)
        
        return ProcessedFeedback(
            unit_id=feedback.unit_id,
            original_feedback=feedback,
            categories=categories,
            sentiment=sentiment,
            confidence=confidence,
            refinement_actions=actions,
            summary=summary
        )
    
    def batch_process_feedback(self, feedback_list: List[UserFeedback], unit: LearningUnit) -> List[ProcessedFeedback]:
        """
        Process multiple feedback items for the same unit.
        
        Args:
            feedback_list: List of UserFeedback objects
            unit: LearningUnit being refined
            
        Returns:
            List of ProcessedFeedback objects
        """
        return [self.process_feedback(feedback, unit) for feedback in feedback_list]
    
    def consolidate_feedback(self, processed_feedback: List[ProcessedFeedback]) -> Dict[str, Any]:
        """
        Consolidate multiple feedback analyses into a unified refinement plan.
        
        Args:
            processed_feedback: List of ProcessedFeedback objects
            
        Returns:
            Consolidated refinement plan
        """
        if not processed_feedback:
            return {"actions": [], "summary": "No feedback to process"}
        
        # Combine all actions
        all_actions = []
        for pf in processed_feedback:
            all_actions.extend(pf.refinement_actions)
        
        # Group actions by type and priority
        actions_by_type = {}
        for action in all_actions:
            if action.action_type not in actions_by_type:
                actions_by_type[action.action_type] = []
            actions_by_type[action.action_type].append(action)
        
        # Sort by priority
        consolidated_actions = []
        for action_type, actions in actions_by_type.items():
            # Take highest priority action of each type
            top_action = max(actions, key=lambda a: a.priority)
            consolidated_actions.append(top_action)
        
        consolidated_actions.sort(key=lambda a: a.priority, reverse=True)
        
        return {
            "actions": consolidated_actions,
            "summary": f"Consolidated {len(all_actions)} feedback items into {len(consolidated_actions)} refinement actions",
            "feedback_count": len(processed_feedback),
            "categories_mentioned": list(set(cat for pf in processed_feedback for cat in pf.categories))
        }
    
    def _format_unit_context(self, unit: LearningUnit) -> str:
        """Format unit information for AI analysis."""
        context = f"""
        Unit: {unit.title}
        Description: {unit.description}
        
        Learning Objectives:
        {chr(10).join(f"- {obj}" for obj in unit.learning_objectives)}
        
        Current Resources ({len(unit.resources)}):
        {chr(10).join(f"- {r.title} ({r.type}): {r.description}" for r in unit.resources)}
        
        Current Tasks ({len(unit.engage_tasks)}):
        {chr(10).join(f"- {t.title} ({t.type}): {t.description}" for t in unit.engage_tasks)}
        """.strip()
        
        return context
    
    def _analyze_feedback_with_ai(self, feedback_text: str, unit_context: str) -> str:
        """Use AI to analyze feedback and suggest actions."""
        try:
            prompt = self.analysis_prompt.format(
                feedback_text=feedback_text,
                unit_context=unit_context
            )
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert learning experience analyst."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            return f"Analysis error: {str(e)}. Basic interpretation: User provided feedback about the learning unit."
    
    def _extract_categories(self, feedback_text: str) -> List[FeedbackCategory]:
        """Extract feedback categories from text using keyword analysis."""
        categories = []
        feedback_lower = feedback_text.lower()
        
        # Category keywords mapping
        category_keywords = {
            FeedbackCategory.CONTENT: ["content", "material", "information", "explanation", "concept", "theory"],
            FeedbackCategory.RESOURCES: ["resource", "video", "article", "reading", "link", "documentation"],
            FeedbackCategory.TASKS: ["task", "exercise", "practice", "assignment", "activity", "project"],
            FeedbackCategory.DIFFICULTY: ["difficult", "hard", "easy", "simple", "complex", "level", "challenging"],
            FeedbackCategory.STRUCTURE: ["structure", "organization", "order", "sequence", "flow", "layout"],
            FeedbackCategory.OBJECTIVES: ["objective", "goal", "outcome", "learning", "understand", "master"]
        }
        
        for category, keywords in category_keywords.items():
            if any(keyword in feedback_lower for keyword in keywords):
                categories.append(category)
        
        # Default to general if no specific categories found
        if not categories:
            categories.append(FeedbackCategory.GENERAL)
        
        return categories
    
    def _generate_refinement_actions(self, feedback: UserFeedback, unit: LearningUnit, analysis: str) -> List[RefinementAction]:
        """Generate specific refinement actions based on feedback analysis."""
        actions = []
        feedback_lower = feedback.feedback_text.lower()
        
        # Generate actions based on feedback categories
        if "resource" in feedback_lower:
            if "more" in feedback_lower or "additional" in feedback_lower:
                actions.append(RefinementAction(
                    action_type="add_resources",
                    target_component="resources",
                    description="Add additional learning resources to the unit",
                    priority=3,
                    details={"resource_types": ["video", "article"], "count": 2}
                ))
            elif "better" in feedback_lower or "different" in feedback_lower:
                actions.append(RefinementAction(
                    action_type="replace_resources",
                    target_component="resources",
                    description="Replace existing resources with better alternatives",
                    priority=4,
                    details={"replace_count": 1}
                ))
        
        if "task" in feedback_lower or "exercise" in feedback_lower:
            if "more" in feedback_lower:
                actions.append(RefinementAction(
                    action_type="add_tasks",
                    target_component="engage_tasks",
                    description="Add more engaging tasks to the unit",
                    priority=3,
                    details={"task_types": ["practice", "reflection"], "count": 1}
                ))
            elif "easier" in feedback_lower:
                actions.append(RefinementAction(
                    action_type="simplify_tasks",
                    target_component="engage_tasks",
                    description="Make existing tasks easier or more accessible",
                    priority=4,
                    details={"adjustment": "reduce_complexity"}
                ))
        
        if "difficult" in feedback_lower or "hard" in feedback_lower:
            actions.append(RefinementAction(
                action_type="reduce_difficulty",
                target_component="content",
                description="Reduce complexity and add more scaffolding",
                priority=5,
                details={"add_prerequisites": True, "simplify_language": True}
            ))
        
        if "easy" in feedback_lower or "simple" in feedback_lower:
            actions.append(RefinementAction(
                action_type="increase_difficulty",
                target_component="content",
                description="Add more challenging elements and advanced concepts",
                priority=3,
                details={"add_advanced_topics": True, "increase_depth": True}
            ))
        
        # General content improvements
        if "unclear" in feedback_lower or "confusing" in feedback_lower:
            actions.append(RefinementAction(
                action_type="clarify_content",
                target_component="description",
                description="Clarify unit description and learning objectives",
                priority=4,
                details={"rewrite_description": True, "add_examples": True}
            ))
        
        # Default action if no specific patterns found
        if not actions:
            actions.append(RefinementAction(
                action_type="general_review",
                target_component="unit",
                description="General review and improvement of unit content",
                priority=2,
                details={"review_all_components": True}
            ))
        
        return actions
    
    def _analyze_sentiment(self, feedback_text: str) -> str:
        """Analyze sentiment of feedback."""
        positive_words = ["good", "great", "excellent", "helpful", "clear", "useful", "love", "like"]
        negative_words = ["bad", "poor", "terrible", "confusing", "unclear", "difficult", "hate", "dislike"]
        
        feedback_lower = feedback_text.lower()
        positive_count = sum(1 for word in positive_words if word in feedback_lower)
        negative_count = sum(1 for word in negative_words if word in feedback_lower)
        
        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"
    
    def _calculate_confidence(self, feedback: UserFeedback, analysis: str) -> float:
        """Calculate confidence in the analysis."""
        # Simple heuristic based on feedback length and specificity
        feedback_length = len(feedback.feedback_text.split())
        specificity_indicators = len(feedback.specific_concerns) + len(feedback.suggested_changes)
        
        # Base confidence on length and specificity
        confidence = min(0.5 + (feedback_length / 100) + (specificity_indicators * 0.1), 1.0)
        
        return round(confidence, 2)
    
    def _generate_summary(self, actions: List[RefinementAction]) -> str:
        """Generate a summary of refinement actions."""
        if not actions:
            return "No specific refinement actions identified."
        
        high_priority = [a for a in actions if a.priority >= 4]
        medium_priority = [a for a in actions if a.priority == 3]
        low_priority = [a for a in actions if a.priority < 3]
        
        summary_parts = []
        
        if high_priority:
            summary_parts.append(f"High priority: {len(high_priority)} critical improvements needed")
        if medium_priority:
            summary_parts.append(f"Medium priority: {len(medium_priority)} moderate improvements")
        if low_priority:
            summary_parts.append(f"Low priority: {len(low_priority)} minor enhancements")
        
        return "; ".join(summary_parts)


def create_feedback_processor(api_key: Optional[str] = None, model: str = "gpt-4o-mini") -> FeedbackProcessor:
    """
    Factory function to create a FeedbackProcessor with OpenAI client.
    
    Args:
        api_key: OpenAI API key. If None, will try to get from environment
        model: OpenAI model to use for analysis
        
    Returns:
        Configured FeedbackProcessor instance
    """
    try:
        if api_key:
            client = OpenAI(api_key=api_key)
        else:
            client = OpenAI()
        
        return FeedbackProcessor(client, model)
    
    except Exception as e:
        raise RuntimeError(f"Failed to create FeedbackProcessor: {str(e)}") 