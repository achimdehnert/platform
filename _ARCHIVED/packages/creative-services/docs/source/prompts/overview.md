# Prompt Template System Overview

The Prompt Template System provides a robust, type-safe way to manage and execute LLM prompts.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      PromptExecutor                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │
│  │ Registry │  │ Renderer │  │  Cache   │  │    LLM Client    │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
         │              │             │                │
         ▼              ▼             ▼                ▼
┌──────────────┐ ┌───────────┐ ┌───────────┐ ┌─────────────────┐
│TemplateSpec  │ │  Jinja2   │ │  Redis/   │ │ OpenAI/Anthropic│
│  (Pydantic)  │ │ Templates │ │  Memory   │ │     APIs        │
└──────────────┘ └───────────┘ └───────────┘ └─────────────────┘
```

## Core Components

### 1. Schemas (Pydantic Models)

- **PromptTemplateSpec** - Complete template definition
- **PromptVariable** - Variable with type, validation, defaults
- **LLMConfig** - Provider, model, temperature, retry settings
- **PromptExecution** - Execution record with metrics

### 2. Registry (Template Storage)

- **InMemoryRegistry** - For testing
- **FileRegistry** - YAML/JSON files
- **DjangoRegistry** - Django ORM backend
- **RedisCache** - Distributed caching

### 3. Security

- **Injection Detection** - Detects prompt injection attempts
- **Input Sanitization** - Cleans user input
- **Unicode Normalization** - Handles obfuscation attempts

### 4. Execution

- **TemplateRenderer** - Jinja2-based rendering
- **RetryStrategy** - Exponential backoff
- **PromptExecutor** - Orchestrates everything

### 5. Observability

- **PromptEvent** - Structured events
- **Prometheus Metrics** - Counters, histograms
- **Logging** - Structured JSON logs

## Design Principles

1. **Immutability** - All schemas use `frozen=True`
2. **Type Safety** - Full Pydantic validation
3. **Platform Agnostic** - No Django dependency in core
4. **Extensible** - Protocol-based registries and clients
5. **Observable** - Built-in metrics and events

## Example Flow

```python
# 1. Define template
template = PromptTemplateSpec(
    template_key="story.chapter.v1",
    domain_code="writing",
    name="Chapter Generator",
    system_prompt="You are a creative writer...",
    user_prompt="Write chapter {{ chapter_num }} about {{ topic }}",
    variables=[
        PromptVariable(name="chapter_num", var_type=VariableType.INTEGER),
        PromptVariable(name="topic", required=True),
    ],
)

# 2. Save to registry
registry.save(template)

# 3. Execute
result = await executor.execute(
    template_key="story.chapter.v1",
    variables={"chapter_num": 1, "topic": "the journey begins"},
)

# 4. Access result
print(result.content)           # LLM response
print(result.execution.cost_dollars)  # Cost tracking
print(result.execution.tokens_total)  # Token usage
```
