"""
Core Module - Consolidated Services for BF Agent Framework

This module provides centralized, production-ready services:

Services:
    - handlers: Unified handler framework with base classes
    - llm: Multi-provider LLM integration (OpenAI, Anthropic, etc.)
    - cache: Multi-backend caching (Redis, Memory, File)
    - storage: Unified storage (Local, S3, GCS)
    - export: Document export (DOCX, PDF, EPUB, Markdown)
    - extractors: File content extraction (PDF, DOCX, PPTX, Excel)

Event-Driven Architecture (Feature Flag controlled):
    - feature_flags: Runtime feature toggles
    - events: Event definitions
    - event_bus: Central event dispatcher

Hub Plugin System (Feature Flag controlled):
    - hub_registry: Dynamic hub management

Quick Start:
    # LLM
    from apps.core.services.llm import LLMService
    llm = LLMService()
    response = llm.complete("Hello!")

    # Cache
    from apps.core.services.cache import CacheService
    cache = CacheService()
    cache.set("key", "value")

    # Storage
    from apps.core.services.storage import StorageService
    storage = StorageService()
    storage.save("path/file.txt", content)

    # Export
    from apps.core.services.export import export_to
    result = export_to("docx", content, "output.docx")

    # Extractors
    from apps.core.services.extractors import extract_file
    result = extract_file("document.pdf")
    
    # Event Bus (only active when USE_EVENT_BUS=True)
    from apps.core.event_bus import event_bus
    from apps.core.events import Events
    event_bus.publish(Events.CHAPTER_CREATED, chapter_id=123)

Django Settings:
    INSTALLED_APPS = [
        ...
        'apps.core',
    ]
"""

default_app_config = "apps.core.apps.CoreConfig"

__version__ = "1.1.0"
__author__ = "BF Agent Team"

