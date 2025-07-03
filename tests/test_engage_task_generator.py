"""
Tests for the Engage Task Generator agent.
"""

import pytest
from unittest.mock import Mock, patch
from typing import Any, List

from flowgenius.agents.engage_task_generator import (
    EngageTaskGeneratorAgent,
    TaskGenerationRequest,
    format_tasks_for_markdown
)
from flowgenius.models.project import EngageTask, LearningUnit


class TestEngageTaskGeneratorAgent:
    """Test cases for EngageTaskGeneratorAgent."""

    def test_generate_tasks_success(self, mock_openai_client: Mock, sample_learning_unit: Any) -> None:
        """Test successful task generation."""
        agent = EngageTaskGeneratorAgent(mock_openai_client)
        request = TaskGenerationRequest(unit=sample_learning_unit, num_tasks=2)
        
        # Mock AI response
        mock_response_content = {
            "tasks": [
                {"title": "Task 1", "type": "practice", "description": "Desc 1", "instructions": "Do this", "estimated_time": "15 min"},
                {"title": "Task 2", "type": "project", "description": "Desc 2", "instructions": "Do that", "estimated_time": "30 min"}
            ]
        }
        
        with patch.object(agent, '_generate_tasks_with_validation') as mock_validate:
            mock_validate.return_value = [
                Mock(**t) for t in mock_response_content["tasks"]
            ]
            
            tasks, success = agent.generate_tasks(request)
            
            assert success is True
            assert len(tasks) == 2
            assert all(isinstance(t, EngageTask) for t in tasks)
            assert tasks[0].title == "Task 1"
            assert tasks[1].type == "project"

    def test_generate_tasks_api_failure(self, mock_openai_client: Mock, sample_learning_unit: Any) -> None:
        """Test task generation when the AI call fails."""
        agent = EngageTaskGeneratorAgent(mock_openai_client)
        request = TaskGenerationRequest(unit=sample_learning_unit)
        
        with patch.object(agent, '_generate_tasks_with_validation', return_value=[]) as mock_validate:
            tasks, success = agent.generate_tasks(request)
            
            assert success is False
            assert len(tasks) > 0  # Should return fallback tasks
            assert all(isinstance(t, EngageTask) for t in tasks)

    def test_create_fallback_tasks(self, mock_openai_client: Mock, sample_learning_unit: Any) -> None:
        """Test fallback task creation."""
        agent = EngageTaskGeneratorAgent(mock_openai_client)
        
        tasks = agent._create_fallback_tasks(sample_learning_unit, 2)
        
        assert len(tasks) == 2
        assert all(isinstance(t, EngageTask) for t in tasks)
        assert "Reflect" in tasks[0].title
        assert "Practice" in tasks[1].title


class TestTaskFormatting:
    """Test cases for task formatting utility."""
    
    def test_format_tasks_for_markdown(self) -> None:
        """Test markdown formatting for engage tasks."""
        formatted = format_tasks_for_markdown([
            EngageTask(title="Task One", type="practice", description="Practice this.", estimated_time="10 min"),
            EngageTask(title="Task Two", type="project", description="Build that.", estimated_time="1-2 hours")
        ])
        
        assert len(formatted) == 2
        assert "1. 🛠️ **Task One**" in formatted[0]
        assert "*(10 min)*" in formatted[0]
        assert "Practice this" in formatted[0]
        assert "2. 🎯 **Task Two**" in formatted[1]
        assert "*(1-2 hours)*" in formatted[1]
        assert "Build that" in formatted[1] 