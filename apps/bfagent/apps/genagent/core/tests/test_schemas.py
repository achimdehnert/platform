"""
Tests for GenAgent Schemas - Feature 4: Pydantic Schemas

Author: GenAgent Development Team
Created: 2025-01-19
"""

import pytest
from datetime import datetime
from pydantic import BaseModel, Field, ValidationError
from apps.genagent.core.schemas import (
    BaseHandlerInput,
    BaseHandlerOutput,
    HandlerExecutionContext,
    ValidationResult,
    SchemaValidator,
    get_validator
)


class TestBaseHandlerInput:
    """Test suite for BaseHandlerInput schema."""
    
    def test_create_with_defaults(self):
        """Test creating input with default values."""
        input_data = BaseHandlerInput()
        
        assert input_data.context == {}
        assert input_data.config == {}
        assert input_data.metadata is None
    
    def test_create_with_data(self):
        """Test creating input with provided data."""
        input_data = BaseHandlerInput(
            context={"user_id": 123},
            config={"mode": "test"},
            metadata={"source": "test"}
        )
        
        assert input_data.context == {"user_id": 123}
        assert input_data.config == {"mode": "test"}
        assert input_data.metadata == {"source": "test"}
    
    def test_allows_extra_fields(self):
        """Test that extra fields are allowed."""
        input_data = BaseHandlerInput(
            context={},
            extra_field="allowed"
        )
        
        assert input_data.extra_field == "allowed"
    
    def test_validates_assignment(self):
        """Test that assignment validation works."""
        input_data = BaseHandlerInput()
        input_data.context = {"new": "data"}
        
        assert input_data.context == {"new": "data"}
    
    def test_strips_whitespace(self):
        """Test that string whitespace is stripped."""
        # This would apply if we had string fields with strip enabled
        # For now, just verify the config is set
        assert BaseHandlerInput.model_config['str_strip_whitespace'] is True


class TestBaseHandlerOutput:
    """Test suite for BaseHandlerOutput schema."""
    
    def test_successful_output(self):
        """Test creating successful output."""
        output = BaseHandlerOutput(
            success=True,
            result={"data": "value"}
        )
        
        assert output.success is True
        assert output.result == {"data": "value"}
        assert output.error is None
    
    def test_failed_output(self):
        """Test creating failed output."""
        output = BaseHandlerOutput(
            success=False,
            error="Something went wrong"
        )
        
        assert output.success is False
        assert output.error == "Something went wrong"
        assert output.result is None
    
    def test_error_validation_fails_with_success_true(self):
        """Test that error with success=True raises validation error."""
        with pytest.raises(ValidationError):
            BaseHandlerOutput(
                success=True,
                error="This should fail"
            )
    
    def test_metadata_optional(self):
        """Test that metadata is optional."""
        output = BaseHandlerOutput(success=True)
        assert output.metadata is None
        
        output_with_meta = BaseHandlerOutput(
            success=True,
            metadata={"execution_time": 1.5}
        )
        assert output_with_meta.metadata == {"execution_time": 1.5}


class TestHandlerExecutionContext:
    """Test suite for HandlerExecutionContext schema."""
    
    def test_minimal_context(self):
        """Test creating context with minimal data."""
        context = HandlerExecutionContext(
            handler_name="test_handler"
        )
        
        assert context.handler_name == "test_handler"
        assert context.action_id is None
        assert context.phase_id is None
        assert context.context == {}
        assert context.config == {}
        assert context.execution_id is None
        assert isinstance(context.timestamp, datetime)
    
    def test_full_context(self):
        """Test creating context with all fields."""
        now = datetime.now()
        
        context = HandlerExecutionContext(
            handler_name="test_handler",
            action_id=1,
            phase_id=2,
            context={"user": "test"},
            config={"mode": "production"},
            execution_id="exec_123",
            timestamp=now
        )
        
        assert context.handler_name == "test_handler"
        assert context.action_id == 1
        assert context.phase_id == 2
        assert context.context == {"user": "test"}
        assert context.config == {"mode": "production"}
        assert context.execution_id == "exec_123"
        assert context.timestamp == now
    
    def test_handler_name_required(self):
        """Test that handler_name is required."""
        with pytest.raises(ValidationError):
            HandlerExecutionContext()


class TestValidationResult:
    """Test suite for ValidationResult schema."""
    
    def test_valid_result(self):
        """Test creating a valid validation result."""
        result = ValidationResult(
            is_valid=True,
            validated_data={"key": "value"}
        )
        
        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == []
        assert result.validated_data == {"key": "value"}
    
    def test_invalid_result_with_errors(self):
        """Test creating an invalid result with errors."""
        result = ValidationResult(
            is_valid=False,
            errors=["Error 1", "Error 2"]
        )
        
        assert result.is_valid is False
        assert len(result.errors) == 2
        assert result.validated_data is None
    
    def test_warnings_optional(self):
        """Test that warnings are optional."""
        result = ValidationResult(
            is_valid=True,
            warnings=["Warning message"]
        )
        
        assert len(result.warnings) == 1


