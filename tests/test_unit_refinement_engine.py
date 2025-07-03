"""
Tests for the Unit Refinement Engine component.
"""

import pytest
from unittest.mock import Mock, patch
from typing import Any, List, Tuple

from flowgenius.agents.unit_refinement_engine import (
    UnitRefinementEngine,
    RefinementResult,
    create_unit_refinement_engine
)
from flowgenius.agents.feedback_processor import RefinementRecommendation, RefinementAction
from flowgenius.models.project import LearningUnit, LearningResource, EngageTask, UserFeedback


class TestRefinementResult:
    """Test cases for RefinementResult model."""

    def test_refinement_result_creation(self, sample_learning_unit: LearningUnit) -> None:
        """Test RefinementResult model creation."""
        result = RefinementResult(
            unit_id="unit-1",
            refined_unit=sample_learning_unit,
            success=True,
            changes_made=["action1", "action2"],
            updated_components=["resources", "tasks"],
            agent_responses={"content": "response1", "resources": "response2"},
            errors=[],
            reasoning="Successfully applied refinements"
        )
        
        assert result.unit_id == "unit-1"
        assert result.success is True
        assert result.refined_unit == sample_learning_unit
        assert result.changes_made == ["action1", "action2"]
        # Check backward compatibility alias
        assert result.applied_actions == ["action1", "action2"]
        assert result.updated_components == ["resources", "tasks"]
        assert result.agent_responses == {"content": "response1", "resources": "response2"}
        assert result.errors == []
        assert result.reasoning == "Successfully applied refinements"
        assert result.summary == "Successfully applied refinements"

    def test_refinement_result_defaults(self) -> None:
        """Test RefinementResult with default values."""
        result = RefinementResult(
            unit_id="unit-1",
            success=False
        )
        
        assert result.refined_unit is None
        assert result.changes_made == []
        assert result.updated_components == []
        assert result.agent_responses == {}
        assert result.errors == []
        assert result.reasoning == ""


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
        assert engine.feedback_processor is not None

    def test_apply_refinement_no_action(self, mock_openai_client: Mock, sample_learning_unit: Any) -> None:
        """Test refinement application when no action is needed."""
        engine = UnitRefinementEngine(mock_openai_client)
        
        feedback = UserFeedback(
            unit_id="unit-1",
            feedback_text="This looks good overall",
            timestamp="2024-01-01T10:00:00"
        )
        
        # Mock the feedback processor to return NO_ACTION
        with patch.object(engine.feedback_processor, 'analyze_feedback') as mock_analyze:
            mock_analyze.return_value = RefinementRecommendation(
                action=RefinementAction.NO_ACTION,
                priority="low",
                reasoning="No specific changes needed",
                estimated_impact="Low"
            )
            
            result = engine.apply_refinement(sample_learning_unit, feedback)
            
            assert isinstance(result, RefinementResult)
            assert result.unit_id == sample_learning_unit.id
            assert result.success is True
            assert "No changes needed" in result.changes_made[0]

    def test_apply_refinement_add_content(self, mock_openai_client: Mock, sample_learning_unit: Any) -> None:
        """Test refinement application for adding content (resources)."""
        engine = UnitRefinementEngine(mock_openai_client)
        
        feedback = UserFeedback(
            unit_id="unit-1",
            feedback_text="I need more video resources",
            timestamp="2024-01-01T10:00:00"
        )
        
        # Mock the feedback processor
        with patch.object(engine.feedback_processor, 'analyze_feedback') as mock_analyze:
            mock_analyze.return_value = RefinementRecommendation(
                action=RefinementAction.ADD_CONTENT,
                priority="high",
                specific_changes=["Add video tutorials"],
                reasoning="User needs visual learning materials",
                estimated_impact="High"
            )
            
            # Mock the resource curator response
            with patch.object(engine.resource_curator, 'curate_resources') as mock_curate:
                mock_curate.return_value = ([LearningResource(title="New Resource", url="http://example.com", type="video")], {"success": True, "count": 1})
                
                result = engine.apply_refinement(sample_learning_unit, feedback)
                
                assert result.success is True
                assert "Added 1 new resources" in result.changes_made[0]
                assert "resources" in result.updated_components
                assert len(result.refined_unit.resources) == len(sample_learning_unit.resources) + 1
                mock_curate.assert_called_once()

    def test_apply_refinement_add_examples(self, mock_openai_client: Mock, sample_learning_unit: Any) -> None:
        """Test refinement application for adding examples (tasks)."""
        engine = UnitRefinementEngine(mock_openai_client)
        
        feedback = UserFeedback(
            unit_id="unit-1",
            feedback_text="I need more practice examples",
            timestamp="2024-01-01T10:00:00"
        )
        
        # Mock the feedback processor
        with patch.object(engine.feedback_processor, 'analyze_feedback') as mock_analyze:
            mock_analyze.return_value = RefinementRecommendation(
                action=RefinementAction.ADD_EXAMPLES,
                priority="high",
                specific_changes=["Add practice exercises"],
                reasoning="User needs hands-on practice",
                estimated_impact="High"
            )
            
            # Mock the task generator response
            with patch.object(engine.task_generator, 'generate_tasks') as mock_generate:
                mock_generate.return_value = ([EngageTask(title="New Task", description="Do it", type="practice")], {"success": True, "count": 1})
                
                result = engine.apply_refinement(sample_learning_unit, feedback)
                
                assert result.success is True
                assert "Added 1 new engage task as examples" in result.changes_made[0]
                assert "engage_tasks" in result.updated_components
                assert len(result.refined_unit.engage_tasks) == len(sample_learning_unit.engage_tasks) + 1
                mock_generate.assert_called_once()

    def test_apply_refinement_clarify_content(self, mock_openai_client: Mock, sample_learning_unit: Any) -> None:
        """Test refinement application for clarifying content."""
        engine = UnitRefinementEngine(mock_openai_client)
        
        feedback = UserFeedback(
            unit_id="unit-1",
            feedback_text="This content is confusing",
            timestamp="2024-01-01T10:00:00"
        )
        
        # Mock the feedback processor
        with patch.object(engine.feedback_processor, 'analyze_feedback') as mock_analyze:
            mock_analyze.return_value = RefinementRecommendation(
                action=RefinementAction.CLARIFY_CONTENT,
                priority="high",
                specific_changes=["Clarify the explanation"],
                reasoning="Content needs clarification",
                estimated_impact="High"
            )
            
            # Mock the content generator response
            with patch.object(engine.content_generator, 'generate_complete_content') as mock_generate:
                from flowgenius.agents.content_generator import GeneratedContent
                generated_content = GeneratedContent(
                    unit_id="unit-1",
                    resources=[],
                    engage_tasks=[],
                    formatted_resources=[],
                    formatted_tasks=[],
                    generation_success=True,
                    generation_notes=["Content updated successfully"]
                )
                mock_generate.return_value = generated_content
                
                result = engine.apply_refinement(sample_learning_unit, feedback)
                
                assert result.success is True
                assert "Updated content" in result.changes_made[0]
                assert "content" in result.updated_components
                assert "[Clarified]" in result.refined_unit.description

    def test_apply_refinement_simplify_content(self, mock_openai_client: Mock, sample_learning_unit: Any) -> None:
        """Test refinement application for simplifying content."""
        engine = UnitRefinementEngine(mock_openai_client)
        
        feedback = UserFeedback(
            unit_id="unit-1",
            feedback_text="This is too difficult for beginners",
            timestamp="2024-01-01T10:00:00"
        )
        
        # Mock the feedback processor
        with patch.object(engine.feedback_processor, 'analyze_feedback') as mock_analyze:
            mock_analyze.return_value = RefinementRecommendation(
                action=RefinementAction.SIMPLIFY_CONTENT,
                priority="high",
                specific_changes=["Simplify for beginners"],
                reasoning="Content too difficult",
                estimated_impact="High"
            )
            
            # Mock the content generator
            with patch.object(engine.content_generator, 'generate_complete_content') as mock_generate:
                from flowgenius.agents.content_generator import GeneratedContent
                generated_content = GeneratedContent(
                    unit_id="unit-1",
                    resources=[],
                    engage_tasks=[],
                    formatted_resources=[],
                    formatted_tasks=[],
                    generation_success=True,
                    generation_notes=["Content simplified successfully"]
                )
                mock_generate.return_value = generated_content
                
                result = engine.apply_refinement(sample_learning_unit, feedback)
                
                assert result.success is True
                assert "Updated content" in result.changes_made[0]
                assert "content" in result.updated_components
                assert "[Simplified]" in result.refined_unit.description

    def test_apply_refinement_with_errors(self, mock_openai_client: Mock, sample_learning_unit: Any) -> None:
        """Test refinement application when errors occur."""
        engine = UnitRefinementEngine(mock_openai_client)
        
        feedback = UserFeedback(
            unit_id="unit-1",
            feedback_text="Need more resources",
            timestamp="2024-01-01T10:00:00"
        )
        
        # Mock the feedback processor
        with patch.object(engine.feedback_processor, 'analyze_feedback') as mock_analyze:
            mock_analyze.return_value = RefinementRecommendation(
                action=RefinementAction.ADD_CONTENT,
                priority="high",
                specific_changes=["Add resources"],
                reasoning="Need resources",
                estimated_impact="High"
            )
            
            # Mock agent to raise an exception
            with patch.object(engine.resource_curator, 'curate_resources') as mock_curate:
                mock_curate.side_effect = ValueError("Resource curation failed")
                
                result = engine.apply_refinement(sample_learning_unit, feedback)
                
                assert result.success is False
                assert len(result.errors) > 0
                assert "Resource curation failed" in str(result.errors[0])
                assert len(result.refined_unit.resources) == len(sample_learning_unit.resources)

    def test_batch_apply_refinements(self, mock_openai_client: Mock, sample_learning_unit: Any) -> None:
        """Test batch application of refinements."""
        engine = UnitRefinementEngine(mock_openai_client)
        
        # Create multiple units
        units = [
            sample_learning_unit,
            sample_learning_unit.model_copy(update={"id": "unit-2", "title": "Advanced Python"})
        ]
        
        # Create feedback for each unit
        feedback_list = [
            UserFeedback(
                unit_id="unit-1",
                feedback_text="Need more resources",
                timestamp="2024-01-01T10:00:00"
            ),
            UserFeedback(
                unit_id="unit-2",
                feedback_text="Need more tasks",
                timestamp="2024-01-01T10:00:00"
            )
        ]
        
        # Mock the feedback processor
        with patch.object(engine.feedback_processor, 'analyze_feedback') as mock_analyze:
            mock_analyze.side_effect = [
                RefinementRecommendation(
                    action=RefinementAction.ADD_CONTENT,
                    priority="medium",
                    reasoning="Need resources",
                    estimated_impact="Medium"
                ),
                RefinementRecommendation(
                    action=RefinementAction.ADD_EXAMPLES,
                    priority="medium",
                    reasoning="Need tasks",
                    estimated_impact="Medium"
                )
            ]
            
            with patch.object(engine.resource_curator, 'curate_resources') as mock_curate, \
                 patch.object(engine.task_generator, 'generate_tasks') as mock_generate:
                
                mock_curate.return_value = ([], {"success": True, "count": 0})
                mock_generate.return_value = ([], {"success": True, "count": 0})
                
                results = engine.batch_apply_refinements(units, feedback_list)
                
                assert len(results) == 2
                assert all(r.success for r in results)
                assert results[0].unit_id == "unit-1"
                assert results[1].unit_id == "unit-2"


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
        
        with pytest.raises(RuntimeError):
            create_unit_refinement_engine()


