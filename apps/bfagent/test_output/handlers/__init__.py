"""
Modern Handler Framework v2.0

Production-ready handler pipeline system with:
- Type-safe configuration (Pydantic)
- Structured logging (structlog)
- Custom exception hierarchy
- Transaction safety
- Performance monitoring
"""

__version__ = "2.0.0"
__author__ = "BF Agent Team"

from .exceptions import (
    HandlerException,
    InputHandlerException,
    ProcessingHandlerException,
    OutputHandlerException,
    ValidationException,
    ConfigurationException,
    HandlerNotFoundException,
    LLMException,
)

__all__ = [
    "HandlerException",
    "InputHandlerException",
    "ProcessingHandlerException",
    "OutputHandlerException",
    "ValidationException",
    "ConfigurationException",
    "HandlerNotFoundException",
    "LLMException",
]
