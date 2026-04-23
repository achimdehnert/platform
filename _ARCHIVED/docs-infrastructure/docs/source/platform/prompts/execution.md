# Execution

Das Execution-Modul orchestriert Template-Rendering, LLM-Aufrufe, Caching und Retry-Logik.

## PromptExecutor

Der Haupt-Orchestrator:

```python
from creative_services.prompts import PromptExecutor, InMemoryRegistry
from creative_services.prompts.execution import InMemoryCache
from creative_services.prompts.integration import OpenAIClient

executor = PromptExecutor(
    registry=InMemoryRegistry(),
    llm_client=OpenAIClient(),
    app_name="my_app",
    cache=InMemoryCache(default_ttl=3600),
)
```

## Ausführung

```python
result = await executor.execute(
    template_key="my.template.v1",
    variables={"name": "Alice"},
    use_cache=True,
    user_id="user_123",
)

if result.success:
    print(result.content)
else:
    print(f"Error: {result.error}")
```

## Caching

### InMemoryCache

```python
from creative_services.prompts.execution import InMemoryCache

cache = InMemoryCache(default_ttl=3600)
cache.set("key", "value", ttl=300)
value = cache.get("key")
```

### RedisCache

```python
from creative_services.prompts.execution import RedisCache

cache = RedisCache(
    host="localhost",
    port=6379,
    prefix="prompts:",
)
```

## Retry Logic

Automatischer Retry mit Exponential Backoff:

```python
from creative_services.prompts import RetryConfig

config = RetryConfig(
    max_attempts=3,
    initial_delay_seconds=1.0,
    max_delay_seconds=30.0,
    exponential_base=2.0,
)
```
