# Platform & Creative Services

Das `creative-services` Package bietet wiederverwendbare AI-Services für alle Platform-Anwendungen.

```{toctree}
:maxdepth: 2

installation
prompts/index
integrations/index
```

## Übersicht

```
creative_services/
├── prompts/           # Prompt Template System
│   ├── schemas/       # Pydantic Schemas
│   ├── security/      # Injection Detection
│   ├── registry/      # Template Storage
│   ├── execution/     # Executor & Caching
│   └── integration/   # LLM Clients
├── core/              # LLM Infrastructure
└── adapters/          # Django Adapters
```

## Features

- **Prompt Template System** - Type-safe Prompt-Verwaltung mit Pydantic
- **LLM Clients** - OpenAI, Anthropic, Groq, Ollama
- **Security** - Prompt Injection Detection & Sanitization
- **Caching** - Redis & In-Memory mit TTL
- **Observability** - Prometheus Metrics & Events
