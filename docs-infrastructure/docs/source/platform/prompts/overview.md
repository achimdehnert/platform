# Übersicht

Das Prompt Template System bietet eine robuste, typsichere Verwaltung und Ausführung von LLM-Prompts.

## Architektur

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

## Kernkomponenten

### 1. Schemas (Pydantic Models)

- **PromptTemplateSpec** - Vollständige Template-Definition
- **PromptVariable** - Variable mit Typ, Validierung, Defaults
- **LLMConfig** - Provider, Model, Temperature, Retry-Settings
- **PromptExecution** - Ausführungs-Record mit Metriken

### 2. Registry (Template Storage)

- **InMemoryRegistry** - Für Tests
- **FileRegistry** - YAML/JSON Dateien
- **DjangoRegistry** - Django ORM Backend
- **RedisCache** - Verteiltes Caching

### 3. Security

- **Injection Detection** - Erkennt Prompt-Injection-Versuche
- **Input Sanitization** - Bereinigt User-Input
- **Unicode Normalization** - Erkennt Obfuskation

### 4. Execution

- **TemplateRenderer** - Jinja2-basiertes Rendering
- **RetryStrategy** - Exponential Backoff
- **PromptExecutor** - Orchestriert alles

### 5. Observability

- **PromptEvent** - Strukturierte Events
- **Prometheus Metrics** - Counter, Histogramme
- **Logging** - Strukturierte JSON-Logs

## Design-Prinzipien

1. **Immutability** - Alle Schemas nutzen `frozen=True`
2. **Type Safety** - Vollständige Pydantic-Validierung
3. **Platform Agnostic** - Keine Django-Abhängigkeit im Core
4. **Extensible** - Protocol-basierte Registries und Clients
5. **Observable** - Eingebaute Metriken und Events
