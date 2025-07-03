"""
FlowGenius Conversation Manager

This module provides conversation management for handling user feedback
during the unit refinement process using LangChain framework.
"""

from typing import Dict, List, Optional, Any, Tuple
from openai import OpenAI
from pydantic import BaseModel, Field
import uuid
import datetime

from ..models.project import LearningUnit


class UserFeedback(BaseModel):
    """Structured representation of user feedback for unit refinement."""
    unit_id: str = Field(description="ID of the unit being refined")
    feedback_text: str = Field(description="Raw user feedback")
    feedback_type: str = Field(default="general", description="Type of feedback")
    specific_concerns: List[str] = Field(default_factory=list, description="Specific concerns")
    suggested_changes: List[str] = Field(default_factory=list, description="Suggested changes")
    timestamp: str = Field(description="When feedback was provided")


class ConversationManager:
    """
    Manages conversational interactions for unit refinement using LangChain.
    """
    
    def __init__(self, openai_client: OpenAI, model: str = "gpt-4o-mini") -> None:
        self.client = openai_client
        self.model = model
        self.system_prompt = """
        You are a learning assistant helping to refine educational units based on user feedback.
        Identify specific concerns and extract concrete suggestions for improvement.
        """
    
    def start_refinement_session(self, unit: LearningUnit) -> str:
        """Start a new conversation session for refining a unit."""
        import uuid
        session_id = f"refine_{unit.id}_{uuid.uuid4().hex[:8]}"
        return session_id
    
    def process_user_feedback(self, session_id: str, feedback_text: str) -> Tuple[str, UserFeedback]:
        """Process user feedback and extract structured information."""
        from datetime import datetime
        
        # Simple response for now
        response = f"I understand your feedback: '{feedback_text}'. Let me help you refine this unit."
        
        # Create structured feedback
        feedback = UserFeedback(
            unit_id=session_id.split('_')[1],  # Extract unit_id from session_id
            feedback_text=feedback_text,
            feedback_type="general",
            timestamp=datetime.now().isoformat()
        )
        
        return response, feedback


def create_conversation_manager(api_key: Optional[str] = None, model: str = "gpt-4o-mini") -> ConversationManager:
    """Factory function to create a ConversationManager with OpenAI client."""
    try:
        if api_key:
            client = OpenAI(api_key=api_key)
        else:
            client = OpenAI()
        
        return ConversationManager(client, model)
    
    except Exception as e:
        raise RuntimeError(f"Failed to create ConversationManager: {str(e)}") 