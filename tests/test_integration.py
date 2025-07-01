"""
Integration tests for FlowGenius agents.

These tests verify that all components work together correctly.
Some tests may require environment variables for API keys.
"""

import os
import pytest
from unittest.mock import Mock, patch

from flowgenius.models.project import LearningUnit, LearningProject, ProjectMetadata
from flowgenius.agents import (
    generate_unit_content_simple,
    create_content_generator,
    ContentGenerationRequest
)


class TestIntegration:
    """Integration tests for the complete agent workflow."""

    def test_end_to_end_with_mock(self, mock_openai_client, sample_learning_unit):
        """Test complete end-to-end workflow with mocked API."""
        # Mock successful responses for both agents
        mock_responses = [
            # Resource curator response
            '{"resources": [{"title": "Python Tutorial", "url": "https://youtube.com/test", "type": "video", "description": "Great tutorial", "estimated_time": "30 min"}, {"title": "Python Guide", "url": "https://docs.python.org", "type": "article", "description": "Official docs", "estimated_time": "45 min"}]}',
            # Task generator response  
            '{"tasks": [{"title": "Build a Calculator", "description": "Create a simple calculator app", "type": "project", "estimated_time": "60 min"}]}'
        ]
        
        # Configure mock to return different responses for each call
        mock_openai_client.chat.completions.create.side_effect = [
            Mock(choices=[Mock(message=Mock(content=response))]) for response in mock_responses
        ]
        
        # Test the simple generation function
        with patch('flowgenius.agents.content_generator.OpenAI', return_value=mock_openai_client):
            content = generate_unit_content_simple(sample_learning_unit)
        
        # Verify the results
        assert content.generation_success is True
        assert len(content.resources) == 2
        assert len(content.engage_tasks) == 1
        assert len(content.formatted_resources) == 2
        assert len(content.formatted_tasks) == 1
        
        # Check formatted output quality
        assert "🎥" in content.formatted_resources[0]  # Video emoji
        assert "📖" in content.formatted_resources[1]  # Article emoji
        assert "🎯" in content.formatted_tasks[0]      # Project emoji
        
        # Verify content quality
        assert "Python Tutorial" in content.formatted_resources[0]
        assert "Build a Calculator" in content.formatted_tasks[0]

    def test_fallback_system_integration(self, sample_learning_unit):
        """Test that fallback systems work when API is unavailable."""
        # Test without any API client (simulating complete failure)
        with patch('flowgenius.agents.content_generator.OpenAI') as mock_openai_class:
            mock_openai_class.side_effect = Exception("No API available")
            
            with pytest.raises(RuntimeError):
                create_content_generator()
        
        # Test with client that fails to generate content but agents handle gracefully
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        
        # Create generator with failing client directly
        from flowgenius.agents.content_generator import ContentGeneratorAgent, ContentGenerationRequest
        generator = ContentGeneratorAgent(mock_client)
        request = ContentGenerationRequest(unit=sample_learning_unit)
        content = generator.generate_complete_content(request)
        
        # Should still generate content using fallbacks
        assert content.generation_success is False
        assert len(content.resources) >= 2  # Fallback resources
        assert len(content.engage_tasks) >= 1  # Fallback task
        # Check if any note mentions error or fallback
        notes_text = ' '.join(content.generation_notes).lower()
        assert "error" in notes_text or "fallback" in notes_text

    def test_different_unit_types_integration(self, mock_openai_client):
        """Test integration with different types of learning units."""
        # Mock consistent responses
        mock_resource_response = '{"resources": [{"title": "Test Video", "url": "https://test.com", "type": "video", "description": "Test", "estimated_time": "20 min"}]}'
        mock_task_response = '{"tasks": [{"title": "Test Task", "description": "Do something", "type": "practice", "estimated_time": "30 min"}]}'
        
        mock_openai_client.chat.completions.create.side_effect = [
            Mock(choices=[Mock(message=Mock(content=mock_resource_response))]),
            Mock(choices=[Mock(message=Mock(content=mock_task_response))])
        ]
        
        # Test with programming unit
        programming_unit = LearningUnit(
            id="prog-1",
            title="Advanced JavaScript",
            description="Learn advanced JavaScript concepts",
            learning_objectives=[
                "Master async/await patterns",
                "Implement complex data structures",
                "Build scalable applications"
            ]
        )
        
        with patch('flowgenius.agents.content_generator.OpenAI', return_value=mock_openai_client):
            generator = create_content_generator()
            content = generator.generate_complete_content(
                ContentGenerationRequest(unit=programming_unit)
            )
        
        assert content.generation_success is True
        assert content.unit_id == "prog-1"

    def test_batch_processing_integration(self, mock_openai_client):
        """Test batch processing of multiple units."""
        # Create multiple units
        units = [
            LearningUnit(
                id=f"unit-{i}",
                title=f"Topic {i}",
                description=f"Learn about topic {i}",
                learning_objectives=[f"Understand concept {i}", f"Apply knowledge {i}"]
            )
            for i in range(1, 4)
        ]
        
        # Mock responses (need 6 total: 3 resource calls + 3 task calls)
        mock_responses = [
            '{"resources": [{"title": "Video", "url": "https://test.com", "type": "video", "description": "Test", "estimated_time": "20 min"}]}',
            '{"tasks": [{"title": "Task", "description": "Do something", "type": "practice", "estimated_time": "30 min"}]}'
        ] * 3
        
        mock_openai_client.chat.completions.create.side_effect = [
            Mock(choices=[Mock(message=Mock(content=response))]) for response in mock_responses
        ]
        
        with patch('flowgenius.agents.content_generator.OpenAI', return_value=mock_openai_client):
            generator = create_content_generator()
            results = generator.batch_populate_units(units)
        
        assert len(results) == 3
        assert all(r.generation_success for r in results)
        
        # Verify all units were populated
        for unit in units:
            assert len(unit.resources) >= 1
            assert len(unit.engage_tasks) >= 1

    def test_obsidian_vs_standard_formatting_integration(self, mock_openai_client, sample_learning_unit):
        """Test different link formatting options."""
        mock_resource_response = '{"resources": [{"title": "Test Resource", "url": "https://example.com", "type": "article", "description": "Test", "estimated_time": "15 min"}]}'
        mock_task_response = '{"tasks": [{"title": "Test Task", "description": "Do test", "type": "reflection", "estimated_time": "10 min"}]}'
        
        # Setup mock to return both responses in sequence
        mock_openai_client.chat.completions.create.side_effect = [
            Mock(choices=[Mock(message=Mock(content=mock_resource_response))]),
            Mock(choices=[Mock(message=Mock(content=mock_task_response))]),
            Mock(choices=[Mock(message=Mock(content=mock_resource_response))]),
            Mock(choices=[Mock(message=Mock(content=mock_task_response))])
        ]
        
        with patch('flowgenius.agents.content_generator.OpenAI', return_value=mock_openai_client):
            # Test Obsidian formatting
            content_obsidian = generate_unit_content_simple(sample_learning_unit, use_obsidian_links=True)
            
            # Test standard formatting
            content_standard = generate_unit_content_simple(sample_learning_unit, use_obsidian_links=False)
        
        # Both should work and produce formatted content
        assert content_obsidian.generation_success is True
        assert content_standard.generation_success is True
        
        # Verify resources were generated and formatted
        assert len(content_obsidian.formatted_resources) > 0
        assert len(content_standard.formatted_resources) > 0
        
        # Both should have emojis for article type
        formatted_resource_obsidian = content_obsidian.formatted_resources[0]
        formatted_resource_standard = content_standard.formatted_resources[0]
        
        assert "📖" in formatted_resource_obsidian  # Article emoji
        assert "📖" in formatted_resource_standard  # Article emoji

    def test_error_recovery_integration(self, mock_openai_client, sample_learning_unit):
        """Test that the system recovers gracefully from various errors."""
        with patch('flowgenius.agents.content_generator.OpenAI', return_value=mock_openai_client):
            generator = create_content_generator()
            
            # Test JSON parsing error
            mock_openai_client.chat.completions.create.return_value = Mock(
                choices=[Mock(message=Mock(content="Invalid JSON"))]
            )
            
            content = generator.generate_complete_content(
                ContentGenerationRequest(unit=sample_learning_unit)
            )
            
            # Should fall back to backup content
            assert isinstance(content.resources, list)
            assert isinstance(content.engage_tasks, list)
            assert len(content.generation_notes) > 0

    @pytest.mark.skipif(
        not os.getenv('OPENAI_API_KEY'), 
        reason="Requires OPENAI_API_KEY environment variable for live testing"
    )
    def test_live_api_integration(self, sample_learning_unit):
        """Test with real OpenAI API (requires API key)."""
        # This test only runs if OPENAI_API_KEY is set
        content = generate_unit_content_simple(sample_learning_unit)
        
        # With real API, should generate meaningful content
        assert content.generation_success is True
        assert len(content.resources) >= 2
        assert len(content.engage_tasks) >= 1
        
        # Check that generated content is relevant
        unit_title_lower = sample_learning_unit.title.lower()
        
        # At least one resource should mention the topic
        resource_texts = ' '.join([r.title + ' ' + (r.description or '') for r in content.resources]).lower()
        assert any(word in resource_texts for word in unit_title_lower.split())
        
        # Task should be relevant
        task_texts = ' '.join([t.title + ' ' + t.description for t in content.engage_tasks]).lower()
        assert any(word in task_texts for word in unit_title_lower.split())


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_invalid_learning_unit(self, mock_openai_client):
        """Test handling of invalid learning units."""
        # Unit with minimal information
        minimal_unit = LearningUnit(
            id="minimal",
            title="",
            description="",
            learning_objectives=[]
        )
        
        mock_openai_client.chat.completions.create.side_effect = Exception("API Error")
        
        with patch('flowgenius.agents.content_generator.OpenAI', return_value=mock_openai_client):
            content = generate_unit_content_simple(minimal_unit)
        
        # Should still generate some content
        assert len(content.resources) > 0
        assert len(content.engage_tasks) > 0

    def test_network_timeout_simulation(self, sample_learning_unit):
        """Simulate network timeout scenarios."""
        import socket
        
        # Create a mock client that simulates timeout
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = socket.timeout("Network timeout")
        
        # Create generator with timeout-simulating client directly
        from flowgenius.agents.content_generator import ContentGeneratorAgent, ContentGenerationRequest
        generator = ContentGeneratorAgent(mock_client)
        request = ContentGenerationRequest(unit=sample_learning_unit)
        content = generator.generate_complete_content(request)
        
        # Should handle timeout gracefully
        assert content.generation_success is False
        assert len(content.resources) > 0  # Fallback content
        assert len(content.engage_tasks) > 0  # Fallback tasks
        
        # Check if any note mentions error or fallback or timeout
        notes_text = ' '.join(content.generation_notes).lower()
        assert any(keyword in notes_text for keyword in ["error", "fallback", "timeout", "failed"]) 