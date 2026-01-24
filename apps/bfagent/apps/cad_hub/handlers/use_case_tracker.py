"""
Use Case Tracker - Erfasst unlösbare Probleme als neue Feature-Anfragen.

Wenn das System eine Anfrage nicht beantworten kann oder ein leeres
Ergebnis liefert, wird dies als potenzieller neuer Use Case erfasst.
"""
import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional
from enum import Enum

logger = logging.getLogger(__name__)

USE_CASE_DATA_PATH = Path(__file__).parent.parent / "data" / "use_cases.json"


class UseCaseStatus(Enum):
    """Status eines Use Cases."""
    NEW = "new"                    # Neu erfasst
    CONFIRMED = "confirmed"        # Von Admin bestätigt
    IN_PROGRESS = "in_progress"    # In Entwicklung
    IMPLEMENTED = "implemented"    # Umgesetzt
    REJECTED = "rejected"          # Abgelehnt
    DUPLICATE = "duplicate"        # Duplikat


class UseCasePriority(Enum):
    """Priorität basierend auf Anfragehäufigkeit."""
    LOW = "low"        # < 3 Anfragen
    MEDIUM = "medium"  # 3-10 Anfragen
    HIGH = "high"      # > 10 Anfragen
    CRITICAL = "critical"  # Manuell gesetzt


@dataclass
class UseCase:
    """Ein erfasster Use Case / Feature Request."""
    id: str
    title: str
    description: str
    example_queries: list = field(default_factory=list)
    intent: str = ""
    status: str = "new"
    priority: str = "low"
    request_count: int = 1
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    tags: list = field(default_factory=list)
    technical_notes: str = ""
    resolution: str = ""
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    def update_priority(self):
        """Aktualisiert Priorität basierend auf Anfragehäufigkeit."""
        if self.request_count >= 10:
            self.priority = UseCasePriority.HIGH.value
        elif self.request_count >= 3:
            self.priority = UseCasePriority.MEDIUM.value
        else:
            self.priority = UseCasePriority.LOW.value