class TestUnitRefinementEngineIntegration:
    """Integration test cases for UnitRefinementEngine."""

    def test_complete_refinement_workflow(self, mock_openai_client: Mock, sample_learning_unit: Any) -> None:
        """Test complete refinement workflow with real-world scenario."""
        engine = UnitRefinementEngine(mock_openai_client)
        
        # Create realistic feedback
        feedback = UserFeedback(
            unit_id="unit-1",
            feedback_text="This unit needs beginner-friendly video tutorials and practice exercises",
            timestamp="2024-01-01T10:00:00"
        )
        
        # Mock the feedback processor to return a realistic recommendation
        with patch.object(engine.feedback_processor, 'analyze_feedback') as mock_analyze:
            mock_analyze.return_value = RefinementRecommendation(
                action=RefinementAction.ADD_CONTENT,
                priority="high",
                specific_changes=["Add beginner video tutorials", "Include practice exercises"],
                reasoning="User needs visual learning materials and hands-on practice",
                estimated_impact="High - Will significantly improve learning experience"
            )
            
            # Mock sub-agent responses
            with patch.object(engine.resource_curator, 'curate_resources') as mock_curate:
                mock_curate.return_value = (
                    [
                        LearningResource(title="Beginner Tutorial", url="http://example.com/tutorial", type="video"),
                        LearningResource(title="Practice Guide", url="http://example.com/guide", type="article")
                    ],
                    {"success": True, "count": 2}
                )
                
                result = engine.apply_refinement(sample_learning_unit, feedback)
                
                assert result.success is True
                assert len(result.changes_made) > 0
                assert "resources" in result.updated_components
                assert len(result.refined_unit.resources) > len(sample_learning_unit.resources)
                assert "visual learning materials" in result.reasoning 