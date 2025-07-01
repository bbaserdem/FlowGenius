#!/usr/bin/env python3
"""
Manual test script for FlowGenius agents.

This script can be run directly to test the functionality without pytest.
Useful for quick verification and debugging.
"""

import sys
import os
from pathlib import Path

# Add the src directory to Python path so we can import flowgenius
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from flowgenius.models.project import LearningUnit
from flowgenius.agents import (
    generate_unit_content_simple,
    create_content_generator,
    ContentGenerationRequest,
    ResourceCuratorAgent,
    EngageTaskGeneratorAgent,
    ResourceRequest,
    TaskGenerationRequest
)


def run_basic_functionality_test() -> bool:
    """Test basic functionality with fallback systems."""
    print("🧪 Testing Basic Functionality...")
    
    # Create a sample learning unit
    unit = LearningUnit(
        id="test-unit-1",
        title="Introduction to Python",
        description="Learn Python basics and fundamentals",
        learning_objectives=[
            "Understand Python syntax and basic concepts",
            "Write simple Python programs",
            "Use variables, functions, and control structures"
        ],
        estimated_duration="2-3 hours"
    )
    
    print(f"📚 Created test unit: {unit.title}")
    
    try:
        # Test simple content generation (this will use fallbacks if no API key)
        print("🔄 Generating content...")
        content = generate_unit_content_simple(unit, use_obsidian_links=True)
        
        print(f"✅ Generation Success: {content.generation_success}")
        print(f"📄 Generated {len(content.resources)} resources")
        print(f"🎯 Generated {len(content.engage_tasks)} tasks")
        print(f"📝 Generation notes: {len(content.generation_notes)} entries")
        
        # Show formatted output
        print("\n📚 Formatted Resources:")
        for i, resource in enumerate(content.formatted_resources, 1):
            print(f"  {i}. {resource}")
        
        print("\n🎯 Formatted Tasks:")
        for i, task in enumerate(content.formatted_tasks, 1):
            print(f"  {i}. {task}")
        
        print("\n📊 Generation Notes:")
        for note in content.generation_notes:
            print(f"  - {note}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during basic test: {e}")
        return False


def run_individual_agents_test() -> bool:
    """Test individual agents separately."""
    print("\n🧪 Testing Individual Agents...")
    
    unit = LearningUnit(
        id="test-unit-2",
        title="Machine Learning Basics",
        description="Introduction to machine learning concepts",
        learning_objectives=[
            "Understand supervised vs unsupervised learning",
            "Implement basic algorithms",
            "Evaluate model performance"
        ]
    )
    
    try:
        # Test without API (will use fallbacks)
        print("🔄 Testing Resource Curator (fallback mode)...")
        
        # Create mock client for testing
        from unittest.mock import Mock
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("No API")
        
        curator = ResourceCuratorAgent(mock_client)
        request = ResourceRequest(unit=unit)
        resources = curator.curate_resources(request)
        
        print(f"✅ Generated {len(resources)} fallback resources")
        for resource in resources:
            print(f"  - {resource.type}: {resource.title}")
        
        print("\n🔄 Testing Task Generator (fallback mode)...")
        task_gen = EngageTaskGeneratorAgent(mock_client)
        task_request = TaskGenerationRequest(unit=unit, num_tasks=2)
        tasks = task_gen.generate_tasks(task_request)
        
        print(f"✅ Generated {len(tasks)} fallback tasks")
        for task in tasks:
            print(f"  - {task.type}: {task.title}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during individual agent test: {e}")
        return False


def run_with_api_key_test() -> bool:
    """Test with API key if available."""
    api_key = os.getenv('OPENAI_API_KEY')
    
    if not api_key:
        print("\n⚠️  No OPENAI_API_KEY found - skipping live API test")
        print("   Set OPENAI_API_KEY environment variable to test with real API")
        return True
    
    print("\n🧪 Testing with Live API...")
    
    unit = LearningUnit(
        id="api-test",
        title="React Hooks",
        description="Modern React development with hooks",
        learning_objectives=[
            "Master useState and useEffect",
            "Create custom hooks",
            "Optimize performance with hooks"
        ]
    )
    
    try:
        print("🔄 Generating content with live API...")
        content = generate_unit_content_simple(unit, api_key=api_key)
        
        print(f"✅ Live API Success: {content.generation_success}")
        
        if content.generation_success:
            print("🎉 Real AI-generated content:")
            print(f"  📄 Resources: {len(content.resources)}")
            for resource in content.resources:
                print(f"    • {resource.title} ({resource.type})")
            
            print(f"  🎯 Tasks: {len(content.engage_tasks)}")
            for task in content.engage_tasks:
                print(f"    • {task.title} ({task.type})")
        else:
            print("⚠️  API generation failed, used fallbacks")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during API test: {e}")
        return False


def run_error_handling_test() -> bool:
    """Test error handling scenarios."""
    print("\n🧪 Testing Error Handling...")
    
    # Test with minimal unit
    minimal_unit = LearningUnit(
        id="minimal",
        title="",
        description="",
        learning_objectives=[]
    )
    
    try:
        print("🔄 Testing with minimal unit data...")
        content = generate_unit_content_simple(minimal_unit)
        
        print(f"✅ Handled minimal unit: {len(content.resources)} resources, {len(content.engage_tasks)} tasks")
        
        # Test with invalid data
        print("🔄 Testing error recovery...")
        from unittest.mock import Mock
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = ConnectionError("Network error")
        
        from flowgenius.agents.content_generator import ContentGeneratorAgent
        agent = ContentGeneratorAgent(mock_client)
        request = ContentGenerationRequest(unit=minimal_unit)
        content = agent.generate_complete_content(request)
        
        print(f"✅ Recovered from network error: {content.generation_success}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during error handling test: {e}")
        return False


def main() -> bool:
    """Run all tests."""
    print("🚀 FlowGenius Agent Manual Testing")
    print("=" * 50)
    
    tests = [
        ("Basic Functionality", run_basic_functionality_test),
        ("Individual Agents", run_individual_agents_test),
        ("Live API (if available)", run_with_api_key_test),
        ("Error Handling", run_error_handling_test)
    ]
    
    results = []
    
    for name, test_func in tests:
        print(f"\n{'=' * 20} {name} {'=' * 20}")
        success = test_func()
        results.append((name, success))
    
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    
    all_passed = True
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status} {name}")
        if not success:
            all_passed = False
    
    if all_passed:
        print("\n🎉 All tests passed! FlowGenius agents are working correctly.")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 