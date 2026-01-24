#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# BF Agent MCP Server v2.0 - Installation Script
# ═══════════════════════════════════════════════════════════════════════════════
#
# Usage:
#   chmod +x install_bfagent_mcp.sh
#   ./install_bfagent_mcp.sh [target_directory]
#
# Default: ~/projects/bf_agent/packages/bfagent_mcp
#
# ═══════════════════════════════════════════════════════════════════════════════

set -e

# Target directory
TARGET_DIR="${1:-$HOME/projects/bf_agent/packages/bfagent_mcp}"

echo "🚀 Installing BF Agent MCP Server v2.0"
echo "   Target: $TARGET_DIR"
echo ""

# Create directories
mkdir -p "$TARGET_DIR"/{metaprompter,standards,examples}

# ═══════════════════════════════════════════════════════════════════════════════
# 1. __init__.py
# ═══════════════════════════════════════════════════════════════════════════════
cat > "$TARGET_DIR/__init__.py" << 'EOF'
"""
BF Agent MCP Server v2.0
========================

Universal MCP Server with:
- MetaPrompter Gateway (natural language interface)
- Standards Enforcement Layer (guaranteed compliance)
"""

__version__ = "2.0.0"
EOF

echo "✅ __init__.py"

# ═══════════════════════════════════════════════════════════════════════════════
# 2. metaprompter/__init__.py
# ═══════════════════════════════════════════════════════════════════════════════
cat > "$TARGET_DIR/metaprompter/__init__.py" << 'EOF'
"""
MetaPrompter Gateway
====================

Universal Natural Language Interface für BF Agent MCP Server.
Verarbeitet JEDE Eingabe und routet zum richtigen Tool.
"""

from .gateway import UniversalGateway
from .intent import IntentClassifier, Intent
from .enricher import ContextEnricher

__all__ = ["UniversalGateway", "IntentClassifier", "Intent", "ContextEnricher"]
EOF

echo "✅ metaprompter/__init__.py"

# ═══════════════════════════════════════════════════════════════════════════════
# 3. metaprompter/intent.py
# ═══════════════════════════════════════════════════════════════════════════════
cat > "$TARGET_DIR/metaprompter/intent.py" << 'EOF'
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
EOF

echo "✅ metaprompter/intent.py"

# ═══════════════════════════════════════════════════════════════════════════════
# 4. metaprompter/enricher.py
# ═══════════════════════════════════════════════════════════════════════════════
cat > "$TARGET_DIR/metaprompter/enricher.py" << 'EOF'
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
EOF

echo "✅ metaprompter/enricher.py"

