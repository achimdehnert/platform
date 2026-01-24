# -*- coding: utf-8 -*-
"""
ResearchAgent - Konsolidierter Research Agent.

Vereint bestehende Research-Funktionalität:
- BraveSearchService (Web Search)
- ResearchService (Full Research, Fact-Check)
- ResearchAgentHandler (Slide Generation)

Kompatibel mit dem Orchestrator (BaseAgent).
Kann in Pipelines mit anderen Agents kombiniert werden.
"""
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

from .orchestrator import BaseAgent, AgentState

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class SearchResult:
    """Ein einzelnes Suchergebnis."""
    title: str
    url: str
    snippet: str
    source_type: str = "web"
    relevance_score: float = 0.8
    metadata: Dict = field(default_factory=dict)


@dataclass
class ResearchResult:
    """Ergebnis einer Research-Operation."""
    query: str
    success: bool
    sources: List[SearchResult] = field(default_factory=list)
    findings: List[Dict] = field(default_factory=list)
    summary: Optional[str] = None
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "query": self.query,
            "success": self.success,
            "source_count": len(self.sources),
            "finding_count": len(self.findings),
            "summary": self.summary,
            "sources": [
                {"title": s.title, "url": s.url, "snippet": s.snippet[:100]}
                for s in self.sources[:5]
            ],
        }


@dataclass
class FactCheckResult:
    """Ergebnis einer Faktenprüfung."""
    claim: str
    verified: Optional[bool]  # True, False, None (unknown)
    confidence: float
    sources: List[SearchResult] = field(default_factory=list)
    explanation: Optional[str] = None


# =============================================================================
# RESEARCH AGENT
# =============================================================================

