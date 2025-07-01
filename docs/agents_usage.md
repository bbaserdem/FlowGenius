# FlowGenius Agents Usage Guide

This guide covers the usage of FlowGenius AI agents for content generation, including resource curation and engage task generation.

## Overview

FlowGenius provides three main agents for enhanced learning content generation:

- **ResourceCuratorAgent**: Finds and curates learning resources (videos, articles, papers)
- **EngageTaskGeneratorAgent**: Creates engaging, active learning tasks
- **ContentGeneratorAgent**: Integrated agent that combines both for complete content generation

## Quick Start

### Simple Content Generation

```python
from flowgenius.agents import generate_unit_content_simple
from flowgenius.models.project import LearningUnit

# Create a learning unit
unit = LearningUnit(
    id="unit-1",
    title="Introduction to Python",
    description="Learn Python basics and fundamentals",
    learning_objectives=[
        "Understand Python syntax and basic concepts",
        "Write simple Python programs",
        "Use variables, functions, and control structures"
    ]
)

# Generate complete content (requires OPENAI_API_KEY environment variable)
content = generate_unit_content_simple(unit, use_obsidian_links=True)

print(f"Generated {len(content.resources)} resources")
print(f"Generated {len(content.engage_tasks)} tasks")
print("\nFormatted resources:")
for resource in content.formatted_resources:
    print(resource)
print("\nFormatted tasks:")
for task in content.formatted_tasks:
    print(task)
```

## Resource Curator Agent

### Basic Usage

```python
from flowgenius.agents import ResourceCuratorAgent, ResourceRequest
from openai import OpenAI

# Initialize the agent
client = OpenAI(api_key="your-api-key")
curator = ResourceCuratorAgent(client)

# Create a resource request
request = ResourceRequest(
    unit=unit,
    min_video_resources=2,
    min_reading_resources=2,
    max_total_resources=6,
    difficulty_preference="beginner"
)

# Generate resources
resources = curator.curate_resources(request)

for resource in resources:
    print(f"{resource.type}: {resource.title}")
    print(f"  URL: {resource.url}")
    print(f"  Time: {resource.estimated_time}")
    print(f"  Description: {resource.description}")
    print()
```

### Obsidian Formatting

```python
from flowgenius.agents import format_resources_for_obsidian

# Format for Obsidian
obsidian_links = format_resources_for_obsidian(resources, use_obsidian_links=True)

for link in obsidian_links:
    print(link)
```

Example output:
```markdown
🎥 [Python Basics Tutorial](https://youtube.com/watch?v=example) *(20 min)*
  > Complete introduction to Python programming fundamentals

📖 [Python Official Documentation](https://docs.python.org/3/tutorial/) *(45 min)*
  > Comprehensive Python tutorial from the official documentation
```

## Engage Task Generator Agent

### Basic Usage

```python
from flowgenius.agents import EngageTaskGeneratorAgent, TaskGenerationRequest

# Initialize the agent
task_generator = EngageTaskGeneratorAgent(client)

# Create a task generation request
request = TaskGenerationRequest(
    unit=unit,
    resources=resources,  # Optional: include resources for context
    num_tasks=2,
    difficulty_preference="beginner",
    focus_on_application=True
)

# Generate tasks
tasks = task_generator.generate_tasks(request)

for task in tasks:
    print(f"Task: {task.title} ({task.type})")
    print(f"Description: {task.description}")
    print(f"Estimated time: {task.estimated_time}")
    print()
```

### Task Formatting

```python
from flowgenius.agents import format_tasks_for_markdown

# Format for markdown
formatted_tasks = format_tasks_for_markdown(tasks)

for task_md in formatted_tasks:
    print(task_md)
```

Example output:
```markdown
1. 🛠️ **Practice Python Basics** *(30 min)*
   Write a simple Python program that uses variables, functions, and loops to solve a practical problem.

2. 🤔 **Reflect on Python Applications** *(15 min)*
   Think about how Python could be useful in your field or interests. Write down 3 specific use cases.
```

### Non-AI Task Suggestion

```python
from flowgenius.agents import suggest_task_for_objectives

# Generate a task without AI based on learning objectives
task = suggest_task_for_objectives(unit.learning_objectives, unit.title)
print(f"Suggested task: {task.title} ({task.type})")
```

## Content Generator Agent (Integrated)

### Basic Integration

