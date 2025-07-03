"""
Tests for the Content Generator integration agent.
"""

import json
import pytest
from typing import Any
from unittest.mock import Mock, patch, MagicMock

from flowgenius.agents.content_generator import (
    ContentGeneratorAgent,
    ContentGenerationRequest,
    GeneratedContent,
    create_content_generator,
    generate_unit_content_simple
)
from flowgenius.agents.resource_curator import ResourceCuratorAgent
from flowgenius.agents.engage_task_generator import EngageTaskGeneratorAgent


class TestContentGeneratorAgent:
    """Test cases for ContentGeneratorAgent."""

    def test_init(self, mock_openai_client: Mock) -> None:
        """Test agent initialization."""
        agent = ContentGeneratorAgent(mock_openai_client)
        
        assert agent.client == mock_openai_client
        assert agent.model == "gpt-4o-mini"
        assert isinstance(agent.resource_curator, ResourceCuratorAgent)
        assert isinstance(agent.task_generator, EngageTaskGeneratorAgent)

    def test_generate_complete_content_success(self, mock_openai_client: Mock, sample_learning_unit: Any, sample_learning_resources: Any, sample_engage_tasks: Any) -> None:
        """Test successful complete content generation."""
        agent = ContentGeneratorAgent(mock_openai_client)
        
        # Mock the component agents
        with patch.object(agent.resource_curator, 'curate_resources') as mock_resources, \
             patch.object(agent.task_generator, 'generate_tasks') as mock_tasks:
            
            mock_resources.return_value = (sample_learning_resources, True)
            mock_tasks.return_value = (sample_engage_tasks, True)
            
            request = ContentGenerationRequest(unit=sample_learning_unit)
            content = agent.generate_complete_content(request)
            
            assert isinstance(content, GeneratedContent)
            assert content.generation_success is True
            assert content.unit_id == sample_learning_unit.id
            assert len(content.resources) == 2
            assert len(content.engage_tasks) == 2
            assert len(content.formatted_resources) == 2
            assert len(content.formatted_tasks) == 2
            assert len(content.generation_notes) == 2

    def test_generate_complete_content_with_custom_request(self, mock_openai_client: Mock, sample_learning_unit: Any) -> None:
        """Test content generation with custom request parameters."""
        agent = ContentGeneratorAgent(mock_openai_client)
        
        with patch.object(agent.resource_curator, 'curate_resources') as mock_resources, \
             patch.object(agent.task_generator, 'generate_tasks') as mock_tasks:
            
            mock_resources.return_value = ([], True)
            mock_tasks.return_value = ([], True)
            
            request = ContentGenerationRequest(
                unit=sample_learning_unit,
                min_video_resources=2,
                min_reading_resources=3,
                max_total_resources=8,
                num_engage_tasks=3,
                difficulty_preference="advanced",
                focus_on_application=False,
                use_obsidian_links=False
            )
            
            content = agent.generate_complete_content(request)
            
            # Verify that the right parameters were passed to component agents
            mock_resources.assert_called_once()
            resource_request = mock_resources.call_args[0][0]
            assert resource_request.min_video_resources == 2
            assert resource_request.min_reading_resources == 3
            assert resource_request.max_total_resources == 8
            assert resource_request.difficulty_preference == "advanced"
            
            mock_tasks.assert_called_once()
            task_request = mock_tasks.call_args[0][0]
            assert task_request.num_tasks == 3
            assert task_request.difficulty_preference == "advanced"
            assert task_request.focus_on_application is False

    def test_generate_complete_content_failure(self, mock_openai_client: Mock, sample_learning_unit: Any) -> None:
        """Test content generation when component agents fail."""
        agent = ContentGeneratorAgent(mock_openai_client)
        
        # Mock component agents to fail
        with patch.object(agent.resource_curator, 'curate_resources') as mock_resources, \
             patch.object(agent.task_generator, 'generate_tasks') as mock_tasks:
            
            mock_resources.side_effect = ValueError("Resource generation failed")
            
            request = ContentGenerationRequest(unit=sample_learning_unit)
            content = agent.generate_complete_content(request)
            
            # Should still return content with fallback
            assert isinstance(content, GeneratedContent)
            assert content.generation_success is False
            assert len(content.generation_notes) > 0
            assert "error" in content.generation_notes[0].lower() or "fallback" in content.generation_notes[-1].lower()
            assert len(content.resources) >= 2  # Fallback resources
            assert len(content.engage_tasks) >= 1  # Fallback task

    def test_populate_unit_with_content(self, mock_openai_client: Mock, sample_learning_unit: Any, sample_learning_resources: Any, sample_engage_tasks: Any) -> None:
        """Test in-place unit population."""
        agent = ContentGeneratorAgent(mock_openai_client)
        
        with patch.object(agent, 'generate_complete_content') as mock_generate:
            mock_content = GeneratedContent(
                unit_id=sample_learning_unit.id,
                resources=sample_learning_resources,
                engage_tasks=sample_engage_tasks,
                formatted_resources=[],
                formatted_tasks=[],
                generation_success=True
            )
            mock_generate.return_value = mock_content
            
            # Make a copy to test mutation
            unit_copy = sample_learning_unit.model_copy()
            assert len(unit_copy.resources) == 0
            assert len(unit_copy.engage_tasks) == 0
            
            result_unit = agent.populate_unit_with_content(unit_copy)
            
            assert result_unit is unit_copy  # Same object
            assert len(result_unit.resources) == 2
            assert len(result_unit.engage_tasks) == 2

    def test_populate_unit_with_content_custom_request(self, mock_openai_client: Mock, sample_learning_unit: Any) -> None:
        """Test unit population with custom request."""
        agent = ContentGeneratorAgent(mock_openai_client)
        
        with patch.object(agent, 'generate_complete_content') as mock_generate:
            mock_generate.return_value = GeneratedContent(
                unit_id=sample_learning_unit.id,
                resources=[],
                engage_tasks=[],
                formatted_resources=[],
                formatted_tasks=[],
                generation_success=True
            )
            
            custom_request = ContentGenerationRequest(
                unit=sample_learning_unit,
                num_engage_tasks=5
            )
            
            agent.populate_unit_with_content(sample_learning_unit, custom_request)
            
            # Verify the request was updated with the correct unit
            mock_generate.assert_called_once()
            actual_request = mock_generate.call_args[0][0]
            assert actual_request.unit == sample_learning_unit
            assert actual_request.num_engage_tasks == 5

    def test_batch_populate_units(self, mock_openai_client: Mock, sample_learning_unit: Any, sample_learning_resources: Any, sample_engage_tasks: Any) -> None:
        """Test batch unit population."""
        agent = ContentGeneratorAgent(mock_openai_client)
        
        # Create multiple units
        units = [
            sample_learning_unit,
            sample_learning_unit.model_copy(update={"id": "unit-2", "title": "Advanced Python"}),
            sample_learning_unit.model_copy(update={"id": "unit-3", "title": "Python Projects"})
        ]
        
        with patch.object(agent, 'generate_complete_content') as mock_generate:
            # Mock different responses for each unit
            mock_responses = [
                GeneratedContent(
                    unit_id=unit.id,
                    resources=sample_learning_resources[:1],
                    engage_tasks=sample_engage_tasks[:1],
                    formatted_resources=[],
                    formatted_tasks=[],
                    generation_success=True
                )
                for unit in units
            ]
            mock_generate.side_effect = mock_responses
            
            results = agent.batch_populate_units(units)
            
            assert len(results) == 3
            assert all(isinstance(r, GeneratedContent) for r in results)
            assert mock_generate.call_count == 3
            
            # Verify units were populated
            for unit in units:
                assert len(unit.resources) == 1
                assert len(unit.engage_tasks) == 1

    def test_batch_populate_units_with_base_request(self, mock_openai_client: Mock, sample_learning_unit: Any) -> None:
        """Test batch population with base request."""
        agent = ContentGeneratorAgent(mock_openai_client)
        
        units = [sample_learning_unit]
        base_request = ContentGenerationRequest(
            unit=sample_learning_unit,
            num_engage_tasks=3,
            difficulty_preference="expert"
        )
        
        with patch.object(agent, 'generate_complete_content') as mock_generate:
            mock_generate.return_value = GeneratedContent(
                unit_id=sample_learning_unit.id,
                resources=[],
                engage_tasks=[],
                formatted_resources=[],
                formatted_tasks=[],
                generation_success=True
            )
            
            agent.batch_populate_units(units, base_request)
            
            # Verify the base request parameters were used
            actual_request = mock_generate.call_args[0][0]
            assert actual_request.num_engage_tasks == 3
            assert actual_request.difficulty_preference == "expert"
            assert actual_request.unit == sample_learning_unit

    def test_format_resources(self, mock_openai_client: Mock, sample_learning_resources: Any) -> None:
        """Test resource formatting."""
        agent = ContentGeneratorAgent(mock_openai_client)
        
        formatted = agent._format_resources(sample_learning_resources, use_obsidian_links=True)
        
        assert len(formatted) == 2
        assert "🎥" in formatted[0]
        assert "📖" in formatted[1]

    def test_format_tasks(self, mock_openai_client: Mock, sample_engage_tasks: Any) -> None:
        """Test task formatting."""
        agent = ContentGeneratorAgent(mock_openai_client)
        
        formatted = agent._format_tasks(sample_engage_tasks)
        
        assert len(formatted) == 2
        assert "🛠️" in formatted[0]
        assert "🤔" in formatted[1]

    def test_generate_fallback_content(self, mock_openai_client: Mock, sample_learning_unit: Any) -> None:
        """Test fallback content generation."""
        agent = ContentGeneratorAgent(mock_openai_client)
        request = ContentGenerationRequest(unit=sample_learning_unit)
        generation_notes = ["Initial error"]
        
        content = agent._generate_fallback_content(request, generation_notes)
        
        assert isinstance(content, GeneratedContent)
        assert content.generation_success is False
        assert len(content.generation_notes) > 1
        assert "fallback" in content.generation_notes[-1].lower()
        assert len(content.resources) == 2  # Basic video + article
        assert len(content.engage_tasks) == 1
        assert any(r.type == "video" for r in content.resources)
        assert any(r.type == "article" for r in content.resources)


