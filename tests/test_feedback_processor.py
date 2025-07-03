"""
Tests for the Feedback Processor component.
"""

import pytest
from unittest.mock import Mock, patch
from typing import Any

from flowgenius.agents.feedback_processor import (
    FeedbackProcessor,
    FeedbackCategory,
    RefinementAction,
    ProcessedFeedback,
    create_feedback_processor
)
from flowgenius.agents.conversation_manager import UserFeedback


class TestFeedbackCategory:
    """Test cases for FeedbackCategory enum."""

    def test_feedback_categories(self) -> None:
        """Test that all expected categories exist."""
        expected_categories = [
            "content", "resources", "tasks", "difficulty", "general"
        ]
        
        for category in expected_categories:
            assert hasattr(FeedbackCategory, category.upper())
            assert getattr(FeedbackCategory, category.upper()) == category


class TestRefinementAction:
    """Test cases for RefinementAction model."""

    def test_refinement_action_creation(self) -> None:
        """Test RefinementAction model creation."""
        action = RefinementAction(
            action_type="add_resources",
            target_component="resources",
            description="Add more video resources",
            priority=4,
            details={"count": 2, "types": ["video"]}
        )
        
        assert action.action_type == "add_resources"
        assert action.target_component == "resources"
        assert action.description == "Add more video resources"
        assert action.priority == 4
        assert action.details == {"count": 2, "types": ["video"]}

    def test_refinement_action_defaults(self) -> None:
        """Test RefinementAction with default values."""
        action = RefinementAction(
            action_type="test_action",
            target_component="test_component",
            description="Test description",
            priority=3
        )
        
        assert action.details == {}


class TestProcessedFeedback:
    """Test cases for ProcessedFeedback model."""

    def test_processed_feedback_creation(self) -> None:
        """Test ProcessedFeedback model creation."""
        user_feedback = UserFeedback(
            unit_id="unit-1",
            feedback_text="Test feedback",
            timestamp="2024-01-01T10:00:00"
        )
        
        action = RefinementAction(
            action_type="test_action",
            target_component="test_component",
            description="Test action",
            priority=3
        )
        
        processed = ProcessedFeedback(
            unit_id="unit-1",
            original_feedback=user_feedback,
            categories=[FeedbackCategory.CONTENT],
            sentiment="positive",
            refinement_actions=[action],
            summary="Test summary"
        )
        
        assert processed.unit_id == "unit-1"
        assert processed.original_feedback == user_feedback
        assert processed.categories == [FeedbackCategory.CONTENT]
        assert processed.sentiment == "positive"
        assert len(processed.refinement_actions) == 1
        assert processed.summary == "Test summary"


