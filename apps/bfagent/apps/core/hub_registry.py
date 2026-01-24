"""
Hub Registry für BF Agent

Zentrale Verwaltung aller Hubs im System.
Ermöglicht dynamische Hub-Aktivierung/-Deaktivierung ohne Code-Änderungen.

WICHTIG: Dynamische Aktivierung nur wenn USE_HUB_REGISTRY Feature Flag aktiv!
Sonst werden alle Hubs wie bisher über INSTALLED_APPS geladen.

Usage:
    from apps.core.hub_registry import hub_registry
    
    # Alle Hubs auflisten
    hubs = hub_registry.get_all_hubs()
    
    # Hub-Info abrufen
    info = hub_registry.get_hub_info("writing_hub")
"""
import importlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional
from enum import Enum

import structlog

from apps.core.feature_flags import is_feature_enabled

logger = structlog.get_logger(__name__)


class HubStatus(str, Enum):
    """Status eines Hubs."""
    PRODUCTION = "production"
    BETA = "beta"
    DEVELOPMENT = "development"
    DEPRECATED = "deprecated"
    DISABLED = "disabled"


class HubCategory(str, Enum):
    """Kategorie eines Hubs."""
    CONTENT = "content"       # Writing, Media
    ENGINEERING = "engineering"  # CAD, Expert
    SYSTEM = "system"         # Control Center, MCP
    RESEARCH = "research"     # Research, DLM
    OTHER = "other"


@dataclass
class HubManifest:
    """Manifest-Informationen eines Hubs.
    
    Wird aus hub_manifest.py im Hub-Verzeichnis geladen
    oder programmatisch erstellt.
    """
    id: str
    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = "BF Agent Team"
    status: HubStatus = HubStatus.PRODUCTION
    category: HubCategory = HubCategory.OTHER
    icon: str = "bi-puzzle"
    dependencies: list[str] = field(default_factory=list)
    entry_point: str = ""
    provides: list[str] = field(default_factory=lambda: ["views", "models"])
    config_schema: dict = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.entry_point:
            self.entry_point = f"apps.{self.id}"


@dataclass
class HubInfo:
    """Laufzeit-Informationen eines Hubs."""
    manifest: HubManifest
    is_active: bool = True
    is_loaded: bool = False
    load_error: Optional[str] = None
    config: dict = field(default_factory=dict)


