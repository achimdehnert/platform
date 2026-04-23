"""
Registry module for template storage and retrieval.

Provides protocols and implementations for different storage backends:
- In-memory (for testing)
- File-based (YAML/JSON)
- Database (via adapter pattern)
- Django ORM (for Django projects)
- Redis (for distributed caching)
"""

from .protocols import TemplateRegistry, TemplateStore
from .memory import InMemoryRegistry
from .file import FileRegistry
from .django_registry import (
    DjangoRegistry,
    AsyncDjangoRegistry,
    DjangoModelAdapter,
    GenericDjangoAdapter,
)

__all__ = [
    "TemplateRegistry",
    "TemplateStore",
    "InMemoryRegistry",
    "FileRegistry",
    "DjangoRegistry",
    "AsyncDjangoRegistry",
    "DjangoModelAdapter",
    "GenericDjangoAdapter",
]
