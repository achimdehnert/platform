"""
Core Handler Exceptions
=======================

Centralized exception hierarchy for all handler operations.
Migrated from apps/bfagent/services/handlers/exceptions.py

All domain-specific handlers should use these exceptions for consistent
error handling across the system.

Usage:
    from apps.core.handlers.exceptions import (
        HandlerException,
        ValidationError,
        ProcessingError,
        ConfigurationException
    )
"""

from typing import Any, Dict, Optional


class HandlerException(Exception):
    """
    Base exception for all handler errors.

    All handler-related exceptions should inherit from this class
    to enable consistent error handling.

    Attributes:
        message: Human-readable error message
        handler_name: Name of the handler that raised the exception
        context: Additional context data for debugging
        original_error: The original exception if this wraps another error
    """

    def __init__(
        self,
        message: str,
        handler_name: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        self.message = message
        self.handler_name = handler_name
        self.context = context or {}
        self.original_error = original_error

        # Build full message
        full_message = message
        if handler_name:
            full_message = f"[{handler_name}] {message}"

        super().__init__(full_message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for JSON responses."""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "handler_name": self.handler_name,
            "context": self.context,
            "original_error": str(self.original_error) if self.original_error else None,
        }


class ValidationError(HandlerException):
    """
    Raised when input validation fails.

    Use this for:
    - Missing required fields
    - Invalid data types
    - Data format errors
    - Schema validation failures

    Example:
        if 'project_id' not in context:
            raise ValidationError(
                "Missing required field: project_id",
                handler_name="BookCreateHandler",
                context={'received_keys': list(context.keys())}
            )
    """

    pass


class ConfigurationException(HandlerException):
    """
    Raised when handler configuration is invalid.

    Use this for:
    - Missing configuration keys
    - Invalid configuration values
    - Configuration schema violations

    Example:
        if not self.config.get('api_key'):
            raise ConfigurationException(
                "Missing required configuration: api_key",
                handler_name=self.handler_name
            )
    """

    pass


class ProcessingError(HandlerException):
    """
    Raised when handler processing fails.

    Use this for:
    - Business logic failures
    - External service errors (API calls, LLM)
    - Data transformation errors

    Example:
        try:
            result = llm_client.generate(prompt)
        except Exception as e:
            raise ProcessingError(
                "LLM generation failed",
                handler_name=self.handler_name,
                original_error=e
            )
    """

    pass


class InputHandlerException(HandlerException):
    """
    Raised when input collection fails.

    Use this for:
    - File read errors
    - Database query failures
    - External data source errors
    """

    pass


class OutputHandlerException(HandlerException):
    """
    Raised when output/persistence fails.

    Use this for:
    - Database write errors
    - File system errors
    - External service write failures
    """

    pass


class RegistryError(HandlerException):
    """
    Raised when handler registry operations fail.

    Use this for:
    - Handler not found
    - Duplicate handler registration
    - Invalid handler class
    """

    pass


class TimeoutError(HandlerException):
    """
    Raised when handler execution times out.

    Use this for:
    - Long-running operations
    - External service timeouts
    """

    pass


class RetryableError(HandlerException):
    """
    Raised for errors that can be retried.

    Use this for:
    - Temporary network failures
    - Rate limiting
    - Resource temporarily unavailable

    Attributes:
        retry_after: Suggested wait time before retry (seconds)
        max_retries: Maximum number of retries allowed
    """

    def __init__(
        self,
        message: str,
        handler_name: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
        retry_after: int = 5,
        max_retries: int = 3,
    ):
        super().__init__(message, handler_name, context, original_error)
        self.retry_after = retry_after
        self.max_retries = max_retries

    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result["retry_after"] = self.retry_after
        result["max_retries"] = self.max_retries
        return result
