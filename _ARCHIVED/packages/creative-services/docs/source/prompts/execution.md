# Execution

The execution module orchestrates template rendering, LLM calls, caching, and retry logic.

## PromptExecutor

The main orchestrator for prompt execution:

```python
from creative_services.prompts import PromptExecutor, InMemoryRegistry
from creative_services.prompts.execution import InMemoryCache
from creative_services.prompts.integration import OpenAIClient

executor = PromptExecutor(
    registry=InMemoryRegistry(),
    llm_client=OpenAIClient(),
    app_name="my_app",
    cache=InMemoryCache(default_ttl=3600),
    cost_limit_dollars=1.0,  # Optional cost limit
)
```

### Basic Execution

```python
result = await executor.execute(
    template_key="my.template.v1",
    variables={"name": "Alice", "topic": "adventure"},
)

if result.success:
    print(result.content)
else:
    print(f"Error: {result.error}")
```

### Execution Options

```python
result = await executor.execute(
    template_key="my.template.v1",
    variables={"name": "Alice"},
    
    # Caching
    use_cache=True,           # Use cache (default: True)
    cache_ttl=3600,           # Cache TTL in seconds
    
    # LLM override
    llm_config_override=LLMConfig(
        temperature=0.9,
        max_tokens=2000,
    ),
    
    # Tracking
    user_id="user_123",       # For analytics
    metadata={"request_id": "req_456"},
)
```

## Template Rendering

Jinja2-based template rendering:

```python
from creative_services.prompts.execution import TemplateRenderer

renderer = TemplateRenderer()

system_prompt, user_prompt = renderer.render(
    template=template,
    variables={"name": "Alice"},
)
```

### Jinja2 Features

Templates support full Jinja2 syntax:

```jinja
{# Variables #}
Hello {{ name }}!

{# Conditionals #}
{% if genre == "fantasy" %}
In a magical realm...
{% else %}
In the real world...
{% endif %}

{# Loops #}
Characters:
{% for char in characters %}
- {{ char.name }}: {{ char.role }}
{% endfor %}

{# Filters #}
{{ description | upper }}
{{ items | join(", ") }}
```

## Caching

### InMemoryCache

For single-instance applications:

```python
from creative_services.prompts.execution import InMemoryCache

cache = InMemoryCache(default_ttl=3600)

# Manual operations
cache.set("key", "value", ttl=300)
value = cache.get("key")
cache.delete("key")
cache.clear()
```

### RedisCache

For distributed applications:

```python
from creative_services.prompts.execution import RedisCache

cache = RedisCache(
    host="localhost",
    port=6379,
    prefix="prompts:",
    default_ttl=3600,
)
```

## Retry Logic

Automatic retry with exponential backoff:

```python
from creative_services.prompts.execution import with_retry, RetryStrategy
from creative_services.prompts import RetryConfig

# Using with_retry decorator
response = await with_retry(
    llm_client.generate,
    config=RetryConfig(
        max_attempts=3,
        initial_delay_seconds=1.0,
        exponential_base=2.0,
    ),
    system_prompt="...",
    user_prompt="...",
)
```

### Retry Configuration

```python
from creative_services.prompts import RetryConfig

config = RetryConfig(
    max_attempts=3,              # Total attempts
    initial_delay_seconds=1.0,   # First retry delay
    max_delay_seconds=30.0,      # Maximum delay
    exponential_base=2.0,        # Backoff multiplier
    retry_on_status_codes=[429, 500, 502, 503, 504],
)
```

## LLM Response

Structure returned by LLM clients:

```python
from creative_services.prompts.execution import LLMResponse

response = LLMResponse(
    content="Generated text...",
    model="gpt-4o",
    provider="openai",
    tokens_input=100,
    tokens_output=50,
    cost_dollars=0.002,
    finish_reason="stop",
    raw_response={...},  # Provider-specific response
)

# Computed property
response.tokens_total  # 150
```

## Factory Function

Quick executor creation:

```python
from creative_services.prompts.execution import create_executor

# With defaults
executor = create_executor(app_name="my_app")

# With custom settings
executor = create_executor(
    registry=my_registry,
    llm_client=my_client,
    app_name="my_app",
    enable_cache=True,
)
```
