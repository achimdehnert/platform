"""
BookWriting Domain Handlers.

Handlers for Book Writing Studio functionality:
- Project enrichment (outline, premise, themes, etc.)
- Chapter generation and management
- Character development and enrichment
- Content writing and editing
"""

from .enrichment import (
    ChapterEnrichmentHandler,
    CharacterEnrichmentHandler,
    ProjectEnrichmentHandler,
)
from .generation import ChapterGenerateHandler, CharacterCastHandler, WorldCreationHandler

__all__ = [
    # Enrichment
    "ProjectEnrichmentHandler",
    "ChapterEnrichmentHandler",
    "CharacterEnrichmentHandler",
    # Generation
    "ChapterGenerateHandler",
    "CharacterCastHandler",
    "WorldCreationHandler",
]
