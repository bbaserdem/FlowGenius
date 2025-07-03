"""
FlowGenius Conversation Manager

This module provides conversation management for handling user feedback
during the unit refinement process.
"""

from typing import Dict, List, Optional, Any, Tuple, Callable
import uuid
import logging
import re

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from ..models.project import LearningUnit, UserFeedback
from ..utils import get_timestamp

logger = logging.getLogger(__name__)


class ConversationSession:
    """Represents an active conversation session."""
    
    def __init__(self, session_id: str, unit_id: str, unit: LearningUnit) -> None:
        """
        Initialize a conversation session.
        
        Args:
            session_id: Unique session identifier
            unit_id: ID of the learning unit
            unit: The learning unit instance
        """
        self.session_id = session_id
        self.unit_id = unit_id
        self.unit = unit
        self.created_at = get_timestamp()
        self.feedback_history: List[UserFeedback] = []


class ConversationManager:
    """
    Manages conversation sessions with learners.
    
    This class handles the creation and management of refinement sessions,
    processes user feedback, and generates appropriate responses.
    """
    
    def __init__(self, openai_client=None, model: str = "gpt-4o-mini", timestamp_provider: Optional[Callable[[], str]] = None) -> None:
        """
        Initialize the conversation manager.
        
        Args:
            openai_client: OpenAI client (kept for backward compatibility)
            model: Model name (kept for backward compatibility)
            timestamp_provider: Optional function to provide timestamps.
                Defaults to utils.get_timestamp().
        """
        self.client = openai_client  # Keep for backward compatibility
        self.model = model  # Keep for backward compatibility
        self.system_prompt = """You are an AI learning assistant helping users refine and improve their learning units. 
        You analyze feedback, ask clarifying questions, and help users articulate specific improvements they want to make. 
        Focus on understanding user needs and converting feedback into actionable refinement suggestions."""
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self._timestamp_provider = timestamp_provider or get_timestamp
    
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
            "created_at": self._timestamp_provider(),
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
            timestamp=self._timestamp_provider()
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
        except (AttributeError, TypeError, ValueError):
            return "unknown-unit"
    
    def _generate_response(self, feedback: UserFeedback) -> str:
        """
        Generate a response to user feedback.
        
        Args:
            feedback: Structured user feedback
            
        Returns:
            Response string
        """
        # Analyze feedback sentiment
        sentiment = self._analyze_sentiment(feedback.feedback_text)
        
        # Generate appropriate response based on sentiment and content
        if sentiment == "positive":
            response = "I understand your feedback. Thank you for your positive input! "
        elif sentiment == "negative":
            response = "I understand your feedback about your concerns. "
        else:
            response = "I understand your feedback. "
        
        # Add specific acknowledgment
        if feedback.specific_concerns:
            response += f"I've noted your concerns about: {', '.join(feedback.specific_concerns)}. "
        
        if feedback.suggestions:
            response += f"Your suggestions about {', '.join(feedback.suggestions)} are valuable. "
        
        response += "I'll work on refining the unit based on your input."
        
        return response
    
    def _analyze_sentiment(self, text: str) -> str:
        """
        Simple sentiment analysis of feedback text.
        
        Args:
            text: Feedback text to analyze
            
        Returns:
            Sentiment string: 'positive', 'negative', or 'neutral'
        """
        positive_words = ["good", "great", "excellent", "helpful", "clear", "useful", "love", "like"]
        negative_words = ["bad", "poor", "terrible", "confusing", "unclear", "difficult", "hate", "dislike"]
        
        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session information dictionary or None if not found
        """
        return self.active_sessions.get(session_id)
    
    def end_session(self, session_id: str) -> bool:
        """
        End a conversation session.
        
        Args:
            session_id: Session identifier to end
            
        Returns:
            True if session was ended, False if not found
        """
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            logger.info(f"Ended session {session_id}")
            return True
        return False


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
        if OpenAI is None:
            raise ImportError("OpenAI package not installed")
        
        if api_key:
            client = OpenAI(api_key=api_key)
        else:
            client = OpenAI()  # Will use environment variable
            
        return ConversationManager(client, model=model)
    except ImportError as e:
        raise RuntimeError(f"Failed to create ConversationManager: OpenAI package not installed") from e
    except Exception as e:
        logger.error(f"Failed to create ConversationManager: {e}", exc_info=True)
        raise RuntimeError(f"Failed to create ConversationManager: {e}") from e

 