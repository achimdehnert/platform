from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, validator
from apps.bfagent.services.handlers.config_models import BaseHandlerConfig

class JsonSchemaValidatorHandlerConfig(BaseHandlerConfig):
    """
    Configuration model for JSON Schema Validator handler.

    Attributes:
        required_fields (List[str]): List of field paths that must be present in JSON
        schema (Dict[str, Any]): JSON schema definition for validation
        strict_mode (bool): If true, fails on any additional properties not in schema
    """

    required_fields: List[str] = Field(
        default=[],
        description="List of field paths that must be present in JSON",
        example=["user.id", "user.email", "metadata.timestamp"]
    )

    schema: Dict[str, Any] = Field(
        default={},
        description="JSON schema definition for validation",
        example={
            "type": "object",
            "properties": {
                "user": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "email": {"type": "string", "format": "email"}
                    }
                }
            }
        }
    )

    strict_mode: bool = Field(
        default=False,
        description="If true, fails on any additional properties not in schema"
    )

    @validator('schema')
    def validate_schema(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validates that schema is a non-empty dictionary with valid structure."""
        if not isinstance(v, dict):
            raise ValueError("Schema must be a dictionary")
        if v and 'type' not in v:
            raise ValueError("Schema must specify a 'type' field")
        return v

    @validator('required_fields')
    def validate_required_fields(cls, v: List[str]) -> List[str]:
        """Validates that required fields are properly formatted."""
        for field in v:
            if not isinstance(field, str) or not field.strip():
                raise ValueError("Required fields must be non-empty strings")
            if not all(part.isalnum() or part == '_' for part in field.split('.')):
                raise ValueError(f"Invalid field path format: {field}")
        return v