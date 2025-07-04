"""
FlowGenius Conversation Manager

This module provides conversation management for handling user feedback
during the unit refinement process using LangChain for message management.
"""

from typing import Dict, List, Optional, Any, Tuple, Callable
import uuid
import logging
import re
import os

from langchain_core.messages import HumanMessage, AIMessage, BaseMessage, SystemMessage, trim_messages
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

from ..models.project import LearningUnit, UserFeedback
from ..utils import get_timestamp

logger = logging.getLogger(__name__)


class ConversationSession:
    """Represents an active conversation session with message history."""
    
    def __init__(self, session_id: str, unit_id: str, unit: LearningUnit) -> None:
        """
        Initialize a conversation session with message history.
        
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
        
        # Store conversation messages directly instead of using deprecated ConversationBufferMemory
        self.messages: List[BaseMessage] = []


class ConversationManager:
    """
    Manages conversation sessions with learners using LangChain.
    
    This class handles the creation and management of refinement sessions,
    processes user feedback using LangChain messages, and generates appropriate responses.
    """
    
    def __init__(self, openai_client=None, model: str = "gpt-4o-mini", timestamp_provider: Optional[Callable[[], str]] = None) -> None:
        """
        Initialize the conversation manager with LangChain components.
        
        Args:
            openai_client: OpenAI client for LLM operations (deprecated, use api_key instead)
            model: Model name for chat completions
            timestamp_provider: Optional function to provide timestamps.
                Defaults to utils.get_timestamp().
        """
        # For LangChain, we'll use ChatOpenAI directly
        self.chat_model = None
        if openai_client and hasattr(openai_client, 'api_key'):
            # Extract API key from OpenAI client if provided
            os.environ["OPENAI_API_KEY"] = openai_client.api_key
            self.chat_model = ChatOpenAI(model=model, temperature=0.7)
        elif "OPENAI_API_KEY" in os.environ:
            self.chat_model = ChatOpenAI(model=model, temperature=0.7)
            
        self.model = model
        self._timestamp_provider = timestamp_provider or get_timestamp
        self.active_sessions: Dict[str, ConversationSession] = {}
        
        # System prompt for the conversation
        self.system_message = SystemMessage(
            content="""You are an AI learning assistant helping users refine and improve their learning units. 
            You analyze feedback, ask clarifying questions, and help users articulate specific improvements they want to make. 
            Focus on understanding user needs and converting feedback into actionable refinement suggestions."""
        )
        
        # Create the prompt template with memory placeholder
        self.prompt_template = ChatPromptTemplate.from_messages([
            self.system_message,
            MessagesPlaceholder(variable_name="chat_history"),
            HumanMessage(content="{input}")
        ])
    
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
        
        # Create a new session with message history
        session = ConversationSession(session_id, unit.id, unit)
        self.active_sessions[session_id] = session
        
        logger.info(f"Started refinement session {session_id} for unit {unit.id}")
        return session_id
    
    def process_user_feedback(self, session_id: str, feedback_text: str) -> Tuple[str, UserFeedback]:
        """
        Process user feedback from a session using LangChain messages.
        
        Args:
            session_id: Session identifier
            feedback_text: Raw user feedback text
            
        Returns:
            Tuple of (response_string, UserFeedback_object)
        """
        # Get the session
        session = self.active_sessions.get(session_id)
        if not session:
            # Create a minimal session if it doesn't exist
            unit_id = self._extract_unit_id_from_session(session_id)
            response = "Session not found. Please start a new refinement session."
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
            return response, feedback
        
        # Create structured feedback
        feedback = UserFeedback(
            unit_id=session.unit_id,
            feedback_text=feedback_text,
            feedback_type="general",
            specific_concerns=self._extract_concerns(feedback_text),
            suggestions=self._extract_suggestions(feedback_text),
            suggested_changes=[],
            priority="medium",
            timestamp=self._timestamp_provider()
        )
        
        # Generate response using LangChain
        response = self._generate_langchain_response(session, feedback_text)
        
        # Store feedback in session history
        session.feedback_history.append(feedback)
        
        # Update message history
        session.messages.append(HumanMessage(content=feedback_text))
        session.messages.append(AIMessage(content=response))
        
        return response, feedback
    
    def _generate_langchain_response(self, session: ConversationSession, input_text: str) -> str:
        """
        Generate a response using LangChain with conversation history.
        
        Args:
            session: The conversation session
            input_text: User input text
            
        Returns:
            AI response string
        """
        if not self.chat_model:
            # Fallback response if no chat model configured
            return self._generate_fallback_response(input_text)
        
        try:
            # Trim messages to keep only recent context (max 10 messages)
            trimmed_messages = trim_messages(
                session.messages,
                token_counter=len,  # Simple message count
                max_tokens=10,  # Keep last 10 messages
                strategy="last",
                start_on="human",
                include_system=True,
                allow_partial=False
            )
            
            # Create a simple chain with the chat model
            chain = self.prompt_template | self.chat_model
            
            # Invoke the chain with the input and chat history
            response = chain.invoke({
                "chat_history": trimmed_messages,
                "input": input_text
            })
            
            # Extract content from the response
            if hasattr(response, 'content'):
                return response.content.strip()
            else:
                return str(response).strip()
                
        except Exception as e:
            logger.error(f"Error generating LangChain response: {e}", exc_info=True)
            return self._generate_fallback_response(input_text)
    
    def _generate_fallback_response(self, feedback_text: str) -> str:
        """
        Generate a fallback response without LLM.
        
        Args:
            feedback_text: User feedback text
            
        Returns:
            Fallback response string
        """
        # Analyze feedback sentiment
        sentiment = self._analyze_sentiment(feedback_text)
        
        # Generate appropriate response based on sentiment and content
        if sentiment == "positive":
            response = "I understand your feedback. Thank you for your positive input! "
        elif sentiment == "negative":
            response = "I understand your feedback about your concerns. "
        else:
            response = "I understand your feedback. "
        
        # Add specific acknowledgment
        concerns = self._extract_concerns(feedback_text)
        suggestions = self._extract_suggestions(feedback_text)
        
        if concerns:
            response += f"I've noted your concerns about: {', '.join(concerns)}. "
        
        if suggestions:
            response += f"Your suggestions about {', '.join(suggestions)} are valuable. "
        
        response += "I'll work on refining the unit based on your input."
        
        return response
    
    def _extract_concerns(self, text: str) -> List[str]:
        """Extract specific concerns from feedback text."""
        concerns = []
        concern_keywords = ["concern", "problem", "issue", "difficult", "confusing", "unclear"]
        
        text_lower = text.lower()
        for keyword in concern_keywords:
            if keyword in text_lower:
                # Simple extraction - in real implementation, use NLP
                concerns.append(keyword)
        
        return concerns[:3]  # Limit to 3 concerns
    
    def _extract_suggestions(self, text: str) -> List[str]:
        """Extract suggestions from feedback text."""
        suggestions = []
        suggestion_keywords = ["suggest", "recommend", "should", "could", "would be better", "improve"]
        
        text_lower = text.lower()
        for keyword in suggestion_keywords:
            if keyword in text_lower:
                suggestions.append(keyword)
        
        return suggestions[:3]  # Limit to 3 suggestions
    
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
        session = self.active_sessions.get(session_id)
        if not session:
            return None
        
        # Return session info including message count
        return {
            "session_id": session.session_id,
            "unit_id": session.unit_id,
            "created_at": session.created_at,
            "feedback_count": len(session.feedback_history),
            "message_count": len(session.messages)
        }
    
    def end_session(self, session_id: str) -> bool:
        """
        End a conversation session.
        
        Args:
            session_id: Session identifier to end
            
        Returns:
            True if session was ended, False if not found
        """
        if session_id in self.active_sessions:
            # Clear messages before deletion
            session = self.active_sessions[session_id]
            session.messages.clear()
            
            del self.active_sessions[session_id]
            logger.info(f"Ended session {session_id}")
            return True
        return False


def create_conversation_manager(api_key: Optional[str] = None, model: str = "gpt-4o-mini") -> ConversationManager:
    """
    Factory function to create a ConversationManager with LangChain.
    
    Args:
        api_key: Optional OpenAI API key. If not provided, will use environment variable.
        model: Model name for the chat model
        
    Returns:
        ConversationManager instance
        
    Raises:
        RuntimeError: If ConversationManager creation fails
    """
    try:
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key
        elif "OPENAI_API_KEY" not in os.environ:
            raise RuntimeError("OpenAI API key not provided and OPENAI_API_KEY environment variable not set")
        
        return ConversationManager(openai_client=None, model=model)
    except Exception as e:
        logger.error(f"Failed to create ConversationManager: {e}", exc_info=True)
        raise RuntimeError(f"Failed to create ConversationManager: {e}") from e

 