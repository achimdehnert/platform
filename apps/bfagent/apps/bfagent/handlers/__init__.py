"""
BF Agent Handler System
Modular, reusable handlers for input, processing, and output
"""

from .base import (
    BaseInputHandler,
    BaseOutputHandler,
    BaseProcessingHandler,
    HandlerException,
    OutputError,
    ProcessingError,
    ValidationError,
)
from .input_handlers import CharacterInputHandler, ProjectInputHandler
from .output_handlers import CharacterOutputHandler, ProjectOutputHandler
from .processing_handlers import EnrichmentHandler
from .registry import HandlerRegistry

__all__ = [
    # Base Classes
    'BaseInputHandler',
    'BaseProcessingHandler',
    'BaseOutputHandler',
    # Exceptions
    'HandlerException',
    'ValidationError',
    'ProcessingError',
    'OutputError',
    # Registry
    'HandlerRegistry',
    # Input Handlers
    'ProjectInputHandler',
    'CharacterInputHandler',
    # Processing Handlers
    'EnrichmentHandler',
    # Output Handlers
    'ProjectOutputHandler',
    'CharacterOutputHandler',
]
