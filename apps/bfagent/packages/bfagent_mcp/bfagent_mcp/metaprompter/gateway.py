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
    AUTO_THRESHOLD = 0.70  # Etwas niedriger für schnellere Ausführung
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
