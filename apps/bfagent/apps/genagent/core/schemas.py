"""
GenAgent Schemas - Feature 4: Pydantic Schemas

Type-safe schemas for handler input/output validation and documentation.

Author: GenAgent Development Team
Created: 2025-01-19
"""

import logging
from typing import Any, Dict, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator
from pydantic_core import PydanticUndefined


logger = logging.getLogger(__name__)


class BaseHandlerInput(BaseModel):
    """
    Base schema for all handler inputs.
    
    All handlers should accept inputs that extend this base schema.
    """
    
    model_config = ConfigDict(
        extra='allow',  # Allow additional fields
        validate_assignment=True,
        str_strip_whitespace=True
    )
    
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Execution context data"
    )
    
    config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Handler configuration"
    )
    
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional metadata for execution"
    )


class BaseHandlerOutput(BaseModel):
    """
    Base schema for all handler outputs.
    
    All handlers should return outputs that extend this base schema.
    """
    
    model_config = ConfigDict(
        extra='allow',
        validate_assignment=True
    )
    
    success: bool = Field(
        description="Whether handler execution succeeded"
    )
    
    result: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Handler execution result data"
    )
    
    error: Optional[str] = Field(
        default=None,
        description="Error message if execution failed"
    )
    
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional metadata about execution"
    )
    
    @field_validator('error')
    @classmethod
    def error_requires_failed_status(cls, v, info):
        """Validate that error is only set when success is False."""
        if v is not None and info.data.get('success', True):
            raise ValueError("error can only be set when success is False")
        return v


class HandlerExecutionContext(BaseModel):
    """
    Schema for handler execution context.
    
    Represents the full context in which a handler executes.
    """
    
    model_config = ConfigDict(validate_assignment=True)
    
    handler_name: str = Field(
        description="Name of the handler being executed"
    )
    
    action_id: Optional[int] = Field(
        default=None,
        description="ID of the action being executed"
    )
    
    phase_id: Optional[int] = Field(
        default=None,
        description="ID of the phase containing the action"
    )
    
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Execution context data"
    )
    
    config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Handler configuration"
    )
    
    execution_id: Optional[str] = Field(
        default=None,
        description="Unique execution identifier"
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Execution timestamp"
    )


class ValidationResult(BaseModel):
    """
    Schema for validation results.
    
    Used to report validation success/failure with details.
    """
    
    model_config = ConfigDict(validate_assignment=True)
    
    is_valid: bool = Field(
        description="Whether validation passed"
    )
    
    errors: List[str] = Field(
        default_factory=list,
        description="List of validation error messages"
    )
    
    warnings: List[str] = Field(
        default_factory=list,
        description="List of validation warnings"
    )
    
    validated_data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Validated and potentially transformed data"
    )


class SchemaValidator:
    """
    Utility class for schema validation operations.
    
    Provides helper methods for validating data against Pydantic schemas.
    """
    
    @staticmethod
    def validate_input(
        data: Dict[str, Any],
        schema_class: type[BaseModel]
    ) -> ValidationResult:
        """
        Validate input data against a schema.
        
        Args:
            data: Data to validate
            schema_class: Pydantic model class to validate against
            
        Returns:
            ValidationResult with validation status and details
        """
        try:
            validated = schema_class(**data)
            return ValidationResult(
                is_valid=True,
                validated_data=validated.model_dump()
            )
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"Validation failed: {error_msg}")
            return ValidationResult(
                is_valid=False,
                errors=[error_msg]
            )
    
    @staticmethod
    def validate_output(
        data: Dict[str, Any],
        schema_class: type[BaseModel],
        strict: bool = True
    ) -> ValidationResult:
        """
        Validate output data against a schema.
        
        Args:
            data: Data to validate
            schema_class: Pydantic model class to validate against
            strict: If True, fail on any validation error
            
        Returns:
            ValidationResult with validation status and details
        """
        try:
            validated = schema_class(**data)
            return ValidationResult(
                is_valid=True,
                validated_data=validated.model_dump()
            )
        except Exception as e:
            error_msg = str(e)
            
            if strict:
                logger.error(f"Strict validation failed: {error_msg}")
                return ValidationResult(
                    is_valid=False,
                    errors=[error_msg]
                )
            else:
                logger.warning(f"Non-strict validation warning: {error_msg}")
                return ValidationResult(
                    is_valid=True,
                    warnings=[error_msg],
                    validated_data=data
                )
    
    @staticmethod
    def get_schema_fields(schema_class: type[BaseModel]) -> Dict[str, Any]:
        """
        Get field information from a schema.
        
        Args:
            schema_class: Pydantic model class
            
        Returns:
            Dictionary with field names and their properties
        """
        return {
            name: {
                "type": str(field.annotation),
                "required": field.is_required(),
                "default": field.default if field.default is not None else None,
                "description": field.description
            }
            for name, field in schema_class.model_fields.items()
        }
    
    @staticmethod
    def generate_example(schema_class: type[BaseModel]) -> Dict[str, Any]:
        """
        Generate an example instance of a schema.
        
        Args:
            schema_class: Pydantic model class
            
        Returns:
            Dictionary with example data
        """
        example = {}
        
        for name, field in schema_class.model_fields.items():
            # Check if field has a default value (not PydanticUndefined)
            if field.default is not PydanticUndefined:
                example[name] = field.default
            elif field.default_factory is not None:
                example[name] = field.default_factory()
            else:
                # Provide sensible defaults based on type
                annotation = field.annotation
                if annotation is str:
                    example[name] = f"example_{name}"
                elif annotation is int:
                    example[name] = 0
                elif annotation is bool:
                    example[name] = True
                elif annotation is dict or annotation == Dict[str, Any]:
                    example[name] = {}
                elif annotation is list or annotation == List[Any]:
                    example[name] = []
                else:
                    example[name] = None
        
        return example


# Global validator instance
_validator = SchemaValidator()


def get_validator() -> SchemaValidator:
    """
    Get the global SchemaValidator instance.
    
    Returns:
        Global SchemaValidator
    """
    return _validator
