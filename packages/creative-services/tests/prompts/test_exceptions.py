"""Tests for prompt template exceptions."""

import pytest

from creative_services.prompts.exceptions import (
    PromptTemplateError,
    TemplateNotFoundError,
    TemplateValidationError,
    VariableMissingError,
    VariableTypeError,
    VariableLengthError,
    InjectionDetectedError,
    InputSanitizationError,
    LLMError,
    RenderError,
    ContextLimitError,
    CostLimitError,
)


class TestPromptTemplateError:
    """Tests for base exception."""

    def test_basic_message(self):
        err = PromptTemplateError("Something went wrong")
        assert str(err) == "Something went wrong"
        assert err.message == "Something went wrong"
        assert err.context == {}

    def test_with_context(self):
        err = PromptTemplateError(
            "Error occurred",
            context={"key": "value", "count": 42},
        )
        assert "key='value'" in str(err)
        assert "count=42" in str(err)

    def test_inheritance(self):
        err = PromptTemplateError("test")
        assert isinstance(err, Exception)


class TestTemplateNotFoundError:
    """Tests for template not found errors."""

    def test_basic(self):
        err = TemplateNotFoundError("my.template.key")
        assert err.template_key == "my.template.key"
        assert "my.template.key" in str(err)

    def test_with_registry(self):
        err = TemplateNotFoundError("my.template", registry="file")
        assert err.context["registry"] == "file"


class TestTemplateValidationError:
    """Tests for template validation errors."""

    def test_with_errors(self):
        errors = ["field1 is required", "field2 must be positive"]
        err = TemplateValidationError("test.template", errors)
        assert err.template_key == "test.template"
        assert err.errors == errors
        assert err.context["errors"] == errors


class TestVariableErrors:
    """Tests for variable-related errors."""

    def test_missing_error(self):
        err = VariableMissingError("character_name", "writing.character.v1")
        assert err.variable_name == "character_name"
        assert err.template_key == "writing.character.v1"
        assert "character_name" in str(err)

    def test_type_error(self):
        err = VariableTypeError("count", "integer", "string")
        assert err.variable_name == "count"
        assert err.expected_type == "integer"
        assert err.actual_type == "string"
        assert "expected integer" in str(err)

    def test_length_error(self):
        err = VariableLengthError("content", max_length=1000, actual_length=5000)
        assert err.variable_name == "content"
        assert err.max_length == 1000
        assert err.actual_length == 5000
        assert "5000 > 1000" in str(err)


class TestSecurityErrors:
    """Tests for security-related errors."""

    def test_injection_detected(self):
        err = InjectionDetectedError(
            variable_name="user_input",
            pattern_matched="ignore previous instructions",
            input_preview="Please ignore previous instructions and...",
        )
        assert err.variable_name == "user_input"
        assert err.pattern_matched == "ignore previous instructions"
        assert "user_input" in str(err)

    def test_injection_truncates_preview(self):
        long_input = "x" * 200
        err = InjectionDetectedError("input", "pattern", long_input)
        assert len(err.context["input_preview"]) == 100

    def test_sanitization_error(self):
        err = InputSanitizationError("field", "contains null bytes")
        assert err.variable_name == "field"
        assert err.reason == "contains null bytes"


class TestExecutionErrors:
    """Tests for execution-related errors."""

    def test_llm_error(self):
        err = LLMError(
            "Rate limit exceeded",
            provider="openai",
            model="gpt-4",
            status_code=429,
            retryable=True,
        )
        assert err.provider == "openai"
        assert err.model == "gpt-4"
        assert err.status_code == 429
        assert err.retryable is True

    def test_render_error(self):
        err = RenderError("my.template", "undefined variable 'foo'")
        assert err.template_key == "my.template"
        assert "undefined variable" in str(err)

    def test_context_limit_error(self):
        err = ContextLimitError("large.template", 150000, 128000)
        assert err.estimated_tokens == 150000
        assert err.max_tokens == 128000
        assert "150000 > 128000" in str(err)

    def test_cost_limit_error(self):
        err = CostLimitError("expensive.template", 0.50, 0.10)
        assert err.estimated_cost == 0.50
        assert err.max_cost == 0.10
        assert "$0.50" in str(err) or "0.5" in str(err)


class TestExceptionHierarchy:
    """Tests for exception inheritance."""

    def test_all_inherit_from_base(self):
        exceptions = [
            TemplateNotFoundError("key"),
            TemplateValidationError("key", []),
            VariableMissingError("var", "key"),
            VariableTypeError("var", "int", "str"),
            VariableLengthError("var", 100, 200),
            InjectionDetectedError("var", "pattern"),
            InputSanitizationError("var", "reason"),
            LLMError("error"),
            RenderError("key", "detail"),
            ContextLimitError("key", 100, 50),
            CostLimitError("key", 1.0, 0.5),
        ]

        for exc in exceptions:
            assert isinstance(exc, PromptTemplateError)
            assert isinstance(exc, Exception)

    def test_can_catch_by_category(self):
        from creative_services.prompts.exceptions import (
            SecurityError,
            ExecutionError,
            VariableValidationError,
        )

        # Security errors
        assert isinstance(InjectionDetectedError("v", "p"), SecurityError)
        assert isinstance(InputSanitizationError("v", "r"), SecurityError)

        # Execution errors
        assert isinstance(LLMError("e"), ExecutionError)
        assert isinstance(RenderError("k", "d"), ExecutionError)
        assert isinstance(ContextLimitError("k", 1, 1), ExecutionError)

        # Variable errors
        assert isinstance(VariableMissingError("v", "k"), VariableValidationError)
        assert isinstance(VariableTypeError("v", "a", "b"), VariableValidationError)
