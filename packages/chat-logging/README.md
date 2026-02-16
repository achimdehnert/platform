# chat-logging

Persistent chat conversation logging & quality management for Django apps.

Part of the platform ecosystem (ADR-037). Works with any app using `chat-agent`.

## Features

- **ChatConversation + ChatMessage** — Full conversation persistence
- **UseCaseCandidate** — Track unmet user needs
- **EvaluationScore** — Store evaluation metrics (DeepEval, LangFuse)
- **LoggingSessionBackend** — Drop-in wrapper for any SessionBackend
- **Django Admin** — Filter, search, review, export conversations

## Installation

```bash
pip install chat-logging
```

Add to `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    ...
    "chat_logging",
]
```

Run migrations:

```bash
python manage.py migrate chat_logging
```

## Usage

```python
from chat_agent import ChatAgent, InMemorySessionBackend
from chat_logging import LoggingSessionBackend

backend = LoggingSessionBackend(
    wrapped=InMemorySessionBackend(),
    app_name="drifttales",
    user=request.user,
)

agent = ChatAgent(
    toolkit=my_toolkit,
    completion=my_backend,
    session_backend=backend,  # conversations are now logged!
    system_prompt="...",
)
```

## Export

```python
from chat_logging.exporters import (
    export_conversations_csv,
    export_conversations_jsonl,
)
from chat_logging.models import ChatConversation

qs = ChatConversation.objects.filter(app_name="drifttales")
jsonl = export_conversations_jsonl(qs)
csv_data = export_conversations_csv(qs)
```
