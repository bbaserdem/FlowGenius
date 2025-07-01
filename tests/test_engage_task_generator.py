"""
Tests for the Engage Task Generator Agent.
"""

import json
import pytest
from unittest.mock import Mock, patch

from flowgenius.agents.engage_task_generator import (
    EngageTaskGeneratorAgent,
    TaskGenerationRequest,
    format_tasks_for_markdown,
    suggest_task_for_objectives
)
from flowgenius.models.project import EngageTask


class TestEngageTaskGeneratorAgent:
    """Test cases for EngageTaskGeneratorAgent."""

    def test_init(self, mock_openai_client):
        """Test agent initialization."""
        agent = EngageTaskGeneratorAgent(mock_openai_client)
        assert agent.client == mock_openai_client
        assert agent.model == "gpt-4o-mini"
        
        # Test with custom model
        agent_custom = EngageTaskGeneratorAgent(mock_openai_client, model="gpt-4")
        assert agent_custom.model == "gpt-4"

    def test_generate_tasks_success(self, mock_openai_client, sample_learning_unit, mock_successful_task_response):
        """Test successful task generation."""
        # Setup mock response
        mock_openai_client.chat.completions.create.return_value.choices[0].message.content = json.dumps(mock_successful_task_response)
        
        agent = EngageTaskGeneratorAgent(mock_openai_client)
        request = TaskGenerationRequest(unit=sample_learning_unit)
        
        tasks = agent.generate_tasks(request)
        
        assert len(tasks) == 2
        assert all(isinstance(t, EngageTask) for t in tasks)
        assert tasks[0].title == "Build a Simple Calculator"
        assert tasks[0].type == "project"
        assert tasks[1].title == "Python Syntax Reflection"
        assert tasks[1].type == "reflection"

    def test_generate_tasks_with_resources(self, mock_openai_client, sample_learning_unit, sample_learning_resources, mock_successful_task_response):
        """Test task generation with resource context."""
        mock_openai_client.chat.completions.create.return_value.choices[0].message.content = json.dumps(mock_successful_task_response)
        
        agent = EngageTaskGeneratorAgent(mock_openai_client)
        request = TaskGenerationRequest(
            unit=sample_learning_unit,
            resources=sample_learning_resources,
            num_tasks=2,
            difficulty_preference="beginner",
            focus_on_application=True
        )
        
        tasks = agent.generate_tasks(request)
        
        assert len(tasks) == 2
        # Verify that OpenAI was called with the correct prompt including resources
        mock_openai_client.chat.completions.create.assert_called_once()

    def test_generate_tasks_api_failure(self, mock_openai_client, sample_learning_unit):
        """Test task generation when API fails."""
        # Simulate API failure
        mock_openai_client.chat.completions.create.side_effect = Exception("API Error")
        
        agent = EngageTaskGeneratorAgent(mock_openai_client)
        request = TaskGenerationRequest(unit=sample_learning_unit, num_tasks=2)
        
        tasks = agent.generate_tasks(request)
        
        # Should still return fallback tasks
        assert len(tasks) == 2
        assert all(isinstance(t, EngageTask) for t in tasks)

    def test_generate_tasks_insufficient_ai_response(self, mock_openai_client, sample_learning_unit):
        """Test when AI doesn't provide enough tasks."""
        # Mock response with insufficient tasks
        insufficient_response = {"tasks": [
            {
                "title": "Single Task",
                "description": "Only one task",
                "type": "reflection",
                "estimated_time": "10 min"
            }
        ]}
        
        mock_openai_client.chat.completions.create.return_value.choices[0].message.content = json.dumps(insufficient_response)
        
        agent = EngageTaskGeneratorAgent(mock_openai_client)
        request = TaskGenerationRequest(unit=sample_learning_unit, num_tasks=3)
        
        tasks = agent.generate_tasks(request)
        
        # Should supplement with fallback tasks
        assert len(tasks) == 3  # 1 from AI + 2 fallback
        assert tasks[0].title == "Single Task"

    def test_build_system_prompt(self, mock_openai_client):
        """Test system prompt building."""
        agent = EngageTaskGeneratorAgent(mock_openai_client)
        prompt = agent._build_system_prompt()
        
        assert "expert learning designer" in prompt
        assert "active learning tasks" in prompt
        assert "JSON" in prompt
        assert "reflection" in prompt
        assert "practice" in prompt
        assert "project" in prompt
        assert "quiz" in prompt
        assert "experiment" in prompt

    def test_build_user_prompt(self, mock_openai_client, sample_learning_unit, sample_learning_resources):
        """Test user prompt building."""
        agent = EngageTaskGeneratorAgent(mock_openai_client)
        request = TaskGenerationRequest(
            unit=sample_learning_unit,
            resources=sample_learning_resources,
            num_tasks=2,
            difficulty_preference="beginner",
            focus_on_application=True
        )
        
        prompt = agent._build_user_prompt(request)
        
        assert sample_learning_unit.title in prompt
        assert sample_learning_unit.description in prompt
        assert "2 engaging task(s)" in prompt
        assert "beginner" in prompt
        assert "real-world application" in prompt
        
        # Should include resources
        assert "Available Resources:" in prompt
        assert sample_learning_resources[0].title in prompt
        
        for objective in sample_learning_unit.learning_objectives:
            assert objective in prompt

    def test_build_user_prompt_no_resources(self, mock_openai_client, sample_learning_unit):
        """Test user prompt building without resources."""
        agent = EngageTaskGeneratorAgent(mock_openai_client)
        request = TaskGenerationRequest(unit=sample_learning_unit)
        
        prompt = agent._build_user_prompt(request)
        
        assert "Available Resources:" not in prompt

    def test_generate_fallback_tasks(self, mock_openai_client, sample_learning_unit):
        """Test fallback task generation."""
        agent = EngageTaskGeneratorAgent(mock_openai_client)
        request = TaskGenerationRequest(unit=sample_learning_unit)
        
        tasks = agent._generate_fallback_tasks(request, 3)
        
        assert len(tasks) == 3
        assert all(isinstance(t, EngageTask) for t in tasks)
        
        # Should cycle through templates
        types = [t.type for t in tasks]
        assert "reflection" in types
        assert "practice" in types
        assert "project" in types

    def test_create_fallback_tasks(self, mock_openai_client, sample_learning_unit):
        """Test complete fallback task creation."""
        agent = EngageTaskGeneratorAgent(mock_openai_client)
        request = TaskGenerationRequest(unit=sample_learning_unit, num_tasks=2)
        
        tasks = agent._create_fallback_tasks(request)
        
        assert len(tasks) == 2
        assert tasks[0].type == "reflection"
        assert tasks[1].type == "practice"
        assert all(sample_learning_unit.title in t.title for t in tasks)


