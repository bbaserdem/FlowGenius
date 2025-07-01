# FlowGenius Agents Module

This module contains AI-powered agents for enhanced learning content generation.

## Agents Overview

### 🏗️ TopicScaffolderAgent
**File**: `topic_scaffolder.py`  
**Purpose**: Creates structured learning plans from freeform learning goals and motivations.

**Key Features**:
- Converts topics into logical learning unit progressions
- Uses AI to generate learning objectives and structure
- Includes fallback system for offline operation

### 📚 ResourceCuratorAgent
**File**: `resource_curator.py`  
**Purpose**: Finds and curates learning resources (videos, articles, papers) for learning units.

**Key Features**:
- AI-powered resource discovery and curation
- Ensures minimum video and reading resource requirements
- Obsidian-compatible link formatting
- Intelligent fallback resource generation

### 🎯 EngageTaskGeneratorAgent
**File**: `engage_task_generator.py`  
**Purpose**: Creates engaging, active learning tasks for learning units.

**Key Features**:
- Generates 5 types of tasks: reflection, practice, project, quiz, experiment
- Context-aware task generation using available resources
- Smart task type selection based on learning objectives
- Multiple fallback systems for reliability

### 🔄 ContentGeneratorAgent
**File**: `content_generator.py`  
**Purpose**: Integrated agent that combines resource curation and task generation for complete content generation.

**Key Features**:
- Orchestrates both ResourceCuratorAgent and EngageTaskGeneratorAgent
- Single interface for complete unit population
- Batch processing capabilities
- Factory functions for easy setup

## Quick Usage

```python
# Simple content generation
from flowgenius.agents import generate_unit_content_simple

content = generate_unit_content_simple(unit, use_obsidian_links=True)
```

```python
# Full control integration
from flowgenius.agents import create_content_generator, ContentGenerationRequest

generator = create_content_generator()
request = ContentGenerationRequest(unit=unit, num_engage_tasks=2)
content = generator.generate_complete_content(request)
```

## Module Structure

```
agents/
├── __init__.py                 # Module exports
├── topic_scaffolder.py         # Learning plan structure generation
├── resource_curator.py         # Resource finding and curation  
├── engage_task_generator.py    # Active learning task creation
├── content_generator.py        # Integrated content generation
└── README.md                   # This file
```

## Exported Classes and Functions

### Main Agents
- `TopicScaffolderAgent`
- `ResourceCuratorAgent` 
- `EngageTaskGeneratorAgent`
- `ContentGeneratorAgent`

### Request Models
- `ScaffoldingRequest`
- `ResourceRequest`
- `TaskGenerationRequest` 
- `ContentGenerationRequest`

### Result Models
- `GeneratedContent`

### Utility Functions
- `format_resources_for_obsidian()` - Format resources for Obsidian
- `format_tasks_for_markdown()` - Format tasks for markdown
- `suggest_task_for_objectives()` - Non-AI task suggestion
- `create_content_generator()` - Factory function for ContentGeneratorAgent
- `generate_unit_content_simple()` - Simple one-line content generation

## Dependencies

- **OpenAI**: For AI-powered content generation
- **Pydantic**: For data models and validation
- **Project Models**: From `flowgenius.models.project`

## Documentation

For comprehensive usage examples and API reference, see:
- [Full Usage Guide](../../../docs/agents_usage.md)
- Inline docstrings in each module
- Type hints for all functions and classes

## Error Handling

All agents include robust error handling with multiple fallback levels:
1. AI generation (primary)
2. Template-based fallbacks
3. Basic fallback systems
4. Never fails completely - always produces usable content

## Testing

Each agent is designed to work:
- ✅ With internet and valid API key (full AI capabilities)
- ✅ Without internet (using fallback systems) 
- ✅ With invalid/missing API key (graceful degradation)
- ✅ With partial failures (mixed AI and fallback content) 