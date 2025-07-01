#!/usr/bin/env python3
"""
Manual Testing Script for MarkdownRenderer

This script demonstrates and validates the MarkdownRenderer functionality
through interactive testing scenarios.
"""

import tempfile
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

from flowgenius.models.renderer import MarkdownRenderer
from flowgenius.models.config import FlowGeniusConfig
from flowgenius.models.project import (
    LearningProject, LearningUnit, ProjectMetadata, 
    LearningResource, EngageTask
)
from flowgenius.agents.content_generator import GeneratedContent


def create_sample_project() -> LearningProject:
    """Create a sample learning project for testing."""
    print("🏗️  Creating sample project...")
    
    units = [
        LearningUnit(
            id="unit-1",
            title="Introduction to Python",
            description="Learn Python basics including syntax, variables, and data types",
            learning_objectives=[
                "Understand Python syntax and structure",
                "Work with variables and basic data types",
                "Write simple Python programs"
            ],
            status="pending",
            estimated_duration="3 hours"
        ),
        LearningUnit(
            id="unit-2", 
            title="Python Data Structures",
            description="Master Python lists, dictionaries, sets, and tuples",
            learning_objectives=[
                "Use lists and dictionaries effectively",
                "Understand when to use different data structures",
                "Manipulate collections of data"
            ],
            status="pending",
            prerequisites=["unit-1"],
            estimated_duration="4 hours"
        ),
        LearningUnit(
            id="unit-3",
            title="Functions and Modules",
            description="Create reusable code with functions and modules",
            learning_objectives=[
                "Define and call functions",
                "Understand scope and parameters",
                "Organize code into modules"
            ],
            status="pending",
            prerequisites=["unit-2"],
            estimated_duration="5 hours"
        )
    ]
    
    metadata = ProjectMetadata(
        id="python-basics-manual-test",
        title="Python Programming Fundamentals",
        topic="Python Programming",
        motivation="Build a solid foundation in Python for web development and data science",
        created_at=datetime.now(),
        estimated_total_time="12 hours",
        difficulty_level="beginner",
        tags=["python", "programming", "beginner"]
    )
    
    project = LearningProject(metadata=metadata, units=units)
    print(f"✅ Created project '{project.title}' with {len(project.units)} units")
    return project