class TestContentGenerationRequest:
    """Test cases for ContentGenerationRequest model."""

    def test_content_generation_request_defaults(self, sample_learning_unit: Any) -> None:
        """Test ContentGenerationRequest with default values."""
        request = ContentGenerationRequest(unit=sample_learning_unit)
        
        assert request.unit == sample_learning_unit
        assert request.min_video_resources == 1
        assert request.min_reading_resources == 1
        assert request.max_total_resources == 5
        assert request.num_engage_tasks == 1
        assert request.difficulty_preference is None
        assert request.focus_on_application is True
        assert request.use_obsidian_links is True

    def test_content_generation_request_custom_values(self, sample_learning_unit: Any) -> None:
        """Test ContentGenerationRequest with custom values."""
        request = ContentGenerationRequest(
            unit=sample_learning_unit,
            min_video_resources=3,
            min_reading_resources=2,
            max_total_resources=8,
            num_engage_tasks=4,
            difficulty_preference="advanced",
            focus_on_application=False,
            use_obsidian_links=False
        )
        
        assert request.min_video_resources == 3
        assert request.min_reading_resources == 2
        assert request.max_total_resources == 8
        assert request.num_engage_tasks == 4
        assert request.difficulty_preference == "advanced"
        assert request.focus_on_application is False
        assert request.use_obsidian_links is False


