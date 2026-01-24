"""
Core Base Handler Classes
=========================

Consolidated handler base classes combining best features from:
- apps/core/handlers/base.py (original simple version)
- apps/bfagent/handlers/base.py (similar simple version)
- apps/bfagent/services/handlers/base/ (enhanced version with structlog)
- apps/bfagent/handlers/base_handler_v2.py (Pydantic integration)
- apps/genagent/handlers/__init__.py (GenAgent version)

This module provides the single source of truth for all handler base classes.

Usage:
    from apps.core.handlers import (
        BaseHandler,
        InputHandler,
        ProcessingHandler,
        OutputHandler
    )

    class MyHandler(ProcessingHandler):
        handler_name = "my_processing_handler"
        handler_version = "1.0.0"

        def process(self, data, context):
            return {'processed': True}

Architecture:
    BaseHandler (ABC)
    ├── InputHandler     - Data collection from sources
    ├── ProcessingHandler - Business logic & transformations
    └── OutputHandler    - Persistence & output formatting
"""

import logging
from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Type

from .exceptions import (
    ConfigurationException,
    HandlerException,
    InputHandlerException,
    OutputHandlerException,
    ProcessingError,
    ValidationError,
)

# Try to import structlog, fall back to standard logging
try:
    import structlog

    _logger = structlog.get_logger()
    USE_STRUCTLOG = True
except ImportError:
    _logger = logging.getLogger(__name__)
    USE_STRUCTLOG = False

# Try to import Pydantic for schema validation
try:
    from pydantic import BaseModel
    from pydantic import ValidationError as PydanticValidationError

    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    BaseModel = None
    PydanticValidationError = None

# Try to import Django for database transactions
try:
    from django.db import transaction

    DJANGO_AVAILABLE = True
except ImportError:
    DJANGO_AVAILABLE = False
    transaction = None


