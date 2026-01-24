"""
Scientific Writing Handler
Generates academic/scientific content using LLM with proper methodology,
citations, and formal structure (IMRaD, Thesis, Literature Review).
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class SectionType(Enum):
    """Types of scientific paper sections with their specific requirements"""
    ABSTRACT = "abstract"
    INTRODUCTION = "introduction"
    LITERATURE_REVIEW = "literature_review"
    METHODOLOGY = "methodology"
    RESULTS = "results"
    DISCUSSION = "discussion"
    CONCLUSION = "conclusion"
    REFERENCES = "references"


@dataclass
class ScientificContext:
    """Context for scientific paper writing"""
    project_id: int
    section_id: int
    
    # Paper info
    title: str = ""
    research_field: str = ""  # e.g., "Wirtschaftsinformatik", "KI", "BWL"
    paper_type: str = ""  # e.g., "empirical", "theoretical", "literature_review"
    
    # Research question & hypothesis
    research_question: str = ""
    hypotheses: List[str] = field(default_factory=list)
    
    # Section info
    section_number: int = 1
    section_title: str = ""
    section_type: str = ""  # from SectionType enum
    section_outline: str = ""
    target_word_count: int = 1000
    existing_content: str = ""
    
    # Previous sections for coherence
    abstract: str = ""
    introduction_summary: str = ""
    methodology_summary: str = ""
    results_summary: str = ""
    
    # Literature & Citations
    literature_sources: List[Dict] = field(default_factory=list)
    citation_style: str = "APA"  # APA, Harvard, IEEE, etc.
    
    # Key concepts and definitions
    key_concepts: List[Dict] = field(default_factory=list)
    
    def to_prompt_context(self) -> str:
        """Build comprehensive context string for scientific LLM prompt"""
        parts = []
        
        # ===== PAPER INFO =====
        parts.append("=" * 60)
        parts.append("📚 WISSENSCHAFTLICHE ARBEIT")
        parts.append("=" * 60)
        parts.append(f"**Titel:** {self.title}")
        parts.append(f"**Fachgebiet:** {self.research_field}")
        parts.append(f"**Arbeitstyp:** {self.paper_type}")
        parts.append(f"**Zitationsstil:** {self.citation_style}")
        
        # ===== RESEARCH FOUNDATION =====
        parts.append("")
        parts.append("=" * 60)
        parts.append("🎯 FORSCHUNGSGRUNDLAGE")
        parts.append("=" * 60)
        parts.append(f"**Forschungsfrage:** {self.research_question}")
        
        if self.hypotheses:
            parts.append("\n**Hypothesen:**")
            for i, h in enumerate(self.hypotheses, 1):
                parts.append(f"  H{i}: {h}")
        
        # ===== CURRENT SECTION =====
        parts.append("")
        parts.append("=" * 60)
        parts.append(f"📝 ZU SCHREIBENDER ABSCHNITT: {self.section_number}. {self.section_title}")
        parts.append("=" * 60)
        parts.append(f"**Abschnittstyp:** {self.section_type}")
        parts.append(f"**Ziel-Wortanzahl:** ca. {self.target_word_count} Wörter")
        
        if self.section_outline:
            parts.append(f"\n**Gliederung dieses Abschnitts:**\n{self.section_outline}")
        
        # ===== PREVIOUS SECTIONS SUMMARY =====
        if self.abstract or self.introduction_summary or self.methodology_summary:
            parts.append("")
            parts.append("=" * 60)
            parts.append("📋 BISHERIGER INHALT (Zusammenfassung)")
            parts.append("=" * 60)
            
            if self.abstract:
                parts.append(f"\n**Abstract:** {self.abstract[:500]}...")
            if self.introduction_summary:
                parts.append(f"\n**Einleitung:** {self.introduction_summary[:500]}...")
            if self.methodology_summary:
                parts.append(f"\n**Methodik:** {self.methodology_summary[:500]}...")
            if self.results_summary:
                parts.append(f"\n**Ergebnisse:** {self.results_summary[:500]}...")
        
        # ===== LITERATURE =====
        if self.literature_sources:
            parts.append("")
            parts.append("=" * 60)
            parts.append("📖 VERFÜGBARE LITERATUR")
            parts.append("=" * 60)
            for source in self.literature_sources[:10]:  # Limit to 10
                parts.append(f"- {source.get('author', 'Unknown')} ({source.get('year', 'n.d.')}): {source.get('title', 'Untitled')}")
                if source.get('key_findings'):
                    parts.append(f"  → {source.get('key_findings')}")
        
        # ===== KEY CONCEPTS =====
        if self.key_concepts:
            parts.append("")
            parts.append("=" * 60)
            parts.append("🔑 SCHLÜSSELKONZEPTE")
            parts.append("=" * 60)
            for concept in self.key_concepts:
                parts.append(f"- **{concept.get('term', '')}:** {concept.get('definition', '')}")
        
        return "\n".join(parts)


class ScientificWritingHandler:
    """
    Handler for generating scientific paper content.
    
    Differentiates from novel writing by:
    - Using formal, objective language
    - Including citations and references
    - Following academic structure (IMRaD, etc.)
    - Focusing on evidence and argumentation
    """
    
    # Section-specific system prompts
    SECTION_PROMPTS = {
        SectionType.ABSTRACT: """Du bist ein Experte für wissenschaftliches Schreiben.
