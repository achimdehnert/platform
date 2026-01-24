"""
Template Renderer Handler

Renders mustache-style templates with collected input data.
"""

from typing import Any, Dict
import structlog

from ..base.processing import BaseProcessingHandler
from ..exceptions import ProcessingHandlerException
from ..decorators import with_logging, with_performance_monitoring
from ..schemas import TemplateRendererConfig

logger = structlog.get_logger()


class TemplateRendererHandler(BaseProcessingHandler):
    """
    Renders templates with mustache-style variable substitution.
    
    Replaces {{ variable_name }} with values from input_data.
    
    Configuration:
        {
            "template": "Title: {{ title }}\nGenre: {{ genre }}"
        }
    
    Example:
        >>> handler = TemplateRendererHandler({
        ...     "template": "Title: {{ title }}\nGenre: {{ genre }}"
        ... })
        >>> input_data = {"title": "My Novel", "genre": "Fantasy"}
        >>> result = handler.process(input_data, context)
        >>> # Returns: "Title: My Novel\nGenre: Fantasy"
    """
    
    handler_name = "template_renderer"
    handler_version = "1.0.0"
    description = "Renders mustache-style templates with input data"
    
    def validate_config(self) -> None:
        """Validate configuration using Pydantic."""
        try:
            TemplateRendererConfig(**self.config)
        except Exception as e:
            raise ProcessingHandlerException(
                message="Invalid configuration for TemplateRendererHandler",
                handler_name=self.handler_name,
                context={"config": self.config, "error": str(e)}
            )
    
    @with_logging
    @with_performance_monitoring
    def process(
        self,
        input_data: Any,
        context: Dict[str, Any]
    ) -> str:
        """
        Render template with input data.
        
        Args:
            input_data: Dictionary with variables for substitution
            context: Runtime context (not used)
            
        Returns:
            Rendered template string
        """
        template = self.config["template"]
        
        if not isinstance(input_data, dict):
            raise ValueError("input_data must be a dictionary")
        
        # Perform mustache-style substitution
        rendered = template
        
        for key, value in input_data.items():
            # Handle {{ variable }} pattern (with spaces)
            placeholder = "{{ " + str(key) + " }}"
            rendered = rendered.replace(placeholder, str(value))
            
            # Also handle {{variable}} pattern (without spaces)
            placeholder_no_space = "{{" + str(key) + "}}"
            rendered = rendered.replace(placeholder_no_space, str(value))
        
        return rendered
