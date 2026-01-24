"""
Base Handler Classes

Provides abstract base classes for all handler types:
- BaseHandler: Generic handler
- InputHandler: Data input handlers
- ProcessingHandler: Data processing handlers
- OutputHandler: Data output handlers
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class BaseHandler(ABC):
    """
    Abstract base class for all handlers

    All handlers must implement:
    - execute(): Main handler logic

    Optional overrides:
    - validate(): Validate input context
    - get_config_schema(): Return JSON schema for configuration
    """

    def __init__(self):
        self.name = self.__class__.__name__
        self.logger = logging.getLogger(f"handlers.{self.name}")

    @abstractmethod
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the handler logic

        Args:
            context: Dictionary with input data and configuration

        Returns:
            Dictionary with execution results

        Example:
            context = {'user_id': 123, 'data': {...}}
            result = handler.execute(context)
            # result = {'status': 'success', 'data': {...}}
        """
        pass

    def validate(self, context: Dict[str, Any]) -> bool:
        """
        Validate context before execution

        Args:
            context: Input context to validate

        Returns:
            True if valid, raises exception otherwise
        """
        return True

    def get_config_schema(self) -> Optional[Dict[str, Any]]:
        """
        Return JSON schema for handler configuration

        Returns:
            JSON schema dict or None
        """
        return None

    def log_info(self, message: str):
        """Log info message"""
        self.logger.info(f"[{self.name}] {message}")

    def log_error(self, message: str):
        """Log error message"""
        self.logger.error(f"[{self.name}] {message}")

    def log_debug(self, message: str):
        """Log debug message"""
        self.logger.debug(f"[{self.name}] {message}")


class InputHandler(BaseHandler):
    """
    Base class for input handlers

    Input handlers are responsible for:
    - Reading data from external sources
    - Validating input data
    - Transforming data into standardized format

    Example:
        - FileUploadHandler
        - APIInputHandler
        - DatabaseInputHandler
    """

    @abstractmethod
    def read(self, source: Any) -> Dict[str, Any]:
        """
        Read data from source

        Args:
            source: Input source (file, API endpoint, etc.)

        Returns:
            Standardized data dict
        """
        pass

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute input handler

        Default implementation calls read() with context['source']
        """
        source = context.get("source")
        data = self.read(source)
        return {"status": "success", "data": data}


class ProcessingHandler(BaseHandler):
    """
    Base class for processing handlers

    Processing handlers are responsible for:
    - Transforming data
    - Applying business logic
    - Calling external services (LLMs, APIs)

    Example:
        - LLMProcessingHandler
        - DataValidationHandler
        - EnrichmentHandler
    """

    @abstractmethod
    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process input data

        Args:
            data: Input data to process

        Returns:
            Processed data
        """
        pass

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute processing handler

        Default implementation calls process() with context['data']
        """
        data = context.get("data", {})
        processed_data = self.process(data)
        return {"status": "success", "data": processed_data}


class OutputHandler(BaseHandler):
    """
    Base class for output handlers

    Output handlers are responsible for:
    - Writing data to destinations
    - Formatting output
    - Persisting results

    Example:
        - DatabaseOutputHandler
        - FileOutputHandler
        - EmailOutputHandler
    """

    @abstractmethod
    def write(self, data: Dict[str, Any], destination: Any) -> bool:
        """
        Write data to destination

        Args:
            data: Data to write
            destination: Output destination

        Returns:
            True if successful
        """
        pass

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute output handler

        Default implementation calls write() with context['data'] and context['destination']
        """
        data = context.get("data", {})
        destination = context.get("destination")
        success = self.write(data, destination)
        return {"status": "success" if success else "failed", "written": success}
