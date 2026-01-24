"""
Feature Flags für BF Agent

Ermöglicht schrittweise Aktivierung neuer Features ohne Breaking Changes.
Alle Flags sind standardmäßig deaktiviert (False).

Usage:
    from apps.core.feature_flags import is_feature_enabled, FEATURES
    
    if is_feature_enabled("USE_EVENT_BUS"):
        event_bus.publish("chapter.created", ...)
"""
import os
from typing import Optional
import structlog

logger = structlog.get_logger(__name__)

# =============================================================================
# FEATURE FLAGS DEFINITION
# =============================================================================

FEATURES = {
    # Event-Driven Architecture
    "USE_EVENT_BUS": False,           # Event Bus für Handler-Kommunikation
    "EVENT_BUS_ASYNC": False,         # Async Event Processing (Celery)
    
    # Plugin System für Hubs
    "USE_HUB_REGISTRY": False,        # Dynamische Hub-Registrierung
    "HUB_HOT_RELOAD": False,          # Hot-Reload für Hubs (nur Dev)
    
    # AI Features
    "AI_COST_TRACKING": True,         # Token/Cost Tracking (bereits aktiv)
    "AI_FALLBACK_ENABLED": True,      # Fallback zu Mock bei API-Fehler
    
    # UI Features
    "REALTIME_DASHBOARD": False,      # WebSocket Dashboard Updates
}

# =============================================================================
# ENVIRONMENT OVERRIDES
# =============================================================================

def _load_env_overrides():
    """Lade Feature Flag Overrides aus Umgebungsvariablen.
    
    Format: FEATURE_FLAG_<NAME>=true|false
    Beispiel: FEATURE_FLAG_USE_EVENT_BUS=true
    """
    for key in FEATURES.keys():
        env_key = f"FEATURE_FLAG_{key}"
        env_value = os.environ.get(env_key)
        if env_value is not None:
            FEATURES[key] = env_value.lower() in ("true", "1", "yes", "on")
            logger.info(
                "feature_flag_override",
                flag=key,
                value=FEATURES[key],
                source="environment"
            )

# Load overrides on module import
_load_env_overrides()

# =============================================================================
# PUBLIC API
# =============================================================================

def is_feature_enabled(flag_name: str, default: bool = False) -> bool:
    """Prüft ob ein Feature Flag aktiviert ist.
    
    Args:
        flag_name: Name des Feature Flags
        default: Fallback-Wert wenn Flag nicht existiert
        
    Returns:
        True wenn Feature aktiviert, sonst False
        
    Example:
        if is_feature_enabled("USE_EVENT_BUS"):
            event_bus.publish("chapter.created", data)
    """
    return FEATURES.get(flag_name, default)


def enable_feature(flag_name: str) -> None:
    """Aktiviert ein Feature Flag zur Laufzeit.
    
    ACHTUNG: Nur für Tests und Debugging verwenden!
    """
    if flag_name in FEATURES:
        FEATURES[flag_name] = True
        logger.info("feature_flag_enabled", flag=flag_name)
    else:
        logger.warning("feature_flag_unknown", flag=flag_name)


def disable_feature(flag_name: str) -> None:
    """Deaktiviert ein Feature Flag zur Laufzeit.
    
    Nützlich für Rollback bei Problemen.
    """
    if flag_name in FEATURES:
        FEATURES[flag_name] = False
        logger.info("feature_flag_disabled", flag=flag_name)


def get_all_flags() -> dict:
    """Gibt alle Feature Flags mit aktuellem Status zurück."""
    return FEATURES.copy()


def get_enabled_flags() -> list[str]:
    """Gibt Liste aller aktivierten Feature Flags zurück."""
    return [k for k, v in FEATURES.items() if v]