class UseCaseTracker:
    """
    Verwaltet Use Cases / Feature Requests.
    
    Erfasst automatisch:
    - Leere Ergebnisse (z.B. "0 Fenster gefunden")
    - Unbekannte Intents
    - Fehler bei der Verarbeitung
    
    Ermöglicht:
    - Priorisierung nach Häufigkeit
    - Admin-Review
    - Tracking der Implementierung
    """
    
    def __init__(self, data_path: Path = None):
        self.data_path = data_path or USE_CASE_DATA_PATH
        self.use_cases: dict[str, UseCase] = {}
        self._load()
    
    def _load(self):
        """Lädt Use Cases aus JSON."""
        try:
            if self.data_path.exists():
                with open(self.data_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for uc_data in data.get("use_cases", []):
                        uc = UseCase(**uc_data)
                        self.use_cases[uc.id] = uc
                logger.info(f"[UseCaseTracker] Loaded {len(self.use_cases)} use cases")
        except Exception as e:
            logger.warning(f"[UseCaseTracker] Could not load: {e}")
    
    def _save(self):
        """Speichert Use Cases in JSON."""
        try:
            self.data_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.data_path, "w", encoding="utf-8") as f:
                json.dump({
                    "version": "1.0",
                    "updated_at": datetime.now().isoformat(),
                    "use_case_count": len(self.use_cases),
                    "use_cases": [uc.to_dict() for uc in self.use_cases.values()],
                }, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[UseCaseTracker] Could not save: {e}")
    
    def _generate_id(self, title: str) -> str:
        """Generiert ID aus Titel."""
        import re
        slug = re.sub(r'[^\w\s-]', '', title.lower())
        slug = re.sub(r'[-\s]+', '_', slug).strip('_')
        return slug[:50]
    
    def report_empty_result(
        self,
        query: str,
        intent: str,
        result_type: str,
        context: dict = None
    ) -> UseCase:
        """
        Erfasst leeres Ergebnis als potenziellen Use Case.
        
        Args:
            query: Original-Anfrage
            intent: Erkannter Intent
            result_type: Art des Ergebnisses (z.B. "fenster", "türen")
            context: Zusätzlicher Kontext
        
        Returns:
            Erstellter/aktualisierter Use Case
        """
        title = f"{result_type.title()}-Erkennung verbessern"
        uc_id = self._generate_id(f"{result_type}_detection")
        
        if uc_id in self.use_cases:
            uc = self.use_cases[uc_id]
            uc.request_count += 1
            if query not in uc.example_queries:
                uc.example_queries.append(query)
            uc.updated_at = datetime.now().isoformat()
            uc.update_priority()
        else:
            uc = UseCase(
                id=uc_id,
                title=title,
                description=f"Automatisch erfasst: {result_type} werden nicht erkannt oder liefern 0 Ergebnisse.",
                example_queries=[query],
                intent=intent,
                tags=[result_type, "auto_detected", "empty_result"],
            )
            self.use_cases[uc_id] = uc
        
        self._save()
        logger.info(f"[UseCaseTracker] Reported: {uc_id} (count: {uc.request_count})")
        return uc
    
    def report_unknown_intent(self, query: str) -> UseCase:
        """Erfasst unbekannten Intent als Use Case."""
        uc_id = "unknown_intent_patterns"
        
        if uc_id in self.use_cases:
            uc = self.use_cases[uc_id]
            uc.request_count += 1
            if query not in uc.example_queries[-20:]:  # Keep last 20
                uc.example_queries.append(query)
                if len(uc.example_queries) > 50:
                    uc.example_queries = uc.example_queries[-50:]
            uc.updated_at = datetime.now().isoformat()
            uc.update_priority()
        else:
            uc = UseCase(
                id=uc_id,
                title="Neue Sprachmuster erkennen",
                description="Sammlung von Anfragen, die nicht erkannt wurden.",
                example_queries=[query],
                intent="unknown",
                tags=["language", "patterns", "auto_detected"],
            )
            self.use_cases[uc_id] = uc
        
        self._save()
        return uc
    
    def report_feature_request(
        self,
        title: str,
        description: str,
        query: str = "",
        tags: list = None
    ) -> UseCase:
        """
        Erfasst manuellen Feature Request.
        
        Args:
            title: Titel des Features
            description: Beschreibung
            query: Optional - auslösende Anfrage
            tags: Optional - Tags
        
        Returns:
            Erstellter Use Case
        """
        uc_id = self._generate_id(title)
        
        if uc_id in self.use_cases:
            uc = self.use_cases[uc_id]
            uc.request_count += 1
            if query and query not in uc.example_queries:
                uc.example_queries.append(query)
            uc.updated_at = datetime.now().isoformat()
            uc.update_priority()
        else:
            uc = UseCase(
                id=uc_id,
                title=title,
                description=description,
                example_queries=[query] if query else [],
                tags=tags or ["user_request"],
            )
            self.use_cases[uc_id] = uc
        
        self._save()
        logger.info(f"[UseCaseTracker] Feature request: {uc_id}")
        return uc
    
    def get_use_case(self, uc_id: str) -> Optional[UseCase]:
        """Gibt Use Case zurück."""
        return self.use_cases.get(uc_id)
    
    def list_use_cases(
        self,
        status: str = None,
        priority: str = None,
        limit: int = 50
    ) -> list[UseCase]:
        """Listet Use Cases mit Filtern."""
        results = list(self.use_cases.values())
        
        if status:
            results = [uc for uc in results if uc.status == status]
        if priority:
            results = [uc for uc in results if uc.priority == priority]
        
        # Sort by request count (most requested first)
        results.sort(key=lambda x: -x.request_count)
        return results[:limit]
    
    def update_status(self, uc_id: str, status: str, resolution: str = "") -> Optional[UseCase]:
        """Aktualisiert Status eines Use Cases."""
        if uc_id not in self.use_cases:
            return None
        
        uc = self.use_cases[uc_id]
        uc.status = status
        uc.resolution = resolution
        uc.updated_at = datetime.now().isoformat()
        self._save()
        return uc
    
    def get_stats(self) -> dict:
        """Statistiken über Use Cases."""
        status_counts = {}
        priority_counts = {}
        total_requests = 0
        
        for uc in self.use_cases.values():
            status_counts[uc.status] = status_counts.get(uc.status, 0) + 1
            priority_counts[uc.priority] = priority_counts.get(uc.priority, 0) + 1
            total_requests += uc.request_count
        
        return {
            "total_use_cases": len(self.use_cases),
            "total_requests": total_requests,
            "by_status": status_counts,
            "by_priority": priority_counts,
            "top_requested": [
                {"id": uc.id, "title": uc.title, "count": uc.request_count}
                for uc in sorted(self.use_cases.values(), key=lambda x: -x.request_count)[:5]
            ],
        }


# Singleton
_tracker: Optional[UseCaseTracker] = None

def get_use_case_tracker() -> UseCaseTracker:
    """Gibt Singleton UseCaseTracker zurück."""
    global _tracker
    if _tracker is None:
        _tracker = UseCaseTracker()
    return _tracker
