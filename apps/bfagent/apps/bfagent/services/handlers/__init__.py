"""
Pipeline Handler System for BF Agent - Modern Handler Framework v2.0

This package provides a complete 3-stage pipeline system for processing
AI-assisted enrichment actions:

1. INPUT Stage: Collect data from various sources
2. PROCESSING Stage: Transform/process the data
3. OUTPUT Stage: Store results in database or export

Each stage consists of handlers that can be freely combined and configured.

Features:
- Type-safe configuration with Pydantic
- Structured logging with structlog
- Custom exception hierarchy
- Transaction safety
- Performance monitoring
- Retry logic
"""

from .base.input import BaseInputHandler
from .base.processing import BaseProcessingHandler
from .base.output import BaseOutputHandler

from .registries import (
    InputHandlerRegistry,
    ProcessingHandlerRegistry,
    OutputHandlerRegistry,
)

__all__ = [
    "BaseInputHandler",
    "BaseProcessingHandler",
    "BaseOutputHandler",
    "InputHandlerRegistry",
    "ProcessingHandlerRegistry",
    "OutputHandlerRegistry",
]