class TestSchemaValidator:
    """Test suite for SchemaValidator utility class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = SchemaValidator()
    
    def test_validate_input_success(self):
        """Test successful input validation."""
        data = {
            "context": {"user": "test"},
            "config": {"mode": "test"}
        }
        
        result = self.validator.validate_input(data, BaseHandlerInput)
        
        assert result.is_valid is True
        assert result.errors == []
        assert result.validated_data is not None
    
    def test_validate_input_failure(self):
        """Test failed input validation."""
        # Create a schema that will fail
        class StrictSchema(BaseModel):
            required_field: str
        
        data = {}  # Missing required field
        
        result = self.validator.validate_input(data, StrictSchema)
        
        assert result.is_valid is False
        assert len(result.errors) > 0
    
    def test_validate_output_strict_success(self):
        """Test successful strict output validation."""
        data = {
            "success": True,
            "result": {"data": "value"}
        }
        
        result = self.validator.validate_output(data, BaseHandlerOutput, strict=True)
        
        assert result.is_valid is True
        assert result.errors == []
    
    def test_validate_output_strict_failure(self):
        """Test failed strict output validation."""
        data = {
            "success": True,
            "error": "This should fail"  # Error with success=True
        }
        
        result = self.validator.validate_output(data, BaseHandlerOutput, strict=True)
        
        assert result.is_valid is False
        assert len(result.errors) > 0
    
    def test_validate_output_non_strict(self):
        """Test non-strict output validation."""
        class StrictSchema(BaseModel):
            required_field: str
        
        data = {}  # Missing required field
        
        result = self.validator.validate_output(data, StrictSchema, strict=False)
        
        # Non-strict should return success with warnings
        assert result.is_valid is True
        assert len(result.warnings) > 0
    
    def test_get_schema_fields(self):
        """Test getting field information from schema."""
        fields = self.validator.get_schema_fields(BaseHandlerInput)
        
        assert "context" in fields
        assert "config" in fields
        assert "metadata" in fields
        
        # Check field properties
        assert fields["context"]["required"] is False  # Has default
        assert fields["context"]["description"] == "Execution context data"
    
    def test_generate_example(self):
        """Test generating example data from schema."""
        example = self.validator.generate_example(BaseHandlerInput)
        
        assert isinstance(example, dict)
        assert "context" in example
        assert "config" in example
        assert isinstance(example["context"], dict)
        assert isinstance(example["config"], dict)
    
    def test_generate_example_with_defaults(self):
        """Test that defaults are used in examples."""
        example = self.validator.generate_example(BaseHandlerOutput)
        
        # Check that fields with no defaults get sensible values
        assert "success" in example
        assert "result" in example


class TestGlobalValidator:
    """Test suite for global validator accessor."""
    
    def test_get_validator_singleton(self):
        """Test that get_validator returns same instance."""
        validator1 = get_validator()
        validator2 = get_validator()
        
        assert validator1 is validator2
        assert isinstance(validator1, SchemaValidator)


class TestCustomSchemas:
    """Test suite for custom schema extensions."""
    
    def test_extend_base_input(self):
        """Test extending BaseHandlerInput."""
        class CustomInput(BaseHandlerInput):
            custom_field: str = Field(description="Custom field")
        
        custom = CustomInput(
            context={},
            custom_field="test"
        )
        
        assert custom.custom_field == "test"
        assert custom.context == {}
    
    def test_extend_base_output(self):
        """Test extending BaseHandlerOutput."""
        class CustomOutput(BaseHandlerOutput):
            execution_time: float = Field(description="Execution time")
        
        custom = CustomOutput(
            success=True,
            execution_time=1.5
        )
        
        assert custom.success is True
        assert custom.execution_time == 1.5
    
    def test_nested_schemas(self):
        """Test using nested schemas."""
        class NestedData(BaseModel):
            value: str
            count: int
        
        class ContainerOutput(BaseHandlerOutput):
            nested: NestedData
        
        output = ContainerOutput(
            success=True,
            nested=NestedData(value="test", count=5)
        )
        
        assert output.nested.value == "test"
        assert output.nested.count == 5


class TestEdgeCases:
    """Test suite for edge cases."""
    
    def test_empty_context(self):
        """Test handling empty context."""
        context = HandlerExecutionContext(handler_name="test")
        assert context.context == {}
    
    def test_large_context(self):
        """Test handling large context data."""
        large_data = {f"key_{i}": f"value_{i}" for i in range(1000)}
        
        input_data = BaseHandlerInput(context=large_data)
        assert len(input_data.context) == 1000
    
    def test_special_characters_in_data(self):
        """Test handling special characters."""
        input_data = BaseHandlerInput(
            context={"special": "!@#$%^&*()"},
            config={"unicode": "🎉✨"}
        )
        
        assert input_data.context["special"] == "!@#$%^&*()"
        assert input_data.config["unicode"] == "🎉✨"
    
    def test_none_values(self):
        """Test handling None values."""
        output = BaseHandlerOutput(
            success=True,
            result=None,
            error=None
        )
        
        assert output.result is None
        assert output.error is None
