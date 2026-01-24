"""
Intent Classifier
=================

Erkennt User-Intent aus natürlicher Sprache.
"""

import re
from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional


class Intent(Enum):
    """Erkannte Intents"""
    # Domain & Handler
    LIST_DOMAINS = "list_domains"
    SCAFFOLD_DOMAIN = "scaffold_domain"
    SEARCH_HANDLERS = "search_handlers"
    GENERATE_HANDLER = "generate_handler"
    VALIDATE_CODE = "validate_code"
    
    # Knowledge
    BEST_PRACTICES = "best_practices"
    EXPLAIN = "explain"
    
    # CAD
    CAD_LIST_ROOMS = "cad_list_rooms"
    CAD_GET_DIMENSIONS = "cad_get_dimensions"
    CAD_CALCULATE_VOLUME = "cad_calculate_volume"
    CAD_QUERY = "cad_query"
    CAD_EXPORT = "cad_export"
    
    # System
    HELP = "help"
    UNKNOWN = "unknown"


@dataclass
class IntentResult:
    """Ergebnis der Intent-Erkennung"""
    intent: Intent
    confidence: float
    entities: Dict[str, str]
    missing_required: List[str]


# Intent Patterns
INTENT_PATTERNS: Dict[Intent, List[str]] = {
    
    # Domain & Handler
    Intent.LIST_DOMAINS: [
        r"(zeig|list|welche).*(domain|bereiche)",
        r"alle domains",
    ],
    Intent.SCAFFOLD_DOMAIN: [
        r"(erstell|generier|neu).*(domain)",
        r"domain.*(anlegen|erstellen)",
    ],
    Intent.SEARCH_HANDLERS: [
        r"(find|such|zeig).*(handler)",
        r"welche handler",
    ],
    Intent.GENERATE_HANDLER: [
        r"(erstell|generier|bau|mach).*(handler|parser|extractor)",
        r"handler.*(erstellen|generieren)",
        r"(ifc|dxf|pdf|cad).*(parser|handler|extractor)",
    ],
    Intent.VALIDATE_CODE: [
        r"(validier|prüf|check).*(code|handler)",
        r"code.*review",
    ],
    
    # Knowledge
    Intent.BEST_PRACTICES: [
        r"best.?practice",
        r"wie.*(soll|muss|kann).*ich",
        r"(empfehlung|tipps?)",
    ],
    
    # CAD
    Intent.CAD_LIST_ROOMS: [
        r"(list|zeig|welche).*(räume|rooms|space)",
        r"alle räume",
    ],
    Intent.CAD_GET_DIMENSIONS: [
        r"(maße|größe|dimension|fläche).*(raum|zimmer|room)",
        r"wie (groß|hoch|breit)",
    ],
    Intent.CAD_CALCULATE_VOLUME: [
        r"(umbauter? raum|volumen|kubatur)",
        r"gesamt.*(volumen|fläche)",
        r"bri|brutto.?raum",
    ],
    Intent.CAD_QUERY: [
        r"(räume|rooms).*(größer|kleiner|über|unter)",
        r"welche.*(räume|rooms).*(haben|sind)",
    ],
    Intent.CAD_EXPORT: [
        r"export.*(excel|pdf|csv)",
        r"(speicher|download).*(liste|tabelle)",
    ],
    
    # System
    Intent.HELP: [
        r"^hilfe$",
        r"^help$",
        r"was kannst du",
    ],
}

# Entity Patterns
ENTITY_PATTERNS: Dict[str, List[Tuple[str, str]]] = {
    "file_format": [
        (r"\bifc\b", "ifc"),
        (r"\bdxf\b", "dxf"),
        (r"\bdwg\b", "dwg"),
        (r"\bpdf\b", "pdf"),
    ],
    "entity_type": [
        (r"\b(raum|räume|room|space)\b", "IfcSpace"),
        (r"\b(wand|wände|wall)\b", "IfcWall"),
        (r"\b(tür|türen|door)\b", "IfcDoor"),
    ],
    "output_format": [
        (r"\bjson\b", "json"),
        (r"\bexcel\b", "excel"),
        (r"\bpdf\b", "pdf"),
    ],
    "domain": [
        (r"\bcad\b", "cad_analysis"),
        (r"\bbuch|book\b", "book_writing"),
        (r"\bmedical|medizin\b", "medical_translation"),
    ],
}

# Required fields per intent
REQUIRED_FIELDS: Dict[Intent, List[str]] = {
    Intent.GENERATE_HANDLER: ["domain"],
    Intent.SCAFFOLD_DOMAIN: ["domain_id"],
    Intent.VALIDATE_CODE: ["code"],
    Intent.CAD_LIST_ROOMS: ["file_path"],
    Intent.CAD_GET_DIMENSIONS: ["file_path", "room_name"],
    Intent.CAD_CALCULATE_VOLUME: ["file_path"],
}


class IntentClassifier:
    """Klassifiziert User-Input"""
    
    def classify(self, text: str) -> IntentResult:
        """Klassifiziert Text und extrahiert Entities"""
        text_lower = text.lower()
        
        # Intent erkennen
        intent, confidence = self._detect_intent(text_lower)
        
        # Entities extrahieren
        entities = self._extract_entities(text_lower)
        
        # Fehlende Felder
        required = REQUIRED_FIELDS.get(intent, [])
        missing = [f for f in required if f not in entities]
        
        return IntentResult(
            intent=intent,
            confidence=confidence,
            entities=entities,
            missing_required=missing,
        )
    
    def _detect_intent(self, text: str) -> Tuple[Intent, float]:
        """Erkennt Intent via Pattern Matching"""
        best_intent = Intent.UNKNOWN
        best_score = 0.0
        
        for intent, patterns in INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    score = min(0.6 + len(pattern) * 0.01, 0.95)
                    if score > best_score:
                        best_score = score
                        best_intent = intent
        
        return best_intent, best_score
    
    def _extract_entities(self, text: str) -> Dict[str, str]:
        """Extrahiert Entities aus Text"""
        entities = {}
        
        for entity_type, patterns in ENTITY_PATTERNS.items():
            for pattern, value in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    entities[entity_type] = value
                    break
        
        # File path
        file_match = re.search(r'[\w./\\-]+\.(ifc|dxf|dwg)', text, re.IGNORECASE)
        if file_match:
            entities["file_path"] = file_match.group()
        
        # Room name
        room_match = re.search(r"(?:raum|room|zimmer)\s+['\"]?(\w+)['\"]?", text, re.IGNORECASE)
        if room_match:
            entities["room_name"] = room_match.group(1)
        
        return entities
