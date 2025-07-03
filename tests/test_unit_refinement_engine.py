"""
Tests for the Unit Refinement Engine component.
"""

import pytest
from unittest.mock import Mock, patch
from typing import Any

from flowgenius.agents.unit_refinement_engine import (
    UnitRefinementEngine,
    RefinementResult,
    create_unit_refinement_engine
)
from flowgenius.agents.feedback_processor import ProcessedFeedback, RefinementAction, FeedbackCategory
from flowgenius.agents.conversation_manager import UserFeedback


class TestRefinementResult:
    """Test cases for RefinementResult model."""

    def test_refinement_result_creation(self) -> None:
        """Test RefinementResult model creation."""
        result = RefinementResult(
            unit_id="unit-1",
            success=True,
            applied_actions=["action1", "action2"],
            updated_components=["resources", "tasks"],
            agent_responses={"content": "response1", "resources": "response2"},
            errors=[],
            summary="Successfully applied refinements"
        )
        
        assert result.unit_id == "unit-1"
        assert result.success is True
        assert result.applied_actions == ["action1", "action2"]
        assert result.updated_components == ["resources", "tasks"]
        assert result.agent_responses == {"content": "response1", "resources": "response2"}
        assert result.errors == []
        assert result.summary == "Successfully applied refinements"

    def test_refinement_result_defaults(self) -> None:
        """Test RefinementResult with default values."""
        result = RefinementResult(
            unit_id="unit-1",
            success=False
        )
        
        assert result.applied_actions == []
        assert result.updated_components == []
        assert result.agent_responses == {}
        assert result.errors == []
        assert result.summary == ""


