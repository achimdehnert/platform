# Storage Service Migration Guide

## Overview

This guide helps migrate from existing storage implementations to the consolidated Core Storage Service.

## Existing Implementations

| Location | Class | Features | Migration Effort |
|----------|-------|----------|------------------|
| `bfagent/services/storage_service.py` | `StorageService` | Basic chapter CRUD | 5 min |
| `bfagent/services/content_storage.py` | `ContentStorageService` | Full project structure | 10 min |
| Django Models | `FileField` | Media uploads | No change needed |

## Quick Migration

### 1. Import Changes

```python
# OLD
from apps.bfagent.services.storage_service import StorageService
from apps.bfagent.services.content_storage import ContentStorageService

# NEW
from apps.core.services.storage import ProjectStorage, storage
```

### 2. StorageService Migration

**Before:**
```python
from apps.bfagent.services.storage_service import StorageService

storage = StorageService(base_path='generated_content')
storage.save_chapter(project_slug, chapter_number, content)
content = storage.load_chapter(project_slug, chapter_number)
exists = storage.chapter_exists(project_slug, chapter_number)
```

**After:**
```python
from apps.core.services.storage import ProjectStorage

storage = ProjectStorage(project_slug)
storage.save_chapter(chapter_number, content)
content = storage.load_chapter(chapter_number)
exists = storage.chapter_exists(chapter_number)
```

### 3. ContentStorageService Migration

**Before:**
```python
from apps.bfagent.services.content_storage import ContentStorageService

storage = ContentStorageService(base_path=Path.home() / 'domains')

# Get paths
chapter_path = storage.get_chapter_path(project_slug)
export_path = storage.get_export_path(project_slug)

# Save content
storage.save_chapter(project_slug, chapter_number, content, metadata={...})
storage.save_character(project_slug, "protagonist", {...})
storage.save_metadata(project_slug, {...})
```

**After:**
```python
from apps.core.services.storage import ProjectStorage

storage = ProjectStorage(project_slug, base_path="~/domains")

# Paths are handled internally
# Save content
storage.save_chapter(chapter_number, content, metadata={...})
storage.save_character("protagonist", {...})
storage.save_metadata({...})
```

## Feature Comparison

| Feature | Old Implementations | New Core Service |
|---------|---------------------|------------------|
| Multiple backends | ❌ Local only | ✅ Local/Media/S3 |
| File metadata | Partial | ✅ Full (size, type, checksum) |
| Versioning | Partial | ✅ Built-in |
| Project structure | ✅ | ✅ Improved |
| S3 support | ❌ | ✅ |
| Presigned URLs | ❌ | ✅ (S3) |
| Health checks | ❌ | ✅ |

## Detailed Examples

### Simple File Operations

```python
from apps.core.services.storage import storage

# Write
storage.write("docs/readme.md", "# Hello World")
storage.write_json("config.json", {"key": "value"})

# Read
content = storage.read("docs/readme.md")
text = storage.read_text("docs/readme.md")
data = storage.read_json("config.json")

# Check & Delete
if storage.exists("docs/readme.md"):
    storage.delete("docs/readme.md")
```

### Project-Based Storage

```python
from apps.core.services.storage import ProjectStorage

# Initialize for project
project = ProjectStorage("my-novel")

# Chapters
project.save_chapter(1, "# Chapter 1\n\nContent...", metadata={
    "title": "The Beginning",
    "word_count": 2500
})

content = project.load_chapter(1)
chapters = project.list_chapters()  # [1, 2, 3, ...]

# Characters
project.save_character("protagonist", {
    "name": "John",
    "age": 35,
    "traits": ["brave", "curious"]
})

character = project.load_character("protagonist")

# Metadata
project.save_metadata({
    "title": "My Novel",
    "genre": "Fiction",
    "target_words": 80000
})

metadata = project.load_metadata()
```

### Using Different Backends

```python
from apps.core.services.storage import (
    get_storage, ProjectStorage,
    LocalStorageBackend, MediaStorageBackend, S3StorageBackend,
    StorageConfig
)

# Local storage
local = LocalStorageBackend(StorageConfig(
    base_path="/var/data/myapp"
))

# Django media storage
media = MediaStorageBackend()  # Uses MEDIA_ROOT

# S3 storage
s3 = S3StorageBackend(StorageConfig(
    bucket_name="my-bucket",
    region="us-east-1",
    access_key="...",
    secret_key="..."
))

# Use S3 for a project
project = ProjectStorage("my-novel", backend=s3)
```

## Django Settings

```python
# Storage Configuration
STORAGE_BACKEND = env("STORAGE_BACKEND", default="local")
STORAGE_BASE_PATH = env("STORAGE_BASE_PATH", default=str(BASE_DIR / "storage"))

# S3 Configuration (optional)
AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME", default=None)
AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default="us-east-1")
AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID", default=None)
AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY", default=None)
AWS_S3_ENDPOINT_URL = env("AWS_S3_ENDPOINT_URL", default=None)  # For MinIO
```

## Testing

```python
import pytest
from apps.core.services.storage import (
    LocalStorageBackend, ProjectStorage, StorageConfig
)

@pytest.fixture
def test_storage(tmp_path):
    return LocalStorageBackend(StorageConfig(
        base_path=str(tmp_path)
    ))

def test_write_read(test_storage):
    test_storage.write("test.txt", "Hello")
    assert test_storage.read_text("test.txt") == "Hello"

def test_project_storage(tmp_path):
    project = ProjectStorage("test-project", base_path=str(tmp_path))
    
    project.save_chapter(1, "Chapter content")
    assert project.chapter_exists(1)
    assert project.load_chapter(1) == "Chapter content"
```

## Troubleshooting

### Permission Errors

```python
from apps.core.services.storage import storage

# Check health
if not storage.health_check():
    print("Storage backend not healthy!")
    
# Check specific path
import os
path = storage.backend.config.get_base_path()
print(f"Base path: {path}")
print(f"Writable: {os.access(path, os.W_OK)}")
```

### S3 Connection Issues

```python
from apps.core.services.storage import S3StorageBackend, StorageConfig

config = StorageConfig(
    bucket_name="my-bucket",
    endpoint_url="http://localhost:9000"  # MinIO
)

try:
    s3 = S3StorageBackend(config)
    s3.health_check()
except Exception as e:
    print(f"S3 error: {e}")
```