def create_sample_generated_content() -> Dict[str, GeneratedContent]:
    """Create sample generated content for testing."""
    print("🤖 Creating sample generated content...")
    
    # Content for unit-1
    unit1_resources = [
        LearningResource(
            title="Python.org Official Tutorial",
            url="https://docs.python.org/3/tutorial/",
            type="documentation",
            description="Official Python tutorial covering basics",
            estimated_time="2 hours"
        ),
        LearningResource(
            title="Automate the Boring Stuff - Chapter 1",
            url="https://automatetheboringstuff.com/2e/chapter1/",
            type="book",
            description="Free online book chapter on Python basics",
            estimated_time="45 minutes"
        )
    ]
    
    unit1_tasks = [
        EngageTask(
            title="Hello World Variations",
            description="Write 5 different 'Hello World' programs with variations",
            type="practice",
            estimated_time="30 minutes"
        ),
        EngageTask(
            title="Variable Playground",
            description="Create variables of different types and experiment with operations",
            type="experiment",
            estimated_time="45 minutes"
        )
    ]
    
    unit1_content = GeneratedContent(
        unit_id="unit-1",
        resources=unit1_resources,
        engage_tasks=unit1_tasks,
        formatted_resources=[
            "📖 [Python.org Official Tutorial](https://docs.python.org/3/tutorial/) - Official Python tutorial covering basics (2 hours)",
            "📚 [Automate the Boring Stuff - Chapter 1](https://automatetheboringstuff.com/2e/chapter1/) - Free online book chapter on Python basics (45 minutes)"
        ],
        formatted_tasks=[
            "🎯 **Hello World Variations** - Write 5 different 'Hello World' programs with variations (30 minutes)",
            "🧪 **Variable Playground** - Create variables of different types and experiment with operations (45 minutes)"
        ],
        generation_success=True,
        generation_notes=[
            "Generated successfully using AI content curator",
            "Resources focus on official documentation and practical examples",
            "Tasks are beginner-friendly with hands-on practice"
        ]
    )
    
    # Content for unit-2 (partial generation)
    unit2_resources = [
        LearningResource(
            title="Real Python - Python Lists and Tuples",
            url="https://realpython.com/python-lists-tuples/",
            type="article",
            description="Comprehensive guide to Python sequences",
            estimated_time="1 hour"
        )
    ]
    
    unit2_tasks = [
        EngageTask(
            title="Build a Contact Manager",
            description="Create a simple contact manager using dictionaries",
            type="project",
            estimated_time="2 hours"
        )
    ]
    
    unit2_content = GeneratedContent(
        unit_id="unit-2",
        resources=unit2_resources,
        engage_tasks=unit2_tasks,
        formatted_resources=[
            "📰 [Real Python - Python Lists and Tuples](https://realpython.com/python-lists-tuples/) - Comprehensive guide to Python sequences (1 hour)"
        ],
        formatted_tasks=[
            "🏗️ **Build a Contact Manager** - Create a simple contact manager using dictionaries (2 hours)"
        ],
        generation_success=True,
        generation_notes=[
            "Partial generation - focused on most important resources",
            "Project-based task for practical application"
        ]
    )
    
    content_map = {
        "unit-1": unit1_content,
        "unit-2": unit2_content
        # unit-3 intentionally left without generated content
    }
    
    print(f"✅ Created generated content for {len(content_map)} units")
    return content_map


def test_basic_rendering(renderer: MarkdownRenderer, project: LearningProject, output_dir: Path):
    """Test basic project rendering functionality."""
    print("\n🧪 Test 1: Basic Project Rendering")
    print("=" * 50)
    
    def progress_callback(message: str, current: int, total: int):
        print(f"📊 Progress ({current}/{total}): {message}")
    
    # Render the project
    renderer.render_project_files(
        project, 
        output_dir,
        progress_callback=progress_callback
    )
    
    # Verify files were created
    files_created = []
    for file_path in [
        output_dir / "project.json",
        output_dir / "toc.md", 
        output_dir / "README.md",
        output_dir / "units" / "unit-1.md",
        output_dir / "units" / "unit-2.md",
        output_dir / "units" / "unit-3.md"
    ]:
        if file_path.exists():
            files_created.append(file_path.name)
            print(f"✅ Created: {file_path.name}")
        else:
            print(f"❌ Missing: {file_path.name}")
    
    print(f"\n📈 Summary: {len(files_created)}/6 files created successfully")
    return files_created


def test_content_integration(renderer: MarkdownRenderer, project: LearningProject, 
                           content_map: Dict[str, GeneratedContent], output_dir: Path):
    """Test rendering with generated content integration."""
    print("\n🧪 Test 2: Content Integration")
    print("=" * 50)
    
    # Render with content integration
    renderer.render_project_files(
        project,
        output_dir,
        unit_content_map=content_map
    )
    
    # Check TOC for content generation status
    toc_content = (output_dir / "toc.md").read_text()
    if "content_generated: 2/3 units" in toc_content:
        print("✅ TOC shows correct content generation status")
    else:
        print("❌ TOC content generation status incorrect")
    
    # Check unit-1 for generated content
    unit1_content = (output_dir / "units" / "unit-1.md").read_text()
    if "Python.org Official Tutorial" in unit1_content and "Hello World Variations" in unit1_content:
        print("✅ Unit-1 contains generated resources and tasks")
    else:
        print("❌ Unit-1 missing generated content")
    
    # Check unit-3 for placeholder content (no generated content)
    unit3_content = (output_dir / "units" / "unit-3.md").read_text()
    if "TODO: Add curated resources" in unit3_content:
        print("✅ Unit-3 shows placeholder content correctly")
    else:
        print("❌ Unit-3 placeholder content incorrect")


