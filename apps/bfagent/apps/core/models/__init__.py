"""
Core Models Package

This package contains all core application models.

Models are organized by functionality:
- domain.py: Domain/App management
- handler_category.py: Handler categorization (DB over Enum)
- url_pattern.py: Normalized URL pattern storage
- agent.py: AI Agent definitions (imported from legacy location)
- media_base.py: Abstract base classes for media production workflows

All models use:
    ✅ Integer primary keys
    ✅ Proper foreign key constraints
    ✅ Database over hardcoded enums
    ✅ PostgreSQL-ready design
"""

# Import legacy models from models.py
from apps.core.models_legacy import Domain

from .handler import Handler

# Import new normalized models
from .handler_category import HandlerCategory
from .url_pattern import URLPattern

# Import media base classes (abstract, not registered with Django)
from .media_base import (
    AbstractPreset,
    AbstractStylePreset,
    AbstractFormatPreset,
    AbstractQualityPreset,
    AbstractVoicePreset,
    AbstractWorkflowDefinition,
    AbstractRenderJob,
    AbstractRenderAttempt,
    AbstractAsset,
    AbstractAssetFile,
)

# Import Unified Work Item System
from .work_item import (
    WorkItem,
    WorkItemType,
    WorkItemStatus,
    WorkItemPriority,
    LLMTier,
    Complexity,
    BugDetails,
    FeatureDetails,
    TaskDetails,
    WorkItemLLMAssignment,
    WorkItemComment,
)

# Import Hub Model (DB-driven Hub Management)
from .hub import Hub, HubStatus, HubCategory

# Export all models
__all__ = [
    # Legacy
    "Domain",
    # Normalized (Phase 1)
    "HandlerCategory",
    "URLPattern",
    # Normalized (Phase 2)
    "Handler",
    # Unified Work Item System
    "WorkItem",
    "WorkItemType",
    "WorkItemStatus",
    "WorkItemPriority",
    "LLMTier",
    "Complexity",
    "BugDetails",
    "FeatureDetails",
    "TaskDetails",
    "WorkItemLLMAssignment",
    "WorkItemComment",
    # Hub Management
    "Hub",
    "HubStatus",
    "HubCategory",
    # Media Base Classes (Abstract)
    "AbstractPreset",
    "AbstractStylePreset",
    "AbstractFormatPreset",
    "AbstractQualityPreset",
    "AbstractVoicePreset",
    "AbstractWorkflowDefinition",
    "AbstractRenderJob",
    "AbstractRenderAttempt",
    "AbstractAsset",
    "AbstractAssetFile",
]
