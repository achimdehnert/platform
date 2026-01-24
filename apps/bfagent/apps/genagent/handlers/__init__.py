"""
GenAgent Handler Registry
Central registry for all GenAgent handlers
"""

from typing import Dict, Any, Type
from abc import ABC, abstractmethod


# Handler Registry - stores all registered handlers
HANDLER_REGISTRY: Dict[str, Type['BaseHandler']] = {}


def register_handler(cls):
    """
    Decorator to register handlers in the global registry
    
    Usage:
        @register_handler
        class MyHandler(BaseHandler):
            ...
    """
    path = f"{cls.__module__}.{cls.__name__}"
    HANDLER_REGISTRY[path] = cls
    return cls


def get_handler(handler_path: str) -> Type['BaseHandler']:
    """Get handler class by path"""
    return HANDLER_REGISTRY.get(handler_path)


def list_handlers() -> Dict[str, Type['BaseHandler']]:
    """Get all registered handlers"""
    return HANDLER_REGISTRY.copy()


class BaseHandler(ABC):
    """
    Base Handler Class for GenAgent
    
    All handlers must inherit from this class and implement execute()
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize handler with configuration
        
        Args:
            config: JSON configuration from Action.config field
        """
        self.config = config or {}
    
    @abstractmethod
    def execute(self, context: Dict[str, Any], test_mode: bool = False) -> Dict[str, Any]:
        """
        Execute handler logic
        
        Args:
            context: Execution context with input data
            test_mode: If True, handler should run in test/dry-run mode
            
        Returns:
            Dict with result data, must include:
                - success: bool
                - output: Any (result data)
                - error: str (if success=False)
        """
        pass
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """
        Return JSON schema for handler configuration
        
        Used for UI validation and documentation
        """
        return {
            "type": "object",
            "properties": {},
            "required": []
        }
    
    @classmethod
    def get_description(cls) -> str:
        """Return handler description"""
        return cls.__doc__ or cls.__name__
