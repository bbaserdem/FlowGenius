"""
Tests for the Conversation Manager component.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from typing import Any
import os

from flowgenius.agents.conversation_manager import (
    ConversationManager,
    UserFeedback,
    create_conversation_manager
)


class TestUserFeedback:
    """Test cases for UserFeedback model."""

    def test_user_feedback_creation(self) -> None:
        """Test UserFeedback model creation."""
        feedback = UserFeedback(
            unit_id="unit-1",
            feedback_text="This unit needs more examples",
            feedback_type="content",
            specific_concerns=["lacks examples"],
            suggested_changes=["add code examples"],
            timestamp="2024-01-01T10:00:00"
        )
        
        assert feedback.unit_id == "unit-1"
        assert feedback.feedback_text == "This unit needs more examples"
        assert feedback.feedback_type == "content"
        assert feedback.specific_concerns == ["lacks examples"]
        assert feedback.suggested_changes == ["add code examples"]
        assert feedback.timestamp == "2024-01-01T10:00:00"

    def test_user_feedback_defaults(self) -> None:
        """Test UserFeedback with default values."""
        feedback = UserFeedback(
            unit_id="unit-1",
            feedback_text="Good unit",
            timestamp="2024-01-01T10:00:00"
        )
        
        assert feedback.feedback_type == "general"
        assert feedback.specific_concerns == []
        assert feedback.suggested_changes == []


class TestConversationManager:
    """Test cases for ConversationManager."""

    def test_init(self, mock_openai_client: Mock) -> None:
        """Test conversation manager initialization."""
        # Mock environment variable for OpenAI API key
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            manager = ConversationManager(mock_openai_client, model="gpt-4")
            
            assert manager.model == "gpt-4"
            assert manager.chat_model is not None  # LangChain ChatOpenAI model
            assert hasattr(manager, 'system_message')
            assert "learning assistant" in manager.system_message.content.lower()

    def test_start_refinement_session(self, mock_openai_client: Mock, sample_learning_unit: Any) -> None:
        """Test starting a refinement session."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            manager = ConversationManager(mock_openai_client)
            
            with patch('uuid.uuid4') as mock_uuid:
                mock_uuid.return_value.hex = "12345678"
                
                session_id = manager.start_refinement_session(sample_learning_unit)
                
                assert session_id.startswith("refine_unit-1_")
                assert session_id in manager.active_sessions
                # Check that the session has LangChain memory
                assert hasattr(manager.active_sessions[session_id], 'memory')

    def test_process_user_feedback_basic(self, mock_openai_client: Mock, sample_learning_unit: Any) -> None:
        """Test basic feedback processing."""
        timestamp = "2024-01-01T10:00:00"
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            manager = ConversationManager(
                mock_openai_client,
                timestamp_provider=lambda: timestamp
            )
            
            # Start a session first
            with patch('uuid.uuid4') as mock_uuid:
                mock_uuid.return_value.hex = "12345678"
                session_id = manager.start_refinement_session(sample_learning_unit)
                
                response, feedback = manager.process_user_feedback(
                    session_id,
                    "This unit needs more examples"
                )
                
                # The response should acknowledge the feedback
                assert response is not None and len(response) > 0
                assert isinstance(feedback, UserFeedback)
                assert feedback.unit_id == sample_learning_unit.id
                assert feedback.feedback_text == "This unit needs more examples"
                assert feedback.feedback_type == "general"
                assert feedback.timestamp == timestamp

    def test_process_user_feedback_invalid_session(self, mock_openai_client: Mock) -> None:
        """Test feedback processing with invalid session ID."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            manager = ConversationManager(mock_openai_client)
            
            # Should not raise exception, just extract unit_id from session_id
            response, feedback = manager.process_user_feedback(
                "invalid_session",
                "Some feedback"
            )
            
            assert response is not None
            assert isinstance(feedback, UserFeedback)

    def test_process_user_feedback_with_controlled_datetime(self, mock_openai_client: Mock) -> None:
        """Test feedback processing with controlled datetime."""
        timestamp = "2024-01-01T10:00:00"
        
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            # The timestamp_provider is now injected directly
            manager = ConversationManager(
                mock_openai_client,
                timestamp_provider=lambda: timestamp
            )
            
            response, feedback = manager.process_user_feedback(
                "refine_unit-1_12345678",
                "Add more resources"
            )
            
            assert feedback.timestamp == timestamp

    def test_feedback_extraction_from_session_id(self, mock_openai_client: Mock) -> None:
        """Test that unit_id is correctly extracted from session_id."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            manager = ConversationManager(mock_openai_client)
            
            test_cases = [
                ("refine_unit-1_12345678", "unit-1"),
                ("refine_unit-abc_87654321", "unit-abc"),
                ("refine_test-unit_99999999", "test-unit"),
                ("refine_unit_with_underscores_1_uuid", "unit_with_underscores_1"),
            ]
            
            for session_id, expected_unit_id in test_cases:
                _, feedback = manager.process_user_feedback(session_id, "Test feedback")
                assert feedback.unit_id == expected_unit_id

    def test_response_generation_with_different_feedback(self, mock_openai_client: Mock) -> None:
        """Test that responses are generated for different types of feedback."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            manager = ConversationManager(mock_openai_client)
            
            feedback_texts = [
                "This unit is too difficult",
                "I need more resources",
                "The tasks are unclear",
                "Great unit overall"
            ]
            
            for feedback_text in feedback_texts:
                response, feedback = manager.process_user_feedback(
                    "refine_unit-1_12345678",
                    feedback_text
                )
                
                assert response is not None
                assert len(response) > 0
                assert feedback.feedback_text == feedback_text


class TestFactoryFunction:
    """Test cases for factory function."""

    def test_create_conversation_manager_with_api_key(self) -> None:
        """Test creating conversation manager with API key."""
        with patch.dict('os.environ', {}, clear=True):  # Clear environment
            manager = create_conversation_manager(api_key="test-key", model="gpt-4")
            
            assert isinstance(manager, ConversationManager)
            assert manager.model == "gpt-4"
            # Check that the API key was set in environment
            assert os.environ.get("OPENAI_API_KEY") == "test-key"

    def test_create_conversation_manager_with_env_var(self) -> None:
        """Test creating conversation manager with environment variable."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'env-test-key'}):
            manager = create_conversation_manager()
            
            assert isinstance(manager, ConversationManager)
            assert manager.model == "gpt-4o-mini"

    def test_create_conversation_manager_without_api_key(self) -> None:
        """Test creating conversation manager without API key should fail."""
        with patch.dict('os.environ', {}, clear=True):  # Clear environment
            with pytest.raises(RuntimeError, match="OpenAI API key not provided"):
                create_conversation_manager()


