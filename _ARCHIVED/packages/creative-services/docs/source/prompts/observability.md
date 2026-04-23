# Observability

Built-in monitoring, logging, and metrics for prompt executions.

## Events

Structured events for all execution stages:

```python
from creative_services.prompts.observability import (
    PromptEvent,
    EventType,
    emit_event,
)

# Events are emitted automatically by PromptExecutor
# You can also emit custom events:

emit_event(PromptEvent(
    event_type=EventType.EXECUTION_STARTED,
    execution_id=uuid4(),
    template_key="my.template.v1",
    app_name="my_app",
    data={"custom": "data"},
))
```

### Event Types

| Event | Description |
|-------|-------------|
| `EXECUTION_STARTED` | Execution began |
| `EXECUTION_COMPLETED` | Execution finished successfully |
| `EXECUTION_FAILED` | Execution failed |
| `CACHE_HIT` | Response served from cache |
| `CACHE_MISS` | Cache miss, LLM call needed |
| `CACHE_SET` | Response cached |
| `LLM_REQUEST_STARTED` | LLM API call started |
| `LLM_REQUEST_COMPLETED` | LLM API call completed |
| `LLM_REQUEST_FAILED` | LLM API call failed |
| `LLM_RETRY` | Retrying LLM call |
| `VALIDATION_FAILED` | Variable validation failed |
| `INJECTION_DETECTED` | Prompt injection detected |

## Prometheus Metrics

Optional Prometheus metrics (requires `prometheus_client`):

```python
from creative_services.prompts.observability import (
    is_prometheus_available,
    record_execution,
)

if is_prometheus_available():
    # Metrics are recorded automatically
    record_execution(
        template_key="my.template.v1",
        app_name="my_app",
        status="success",
        duration_seconds=1.5,
        tokens_input=100,
        tokens_output=50,
        cost_dollars=0.002,
        llm_provider="openai",
    )
```

### Available Metrics

| Metric | Type | Labels |
|--------|------|--------|
| `prompt_executions_total` | Counter | template_key, app_name, status |
| `prompt_execution_duration_seconds` | Histogram | template_key, app_name |
| `prompt_tokens_total` | Counter | template_key, direction (input/output) |
| `prompt_cost_dollars_total` | Counter | template_key, llm_provider |
| `prompt_cache_hits_total` | Counter | template_key |
| `prompt_cache_misses_total` | Counter | template_key |
| `prompt_injection_detected_total` | Counter | template_key, pattern |

## Logging

Events are automatically logged with structured data:

```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Events are logged to 'creative_services.prompts.events'
logger = logging.getLogger('creative_services.prompts.events')
```

### Log Levels

| Event Type | Log Level |
|------------|-----------|
| `*_FAILED` | ERROR |
| `INJECTION_DETECTED` | WARNING |
| All others | INFO |

## Custom Event Handlers

Register custom handlers for events:

```python
from creative_services.prompts.observability import register_event_handler

def my_handler(event: PromptEvent):
    # Send to external monitoring
    send_to_datadog(event)
    
    # Or store in database
    save_event_to_db(event)

register_event_handler(my_handler)
```

## Execution Callbacks

Use callbacks for post-execution processing:

```python
def on_complete(execution: PromptExecution):
    # Log to analytics
    analytics.track("prompt_executed", {
        "template": execution.template_key,
        "tokens": execution.tokens_total,
        "cost": execution.cost_dollars,
    })

executor = PromptExecutor(
    registry=registry,
    llm_client=client,
    on_execution_complete=on_complete,
)
```