class TestTaskFormatting:
    """Test cases for task formatting functions."""

    def test_format_tasks_for_markdown(self, sample_engage_tasks):
        """Test markdown formatting for tasks."""
        formatted = format_tasks_for_markdown(sample_engage_tasks)
        
        assert len(formatted) == 2
        assert "1. 🛠️ **Practice Python Basics**" in formatted[0]
        assert "*(30 min)*" in formatted[0]
        assert "Write a simple Python program" in formatted[0]
        
        assert "2. 🤔 **Reflect on Python Applications**" in formatted[1]
        assert "*(15 min)*" in formatted[1]
        assert "Think about how Python applies" in formatted[1]

    def test_format_tasks_different_types(self):
        """Test formatting for different task types."""
        tasks = [
            EngageTask(title="Reflect", description="Think", type="reflection"),
            EngageTask(title="Practice", description="Do", type="practice"),
            EngageTask(title="Project", description="Build", type="project"),
            EngageTask(title="Quiz", description="Test", type="quiz"),
            EngageTask(title="Experiment", description="Try", type="experiment"),
        ]
        
        formatted = format_tasks_for_markdown(tasks)
        
        assert "🤔" in formatted[0]  # reflection
        assert "🛠️" in formatted[1]  # practice
        assert "🎯" in formatted[2]  # project
        assert "❓" in formatted[3]  # quiz
        assert "🧪" in formatted[4]  # experiment

    def test_format_tasks_minimal_info(self):
        """Test formatting with minimal task information."""
        task = EngageTask(
            title="Simple Task",
            description="Do something",
            type="practice"
        )
        
        formatted = format_tasks_for_markdown([task])
        
        assert len(formatted) == 1
        assert "1. 🛠️ **Simple Task**" in formatted[0]
        assert "Do something" in formatted[0]
        # Should not have time since it's None


