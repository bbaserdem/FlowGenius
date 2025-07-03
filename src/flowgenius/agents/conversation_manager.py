"""
FlowGenius Conversation Manager

This module provides conversation management for handling user feedback
during the unit refinement process using LangChain framework.
"""

from typing import Dict, List, Optional, Any, Tuple, Callable
from openai import OpenAI
from pydantic import BaseModel, Field
import uuid
import datetime
import logging
import re

from ..models.project import LearningUnit
from ..models.settings import DefaultSettings

logger = logging.getLogger(__name__)


class UserFeedback(BaseModel):
    """Structured representation of user feedback for unit refinement."""
    unit_id: str = Field(description="ID of the unit being refined")
    feedback_text: str = Field(description="Raw user feedback")
    feedback_type: str = Field(default="general", description="Type of feedback")
    specific_concerns: List[str] = Field(default_factory=list, description="Specific issues identified")
    suggestions: List[str] = Field(default_factory=list, description="Suggested improvements")
    suggested_changes: List[str] = Field(default_factory=list, description="Specific suggested changes")
    priority: str = Field(default="medium", description="Priority level")
    timestamp: Optional[str] = Field(default=None, description="Timestamp of feedback")


class ConversationManager:
    """Manages conversation flow and feedback processing for learning units."""
    
    def __init__(
        self,
        openai_client: OpenAI,
        model: str = DefaultSettings.DEFAULT_MODEL,
        timestamp_provider: Optional[Callable[[], str]] = None
    ) -> None:
        """
        Initialize the conversation manager.
        
        Args:
            openai_client: Configured OpenAI client.
            model: OpenAI model to use for conversations.
            timestamp_provider: A callable that returns an ISO format timestamp string.
                                Defaults to datetime.datetime.now().isoformat().
        """
        self.client = openai_client
        self.model = model
        self.system_prompt = """You are an AI learning assistant helping users refine and improve their learning units. 
        You analyze feedback, ask clarifying questions, and help users articulate specific improvements they want to make. 
        Focus on understanding user needs and converting feedback into actionable refinement suggestions."""
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self._timestamp_provider = timestamp_provider or (lambda: datetime.datetime.now().isoformat())
    
    def start_refinement_session(self, unit: LearningUnit) -> str:
        """
        Start a new refinement session for a learning unit.
        
        Args:
            unit: The learning unit to refine
            
        Returns:
            Session ID string in format 'refine_{unit.id}_{uuid}'
        """
        session_uuid = uuid.uuid4().hex
        session_id = f"refine_{unit.id}_{session_uuid}"
        
        # Store session information for later retrieval
        self.active_sessions[session_id] = {
            "unit_id": unit.id,
            "unit": unit,
            "created_at": self._get_timestamp(),
            "feedback_history": []
        }
        
        logger.info(f"Started refinement session {session_id} for unit {unit.id}")
        return session_id
    
    def process_user_feedback(self, session_id: str, feedback_text: str) -> Tuple[str, UserFeedback]:
        """
        Process user feedback from a session.
        
        Args:
            session_id: Session identifier
            feedback_text: Raw user feedback text
            
        Returns:
            Tuple of (response_string, UserFeedback_object)
        """
        # Extract unit_id from session_id
        unit_id = self._extract_unit_id_from_session(session_id)
        
        # Create structured feedback
        feedback = UserFeedback(
            unit_id=unit_id,
            feedback_text=feedback_text,
            feedback_type="general",
            specific_concerns=[],
            suggestions=[],
            suggested_changes=[],
            priority="medium",
            timestamp=self._get_timestamp()
        )
        
        # Generate response
        response = self._generate_response(feedback)
        
        # Store feedback in session history
        if session_id in self.active_sessions:
            self.active_sessions[session_id]["feedback_history"].append(feedback)
        
        return response, feedback
    
    def _extract_unit_id_from_session(self, session_id: str) -> str:
        """
        Extract unit ID from session ID.
        
        Args:
            session_id: Session ID in format 'refine_{unit_id}_{uuid}'
            
        Returns:
            Extracted unit ID
        """
        try:
            # Regex to capture everything between "refine_" and the final underscore
            match = re.match(r"^refine_(.+)_[^_]+$", session_id)
            if match:
                return match.group(1)
            
            # Fallback for older or different formats
            if session_id.startswith("refine_"):
                parts = session_id.split("_")
                if len(parts) >= 3:
                    return "_".join(parts[1:-1])

            # Fallback: try to find any recognizable unit pattern
            match = re.search(r"unit-[\w-]+", session_id)
            if match:
                return match.group(0)
            
            # Final fallback
            return "unknown-unit"
        except Exception:
            return "unknown-unit"
    
    def _generate_response(self, feedback: UserFeedback) -> str:
        """
        Generate a response to user feedback.
        
        Args:
            feedback: Structured user feedback
            
        Returns:
            Response string
        """
        # Simple response generation for now
        # In a real implementation, this would use the OpenAI client
        
        base_response = "I understand your feedback"
        
        if not feedback.feedback_text.strip():
            return f"{base_response}. Could you provide more specific details about what you'd like to improve?"
        
        if "example" in feedback.feedback_text.lower():
            return f"{base_response} about needing more examples. I'll help you add practical examples to make the concepts clearer."
        elif "difficult" in feedback.feedback_text.lower():
            return f"{base_response} about the difficulty level. Let's work together to adjust the complexity."
        elif "resource" in feedback.feedback_text.lower():
            return f"{base_response} about resources. I can help you add more learning materials."
        else:
            return f"{base_response}. Let me help you improve this unit based on your suggestions."

    def _get_timestamp(self) -> str:
        """
        Get current timestamp using the configured provider.
        
        Returns:
            ISO format timestamp string
        """
        return self._timestamp_provider()


def create_conversation_manager(api_key: Optional[str] = None, model: str = "gpt-4o-mini") -> ConversationManager:
    """
    Factory function to create a ConversationManager with OpenAI client.
    
    Args:
        api_key: OpenAI API key (optional)
        model: OpenAI model to use
        
    Returns:
        Configured ConversationManager instance
        
    Raises:
        RuntimeError: If OpenAI client creation fails
    """
    try:
        if api_key:
            client = OpenAI(api_key=api_key)
        else:
            client = OpenAI()  # Will use environment variable
            
        return ConversationManager(client, model=model)
    except Exception as e:
        raise RuntimeError(f"Failed to create ConversationManager: {e}") 