"""
FlowGenius AI Agents

This package contains AI agents responsible for different aspects of learning
project generation, including scaffolding, resource curation, and task generation.
"""

from .topic_scaffolder import TopicScaffolderAgent, ScaffoldingRequest
from .resource_curator import ResourceCuratorAgent, ResourceRequest, format_resources_for_obsidian
from .engage_task_generator import (
    EngageTaskGeneratorAgent, 
    TaskGenerationRequest, 
    format_tasks_for_markdown,
    suggest_task_for_objectives
)
from .content_generator import (
    ContentGeneratorAgent,
    ContentGenerationRequest,
    GeneratedContent,
    create_content_generator,
    generate_unit_content_simple
)

__all__ = [
    "TopicScaffolderAgent",
    "ScaffoldingRequest",
    "ResourceCuratorAgent",
    "ResourceRequest",
    "format_resources_for_obsidian",
    "EngageTaskGeneratorAgent",
    "TaskGenerationRequest",
    "format_tasks_for_markdown",
    "suggest_task_for_objectives",
    "ContentGeneratorAgent",
    "ContentGenerationRequest",
    "GeneratedContent",
    "create_content_generator",
    "generate_unit_content_simple"
] 