class TestSuggestTaskForObjectives:
    """Test cases for objective-based task suggestion."""

    def test_suggest_task_apply_objectives(self):
        """Test task suggestion for application-focused objectives."""
        objectives = [
            "Apply Python concepts to real problems",
            "Use variables and functions effectively",
            "Implement basic algorithms"
        ]
        
        task = suggest_task_for_objectives(objectives, "Python Basics")
        
        assert task.type == "project"
        assert "Apply" in task.title
        assert "Python Basics" in task.title
        assert "practical example" in task.description

    def test_suggest_task_analyze_objectives(self):
        """Test task suggestion for analysis-focused objectives."""
        objectives = [
            "Analyze different programming paradigms",
            "Evaluate the effectiveness of algorithms",
            "Compare Python with other languages"
        ]
        
        task = suggest_task_for_objectives(objectives, "Programming Concepts")
        
        assert task.type == "reflection"
        assert "Analyze" in task.title
        assert "Programming Concepts" in task.title
        assert "analysis" in task.description

    def test_suggest_task_practice_objectives(self):
        """Test task suggestion for practice-focused objectives."""
        objectives = [
            "Practice writing Python functions",
            "Exercise problem-solving skills",
            "Solve basic programming challenges"
        ]
        
        task = suggest_task_for_objectives(objectives, "Python Functions")
        
        assert task.type == "practice"
        assert "Practice" in task.title
        assert "Python Functions" in task.title
        assert "exercises" in task.description

    def test_suggest_task_default_objectives(self):
        """Test task suggestion for general objectives."""
        objectives = [
            "Understand basic concepts",
            "Learn fundamental principles",
            "Know the basics"
        ]
        
        task = suggest_task_for_objectives(objectives, "General Topic")
        
        assert task.type == "reflection"
        assert "Reflect" in task.title
        assert "General Topic" in task.title
        assert "reflect" in task.description

    def test_suggest_task_empty_objectives(self):
        """Test task suggestion with empty objectives."""
        task = suggest_task_for_objectives([], "Empty Topic")
        
        assert task.type == "reflection"
        assert "Empty Topic" in task.title


class TestTaskGenerationRequest:
    """Test cases for TaskGenerationRequest model."""

    def test_task_generation_request_defaults(self, sample_learning_unit):
        """Test TaskGenerationRequest with default values."""
        request = TaskGenerationRequest(unit=sample_learning_unit)
        
        assert request.unit == sample_learning_unit
        assert request.resources is None
        assert request.num_tasks == 1
        assert request.difficulty_preference is None
        assert request.focus_on_application is True

    def test_task_generation_request_custom_values(self, sample_learning_unit, sample_learning_resources):
        """Test TaskGenerationRequest with custom values."""
        request = TaskGenerationRequest(
            unit=sample_learning_unit,
            resources=sample_learning_resources,
            num_tasks=3,
            difficulty_preference="advanced",
            focus_on_application=False
        )
        
        assert request.resources == sample_learning_resources
        assert request.num_tasks == 3
        assert request.difficulty_preference == "advanced"
        assert request.focus_on_application is False 