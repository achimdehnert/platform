"""
NL2CAD Learning System - Speichert und lernt Query-Intent Paare.

Ermöglicht:
- Feedback von Nutzern speichern
- Gelernte Patterns für bessere Erkennung nutzen
- Synonyme und Variationen lernen
"""
import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional
import re

logger = logging.getLogger(__name__)

# Storage path for learned patterns
LEARNING_DATA_PATH = Path(__file__).parent.parent / "data" / "nl_learning.json"


@dataclass
class LearnedPattern:
    """Ein gelerntes Query-Intent Paar."""
    query: str
    query_normalized: str
    intent: str
    confidence: float = 1.0
    source: str = "user_feedback"  # user_feedback, auto_learned, admin
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    use_count: int = 0
    
    def to_dict(self) -> dict:
        return asdict(self)


class NLLearningStore:
    """
    Speichert und verwaltet gelernte NL Patterns.
    
    Features:
    - JSON-basierter persistenter Speicher
    - Fuzzy Matching für ähnliche Queries
    - Confidence-basierte Priorisierung
    - Usage Tracking
    """
    
    def __init__(self, data_path: Path = None):
        self.data_path = data_path or LEARNING_DATA_PATH
        self.patterns: list[LearnedPattern] = []
        self._load()
    
    def _load(self):
        """Lädt gelernte Patterns aus JSON."""
        try:
            if self.data_path.exists():
                with open(self.data_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.patterns = [
                        LearnedPattern(**p) for p in data.get("patterns", [])
                    ]
                logger.info(f"[NLLearning] Loaded {len(self.patterns)} patterns")
        except Exception as e:
            logger.warning(f"[NLLearning] Could not load: {e}")
            self.patterns = []
    
    def _save(self):
        """Speichert Patterns in JSON."""
        try:
            self.data_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.data_path, "w", encoding="utf-8") as f:
                json.dump({
                    "version": "1.0",
                    "updated_at": datetime.now().isoformat(),
                    "pattern_count": len(self.patterns),
                    "patterns": [p.to_dict() for p in self.patterns],
                }, f, indent=2, ensure_ascii=False)
            logger.info(f"[NLLearning] Saved {len(self.patterns)} patterns")
        except Exception as e:
            logger.error(f"[NLLearning] Could not save: {e}")
    
    @staticmethod
    def normalize_query(query: str) -> str:
        """Normalisiert Query für Vergleich."""
        # Lowercase
        normalized = query.lower().strip()
        # Remove punctuation
        normalized = re.sub(r'[^\w\s]', '', normalized)
        # Collapse whitespace
        normalized = re.sub(r'\s+', ' ', normalized)
        return normalized
    
    def learn(self, query: str, intent: str, source: str = "user_feedback") -> LearnedPattern:
        """
        Speichert neues Query-Intent Paar.
        
        Args:
            query: Original Query
            intent: Korrekter Intent
            source: Quelle (user_feedback, auto_learned, admin)
        
        Returns:
            Gespeichertes Pattern
        """
        normalized = self.normalize_query(query)
        
        # Check if similar pattern exists
        existing = self.find_exact(normalized)
        if existing:
            existing.intent = intent
            existing.confidence = min(existing.confidence + 0.1, 1.0)
            existing.use_count += 1
            self._save()
            return existing
        
        # Create new pattern
        pattern = LearnedPattern(
            query=query,
            query_normalized=normalized,
            intent=intent,
            source=source,
        )
        self.patterns.append(pattern)
        self._save()
        
        logger.info(f"[NLLearning] Learned: '{query}' → {intent}")
        return pattern
    
    def find_exact(self, query_normalized: str) -> Optional[LearnedPattern]:
        """Findet exaktes Match."""
        for p in self.patterns:
            if p.query_normalized == query_normalized:
                return p
        return None
    
    def find_similar(self, query: str, threshold: float = 0.7) -> Optional[LearnedPattern]:
        """
        Findet ähnliches Pattern mittels Jaccard-Similarity.
        
        Args:
            query: Suchquery
            threshold: Mindest-Ähnlichkeit (0-1)
        
        Returns:
            Bestes Match oder None
        """
        normalized = self.normalize_query(query)
        query_words = set(normalized.split())
        
        best_match = None
        best_score = threshold
        
        for pattern in self.patterns:
            pattern_words = set(pattern.query_normalized.split())
            
            # Jaccard similarity
            intersection = len(query_words & pattern_words)
            union = len(query_words | pattern_words)
            
            if union > 0:
                score = intersection / union
                if score > best_score:
                    best_score = score
                    best_match = pattern
        
        if best_match:
            best_match.use_count += 1
            self._save()
            logger.info(f"[NLLearning] Found similar: '{query}' ≈ '{best_match.query}' ({best_score:.2f})")
        
        return best_match
    
    def get_intent(self, query: str) -> Optional[str]:
        """
        Versucht Intent aus gelernten Patterns zu finden.
        
        Args:
            query: Query
        
        Returns:
            Intent oder None
        """
        normalized = self.normalize_query(query)
        
        # 1. Exact match
        exact = self.find_exact(normalized)
        if exact:
            return exact.intent
        
        # 2. Similar match
        similar = self.find_similar(query)
        if similar:
            return similar.intent
        
        return None
    
    def get_suggestions(self, partial_query: str, limit: int = 5) -> list[str]:
        """
        Gibt Vorschläge basierend auf gelernten Patterns.
        
        Args:
            partial_query: Teilweise eingegebene Query
            limit: Max Anzahl Vorschläge
        
        Returns:
            Liste von Query-Vorschlägen
        """
        partial_lower = partial_query.lower()
        suggestions = []
        
        for pattern in sorted(self.patterns, key=lambda p: -p.use_count):
            if partial_lower in pattern.query.lower():
                suggestions.append(pattern.query)
                if len(suggestions) >= limit:
                    break
        
        return suggestions
    
    def get_examples_for_intent(self, intent: str, limit: int = 3) -> list[str]:
        """Gibt Beispiel-Queries für einen Intent."""
        examples = []
        for p in self.patterns:
            if p.intent == intent:
                examples.append(p.query)
                if len(examples) >= limit:
                    break
        return examples
    
    def get_stats(self) -> dict:
        """Statistiken über gelernte Patterns."""
        intent_counts = {}
        for p in self.patterns:
            intent_counts[p.intent] = intent_counts.get(p.intent, 0) + 1
        
        return {
            "total_patterns": len(self.patterns),
            "intents": intent_counts,
            "most_used": sorted(self.patterns, key=lambda p: -p.use_count)[:5],
        }


# Singleton instance
_learning_store: Optional[NLLearningStore] = None

def get_learning_store() -> NLLearningStore:
    """Gibt Singleton LearningStore zurück."""
    global _learning_store
    if _learning_store is None:
        _learning_store = NLLearningStore()
    return _learning_store
