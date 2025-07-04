"""
Pytest configuration and shared fixtures for FlowGenius tests.
"""

import pytest
from typing import List
from unittest.mock import Mock, patch
from openai import OpenAI

from flowgenius.models.project import LearningUnit, LearningResource, EngageTask


@pytest.fixture
def mock_openai_client() -> Mock:
    """Create a mock OpenAI client for testing."""
    client = Mock(spec=OpenAI)
    
    # Mock the chat.completions.create method
    mock_response = Mock()
    mock_choice = Mock()
    mock_choice.message.content = '{"resources": [], "tasks": []}'
    mock_response.choices = [mock_choice]
    
    client.chat.completions.create.return_value = mock_response
    
    return client


@pytest.fixture
def sample_learning_unit() -> LearningUnit:
    """Create a sample learning unit for testing."""
    return LearningUnit(
        id="unit-1",
        title="Introduction to Python",
        description="Learn Python basics and fundamentals",
        learning_objectives=[
            "Understand Python syntax and basic concepts",
            "Write simple Python programs",
            "Use variables, functions, and control structures"
        ],
        estimated_duration="2-3 hours"
    )


@pytest.fixture
def sample_learning_resources() -> List[LearningResource]:
    """Create sample learning resources for testing."""
    return [
        LearningResource(
            title="Python Basics Tutorial",
            url="https://youtube.com/watch?v=example",
            type="video",
            description="Complete introduction to Python programming",
            estimated_time="20 min"
        ),
        LearningResource(
            title="Python Official Documentation",
            url="https://docs.python.org/3/tutorial/",
            type="article",
            description="Comprehensive Python tutorial",
            estimated_time="45 min"
        )
    ]


@pytest.fixture
def sample_engage_tasks() -> List[EngageTask]:
    """Create sample engage tasks for testing."""
    return [
        EngageTask(
            title="Practice Python Basics",
            description="Write a simple Python program using variables and functions",
            type="practice",
            estimated_time="30 min"
        ),
        EngageTask(
            title="Reflect on Python Applications",
            description="Think about how Python applies to your goals",
            type="reflection",
            estimated_time="15 min"
        )
    ]


@pytest.fixture
def mock_successful_resource_response() -> dict:
    """Mock successful OpenAI response for resource generation."""
    return {
        "resources": [
            {
                "title": "Python Fundamentals Video Course",
                "url": "https://youtube.com/watch?v=example123",
                "type": "video",
                "description": "Comprehensive video course covering Python fundamentals",
                "estimated_time": "2 hours"
            },
            {
                "title": "Python Beginner's Guide",
                "url": "https://realpython.com/python-basics/",
                "type": "article",
                "description": "Complete beginner's guide to Python programming",
                "estimated_time": "30 min"
            }
        ]
    }


@pytest.fixture
def mock_successful_task_response() -> dict:
    """Mock successful OpenAI response for task generation."""
    return {
        "tasks": [
            {
                "title": "Build a Simple Calculator",
                "description": "Create a Python calculator that performs basic arithmetic operations",
                "type": "project",
                "estimated_time": "45 min"
            },
            {
                "title": "Python Syntax Reflection",
                "description": "Write about what you found most interesting in Python syntax",
                "type": "reflection", 
                "estimated_time": "15 min"
            }
        ]
    }


# Nix sandbox environment handling
import os
import tempfile
from pathlib import Path


def pytest_configure(config):
    """Configure pytest for Nix sandbox environment."""
    # Check if we're running in Nix sandbox
    if os.environ.get('HOME') == '/homeless-shelter' or os.environ.get('NIX_BUILD_TOP'):
        # We're in Nix sandbox
        if hasattr(config, 'option') and hasattr(config.option, 'markexpr'):
            config.option.markexpr = "not requires_api_key and not requires_network"
        
        # Create a temporary HOME directory
        temp_home = tempfile.mkdtemp(prefix='flowgenius-test-home-')
        os.environ['HOME'] = temp_home
        
        # Create XDG directories
        config_dir = Path(temp_home) / '.config' / 'flowgenius'
        config_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a dummy API key file to prevent file not found errors
        api_key_file = config_dir / 'openai_key.txt'
        api_key_file.write_text('dummy-key-for-testing')
        api_key_file.chmod(0o600)
        
        # Set environment variables for tests
        os.environ['FLOWGENIUS_TEST_MODE'] = '1'
        os.environ['XDG_CONFIG_HOME'] = str(Path(temp_home) / '.config')
        os.environ['XDG_DOCUMENTS_DIR'] = str(Path(temp_home) / 'Documents') 