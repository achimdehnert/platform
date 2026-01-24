"""
Event Bus für BF Agent

Zentrale Event-Vermittlung zwischen Komponenten.
Basiert auf Django Signals, kann später auf Redis/RabbitMQ erweitert werden.

WICHTIG: Events werden NUR ausgelöst wenn USE_EVENT_BUS Feature Flag aktiv ist!

Usage:
    from apps.core.event_bus import event_bus
    from apps.core.events import Events
    
    # Event publizieren (nur wenn Feature aktiv)
    event_bus.publish(Events.CHAPTER_CREATED, chapter_id=123, project_id=1)
    
    # Handler registrieren
    @event_bus.subscribe(Events.CHAPTER_CREATED)
    def on_chapter_created(chapter_id, project_id, **kwargs):
        print(f"Chapter {chapter_id} created in project {project_id}")
"""
import uuid
from datetime import datetime
from typing import Any, Callable, Optional, Union
from functools import wraps

from django.dispatch import Signal
import structlog

from apps.core.feature_flags import is_feature_enabled
from apps.core.events import Events, Event

logger = structlog.get_logger(__name__)


class EventBus:
    """Zentraler Event Bus für das gesamte System.
    
    Features:
    - Feature Flag gesteuert (deaktiviert = keine Events)
    - Django Signals als Backend (erweiterbar auf Redis)
    - Event Logging für Debugging
    - Type-safe Event Definitionen
    """
    
    def __init__(self):
        self._signals: dict[str, Signal] = {}
        self._handlers: dict[str, list[Callable]] = {}
        self._event_log: list[Event] = []
        self._max_log_size = 1000  # Letzte 1000 Events behalten
    
    def _get_or_create_signal(self, event_type: Union[Events, str]) -> Signal:
        """Holt oder erstellt ein Django Signal für einen Event-Typ."""
        key = event_type.value if isinstance(event_type, Events) else event_type
        if key not in self._signals:
            self._signals[key] = Signal()
        return self._signals[key]
    
    def publish(
        self,
        event_type: Union[Events, str],
        source: Optional[str] = None,
        correlation_id: Optional[str] = None,
        **payload
    ) -> bool:
        """Publiziert ein Event an alle Subscriber.
        
        Args:
            event_type: Art des Events (aus Events Enum)
            source: Quelle des Events (z.B. "ChapterHandler")
            correlation_id: ID zum Verknüpfen zusammengehöriger Events
            **payload: Event-Daten
            
        Returns:
            True wenn Event publiziert wurde, False wenn Feature deaktiviert
            
        Example:
            event_bus.publish(
                Events.CHAPTER_CREATED,
                source="ChapterHandler",
                chapter_id=123,
                project_id=1
            )
        """
        # Feature Flag Check - wenn deaktiviert, nichts tun
        if not is_feature_enabled("USE_EVENT_BUS"):
            return False
        
        # Event-Objekt erstellen
        event = Event(
            event_type=event_type if isinstance(event_type, Events) else Events(event_type),
            payload=payload,
            timestamp=datetime.now(),
            source=source,
            correlation_id=correlation_id or str(uuid.uuid4())[:8],
        )
        
        # Event loggen
        self._log_event(event)
        
        # Signal senden
        signal = self._get_or_create_signal(event_type)
        try:
            signal.send(
                sender=self.__class__,
                event=event,
                **payload
            )
            logger.debug(
                "event_published",
                event_type=event.event_type.value,
                source=source,
                correlation_id=event.correlation_id,
            )
            return True
        except Exception as e:
            logger.error(
                "event_publish_failed",
                event_type=event.event_type.value,
                error=str(e),
            )
            return False
    
    def subscribe(
        self,
        event_type: Union[Events, str]
    ) -> Callable:
        """Decorator zum Registrieren eines Event Handlers.
        
        Args:
            event_type: Art des Events zum Abonnieren
            
        Example:
            @event_bus.subscribe(Events.CHAPTER_CREATED)
            def on_chapter_created(chapter_id, **kwargs):
                print(f"Chapter {chapter_id} created")
        """
        def decorator(func: Callable) -> Callable:
            signal = self._get_or_create_signal(event_type)
            
            @wraps(func)
            def wrapper(sender, event: Event = None, **kwargs):
                try:
                    return func(**kwargs)
                except Exception as e:
                    logger.error(
                        "event_handler_failed",
                        event_type=event_type.value if isinstance(event_type, Events) else event_type,
                        handler=func.__name__,
                        error=str(e),
                    )
                    raise
            
            signal.connect(wrapper)
            
            # Handler registrieren für Debugging
            key = event_type.value if isinstance(event_type, Events) else event_type
            if key not in self._handlers:
                self._handlers[key] = []
            self._handlers[key].append(func.__name__)
            
            logger.debug(
                "event_handler_registered",
                event_type=key,
                handler=func.__name__,
            )
            
            return func
        return decorator
    
    def _log_event(self, event: Event) -> None:
        """Speichert Event im internen Log (für Debugging)."""
        self._event_log.append(event)
        # Log-Größe begrenzen
        if len(self._event_log) > self._max_log_size:
            self._event_log = self._event_log[-self._max_log_size:]
    
    def get_recent_events(self, limit: int = 50) -> list[dict]:
        """Gibt die letzten Events zurück (für Debugging/Monitoring)."""
        return [e.to_dict() for e in self._event_log[-limit:]]
    
    def get_handlers(self, event_type: Optional[Union[Events, str]] = None) -> dict:
        """Gibt registrierte Handler zurück."""
        if event_type:
            key = event_type.value if isinstance(event_type, Events) else event_type
            return {key: self._handlers.get(key, [])}
        return self._handlers.copy()
    
    def clear_log(self) -> None:
        """Löscht das Event Log."""
        self._event_log = []


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

event_bus = EventBus()


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def publish_event(event_type: Union[Events, str], **payload) -> bool:
    """Shortcut zum Publizieren eines Events."""
    return event_bus.publish(event_type, **payload)


def subscribe_to(event_type: Union[Events, str]) -> Callable:
    """Shortcut Decorator zum Abonnieren eines Events."""
    return event_bus.subscribe(event_type)