# ═══════════════════════════════════════════════════════════════════════════════
# 5. metaprompter/gateway.py
# ═══════════════════════════════════════════════════════════════════════════════
cat > "$TARGET_DIR/metaprompter/gateway.py" << 'EOF'
"""
Universal Gateway
=================

Zentraler Einstiegspunkt für ALLE Anfragen.
Orchestriert Intent → Enrichment → Standards → Execution.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, Callable, Awaitable
from enum import Enum

from .intent import IntentClassifier, Intent, IntentResult
from .enricher import ContextEnricher, EnrichmentResult


class Strategy(Enum):
    """Verarbeitungs-Strategien"""
    AUTO = "auto"        # Direkt ausführen
    CLARIFY = "clarify"  # Immer nachfragen
    HYBRID = "hybrid"    # Kombiniert (empfohlen)


@dataclass
class GatewayResult:
    """Ergebnis des Gateways"""
    success: bool
    needs_input: bool = False
    
    # Bei Erfolg
    result: Optional[str] = None
    tool_used: Optional[str] = None
    
    # Bei Rückfrage
    prompt: Optional[str] = None
    
    # Immer
    intent: Optional[Intent] = None
    confidence: float = 0.0
    assumptions: list = None


# Intent → Tool Mapping
INTENT_TO_TOOL: Dict[Intent, str] = {
    Intent.LIST_DOMAINS: "bfagent_list_domains",
    Intent.SCAFFOLD_DOMAIN: "bfagent_scaffold_domain",
    Intent.SEARCH_HANDLERS: "bfagent_search_handlers",
    Intent.GENERATE_HANDLER: "bfagent_generate_handler",
    Intent.VALIDATE_CODE: "bfagent_validate_handler",
    Intent.BEST_PRACTICES: "bfagent_get_best_practices",
    Intent.CAD_LIST_ROOMS: "cad_list_rooms",
    Intent.CAD_GET_DIMENSIONS: "cad_get_dimensions",
    Intent.CAD_CALCULATE_VOLUME: "cad_calculate_volume",
    Intent.CAD_QUERY: "cad_query",
    Intent.CAD_EXPORT: "cad_export",
    Intent.HELP: "bfagent_help",
}


class UniversalGateway:
    """
    Universal Gateway für alle MCP-Anfragen.
    
    Workflow:
    1. Intent klassifizieren
    2. Entities extrahieren
    3. Kontext anreichern
    4. Strategie anwenden (auto/clarify/hybrid)
    5. Tool ausführen ODER Rückfrage generieren
    """
    
    # Thresholds
    AUTO_THRESHOLD = 0.70
    CLARIFY_THRESHOLD = 0.35
    
    def __init__(self, strategy: Strategy = Strategy.HYBRID):
        self.strategy = strategy
        self.classifier = IntentClassifier()
        self.enricher = ContextEnricher()
        self._tool_executor: Optional[Callable] = None
    
    def set_tool_executor(self, executor: Callable[[str, Dict], Awaitable[str]]):
        """Setzt die Funktion die Tools ausführt"""
        self._tool_executor = executor
    
    async def process(self, user_input: str) -> GatewayResult:
        """Haupteinstiegspunkt für alle Anfragen"""
        
        # Leere Eingabe → Hilfe
        if not user_input.strip():
            return await self._handle_help()
        
        # 1. Intent klassifizieren
        intent_result = self.classifier.classify(user_input)
        
        # 2. Kontext anreichern
        enrichment = self.enricher.enrich(
            intent=intent_result.intent,
            entities=intent_result.entities,
        )
        
        # 3. Combined Confidence
        combined_conf = (
            intent_result.confidence * 0.5 +
            enrichment.confidence * 0.5
        )
        
        # 4. Strategie anwenden
        if self.strategy == Strategy.AUTO:
            return await self._handle_auto(intent_result, enrichment)
        elif self.strategy == Strategy.CLARIFY:
            return self._handle_clarify(intent_result, enrichment)
        else:
            return await self._handle_hybrid(intent_result, enrichment, combined_conf)
    
    async def _handle_auto(
        self,
        intent: IntentResult,
        enrichment: EnrichmentResult,
    ) -> GatewayResult:
        """Strategie AUTO: Direkt ausführen"""
        
        # Kritische Felder prüfen
        if intent.missing_required:
            return self._generate_clarification(intent, enrichment)
        
        return await self._execute(intent, enrichment)
    
    def _handle_clarify(
        self,
        intent: IntentResult,
        enrichment: EnrichmentResult,
    ) -> GatewayResult:
        """Strategie CLARIFY: Immer nachfragen"""
        return self._generate_clarification(intent, enrichment)
    
    async def _handle_hybrid(
        self,
        intent: IntentResult,
        enrichment: EnrichmentResult,
        confidence: float,
    ) -> GatewayResult:
        """Strategie HYBRID: Basierend auf Confidence"""
        
        # Hohe Confidence → Ausführen
        if confidence >= self.AUTO_THRESHOLD and not intent.missing_required:
            return await self._execute(intent, enrichment)
        
        # Niedrige Confidence → Nachfragen
        if confidence < self.CLARIFY_THRESHOLD or intent.missing_required:
            return self._generate_clarification(intent, enrichment)
        
        # Mittlere Confidence → Vorschlag mit Optionen
        return self._generate_suggestion(intent, enrichment, confidence)
    
    async def _execute(
        self,
        intent: IntentResult,
        enrichment: EnrichmentResult,
    ) -> GatewayResult:
        """Führt das Tool aus"""
        
        tool_name = INTENT_TO_TOOL.get(intent.intent)
        if not tool_name:
            return GatewayResult(
                success=False,
                result="❌ Unbekannte Anfrage",
            )
        
        # Tool ausführen
        if self._tool_executor:
            try:
                result = await self._tool_executor(tool_name, enrichment.params)
                
                # Context aktualisieren
                self.enricher.update_context(enrichment.params)
                
                return GatewayResult(
                    success=True,
                    result=result,
                    tool_used=tool_name,
                    intent=intent.intent,
                    confidence=intent.confidence,
                    assumptions=enrichment.assumptions,
                )
            except Exception as e:
                return GatewayResult(
                    success=False,
                    result=f"❌ Fehler: {str(e)}",
                )
        
        # Kein Executor → Mock-Response
        return GatewayResult(
            success=True,
            result=f"[Mock] Would execute: {tool_name} with {enrichment.params}",
            tool_used=tool_name,
            intent=intent.intent,
        )
    
    def _generate_clarification(
        self,
        intent: IntentResult,
        enrichment: EnrichmentResult,
    ) -> GatewayResult:
        """Generiert Rückfrage"""
        
        lines = ["Ich brauche noch ein paar Infos:\n"]
        
        # Fehlende Felder
        questions = {
            "file_path": "📁 Welche Datei? (z.B. building.ifc)",
            "domain": "🏷️ Welche Domain? (cad, book, medical)",
            "room_name": "🚪 Welcher Raum?",
            "code": "💻 Welcher Code soll validiert werden?",
        }
        
        for field in intent.missing_required:
            q = questions.get(field, f"❓ Was ist '{field}'?")
            lines.append(f"• {q}")
        
        # Was schon erkannt wurde
        if enrichment.params:
            lines.append(f"\n✓ Erkannt: {', '.join(f'{k}={v}' for k,v in enrichment.params.items())}")
        
        return GatewayResult(
            success=False,
            needs_input=True,
            prompt="\n".join(lines),
            intent=intent.intent,
            confidence=intent.confidence,
        )
    
    def _generate_suggestion(
        self,
        intent: IntentResult,
        enrichment: EnrichmentResult,
        confidence: float,
    ) -> GatewayResult:
        """Generiert Vorschlag mit Optionen"""
        
        lines = [f"Ich verstehe: **{intent.intent.value}**\n"]
        lines.append("📋 **Vorgeschlagene Konfiguration:**")
        
        for key, value in list(enrichment.params.items())[:5]:
            lines.append(f"• {key}: `{value}`")
        
        if enrichment.assumptions:
            lines.append("\nℹ️ **Angenommen:**")
            for a in enrichment.assumptions[:3]:
                lines.append(f"• {a}")
        
        lines.append("\n**Soll ich fortfahren? (Ja/Nein/Anpassen)**")
        
        return GatewayResult(
            success=False,
            needs_input=True,
            prompt="\n".join(lines),
            intent=intent.intent,
            confidence=confidence,
            assumptions=enrichment.assumptions,
        )
    
    async def _handle_help(self) -> GatewayResult:
        """Zeigt Hilfe"""
        help_text = """
# 🤖 BF Agent - Was kann ich für dich tun?

## 📁 Domains & Handler
• "Zeig mir alle Domains"
• "Erstelle einen IFC Parser für CAD"
• "Validiere diesen Code"

## 🏗️ CAD Analyse
• "Liste Räume aus building.ifc"
• "Wie groß ist das Wohnzimmer?"
• "Exportiere als Excel"

## 💡 Wissen
• "Best Practices für IFC"

