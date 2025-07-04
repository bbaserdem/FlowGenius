#!/usr/bin/env python3
"""
Test script to verify LangChain orchestrator integration
"""

import os
import sys
from pathlib import Path
import tempfile

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from flowgenius.models.config import FlowGeniusConfig
from flowgenius.models.project_generator import ProjectGenerator

def test_project_generation():
    """Test that project generation includes resources and tasks."""
    
    # Create temp directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Setup config
        config = FlowGeniusConfig(
            projects_root=temp_dir,
            openai_key_path=os.path.expanduser("~/.config/sops-nix/secrets/openai-apk"),
            link_style="obsidian",
            default_model="gpt-4o-mini"
        )
        
        # Create generator
        generator = ProjectGenerator(config)
        
        try:
            # Create a project
            print("Creating a test project...")
            project = generator.create_project(
                topic="Python Flask Web Development",
                motivation="I want to learn Flask to build a simple blog application",
                target_units=2
            )
            
            print(f"\n✅ Project created: {project.title}")
            
            # Construct the project path correctly
            project_path = Path(temp_dir) / project.project_id
            print(f"📁 Location: {project_path}")
            
            # Debug: List all files in the project
            print("\n📂 Project structure:")
            for file in sorted(project_path.rglob("*")):
                if file.is_file():
                    print(f"  - {file.relative_to(project_path)}")
            
            # Print first unit content for debugging
            first_unit_path = project_path / "units" / "unit-1.md"
            if first_unit_path.exists():
                print("\n📄 Sample unit file (first 50 lines of unit-1.md):")
                content = first_unit_path.read_text()
                lines = content.split('\n')[:50]
                for i, line in enumerate(lines, 1):
                    print(f"{i:3}: {line}")
            
            # Check for resources and tasks
            for i, unit in enumerate(project.units):
                print(f"\n📚 Unit {i+1}: {unit.title}")
                print(f"   Unit ID: {unit.id}")
                
                # Read the unit file
                unit_path = project_path / "units" / f"{unit.id}.md"
                print(f"   Looking for: {unit_path.relative_to(project_path)}")
                
                if unit_path.exists():
                    content = unit_path.read_text()
                    
                    # Check for resources
                    if "<!-- TODO: Add curated resources -->" in content:
                        print("  ❌ Resources: Missing (TODO placeholder found)")
                    elif "## Resources" in content or "## 🔗 Resources" in content:
                        print("  ✅ Resources: Found!")
                        # Count resource links
                        import re
                        links = re.findall(r'\[.*?\]\(.*?\)', content)
                        print(f"     - {len(links)} resource links generated")
                        
                        # Check if they are search links
                        search_links = [l for l in links if "search_query=" in l or "search?q=" in l]
                        if search_links:
                            print(f"     - {len(search_links)} are search queries (as expected)")
                            # Show first search link as example
                            if search_links:
                                first_link = search_links[0]
                                print(f"     - Example: {first_link[:80]}...")
                    
                    # Check for tasks
                    if "<!-- TODO: Add engaging tasks -->" in content:
                        print("  ❌ Tasks: Missing (TODO placeholder found)")
                    elif "## Practice & Engagement" in content or "## 📝 Engage Tasks" in content:
                        print("  ✅ Tasks: Found!")
                        # Count task items - look for numbered list items
                        task_markers = re.findall(r'^\d+\.\s+', content, re.MULTILINE)
                        print(f"     - {len(task_markers)} tasks generated")
                else:
                    print(f"  ❌ Unit file not found!")
            
            print("\n✨ Test completed successfully!")
            return True
            
        except Exception as e:
            print(f"\n❌ Error during project generation: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    test_project_generation() 