```python
from flowgenius.agents import ContentGeneratorAgent, ContentGenerationRequest

# Initialize integrated agent
content_generator = ContentGeneratorAgent(client)

# Create comprehensive request
request = ContentGenerationRequest(
    unit=unit,
    min_video_resources=1,
    min_reading_resources=1,
    max_total_resources=4,
    num_engage_tasks=2,
    difficulty_preference="beginner",
    focus_on_application=True,
    use_obsidian_links=True
)

# Generate complete content
content = content_generator.generate_complete_content(request)

print(f"Success: {content.generation_success}")
print(f"Notes: {content.generation_notes}")
```

### In-Place Unit Population

```python
# Populate a unit directly
updated_unit = content_generator.populate_unit_with_content(unit)

print(f"Unit now has {len(updated_unit.resources)} resources")
print(f"Unit now has {len(updated_unit.engage_tasks)} tasks")
```

### Batch Processing

```python
# Process multiple units at once
units = [unit1, unit2, unit3]

base_request = ContentGenerationRequest(
    unit=units[0],  # Will be overridden for each unit
    min_video_resources=1,
    min_reading_resources=1,
    num_engage_tasks=1
)

results = content_generator.batch_populate_units(units, base_request)

for i, result in enumerate(results):
    print(f"Unit {i+1}: {len(result.resources)} resources, {len(result.engage_tasks)} tasks")
```

## Factory Functions

### Simple Agent Creation

```python
from flowgenius.agents import create_content_generator

# Create with API key
generator = create_content_generator(api_key="your-key", model="gpt-4o-mini")

# Create with environment variable (OPENAI_API_KEY)
generator = create_content_generator()
```

## Error Handling and Fallbacks

All agents include robust error handling:

```python
# Even without internet or API access, agents provide fallback content
try:
    content = generate_unit_content_simple(unit)
    if content.generation_success:
        print("AI generation successful!")
    else:
        print("Used fallback generation")
        print(f"Fallback notes: {content.generation_notes}")
except Exception as e:
    print(f"Generation failed: {e}")
```

## Integration with Project Generation

### Enhancing Existing Projects

```python
from flowgenius.models.project_generator import ProjectGenerator
from flowgenius.agents import create_content_generator

# Create a project with basic structure
generator = ProjectGenerator(projects_root="./projects", openai_client=client)
project = generator.create_project("Advanced Python", "to build better applications")

# Enhance units with resources and tasks
content_gen = create_content_generator()

for unit in project.units:
    content_gen.populate_unit_with_content(unit)
    print(f"Enhanced {unit.title} with content")

# Save enhanced project
generator.save_project(project)
```

## Configuration Options

### ResourceRequest Parameters

- `min_video_resources`: Minimum number of video resources (default: 1)
- `min_reading_resources`: Minimum number of reading resources (default: 1)
- `max_total_resources`: Maximum total resources (default: 5)
- `difficulty_preference`: "beginner", "intermediate", or "advanced"

### TaskGenerationRequest Parameters

- `num_tasks`: Number of tasks to generate (default: 1)
- `focus_on_application`: Emphasize practical application (default: True)
- `difficulty_preference`: Task difficulty level
- `resources`: Optional list of resources for context

### ContentGenerationRequest Parameters

Combines all parameters from both resource and task generation, plus:
- `use_obsidian_links`: Format links for Obsidian (default: True)

## Task Types

The Engage Task Generator creates five types of tasks:

- **reflection**: Deep thinking, analysis, self-assessment
- **practice**: Hands-on exercises, skill application
- **project**: Creative application, building something
- **quiz**: Self-testing, knowledge verification
- **experiment**: Try new approaches, test hypotheses

## Best Practices

1. **API Key Management**: Store API keys in environment variables
2. **Batch Processing**: Use batch functions for multiple units
3. **Error Handling**: Always check `generation_success` in results
4. **Resource Context**: Include resources in task generation for better alignment
5. **Fallback Planning**: Agents work without internet; test fallback scenarios

## Examples Repository

See the `examples/` directory for complete working examples:

- `basic_content_generation.py`: Simple single-unit generation
- `batch_project_enhancement.py`: Enhancing multiple units
- `custom_requirements.py`: Using specific resource/task requirements
- `obsidian_integration.py`: Optimizing for Obsidian workflows

## Troubleshooting

### Common Issues

**"No API key found"**
- Set `OPENAI_API_KEY` environment variable
- Or pass `api_key` parameter to creation functions

**"Generation failed"**
- Check internet connection
- Verify API key is valid and has credits
- Agents will use fallback content if AI fails

**"Empty resources/tasks"**
- Check minimum requirements in request
- Fallback systems ensure minimum content is always generated

**"Invalid URLs"**
- AI-generated URLs are examples; real implementation would validate
- Fallback URLs are search-based for maximum compatibility 