class TestConversationManagerIntegration:
    """Integration test cases for ConversationManager."""

    def test_complete_feedback_session_workflow(self, mock_openai_client: Mock, sample_learning_unit: Any) -> None:
        """Test a complete feedback session workflow."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            manager = ConversationManager(mock_openai_client)
            
            # Start session
            with patch('uuid.uuid4') as mock_uuid:
                mock_uuid.return_value.hex = "12345678"
                session_id = manager.start_refinement_session(sample_learning_unit)
            
            # Process multiple feedback items
            feedback_items = [
                "This unit needs more examples",
                "The difficulty is too high",
                "Add more video resources"
            ]
            
            collected_feedback = []
            for feedback_text in feedback_items:
                response, feedback = manager.process_user_feedback(session_id, feedback_text)
                collected_feedback.append(feedback)
                
                assert response is not None
                assert isinstance(feedback, UserFeedback)
                assert feedback.unit_id == sample_learning_unit.id
                assert feedback.feedback_text == feedback_text
            
            # Check session has feedback history
            assert len(manager.active_sessions[session_id].feedback_history) == 3
            assert all(f.unit_id == sample_learning_unit.id for f in collected_feedback)

    def test_feedback_processing_with_empty_input(self, mock_openai_client: Mock) -> None:
        """Test feedback processing with edge cases."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            manager = ConversationManager(mock_openai_client)
            
            # Test with empty feedback
            response, feedback = manager.process_user_feedback(
                "refine_unit-1_12345678",
                ""
            )
            
            assert response is not None
            assert feedback.feedback_text == ""
            assert feedback.unit_id == "unit-1"

    def test_feedback_processing_with_whitespace(self, mock_openai_client: Mock) -> None:
        """Test feedback processing with whitespace-only input."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            manager = ConversationManager(mock_openai_client)
            
            response, feedback = manager.process_user_feedback(
                "refine_unit-1_12345678",
                "   \n\t   "
            )
            
            assert response is not None
            assert feedback.feedback_text == "   \n\t   "
            assert feedback.unit_id == "unit-1" 