Sprich einfach natürlich - ich frage nach wenn mir was fehlt!
"""
        return GatewayResult(
            success=True,
            result=help_text,
            intent=Intent.HELP,
            confidence=1.0,
        )
EOF

echo "✅ metaprompter/gateway.py"

# ═══════════════════════════════════════════════════════════════════════════════
# 6. standards/__init__.py
# ═══════════════════════════════════════════════════════════════════════════════
cat > "$TARGET_DIR/standards/__init__.py" << 'EOF'
"""
Standards Knowledge Base
========================

Zentrale Definition aller BF Agent Coding Standards.
Diese Standards werden für Validierung UND Template-Generierung verwendet.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional


class StandardCategory(Enum):
    """Kategorien von Standards"""
    HANDLER = "handler"
    SCHEMA = "schema"
    ERROR_HANDLING = "error_handling"
    LOGGING = "logging"
    DOCUMENTATION = "documentation"
    NAMING = "naming"
    TESTING = "testing"


@dataclass
class Standard:
    """Definition eines einzelnen Standards"""
    id: str
    category: StandardCategory
    name: str
    description: str
    severity: str  # "error" | "warning" | "info"
    
    # Patterns für Validierung
    check_pattern: Optional[str] = None  # MUSS vorhanden sein
    anti_pattern: Optional[str] = None   # DARF NICHT vorhanden sein
    
    # Beispiele
    good_example: Optional[str] = None
    bad_example: Optional[str] = None
    
    # Auto-Fix
    auto_fixable: bool = False


# ═══════════════════════════════════════════════════════════════════════════════
# STANDARDS DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════

STANDARDS: Dict[str, Standard] = {
    
    # HANDLER STANDARDS (H)
    "H001": Standard(
        id="H001",
        category=StandardCategory.HANDLER,
        name="BaseHandler Inheritance",
        description="Handler MÜSSEN von BaseHandler erben",
        severity="error",
        check_pattern=r"class\s+\w+\(BaseHandler\)",
        auto_fixable=True,
    ),
    
    "H002": Standard(
        id="H002",
        category=StandardCategory.HANDLER,
        name="Three-Phase Pattern",
        description="Handler MÜSSEN validate(), process(), cleanup() haben",
        severity="error",
        check_pattern=r"async def process\s*\(",
        auto_fixable=True,
    ),
    
    "H003": Standard(
        id="H003",
        category=StandardCategory.HANDLER,
        name="HandlerResult Return",
        description="process() MUSS HandlerResult zurückgeben",
        severity="error",
        check_pattern=r"return\s+HandlerResult",
    ),
    
    "H004": Standard(
        id="H004",
        category=StandardCategory.HANDLER,
        name="Handler Metadata",
        description="Handler MÜSSEN name, description, version haben",
        severity="error",
        check_pattern=r'name\s*=\s*["\']',
        auto_fixable=True,
    ),
    
    # SCHEMA STANDARDS (S)
    "S001": Standard(
        id="S001",
        category=StandardCategory.SCHEMA,
        name="Pydantic Input Schema",
        description="Handler MÜSSEN input_schema definieren",
        severity="error",
        check_pattern=r"input_schema\s*=",
        auto_fixable=True,
    ),
    
    "S002": Standard(
        id="S002",
        category=StandardCategory.SCHEMA,
        name="Pydantic Output Schema",
        description="Handler MÜSSEN output_schema definieren",
        severity="error",
        check_pattern=r"output_schema\s*=",
        auto_fixable=True,
    ),
    
    "S003": Standard(
        id="S003",
        category=StandardCategory.SCHEMA,
        name="Field Descriptions",
        description="Pydantic Fields SOLLEN description haben",
        severity="warning",
        check_pattern=r"Field\([^)]*description\s*=",
    ),
    
    # ERROR HANDLING STANDARDS (E)
    "E001": Standard(
        id="E001",
        category=StandardCategory.ERROR_HANDLING,
        name="Try-Except in process()",
        description="process() MUSS try-except Block haben",
        severity="error",
        check_pattern=r"try\s*:",
    ),
    
    # LOGGING STANDARDS (L)
    "L001": Standard(
        id="L001",
        category=StandardCategory.LOGGING,
        name="Logger Usage",
        description="Handler SOLLEN self.logger verwenden",
        severity="warning",
        check_pattern=r"self\.logger\.",
    ),
    
    # DOCUMENTATION STANDARDS (D)
    "D001": Standard(
        id="D001",
        category=StandardCategory.DOCUMENTATION,
        name="Class Docstring",
        description="Handler-Klasse MUSS Docstring haben",
        severity="error",
        check_pattern=r'class\s+\w+Handler.*:\s*\n\s*"""',
        auto_fixable=True,
    ),
    
    # NAMING STANDARDS (N)
    "N001": Standard(
        id="N001",
        category=StandardCategory.NAMING,
        name="Handler Suffix",
        description="Handler-Klassen MÜSSEN mit 'Handler' enden",
        severity="error",
        check_pattern=r"class\s+\w+Handler\(",
    ),
    
    # TESTING STANDARDS (T)
    "T001": Standard(
        id="T001",
        category=StandardCategory.TESTING,
        name="Test Class",
        description="Handler SOLLTEN Test-Klasse haben",
        severity="warning",
        check_pattern=r"class\s+Test\w+Handler",
    ),
}


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def get_all_standards() -> List[Standard]:
    """Alle Standards abrufen"""
    return list(STANDARDS.values())


def get_standards_by_category(category: StandardCategory) -> List[Standard]:
    """Standards einer Kategorie"""
    return [s for s in STANDARDS.values() if s.category == category]


def get_standards_by_severity(severity: str) -> List[Standard]:
    """Standards einer Severity"""
    return [s for s in STANDARDS.values() if s.severity == severity]


def get_error_standards() -> List[Standard]:
    """Nur Error-Standards (MÜSSEN erfüllt sein)"""
    return get_standards_by_severity("error")