class TestUnitRefinementEngine:
    """Test cases for UnitRefinementEngine."""

    def test_init(self, mock_openai_client: Mock) -> None:
        """Test unit refinement engine initialization."""
        engine = UnitRefinementEngine(mock_openai_client, model="gpt-4")
        
        assert engine.client == mock_openai_client
        assert engine.model == "gpt-4"
        assert engine.content_generator is not None
        assert engine.resource_curator is not None
        assert engine.task_generator is not None

    def test_apply_refinement_empty_actions(self, mock_openai_client: Mock, sample_learning_unit: Any) -> None:
        """Test refinement application with empty actions list."""
        engine = UnitRefinementEngine(mock_openai_client)
        
        processed_feedback = ProcessedFeedback(
            unit_id="unit-1",
            original_feedback=Mock(),
            categories=[FeedbackCategory.GENERAL],
            sentiment="neutral",
            refinement_actions=[],
            summary="No specific actions needed"
        )
        
        result = engine.apply_refinement(sample_learning_unit, processed_feedback)
        
        assert isinstance(result, RefinementResult)
        assert result.unit_id == sample_learning_unit.id
        assert result.success is True
        assert len(result.applied_actions) == 0
        assert "No refinement actions" in result.summary

    def test_apply_refinement_add_resources(self, mock_openai_client: Mock, sample_learning_unit: Any) -> None:
        """Test refinement application for adding resources."""
        engine = UnitRefinementEngine(mock_openai_client)
        
        action = RefinementAction(
            action_type="add_resources",
            target_component="resources",
            description="Add more video resources",
            priority=4,
            details={"types": ["video"], "count": 2}
        )
        
        processed_feedback = ProcessedFeedback(
            unit_id="unit-1",
            original_feedback=Mock(),
            categories=[FeedbackCategory.RESOURCES],
            sentiment="neutral",
            refinement_actions=[action],
            summary="User needs more video resources"
        )
        
        # Mock the resource curator response
        with patch.object(engine.resource_curator, 'curate_resources') as mock_curate:
            mock_curate.return_value = ([], True)
            
            result = engine.apply_refinement(sample_learning_unit, processed_feedback)
            
            assert result.success is True
            assert "add_resources" in result.applied_actions
            assert "resources" in result.updated_components
            mock_curate.assert_called_once()

    def test_apply_refinement_add_tasks(self, mock_openai_client: Mock, sample_learning_unit: Any) -> None:
        """Test refinement application for adding tasks."""
        engine = UnitRefinementEngine(mock_openai_client)
        
        action = RefinementAction(
            action_type="add_tasks",
            target_component="engage_tasks",
            description="Add more practice tasks",
            priority=3,
            details={"count": 2}
        )
        
        processed_feedback = ProcessedFeedback(
            unit_id="unit-1",
            original_feedback=Mock(),
            categories=[FeedbackCategory.TASKS],
            sentiment="neutral",
            refinement_actions=[action],
            summary="User needs more practice tasks"
        )
        
        # Mock the task generator response
        with patch.object(engine.task_generator, 'generate_tasks') as mock_generate:
            mock_generate.return_value = ([], True)
            
            result = engine.apply_refinement(sample_learning_unit, processed_feedback)
            
            assert result.success is True
            assert "add_tasks" in result.applied_actions
            assert "engage_tasks" in result.updated_components
            mock_generate.assert_called_once()

    def test_apply_refinement_update_content(self, mock_openai_client: Mock, sample_learning_unit: Any) -> None:
        """Test refinement application for updating content."""
        engine = UnitRefinementEngine(mock_openai_client)
        
        action = RefinementAction(
            action_type="clarify_content",
            target_component="description",
            description="Make content clearer",
            priority=4
        )
        
        processed_feedback = ProcessedFeedback(
            unit_id="unit-1",
            original_feedback=Mock(),
            categories=[FeedbackCategory.CONTENT],
            sentiment="negative",
            refinement_actions=[action],
            summary="Content needs clarification"
        )
        
        # Mock OpenAI response for content update
        mock_response = Mock()
        mock_choice = Mock()
        mock_choice.message.content = "Improved content description"
        mock_response.choices = [mock_choice]
        engine.client.chat.completions.create.return_value = mock_response
        
        result = engine.apply_refinement(sample_learning_unit, processed_feedback)
        
        assert result.success is True
        assert "clarify_content" in result.applied_actions
        assert "description" in result.updated_components
        # Verify the unit's description was updated
        assert sample_learning_unit.description == "Improved content description"

    def test_apply_refinement_reduce_difficulty(self, mock_openai_client: Mock, sample_learning_unit: Any) -> None:
        """Test refinement application for reducing difficulty."""
        engine = UnitRefinementEngine(mock_openai_client)
        
        action = RefinementAction(
            action_type="reduce_difficulty",
            target_component="content",
            description="Make content easier for beginners",
            priority=5
        )
        
        processed_feedback = ProcessedFeedback(
            unit_id="unit-1",
            original_feedback=Mock(),
            categories=[FeedbackCategory.DIFFICULTY],
            sentiment="negative",
            refinement_actions=[action],
            summary="Content too difficult"
        )
        
        # Mock OpenAI responses for content updates
        mock_response = Mock()
        mock_choice = Mock()
        mock_choice.message.content = "Simplified content"
        mock_response.choices = [mock_choice]
        engine.client.chat.completions.create.return_value = mock_response
        
        result = engine.apply_refinement(sample_learning_unit, processed_feedback)
        
        assert result.success is True
        assert "reduce_difficulty" in result.applied_actions
        assert "description" in result.updated_components or "learning_objectives" in result.updated_components

    def test_apply_refinement_multiple_actions(self, mock_openai_client: Mock, sample_learning_unit: Any) -> None:
        """Test refinement application with multiple actions."""
        engine = UnitRefinementEngine(mock_openai_client)
        
        actions = [
            RefinementAction(
                action_type="add_resources",
                target_component="resources",
                description="Add video resources",
                priority=4
            ),
            RefinementAction(
                action_type="add_tasks",
                target_component="engage_tasks",
                description="Add practice tasks",
                priority=3
            )
        ]
        
        processed_feedback = ProcessedFeedback(
            unit_id="unit-1",
            original_feedback=Mock(),
            categories=[FeedbackCategory.RESOURCES, FeedbackCategory.TASKS],
            sentiment="neutral",
            refinement_actions=actions,
            summary="Need more resources and tasks"
        )
        
        # Mock agent responses
        with patch.object(engine.resource_curator, 'curate_resources') as mock_curate, \
             patch.object(engine.task_generator, 'generate_tasks') as mock_generate:
            
            mock_curate.return_value = ([], True)
            mock_generate.return_value = ([], True)
            
            result = engine.apply_refinement(sample_learning_unit, processed_feedback)
            
            assert result.success is True
            assert len(result.applied_actions) == 2
            assert "add_resources" in result.applied_actions
            assert "add_tasks" in result.applied_actions
            assert "resources" in result.updated_components
            assert "engage_tasks" in result.updated_components

    def test_apply_refinement_with_errors(self, mock_openai_client: Mock, sample_learning_unit: Any) -> None:
        """Test refinement application when errors occur."""
        engine = UnitRefinementEngine(mock_openai_client)
        
        action = RefinementAction(
            action_type="add_resources",
            target_component="resources",
            description="Add resources",
            priority=4
        )
        
        processed_feedback = ProcessedFeedback(
            unit_id="unit-1",
            original_feedback=Mock(),
            categories=[FeedbackCategory.RESOURCES],
            sentiment="neutral",
            refinement_actions=[action],
            summary="Need resources"
        )
        
        # Mock agent to raise an exception
        with patch.object(engine.resource_curator, 'curate_resources') as mock_curate:
            mock_curate.side_effect = Exception("Resource curation failed")
            
            result = engine.apply_refinement(sample_learning_unit, processed_feedback)
            
            assert result.success is False
            assert len(result.errors) > 0
            assert "Resource curation failed" in str(result.errors[0])

    def test_batch_apply_refinements(self, mock_openai_client: Mock, sample_learning_unit: Any) -> None:
        """Test batch application of refinements."""
        engine = UnitRefinementEngine(mock_openai_client)
        
        # Create multiple units
        units = [
            sample_learning_unit,
            sample_learning_unit.model_copy(update={"id": "unit-2", "title": "Advanced Python"})
        ]
        
        # Create processed feedback for each unit
        feedback_list = [
            ProcessedFeedback(
                unit_id="unit-1",
                original_feedback=Mock(),
                categories=[FeedbackCategory.RESOURCES],
                sentiment="neutral",
                refinement_actions=[
                    RefinementAction(
                        action_type="add_resources",
                        target_component="resources",
                        description="Add resources",
                        priority=3
                    )
                ],
                summary="Need resources"
            ),
            ProcessedFeedback(
                unit_id="unit-2",
                original_feedback=Mock(),
                categories=[FeedbackCategory.TASKS],
                sentiment="neutral",
                refinement_actions=[
                    RefinementAction(
                        action_type="add_tasks",
                        target_component="engage_tasks",
                        description="Add tasks",
                        priority=3
                    )
                ],
                summary="Need tasks"
            )
        ]
        
        with patch.object(engine.resource_curator, 'curate_resources') as mock_curate, \
             patch.object(engine.task_generator, 'generate_tasks') as mock_generate:
            
            mock_curate.return_value = ([], True)
            mock_generate.return_value = ([], True)
            
            results = engine.batch_apply_refinements(units, feedback_list)
            
            assert len(results) == 2
            assert all(r.success for r in results)
            assert results[0].unit_id == "unit-1"
            assert results[1].unit_id == "unit-2"

    def test_action_execution_mapping(self, mock_openai_client: Mock, sample_learning_unit: Any) -> None:
        """Test that action types are correctly mapped to execution methods."""
        engine = UnitRefinementEngine(mock_openai_client)
        
        # Test different action types
        action_types = [
            "add_resources",
            "add_tasks", 
            "clarify_content",
            "reduce_difficulty",
            "increase_difficulty",
            "general_review"
        ]
        
        for action_type in action_types:
            action = RefinementAction(
                action_type=action_type,
                target_component="test",
                description=f"Test {action_type}",
                priority=3
            )
            
            processed_feedback = ProcessedFeedback(
                unit_id="unit-1",
                original_feedback=Mock(),
                categories=[FeedbackCategory.GENERAL],
                sentiment="neutral",
                refinement_actions=[action],
                summary=f"Test {action_type}"
            )
            
            # Mock all possible agent calls
            with patch.object(engine.resource_curator, 'curate_resources') as mock_curate, \
                 patch.object(engine.task_generator, 'generate_tasks') as mock_generate:
                
                mock_curate.return_value = ([], True)
                mock_generate.return_value = ([], True)
                
                # Mock OpenAI for content updates
                mock_response = Mock()
                mock_choice = Mock()
                mock_choice.message.content = "Updated content"
                mock_response.choices = [mock_choice]
                engine.client.chat.completions.create.return_value = mock_response
                
                result = engine.apply_refinement(sample_learning_unit, processed_feedback)
                
                # Each action type should execute without error
                assert result.success is True
                assert action_type in result.applied_actions


