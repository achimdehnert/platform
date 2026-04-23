"""
Exception hierarchy for the Prompt Template System.

All exceptions inherit from PromptTemplateError for easy catching.
Each exception includes structured context for logging and debugging.
"""

from typing import Any


class PromptTemplateError(Exception):
    """Base exception for all prompt template errors."""

    def __init__(self, message: str, context: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.context = context or {}

    def __str__(self) -> str:
        if self.context:
            ctx_str = ", ".join(f"{k}={v!r}" for k, v in self.context.items())
            return f"{self.message} [{ctx_str}]"
        return self.message


# === Template Errors ===


class TemplateNotFoundError(PromptTemplateError):
    """Template with given key does not exist."""

    def __init__(self, template_key: str, registry: str | None = None):
        super().__init__(
            f"Template not found: {template_key}",
            context={"template_key": template_key, "registry": registry},
        )
        self.template_key = template_key


class TemplateValidationError(PromptTemplateError):
    """Template schema validation failed."""

    def __init__(self, template_key: str, errors: list[str]):
        super().__init__(
            f"Template validation failed: {template_key}",
            context={"template_key": template_key, "errors": errors},
        )
        self.template_key = template_key
        self.errors = errors


# === Variable Errors ===


class VariableValidationError(PromptTemplateError):
    """Base class for variable validation errors."""

    def __init__(self, variable_name: str, message: str, **kwargs: Any):
        super().__init__(
            message,
            context={"variable_name": variable_name, **kwargs},
        )
        self.variable_name = variable_name


class VariableMissingError(VariableValidationError):
    """Required variable was not provided."""

    def __init__(self, variable_name: str, template_key: str):
        super().__init__(
            variable_name,
            f"Required variable missing: {variable_name}",
            template_key=template_key,
        )
        self.template_key = template_key


class VariableTypeError(VariableValidationError):
    """Variable has wrong type."""

    def __init__(
        self, variable_name: str, expected_type: str, actual_type: str
    ):
        super().__init__(
            variable_name,
            f"Variable '{variable_name}' has wrong type: expected {expected_type}, got {actual_type}",
            expected_type=expected_type,
            actual_type=actual_type,
        )
        self.expected_type = expected_type
        self.actual_type = actual_type


class VariableLengthError(VariableValidationError):
    """Variable exceeds maximum length."""

    def __init__(self, variable_name: str, max_length: int, actual_length: int):
        super().__init__(
            variable_name,
            f"Variable '{variable_name}' exceeds max length: {actual_length} > {max_length}",
            max_length=max_length,
            actual_length=actual_length,
        )
        self.max_length = max_length
        self.actual_length = actual_length


# === Security Errors ===


class SecurityError(PromptTemplateError):
    """Base class for security-related errors."""

    pass


class InjectionDetectedError(SecurityError):
    """Potential prompt injection detected in input."""

    def __init__(
        self,
        variable_name: str,
        pattern_matched: str,
        input_preview: str | None = None,
    ):
        preview = input_preview[:100] if input_preview else None
        super().__init__(
            f"Potential injection detected in variable '{variable_name}'",
            context={
                "variable_name": variable_name,
                "pattern_matched": pattern_matched,
                "input_preview": preview,
            },
        )
        self.variable_name = variable_name
        self.pattern_matched = pattern_matched


class InputSanitizationError(SecurityError):
    """Input could not be safely sanitized."""

    def __init__(self, variable_name: str, reason: str):
        super().__init__(
            f"Failed to sanitize input for variable '{variable_name}': {reason}",
            context={"variable_name": variable_name, "reason": reason},
        )
        self.variable_name = variable_name
        self.reason = reason


# === Execution Errors ===


class ExecutionError(PromptTemplateError):
    """Base class for execution-related errors."""

    pass


class LLMError(ExecutionError):
    """Error during LLM API call."""

    def __init__(
        self,
        message: str,
        provider: str | None = None,
        model: str | None = None,
        status_code: int | None = None,
        retryable: bool = False,
    ):
        super().__init__(
            message,
            context={
                "provider": provider,
                "model": model,
                "status_code": status_code,
                "retryable": retryable,
            },
        )
        self.provider = provider
        self.model = model
        self.status_code = status_code
        self.retryable = retryable


class RenderError(ExecutionError):
    """Error during template rendering (Jinja2)."""

    def __init__(self, template_key: str, error_detail: str):
        super().__init__(
            f"Failed to render template '{template_key}': {error_detail}",
            context={"template_key": template_key, "error_detail": error_detail},
        )
        self.template_key = template_key
        self.error_detail = error_detail


class ContextLimitError(ExecutionError):
    """Rendered prompt exceeds LLM context window."""

    def __init__(
        self,
        template_key: str,
        estimated_tokens: int,
        max_tokens: int,
    ):
        super().__init__(
            f"Context limit exceeded for '{template_key}': {estimated_tokens} > {max_tokens}",
            context={
                "template_key": template_key,
                "estimated_tokens": estimated_tokens,
                "max_tokens": max_tokens,
            },
        )
        self.template_key = template_key
        self.estimated_tokens = estimated_tokens
        self.max_tokens = max_tokens


class CostLimitError(ExecutionError):
    """Execution would exceed cost limit."""

    def __init__(
        self,
        template_key: str,
        estimated_cost: float,
        max_cost: float,
    ):
        super().__init__(
            f"Cost limit exceeded for '{template_key}': ${estimated_cost:.4f} > ${max_cost:.4f}",
            context={
                "template_key": template_key,
                "estimated_cost": estimated_cost,
                "max_cost": max_cost,
            },
        )
        self.template_key = template_key
        self.estimated_cost = estimated_cost
        self.max_cost = max_cost