class TestGeneratedContent:
    """Test cases for GeneratedContent model."""

    def test_generated_content_creation(self, sample_learning_resources: Any, sample_engage_tasks: Any) -> None:
        """Test GeneratedContent model creation."""
        content = GeneratedContent(
            unit_id="unit-1",
            resources=sample_learning_resources,
            engage_tasks=sample_engage_tasks,
            formatted_resources=["formatted resource"],
            formatted_tasks=["formatted task"],
            generation_success=True,
            generation_notes=["note 1", "note 2"]
        )
        
        assert content.unit_id == "unit-1"
        assert len(content.resources) == 2
        assert len(content.engage_tasks) == 2
        assert content.generation_success is True
        assert len(content.generation_notes) == 2

    def test_generated_content_defaults(self) -> None:
        """Test GeneratedContent with default values."""
        content = GeneratedContent(
            unit_id="unit-1",
            resources=[],
            engage_tasks=[],
            formatted_resources=[],
            formatted_tasks=[],
            generation_success=True
        )
        
        assert content.generation_notes == []


class TestFactoryFunctions:
    """Test cases for factory functions."""

    @patch('flowgenius.agents.content_generator.OpenAI')
    def test_create_content_generator_with_api_key(self, mock_openai_class: Mock) -> None:
        """Test creating content generator with API key."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        generator = create_content_generator(api_key="test-key", model="gpt-4")
        
        assert isinstance(generator, ContentGeneratorAgent)
        mock_openai_class.assert_called_once_with(api_key="test-key")
        assert generator.model == "gpt-4"

    @patch('flowgenius.agents.content_generator.OpenAI')
    def test_create_content_generator_without_api_key(self, mock_openai_class: Mock) -> None:
        """Test creating content generator without API key."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        generator = create_content_generator()
        
        assert isinstance(generator, ContentGeneratorAgent)
        mock_openai_class.assert_called_once_with()
        assert generator.model == "gpt-4o-mini"

    @patch('flowgenius.agents.content_generator.OpenAI')
    def test_create_content_generator_failure(self, mock_openai_class: Mock) -> None:
        """Test factory function handling OpenAI client creation failure."""
        mock_openai_class.side_effect = Exception("API Error")
        
        with pytest.raises(RuntimeError, match="Failed to create ContentGeneratorAgent"):
            create_content_generator()

    @patch('flowgenius.agents.content_generator.create_content_generator')
    def test_generate_unit_content_simple(self, mock_create_generator: Mock, sample_learning_unit: Any) -> None:
        """Test simple content generation utility function."""
        mock_generator = Mock()
        mock_content = GeneratedContent(
            unit_id=sample_learning_unit.id,
            resources=[],
            engage_tasks=[],
            formatted_resources=[],
            formatted_tasks=[],
            generation_success=True
        )
        mock_generator.generate_complete_content.return_value = mock_content
        mock_create_generator.return_value = mock_generator
        
        result = generate_unit_content_simple(
            sample_learning_unit,
            api_key="test-key",
            use_obsidian_links=False
        )
        
        assert result is mock_content
        mock_create_generator.assert_called_once_with("test-key")
        
        # Verify the request was created correctly
        mock_generator.generate_complete_content.assert_called_once()
        request = mock_generator.generate_complete_content.call_args[0][0]
        assert request.unit == sample_learning_unit
        assert request.use_obsidian_links is False 