class BaseHandler(ABC):
    """
    Abstract base class for all handlers.

    This is the foundation class that all handlers inherit from.
    It provides common functionality for logging, configuration,
    and execution lifecycle.

    Class Attributes:
        handler_name: Unique identifier for the handler (REQUIRED)
        handler_version: Semantic version string (default: "1.0.0")
        handler_type: Type classification (input/processing/output)
        description: Human-readable description
        domain: Domain this handler belongs to (for registry)

    Instance Attributes:
        config: Handler configuration dictionary
        logger: Bound logger instance

    Example:
        class BookCreateHandler(BaseHandler):
            handler_name = "book.create"
            handler_version = "2.0.0"
            handler_type = "processing"
            description = "Creates a new book project"
            domain = "writing"

            def execute(self, context):
                # Implementation
                return {'success': True, 'book_id': 123}
    """

    # Class attributes - override in subclasses
    handler_name: str = None
    handler_version: str = "1.0.0"
    handler_type: str = "base"
    description: str = ""
    domain: str = "core"

    # Feature flags
    supports_test_mode: bool = True
    supports_dry_run: bool = False
    requires_authentication: bool = True

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize handler with configuration.

        Args:
            config: Handler-specific configuration dictionary

        Raises:
            ConfigurationException: If handler_name is not defined
        """
        # Validate handler_name is set
        if self.handler_name is None:
            self.handler_name = self.__class__.__name__

        self.config = config or {}

        # Initialize logger
        if USE_STRUCTLOG:
            self.logger = _logger.bind(
                handler=self.handler_name, version=self.handler_version, domain=self.domain
            )
        else:
            self.logger = logging.getLogger(f"handlers.{self.handler_name}")

        # Validate configuration
        try:
            self.validate_config()
        except Exception as e:
            raise ConfigurationException(
                f"Configuration validation failed: {e}",
                handler_name=self.handler_name,
                context={"config": self.config},
                original_error=e,
            )

    def validate_config(self) -> None:
        """
        Validate handler configuration.

        Override in subclasses to add custom validation.

        Raises:
            ValueError: If configuration is invalid
        """
        pass

    @abstractmethod
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the handler logic.

        This is the main entry point for handler execution.
        All handlers must implement this method.

        Args:
            context: Execution context containing:
                - Input data
                - Configuration overrides
                - User/session information
                - Other handler-specific data

        Returns:
            Dictionary with execution results, should include:
                - success: bool
                - Any handler-specific output data

        Raises:
            HandlerException: For handler-specific errors
            ValidationError: For input validation failures
            ProcessingError: For processing failures
        """
        pass

    def validate(self, context: Dict[str, Any]) -> bool:
        """
        Validate context before execution.

        Override in subclasses for custom validation.

        Args:
            context: Input context to validate

        Returns:
            True if valid

        Raises:
            ValidationError: If validation fails
        """
        return True

    def get_config_schema(self) -> Optional[Dict[str, Any]]:
        """
        Return JSON schema for handler configuration.

        Override to provide configuration documentation.

        Returns:
            JSON schema dict or None
        """
        return None

    def get_context_schema(self) -> Optional[Dict[str, Any]]:
        """
        Return JSON schema for execution context.

        Override to provide context documentation.

        Returns:
            JSON schema dict or None
        """
        return None

    # ==================== Logging Helpers ====================

    def log_info(self, message: str, **kwargs):
        """Log info message with context."""
        if USE_STRUCTLOG:
            self.logger.info(message, **kwargs)
        else:
            self.logger.info(f"[{self.handler_name}] {message}")

    def log_error(self, message: str, **kwargs):
        """Log error message with context."""
        if USE_STRUCTLOG:
            self.logger.error(message, **kwargs)
        else:
            self.logger.error(f"[{self.handler_name}] {message}")

    def log_warning(self, message: str, **kwargs):
        """Log warning message with context."""
        if USE_STRUCTLOG:
            self.logger.warning(message, **kwargs)
        else:
            self.logger.warning(f"[{self.handler_name}] {message}")

    def log_debug(self, message: str, **kwargs):
        """Log debug message with context."""
        if USE_STRUCTLOG:
            self.logger.debug(message, **kwargs)
        else:
            self.logger.debug(f"[{self.handler_name}] {message}")

    # ==================== Utility Methods ====================

    def _validate_required_keys(
        self, data: Dict[str, Any], required_keys: List[str], data_name: str = "context"
    ) -> None:
        """
        Validate that required keys are present in a dictionary.

        Args:
            data: Dictionary to validate
            required_keys: List of required key names
            data_name: Name of data for error messages

        Raises:
            ValidationError: If any required key is missing
        """
        missing = [key for key in required_keys if key not in data]
        if missing:
            raise ValidationError(
                f"Missing required keys in {data_name}: {', '.join(missing)}",
                handler_name=self.handler_name,
                context={
                    "required_keys": required_keys,
                    "missing_keys": missing,
                    "received_keys": list(data.keys()),
                },
            )

    def get_info(self) -> Dict[str, Any]:
        """
        Get handler information.

        Returns:
            Dictionary with handler metadata
        """
        return {
            "name": self.handler_name,
            "version": self.handler_version,
            "type": self.handler_type,
            "description": self.description,
            "domain": self.domain,
            "class": self.__class__.__name__,
            "module": self.__class__.__module__,
        }

    @classmethod
    def get_description(cls) -> str:
        """Get handler description."""
        return cls.description or cls.__doc__ or cls.__name__


