"""
Context Enricher
================

Reichert unvollständige Parameter mit intelligenten Defaults an.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

from .intent import Intent


@dataclass
class EnrichmentResult:
    """Ergebnis der Anreicherung"""
    params: Dict[str, Any]
    confidence: float
    assumptions: List[str] = field(default_factory=list)


# Domain-spezifische Defaults
DOMAIN_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "cad_analysis": {
        "file_format": "ifc",
        "entity_type": "IfcSpace",
        "output_format": "json",
        "handler_type": "parser",
        "library": "ifcopenshell",
    },
    "book_writing": {
        "output_format": "markdown",
        "handler_type": "generator",
    },
    "exschutz_forensics": {
        "file_format": "pdf",
        "output_format": "json",
        "handler_type": "analyzer",
    },
}

# Statistische Defaults (häufigste Werte)
STATISTICAL_DEFAULTS: Dict[str, Any] = {
    "handler_type": "parser",
    "output_format": "json",
    "include_tests": True,
    "version": "1.0.0",
}


class ContextEnricher:
    """Reichert Kontext mit Defaults an"""
    
    def __init__(self):
        self.conversation_context: Dict[str, Any] = {}
    
    def enrich(
        self,
        intent: Intent,
        entities: Dict[str, str],
    ) -> EnrichmentResult:
        """
        Reichert Entities mit Kontext an.
        
        Priorität:
        1. Explizit vom User
        2. Conversation Context
        3. Domain Defaults
        4. Statistical Defaults
        """
        enriched = dict(entities)
        assumptions = []
        
        domain = entities.get("domain")
        
        # 1. Conversation Context
        for key, value in self.conversation_context.items():
            if key not in enriched:
                enriched[key] = value
                assumptions.append(f"'{key}' aus letzter Anfrage")
        
        # 2. Domain Defaults
        if domain and domain in DOMAIN_DEFAULTS:
            for key, value in DOMAIN_DEFAULTS[domain].items():
                if key not in enriched:
                    enriched[key] = value
                    assumptions.append(f"'{key}={value}' (Domain-Standard)")
        
        # 3. Statistical Defaults
        for key, value in STATISTICAL_DEFAULTS.items():
            if key not in enriched:
                enriched[key] = value
        
        # Confidence basierend auf wie viel enriched wurde
        original = len(entities)
        total = len(enriched)
        confidence = original / total if total > 0 else 0.0
        
        return EnrichmentResult(
            params=enriched,
            confidence=round(confidence, 2),
            assumptions=assumptions,
        )
    
    def update_context(self, params: Dict[str, Any]) -> None:
        """Aktualisiert Conversation Context"""
        # Wichtige Felder merken
        for key in ["file_path", "domain", "handler_type"]:
            if key in params:
                self.conversation_context[key] = params[key]
    
    def clear_context(self) -> None:
        """Löscht Context"""
        self.conversation_context.clear()
