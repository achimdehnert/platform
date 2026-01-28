"""
bfagent-llm: LLM integration for BFAgent Hub ecosystem.

Provides:
- SecureTemplateEngine: Sandboxed Jinja2 rendering
- PromptRegistry: Multi-layer caching for templates
- ResilientPromptService: LLM calls with retry, circuit breaker, fallback
- LLM Adapters: Gateway, OpenAI, Anthropic, Fallback
- PromptFramework: High-level facade for easy usage
"""

from bfagent_llm.engine import (
    SecureTemplateEngine,
    ValidationResult,
    RenderedPrompt,
    TemplateSecurityError,
    ContextValidationError,
)
from bfagent_llm.service import (
    ResilientPromptService,
    LLMResponse,
    ExecutionResult,
    CircuitBreaker,
    CircuitState,
    LLMClientProtocol,
)
from bfagent_llm.adapters import (
    GatewayLLMAdapter,
    OpenAILLMAdapter,
    AnthropicLLMAdapter,
    FallbackLLMAdapter,
)
from bfagent_llm.facade import PromptFramework

__version__ = "0.1.0"

__all__ = [
    # Engine
    "SecureTemplateEngine",
    "ValidationResult",
    "RenderedPrompt",
    "TemplateSecurityError",
    "ContextValidationError",
    # Service
    "ResilientPromptService",
    "LLMResponse",
    "ExecutionResult",
    "CircuitBreaker",
    "CircuitState",
    "LLMClientProtocol",
    # Adapters
    "GatewayLLMAdapter",
    "OpenAILLMAdapter",
    "AnthropicLLMAdapter",
    "FallbackLLMAdapter",
    # Facade
    "PromptFramework",
]
