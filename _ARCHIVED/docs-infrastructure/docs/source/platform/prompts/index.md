# Prompt Template System

```{toctree}
:maxdepth: 2

overview
schemas
security
registry
execution
observability
```

## Übersicht

Das Prompt Template System bietet:

- **Type-safe Schemas** - Pydantic Models mit `frozen=True`
- **Injection Detection** - Schutz vor Prompt Injection
- **Multiple Registries** - Memory, File, Django ORM, Redis
- **Caching** - TTL-basiertes Caching
- **Retry Logic** - Exponential Backoff
- **Observability** - Prometheus Metrics & Events

## Quick Start

```python
from creative_services.prompts import (
    PromptTemplateSpec,
    PromptVariable,
    PromptExecutor,
    InMemoryRegistry,
)
from creative_services.prompts.integration import OpenAIClient

# Template definieren
template = PromptTemplateSpec(
    template_key="greeting.v1",
    domain_code="examples",
    name="Greeting",
    system_prompt="You are friendly.",
    user_prompt="Say hello to {{ name }}!",
    variables=[PromptVariable(name="name", required=True)],
)

# Registry & Executor
registry = InMemoryRegistry()
registry.save(template)

executor = PromptExecutor(
    registry=registry,
    llm_client=OpenAIClient(),
    app_name="my_app",
)

# Ausführen
result = await executor.execute(
    template_key="greeting.v1",
    variables={"name": "Alice"},
)
print(result.content)
```

## Tests

Das System hat **195 Tests** mit 100% Coverage der Kernfunktionalität.

```bash
pytest tests/prompts/ -v
```