Schreibe ein prägnantes Abstract (150-300 Wörter) das folgende enthält:
- Hintergrund und Problemstellung (1-2 Sätze)
- Ziel/Forschungsfrage (1 Satz)
- Methodik (1-2 Sätze)
- Zentrale Ergebnisse (2-3 Sätze)
- Schlussfolgerung und Implikationen (1-2 Sätze)

Verwende Passiv und unpersönliche Formulierungen. Keine Zitate im Abstract.""",

        SectionType.INTRODUCTION: """Du bist ein Experte für wissenschaftliches Schreiben.
Schreibe eine Einleitung die folgende Struktur hat:
1. **Problemhintergrund**: Warum ist das Thema relevant? (mit Belegen)
2. **Forschungslücke**: Was wurde noch nicht untersucht?
3. **Forschungsfrage**: Präzise Formulierung
4. **Zielsetzung**: Was will die Arbeit erreichen?
5. **Aufbau**: Kurzer Überblick über die Struktur

Verwende formale Sprache, zitiere relevante Quellen, vermeide "ich/wir".""",

        SectionType.LITERATURE_REVIEW: """Du bist ein Experte für systematische Literaturarbeit.
Erstelle einen Forschungsstand der:
- Chronologisch oder thematisch strukturiert ist
- Zentrale Theorien und Modelle vorstellt
- Empirische Befunde zusammenfasst
- Forschungslücken identifiziert
- Jeden Absatz mit Quellen belegt

Zitiere im Format: (Autor, Jahr) oder Autor (Jahr).
Vermeide lange wörtliche Zitate, paraphrasiere stattdessen.""",

        SectionType.METHODOLOGY: """Du bist ein Experte für Forschungsmethodik.
Beschreibe die Methodik so detailliert, dass sie replizierbar ist:
1. **Forschungsdesign**: Qualitativ/quantitativ, Zeitraum
2. **Stichprobe**: Größe, Auswahl, Charakteristika
3. **Datenerhebung**: Instrumente, Ablauf
4. **Datenanalyse**: Statistische Verfahren oder Analysemethode
5. **Gütekriterien**: Validität, Reliabilität, Objektivität

Begründe methodische Entscheidungen mit Literaturverweisen.""",

        SectionType.RESULTS: """Du bist ein Experte für Ergebnisdarstellung.
Präsentiere die Ergebnisse:
- Objektiv und sachlich (keine Interpretation)
- Strukturiert nach Forschungsfragen/Hypothesen
- Mit konkreten Zahlen und Statistiken
- Unter Verweis auf Tabellen/Abbildungen

Bei quantitativen Daten: Mittelwerte, SD, p-Werte, Effektstärken.
Bei qualitativen Daten: Kategorien, Häufigkeiten, Ankerbeispiele.""",

        SectionType.DISCUSSION: """Du bist ein Experte für wissenschaftliche Diskussion.
