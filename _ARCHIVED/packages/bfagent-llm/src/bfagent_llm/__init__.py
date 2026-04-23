"""
bfagent-llm v1.0: LLM integration for BFAgent Hub ecosystem (ADR-089).

Two modes:
- Django apps (DB-driven): `from bfagent_llm.django_app.service import completion`
- MCP servers (no DB): `from bfagent_llm import GroqLLMAdapter, OpenAILLMAdapter`

Provides:
- SecureTemplateEngine: Sandboxed Jinja2 rendering
- PromptRegistry: Multi-layer caching for templates
- ResilientPromptService: LLM calls with retry, circuit breaker, fallback
- LLM Adapters: Gateway, OpenAI, Anthropic, Groq, LiteLLM, Fallback
- PromptFramework: High-level facade for easy usage
- Django App: DB-driven model routing (bfagent_llm.django_app)
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
    LiteLLMAdapter,
    FallbackLLMAdapter,
    GROQ_MODEL_MAP,
)
from bfagent_llm.facade import PromptFramework

__version__ = "1.0.0"

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
    "LiteLLMAdapter",
    "FallbackLLMAdapter",
    "GROQ_MODEL_MAP",
    # Facade
    "PromptFramework",
]
