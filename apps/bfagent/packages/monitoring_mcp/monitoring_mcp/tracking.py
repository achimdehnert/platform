"""
Healing Event Tracking System
==============================

Tracks auto-healing events for analytics and monitoring.
"""

import logging
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)


# In-memory storage (will be replaced with database)
HEALING_EVENTS = []


def track_healing_event(
    app: str,
    error_type: str,
    error_message: str,
    action: str,
    success: bool,
    duration_seconds: float = 0.0,
    metadata: Optional[Dict] = None,
) -> None:
    """
    Track an auto-healing event.

    Args:
        app: App label where healing occurred
        error_type: Type of error (e.g., 'ProgrammingError')
        error_message: Error message
        action: Action taken (e.g., 'migrate', 'create_template')
        success: Whether healing was successful
        duration_seconds: Time taken to heal
        metadata: Additional context
    """
    event = {
        "timestamp": datetime.now(),
        "app": app,
        "error_type": error_type,
        "error_message": error_message,
        "action": action,
        "success": success,
        "duration_seconds": duration_seconds,
        "metadata": metadata or {},
    }

    HEALING_EVENTS.append(event)

    # Log event
    status = "✅ SUCCESS" if success else "❌ FAILED"
    logger.info(
        f"Healing Event [{status}]: {app} - {error_type} - {action} ({duration_seconds:.2f}s)"
    )


def get_healing_events(app: Optional[str] = None, limit: int = 100) -> list:
    """
    Get healing events.

    Args:
        app: Filter by app label (optional)
        limit: Maximum number of events to return

    Returns:
        List of healing events
    """
    events = HEALING_EVENTS

    if app:
        events = [e for e in events if e["app"] == app]

    # Return most recent first
    return sorted(events, key=lambda x: x["timestamp"], reverse=True)[:limit]


def get_healing_stats(app: Optional[str] = None) -> Dict:
    """
    Get healing statistics.

    Args:
        app: Filter by app label (optional)

    Returns:
        Dictionary with statistics
    """
    events = HEALING_EVENTS

    if app:
        events = [e for e in events if e["app"] == app]

    if not events:
        return {
            "total": 0,
            "successful": 0,
            "failed": 0,
            "success_rate": 0.0,
            "average_duration": 0.0,
        }

    successful = sum(1 for e in events if e["success"])
    failed = sum(1 for e in events if not e["success"])
    total_duration = sum(e["duration_seconds"] for e in events)

    return {
        "total": len(events),
        "successful": successful,
        "failed": failed,
        "success_rate": (successful / len(events)) * 100 if events else 0.0,
        "average_duration": total_duration / len(events) if events else 0.0,
    }


def clear_healing_events() -> None:
    """Clear all healing events (for testing)."""
    global HEALING_EVENTS
    HEALING_EVENTS = []