Diskutiere die Ergebnisse:
1. **Zusammenfassung**: Zentrale Befunde kurz wiederholen
2. **Interpretation**: Was bedeuten die Ergebnisse?
3. **Einordnung**: Vergleich mit Literatur (bestätigt/widerspricht)
4. **Implikationen**: Theoretische und praktische Bedeutung
5. **Limitationen**: Einschränkungen der Studie
6. **Ausblick**: Zukünftige Forschung

Argumentiere ausgewogen, benenne Stärken UND Schwächen.""",

        SectionType.CONCLUSION: """Du bist ein Experte für wissenschaftliches Schreiben.
Schreibe ein Fazit das:
- Die Forschungsfrage explizit beantwortet
- Die wichtigsten Erkenntnisse zusammenfasst
- Praktische Handlungsempfehlungen gibt
- Einen Ausblick auf weitere Forschung bietet

Keine neuen Informationen, keine Zitate. Kurz und prägnant (ca. 5-10% der Gesamtarbeit).""",

        SectionType.REFERENCES: """Du bist ein Experte für wissenschaftliche Zitation.
Erstelle ein Literaturverzeichnis im angegebenen Stil.
Prüfe auf Vollständigkeit und korrekte Formatierung.""",
    }
    
    # Academic writing style guidelines
    STYLE_GUIDELINES = """
STILRICHTLINIEN FÜR WISSENSCHAFTLICHES SCHREIBEN:
- Verwende Passiv oder unpersönliche Formulierungen ("Es wurde untersucht..." statt "Ich untersuchte...")
- Vermeide umgangssprachliche Ausdrücke
- Definiere Fachbegriffe bei Erstnennung
- Verwende Absatzübergänge und Signalwörter (jedoch, darüber hinaus, folglich)
- Belege Behauptungen mit Quellen
- Formuliere präzise und sachlich
- Vermeide Redundanzen und Füllwörter
"""

    def __init__(self, llm_service=None):
        """Initialize with optional LLM service"""
        self.llm = llm_service
        self._init_llm()
    
    def _init_llm(self):
        """Initialize LLM if not provided"""
        if self.llm is None:
            try:
                from apps.bfagent.services.llm_client_service import LLMClientService
                self.llm = LLMClientService()
            except ImportError:
                logger.warning("LLMClientService not available")
                self.llm = None
    
    def generate_section(self, context: ScientificContext) -> Dict[str, Any]:
        """
        Generate a scientific paper section based on context.
        
        Args:
            context: ScientificContext with paper data
            
        Returns:
            Dict with success status, content, and metadata
        """
        section_type = self._get_section_type(context.section_type)
        
        # Build prompts
        system_prompt = self._build_system_prompt(section_type)
        user_prompt = self._build_user_prompt(context, section_type)
        
        logger.info(f"Generating scientific section: {context.section_title} (type: {section_type})")
        
        if not self.llm:
            return self._generate_mock(context, section_type)
        
        try:
            result = self.llm.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=context.target_word_count * 2,  # Tokens ≈ 0.75 words
                temperature=0.3  # Lower temperature for more factual output
            )
            
            if result.get('success'):
                content = result.get('content', '')
                return {
                    'success': True,
                    'content': content,
                    'word_count': len(content.split()),
                    'section_type': section_type.value,
                    'model_used': result.get('model', 'unknown')
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Unknown error'),
                    'content': ''
                }
                
        except Exception as e:
            logger.error(f"Error generating section: {e}")
            return {
                'success': False,
                'error': str(e),
                'content': ''
            }
    
    def _get_section_type(self, type_str: str) -> SectionType:
        """Convert string to SectionType enum"""
        type_map = {
            'abstract': SectionType.ABSTRACT,
            'introduction': SectionType.INTRODUCTION,
            'einleitung': SectionType.INTRODUCTION,
            'literature_review': SectionType.LITERATURE_REVIEW,
            'forschungsstand': SectionType.LITERATURE_REVIEW,
            'literatur': SectionType.LITERATURE_REVIEW,
            'methodology': SectionType.METHODOLOGY,
            'methodik': SectionType.METHODOLOGY,
            'methods': SectionType.METHODOLOGY,
            'results': SectionType.RESULTS,
            'ergebnisse': SectionType.RESULTS,
            'discussion': SectionType.DISCUSSION,
            'diskussion': SectionType.DISCUSSION,
            'conclusion': SectionType.CONCLUSION,
            'fazit': SectionType.CONCLUSION,
            'references': SectionType.REFERENCES,
            'literaturverzeichnis': SectionType.REFERENCES,
        }
        return type_map.get(type_str.lower(), SectionType.INTRODUCTION)
    
    def _build_system_prompt(self, section_type: SectionType) -> str:
        """Build system prompt for the section type"""
        base_prompt = self.SECTION_PROMPTS.get(section_type, self.SECTION_PROMPTS[SectionType.INTRODUCTION])
        return f"{base_prompt}\n\n{self.STYLE_GUIDELINES}"
    
    def _build_user_prompt(self, context: ScientificContext, section_type: SectionType) -> str:
        """Build user prompt with context"""
        prompt_parts = [
            context.to_prompt_context(),
            "",
            "=" * 60,
            f"AUFGABE: Schreibe den Abschnitt '{context.section_title}'",
            "=" * 60,
        ]
        
        # Section-specific instructions
        if section_type == SectionType.ABSTRACT:
            prompt_parts.append("\nSchreibe ein strukturiertes Abstract (150-300 Wörter).")
        elif section_type == SectionType.LITERATURE_REVIEW:
            prompt_parts.append("\nStrukturiere den Forschungsstand thematisch und zitiere alle relevanten Quellen.")
        elif section_type == SectionType.METHODOLOGY:
            prompt_parts.append("\nBeschreibe die Methodik so detailliert, dass sie replizierbar ist.")
        elif section_type == SectionType.RESULTS:
            prompt_parts.append("\nPräsentiere die Ergebnisse objektiv ohne Interpretation.")
        elif section_type == SectionType.DISCUSSION:
            prompt_parts.append("\nDiskutiere die Ergebnisse im Kontext der Literatur und benenne Limitationen.")
        
        prompt_parts.append(f"\nZiel-Wortanzahl: ca. {context.target_word_count} Wörter")
        prompt_parts.append(f"\nZitationsstil: {context.citation_style}")
        
        return "\n".join(prompt_parts)
    
    def _generate_mock(self, context: ScientificContext, section_type: SectionType) -> Dict[str, Any]:
        """Generate mock content when no LLM available"""
        logger.info(f"Using mock generation for scientific section: {section_type.value}")
        
        mock_content = {
            SectionType.ABSTRACT: f"""## Abstract

