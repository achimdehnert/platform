"""
bfagent-llm: LLM integration for BFAgent Hub ecosystem.

Provides:
- SecureTemplateEngine: Sandboxed Jinja2 rendering
- PromptRegistry: Multi-layer caching for templates
- ResilientPromptService: LLM calls with retry, circuit breaker, fallback
- LLM Adapters: Gateway, OpenAI, Anthropic, Groq, Fallback
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
    TierConfig,
)
from bfagent_llm.adapters import (
    GatewayLLMAdapter,
    OpenAILLMAdapter,
    AnthropicLLMAdapter,
    GroqLLMAdapter,
    FallbackLLMAdapter,
    GROQ_MODEL_MAP,
)
from bfagent_llm.facade import PromptFramework

__version__ = "0.2.0"

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
    "TierConfig",
    # Adapters
    "GatewayLLMAdapter",
    "OpenAILLMAdapter",
    "AnthropicLLMAdapter",
    "GroqLLMAdapter",
    "FallbackLLMAdapter",
    "GROQ_MODEL_MAP",
    # Facade
    "PromptFramework",
]
