# Observability

Eingebautes Monitoring, Logging und Metriken für Prompt-Ausführungen.

## Events

Strukturierte Events für alle Ausführungsphasen:

```python
from creative_services.prompts.observability import (
    PromptEvent,
    EventType,
    emit_event,
)

emit_event(PromptEvent(
    event_type=EventType.EXECUTION_STARTED,
    execution_id=uuid4(),
    template_key="my.template.v1",
    app_name="my_app",
))
```

### Event Types

| Event | Beschreibung |
|-------|--------------|
| `EXECUTION_STARTED` | Ausführung gestartet |
| `EXECUTION_COMPLETED` | Erfolgreich abgeschlossen |
| `EXECUTION_FAILED` | Fehlgeschlagen |
| `CACHE_HIT` | Aus Cache geliefert |
| `CACHE_MISS` | Cache Miss |
| `LLM_REQUEST_STARTED` | LLM-Aufruf gestartet |
| `LLM_RETRY` | Retry eines LLM-Aufrufs |
| `INJECTION_DETECTED` | Injection erkannt |

## Prometheus Metrics

Optional mit `prometheus_client`:

```python
from creative_services.prompts.observability import (
    is_prometheus_available,
    record_execution,
)

if is_prometheus_available():
    record_execution(
        template_key="my.template.v1",
        status="success",
        duration_seconds=1.5,
        tokens_input=100,
        tokens_output=50,
    )
```

### Verfügbare Metriken

| Metrik | Typ |
|--------|-----|
| `prompt_executions_total` | Counter |
| `prompt_execution_duration_seconds` | Histogram |
| `prompt_tokens_total` | Counter |
| `prompt_cost_dollars_total` | Counter |
| `prompt_cache_hits_total` | Counter |

## Logging

Events werden automatisch geloggt:

```python
import logging
logging.basicConfig(level=logging.INFO)

# Events gehen an 'creative_services.prompts.events'
```
