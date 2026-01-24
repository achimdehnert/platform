# Cache Service Migration Guide

## Overview

This guide helps migrate from existing cache implementations to the consolidated Core Cache Service.

## Existing Implementations

| Location | Type | Backend | Migration Effort |
|----------|------|---------|------------------|
| `bfagent/services/handlers/decorators.py` | `@with_caching` | Django | 2 min/usage |
| `bfagent/services/context_enrichment/enricher.py` | Inline methods | Django | 10 min |
| `medtrans/services/translation_cache.py` | `TranslationCache` | JSON File | 15 min |

## Quick Migration

### 1. Import Changes

```python
# OLD: Django cache
from django.core.cache import cache

# NEW: Core cache
from apps.core.services.cache import cache

# OLD: Custom decorator
from apps.bfagent.services.handlers.decorators import with_caching

# NEW: Core decorator
from apps.core.services.cache import cached
```

### 2. Basic Operations

```python
# These work the same way
cache.set("key", "value", ttl=300)
value = cache.get("key")
cache.delete("key")
```

### 3. Decorator Migration

```python
# OLD
@with_caching(cache_key_prefix="chapter_data", ttl=300)
def collect(self, context):
    ...

# NEW
@cached(ttl=300, key_prefix="chapter_data")
def collect(self, context):
    ...
```

## Detailed Migration Examples

### From `@with_caching` Decorator

**Before:**
```python
from apps.bfagent.services.handlers.decorators import with_caching

class MyHandler:
    cache_enabled = True
    cache_ttl = 300
    
    @with_caching(cache_key_prefix="my_data", ttl=300)
    def collect(self, context):
        return expensive_operation()
```

**After:**
```python
from apps.core.services.cache import cached

class MyHandler:
    @cached(ttl=300, key_prefix="my_data")
    def collect(self, context):
        return expensive_operation()
```

### From `DatabaseContextEnricher`

**Before:**
```python
from django.core.cache import cache

class DatabaseContextEnricher:
    CACHE_TTL = 300
    CACHE_PREFIX = 'ctx_enrich'
    
    def _build_cache_key(self, schema_name, params):
        sorted_params = sorted(params.items())
        params_str = "_".join(f"{k}:{v}" for k, v in sorted_params)
        return f"{self.CACHE_PREFIX}:{schema_name}:{params_str}"
    
    def _get_from_cache(self, schema_name, params):
        cache_key = self._build_cache_key(schema_name, params)
        return cache.get(cache_key)
```

**After:**
```python
from apps.core.services.cache import cache, generate_cache_key

class DatabaseContextEnricher:
    CACHE_TTL = 300
    CACHE_PREFIX = 'ctx_enrich'
    
    def _get_from_cache(self, schema_name, params):
        cache_key = generate_cache_key(
            schema_name, params, prefix=self.CACHE_PREFIX
        )
        return cache.get(cache_key)
```

### From `TranslationCache` (File-based)

**Before:**
```python
from apps.medtrans.services.translation_cache import TranslationCache

cache = TranslationCache(cache_file="translations.json")
cache.save_translation(source, target, "de", "en")
result = cache.get_translation(source, "de", "en")
```

**After:**
```python
from apps.core.services.cache import get_cache, CacheConfig

cache = get_cache("file", config=CacheConfig(
    cache_dir="/path/to/cache",
    cache_file="translations.json",
    key_prefix="trans"
))

key = f"de:en:{source_hash}"
cache.set(key, {"source": source, "target": target}, ttl=None)
result = cache.get(key)
```

## Django Settings

```python
# Cache Configuration
CACHE_BACKEND = env("CACHE_BACKEND", default="django")
CACHE_DEFAULT_TTL = env.int("CACHE_DEFAULT_TTL", default=300)
CACHE_KEY_PREFIX = env("CACHE_KEY_PREFIX", default="bfagent")
CACHE_ENABLE_STATS = env.bool("CACHE_ENABLE_STATS", default=True)

# Redis URL (for direct Redis backend)
REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/0")
```

## Feature Comparison

| Feature | Old Implementations | New Core Service |
|---------|---------------------|------------------|
| Multiple backends | ❌ Per-implementation | ✅ Memory/Django/File/Redis |
| Stats tracking | Partial | ✅ Full (hits/misses/errors) |
| Tag-based invalidation | ❌ | ✅ |
| Distributed locking | ❌ | ✅ |
| TTL support | ✅ | ✅ |
| Key versioning | Partial | ✅ |
| Bulk operations | ❌ | ✅ (get_many/set_many) |
| Health checks | ❌ | ✅ |

## Testing

```python
import pytest
from apps.core.services.cache import MemoryCacheBackend, CacheConfig

@pytest.fixture
def test_cache():
    return MemoryCacheBackend(CacheConfig(
        default_ttl=60,
        key_prefix="test"
    ))

def test_basic_operations(test_cache):
    test_cache.set("key", "value")
    assert test_cache.get("key") == "value"
    
    test_cache.delete("key")
    assert test_cache.get("key") is None
```