class TestFactoryFunction:
    """Test cases for factory function."""

    @patch('flowgenius.agents.unit_refinement_engine.OpenAI')
    def test_create_unit_refinement_engine_with_api_key(self, mock_openai_class: Mock) -> None:
        """Test creating unit refinement engine with API key."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        engine = create_unit_refinement_engine(api_key="test-key", model="gpt-4")
        
        assert isinstance(engine, UnitRefinementEngine)
        mock_openai_class.assert_called_once_with(api_key="test-key")
        assert engine.model == "gpt-4"

    @patch('flowgenius.agents.unit_refinement_engine.OpenAI')
    def test_create_unit_refinement_engine_without_api_key(self, mock_openai_class: Mock) -> None:
        """Test creating unit refinement engine without API key."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        engine = create_unit_refinement_engine()
        
        assert isinstance(engine, UnitRefinementEngine)
        mock_openai_class.assert_called_once_with()
        assert engine.model == "gpt-4o-mini"

    @patch('flowgenius.agents.unit_refinement_engine.OpenAI')
    def test_create_unit_refinement_engine_failure(self, mock_openai_class: Mock) -> None:
        """Test factory function handling OpenAI client creation failure."""
        mock_openai_class.side_effect = Exception("API Error")
        
        with pytest.raises(RuntimeError, match="Failed to create UnitRefinementEngine"):
            create_unit_refinement_engine()


