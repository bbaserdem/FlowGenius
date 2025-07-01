"""
FlowGenius AI Agents

This package contains AI agents responsible for different aspects of learning
project generation, including scaffolding, resource curation, and task generation.
"""

from .topic_scaffolder import TopicScaffolderAgent, ScaffoldingRequest

__all__ = [
    "TopicScaffolderAgent",
    "ScaffoldingRequest"
] 