class TestFeedbackProcessor:
    """Test cases for FeedbackProcessor."""

    def test_init(self, mock_openai_client: Mock) -> None:
        """Test feedback processor initialization."""
        processor = FeedbackProcessor(mock_openai_client, model="gpt-4")
        
        assert processor.client == mock_openai_client
        assert processor.model == "gpt-4"

    def test_extract_categories_resources(self, mock_openai_client: Mock) -> None:
        """Test category extraction for resource-related feedback."""
        processor = FeedbackProcessor(mock_openai_client)
        
        feedback_texts = [
            "Need more video resources",
            "The articles are not helpful",
            "Add reading materials"
        ]
        
        for text in feedback_texts:
            categories = processor._extract_categories(text)
            assert FeedbackCategory.RESOURCES in categories

    def test_extract_categories_tasks(self, mock_openai_client: Mock) -> None:
        """Test category extraction for task-related feedback."""
        processor = FeedbackProcessor(mock_openai_client)
        
        feedback_texts = [
            "The tasks are too easy",
            "Need more practice exercises",
            "Assignment is unclear",
            "Activities don't match content"
        ]
        
        for text in feedback_texts:
            categories = processor._extract_categories(text)
            assert FeedbackCategory.TASKS in categories

    def test_extract_categories_difficulty(self, mock_openai_client: Mock) -> None:
        """Test category extraction for difficulty-related feedback."""
        processor = FeedbackProcessor(mock_openai_client)
        
        feedback_texts = [
            "This is too difficult",
            "Unit is too hard for beginners",
            "Make it easier please",
            "Too simple for my level",
            "More challenging content needed"
        ]
        
        for text in feedback_texts:
            categories = processor._extract_categories(text)
            assert FeedbackCategory.DIFFICULTY in categories

    def test_extract_categories_content(self, mock_openai_client: Mock) -> None:
        """Test category extraction for content-related feedback."""
        processor = FeedbackProcessor(mock_openai_client)
        
        feedback_texts = [
            "The content is confusing",
            "Need better explanations",
            "Material is outdated",
            "Information is incomplete"
        ]
        
        for text in feedback_texts:
            categories = processor._extract_categories(text)
            assert FeedbackCategory.CONTENT in categories

    def test_extract_categories_multiple(self, mock_openai_client: Mock) -> None:
        """Test category extraction for feedback with multiple categories."""
        processor = FeedbackProcessor(mock_openai_client)
        
        feedback_text = "The content is too difficult and needs more video resources and practice tasks"
        categories = processor._extract_categories(feedback_text)
        
        assert FeedbackCategory.CONTENT in categories
        assert FeedbackCategory.DIFFICULTY in categories
        assert FeedbackCategory.RESOURCES in categories
        assert FeedbackCategory.TASKS in categories

    def test_extract_categories_default_general(self, mock_openai_client: Mock) -> None:
        """Test that general category is used when no specific categories match."""
        processor = FeedbackProcessor(mock_openai_client)
        
        feedback_text = "Overall good unit"
        categories = processor._extract_categories(feedback_text)
        
        assert categories == [FeedbackCategory.GENERAL]

    def test_generate_refinement_actions_add_resources(self, mock_openai_client: Mock, sample_learning_unit: Any) -> None:
        """Test refinement action generation for adding resources."""
        processor = FeedbackProcessor(mock_openai_client)
        
        feedback = UserFeedback(
            unit_id="unit-1",
            feedback_text="Need more resources for this topic",
            timestamp="2024-01-01T10:00:00"
        )
        
        actions = processor._generate_refinement_actions(feedback, sample_learning_unit, "analysis")
        
        resource_actions = [a for a in actions if a.action_type == "add_resources"]
        assert len(resource_actions) > 0
        assert resource_actions[0].target_component == "resources"
        assert resource_actions[0].priority >= 3

    def test_generate_refinement_actions_add_tasks(self, mock_openai_client: Mock, sample_learning_unit: Any) -> None:
        """Test refinement action generation for adding tasks."""
        processor = FeedbackProcessor(mock_openai_client)
        
        feedback = UserFeedback(
            unit_id="unit-1",
            feedback_text="Need more practice tasks",
            timestamp="2024-01-01T10:00:00"
        )
        
        actions = processor._generate_refinement_actions(feedback, sample_learning_unit, "analysis")
        
        task_actions = [a for a in actions if a.action_type == "add_tasks"]
        assert len(task_actions) > 0
        assert task_actions[0].target_component == "engage_tasks"
        assert task_actions[0].priority >= 3

    def test_generate_refinement_actions_reduce_difficulty(self, mock_openai_client: Mock, sample_learning_unit: Any) -> None:
        """Test refinement action generation for reducing difficulty."""
        processor = FeedbackProcessor(mock_openai_client)
        
        feedback = UserFeedback(
            unit_id="unit-1",
            feedback_text="This unit is too difficult for beginners",
            timestamp="2024-01-01T10:00:00"
        )
        
        actions = processor._generate_refinement_actions(feedback, sample_learning_unit, "analysis")
        
        difficulty_actions = [a for a in actions if a.action_type == "reduce_difficulty"]
        assert len(difficulty_actions) > 0
        assert difficulty_actions[0].target_component == "content"
        assert difficulty_actions[0].priority == 5  # High priority

    def test_generate_refinement_actions_increase_difficulty(self, mock_openai_client: Mock, sample_learning_unit: Any) -> None:
        """Test refinement action generation for increasing difficulty."""
        processor = FeedbackProcessor(mock_openai_client)
        
        feedback = UserFeedback(
            unit_id="unit-1",
            feedback_text="This unit is too easy, make it more challenging",
            timestamp="2024-01-01T10:00:00"
        )
        
        actions = processor._generate_refinement_actions(feedback, sample_learning_unit, "analysis")
        
        difficulty_actions = [a for a in actions if a.action_type == "increase_difficulty"]
        assert len(difficulty_actions) > 0
        assert difficulty_actions[0].target_component == "content"
        assert difficulty_actions[0].priority == 3

    def test_generate_refinement_actions_clarify_content(self, mock_openai_client: Mock, sample_learning_unit: Any) -> None:
        """Test refinement action generation for clarifying content."""
        processor = FeedbackProcessor(mock_openai_client)
        
        feedback = UserFeedback(
            unit_id="unit-1",
            feedback_text="The content is unclear and confusing",
            timestamp="2024-01-01T10:00:00"
        )
        
        actions = processor._generate_refinement_actions(feedback, sample_learning_unit, "analysis")
        
        clarity_actions = [a for a in actions if a.action_type == "clarify_content"]
        assert len(clarity_actions) > 0
        assert clarity_actions[0].target_component == "description"
        assert clarity_actions[0].priority == 4

    def test_generate_refinement_actions_default(self, mock_openai_client: Mock, sample_learning_unit: Any) -> None:
        """Test default refinement action generation."""
        processor = FeedbackProcessor(mock_openai_client)
        
        feedback = UserFeedback(
            unit_id="unit-1",
            feedback_text="Overall feedback without specific issues",
            timestamp="2024-01-01T10:00:00"
        )
        
        actions = processor._generate_refinement_actions(feedback, sample_learning_unit, "analysis")
        
        assert len(actions) > 0
        # Should have default general review action
        general_actions = [a for a in actions if a.action_type == "general_review"]
        assert len(general_actions) > 0

    def test_analyze_sentiment_positive(self, mock_openai_client: Mock) -> None:
        """Test positive sentiment analysis."""
        processor = FeedbackProcessor(mock_openai_client)
        
        positive_texts = [
            "This unit is great and helpful",
            "Love the clear explanations",
            "Excellent resources provided",
            "Good overall structure"
        ]
        
        for text in positive_texts:
            sentiment = processor._analyze_sentiment(text)
            assert sentiment == "positive"

    def test_analyze_sentiment_negative(self, mock_openai_client: Mock) -> None:
        """Test negative sentiment analysis."""
        processor = FeedbackProcessor(mock_openai_client)
        
        negative_texts = [
            "This unit is terrible and confusing",
            "Hate the unclear explanations",
            "Poor quality resources",
            "Bad overall structure"
        ]
        
        for text in negative_texts:
            sentiment = processor._analyze_sentiment(text)
            assert sentiment == "negative"

    def test_analyze_sentiment_neutral(self, mock_openai_client: Mock) -> None:
        """Test neutral sentiment analysis."""
        processor = FeedbackProcessor(mock_openai_client)
        
        neutral_texts = [
            "This unit covers the topic",
            "Some information provided",
            "Standard content",
            "Basic explanation given"
        ]
        
        for text in neutral_texts:
            sentiment = processor._analyze_sentiment(text)
            assert sentiment == "neutral"

    def test_process_feedback_complete_workflow(self, mock_openai_client: Mock, sample_learning_unit: Any) -> None:
        """Test complete feedback processing workflow."""
        processor = FeedbackProcessor(mock_openai_client)
        
        # Mock the AI analysis
        with patch.object(processor, '_analyze_feedback_with_ai') as mock_ai:
            mock_ai.return_value = "Detailed AI analysis of the feedback"
            
            feedback = UserFeedback(
                unit_id="unit-1",
                feedback_text="This unit needs more video resources",
                timestamp="2024-01-01T10:00:00"
            )
            
            processed = processor.process_feedback(feedback, sample_learning_unit)
            
            assert isinstance(processed, ProcessedFeedback)
            assert processed.unit_id == "unit-1"
            assert processed.original_feedback == feedback
            assert len(processed.refinement_actions) > 0

    def test_batch_process_feedback(self, mock_openai_client: Mock, sample_learning_unit: Any) -> None:
        """Test batch processing of multiple feedback items."""
        processor = FeedbackProcessor(mock_openai_client)
        
        feedback_list = [
            UserFeedback(
                unit_id="unit-1",
                feedback_text="Need more resources",
                timestamp="2024-01-01T10:00:00"
            ),
            UserFeedback(
                unit_id="unit-1",
                feedback_text="Too difficult",
                timestamp="2024-01-01T10:01:00"
            )
        ]
        
        with patch.object(processor, 'process_feedback') as mock_process:
            mock_processed = ProcessedFeedback(
                unit_id="unit-1",
                original_feedback=feedback_list[0],
                categories=[FeedbackCategory.GENERAL],
                sentiment="neutral",
                refinement_actions=[],
                summary="Test summary"
            )
            mock_process.return_value = mock_processed
            
            results = processor.batch_process_feedback(feedback_list, sample_learning_unit)
            
            assert len(results) == 2
            assert mock_process.call_count == 2

    def test_consolidate_feedback_empty(self, mock_openai_client: Mock) -> None:
        """Test feedback consolidation with empty list."""
        processor = FeedbackProcessor(mock_openai_client)
        
        result = processor.consolidate_feedback([])
        
        assert result["actions"] == []
        assert result["summary"] == "No feedback to process"

    def test_consolidate_feedback_multiple(self, mock_openai_client: Mock) -> None:
        """Test feedback consolidation with multiple items."""
        processor = FeedbackProcessor(mock_openai_client)
        
        # Create mock processed feedback items
        action1 = RefinementAction(
            action_type="add_resources",
            target_component="resources",
            description="Add resources",
            priority=4
        )
        
        action2 = RefinementAction(
            action_type="add_resources",
            target_component="resources",
            description="Add more resources",
            priority=3
        )
        
        action3 = RefinementAction(
            action_type="add_tasks",
            target_component="tasks",
            description="Add tasks",
            priority=5
        )
        
        feedback1 = ProcessedFeedback(
            unit_id="unit-1",
            original_feedback=Mock(),
            categories=[FeedbackCategory.RESOURCES],
            sentiment="neutral",
            refinement_actions=[action1],
            summary="Summary 1"
        )
        
        feedback2 = ProcessedFeedback(
            unit_id="unit-1",
            original_feedback=Mock(),
            categories=[FeedbackCategory.RESOURCES],
            sentiment="neutral",
            refinement_actions=[action2, action3],
            summary="Summary 2"
        )
        
        result = processor.consolidate_feedback([feedback1, feedback2])
        
        assert len(result["actions"]) == 2  # Consolidated by type
        assert result["feedback_count"] == 2
        assert "add_resources" in [a.action_type for a in result["actions"]]
        assert "add_tasks" in [a.action_type for a in result["actions"]]
        
        # Should take highest priority action of each type
        add_resources_action = next(a for a in result["actions"] if a.action_type == "add_resources")
        assert add_resources_action.priority == 4  # Higher priority than action2


@patch('flowgenius.agents.feedback_processor.OpenAI')
def test_create_feedback_processor(mock_openai_class: Mock) -> None:
    """Test creating feedback processor."""
    mock_client = Mock()
    mock_openai_class.return_value = mock_client
    
    processor = create_feedback_processor(api_key="test-key", model="gpt-4")
    
    assert isinstance(processor, FeedbackProcessor)
    mock_openai_class.assert_called_once_with(api_key="test-key")
    assert processor.model == "gpt-4" 