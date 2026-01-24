# Installation Guide

## Prerequisites

- Python 3.9+
- Django 4.2+
- Existing Django project

## Installation Steps

### 1. Copy Handler Files
```bash
cp -r handlers/ your_project/apps/bfagent/services/
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Django Settings

Add to `settings.py`:
```python
import structlog

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": structlog.stdlib.ProcessorFormatter,
            "processor": structlog.processors.JSONRenderer(),
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "loggers": {
        "apps.bfagent.services.handlers": {
            "handlers": ["console"],
            "level": "INFO",
        },
    },
}

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)
```

### 4. Verify Installation
```bash
pytest tests/test_handlers.py -v
python examples/complete_pipeline_example.py
```

## Troubleshooting

### Import Errors
Ensure handlers are in: `apps/bfagent/services/handlers/`

### Pydantic Validation Errors
```bash
pip install --upgrade pydantic
```

### Logging Not Working
Check Django LOGGING configuration.

---

**Installation complete!** 🚀
