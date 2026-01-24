# Konfiguration

BF Agent folgt dem **Zero-Hardcoding-Prinzip**: Alle Konfigurationen
werden in der Datenbank gespeichert und können über Django Admin
geändert werden.

## Übersicht

```{mermaid}
flowchart TB
    subgraph "Konfigurationsebenen"
        ENV[".env Datei"]
        DB["Datenbank"]
        ADMIN["Django Admin"]
    end
    
    ENV --> |"Secrets, URLs"| DB
    DB --> |"Runtime Config"| ADMIN
    ADMIN --> |"UI Änderungen"| DB
```

## Umgebungsvariablen

Diese Variablen **müssen** in `.env` gesetzt werden:

### Erforderlich

| Variable | Beschreibung | Beispiel |
|----------|--------------|----------|
| `SECRET_KEY` | Django Secret Key | `your-secret-key` |
| `DATABASE_URL` | Datenbank-Verbindung | `postgres://...` |
| `REDIS_URL` | Redis für Celery | `redis://localhost:6379/0` |

### AI Provider

Mindestens einer erforderlich:

```ini
# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_ORG_ID=org-...  # Optional

# Anthropic Claude
ANTHROPIC_API_KEY=sk-ant-...

# Lokales LLM
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

### Optional

```ini
# Debug Mode
DEBUG=False

# Logging
LOG_LEVEL=INFO

# Rate Limiting
RATE_LIMIT_ENABLED=True
RATE_LIMIT_PER_MINUTE=60

# File Storage
MEDIA_ROOT=/var/bf-agent/media
STATIC_ROOT=/var/bf-agent/static

# n8n Integration
N8N_BASE_URL=http://localhost:5678
N8N_API_KEY=...
```

## Datenbank-Konfiguration

### Domain Configuration

Über Admin: **Core → Domain Configurations**

```python
# Programmatisch
from bf_agent.core.models import DomainConfiguration

DomainConfiguration.objects.create(
    name="comics",
    verbose_name="Comic Creator",
    enabled=True,
    config={
        "ai_provider": "openai",
        "default_model": "gpt-4",
        "image_provider": "dalle3",
        "max_pages": 32,
        "rate_limit": 100,
    }
)
```

### Handler Configuration

Über Admin: **Core → Handler Registrations**

```python
from bf_agent.core.models import HandlerRegistration

HandlerRegistration.objects.create(
    handler_name="story_generator",
    domain="comics",
    enabled=True,
    priority=10,
    config={
        "timeout": 300,
        "retry_count": 3,
        "async_mode": True,
        "ai_config": {
            "model": "gpt-4",
            "temperature": 0.7,
            "max_tokens": 4000,
        }
    }
)
```

## AI Provider Konfiguration

### Multi-Provider Setup

BF Agent unterstützt mehrere AI-Provider gleichzeitig:

```python
# settings.py oder Datenbank
AI_PROVIDERS = {
    "openai": {
        "enabled": True,
        "models": ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"],
        "default_model": "gpt-4",
        "rate_limit": 100,
    },
    "anthropic": {
        "enabled": True,
        "models": ["claude-3-opus", "claude-3-sonnet"],
        "default_model": "claude-3-sonnet",
        "rate_limit": 50,
    },
    "ollama": {
        "enabled": True,
        "models": ["llama3.2", "codellama"],
        "default_model": "llama3.2",
        "for_domains": ["adult_content"],  # Lokale Verarbeitung
    }
}
```

### Provider-Routing

Routing basierend auf Content-Typ:

```python
# In Domain Config
CONTENT_ROUTING = {
    "standard": "openai",
    "adult": "ollama",
    "code": "anthropic",
    "translation": "openai",
}
```

## Caching-Konfiguration

### Redis Cache

```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'bf_agent',
        'TIMEOUT': 3600,  # 1 Stunde
    }
}
```

### AI Response Caching

```python
# Domain Config
AI_CACHE_CONFIG = {
    "enabled": True,
    "ttl": 86400,  # 24 Stunden
    "max_size": 10000,  # Max Cache-Einträge
    "excluded_handlers": ["live_data_handler"],
}
```

## Logging-Konfiguration

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/bf-agent/app.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'bf_agent': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

## Validierung

Prüfe deine Konfiguration:

```bash
# Konfiguration validieren
python manage.py check

# AI Provider testen
python manage.py test_ai_providers

# Alle Checks
python manage.py validate_config
```

```{seealso}
- {doc}`/developer/architecture` - Architektur-Übersicht
- {doc}`/reference/handlers` - Handler-Konfiguration
```