class ResearchAgent(BaseAgent):
    """
    Konsolidierter Research Agent für alle Domains.
    
    Features:
    - Web Search (via Brave Search)
    - Full Research mit Findings
    - Fact Checking
    - Summary Generation
    - World Building Support (für Writing Hub)
    
    Nutzt bestehende Services:
    - apps.research.services.brave_search_service
    - apps.research.services.research_service
    
    Usage (standalone):
        agent = ResearchAgent()
        result = agent.research("AI trends 2024")
        
    Usage (in Pipeline):
        pipeline = Pipeline([
            ResearchAgent(),
            WritingAgent(),
        ])
        result = await pipeline.run(AgentState(data={"query": "..."}))
    """
    
    name = "ResearchAgent"
    
    def __init__(self, use_mcp: bool = True, language: str = "de"):
        """
        Args:
            use_mcp: Ob MCP für Brave Search genutzt werden soll
            language: Sprache für Results (de, en)
        """
        self.use_mcp = use_mcp
        self.language = language
        self._brave_service = None
        self._research_service = None
    
    @property
    def brave_service(self):
        """Lazy load BraveSearchService."""
        if self._brave_service is None:
            try:
                from apps.research.services.brave_search_service import get_brave_search
                self._brave_service = get_brave_search()
            except ImportError:
                logger.warning("BraveSearchService not available, using LLM fallback")
                self._brave_service = LLMFallbackSearchService()
        return self._brave_service
    
    @property
    def research_service(self):
        """Lazy load ResearchService."""
        if self._research_service is None:
            try:
                from apps.research.services.research_service import get_research_service
                self._research_service = get_research_service()
            except ImportError:
                logger.warning("ResearchService not available")
                self._research_service = None
        return self._research_service
    
    async def execute(self, state: AgentState) -> AgentState:
        """
        Führt Research basierend auf State aus.
        
        Erwartet im State:
            - query: Suchanfrage
            - research_type (optional): 'quick', 'full', 'fact_check'
            - max_sources (optional): Max Anzahl Quellen
            
        Setzt im State:
            - research_result: ResearchResult
            - sources: Liste der Quellen
            - summary: Zusammenfassung
        """
        query = state.get("query", "")
        research_type = state.get("research_type", "quick")
        max_sources = state.get("max_sources", 5)
        
        if not query:
            return state.with_error("No query provided for research")
        
        if research_type == "fact_check":
            claim = state.get("claim", query)
            result = self.fact_check(claim)
            return state.with_data(
                fact_check_result=result.__dict__,
                verified=result.verified,
                confidence=result.confidence,
            )
        elif research_type == "full":
            result = self.full_research(query, max_sources=max_sources)
        else:
            result = self.quick_search(query, count=max_sources)
        
        return state.with_data(
            research_result=result.to_dict(),
            sources=[s.title for s in result.sources],
            summary=result.summary,
        )
    
    def quick_search(self, query: str, count: int = 5) -> ResearchResult:
        """
        Schnelle Web-Suche.
        
        Args:
            query: Suchanfrage
            count: Anzahl Ergebnisse
            
        Returns:
            ResearchResult mit Quellen
        """
        raw_result = self.brave_service.search(query, count=count)
        
        sources = []
        for item in raw_result.get('results', []):
            sources.append(SearchResult(
                title=item.get('title', ''),
                url=item.get('url', ''),
                snippet=item.get('description', ''),
                source_type='web',
            ))
        
        return ResearchResult(
            query=query,
            success=raw_result.get('success', False),
            sources=sources,
            summary=self._generate_quick_summary(query, sources),
            metadata={'mock': raw_result.get('mock', False)},
        )
    
    def full_research(
        self,
        query: str,
        max_sources: int = 10,
        domain: Optional[str] = None,
    ) -> ResearchResult:
        """
        Vollständige Research mit Findings.
        
        Args:
            query: Suchanfrage
            max_sources: Maximale Quellen
            domain: Optional Domain-Kontext
            
        Returns:
            ResearchResult mit Findings und Summary
        """
        if self.research_service:
            # Use full research service
            output = self.research_service.research(
                query,
                options={
                    'max_sources': max_sources,
                    'domain': domain,
                    'language': self.language,
                }
            )
            
            sources = [
                SearchResult(
                    title=s.get('title', ''),
                    url=s.get('url', ''),
                    snippet=s.get('snippet', ''),
                    source_type=s.get('source_type', 'web'),
                    relevance_score=s.get('relevance_score', 0.5),
                )
                for s in output.sources
            ]
            
            return ResearchResult(
                query=query,
                success=output.success,
                sources=sources,
                findings=output.findings,
                summary=output.summary,
                metadata=output.metadata,
            )
        else:
            # Fallback to quick search
            return self.quick_search(query, count=max_sources)
    
    def fact_check(self, claim: str, context: Optional[str] = None) -> FactCheckResult:
        """
        Prüft eine Behauptung auf Fakten.
        
        Args:
            claim: Die zu prüfende Behauptung
            context: Optionaler Kontext
            
        Returns:
            FactCheckResult mit Verification und Confidence
        """
        if self.research_service:
            result = self.research_service.fact_check(claim, context)
            
            sources = [
                SearchResult(
                    title=s.get('title', ''),
                    url=s.get('url', ''),
                    snippet=s.get('description', ''),
                )
                for s in result.get('sources', [])
            ]
            
            return FactCheckResult(
                claim=claim,
                verified=result.get('verified'),
                confidence=result.get('confidence', 0.0),
                sources=sources,
                explanation="; ".join(result.get('notes', [])),
            )
        else:
            # Simple fallback
            search_result = self.quick_search(f"fact check: {claim}", count=3)
            
            return FactCheckResult(
                claim=claim,
                verified=None,
                confidence=0.3,
                sources=search_result.sources,
                explanation="Konnte nicht verifiziert werden (Service unavailable)",
            )
    
    def research_for_world_building(
        self,
        topic: str,
        world_type: str = "fantasy",
    ) -> Dict:
        """
        Spezielle Research für World Building (Writing Hub).
        
        Args:
            topic: Thema (z.B. "mittelalterliche Städte", "Magie-Systeme")
            world_type: Art der Welt (fantasy, scifi, historical)
            
        Returns:
            Dict mit strukturierten World-Building Informationen
        """
        # Build search query based on world type
        query_prefix = {
            "fantasy": "fantasy worldbuilding",
            "scifi": "science fiction worldbuilding",
            "historical": "historical accuracy",
        }.get(world_type, "")
        
        full_query = f"{query_prefix} {topic}"
        result = self.full_research(full_query, max_sources=5)
        
        # Structure for world building
        return {
            "topic": topic,
            "world_type": world_type,
            "research": result.to_dict(),
            "inspirations": self._extract_inspirations(result),
            "details": self._extract_details(result),
            "suggested_elements": self._suggest_world_elements(topic, world_type),
        }
    
    # =========================================================================
    # PRIVATE METHODS
    # =========================================================================
    
    def _generate_quick_summary(
        self,
        query: str,
        sources: List[SearchResult],
    ) -> str:
        """Generiert schnelle Zusammenfassung."""
        if not sources:
            return f"Keine Ergebnisse für '{query}' gefunden."
        
        parts = [f"Recherche zu: {query}", f"Quellen gefunden: {len(sources)}", ""]
        
        for i, source in enumerate(sources[:3], 1):
            parts.append(f"{i}. {source.title}")
            if source.snippet:
                parts.append(f"   {source.snippet[:100]}...")
        
        return "\n".join(parts)
    
    def _extract_inspirations(self, result: ResearchResult) -> List[str]:
        """Extrahiert Inspirationen aus Research."""
        inspirations = []
        for source in result.sources[:3]:
            if source.title:
                inspirations.append(source.title)
        return inspirations
    
    def _extract_details(self, result: ResearchResult) -> List[Dict]:
        """Extrahiert Details aus Findings."""
        details = []
        for finding in result.findings[:5]:
            details.append({
                "content": finding.get('content', ''),
                "source": finding.get('source_title', ''),
            })
        return details
    
    def _suggest_world_elements(self, topic: str, world_type: str) -> List[str]:
        """Schlägt World-Building Elemente vor."""
        base_elements = {
            "fantasy": [
                "Magie-System und Regeln",
                "Rassen und Völker",
                "Geschichte und Legenden",
                "Geographie und Klima",
                "Politische Strukturen",
            ],
            "scifi": [
                "Technologie-Level",
                "Raumfahrt und FTL",
                "Alien-Spezies",
                "Gesellschaftsstruktur",
                "Ressourcen und Wirtschaft",
            ],
            "historical": [
                "Zeitperiode und Ort",
                "Gesellschaftliche Normen",
                "Kleidung und Alltag",
                "Politische Situation",
                "Bekannte historische Ereignisse",
            ],
        }
        
        return base_elements.get(world_type, base_elements["fantasy"])