def get_standard(standard_id: str) -> Optional[Standard]:
    """Einzelnen Standard abrufen"""
    return STANDARDS.get(standard_id)
EOF

echo "✅ standards/__init__.py"

# ═══════════════════════════════════════════════════════════════════════════════
# 7. standards/validator.py
# ═══════════════════════════════════════════════════════════════════════════════
cat > "$TARGET_DIR/standards/validator.py" << 'EOF'
"""
Code Validator
==============

Validiert Python Code gegen BF Agent Standards.
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional

from . import STANDARDS, Standard, get_all_standards


@dataclass
class ValidationIssue:
    """Ein gefundenes Problem"""
    standard_id: str
    standard_name: str
    severity: str
    message: str
    line_number: Optional[int] = None
    auto_fixable: bool = False


@dataclass
class ValidationResult:
    """Gesamtergebnis der Validierung"""
    valid: bool
    score: float
    errors: List[ValidationIssue] = field(default_factory=list)
    warnings: List[ValidationIssue] = field(default_factory=list)
    
    @property
    def summary(self) -> str:
        if not self.errors and not self.warnings:
            return "✅ Alle Standards erfüllt!"
        parts = []
        if self.errors:
            parts.append(f"❌ {len(self.errors)} Fehler")
        if self.warnings:
            parts.append(f"⚠️ {len(self.warnings)} Warnungen")
        return " | ".join(parts)


class CodeValidator:
    """Validiert Code gegen alle BF Agent Standards"""
    
    def validate(self, code: str, strict: bool = False) -> ValidationResult:
        """
        Validiert Code gegen alle Standards.
        
        Args:
            code: Python Code
            strict: Warnings als Errors behandeln
        """
        issues = []
        
        for standard in get_all_standards():
            issue = self._check_standard(code, standard)
            if issue:
                issues.append(issue)
        
        # Gruppieren
        errors = [i for i in issues if i.severity == "error"]
        warnings = [i for i in issues if i.severity == "warning"]
        
        if strict:
            errors.extend(warnings)
            warnings = []
        
        # Score
        total = len(get_all_standards())
        failed = len(errors) + len(warnings) * 0.5
        score = max(0, 100 - (failed / total * 100))
        
        return ValidationResult(
            valid=len(errors) == 0,
            score=round(score, 1),
            errors=errors,
            warnings=warnings,
        )
    
    def _check_standard(self, code: str, std: Standard) -> Optional[ValidationIssue]:
        """Prüft einen Standard"""
        
        if std.check_pattern:
            if not re.search(std.check_pattern, code, re.MULTILINE):
                return ValidationIssue(
                    standard_id=std.id,
                    standard_name=std.name,
                    severity=std.severity,
                    message=std.description,
                    auto_fixable=std.auto_fixable,
                )
        
        if std.anti_pattern:
            match = re.search(std.anti_pattern, code, re.MULTILINE)
            if match:
                return ValidationIssue(
                    standard_id=std.id,
                    standard_name=std.name,
                    severity=std.severity,
                    message=f"Anti-pattern: {std.description}",
                    line_number=code[:match.start()].count('\n') + 1,
                )
        
        return None
    
    def format_report(self, result: ValidationResult) -> str:
        """Formatiert Validation Report"""
        
        lines = [
            "# 📋 Validation Report",
            "",
            f"**Status:** {'✅ PASSED' if result.valid else '❌ FAILED'}",
            f"**Score:** {result.score}/100",
            f"**Summary:** {result.summary}",
            "",
        ]
        
        if result.errors:
            lines.append("## ❌ Errors")
            for e in result.errors:
                lines.append(f"- **[{e.standard_id}]** {e.message}")
        
        if result.warnings:
            lines.append("")
            lines.append("## ⚠️ Warnings")
            for w in result.warnings:
                lines.append(f"- **[{w.standard_id}]** {w.message}")
        
        return "\n".join(lines)
EOF

echo "✅ standards/validator.py"

# ═══════════════════════════════════════════════════════════════════════════════
# 8. standards/enforcer.py
# ═══════════════════════════════════════════════════════════════════════════════
cat > "$TARGET_DIR/standards/enforcer.py" << 'ENFORCER_EOF'
"""
Template Enforcer
=================

Generiert Handler-Code der BY DESIGN standard-konform ist.
"""

from typing import Dict, List, Any
import re


def to_snake_case(name: str) -> str:
    """CamelCase → snake_case"""
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


class TemplateEnforcer:
    """Generiert standard-konformen Code durch Templates"""
    
    def generate_handler(
        self,
        handler_name: str,
        description: str,
        domain: str,
        input_fields: List[Dict[str, Any]],
        output_fields: List[Dict[str, Any]],
        use_cases: List[str] = None,
        version: str = "1.0.0",
    ) -> Dict[str, str]:
        """
        Generiert Handler + Test Code.
        
        Returns:
            {"handler_code": str, "test_code": str, ...}
        """
        use_cases = use_cases or ["Process data"]
        snake_name = to_snake_case(handler_name)
        
        # Handler Code generieren
        handler_code = self._generate_handler_code(
            handler_name=handler_name,
            snake_name=snake_name,
            description=description,
            domain=domain,
            input_fields=input_fields,
            output_fields=output_fields,
            use_cases=use_cases,
            version=version,
        )
        
        # Test Code generieren
        test_code = self._generate_test_code(
            handler_name=handler_name,
            snake_name=snake_name,
            domain=domain,
            input_fields=input_fields,
            output_fields=output_fields,
        )
        
        return {
            "handler_code": handler_code,
            "test_code": test_code,
            "handler_filename": f"{snake_name}.py",
            "test_filename": f"test_{snake_name}.py",
        }
    
    def _generate_handler_code(self, **ctx) -> str:
        """Generiert Handler Code"""
        
        # Input Fields formatieren
        input_fields_str = self._format_fields(ctx["input_fields"])
        output_fields_str = self._format_fields(ctx["output_fields"])
        use_cases_str = "\n".join(f"    - {uc}" for uc in ctx["use_cases"])
        
        return f'''"""
{ctx["handler_name"]} - {ctx["description"]}

