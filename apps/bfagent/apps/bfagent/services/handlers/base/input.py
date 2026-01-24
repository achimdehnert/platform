"""
Enhanced Base Input Handler
"""

from abc import ABC, abstractmethod
from typing import Any, Dict
import structlog

from ..exceptions import InputHandlerException, ConfigurationException
from ..decorators import with_logging, with_performance_monitoring

logger = structlog.get_logger()


class BaseInputHandler(ABC):
    """
    Base class for all input handlers.
    
    Input handlers collect data from various sources and make it
    available for the processing stage.
    
    Attributes:
        handler_type: Always "input" for input handlers
        handler_name: Unique identifier for this handler
        handler_version: Version string
        description: Human-readable description
        cache_enabled: Whether to cache results
        cache_ttl: Cache time-to-live in seconds
    """
    
    handler_type: str = "input"
    handler_name: str = None
    handler_version: str = "2.0.0"
    description: str = ""
    
    cache_enabled: bool = False
    cache_ttl: int = 300
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize handler with configuration.
        
        Args:
            config: Handler-specific configuration
            
        Raises:
            ConfigurationException: If handler_name not defined or config invalid
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
    def collect(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Collect data from source.
        
        Args:
            context: Runtime context containing:
                - project: BookProjects instance
                - agent: Agents instance
                - user_context: Optional user context
                
        Returns:
            Dictionary of collected data
            
        Raises:
            InputHandlerException: If collection fails
        """
        pass
    
    def _validate_context(self, context: Dict[str, Any], required_keys: list) -> None:
        """
        Helper to validate required context keys.
        
        Args:
            context: The context dictionary
            required_keys: List of required key names
            
        Raises:
            InputHandlerException: If any required key is missing
        """
        missing_keys = [key for key in required_keys if key not in context]
        
        if missing_keys:
            raise InputHandlerException(
                f"Missing required context keys: {', '.join(missing_keys)}",
                handler_name=self.handler_name,
                context={
                    "required": required_keys,
                    "provided": list(context.keys()),
                    "missing": missing_keys
                }
            )
    
    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} "
            f"name={self.handler_name} "
            f"version={self.handler_version}>"
        )