"""
Prompt Template System for creative-services.

A generic, platform-agnostic prompt templating system that provides:
- Pydantic-based schemas for templates and executions
- Security validators and sanitizers
- Multiple storage backends (in-memory, file, database)
- Observability with structured events and metrics
- Template inheritance, partials, and chains

Usage:
    from creative_services.prompts import (
        PromptTemplateSpec,
        PromptExecution,
        TemplateRegistry,
        InMemoryRegistry,
        render_template,
    )
"""

from .exceptions import (
    PromptTemplateError,
    TemplateNotFoundError,
    TemplateValidationError,
    VariableValidationError,
    VariableMissingError,
    VariableTypeError,
    SecurityError,
    InjectionDetectedError,
    InputSanitizationError,
    ExecutionError,
    LLMError,
    RenderError,
    ContextLimitError,
    CostLimitError,
)

from .schemas import (
    PromptVariable,
    VariableType,
    LLMConfig,
    RetryConfig,
    PromptTemplateSpec,
    PromptExecution,
    ExecutionStatus,
)

from .registry import (
    TemplateRegistry,
    TemplateStore,
    InMemoryRegistry,
    FileRegistry,
)

from .security import (
    check_injection,
    sanitize_for_prompt,
    normalize_text,
)

from .execution import (
    render_template,
    TemplateRenderer,
    InMemoryCache,
    build_cache_key,
    with_retry,
    PromptExecutor,
    LLMClient,
    LLMResponse,
    ExecutionResult,
    create_executor,
)

from .observability import (
    PromptEvent,
    EventType,
    emit_event,
    record_execution,
)

from .migration import (
    BFAgentTemplateAdapter,
    convert_bfagent_template,
    convert_to_bfagent_format,
)

from .registry import (
    DjangoRegistry,
    AsyncDjangoRegistry,
)

from .execution import (
    RedisCache,
    AsyncRedisCache,
)

__all__ = [
    # Exceptions
    "PromptTemplateError",
    "TemplateNotFoundError",
    "TemplateValidationError",
    "VariableValidationError",
    "VariableMissingError",
    "VariableTypeError",
    "SecurityError",
    "InjectionDetectedError",
    "InputSanitizationError",
    "ExecutionError",
    "LLMError",
    "RenderError",
    "ContextLimitError",
    "CostLimitError",
    # Schemas
    "PromptVariable",
    "VariableType",
    "LLMConfig",
    "RetryConfig",
    "PromptTemplateSpec",
    "PromptExecution",
    "ExecutionStatus",
    # Registry
    "TemplateRegistry",
    "TemplateStore",
    "InMemoryRegistry",
    "FileRegistry",
    # Security
    "check_injection",
    "sanitize_for_prompt",
    "normalize_text",
    # Execution
    "render_template",
    "TemplateRenderer",
    "InMemoryCache",
    "build_cache_key",
    "with_retry",
    "PromptExecutor",
    "LLMClient",
    "LLMResponse",
    "ExecutionResult",
    "create_executor",
    # Observability
    "PromptEvent",
    "EventType",
    "emit_event",
    "record_execution",
    # Migration
    "BFAgentTemplateAdapter",
    "convert_bfagent_template",
    "convert_to_bfagent_format",
    # Django Registry
    "DjangoRegistry",
    "AsyncDjangoRegistry",
    # Redis Cache
    "RedisCache",
    "AsyncRedisCache",
]