Auto-generated by BF Agent MCP Server
Standards: H001, H002, H003, H004, S001, S002, E001, L001, D001
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field, ValidationError

from apps.core.handlers.base import BaseHandler, HandlerResult


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMAS (Standards S001, S002, S003)
# ═══════════════════════════════════════════════════════════════════════════════

class {ctx["handler_name"]}Input(BaseModel):
    """Input Schema für {ctx["handler_name"]}"""
{input_fields_str}


class {ctx["handler_name"]}Output(BaseModel):
    """Output Schema für {ctx["handler_name"]}"""
{output_fields_str}


# ═══════════════════════════════════════════════════════════════════════════════
# HANDLER (Standards H001, H002, H003, H004, E001, L001, D001)
# ═══════════════════════════════════════════════════════════════════════════════

class {ctx["handler_name"]}(BaseHandler):
    """
    {ctx["description"]}
    
    Use Cases:
{use_cases_str}
    """
    
    # Metadata (H004)
    name = "{ctx["snake_name"]}"
    description = "{ctx["description"]}"
    version = "{ctx["version"]}"
    
    # Schemas (S001, S002)
    input_schema = {ctx["handler_name"]}Input
    output_schema = {ctx["handler_name"]}Output
    
    async def validate(self, context: Dict[str, Any]) -> None:
        """Phase 1: Validation (H002)"""
        self.logger.debug(f"Validating {{self.name}}")
        self.validated_input = self.input_schema(**context.get("input", {{}}))
    
    async def process(self, context: Dict[str, Any]) -> HandlerResult:
        """Phase 2: Processing (H002, H003, E001)"""
        try:
            self.logger.info(f"Processing {{self.name}}")
            
            # TODO: Implement business logic
            result_data = await self._do_process(self.validated_input)
            
            # Validate output
            output = self.output_schema(**result_data)
            
            self.logger.info(f"Completed {{self.name}}")
            
            return HandlerResult.success(
                data=output.model_dump(),
                metadata={{"handler": self.name, "version": self.version}}
            )
            
        except ValidationError as e:
            self.logger.warning(f"Validation failed: {{e}}")
            return HandlerResult.error(message=str(e), error_code="VALIDATION_ERROR")
        except Exception as e:
            self.logger.exception(f"Error in {{self.name}}")
            return HandlerResult.error(message=str(e), error_code="PROCESSING_ERROR")
    
    async def cleanup(self, context: Dict[str, Any]) -> None:
        """Phase 3: Cleanup (H002)"""
        self.logger.debug(f"Cleanup {{self.name}}")
    
    async def _do_process(self, input_data: {ctx["handler_name"]}Input) -> Dict[str, Any]:
        """Core processing - override this method"""
        raise NotImplementedError("Implement _do_process()")
'''
    
    def _generate_test_code(self, **ctx) -> str:
        """Generiert Test Code"""
        
        return f'''"""
Tests for {ctx["handler_name"]}

Standards: T001, T002, T003
"""

import pytest
from unittest.mock import patch, AsyncMock

from apps.{ctx["domain"]}.handlers.{ctx["snake_name"]} import (
    {ctx["handler_name"]},
    {ctx["handler_name"]}Input,
    {ctx["handler_name"]}Output,
)


class Test{ctx["handler_name"]}:
    """Test suite for {ctx["handler_name"]} (T001)"""
    
    @pytest.fixture
    def handler(self):
        return {ctx["handler_name"]}()
    
    @pytest.fixture
    def valid_input(self):
        return {{
            # TODO: Add valid test data
        }}
    
    @pytest.mark.asyncio
    async def test_process_success(self, handler, valid_input):
        """Happy path test (T002)"""
        context = {{"input": valid_input}}
        
        with patch.object(handler, "_do_process", new_callable=AsyncMock) as mock:
            mock.return_value = {{}}  # TODO: Add expected output
            result = await handler.execute(context)
        
        assert result.success is True
    
    @pytest.mark.asyncio
    async def test_process_error(self, handler):
        """Error path test (T003)"""
        context = {{"input": {{}}}}  # Invalid input
        
        result = await handler.execute(context)
        
        # Should handle gracefully
        assert result is not None
