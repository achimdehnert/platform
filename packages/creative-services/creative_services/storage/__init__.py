"""
creative_services.storage — Content Store Phase 1.

Public API:
    ContentItem, ContentRelation  — Pydantic models
    ContentStore                  — async (asyncpg), for MCP / Agent-Team
    SyncContentStore              — sync wrapper, for Django apps (bfagent, travel-beat)
"""

from .models import ContentItem, ContentRelation, SourceService, SourceType
from .store import ContentStore
from .django_adapter import SyncContentStore

__all__ = [
    "ContentItem",
    "ContentRelation",
    "SourceService",
    "SourceType",
    "ContentStore",
    "SyncContentStore",
]