Die vorliegende Arbeit untersucht {context.title.lower()}. 
Vor dem Hintergrund der zunehmenden Bedeutung dieses Themas wurde folgende Forschungsfrage formuliert: {context.research_question}

Methodisch wurde ein [qualitatives/quantitatives] Forschungsdesign gewählt. Die Ergebnisse zeigen [zentrale Befunde].

Die Studie leistet einen Beitrag zum Verständnis von [Themengebiet] und gibt praktische Implikationen für [Zielgruppe].

*[Mock-Inhalt - LLM aktivieren für echte Generierung]*""",

            SectionType.INTRODUCTION: f"""## 1. Einleitung

### 1.1 Problemhintergrund

{context.research_field} gewinnt in der aktuellen Forschung zunehmend an Bedeutung (vgl. Autor, 2024). 
Die Relevanz des Themas "{context.title}" zeigt sich insbesondere in [Kontext].

### 1.2 Forschungslücke

Trotz umfangreicher Forschung zu [verwandtes Thema] besteht weiterhin Forschungsbedarf bezüglich [Lücke].

### 1.3 Forschungsfrage und Zielsetzung

Daraus ergibt sich folgende Forschungsfrage: **{context.research_question}**

### 1.4 Aufbau der Arbeit

Die Arbeit gliedert sich wie folgt: [Struktur]

*[Mock-Inhalt - LLM aktivieren für echte Generierung]*""",

            SectionType.METHODOLOGY: f"""## 3. Methodik

### 3.1 Forschungsdesign

Zur Beantwortung der Forschungsfrage wurde ein [Design] gewählt.

### 3.2 Datenerhebung

[Beschreibung der Datenerhebung]

### 3.3 Datenanalyse