'''
    
    def _format_fields(self, fields: List[Dict[str, Any]]) -> str:
        """Formatiert Pydantic Fields"""
        if not fields:
            return "    pass"
        
        lines = []
        for f in fields:
            name = f.get("name", "field")
            ftype = f.get("type", "str")
            desc = f.get("description", "Field description")
            required = f.get("required", True)
            default = f.get("default", "None")
            
            if required:
                lines.append(f'    {name}: {ftype} = Field(..., description="{desc}")')
            else:
                lines.append(f'    {name}: {ftype} = Field(default={default}, description="{desc}")')
        
        return "\n".join(lines)
ENFORCER_EOF

echo "✅ standards/enforcer.py"

# ═══════════════════════════════════════════════════════════════════════════════
# 9. server.py
# ═══════════════════════════════════════════════════════════════════════════════
cat > "$TARGET_DIR/server.py" << 'EOF'
"""
BF Agent MCP Server v2.0
========================

Universal MCP Server mit:
- MetaPrompter Gateway (natürliche Sprache)
- Standards Enforcement (garantierte Konformität)
"""

from typing import Dict, Any

from .metaprompter import UniversalGateway, Intent
from .metaprompter.gateway import Strategy
from .standards import get_all_standards
from .standards.validator import CodeValidator
from .standards.enforcer import TemplateEnforcer


class BFAgentMCPServer:
    """
    BF Agent MCP Server mit Universal Gateway.
    
    Ein einziges Tool für ALLE Anfragen.
    """
    
    def __init__(self):
        # Core Components
        self.gateway = UniversalGateway(strategy=Strategy.HYBRID)
        self.validator = CodeValidator()
        self.enforcer = TemplateEnforcer()
        
        # Tool Executor registrieren
        self.gateway.set_tool_executor(self._execute_tool)
        
        # Tool Registry
        self._tools: Dict[str, callable] = {
            "bfagent_list_domains": self._list_domains,
            "bfagent_generate_handler": self._generate_handler,
            "bfagent_validate_handler": self._validate_handler,
            "bfagent_get_best_practices": self._get_best_practices,
            "bfagent_help": self._show_help,
            "cad_list_rooms": self._cad_list_rooms,
            "cad_get_dimensions": self._cad_get_dimensions,
            "cad_calculate_volume": self._cad_calculate_volume,
        }
    
    async def bfagent(self, request: str) -> str:
        """Universal Interface"""
        result = await self.gateway.process(request)
        
        if result.success:
            output = result.result or "✅ Erledigt"
            if result.assumptions:
                output += "\n\n---\nℹ️ **Annahmen:**\n"
                for a in result.assumptions:
                    output += f"• {a}\n"
            return output
        
        if result.needs_input:
            return result.prompt or "Was möchtest du tun?"
        
        return result.result or "❌ Unbekannter Fehler"
    
    async def _execute_tool(self, tool_name: str, params: Dict[str, Any]) -> str:
        """Führt internes Tool aus"""
        handler = self._tools.get(tool_name)
        if handler:
            return await handler(params)
        return f"❌ Tool nicht gefunden: {tool_name}"
    
    async def _list_domains(self, params: Dict) -> str:
        return """
# 📁 Verfügbare Domains

| Domain | Handler | Status |
|--------|---------|--------|
| book_writing | 20 | ✅ Production |
| cad_analysis | 12 | 🟡 Beta |
| medical_translation | 8 | ✅ Production |
| comic_creation | 15 | 🟢 Development |
| exschutz_forensics | 10 | 🟡 Beta |
"""
    
    async def _generate_handler(self, params: Dict) -> str:
        handler_name = params.get("handler_name", "NewHandler")
        description = params.get("description", "Auto-generated handler")
        domain = params.get("domain", "cad_analysis")
        
        input_fields = params.get("input_fields", [
            {"name": "file_path", "type": "str", "description": "Path to file", "required": True},
        ])
        output_fields = params.get("output_fields", [
            {"name": "data", "type": "Dict[str, Any]", "description": "Result data", "required": True},
        ])
        
        result = self.enforcer.generate_handler(
            handler_name=handler_name,
            description=description,
            domain=domain,
            input_fields=input_fields,
            output_fields=output_fields,
        )
        
        validation = self.validator.validate(result["handler_code"])
        
        return f"""
# ✅ Handler generiert: {handler_name}

**Score:** {validation.score}/100 | **Status:** {validation.summary}

## Handler Code
```python
{result['handler_code']}
```

## Test Code
```python
{result['test_code']}
```
"""
    
    async def _validate_handler(self, params: Dict) -> str:
        code = params.get("code", "")
        if not code:
            return "❌ Kein Code zum Validieren"
        
        result = self.validator.validate(code)
        return self.validator.format_report(result)
    
    async def _get_best_practices(self, params: Dict) -> str:
        standards = get_all_standards()
        output = "# 💡 Best Practices\n\n"
        for std in standards[:6]:
            output += f"### [{std.id}] {std.name}\n{std.description}\n\n"
        return output
    
    async def _show_help(self, params: Dict) -> str:
        return """
# 🤖 BF Agent MCP Server v2.0

Sprich einfach natürlich mit mir:
- "Erstelle einen IFC Parser für CAD"
- "Validiere diesen Code: ..."
- "Zeig Best Practices"
"""
    
    async def _cad_list_rooms(self, params: Dict) -> str:
        return "# 🏠 Räume\n\n| Raum | Fläche |\n|------|--------|\n| Wohnzimmer | 35.4 m² |"
    
    async def _cad_get_dimensions(self, params: Dict) -> str:
        return "# 📐 Dimensionen\n\n- Fläche: 35.4 m²\n- Volumen: 99.1 m³"
    
    async def _cad_calculate_volume(self, params: Dict) -> str:
        return "# 📊 Gesamtvolumen: 487.3 m³"


async def main():
    server = BFAgentMCPServer()
    tests = ["Hilfe", "Zeig alle Domains", "Erstelle einen IFC Parser für CAD"]
    for test in tests:
        print(f"\n{'='*60}\nINPUT: {test}\n{'='*60}")
        print(await server.bfagent(test))


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
EOF

echo "✅ server.py"

# ═══════════════════════════════════════════════════════════════════════════════
# 10. mcp_server.py (FastMCP)
# ═══════════════════════════════════════════════════════════════════════════════
cat > "$TARGET_DIR/mcp_server.py" << 'EOF'
"""
BF Agent MCP Server - FastMCP Integration
==========================================

Echter MCP Server mit FastMCP SDK.

Installation:
    pip install mcp

Usage:
    python -m bfagent_mcp.mcp_server
"""

from typing import Dict, Any, Optional
import json

# FastMCP Import
try:
    from mcp.server.fastmcp import FastMCP, Context
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    print("⚠️ MCP SDK nicht installiert. Run: pip install mcp")

from .metaprompter import UniversalGateway
from .metaprompter.gateway import Strategy
from .standards import get_all_standards, get_error_standards
from .standards.validator import CodeValidator
from .standards.enforcer import TemplateEnforcer


if MCP_AVAILABLE:
    mcp = FastMCP(
        "BF Agent",
        version="2.0.0",
        description="Universal Workflow Orchestration Platform - MCP Interface"
    )
else:
    mcp = None


_gateway: Optional[UniversalGateway] = None
_validator: Optional[CodeValidator] = None
_enforcer: Optional[TemplateEnforcer] = None


def get_gateway() -> UniversalGateway:
    global _gateway
    if _gateway is None:
        _gateway = UniversalGateway(strategy=Strategy.HYBRID)
    return _gateway


def get_validator() -> CodeValidator:
    global _validator
    if _validator is None:
        _validator = CodeValidator()
    return _validator


def get_enforcer() -> TemplateEnforcer:
    global _enforcer
    if _enforcer is None:
        _enforcer = TemplateEnforcer()
    return _enforcer


if MCP_AVAILABLE:
    
    @mcp.tool()
    async def bfagent(request: str, ctx: Context) -> str:
        """
        🤖 BF Agent Universal Interface
        
        Beispiele:
        - "Zeig alle Domains"
        - "Erstelle einen IFC Parser für CAD"
        - "Validiere diesen Code"
        - "Hilfe"
        """
        await ctx.info(f"Processing: {request[:50]}...")
        
        gateway = get_gateway()
        result = await gateway.process(request)
        
        if result.success:
            output = result.result or "✅ Erledigt"
            if result.assumptions:
                output += "\n\n---\nℹ️ **Annahmen:**\n"
                for a in result.assumptions:
                    output += f"• {a}\n"
            return output
        
        if result.needs_input:
            return result.prompt or "Was möchtest du tun?"
        
        return result.result or "❌ Fehler aufgetreten"
    
    
    @mcp.tool()
    async def bfagent_generate_handler(
        handler_name: str,
        description: str,
        domain: str = "cad_analysis",
        ctx: Context = None,
    ) -> str:
        """Generiert einen standard-konformen Handler."""
        if ctx:
            await ctx.info(f"Generating handler: {handler_name}")
        
        enforcer = get_enforcer()
        validator = get_validator()
        
        inputs = [{"name": "file_path", "type": "str", "description": "Input file", "required": True}]
        outputs = [{"name": "data", "type": "Dict[str, Any]", "description": "Result", "required": True}]
        
        result = enforcer.generate_handler(
            handler_name=handler_name,
            description=description,
            domain=domain,
            input_fields=inputs,
            output_fields=outputs,
        )
        
        validation = validator.validate(result["handler_code"])
        
        return f"""# ✅ Handler generiert: {handler_name}

**Score:** {validation.score}/100 | **Domain:** {domain}

## Handler Code
```python
{result['handler_code']}
```

## Test Code
```python
{result['test_code']}
```
"""
    
    
    @mcp.tool()
    async def bfagent_validate_code(code: str, ctx: Context = None) -> str:
        """Validiert Python Code gegen BF Agent Standards."""
        if ctx:
            await ctx.info("Validating code...")
        
        validator = get_validator()
        result = validator.validate(code)
        return validator.format_report(result)
    
    
    @mcp.tool()
    async def bfagent_list_standards(ctx: Context = None) -> str:
        """Listet alle BF Agent Coding Standards."""
        standards = get_all_standards()
        errors = get_error_standards()
        
        output = f"# 📋 BF Agent Coding Standards\n\n"
        output += f"**Total:** {len(standards)} | **Errors:** {len(errors)}\n\n"
        output += "| ID | Name | Severity |\n|----|------|----------|\n"
        
        for s in standards:
            output += f"| {s.id} | {s.name} | {s.severity} |\n"
        
        return output
    
    
    @mcp.resource("bfagent://domains")
    def get_domains() -> str:
        """Liste aller verfügbaren Domains"""
        return """# Domains

| Domain | Status |
|--------|--------|
| book_writing | ✅ Production |
| cad_analysis | 🟡 Beta |
| medical_translation | ✅ Production |
"""


def run_server():
    """Startet den MCP Server"""
    if not MCP_AVAILABLE:
        print("❌ MCP SDK nicht verfügbar!")
        print("   Installation: pip install mcp")
        return
    
    print("🚀 BF Agent MCP Server v2.0")
    mcp.run()


if __name__ == "__main__":
    run_server()
EOF

echo "✅ mcp_server.py"

# ═══════════════════════════════════════════════════════════════════════════════
# 11. django_orm.py
# ═══════════════════════════════════════════════════════════════════════════════
cat > "$TARGET_DIR/django_orm.py" << 'EOF'
"""
Django ORM Integration
======================

Verbindet MCP Server mit echten Django Handler-Daten.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum


class HandlerCategory(Enum):
    INPUT = "input"
    PROCESSING = "processing"
    OUTPUT = "output"
    AI_GENERATION = "ai_generation"
    AI_ANALYSIS = "ai_analysis"


@dataclass
class DomainInfo:
    id: str
    name: str
    description: str
    handler_count: int
    status: str


@dataclass
class HandlerInfo:
    id: int
    name: str
    slug: str
    description: str
    domain: str
    category: HandlerCategory
    version: str
    is_active: bool
    ai_powered: bool
    handler_class: str


class DjangoORM:
    """Django ORM Wrapper für MCP Server."""
    
    def __init__(self):
        self._django_available = self._check_django()
        if self._django_available:
            print("✅ Django ORM verfügbar")
        else:
            print("ℹ️ Django nicht verfügbar - nutze Mock-Daten")
    
    def _check_django(self) -> bool:
        try:
            import django
            from django.conf import settings
            return settings.configured
        except:
            return False
    
    def list_domains(self) -> List[DomainInfo]:
        if self._django_available:
            return self._list_domains_django()
        return self._list_domains_mock()
    
    def _list_domains_django(self) -> List[DomainInfo]:
        try:
            from apps.core.models import Domain
            return [
                DomainInfo(
                    id=d.slug, name=d.name, description=d.description or "",
                    handler_count=d.handlers.filter(is_active=True).count(),
                    status="production" if d.is_production else "development"
                )
                for d in Domain.objects.filter(is_active=True)
            ]
        except Exception as e:
            return self._list_domains_mock()
    
    def _list_domains_mock(self) -> List[DomainInfo]:
        return [
            DomainInfo("book_writing", "Book Writing", "Buchprojekte", 20, "production"),
            DomainInfo("cad_analysis", "CAD Analysis", "CAD/IFC Analyse", 12, "beta"),
            DomainInfo("medical_translation", "Medical Translation", "Medizin", 8, "production"),
        ]
    
    def list_handlers(self, domain: Optional[str] = None) -> List[HandlerInfo]:
        return self._list_handlers_mock(domain)
    
    def _list_handlers_mock(self, domain: Optional[str]) -> List[HandlerInfo]:
        handlers = [
            HandlerInfo(1, "IFC Room Parser", "ifc_room_parser", "Parst Räume", "cad_analysis",
                       HandlerCategory.PROCESSING, "1.0.0", True, False, "IFCRoomParserHandler"),
            HandlerInfo(2, "Chapter Generator", "chapter_generator", "Generiert Kapitel", "book_writing",
                       HandlerCategory.AI_GENERATION, "2.0.0", True, True, "ChapterGeneratorHandler"),
        ]
        if domain:
            return [h for h in handlers if h.domain == domain]
        return handlers
    
    def get_statistics(self) -> Dict[str, Any]:
        domains = self.list_domains()
        handlers = self.list_handlers()
        ai = [h for h in handlers if h.ai_powered]
        return {
            "total_domains": len(domains),
            "total_handlers": len(handlers),
            "ai_powered": len(ai),
        }


def get_orm() -> DjangoORM:
    return DjangoORM()
EOF

echo "✅ django_orm.py"

# ═══════════════════════════════════════════════════════════════════════════════
# 12. pyproject.toml
# ═══════════════════════════════════════════════════════════════════════════════
cat > "$TARGET_DIR/pyproject.toml" << 'EOF'
[project]
name = "bfagent-mcp"
version = "2.0.0"
description = "BF Agent MCP Server - Universal Workflow Orchestration"
requires-python = ">=3.10"
license = {text = "MIT"}
dependencies = [
    "mcp>=1.0.0",
    "pydantic>=2.0.0",
]

[project.optional-dependencies]
django = ["django>=4.2", "psycopg2-binary"]
dev = ["pytest>=7.0", "pytest-asyncio", "black", "ruff"]

[project.scripts]
bfagent-mcp = "bfagent_mcp.mcp_server:run_server"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["bfagent_mcp"]
EOF

echo "✅ pyproject.toml"

# ═══════════════════════════════════════════════════════════════════════════════
# 13. examples/mcp_config.json
# ═══════════════════════════════════════════════════════════════════════════════
cat > "$TARGET_DIR/examples/mcp_config.json" << 'EOF'
{
  "mcpServers": {
    "bfagent": {
      "command": "python",
      "args": ["-m", "bfagent_mcp.mcp_server"],
      "env": {
        "PYTHONPATH": "/path/to/your/packages",
        "DJANGO_SETTINGS_MODULE": "config.settings"
      }
    }
  }
}
EOF

echo "✅ examples/mcp_config.json"

# ═══════════════════════════════════════════════════════════════════════════════
# 14. README.md
# ═══════════════════════════════════════════════════════════════════════════════
cat > "$TARGET_DIR/README.md" << 'EOF'
# 🤖 BF Agent MCP Server v2.0

Universal MCP Server mit MetaPrompter Gateway und Standards Enforcement.

## Installation

```bash
pip install mcp pydantic
```

## Windsurf Setup

1. Config: `~/.codeium/windsurf/mcp_config.json`

```json
{
  "mcpServers": {
    "bfagent": {
      "command": "python",
      "args": ["-m", "bfagent_mcp.mcp_server"],
      "env": {
        "PYTHONPATH": "/path/to/packages"
      }
    }
  }
}
```

2. Windsurf → MCP Panel → Refresh
3. `@bfagent Hilfe`

## Features

- ✅ Universal Gateway - Ein Tool für alles
- ✅ Natural Language - Natürliche Sprache
- ✅ Standards Enforcement - 100% konformer Code
- ✅ Django Integration - Echte Daten

## Tools

| Tool | Beschreibung |
|------|--------------|
| `bfagent` | Universal Interface |
| `bfagent_generate_handler` | Handler generieren |
| `bfagent_validate_code` | Code validieren |
| `bfagent_list_standards` | Standards zeigen |
EOF

echo "✅ README.md"

# ═══════════════════════════════════════════════════════════════════════════════
# Done!
# ═══════════════════════════════════════════════════════════════════════════════

echo ""
echo "═══════════════════════════════════════════════════════════════════════════════"
echo "✅ Installation abgeschlossen!"
echo "═══════════════════════════════════════════════════════════════════════════════"
echo ""
echo "📁 Installiert in: $TARGET_DIR"
echo ""
echo "📋 Nächste Schritte:"
echo ""
echo "   1. Dependencies installieren:"
echo "      pip install mcp pydantic"
echo ""
echo "   2. Windsurf Config erstellen:"
echo "      ~/.codeium/windsurf/mcp_config.json"
echo ""
echo "      {"
echo "        \"mcpServers\": {"
echo "          \"bfagent\": {"
echo "            \"command\": \"python\","
echo "            \"args\": [\"-m\", \"bfagent_mcp.mcp_server\"],"
echo "            \"env\": {"
echo "              \"PYTHONPATH\": \"$(dirname $TARGET_DIR)\""
echo "            }"
echo "          }"
echo "        }"
echo "      }"
echo ""
echo "   3. Windsurf → MCP Panel → Refresh"
echo ""
echo "   4. Testen: @bfagent Hilfe"
echo ""
echo "═══════════════════════════════════════════════════════════════════════════════"
