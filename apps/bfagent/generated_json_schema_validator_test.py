import json
import pytest
from typing import Dict, Any
from jsonschema import ValidationError
from apps.bfagent.services.handlers.processing.json_schema_validator import JsonSchemaValidatorHandler
from apps.bfagent.services.handlers.exceptions import HandlerValidationError, HandlerExecutionError

class TestJsonSchemaValidatorHandler:
    @pytest.fixture
    def handler(self) -> JsonSchemaValidatorHandler:
        return JsonSchemaValidatorHandler()

    @pytest.fixture
    def valid_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "user": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "email": {"type": "string"},
                        "age": {"type": "integer"}
                    }
                }
            }
        }

    @pytest.fixture
    def valid_json(self) -> str:
        return json.dumps({
            "user": {
                "id": "123",
                "email": "test@example.com",
                "age": 30
            }
        })

    def test_execute_success(self, handler, valid_json, valid_schema):
        """Test successful validation scenario."""
        context = {"json_string": valid_json}
        config = {
            "schema": valid_schema,
            "required_fields": ["user.id", "user.email"],
            "strict_mode": False
        }

        result = handler.execute(context, config)

        assert result["is_valid"] is True
        assert len(result["errors"]) == 0
        assert result["error_count"] == 0
        assert "user.id" in result["validated_fields"]
        assert "user.email" in result["validated_fields"]

    def test_invalid_json_syntax(self, handler, valid_schema):
        """Test handling of invalid JSON syntax."""
        context = {"json_string": '{"invalid": "json"'}
        config = {"schema": valid_schema}

        result = handler.execute(context, config)

        assert result["is_valid"] is False
        assert len(result["errors"]) == 1
        assert "Invalid JSON syntax" in result["errors"][0]

    def test_missing_required_fields(self, handler, valid_schema):
        """Test detection of missing required fields."""
        context = {"json_string": '{"user": {"id": "123"}}'}
        config = {
            "schema": valid_schema,
            "required_fields": ["user.id", "user.email"],
        }

        result = handler.execute(context, config)

        assert result["is_valid"] is False
        assert len(result["errors"]) == 1
        assert "Missing required field: user.email" in result["errors"]

    def test_schema_validation_error(self, handler, valid_schema):
        """Test schema validation failure."""
        context = {"json_string": '{"user": {"id": 123, "email": "invalid"}}'}
        config = {"schema": valid_schema}

        result = handler.execute(context, config)

        assert result["is_valid"] is False
        assert len(result["errors"]) > 0

    def test_strict_mode_validation(self, handler, valid_schema):
        """Test strict mode validation."""
        context = {
            "json_string": '{"user": {"id": "123", "email": "test@example.com", "extra": "field"}}'
        }
        config = {
            "schema": valid_schema,
            "strict_mode": True
        }

        result = handler.execute(context, config)

        assert result["is_valid"] is False
        assert any("additional properties" in error.lower() for error in result["errors"])

    def test_missing_json_string(self, handler, valid_schema):
        """Test handling of missing json_string in context."""
        context = {}
        config = {"schema": valid_schema}

        with pytest.raises(HandlerValidationError) as exc_info:
            handler.execute(context, config)
        assert "Missing required 'json_string'" in str(exc_info.value)

    def test_invalid_schema(self, handler):
        """Test handling of invalid schema configuration."""
        context = {"json_string": "{}"}
        config = {"schema": {"invalid": "schema"}}

        result = handler.execute(context, config)
        assert result["is_valid"] is False
        assert len(result["errors"]) > 0

    @pytest.mark.parametrize("json_input,expected_valid", [
        ('{"user": {"id": "123"}}', True),
        ('{"user": {"id": 123}}', False),
        ('{"user": {}}', False),
        ('{"other": {}}', False),
    ])
    def test_various_input_scenarios(self, handler, json_input, expected_valid):
        """Test various input scenarios with parameterization."""
        context = {"json_string": json_input}
        config = {
            "schema": {
                "type": "object",
                "properties": {
                    "user": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"}
                        },
                        "required": ["id"]
                    }
                },
                "required": ["user"]
            }
        }

        result = handler.execute(context, config)
        assert result["is_valid"] == expected_valid