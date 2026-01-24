# -*- coding: utf-8 -*-
"""
WritingAgent - Agent für Story/Buch-Generierung.

Features:
- Character Consistency Check
- Plot Continuity Analysis
- Style Analysis
- Chapter Summary Generation
- Dialog Quality Check

Kompatibel mit dem Orchestrator (BaseAgent).
Nutzt LLMAgent für AI-basierte Analysen.
"""
import re
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import Counter

from .orchestrator import BaseAgent, AgentState

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class Character:
    """Charakter-Informationen."""
    name: str
    aliases: List[str] = field(default_factory=list)
    traits: List[str] = field(default_factory=list)
    mentions: int = 0
    first_appearance: Optional[int] = None  # Line number
    
    def matches(self, text: str) -> bool:
        """Prüft ob Text zu diesem Charakter passt."""
        text_lower = text.lower()
        if self.name.lower() in text_lower:
            return True
        return any(alias.lower() in text_lower for alias in self.aliases)


@dataclass
class PlotPoint:
    """Ein Handlungspunkt."""
    description: str
    chapter: Optional[int] = None
    line: Optional[int] = None
    resolved: bool = False
    importance: str = "medium"  # low, medium, high


@dataclass
class WritingAnalysis:
    """Ergebnis einer Schreibanalyse."""
    text_stats: Dict[str, Any] = field(default_factory=dict)
    characters: List[Character] = field(default_factory=list)
    style_metrics: Dict[str, float] = field(default_factory=dict)
    issues: List[Dict] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "text_stats": self.text_stats,
            "characters": [
                {"name": c.name, "mentions": c.mentions, "traits": c.traits}
                for c in self.characters
            ],
            "style_metrics": self.style_metrics,
            "issue_count": len(self.issues),
            "suggestion_count": len(self.suggestions),
        }


# =============================================================================
# STYLE PATTERNS
# =============================================================================

STYLE_ISSUES = {
    "passive_voice": {
        "pattern": r"\b(wurde|wird|worden|geworden|ist\s+\w+t)\b",
        "message": "Passiv-Konstruktion - aktive Form bevorzugen",
        "severity": "info",
    },
    "weak_verbs": {
        "pattern": r"\b(ist|war|hat|hatte|sein|haben|werden|machen|tun)\b",
        "message": "Schwaches Verb - stärkeres Verb erwägen",
        "severity": "info",
    },
    "adverb_overuse": {
        "pattern": r"\b\w+lich\b.*\b\w+lich\b",
        "message": "Mehrere Adverbien auf -lich - variieren",
        "severity": "info",
    },
    "repeated_start": {
        "check": "sentence_starts",
        "message": "Satzanfänge wiederholen sich",
        "severity": "warning",
    },
    "long_sentence": {
        "check": "sentence_length",
        "threshold": 40,
        "message": "Sehr langer Satz (>40 Wörter) - aufteilen erwägen",
        "severity": "info",
    },
    "dialog_attribution": {
        "pattern": r'[""]\s*,?\s*(sagte|fragte|antwortete|meinte|erwiderte)',
        "message": "Standard-Dialog-Attribut - Variation erwägen",
        "severity": "info",
    },
}

GENRE_KEYWORDS = {
    "fantasy": ["Magie", "Zauber", "Drache", "König", "Schwert", "Elf", "Zwerg"],
    "scifi": ["Raumschiff", "Galaxie", "Planet", "Laser", "Roboter", "AI", "Computer"],
    "romance": ["Liebe", "Herz", "Kuss", "Sehnsucht", "Leidenschaft"],
    "thriller": ["Mord", "Ermittlung", "Gefahr", "Flucht", "Verdacht"],
    "horror": ["Angst", "Dunkelheit", "Schrecken", "Monster", "Blut"],
}


# =============================================================================
# WRITING AGENT
# =============================================================================

