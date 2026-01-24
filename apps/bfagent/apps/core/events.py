"""
Event Definitions für BF Agent

Definiert alle verfügbaren Events im System.
Events werden nur ausgelöst wenn USE_EVENT_BUS Feature Flag aktiv ist.

Usage:
    from apps.core.events import Events
    from apps.core.event_bus import event_bus
    
    # Event publizieren
    event_bus.publish(Events.CHAPTER_CREATED, chapter_id=123)
    
    # Event abonnieren
    @event_bus.subscribe(Events.CHAPTER_CREATED)
    def on_chapter_created(chapter_id, **kwargs):
        print(f"Chapter {chapter_id} wurde erstellt")
"""
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional
from datetime import datetime


class Events(str, Enum):
    """Alle verfügbaren Events im System.
    
    Naming Convention: ENTITY_ACTION
    """
    
    # ==========================================================================
    # CONTENT EVENTS
    # ==========================================================================
    
    # Chapter Events
    CHAPTER_CREATED = "chapter.created"
    CHAPTER_UPDATED = "chapter.updated"
    CHAPTER_DELETED = "chapter.deleted"
    CHAPTER_STATUS_CHANGED = "chapter.status_changed"
    
    # Character Events
    CHARACTER_CREATED = "character.created"
    CHARACTER_UPDATED = "character.updated"
    
    # Project Events
    PROJECT_CREATED = "project.created"
    PROJECT_COMPLETED = "project.completed"
    
    # ==========================================================================
    # AI/LLM EVENTS
    # ==========================================================================
    
    CONTENT_GENERATED = "content.generated"
    CONTENT_GENERATION_FAILED = "content.generation_failed"
    LLM_REQUEST_COMPLETED = "llm.request_completed"
    LLM_TOKENS_USED = "llm.tokens_used"
    
    # ==========================================================================
    # HANDLER EVENTS
    # ==========================================================================
    
    HANDLER_STARTED = "handler.started"
    HANDLER_COMPLETED = "handler.completed"
    HANDLER_FAILED = "handler.failed"
    
    # ==========================================================================
    # WORKFLOW EVENTS
    # ==========================================================================
    
    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_STEP_COMPLETED = "workflow.step_completed"
    WORKFLOW_COMPLETED = "workflow.completed"
    WORKFLOW_FAILED = "workflow.failed"
    
    # ==========================================================================
    # HUB EVENTS
    # ==========================================================================
    
    HUB_ACTIVATED = "hub.activated"
    HUB_DEACTIVATED = "hub.deactivated"
    HUB_ERROR = "hub.error"
    
    # ==========================================================================
    # SYSTEM EVENTS
    # ==========================================================================
    
    USER_ACTION = "user.action"
    SYSTEM_ERROR = "system.error"
    SYSTEM_WARNING = "system.warning"


@dataclass
class Event:
    """Event-Objekt mit Metadaten.
    
    Wird intern vom Event Bus verwendet.
    """
    event_type: Events
    payload: dict[str, Any]
    timestamp: datetime
    source: Optional[str] = None
    correlation_id: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type.value,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "correlation_id": self.correlation_id,
        }


# =============================================================================
# EVENT PAYLOAD SCHEMAS (für Dokumentation/Validation)
# =============================================================================

EVENT_SCHEMAS = {
    Events.CHAPTER_CREATED: {
        "required": ["chapter_id", "project_id"],
        "optional": ["user_id", "title"],
    },
    Events.CHAPTER_UPDATED: {
        "required": ["chapter_id"],
        "optional": ["changes", "user_id"],
    },
    Events.CONTENT_GENERATED: {
        "required": ["content_type", "content_id"],
        "optional": ["handler", "tokens_used", "duration_ms"],
    },
    Events.HANDLER_COMPLETED: {
        "required": ["handler_name", "duration_ms"],
        "optional": ["result_summary"],
    },
}
