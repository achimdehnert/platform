# bfagent-llm

LLM integration for the BFAgent Hub ecosystem.

## Features

- **Prompt Framework**: DB-driven prompt templates with Jinja2 rendering
- **Secure Template Engine**: Sandboxed rendering with security validations
- **Multi-Layer Caching**: L1 (local) + L2 (Redis) + L3 (DB) caching
- **Resilient Service**: Retry, circuit breaker, tier fallback
- **LLM Adapters**: Gateway, OpenAI, Anthropic, Fallback

## Installation

```bash
pip install bfagent-llm
# or with all providers
pip install "bfagent-llm[all]"
# or from git
pip install "bfagent-llm @ git+https://github.com/achimdehnert/platform.git#subdirectory=packages/bfagent-llm"
```

## Quick Start

```python
from bfagent_llm import PromptFramework

# Get singleton instance
framework = PromptFramework.get_instance()

# Execute a prompt template
result = await framework.execute(
    template_code="expert_hub.generate_content",
    context={"topic": "Python async programming"},
    tier="standard",
)
print(result.content)
```

## Components

### SecureTemplateEngine

Sandboxed Jinja2 rendering with security features:
- Blocks dangerous patterns (`eval`, `exec`, `__dunder__`)
- Context sanitization
- JSON schema validation
- Custom safe filters

```python
from bfagent_llm import SecureTemplateEngine

engine = SecureTemplateEngine()
result = engine.render(
    template="Hello {{ name }}!",
    context={"name": "World"},
)
print(result.rendered)  # "Hello World!"
```

### PromptRegistry

Multi-layer caching for prompt templates:

```python
from bfagent_llm import CachedPromptRegistry

registry = CachedPromptRegistry()
template = registry.get("expert_hub.generate_content", tenant_id=tenant_id)
```

### ResilientPromptService

LLM calls with resilience patterns:

```python
from bfagent_llm import ResilientPromptService, GatewayLLMAdapter

adapter = GatewayLLMAdapter(base_url="http://llm-gateway:8100")
service = ResilientPromptService(llm_client=adapter)

result = await service.execute(
    system_prompt="You are a helpful assistant.",
    user_prompt="Explain quantum computing.",
    tier="standard",
)
```

### LLM Adapters

```python
from bfagent_llm import (
    GatewayLLMAdapter,    # BFAgent LLM Gateway
    OpenAILLMAdapter,     # Direct OpenAI API
    AnthropicLLMAdapter,  # Direct Anthropic API
    FallbackLLMAdapter,   # Chain with fallback
)

# Gateway (recommended for production)
gateway = GatewayLLMAdapter(base_url="http://llm-gateway:8100")

# Fallback chain
fallback = FallbackLLMAdapter([
    GatewayLLMAdapter(base_url="http://llm-gateway:8100"),
    OpenAILLMAdapter(api_key="..."),
])
```

## Django Integration

Add to `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    ...
    "bfagent_llm",
]
```

Settings:

```python
# LLM Gateway
LLM_GATEWAY_URL = "http://llm-gateway:8100"
LLM_GATEWAY_TIMEOUT = 120.0

# Direct API (optional)
OPENAI_API_KEY = "..."
ANTHROPIC_API_KEY = "..."

# Caching
REDIS_URL = "redis://localhost:6379/0"
```

## License

MIT
