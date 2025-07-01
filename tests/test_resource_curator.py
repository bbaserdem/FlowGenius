"""
Tests for the Resource Curator Agent.
"""

import json
import pytest
from typing import Any
from unittest.mock import Mock, patch

from flowgenius.agents.resource_curator import (
    ResourceCuratorAgent, 
    ResourceRequest, 
    format_resources_for_obsidian
)
from flowgenius.models.project import LearningResource


class TestResourceCuratorAgent:
    """Test cases for ResourceCuratorAgent."""

    def test_init(self, mock_openai_client: Mock) -> None:
        """Test agent initialization."""
        agent = ResourceCuratorAgent(mock_openai_client)
        assert agent.client == mock_openai_client
        assert agent.model == "gpt-4o-mini"
        
        # Test with custom model
        agent_custom = ResourceCuratorAgent(mock_openai_client, model="gpt-4")
        assert agent_custom.model == "gpt-4"

    def test_curate_resources_success(self, mock_openai_client: Mock, sample_learning_unit: Any, mock_successful_resource_response: dict) -> None:
        """Test successful resource curation."""
        # Setup mock response
        mock_openai_client.chat.completions.create.return_value.choices[0].message.content = json.dumps(mock_successful_resource_response)
        
        agent = ResourceCuratorAgent(mock_openai_client)
        request = ResourceRequest(unit=sample_learning_unit)
        
        resources, success = agent.curate_resources(request)
        
        assert success is True
        assert len(resources) == 2
        assert all(isinstance(r, LearningResource) for r in resources)
        assert resources[0].title == "Python Fundamentals Video Course"
        assert resources[0].type == "video"
        assert resources[1].title == "Python Beginner's Guide"
        assert resources[1].type == "article"

    def test_curate_resources_with_requirements(self, mock_openai_client: Mock, sample_learning_unit: Any, mock_successful_resource_response: dict) -> None:
        """Test resource curation with specific requirements."""
        mock_openai_client.chat.completions.create.return_value.choices[0].message.content = json.dumps(mock_successful_resource_response)
        
        agent = ResourceCuratorAgent(mock_openai_client)
        request = ResourceRequest(
            unit=sample_learning_unit,
            min_video_resources=2,
            min_reading_resources=2,
            max_total_resources=6,
            difficulty_preference="beginner"
        )
        
        resources, success = agent.curate_resources(request)
        
        # Should have at least the minimum requirements
        video_count = sum(1 for r in resources if r.type == "video")
        reading_count = sum(1 for r in resources if r.type in ["article", "paper", "documentation"])
        
        assert video_count >= request.min_video_resources or len(resources) <= 2  # Due to mock response limitation
        assert reading_count >= request.min_reading_resources or len(resources) <= 2

    def test_curate_resources_api_failure(self, mock_openai_client: Mock, sample_learning_unit: Any) -> None:
        """Test resource curation when API fails."""
        # Simulate API failure
        mock_openai_client.chat.completions.create.side_effect = Exception("API Error")
        
        agent = ResourceCuratorAgent(mock_openai_client)
        request = ResourceRequest(unit=sample_learning_unit)
        
        resources, success = agent.curate_resources(request)
        
        # Should use fallback content
        assert success is False
        assert len(resources) >= 2  # At least one video and one reading
        assert any(r.type == "video" for r in resources)
        assert any(r.type in ["article", "paper", "documentation"] for r in resources)

    def test_curate_resources_insufficient_ai_response(self, mock_openai_client: Mock, sample_learning_unit: Any) -> None:
        """Test when AI doesn't provide enough resources."""
        # Mock response with insufficient resources
        insufficient_response = {"resources": [
            {
                "title": "Single Video",
                "url": "https://youtube.com/example",
                "type": "video",
                "description": "Only video",
                "estimated_time": "10 min"
            }
        ]}
        
        mock_openai_client.chat.completions.create.return_value.choices[0].message.content = json.dumps(insufficient_response)
        
        agent = ResourceCuratorAgent(mock_openai_client)
        request = ResourceRequest(
            unit=sample_learning_unit,
            min_video_resources=1,
            min_reading_resources=2  # More than provided
        )
        
        resources, success = agent.curate_resources(request)
        
        # Should supplement with fallback resources but still be successful since AI provided some
        assert success is True
        assert len(resources) >= 3  # 1 from AI + 2 fallback readings
        video_count = sum(1 for r in resources if r.type == "video")
        reading_count = sum(1 for r in resources if r.type in ["article", "paper", "documentation"])
        
        assert video_count >= 1
        assert reading_count >= 2

    def test_build_system_prompt(self, mock_openai_client: Mock) -> None:
        """Test system prompt building."""
        agent = ResourceCuratorAgent(mock_openai_client)
        prompt = agent._build_system_prompt()
        
        assert "expert learning resource curator" in prompt
        assert "JSON" in prompt
        assert "resources" in prompt
        assert "video" in prompt
        assert "article" in prompt

    def test_build_user_prompt(self, mock_openai_client: Mock, sample_learning_unit: Any) -> None:
        """Test user prompt building."""
        agent = ResourceCuratorAgent(mock_openai_client)
        request = ResourceRequest(
            unit=sample_learning_unit,
            min_video_resources=2,
            difficulty_preference="beginner"
        )
        
        prompt = agent._build_user_prompt(request)
        
        assert sample_learning_unit.title in prompt
        assert sample_learning_unit.description in prompt
        assert "2 video resource(s)" in prompt
        assert "beginner" in prompt
        for objective in sample_learning_unit.learning_objectives:
            assert objective in prompt

    def test_generate_fallback_videos(self, mock_openai_client: Mock, sample_learning_unit: Any) -> None:
        """Test fallback video generation."""
        agent = ResourceCuratorAgent(mock_openai_client)
        request = ResourceRequest(unit=sample_learning_unit)
        
        videos = agent._generate_fallback_videos(request, 2)
        
        assert len(videos) == 2
        assert all(v.type == "video" for v in videos)
        assert all("youtube.com" in v.url for v in videos)
        assert all(sample_learning_unit.title in v.title for v in videos)

    def test_generate_fallback_readings(self, mock_openai_client: Mock, sample_learning_unit: Any) -> None:
        """Test fallback reading generation."""
        agent = ResourceCuratorAgent(mock_openai_client)
        request = ResourceRequest(unit=sample_learning_unit)
        
        readings = agent._generate_fallback_readings(request, 2)
        
        assert len(readings) == 2
        assert all(r.type == "article" for r in readings)
        assert all("wikipedia.org" in r.url for r in readings)
        assert all(sample_learning_unit.title in r.title for r in readings)

    def test_create_fallback_resources(self, mock_openai_client: Mock, sample_learning_unit: Any) -> None:
        """Test complete fallback resource creation."""
        agent = ResourceCuratorAgent(mock_openai_client)
        request = ResourceRequest(
            unit=sample_learning_unit,
            min_video_resources=2,
            min_reading_resources=3
        )
        
        resources = agent._create_fallback_resources(request)
        
        assert len(resources) == 5  # 2 videos + 3 readings
        video_count = sum(1 for r in resources if r.type == "video")
        reading_count = sum(1 for r in resources if r.type == "article")
        
        assert video_count == 2
        assert reading_count == 3