class TestUnitRefinementEngineIntegration:
    """Integration test cases for UnitRefinementEngine."""

    def test_complete_refinement_workflow(self, mock_openai_client: Mock, sample_learning_unit: Any) -> None:
        """Test complete refinement workflow with real-world scenario."""
        engine = UnitRefinementEngine(mock_openai_client)
        
        # Create realistic feedback scenario
        feedback = UserFeedback(
            unit_id="unit-1",
            feedback_text="This Python unit needs more beginner-friendly examples and practice exercises",
            timestamp="2024-01-01T10:00:00"
        )
        
        actions = [
            RefinementAction(
                action_type="add_resources",
                target_component="resources",
                description="Add beginner tutorials",
                priority=4,
                details={"types": ["video", "article"], "difficulty": "beginner"}
            ),
            RefinementAction(
                action_type="add_tasks",
                target_component="engage_tasks",
                description="Add practice exercises",
                priority=4,
                details={"count": 2, "difficulty": "beginner"}
            ),
            RefinementAction(
                action_type="clarify_content",
                target_component="description",
                description="Simplify explanations",
                priority=3
            )
        ]
        
        processed_feedback = ProcessedFeedback(
            unit_id="unit-1",
            original_feedback=feedback,
            categories=[FeedbackCategory.RESOURCES, FeedbackCategory.TASKS, FeedbackCategory.CONTENT],
            sentiment="constructive",
            refinement_actions=actions,
            summary="User needs more beginner-friendly content and practice"
        )
        
        # Mock all agent responses
        with patch.object(engine.resource_curator, 'curate_resources') as mock_curate, \
             patch.object(engine.task_generator, 'generate_tasks') as mock_generate:
            
            mock_curate.return_value = ([], True)
            mock_generate.return_value = ([], True)
            
            # Mock OpenAI for content clarification
            mock_response = Mock()
            mock_choice = Mock()
            mock_choice.message.content = "Simplified description for beginners"
            mock_response.choices = [mock_choice]
            engine.client.chat.completions.create.return_value = mock_response
            
            result = engine.apply_refinement(sample_learning_unit, processed_feedback)
            
            # Verify comprehensive refinement
            assert result.success is True
            assert len(result.applied_actions) == 3
            assert "add_resources" in result.applied_actions
            assert "add_tasks" in result.applied_actions
            assert "clarify_content" in result.applied_actions
            
            # Verify components were updated
            expected_components = ["resources", "engage_tasks", "description"]
            for component in expected_components:
                assert component in result.updated_components
            
            # Verify unit was actually modified
            assert sample_learning_unit.description == "Simplified description for beginners" 