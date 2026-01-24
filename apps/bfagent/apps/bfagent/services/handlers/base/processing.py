"""
Enhanced Base Processing Handler
"""

from abc import ABC, abstractmethod
from typing import Any, Dict
import structlog

from ..exceptions import ProcessingHandlerException, ConfigurationException
from ..decorators import with_logging, with_performance_monitoring

logger = structlog.get_logger()


class BaseProcessingHandler(ABC):
    """
    Base class for all processing handlers.
    
    Processing handlers transform, validate, or enrich data collected
    from input handlers before it reaches the output stage.
    
    Attributes:
        handler_type: Always "processing"
        handler_name: Unique identifier
        handler_version: Version string
        description: Human-readable description
        supports_streaming: Whether handler supports streaming
        supports_async: Whether handler supports async execution
    """
    
    handler_type: str = "processing"
    handler_name: str = None
    handler_version: str = "2.0.0"
    description: str = ""
    
    supports_streaming: bool = False
    supports_async: bool = False
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize handler with configuration.
        
        Args:
            config: Handler-specific configuration
            
        Raises:
            ConfigurationException: If config invalid
        """
        if self.handler_name is None:
            raise ConfigurationException(
                "Handler must define handler_name class attribute",
                handler_name=self.__class__.__name__
            )
        
        self.config = config
        self.logger = logger.bind(
            handler=self.handler_name,
            version=self.handler_version
        )
        
        try:
            self.validate_config()
        except Exception as e:
            raise ConfigurationException(
                f"Configuration validation failed: {e}",
                handler_name=self.handler_name,
                context={"config": config},
                original_error=e
            )
    
    @abstractmethod
    def validate_config(self) -> None:
        """
        Validate handler configuration.
        
        Raises:
            ValueError: If configuration is invalid
        """
        pass
    
    @abstractmethod
    def process(
        self,
        input_data: Any,
        context: Dict[str, Any]
    ) -> Any:
        """
        Process/transform input data.
        
        Args:
            input_data: Data from previous stage
            context: Runtime context
            
        Returns:
            Processed data
            
        Raises:
            ProcessingHandlerException: If processing fails
        """
        pass
    
    def _validate_input_data(self, input_data: Any, expected_type: type) -> None:
        """
        Helper to validate input data type.
        
        Args:
            input_data: The data to validate
            expected_type: Expected type
            
        Raises:
            ProcessingHandlerException: If type doesn't match
        """
        if not isinstance(input_data, expected_type):
            raise ProcessingHandlerException(
                f"Invalid input data type. Expected {expected_type.__name__}, "
                f"got {type(input_data).__name__}",
                handler_name=self.handler_name,
                context={
                    "expected_type": expected_type.__name__,
                    "actual_type": type(input_data).__name__
                }
            )
    
    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} "
            f"name={self.handler_name} "
            f"version={self.handler_version}>"
        )