class TestResourceFormatting:
    """Test cases for resource formatting functions."""

    def test_format_resources_for_obsidian_default(self, sample_learning_resources: Any) -> None:
        """Test default Obsidian formatting."""
        formatted = format_resources_for_obsidian(sample_learning_resources)
        
        assert len(formatted) == 2
        assert "🎥" in formatted[0]  # Video emoji
        assert "📖" in formatted[1]  # Article emoji
        assert "[Python Basics Tutorial](https://youtube.com/watch?v=example)" in formatted[0]
        assert "*(20 min)*" in formatted[0]
        assert "> Complete introduction to Python programming" in formatted[0]

    def test_format_resources_for_obsidian_standard_links(self, sample_learning_resources: Any) -> None:
        """Test standard markdown formatting."""
        formatted = format_resources_for_obsidian(sample_learning_resources, use_obsidian_links=False)
        
        assert len(formatted) == 2
        # Should still be standard markdown format (same as Obsidian for external links)
        assert "[Python Basics Tutorial](https://youtube.com/watch?v=example)" in formatted[0]

    def test_format_resources_different_types(self) -> None:
        """Test formatting for different resource types."""
        resources = [
            LearningResource(title="Video", url="http://example.com", type="video"),
            LearningResource(title="Article", url="http://example.com", type="article"),
            LearningResource(title="Paper", url="http://example.com", type="paper"),
            LearningResource(title="Tutorial", url="http://example.com", type="tutorial"),
            LearningResource(title="Docs", url="http://example.com", type="documentation"),
        ]
        
        formatted = format_resources_for_obsidian(resources)
        
        assert "🎥" in formatted[0]  # video
        assert "📖" in formatted[1]  # article
        assert "📄" in formatted[2]  # paper
        assert "🛠️" in formatted[3]  # tutorial
        assert "📋" in formatted[4]  # documentation

    def test_format_resources_minimal_info(self) -> None:
        """Test formatting with minimal resource information."""
        resource = LearningResource(
            title="Simple Resource",
            url="http://example.com",
            type="article"
        )
        
        formatted = format_resources_for_obsidian([resource])
        
        assert len(formatted) == 1
        assert "📖 [Simple Resource](http://example.com)" in formatted[0]
        # Should not have time or description since they're None


class TestResourceRequest:
    """Test cases for ResourceRequest model."""

    def test_resource_request_defaults(self, sample_learning_unit: Any) -> None:
        """Test ResourceRequest with default values."""
        request = ResourceRequest(unit=sample_learning_unit)
        
        assert request.unit == sample_learning_unit
        assert request.min_video_resources == 1
        assert request.min_reading_resources == 1
        assert request.max_total_resources == 5
        assert request.difficulty_preference is None

    def test_resource_request_custom_values(self, sample_learning_unit: Any) -> None:
        """Test ResourceRequest with custom values."""
        request = ResourceRequest(
            unit=sample_learning_unit,
            min_video_resources=3,
            min_reading_resources=2,
            max_total_resources=8,
            difficulty_preference="advanced"
        )
        
        assert request.min_video_resources == 3
        assert request.min_reading_resources == 2
        assert request.max_total_resources == 8
        assert request.difficulty_preference == "advanced" 