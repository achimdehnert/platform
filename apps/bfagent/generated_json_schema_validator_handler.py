import json
from typing import Dict, Any, List, Optional
from jsonschema import validate, ValidationError, SchemaError
from apps.bfagent.services.handlers.base import BaseProcessingHandler
from apps.bfagent.services.handlers.exceptions import HandlerValidationError, HandlerExecutionError

class JsonSchemaValidatorHandler(BaseProcessingHandler):
    """
    Validates JSON data against a configurable schema, checking syntax, required fields,
    and nested object structure while providing detailed validation error messages.

    This handler performs JSON validation against a provided schema, ensuring:
    - Valid JSON syntax
    - Required fields presence
    - Correct data types
    - Schema conformance
    - Optional strict mode validation

    Attributes:
        display_name (str): Display name of the handler
        description (str): Detailed description of the handler functionality
        version (str): Handler version number
    """

    display_name = "JSON Schema Validator"
    description = "Validates JSON data against a configurable schema, checking syntax, required fields, and nested object structure while providing detailed validation error messages."
    version = "1.0.0"

    def _validate_json_syntax(self, json_string: str) -> Dict[str, Any]:
        """
        Validates JSON string syntax and returns parsed JSON.

        Args:
            json_string (str): Input JSON string to validate

        Returns:
            Dict[str, Any]: Parsed JSON data

        Raises:
            HandlerValidationError: If JSON syntax is invalid
        """
        try:
            return json.loads(json_string)
        except json.JSONDecodeError as e:
            raise HandlerValidationError(f"Invalid JSON syntax: {str(e)}")

    def _check_required_fields(self, data: Dict[str, Any], required_fields: List[str]) -> List[str]:
        """
        Checks presence of required fields in JSON data.

        Args:
            data (Dict[str, Any]): JSON data to check
            required_fields (List[str]): List of required field paths

        Returns:
            List[str]: List of missing required fields
        """
        missing_fields = []
        for field_path in required_fields:
            parts = field_path.split('.')
            current = data
            try:
                for part in parts:
                    current = current[part]
            except (KeyError, TypeError):
                missing_fields.append(field_path)
        return missing_fields

    def _validate_schema(
        self, 
        data: Dict[str, Any], 
        schema: Dict[str, Any],
        strict_mode: bool
    ) -> List[str]:
        """
        Validates JSON data against provided schema.

        Args:
            data (Dict[str, Any]): JSON data to validate
            schema (Dict[str, Any]): JSON schema for validation
            strict_mode (bool): Whether to enforce strict validation

        Returns:
            List[str]: List of validation error messages

        Raises:
            HandlerValidationError: If schema is invalid
        """
        if strict_mode:
            schema['additionalProperties'] = False

        try:
            validate(instance=data, schema=schema)
            return []
        except SchemaError as e:
            raise HandlerValidationError(f"Invalid schema configuration: {str(e)}")
        except ValidationError as e:
            return [str(e)]

    def _get_validated_fields(self, data: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
        """
        Extracts list of successfully validated fields.

        Args:
            data (Dict[str, Any]): Validated JSON data
            schema (Dict[str, Any]): JSON schema used for validation

        Returns:
            List[str]: List of validated field paths
        """
        validated_fields = []
        properties = schema.get('properties', {})
        
        def extract_fields(obj: Dict[str, Any], path: str = '') -> None:
            for key, value in obj.items():
                full_path = f"{path}.{key}" if path else key
                if isinstance(value, dict) and 'properties' in value:
                    extract_fields(value['properties'], full_path)
                else:
                    validated_fields.append(full_path)

        extract_fields(properties)
        return validated_fields

    def execute(self, context: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes JSON schema validation logic.

        Args:
            context (Dict[str, Any]): Execution context containing json_string
            config (Dict[str, Any]): Configuration parameters including schema and validation options

        Returns:
            Dict[str, Any]: Validation results containing:
                - is_valid (bool): Whether validation passed
                - errors (List[str]): List of validation error messages
                - error_count (int): Number of validation errors
                - validated_fields (List[str]): Successfully validated fields

        Raises:
            HandlerValidationError: For validation configuration errors
            HandlerExecutionError: For execution errors
        """
        if 'json_string' not in context:
            raise HandlerValidationError("Missing required 'json_string' in context")

        json_string = context['json_string']
        required_fields = config.get('required_fields', [])
        schema = config.get('schema', {})
        strict_mode = config.get('strict_mode', False)

        # Validate JSON syntax
        try:
            data = self._validate_json_syntax(json_string)
        except HandlerValidationError as e:
            return {
                'is_valid': False,
                'errors': [str(e)],
                'error_count': 1,
                'validated_fields': []
            }

        # Check required fields
        missing_fields = self._check_required_fields(data, required_fields)
        
        # Validate against schema
        schema_errors = self._validate_schema(data, schema, strict_mode)
        
        # Compile results
        all_errors = []
        if missing_fields:
            all_errors.extend([f"Missing required field: {field}" for field in missing_fields])
        if schema_errors:
            all_errors.extend(schema_errors)

        validated_fields = [] if all_errors else self._get_validated_fields(data, schema)

        return {
            'is_valid': len(all_errors) == 0,
            'errors': all_errors,
            'error_count': len(all_errors),
            'validated_fields': validated_fields
        }