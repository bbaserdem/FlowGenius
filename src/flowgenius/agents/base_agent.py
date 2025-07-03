"""
Base Agent for FlowGenius AI agents.

This module provides a base class with common functionality for all AI agents,
including error handling, fallback mechanisms, and OpenAI client management.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, TypeVar, Generic
from openai import OpenAI
from pydantic import BaseModel

from ..models.settings import DefaultSettings

# Set up module logger
logger = logging.getLogger(__name__)

# Generic type for request models
TRequest = TypeVar('TRequest', bound=BaseModel)
# Generic type for result models  
TResult = TypeVar('TResult')


class BaseAgent(ABC, Generic[TRequest, TResult]):
    """
    Abstract base class for all FlowGenius AI agents.
    
    Provides common functionality including:
    - OpenAI client management
    - Error handling patterns
    - Logging setup
    - Fallback mechanisms
    """
    
    def __init__(self, openai_client: OpenAI, model: str = DefaultSettings.DEFAULT_MODEL) -> None:
        """
        Initialize base agent with OpenAI client.
        
        Args:
            openai_client: Configured OpenAI client
            model: OpenAI model to use for generation
        """
        self.client = openai_client
        self.model = model
        self.logger = logging.getLogger(self.__class__.__name__)
        
    @abstractmethod
    def process_request(self, request: TRequest) -> TResult:
        """
        Process a request and return a result.
        
        This is the main method that subclasses must implement.
        
        Args:
            request: Request object specific to the agent type
            
        Returns:
            Result object specific to the agent type
        """
        pass
    
    def _call_openai_with_retry(
        self, 
        messages: list[Dict[str, str]], 
        temperature: float = 0.7,
        max_tokens: int = 2000,
        response_format: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Call OpenAI API with automatic retry and error handling.
        
        Args:
            messages: List of message dictionaries for chat completion
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            response_format: Optional response format specification
            
        Returns:
            Generated content string or None if failed
        """
        try:
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            if response_format:
                kwargs["response_format"] = response_format
                
            response = self.client.chat.completions.create(**kwargs)
            
            content = response.choices[0].message.content
            if content:
                return content.strip()
            return None
            
        except Exception as e:
            self.logger.error(f"OpenAI API call failed: {e}", exc_info=True)
            return None
    
    def _log_operation_start(self, operation: str, details: Dict[str, Any]) -> None:
        """
        Log the start of an operation with consistent formatting.
        
        Args:
            operation: Name of the operation
            details: Dictionary of relevant details
        """
        details_str = ", ".join(f"{k}={v}" for k, v in details.items())
        self.logger.info(f"{operation} started: {details_str}")
    
    def _log_operation_complete(self, operation: str, success: bool, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Log the completion of an operation with consistent formatting.
        
        Args:
            operation: Name of the operation
            success: Whether operation succeeded
            details: Optional dictionary of additional details
        """
        status = "succeeded" if success else "failed"
        message = f"{operation} {status}"
        
        if details:
            details_str = ", ".join(f"{k}={v}" for k, v in details.items())
            message += f": {details_str}"
            
        if success:
            self.logger.info(message)
        else:
            self.logger.warning(message)
    
    @abstractmethod
    def _create_fallback_result(self, request: TRequest) -> TResult:
        """
        Create a fallback result when AI generation fails.
        
        Subclasses must implement this to provide sensible defaults.
        
        Args:
            request: Original request that failed
            
        Returns:
            Fallback result object
        """
        pass 