[Analysemethoden]

*[Mock-Inhalt - LLM aktivieren für echte Generierung]*""",
        }
        
        content = mock_content.get(section_type, f"## {context.section_title}\n\n[Inhalt wird generiert - LLM aktivieren]")
        
        return {
            'success': True,
            'content': content,
            'word_count': len(content.split()),
            'section_type': section_type.value,
            'model_used': 'mock'
        }
    
    @staticmethod
    def get_imrad_sections() -> List[Dict[str, Any]]:
        """Get standard IMRaD section structure"""
        return [
            {'number': 0, 'title': 'Abstract', 'type': 'abstract', 'target_words': 250},
            {'number': 1, 'title': 'Einleitung', 'type': 'introduction', 'target_words': 1500},
            {'number': 2, 'title': 'Forschungsstand', 'type': 'literature_review', 'target_words': 3000},
            {'number': 3, 'title': 'Methodik', 'type': 'methodology', 'target_words': 2000},
            {'number': 4, 'title': 'Ergebnisse', 'type': 'results', 'target_words': 2500},
            {'number': 5, 'title': 'Diskussion', 'type': 'discussion', 'target_words': 2500},
            {'number': 6, 'title': 'Fazit', 'type': 'conclusion', 'target_words': 1000},
            {'number': 7, 'title': 'Literaturverzeichnis', 'type': 'references', 'target_words': 500},
        ]
    
    @staticmethod
    def get_thesis_sections() -> List[Dict[str, Any]]:
        """Get thesis/Abschlussarbeit section structure"""
        return [
            {'number': 0, 'title': 'Abstract', 'type': 'abstract', 'target_words': 300},
            {'number': 1, 'title': 'Einleitung & Motivation', 'type': 'introduction', 'target_words': 2000},
            {'number': 2, 'title': 'Theoretische Grundlagen', 'type': 'literature_review', 'target_words': 4000},
            {'number': 3, 'title': 'Stand der Forschung', 'type': 'literature_review', 'target_words': 3000},
            {'number': 4, 'title': 'Methodik', 'type': 'methodology', 'target_words': 2500},
            {'number': 5, 'title': 'Durchführung/Analyse', 'type': 'methodology', 'target_words': 3000},
            {'number': 6, 'title': 'Ergebnisse', 'type': 'results', 'target_words': 3000},
            {'number': 7, 'title': 'Diskussion', 'type': 'discussion', 'target_words': 3000},
            {'number': 8, 'title': 'Fazit', 'type': 'conclusion', 'target_words': 1500},
            {'number': 9, 'title': 'Ausblick', 'type': 'conclusion', 'target_words': 500},
            {'number': 10, 'title': 'Literaturverzeichnis', 'type': 'references', 'target_words': 1000},
        ]


# Convenience function for views
def generate_scientific_section(project_id: int, section_id: int, 
                                 context_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a scientific paper section.
    
    Args:
        project_id: Project ID
        section_id: Section/Chapter ID
        context_data: Dict with section context
        
    Returns:
        Dict with success, content, word_count
    """
    context = ScientificContext(
        project_id=project_id,
        section_id=section_id,
        title=context_data.get('title', ''),
        research_field=context_data.get('research_field', ''),
        paper_type=context_data.get('paper_type', 'empirical'),
        research_question=context_data.get('research_question', ''),
        hypotheses=context_data.get('hypotheses', []),
        section_number=context_data.get('section_number', 1),
        section_title=context_data.get('section_title', ''),
        section_type=context_data.get('section_type', 'introduction'),
        section_outline=context_data.get('section_outline', ''),
        target_word_count=context_data.get('target_word_count', 1000),
        existing_content=context_data.get('existing_content', ''),
        abstract=context_data.get('abstract', ''),
        introduction_summary=context_data.get('introduction_summary', ''),
        methodology_summary=context_data.get('methodology_summary', ''),
        results_summary=context_data.get('results_summary', ''),
        literature_sources=context_data.get('literature_sources', []),
        citation_style=context_data.get('citation_style', 'APA'),
        key_concepts=context_data.get('key_concepts', []),
    )
    
    handler = ScientificWritingHandler()
    return handler.generate_section(context)
