# JSON Schema Validator Handler

## Purpose
The JSON Schema Validator handler provides robust JSON data validation against configurable schemas. It ensures data quality and structure conformance by validating JSON syntax, required fields, data types, and schema compliance.

## Features
- JSON syntax validation
- Required fields verification
- Schema-based validation
- Strict mode for additional properties
- Detailed error reporting
- Nested object support
- Field path validation

## Configuration Parameters

| Parameter | Type | Description | Default | Required |
|-----------|------|-------------|---------|----------|
| required_fields | List[str] | List of field paths that must be present in JSON | [] | No |
| schema | Dict[str, Any] | JSON schema definition for validation | {} | No |
| strict_mode | bool | If true, fails on any additional properties not in schema | false | No |

## Input Requirements
The handler expects a JSON string in the context:
```python
context = {
    "json_string": "..." # Valid JSON string to validate
}
```

## Output Format
The handler returns a dictionary containing:
```python
{
    "is_valid": bool,  # Whether validation passed
    "errors": List[str],  # List of validation error messages
    "error_count": int,  # Number of validation errors
    "validated_fields": List[str]  # Successfully validated fields
}
```

## Error Handling

The handler handles the following error scenarios:
1. Invalid JSON Syntax
   - Malformed JSON input
   - Syntax errors

2. Missing Required Fields
   - Required fields not present in input
   - Nested field path validation

3. Invalid Data Types
   - Type mismatches
   - Format validation failures

4. Schema Validation Errors
   - Schema conformance failures
   - Additional properties in strict mode

5. Malformed Schema
   - Invalid schema configuration
   - Schema structural errors

## Best Practices
1. Define clear schema structures
2. Use strict mode for strict data validation
3. Provide specific field paths for required fields
4. Handle all potential error cases
5. Review validation results thoroughly

## Dependencies
- jsonschema
- json (standard library)