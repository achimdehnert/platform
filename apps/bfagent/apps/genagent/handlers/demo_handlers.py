"""
GenAgent Demo Handlers
Example handlers to demonstrate the system
"""

from . import register_handler, BaseHandler
from typing import Dict, Any


@register_handler
class WelcomeHandler(BaseHandler):
    """Simple welcome handler for demonstration"""
    
    def execute(self, context: Dict[str, Any], test_mode: bool = False) -> Dict[str, Any]:
        """Generate a welcome message"""
        name = context.get('name', 'World')
        message = self.config.get('message', 'Hello')
        
        result = f"{message}, {name}!"
        
        return {
            'success': True,
            'output': result,
            'test_mode': test_mode,
            'context_received': list(context.keys())
        }
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "default": "Hello",
                    "description": "Greeting message"
                }
            }
        }


@register_handler
class DataValidationHandler(BaseHandler):
    """Validates that required fields exist in context"""
    
    def execute(self, context: Dict[str, Any], test_mode: bool = False) -> Dict[str, Any]:
        """Validate required fields in context"""
        required_fields = self.config.get('required_fields', [])
        
        missing = [f for f in required_fields if f not in context]
        
        if missing:
            return {
                'success': False,
                'error': f"Missing required fields: {', '.join(missing)}",
                'missing_fields': missing
            }
        
        return {
            'success': True,
            'output': f"All {len(required_fields)} required fields present",
            'validated_fields': required_fields
        }
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "required_fields": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": [],
                    "description": "List of required field names"
                }
            },
            "required": ["required_fields"]
        }


@register_handler
class DataTransformHandler(BaseHandler):
    """Transforms data from one format to another"""
    
    def execute(self, context: Dict[str, Any], test_mode: bool = False) -> Dict[str, Any]:
        """Transform data based on configuration"""
        source_field = self.config.get('source_field')
        target_field = self.config.get('target_field')
        transform_type = self.config.get('transform', 'upper')
        
        if not source_field or not target_field:
            return {
                'success': False,
                'error': "source_field and target_field required in config"
            }
        
        source_value = context.get(source_field)
        
        if source_value is None:
            return {
                'success': False,
                'error': f"Source field '{source_field}' not found in context"
            }
        
        # Apply transformation
        if transform_type == 'upper' and isinstance(source_value, str):
            transformed = source_value.upper()
        elif transform_type == 'lower' and isinstance(source_value, str):
            transformed = source_value.lower()
        elif transform_type == 'capitalize' and isinstance(source_value, str):
            transformed = source_value.capitalize()
        elif transform_type == 'length':
            transformed = len(source_value)
        else:
            transformed = source_value
        
        return {
            'success': True,
            'output': transformed,
            'source_field': source_field,
            'target_field': target_field,
            'transform_type': transform_type
        }
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "source_field": {
                    "type": "string",
                    "description": "Field to read from context"
                },
                "target_field": {
                    "type": "string",
                    "description": "Field to write result to"
                },
                "transform": {
                    "type": "string",
                    "enum": ["upper", "lower", "capitalize", "length"],
                    "default": "upper",
                    "description": "Transformation to apply"
                }
            },
            "required": ["source_field", "target_field"]
        }


@register_handler
class LogHandler(BaseHandler):
    """Logs information for debugging"""
    
    def execute(self, context: Dict[str, Any], test_mode: bool = False) -> Dict[str, Any]:
        """Log context information"""
        log_level = self.config.get('level', 'info')
        message_template = self.config.get('message', 'Context: {context}')
        
        # Format message with context
        message = message_template.format(context=context)
        
        # In real implementation, would use logging module
        print(f"[{log_level.upper()}] {message}")
        
        return {
            'success': True,
            'output': f"Logged at level {log_level}",
            'message': message
        }
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "level": {
                    "type": "string",
                    "enum": ["debug", "info", "warning", "error"],
                    "default": "info",
                    "description": "Log level"
                },
                "message": {
                    "type": "string",
                    "default": "Context: {context}",
                    "description": "Message template (can use {context})"
                }
            }
        }
