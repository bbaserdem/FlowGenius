"""
Shared utilities for FlowGenius AI agents.

This module provides common functionality used across multiple agents,
including prompt building, JSON parsing, and response validation.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Type, TypeVar
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)


def parse_json_response(content: str, expected_keys: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
    """
    Parse and validate JSON response from AI.
    
    Args:
        content: Raw JSON string to parse
        expected_keys: Optional list of keys that must be present
        
    Returns:
        Parsed dictionary or None if parsing fails
    """
    try:
        # Try to parse JSON
        data = json.loads(content)
        
        # Validate expected keys if provided
        if expected_keys:
            for key in expected_keys:
                if key not in data:
                    logger.warning(f"Missing expected key '{key}' in JSON response")
                    return None
                    
        return data
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON: {e}")
        # Try to extract JSON from markdown code blocks
        if "```json" in content:
            try:
                json_start = content.find("```json") + 7
                json_end = content.find("```", json_start)
                json_str = content[json_start:json_end].strip()
                return json.loads(json_str)
            except (json.JSONDecodeError, ValueError):
                pass
        return None


def validate_with_pydantic(data: Dict[str, Any], model_class: Type[T]) -> Optional[T]:
    """
    Validate dictionary data with a Pydantic model.
    
    Args:
        data: Dictionary to validate
        model_class: Pydantic model class to use for validation
        
    Returns:
        Validated model instance or None if validation fails
    """
    try:
        return model_class(**data)
    except ValidationError as e:
        logger.error(f"Pydantic validation failed: {e}")
        return None


def build_ai_prompt(base_prompt: str, context: Dict[str, Any], 
                   include_json_format: bool = True) -> str:
    """
    Build a structured prompt for AI generation.
    
    Args:
        base_prompt: Base prompt template
        context: Dictionary of context values to include
        include_json_format: Whether to include JSON format reminder
        
    Returns:
        Complete prompt string
    """
    prompt_parts = [base_prompt]
    
    # Add context sections
    for key, value in context.items():
        if value is not None:
            # Convert key from snake_case to Title Case
            title = key.replace("_", " ").title()
            prompt_parts.append(f"\n{title}: {value}")
    
    # Add JSON format reminder if needed
    if include_json_format:
        prompt_parts.append("\n\nReturn your response as valid JSON.")
        
    return "\n".join(prompt_parts)


def extract_list_from_response(response: Dict[str, Any], 
                              list_key: str,
                              item_model: Type[T]) -> List[T]:
    """
    Extract and validate a list of items from AI response.
    
    Args:
        response: AI response dictionary
        list_key: Key containing the list in response
        item_model: Pydantic model for list items
        
    Returns:
        List of validated model instances
    """
    items = []
    
    raw_items = response.get(list_key, [])
    if not isinstance(raw_items, list):
        logger.warning(f"Expected list for key '{list_key}', got {type(raw_items)}")
        return items
        
    for item_data in raw_items:
        validated_item = validate_with_pydantic(item_data, item_model)
        if validated_item:
            items.append(validated_item)
        else:
            logger.warning(f"Skipping invalid {item_model.__name__} item")
            
    return items


def create_system_prompt(role: str, expertise: List[str], 
                        additional_instructions: Optional[str] = None) -> str:
    """
    Create a consistent system prompt for AI agents.
    
    Args:
        role: Primary role description
        expertise: List of expertise areas
        additional_instructions: Optional additional instructions
        
    Returns:
        Complete system prompt
    """
    prompt = f"You are {role}"
    
    if expertise:
        expertise_str = ", ".join(expertise)
        prompt += f" with expertise in {expertise_str}"
        
    prompt += "."
    
    if additional_instructions:
        prompt += f" {additional_instructions}"
        
    return prompt 