# =============================================================================
# LLM FALLBACK SERVICE
# =============================================================================

class LLMFallbackSearchService:
    """
    LLM-basierter Fallback wenn Brave API nicht verfügbar.
    
    Nutzt LLMAgent um recherche-ähnliche Inhalte zu generieren.
    Deutlich besser als statische Mock-Daten.
    """
    
    def __init__(self):
        self._llm_agent = None
    
    @property
    def llm_agent(self):
        """Lazy load LLMAgent."""
        if self._llm_agent is None:
            try:
                from apps.bfagent.services.llm_agent import LLMAgent
                self._llm_agent = LLMAgent()
            except ImportError:
                logger.warning("LLMAgent not available")
                self._llm_agent = None
        return self._llm_agent
    
    def _get_model_preference(self, quality: str = "fast"):
        """Get ModelPreference object."""
        try:
            from apps.bfagent.services.llm_agent import ModelPreference
            return ModelPreference(quality=quality)
        except ImportError:
            return None
    
    def search(self, query: str, count: int = 5, **kwargs) -> Dict:
        """
        Generiert Suchergebnisse via LLM.
        
        Der LLM simuliert Web-Recherche basierend auf seinem Wissen.
        """
        if not self.llm_agent:
            return self._static_fallback(query, count)
        
        prompt = f"""Du bist ein Research-Assistent. Generiere {count} informative Suchergebnisse 
zum Thema: "{query}"

Für jedes Ergebnis gib an:
1. Titel (informativer Titel)
2. URL (plausible URL einer bekannten Quelle wie Wikipedia, Fachseiten, etc.)
3. Beschreibung (2-3 Sätze mit konkreten Fakten)

Antworte im JSON-Format:
[
  {{"title": "...", "url": "...", "description": "..."}},
  ...
]

Wichtig: Gib nur bekannte, faktisch korrekte Informationen. Bei Unsicherheit sage es.
"""
        
        try:
            pref = self._get_model_preference("fast")
            response = self.llm_agent.generate(
                prompt,
                preferences=pref,
            )
            
            if response.success and response.content:
                # Parse JSON from response
                import json
                import re
                
                # Extract JSON array from response
                content = response.content
                json_match = re.search(r'\[[\s\S]*\]', content)
                
                if json_match:
                    results = json.loads(json_match.group())
                    return {
                        'success': True,
                        'results': results[:count],
                        'llm_generated': True,
                        'model_used': response.model_used,
                    }
        except Exception as e:
            logger.warning(f"LLM fallback failed: {e}")
        
        return self._static_fallback(query, count)
    
    def local_search(self, query: str, count: int = 5) -> Dict:
        """Local search via LLM."""
        if not self.llm_agent:
            return {'success': True, 'results': [], 'llm_generated': False}
        
        prompt = f"""Generiere {count} lokale Geschäfte/Orte für: "{query}"

Für jeden Ort gib an:
- name: Name des Geschäfts
- address: Plausible Adresse
- rating: Bewertung 1-5
- description: Kurze Beschreibung

Antworte im JSON-Format als Array.
"""
        
        try:
            pref = self._get_model_preference("fast")
            response = self.llm_agent.generate(prompt, preferences=pref)
            if response.success and response.content:
                import json
                import re
                json_match = re.search(r'\[[\s\S]*\]', response.content)
                if json_match:
                    results = json.loads(json_match.group())
                    return {
                        'success': True,
                        'results': results[:count],
                        'llm_generated': True,
                    }
        except Exception as e:
            logger.warning(f"LLM local search failed: {e}")
        
        return {'success': True, 'results': [], 'llm_generated': False}
    
    def _static_fallback(self, query: str, count: int) -> Dict:
        """Fehlermeldung wenn LLM nicht verfügbar - KEIN statischer Fallback."""
        logger.warning(f"Research unavailable for: {query} (LLM not available)")
        return {
            'success': False,
            'results': [],
            'total': 0,
            'query': query,
            'error': 'research_unavailable',
            'message': 'Recherche ist zum jetzigen Zeitpunkt nicht möglich. '
                      'Weder Brave API noch LLM sind verfügbar. '
                      'Bitte versuchen Sie es später erneut.',
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def quick_research(query: str, count: int = 5) -> ResearchResult:
    """
    Convenience-Funktion für schnelle Recherche.
    
    Usage:
        from apps.bfagent.agents import quick_research
        
        result = quick_research("AI trends 2024")
        for source in result.sources:
            print(source.title)
    """
    agent = ResearchAgent()
    return agent.quick_search(query, count=count)


def verify_fact(claim: str) -> FactCheckResult:
    """
    Convenience-Funktion für Faktenprüfung.
    
    Usage:
        result = verify_fact("Die Erde ist rund")
        print(f"Verified: {result.verified}, Confidence: {result.confidence}")
    """
    agent = ResearchAgent()
    return agent.fact_check(claim)


def research_world(topic: str, world_type: str = "fantasy") -> Dict:
    """
    Convenience-Funktion für World Building Research.
    """
    agent = ResearchAgent()
    return agent.research_for_world_building(topic, world_type)


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "ResearchAgent",
    "ResearchResult",
    "SearchResult",
    "FactCheckResult",
    "quick_research",
    "verify_fact",
    "research_world",
]