def test_link_styles():
    """Test different link style configurations."""
    print("\n🧪 Test 3: Link Style Handling")
    print("=" * 50)
    
    project = create_sample_project()
    
    # Test Obsidian style
    obsidian_config = FlowGeniusConfig(
        openai_key_path=Path("/tmp/test"),
        projects_root=Path("/tmp"),
        link_style="obsidian"
    )
    obsidian_renderer = MarkdownRenderer(obsidian_config)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir)
        (output_dir / "units").mkdir()
        
        obsidian_renderer.render_project_files(project, output_dir)
        
        toc_content = (output_dir / "toc.md").read_text()
        readme_content = (output_dir / "README.md").read_text()
        
        if "[[units/unit-1.md|Introduction to Python]]" in toc_content:
            print("✅ Obsidian links in TOC working")
        else:
            print("❌ Obsidian links in TOC failed")
            
        if "[[units/unit-1.md|Introduction to Python]]" in readme_content:
            print("✅ Obsidian links in README working")
        else:
            print("❌ Obsidian links in README failed")
    
    # Test Markdown style
    markdown_config = FlowGeniusConfig(
        openai_key_path=Path("/tmp/test"),
        projects_root=Path("/tmp"),
        link_style="markdown"
    )
    markdown_renderer = MarkdownRenderer(markdown_config)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir)
        (output_dir / "units").mkdir()
        
        markdown_renderer.render_project_files(project, output_dir)
        
        toc_content = (output_dir / "toc.md").read_text()
        readme_content = (output_dir / "README.md").read_text()
        
        if "[Introduction to Python](units/unit-1.md)" in toc_content:
            print("✅ Markdown links in TOC working")
        else:
            print("❌ Markdown links in TOC failed")
            
        if "[Introduction to Python](units/unit-1.md)" in readme_content:
            print("✅ Markdown links in README working")
        else:
            print("❌ Markdown links in README failed")


def test_progress_tracking(renderer: MarkdownRenderer, project: LearningProject, output_dir: Path):
    """Test progress tracking functionality."""
    print("\n🧪 Test 4: Progress Tracking")
    print("=" * 50)
    
    # First render the project
    renderer.render_project_files(project, output_dir)
    
    # Test progress info
    progress_info = renderer.get_rendering_progress_info(project)
    print(f"📊 Progress info: {progress_info['total_files']} total files")
    print(f"📊 File breakdown: {progress_info['file_breakdown']}")
    
    # Test unit progress tracking
    print("\n🔄 Testing unit progress updates...")
    
    def progress_callback(message: str, current: int, total: int):
        print(f"  📊 {message}")
    
    # Update unit-1 to completed
    completion_date = datetime(2024, 1, 15, 14, 30, 0)
    renderer.track_unit_progress(
        output_dir,
        "unit-1", 
        "completed",
        completion_date,
        progress_callback
    )
    
    # Verify the update
    unit1_content = (output_dir / "units" / "unit-1.md").read_text()
    if "status: completed" in unit1_content and "completed_date: 2024-01-15T14:30:00" in unit1_content:
        print("✅ Unit progress tracking working correctly")
    else:
        print("❌ Unit progress tracking failed")


