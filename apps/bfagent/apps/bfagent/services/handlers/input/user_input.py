"""
User Input Handler

Collects user-provided context and requirements.
"""

from typing import Any, Dict
import structlog

from ..base.input import BaseInputHandler
from ..exceptions import InputHandlerException
from ..decorators import with_logging, with_performance_monitoring
from ..schemas import UserInputConfig

logger = structlog.get_logger()


class UserInputHandler(BaseInputHandler):
    """
    Collects user-provided input from context.
    
    This handler extracts user_context and user_requirements
    from the runtime context.
    
    Configuration:
        {} (No configuration needed)
    
    Example:
        >>> handler = UserInputHandler({})
        >>> context = {
        ...     "user_context": "Focus on diverse characters",
        ...     "user_requirements": "At least 6 characters"
        ... }
        >>> data = handler.collect(context)
        >>> # Returns: {"user_context": "...", "user_requirements": "..."}
    """
    
    handler_name = "user_input"
    handler_version = "1.0.0"
    description = "Collects user-provided context and requirements"
    
    def validate_config(self) -> None:
        """Validate configuration using Pydantic."""
        try:
            UserInputConfig(**self.config)
        except Exception as e:
            raise InputHandlerException(
                message="Invalid configuration for UserInputHandler",
                handler_name=self.handler_name,
                context={"config": self.config, "error": str(e)}
            )
    
    @with_logging
    @with_performance_monitoring
    def collect(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Collect user input from context.
        
        Args:
            context: May contain 'user_context' and 'user_requirements'
            
        Returns:
            Dictionary with user-provided data
        """
        collected_data = {}
        
        # Collect user context
        user_context = context.get("user_context", "")
        if user_context:
            collected_data["user_context"] = user_context
        
        # Collect user requirements
        user_requirements = context.get("user_requirements", "")
        if user_requirements:
            collected_data["user_requirements"] = user_requirements
        
        return collected_data
    
    def get_schema(self) -> Dict[str, Any]:
        """Return schema of provided data."""
        return {
            "type": "object",
            "source": "user_input",
            "fields": {
                "user_context": {
                    "type": "string",
                    "source": "context.user_context",
                    "required": False,
                    "description": "User-provided context for the action"
                },
                "user_requirements": {
                    "type": "string",
                    "source": "context.user_requirements",
                    "required": False,
                    "description": "User-provided requirements"
                }
            }
        }