class WritingAgent(BaseAgent):
    """
    Agent für Story/Buch-Analyse und -Generierung.
    
    Features:
    - Text Statistics (Wörter, Sätze, Lesezeit)
    - Character Extraction & Tracking
    - Style Analysis
    - Genre Detection
    - Dialog Quality Check
    
    Usage (standalone):
        agent = WritingAgent()
        analysis = agent.analyze_text(text)
        
    Usage (in Pipeline):
        pipeline = Pipeline([
            WritingAgent(),
            StyleEnhancerAgent(),
        ])
        result = await pipeline.run(AgentState(data={"text": "..."}))
    """
    
    name = "WritingAgent"
    
    def __init__(self, language: str = "de"):
        """
        Args:
            language: Sprache für Analyse (de, en)
        """
        self.language = language
        self._llm_agent = None  # Lazy load
    
    async def execute(self, state: AgentState) -> AgentState:
        """
        Führt Schreibanalyse auf Text im State aus.
        
        Erwartet im State:
            - text: Der zu analysierende Text
            - chapter_num (optional): Kapitelnummer
            
        Setzt im State:
            - writing_analysis: Vollständige WritingAnalysis
            - characters: Liste extrahierter Charaktere
            - style_score: Style-Score (0-100)
        """
        text = state.get("text", "")
        
        if not text:
            return state.with_error("No text provided for analysis")
        
        analysis = self.analyze_text(text)
        style_score = self._calculate_style_score(analysis)
        
        return state.with_data(
            writing_analysis=analysis.to_dict(),
            characters=[c.name for c in analysis.characters],
            style_score=style_score,
        )
    
    def analyze_text(self, text: str) -> WritingAnalysis:
        """
        Vollständige Textanalyse.
        
        Args:
            text: Zu analysierender Text
            
        Returns:
            WritingAnalysis mit allen Metriken
        """
        analysis = WritingAnalysis()
        
        # 1. Basic Stats
        analysis.text_stats = self._calculate_text_stats(text)
        
        # 2. Character Extraction
        analysis.characters = self._extract_characters(text)
        
        # 3. Style Metrics
        analysis.style_metrics = self._analyze_style(text)
        
        # 4. Style Issues
        analysis.issues = self._detect_style_issues(text)
        
        # 5. Suggestions
        analysis.suggestions = self._generate_suggestions(analysis)
        
        return analysis
    
    def check_character_consistency(
        self,
        text: str,
        known_characters: List[Dict],
    ) -> List[Dict]:
        """
        Prüft Charakter-Konsistenz.
        
        Args:
            text: Aktueller Text
            known_characters: Bekannte Charaktere mit Traits
            
        Returns:
            Liste von Inkonsistenzen
        """
        issues = []
        
        for char_data in known_characters:
            name = char_data.get("name", "")
            expected_traits = char_data.get("traits", [])
            
            # Find character mentions
            mentions = self._find_character_mentions(text, name)
            
            # Check for trait contradictions (simplified)
            for mention in mentions:
                context = self._get_context(text, mention)
                for trait in expected_traits:
                    opposite = self._get_opposite_trait(trait)
                    if opposite and opposite.lower() in context.lower():
                        issues.append({
                            "character": name,
                            "issue": f"Mögliche Inkonsistenz: {name} ist '{trait}', aber Text suggeriert '{opposite}'",
                            "context": context[:100],
                            "severity": "warning",
                        })
        
        return issues
    
    def generate_chapter_summary(self, text: str, max_sentences: int = 3) -> str:
        """
        Generiert Kapitelzusammenfassung.
        
        Args:
            text: Kapiteltext
            max_sentences: Maximale Sätze in Summary
            
        Returns:
            Zusammenfassung
        """
        sentences = self._split_into_sentences(text)
        
        if not sentences:
            return "Keine Zusammenfassung möglich."
        
        # Simple extractive summary: first and last significant sentences
        # Plus any sentences with character names
        characters = self._extract_characters(text)
        char_names = {c.name.lower() for c in characters}
        
        important_sentences = []
        
        # First sentence often sets the scene
        if sentences:
            important_sentences.append(sentences[0])
        
        # Sentences with main characters
        for sentence in sentences[1:-1]:
            if any(name in sentence.lower() for name in char_names):
                if len(important_sentences) < max_sentences:
                    important_sentences.append(sentence)
        
        # Last sentence often concludes
        if len(sentences) > 1 and len(important_sentences) < max_sentences:
            important_sentences.append(sentences[-1])
        
        return " ".join(important_sentences[:max_sentences])
    
    def detect_genre(self, text: str) -> Tuple[str, float]:
        """
        Erkennt Genre basierend auf Keywords.
        
        Returns:
            Tuple (genre, confidence)
        """
        text_lower = text.lower()
        scores = {}
        
        for genre, keywords in GENRE_KEYWORDS.items():
            matches = sum(1 for kw in keywords if kw.lower() in text_lower)
            scores[genre] = matches / len(keywords)
        
        if not scores:
            return "unknown", 0.0
        
        best_genre = max(scores, key=scores.get)
        confidence = scores[best_genre]
        
        return best_genre, confidence
    
    def analyze_dialog_quality(self, text: str) -> Dict:
        """
        Analysiert Dialog-Qualität.
        
        Returns:
            Dict mit Dialog-Metriken
        """
        # Find dialog (text in quotes)
        dialog_pattern = r'[„""»«]([^„""»«]+)[„""»«]'
        dialogs = re.findall(dialog_pattern, text)
        
        if not dialogs:
            return {
                "dialog_count": 0,
                "avg_length": 0,
                "variety_score": 0,
                "issues": [],
            }
        
        # Analyze
        lengths = [len(d.split()) for d in dialogs]
        avg_length = sum(lengths) / len(lengths)
        
        # Check variety of dialog attributions
        attributions = re.findall(
            r'[""]\s*,?\s*(\w+)\s+(?:er|sie|es)',
            text,
            re.IGNORECASE
        )
        unique_attrs = len(set(attributions))
        variety_score = min(100, unique_attrs / max(1, len(attributions)) * 100 * 2)
        
        issues = []
        if avg_length > 50:
            issues.append("Dialoge sind sehr lang - aufteilen erwägen")
        if variety_score < 30:
            issues.append("Dialog-Attribute wenig variiert")
        
        return {
            "dialog_count": len(dialogs),
            "avg_length": round(avg_length, 1),
            "variety_score": round(variety_score, 1),
            "issues": issues,
        }
    
    # =========================================================================
    # PRIVATE METHODS
    # =========================================================================
    
    def _calculate_text_stats(self, text: str) -> Dict:
        """Berechnet grundlegende Textstatistiken."""
        words = text.split()
        sentences = self._split_into_sentences(text)
        paragraphs = [p for p in text.split('\n\n') if p.strip()]
        
        word_count = len(words)
        sentence_count = len(sentences)
        
        # Reading time (avg 200 words/min)
        reading_time_min = word_count / 200
        
        # Average sentence length
        avg_sentence_length = word_count / max(1, sentence_count)
        
        return {
            "word_count": word_count,
            "sentence_count": sentence_count,
            "paragraph_count": len(paragraphs),
            "avg_sentence_length": round(avg_sentence_length, 1),
            "reading_time_minutes": round(reading_time_min, 1),
            "character_count": len(text),
        }
    
    def _extract_characters(self, text: str) -> List[Character]:
        """Extrahiert Charaktere aus Text."""
        # Find capitalized words that appear multiple times (likely names)
        words = re.findall(r'\b[A-ZÄÖÜ][a-zäöüß]+\b', text)
        word_counts = Counter(words)
        
        # Filter: must appear at least twice, not common words
        common_words = {
            "Der", "Die", "Das", "Ein", "Eine", "Und", "Aber", "Oder",
            "Wenn", "Als", "Nach", "Vor", "Mit", "Bei", "Zu", "Von",
        }
        
        characters = []
        for name, count in word_counts.most_common(10):
            if count >= 2 and name not in common_words:
                # Find first appearance
                match = re.search(rf'\b{re.escape(name)}\b', text)
                first_line = text[:match.start()].count('\n') + 1 if match else None
                
                characters.append(Character(
                    name=name,
                    mentions=count,
                    first_appearance=first_line,
                ))
        
        return characters
    
    def _analyze_style(self, text: str) -> Dict[str, float]:
        """Analysiert Schreibstil."""
        words = text.split()
        sentences = self._split_into_sentences(text)
        
        # Vocabulary richness (unique words / total words)
        unique_words = set(w.lower() for w in words)
        vocabulary_richness = len(unique_words) / max(1, len(words)) * 100
        
        # Sentence variety (std dev of sentence lengths)
        sentence_lengths = [len(s.split()) for s in sentences]
        if len(sentence_lengths) > 1:
            avg = sum(sentence_lengths) / len(sentence_lengths)
            variance = sum((l - avg) ** 2 for l in sentence_lengths) / len(sentence_lengths)
            sentence_variety = min(100, variance ** 0.5 * 5)
        else:
            sentence_variety = 0
        
        # Dialog ratio
        dialog_matches = re.findall(r'[„""»«][^„""»«]+[„""»«]', text)
        dialog_words = sum(len(d.split()) for d in dialog_matches)
        dialog_ratio = dialog_words / max(1, len(words)) * 100
        
        return {
            "vocabulary_richness": round(vocabulary_richness, 1),
            "sentence_variety": round(sentence_variety, 1),
            "dialog_ratio": round(dialog_ratio, 1),
        }
    
    def _detect_style_issues(self, text: str) -> List[Dict]:
        """Erkennt Stilprobleme."""
        issues = []
        lines = text.split('\n')
        sentences = self._split_into_sentences(text)
        
        for issue_name, config in STYLE_ISSUES.items():
            if "pattern" in config:
                for i, line in enumerate(lines, 1):
                    if re.search(config["pattern"], line, re.IGNORECASE):
                        issues.append({
                            "type": issue_name,
                            "message": config["message"],
                            "severity": config["severity"],
                            "line": i,
                        })
                        break  # One per type
            
            elif config.get("check") == "sentence_length":
                threshold = config.get("threshold", 40)
                for i, sentence in enumerate(sentences):
                    if len(sentence.split()) > threshold:
                        issues.append({
                            "type": issue_name,
                            "message": config["message"],
                            "severity": config["severity"],
                            "context": sentence[:50] + "...",
                        })
                        break
            
            elif config.get("check") == "sentence_starts":
                starts = [s.split()[0].lower() if s.split() else "" for s in sentences]
                start_counts = Counter(starts)
                for start, count in start_counts.most_common(3):
                    if count >= 3 and start:
                        issues.append({
                            "type": issue_name,
                            "message": f"'{start.title()}' beginnt {count} Sätze",
                            "severity": config["severity"],
                        })
                        break
        
        return issues
    
    def _generate_suggestions(self, analysis: WritingAnalysis) -> List[str]:
        """Generiert Verbesserungsvorschläge."""
        suggestions = []
        
        stats = analysis.text_stats
        style = analysis.style_metrics
        
        # Based on stats
        if stats.get("avg_sentence_length", 0) > 25:
            suggestions.append("Kürzere Sätze für bessere Lesbarkeit erwägen")
        
        if style.get("vocabulary_richness", 100) < 40:
            suggestions.append("Wortschatz variieren - Synonyme verwenden")
        
        if style.get("dialog_ratio", 0) < 10 and stats.get("word_count", 0) > 500:
            suggestions.append("Mehr Dialog könnte den Text lebendiger machen")
        
        if style.get("sentence_variety", 100) < 20:
            suggestions.append("Satzlängen variieren für besseren Rhythmus")
        
        # Based on issues
        error_types = [i["type"] for i in analysis.issues]
        if error_types.count("passive_voice") >= 3:
            suggestions.append("Passiv-Konstruktionen reduzieren")
        
        return suggestions
    
    def _calculate_style_score(self, analysis: WritingAnalysis) -> float:
        """Berechnet Gesamt-Style-Score."""
        score = 100
        
        # Deduct for issues
        for issue in analysis.issues:
            if issue["severity"] == "error":
                score -= 10
            elif issue["severity"] == "warning":
                score -= 5
            else:
                score -= 2
        
        # Bonus for good metrics
        style = analysis.style_metrics
        if style.get("vocabulary_richness", 0) > 50:
            score += 5
        if style.get("sentence_variety", 0) > 30:
            score += 5
        
        return max(0, min(100, score))
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Teilt Text in Sätze."""
        # Simple sentence splitting
        sentences = re.split(r'[.!?]+\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _find_character_mentions(self, text: str, name: str) -> List[int]:
        """Findet alle Erwähnungen eines Charakters."""
        positions = []
        for match in re.finditer(rf'\b{re.escape(name)}\b', text, re.IGNORECASE):
            positions.append(match.start())
        return positions
    
    def _get_context(self, text: str, position: int, window: int = 100) -> str:
        """Holt Kontext um eine Position."""
        start = max(0, position - window)
        end = min(len(text), position + window)
        return text[start:end]
    
    def _get_opposite_trait(self, trait: str) -> Optional[str]:
        """Gibt Gegenteil eines Traits zurück."""
        opposites = {
            "mutig": "ängstlich",
            "freundlich": "unfreundlich",
            "klug": "dumm",
            "stark": "schwach",
            "jung": "alt",
            "ruhig": "aufgeregt",
            "ehrlich": "unehrlich",
        }
        return opposites.get(trait.lower())


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def analyze_writing(text: str) -> WritingAnalysis:
    """
    Convenience-Funktion für Schreibanalyse.
    
    Usage:
        from apps.bfagent.agents import analyze_writing
        
        analysis = analyze_writing(chapter_text)
        print(f"Word count: {analysis.text_stats['word_count']}")
    """
    agent = WritingAgent()
    return agent.analyze_text(text)


def summarize_chapter(text: str, sentences: int = 3) -> str:
    """
    Generiert Kapitelzusammenfassung.
    """
    agent = WritingAgent()
    return agent.generate_chapter_summary(text, sentences)


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "WritingAgent",
    "WritingAnalysis",
    "Character",
    "analyze_writing",
    "summarize_chapter",
]
