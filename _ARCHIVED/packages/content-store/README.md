# content_store — Shared Django App (ADR-130)

Shared Django app for AI-generated content persistence across all platform hubs.

## Features

- **ContentItem**: Versioned, SHA-256 deduplicated content storage
- **ContentRelation**: Directed relations between content items
- **AdrCompliance**: ADR drift-detector compliance results
- **ContentStoreRouter**: Database router for dedicated `content_store` DB
- **ContentStoreService**: Service-layer API (ADR-041 compliant)

## Installation

```bash
pip install iil-content-store
```

## Usage

```python
# settings.py
INSTALLED_APPS = [..., "content_store"]
DATABASES = {
    "default": { ... },
    "content_store": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("CONTENT_STORE_DB_NAME", default="content_store"),
        "USER": config("CONTENT_STORE_DB_USER", default="content_store"),
        "PASSWORD": config("CONTENT_STORE_DB_PASSWORD"),
        "HOST": config("CONTENT_STORE_DB_HOST", default="localhost"),
        "PORT": config("CONTENT_STORE_DB_PORT", default="5432"),
    },
}
DATABASE_ROUTERS = ["content_store.router.ContentStoreRouter"]
```

```python
from content_store.services import ContentStoreService

item = ContentStoreService.save_content(
    tenant_id=1,
    source="travel-beat",
    content_type="story",
    ref_id="trip-42",
    content="A wonderful journey...",
)
```

## Platform Standards

- BigAutoField PK (ADR-022)
- tenant_id on all models (ADR-109)
- Service-layer only, no direct Model.objects in views (ADR-041)
- Django ORM, no hardcoded SQL (ADR-022)