def test_edge_cases():
    """Test edge cases like empty projects."""
    print("\n🧪 Test 5: Edge Cases")
    print("=" * 50)
    
    # Create empty project
    empty_metadata = ProjectMetadata(
        id="empty-test",
        title="Empty Test Project",
        topic="Testing",
        created_at=datetime.now()
    )
    empty_project = LearningProject(metadata=empty_metadata, units=[])
    
    config = FlowGeniusConfig(
        openai_key_path=Path("/tmp/test"),
        projects_root=Path("/tmp"),
        link_style="markdown"
    )
    renderer = MarkdownRenderer(config)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir)
        (output_dir / "units").mkdir()
        
        try:
            renderer.render_project_files(empty_project, output_dir)
            print("✅ Empty project rendering successful")
            
            # Check content
            toc_content = (output_dir / "toc.md").read_text()
            readme_content = (output_dir / "README.md").read_text()
            
            if "no learning units" in toc_content and "Add units" in readme_content:
                print("✅ Empty project content handled correctly")
            else:
                print("❌ Empty project content incorrect")
                
        except Exception as e:
            print(f"❌ Empty project rendering failed: {e}")


def display_sample_output(output_dir: Path):
    """Display sample output for manual inspection."""
    print("\n📄 Sample Output Preview")
    print("=" * 50)
    
    # Show TOC content (first 20 lines)
    toc_path = output_dir / "toc.md"
    if toc_path.exists():
        print("\n📋 TOC.md (first 20 lines):")
        print("-" * 30)
        lines = toc_path.read_text().split('\n')
        for i, line in enumerate(lines[:20], 1):
            print(f"{i:2d}: {line}")
        if len(lines) > 20:
            print(f"    ... ({len(lines) - 20} more lines)")
    
    # Show unit file content (first 15 lines)
    unit1_path = output_dir / "units" / "unit-1.md"
    if unit1_path.exists():
        print("\n📘 unit-1.md (first 15 lines):")
        print("-" * 30)
        lines = unit1_path.read_text().split('\n')
        for i, line in enumerate(lines[:15], 1):
            print(f"{i:2d}: {line}")
        if len(lines) > 15:
            print(f"    ... ({len(lines) - 15} more lines)")


def main():
    """Run all manual tests."""
    print("🚀 MarkdownRenderer Manual Testing Suite")
    print("=" * 60)
    
    # Create test data
    project = create_sample_project()
    content_map = create_sample_generated_content()
    
    # Create config (using Obsidian style for main tests)
    config = FlowGeniusConfig(
        openai_key_path=Path("/tmp/test_key"),
        projects_root=Path("/tmp/projects"),
        link_style="obsidian",
        default_model="gpt-4o-mini"
    )
    renderer = MarkdownRenderer(config)
    
    # Use a persistent temp directory for inspection
    with tempfile.TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir)
        print(f"📁 Test output directory: {output_dir}")
        
        # Create units subdirectory
        (output_dir / "units").mkdir()
        
        # Run tests
        test_basic_rendering(renderer, project, output_dir)
        test_content_integration(renderer, project, content_map, output_dir)
        test_progress_tracking(renderer, project, output_dir)
        
        # Display sample output
        display_sample_output(output_dir)
        
        # Ask user if they want to keep files for inspection
        try:
            keep_files = input("\n❓ Keep test files for manual inspection? (y/N): ").lower().strip()
            if keep_files in ['y', 'yes']:
                import shutil
                permanent_dir = Path.cwd() / "manual_test_output"
                if permanent_dir.exists():
                    shutil.rmtree(permanent_dir)
                shutil.copytree(output_dir, permanent_dir)
                print(f"📁 Test files saved to: {permanent_dir}")
        except (KeyboardInterrupt, EOFError):
            print("\n⏭️  Skipping file preservation")
    
    # Run tests that create their own temp directories
    test_link_styles()
    test_edge_cases()
    
    print("\n🎉 Manual testing complete!")
    print("\nFeatures tested:")
    print("✅ Basic project rendering")
    print("✅ Generated content integration") 
    print("✅ Progress tracking and callbacks")
    print("✅ Link style handling (Obsidian & Markdown)")
    print("✅ Edge case handling (empty projects)")
    print("✅ Unit progress updates")
    print("✅ File structure validation")


if __name__ == "__main__":
    main() 