class HubRegistry:
    """Zentrale Registry für alle Hubs.
    
    Features:
    - Automatische Hub-Erkennung via Manifest
    - Aktivierung/Deaktivierung zur Laufzeit (wenn Feature aktiv)
    - Hub-Konfiguration pro Hub
    - Dependency-Tracking
    """
    
    # Bekannte Hubs mit Default-Manifests (Fallback wenn kein Manifest vorhanden)
    DEFAULT_HUBS = {
        "writing_hub": HubManifest(
            id="writing_hub",
            name="Writing Hub",
            version="2.0.0",
            description="AI-gestützte Bucherstellung",
            status=HubStatus.PRODUCTION,
            category=HubCategory.CONTENT,
            icon="bi-book",
            provides=["views", "models", "handlers"],
        ),
        "cad_hub": HubManifest(
            id="cad_hub",
            name="CAD Hub",
            version="1.5.0",
            description="Bauzeichnungs-Analyse und GAEB Export",
            status=HubStatus.PRODUCTION,
            category=HubCategory.ENGINEERING,
            icon="bi-building",
            provides=["views", "models", "handlers"],
        ),
        "control_center": HubManifest(
            id="control_center",
            name="Control Center",
            version="1.0.0",
            description="System-Administration und Konfiguration",
            status=HubStatus.PRODUCTION,
            category=HubCategory.SYSTEM,
            icon="bi-gear",
            provides=["views", "models"],
        ),
        "expert_hub": HubManifest(
            id="expert_hub",
            name="Expert Hub",
            version="1.0.0",
            description="Explosionsschutz-Dokumentation",
            status=HubStatus.PRODUCTION,
            category=HubCategory.ENGINEERING,
            icon="bi-shield-exclamation",
            provides=["views", "models", "handlers"],
        ),
        "research": HubManifest(
            id="research",
            name="Research Hub",
            version="1.0.0",
            description="Deep Research mit Quellenanalyse",
            status=HubStatus.PRODUCTION,
            category=HubCategory.RESEARCH,
            icon="bi-search",
            provides=["views", "models"],
        ),
        "mcp_hub": HubManifest(
            id="mcp_hub",
            name="MCP Hub",
            version="1.0.0",
            description="MCP-Server Verwaltung",
            status=HubStatus.PRODUCTION,
            category=HubCategory.SYSTEM,
            icon="bi-plug",
            provides=["views", "models"],
        ),
        "media_hub": HubManifest(
            id="media_hub",
            name="Media Hub",
            version="1.0.0",
            description="Medien-Pipeline und Illustration",
            status=HubStatus.PRODUCTION,
            category=HubCategory.CONTENT,
            icon="bi-image",
            provides=["views", "models"],
        ),
        "dlm_hub": HubManifest(
            id="dlm_hub",
            name="DLM Hub",
            version="1.0.0",
            description="Document Lifecycle Management",
            status=HubStatus.BETA,
            category=HubCategory.RESEARCH,
            icon="bi-file-earmark-text",
            provides=["views", "models"],
        ),
    }
    
    def __init__(self):
        self._hubs: dict[str, HubInfo] = {}
        self._initialized = False
    
    def initialize(self) -> None:
        """Initialisiert die Registry mit bekannten Hubs."""
        if self._initialized:
            return
        
        # Default-Hubs laden
        for hub_id, manifest in self.DEFAULT_HUBS.items():
            self._hubs[hub_id] = HubInfo(
                manifest=manifest,
                is_active=True,
                is_loaded=True,
            )
        
        self._initialized = True
        logger.info("hub_registry_initialized", hub_count=len(self._hubs))
    
    def discover_hubs(self, apps_path: Path = None) -> list[str]:
        """Entdeckt Hubs im apps/ Verzeichnis.
        
        Sucht nach hub_manifest.py oder __init__.py mit HUB_MANIFEST.
        """
        if apps_path is None:
            apps_path = Path(__file__).parent.parent  # apps/
        
        discovered = []
        for app_dir in apps_path.iterdir():
            if not app_dir.is_dir():
                continue
            if app_dir.name.startswith(("_", ".")):
                continue
            
            # Prüfe ob es ein Hub ist (hat views.py oder handlers/)
            has_views = (app_dir / "views.py").exists()
            has_handlers = (app_dir / "handlers").is_dir()
            
            if has_views or has_handlers:
                # Versuche Manifest zu laden
                manifest = self._load_manifest(app_dir)
                if manifest:
                    self._hubs[manifest.id] = HubInfo(
                        manifest=manifest,
                        is_active=True,
                        is_loaded=False,
                    )
                    discovered.append(manifest.id)
        
        logger.info("hubs_discovered", count=len(discovered), hubs=discovered)
        return discovered
    
    def _load_manifest(self, app_dir: Path) -> Optional[HubManifest]:
        """Lädt Hub-Manifest aus Verzeichnis."""
        manifest_file = app_dir / "hub_manifest.py"
        
        # Fallback auf Default-Manifest
        hub_id = app_dir.name
        if hub_id in self.DEFAULT_HUBS:
            return self.DEFAULT_HUBS[hub_id]
        
        # Versuche hub_manifest.py zu laden
        if manifest_file.exists():
            try:
                spec = importlib.util.spec_from_file_location(
                    f"{hub_id}.hub_manifest", manifest_file
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                if hasattr(module, "HUB_MANIFEST"):
                    data = module.HUB_MANIFEST
                    return HubManifest(**data)
            except Exception as e:
                logger.warning(
                    "hub_manifest_load_failed",
                    hub_id=hub_id,
                    error=str(e)
                )
        
        return None
    
    def get_hub_info(self, hub_id: str) -> Optional[HubInfo]:
        """Gibt Hub-Informationen zurück."""
        self.initialize()
        return self._hubs.get(hub_id)
    
    def get_all_hubs(self) -> dict[str, HubInfo]:
        """Gibt alle registrierten Hubs zurück."""
        self.initialize()
        return self._hubs.copy()
    
    def get_active_hubs(self) -> list[str]:
        """Gibt IDs aller aktiven Hubs zurück."""
        self.initialize()
        return [k for k, v in self._hubs.items() if v.is_active]
    
    def get_hubs_by_category(self, category: HubCategory) -> list[HubInfo]:
        """Gibt alle Hubs einer Kategorie zurück."""
        self.initialize()
        return [
            v for v in self._hubs.values()
            if v.manifest.category == category
        ]
    
    def get_hubs_by_status(self, status: HubStatus) -> list[HubInfo]:
        """Gibt alle Hubs mit einem Status zurück."""
        self.initialize()
        return [
            v for v in self._hubs.values()
            if v.manifest.status == status
        ]
    
    def is_hub_active(self, hub_id: str) -> bool:
        """Prüft ob ein Hub aktiv ist."""
        info = self.get_hub_info(hub_id)
        return info.is_active if info else False
    
    def activate_hub(self, hub_id: str) -> bool:
        """Aktiviert einen Hub (nur wenn Feature aktiv)."""
        if not is_feature_enabled("USE_HUB_REGISTRY"):
            logger.warning("hub_activation_blocked", reason="feature_disabled")
            return False
        
        info = self.get_hub_info(hub_id)
        if info:
            info.is_active = True
            logger.info("hub_activated", hub_id=hub_id)
            return True
        return False
    
    def deactivate_hub(self, hub_id: str) -> bool:
        """Deaktiviert einen Hub (nur wenn Feature aktiv)."""
        if not is_feature_enabled("USE_HUB_REGISTRY"):
            logger.warning("hub_deactivation_blocked", reason="feature_disabled")
            return False
        
        info = self.get_hub_info(hub_id)
        if info:
            info.is_active = False
            logger.info("hub_deactivated", hub_id=hub_id)
            return True
        return False
    
    def get_hub_config(self, hub_id: str) -> dict:
        """Gibt Hub-Konfiguration zurück."""
        info = self.get_hub_info(hub_id)
        return info.config if info else {}
    
    def set_hub_config(self, hub_id: str, config: dict) -> bool:
        """Setzt Hub-Konfiguration."""
        info = self.get_hub_info(hub_id)
        if info:
            info.config = config
            return True
        return False


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

hub_registry = HubRegistry()