class InputHandler(BaseHandler):
    """
    Base class for input handlers.

    Input handlers are responsible for:
    - Collecting data from external sources
    - Validating input data
    - Transforming data into standardized format

    Class Attributes (additional to BaseHandler):
        cache_enabled: Whether to cache collected data
        cache_ttl: Cache time-to-live in seconds

    Example:
        class FileInputHandler(InputHandler):
            handler_name = "file.input"

            def collect(self, context):
                file_path = context['file_path']
                return {'content': read_file(file_path)}
    """

    handler_type: str = "input"

    # Caching options
    cache_enabled: bool = False
    cache_ttl: int = 300

    @abstractmethod
    def collect(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Collect data from source.

        Args:
            context: Runtime context containing source information

        Returns:
            Dictionary of collected data

        Raises:
            InputHandlerException: If collection fails
        """
        pass

    def read(self, source: Any) -> Dict[str, Any]:
        """
        Read data from a specific source.

        Override for custom read logic.

        Args:
            source: Input source (file, API, etc.)

        Returns:
            Standardized data dictionary
        """
        raise NotImplementedError("Subclass must implement read()")

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute input handler.

        Default implementation calls collect() with context.
        """
        self.validate(context)

        try:
            data = self.collect(context)
            return {"success": True, "data": data}
        except Exception as e:
            self.log_error(f"Collection failed: {e}")
            raise InputHandlerException(
                f"Failed to collect data: {e}", handler_name=self.handler_name, original_error=e
            )


class ProcessingHandler(BaseHandler):
    """
    Base class for processing handlers.

    Processing handlers are responsible for:
    - Transforming data
    - Applying business logic
    - Calling external services (LLMs, APIs)
    - Data enrichment and validation

    Class Attributes (additional to BaseHandler):
        supports_streaming: Whether handler supports streaming output
        supports_async: Whether handler supports async execution
        use_transaction: Whether to wrap execution in DB transaction

    Example:
        class EnrichmentHandler(ProcessingHandler):
            handler_name = "content.enrich"
            supports_streaming = True

            def process(self, data, context):
                enriched = llm.enrich(data)
                return enriched
    """

    handler_type: str = "processing"

    # Processing options
    supports_streaming: bool = False
    supports_async: bool = False
    use_transaction: bool = True

    # Optional Pydantic schemas (if available)
    InputSchema: Optional[Type] = None  # Pydantic model for input validation
    OutputSchema: Optional[Type] = None  # Pydantic model for output validation

    @abstractmethod
    def process(self, data: Any, context: Dict[str, Any]) -> Any:
        """
        Process input data.

        Args:
            data: Input data to process
            context: Runtime context

        Returns:
            Processed data

        Raises:
            ProcessingError: If processing fails
        """
        pass

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute processing handler.

        Handles:
        - Input validation (with Pydantic if available)
        - Transaction management (if Django available)
        - Output validation (with Pydantic if available)
        """
        self.validate(context)

        # Extract data from context
        data = context.get("data", context)

        # Validate input with Pydantic if schema defined
        if self.InputSchema and PYDANTIC_AVAILABLE:
            try:
                validated_input = self.InputSchema(**data) if isinstance(data, dict) else data
                data = (
                    validated_input.model_dump()
                    if hasattr(validated_input, "model_dump")
                    else dict(validated_input)
                )
            except PydanticValidationError as e:
                raise ValidationError(
                    f"Input validation failed: {e}",
                    handler_name=self.handler_name,
                    context={"errors": e.errors() if hasattr(e, "errors") else str(e)},
                )

        try:
            # Execute with or without transaction
            if self.use_transaction and DJANGO_AVAILABLE:
                with transaction.atomic():
                    result = self.process(data, context)
            else:
                result = self.process(data, context)

            # Validate output with Pydantic if schema defined
            if self.OutputSchema and PYDANTIC_AVAILABLE:
                try:
                    if isinstance(result, dict):
                        validated_output = self.OutputSchema(**result)
                        result = (
                            validated_output.model_dump()
                            if hasattr(validated_output, "model_dump")
                            else dict(validated_output)
                        )
                except PydanticValidationError as e:
                    self.log_warning(f"Output validation failed: {e}")

            # Ensure result is a dict with success flag
            if isinstance(result, dict):
                result.setdefault("success", True)
                return result
            else:
                return {"success": True, "data": result}

        except HandlerException:
            raise
        except Exception as e:
            self.log_error(f"Processing failed: {e}")
            raise ProcessingError(
                f"Processing failed: {e}", handler_name=self.handler_name, original_error=e
            )


class OutputHandler(BaseHandler):
    """
    Base class for output handlers.

    Output handlers are responsible for:
    - Parsing processed data into structured format
    - Validating data before persistence
    - Creating approval workflows (EnrichmentResponse)
    - Persisting data to database/filesystem

    Class Attributes (additional to BaseHandler):
        supports_multiple_objects: Can create multiple objects
        supports_rollback: Can rollback applied changes
        supports_preview: Can preview changes before apply

    Workflow:
        1. parse() - Convert processed data to list of dicts
        2. validate() - Validate parsed data
        3. create_responses() - Create approval objects (optional)
        4. apply() - Persist data

    Example:
        class CharacterOutputHandler(OutputHandler):
            handler_name = "character.output"
            supports_multiple_objects = True

            def parse(self, processed_data):
                return [{'name': c['name']} for c in processed_data]

            def apply(self, data):
                return Character.objects.create(**data)
    """

    handler_type: str = "output"

    # Output options
    supports_multiple_objects: bool = False
    supports_rollback: bool = False
    supports_preview: bool = True
    supports_validation: bool = True

    @abstractmethod
    def parse(self, processed_data: Any) -> List[Dict[str, Any]]:
        """
        Parse processed data into structured format.

        Args:
            processed_data: Output from processing stage

        Returns:
            List of dictionaries to be created/updated

        Raises:
            OutputHandlerException: If parsing fails
        """
        pass

    def validate_output(self, parsed_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate parsed data before persistence.

        Args:
            parsed_data: Data from parse()

        Returns:
            Validation result dict with 'valid', 'errors', 'warnings'
        """
        return {"valid": True, "errors": [], "warnings": []}

    @abstractmethod
    def apply(self, data: Dict[str, Any]) -> Any:
        """
        Apply/persist a single data item.

        Args:
            data: Single item from parsed data

        Returns:
            Created/updated object

        Raises:
            OutputHandlerException: If persistence fails
        """
        pass

    def write(self, data: Dict[str, Any], destination: Any = None) -> bool:
        """
        Write data to destination (legacy interface).

        Args:
            data: Data to write
            destination: Output destination

        Returns:
            True if successful
        """
        try:
            self.apply(data)
            return True
        except Exception:
            return False

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute output handler.

        Full workflow: parse → validate → apply
        """
        self.validate(context)
        processed_data = context.get("data", context)

        try:
            # Parse
            parsed_items = self.parse(processed_data)

            # Validate
            if self.supports_validation:
                validation_result = self.validate_output(parsed_items)
                if not validation_result.get("valid", True):
                    return {
                        "success": False,
                        "validation_errors": validation_result.get("errors", []),
                        "validation_warnings": validation_result.get("warnings", []),
                    }

            # Apply each item
            results = []
            errors = []

            for item in parsed_items:
                try:
                    result = self.apply(item)
                    results.append(result)
                except Exception as e:
                    errors.append({"item": item, "error": str(e)})

            return {
                "success": len(errors) == 0,
                "created_count": len(results),
                "error_count": len(errors),
                "results": results,
                "errors": errors,
            }

        except Exception as e:
            self.log_error(f"Output failed: {e}")
            raise OutputHandlerException(
                f"Output failed: {e}", handler_name=self.handler_name, original_error=e
            )


# ==================== Aliases for Backward Compatibility ====================

# GenAgent compatibility
GenAgentBaseHandler = BaseHandler

# BFAgent compatibility
BaseInputHandler = InputHandler
BaseProcessingHandler = ProcessingHandler
BaseOutputHandler = OutputHandler
