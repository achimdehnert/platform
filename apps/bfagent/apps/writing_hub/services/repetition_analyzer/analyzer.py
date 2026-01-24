"""
Repetition Analyzer - Main Analyzer Module

Orchestriert alle Analyse-Module basierend auf analysis_level.
"""
from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from collections import defaultdict
import math
import re
import logging

from .config import Config, get_config

logger = logging.getLogger(__name__)


@dataclass
class WordRepetitionResult:
    """Ergebnis für ein wiederholtes Wort."""
    word: str
    frequency: int
    min_distance: int
    avg_distance: float
    salience: float
    score: float
    severity: str  # 'HIGH', 'MEDIUM', 'LOW'
    chapters: List[int]
    typ: str = 'wort'  # wort, proximity, fuellwort


@dataclass
class PhraseRepetitionResult:
    """Ergebnis für eine wiederholte Phrase."""
    phrase: str
    frequency: int
    severity: str
    typ: str = 'phrase'


@dataclass
class DiversityResult:
    """Ergebnis der lexikalischen Diversität."""
    word_count: int
    unique_words: int
    ttr: float
    mtld: float
    assessment: str
    severity: str


class RepetitionAnalyzer:
    """
    Hauptklasse für Wiederholungsanalyse.
    
    Unterstützt verschiedene analysis_levels:
    - basic: Keine ML-Dependencies
    - standard: +lexicalrichness
    - advanced: +spaCy
    - full: +Ollama Embeddings
    """
    
    def __init__(self, config: Config = None, profile: str = 'normal', 
                 analysis_level: str = 'basic'):
        self.config = config or get_config(profile, analysis_level)
        self._nlp = None
        self._nlp_loaded = False
    
    def analyze(self, chapters: Dict[int, str], character_names: List[str] = None) -> Dict[str, Any]:
        """
        Führt die Wiederholungsanalyse durch.
        
        Args:
            chapters: Dict mit {kapitel_nummer: text}
            character_names: Liste von Charakternamen (werden ignoriert)
            
        Returns:
            Dict mit allen Analyseergebnissen
        """
        print("[DEBUG] >>> RepetitionAnalyzer.analyze() CALLED <<<")
        level = self.config.analysis_level
        print(f"[DEBUG] Config analysis_level = {level}")
        logger.info(f"Starting repetition analysis (level={level})")
        
        # Charakternamen zur Config hinzufügen
        if character_names:
            self.config.character_names = [n.lower() for n in character_names]
        
        # Alle Wörter sammeln
        all_words = []
        chapter_words = {}  # {chapter_num: [words]}
        
        for chapter_num, content in chapters.items():
            if not content:
                continue
            words = self._tokenize(content)
            all_words.extend(words)
            chapter_words[chapter_num] = words
        
        total_words = len(all_words)
        logger.info(f"Total: {len(chapters)} chapters, {total_words} words")
        
        results = {
            'total_words': total_words,
            'total_chapters': len(chapters),
            'word_repetitions': [],
            'phrase_repetitions': [],
            'filler_words': [],
            'proximity_issues': [],
            'diversity': None,
            'fehler_count': 0,
        }
        
        if total_words == 0:
            return results
        
        # STUFE 1: Basis-Analyse (immer)
        results['proximity_issues'] = self._analyze_proximity(chapter_words)
        results['filler_words'] = self._analyze_filler_words(all_words, total_words)
        results['phrase_repetitions'] = self._analyze_phrases(all_words)
        results['word_repetitions'] = self._analyze_overused_words(
            all_words, chapter_words, total_words
        )
        
        # Lexikalische Diversität - IMMER mit lexicalrichness (wenn verfügbar)
        # Früher: level-basiert, jetzt: immer FULL versuchen
        results['diversity'] = self._analyze_diversity_full(all_words)
        
        # STUFE 3: Erweiterte Wort-Salienz (ohne spaCy wegen Python 3.14)
        if level in ['advanced', 'full']:
            # Heuristische Salienz-Bewertung basierend auf Wortmerkmalen
            results['word_repetitions'] = self._enhance_with_salience(
                results['word_repetitions'], all_words, total_words
            )
        
        # STUFE 4: Semantische Analyse
        if level == 'full':
            # Ollama Embeddings würden hier verwendet
            pass
        
        # Fehler zählen
        results['fehler_count'] = (
            len([r for r in results['proximity_issues'] if r.severity == 'HIGH']) +
            len([r for r in results['filler_words'] if r.severity == 'HIGH']) +
            len([r for r in results['phrase_repetitions'] if r.severity == 'HIGH']) +
            len([r for r in results['word_repetitions'] if r.severity == 'HIGH'])
        )
        
        return results
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenisiert Text in Wörter."""
        text = text.lower()
        words = re.findall(r'\b[a-zäöüß]{2,}\b', text)
        return words
    
    def _analyze_proximity(self, chapter_words: Dict[int, List[str]]) -> List[WordRepetitionResult]:
        """
        Analysiert Proximity-Wiederholungen (Wörter in kurzem Abstand).
        """
        PROXIMITY_WINDOW = 50
        MIN_WORD_LENGTH = 5
        
        proximity_issues = []
        stopwords = self.config.stopwords
        char_names = set(self.config.character_names)
        
        for chapter_num, words in chapter_words.items():
            word_positions = defaultdict(list)
            
            for pos, word in enumerate(words):
                if len(word) < MIN_WORD_LENGTH:
                    continue
                if word in stopwords:
                    continue
                if word in char_names:
                    continue
                word_positions[word].append(pos)
            
            # Prüfe auf Proximity-Wiederholungen
            for word, positions in word_positions.items():
                if len(positions) < 2:
                    continue
                
                close_count = 0
                for i in range(len(positions) - 1):
                    if positions[i+1] - positions[i] <= PROXIMITY_WINDOW:
                        close_count += 1
                
                if close_count >= 2:
                    proximity_issues.append({
                        'word': word,
                        'count': close_count,
                        'chapter': chapter_num
                    })
        
        # Gruppieren nach Wort
        by_word = defaultdict(list)
        for issue in proximity_issues:
            by_word[issue['word']].append(issue)
        
        # Top 20 nach Anzahl
        results = []
        sorted_words = sorted(by_word.items(), key=lambda x: sum(i['count'] for i in x[1]), reverse=True)[:20]
        
        for word, issues in sorted_words:
            total_count = sum(i['count'] for i in issues)
            chapters = list(set(i['chapter'] for i in issues))
            
            if total_count >= 3:
                results.append(WordRepetitionResult(
                    word=word,
                    frequency=total_count,
                    min_distance=PROXIMITY_WINDOW,
                    avg_distance=PROXIMITY_WINDOW / 2,
                    salience=0.7,
                    score=total_count * 0.1,
                    severity='HIGH' if total_count >= 10 else 'MEDIUM' if total_count >= 5 else 'LOW',
                    chapters=chapters,
                    typ='proximity'
                ))
        
        return results
    
    def _analyze_filler_words(self, all_words: List[str], total_words: int) -> List[WordRepetitionResult]:
        """Analysiert Füllwort-Übernutzung."""
        filler_words = self.config.filler_words
        word_counts = defaultdict(int)
        
        for word in all_words:
            if word in filler_words:
                word_counts[word] += 1
        
        results = []
        for word, count in word_counts.items():
            percentage = count / total_words
            
            if percentage > 0.001:  # >0.1%
                severity = 'HIGH' if percentage > 0.002 else 'MEDIUM' if percentage > 0.0015 else 'LOW'
                results.append(WordRepetitionResult(
                    word=word,
                    frequency=count,
                    min_distance=0,
                    avg_distance=total_words / count if count > 0 else 0,
                    salience=0.8,
                    score=percentage * 100,
                    severity=severity,
                    chapters=[],
                    typ='fuellwort'
                ))
        
        return sorted(results, key=lambda x: x.frequency, reverse=True)
    
    def _analyze_phrases(self, all_words: List[str]) -> List[PhraseRepetitionResult]:
        """Findet wiederholte 3-Wort-Phrasen."""
        stopwords = self.config.stopwords
        phrases = defaultdict(int)
        
        for i in range(len(all_words) - 2):
            w1, w2, w3 = all_words[i], all_words[i+1], all_words[i+2]
            
            # Mindestens ein Wort muss kein Stopword sein
            non_stop = sum(1 for w in [w1, w2, w3] if w not in stopwords and len(w) >= 4)
            if non_stop < 1:
                continue
            
            phrase = f"{w1} {w2} {w3}"
            if len(phrase) >= 12:
                phrases[phrase] += 1
        
        # Top 20 mit ≥5 Vorkommen
        results = []
        sorted_phrases = sorted(phrases.items(), key=lambda x: x[1], reverse=True)
        
        for phrase, count in sorted_phrases[:20]:
            if count >= 5:
                results.append(PhraseRepetitionResult(
                    phrase=phrase,
                    frequency=count,
                    severity='HIGH' if count >= 15 else 'MEDIUM' if count >= 8 else 'LOW',
                    typ='phrase'
                ))
        
        return results
    
    def _analyze_overused_words(self, all_words: List[str], chapter_words: Dict, 
                                 total_words: int) -> List[WordRepetitionResult]:
        """Findet stark übernutzte Wörter (>0.5% und >100x)."""
        stopwords = self.config.stopwords
        char_names = set(self.config.character_names)
        
        word_counts = defaultdict(int)
        for word in all_words:
            word_counts[word] += 1
        
        results = []
        for word, count in word_counts.items():
            if len(word) < 5:
                continue
            if word in stopwords:
                continue
            if word in char_names:
                continue
            
            percentage = count / total_words
            if count >= 100 and percentage > 0.005:
                # In welchen Kapiteln?
                chapters = [ch for ch, words in chapter_words.items() if word in words]
                
                results.append(WordRepetitionResult(
                    word=word,
                    frequency=count,
                    min_distance=int(total_words / count),
                    avg_distance=total_words / count,
                    salience=0.7,
                    score=percentage * 100,
                    severity='HIGH',
                    chapters=chapters[:5],
                    typ='wort'
                ))
        
        return sorted(results, key=lambda x: x.frequency, reverse=True)[:10]
    
    def _enhance_with_salience(self, word_results: List[WordRepetitionResult], 
                                all_words: List[str], total_words: int) -> List[WordRepetitionResult]:
        """
        Verbessert Wort-Ergebnisse mit heuristischer Salienz-Bewertung.
        Ersatz für spaCy POS-Tagging (nicht kompatibel mit Python 3.14).
        """
        # Heuristische Wort-Kategorien basierend auf Endungen/Mustern
        verb_endings = ('en', 'te', 'st', 'et', 'ete', 'ten', 'end')
        noun_indicators = ('ung', 'heit', 'keit', 'schaft', 'tion', 'tät')
        adj_endings = ('ig', 'lich', 'isch', 'bar', 'sam', 'haft', 'los')
        
        # TF-IDF-ähnliche Gewichtung
        word_freq = {}
        for w in all_words:
            word_freq[w] = word_freq.get(w, 0) + 1
        
        enhanced = []
        for result in word_results:
            word = result.word.lower()
            
            # Basis-Salienz
            salience = 0.5
            
            # Länge erhöht Salienz (längere Wörter sind spezifischer)
            if len(word) >= 8:
                salience += 0.2
            elif len(word) >= 6:
                salience += 0.1
            
            # Wortart-Heuristik
            if word.endswith(noun_indicators):
                salience += 0.15  # Substantive wichtig
            elif word.endswith(adj_endings):
                salience += 0.1   # Adjektive mittel-wichtig
            elif word.endswith(verb_endings) and len(word) > 4:
                salience += 0.05  # Verben weniger wichtig
            
            # Seltenheit erhöht Salienz (inverse document frequency)
            freq = word_freq.get(word, 1)
            idf = 1 - (freq / total_words)
            salience += idf * 0.2
            
            # Score neu berechnen
            new_score = result.score * salience
            
            # Neues Result mit angepasster Salienz
            enhanced.append(WordRepetitionResult(
                word=result.word,
                frequency=result.frequency,
                min_distance=result.min_distance,
                avg_distance=result.avg_distance,
                salience=min(salience, 1.0),
                score=new_score,
                severity=result.severity,
                chapters=result.chapters,
                typ=result.typ
            ))
        
        # Nach neuem Score sortieren
        return sorted(enhanced, key=lambda x: x.score, reverse=True)
    
    def _analyze_diversity_simple(self, words: List[str]) -> DiversityResult:
        """MTLD und HD-D Berechnung - versucht lexicalrichness, sonst Fallback."""
        if len(words) < 10:
            return DiversityResult(
                word_count=len(words),
                unique_words=len(set(words)),
                ttr=1.0,
                mtld=0,
                assessment="Zu wenig Text",
                severity="OK"
            )
        
        unique = len(set(words))
        ttr = unique / len(words)
        
        # Versuche lexicalrichness für MTLD und HD-D
        mtld = 0
        hdd = None
        use_library = False
        
        try:
            from lexicalrichness import LexicalRichness
            text = ' '.join(words)
            lex = LexicalRichness(text)
            mtld = lex.mtld()
            ttr = lex.ttr
            use_library = True
            
            # HD-D berechnen wenn genug Wörter
            if len(words) >= 42:
                try:
                    hdd = lex.hdd(draws=42)
                except:
                    pass
        except:
            # Fallback: Vereinfachte MTLD-Berechnung
            mtld = self._calculate_mtld(words)
        
        # Bewertung erstellen
        if mtld < 50:
            assessment = f"KRITISCH - Sehr geringe Diversität (MTLD={mtld:.1f}"
            severity = "CRITICAL"
        elif mtld < 70:
            assessment = f"WARNUNG - Niedrige Diversität (MTLD={mtld:.1f}"
            severity = "WARNING"
        elif mtld < 100:
            assessment = f"OK - Normale Diversität (MTLD={mtld:.1f}"
            severity = "OK"
        else:
            assessment = f"GUT - Hohe Diversität (MTLD={mtld:.1f}"
            severity = "OK"
        
        # HD-D hinzufügen wenn berechnet
        if hdd is not None:
            assessment += f", HD-D={hdd:.3f})"
        else:
            assessment += ")"
        
        return DiversityResult(
            word_count=len(words),
            unique_words=unique,
            ttr=ttr,
            mtld=mtld,
            assessment=assessment,
            severity=severity
        )
    
    def _analyze_diversity_full(self, words: List[str]) -> DiversityResult:
        """MTLD und HD-D mit lexicalrichness Library."""
        try:
            from lexicalrichness import LexicalRichness
            text = ' '.join(words)
            lex = LexicalRichness(text)
            
            mtld = lex.mtld()
            ttr = lex.ttr
            
            # HD-D (Hypergeometric Distribution D) - robustere Metrik
            hdd = None
            try:
                if len(words) >= 42:  # Minimum für HD-D
                    hdd = lex.hdd(draws=42)
            except Exception:
                pass
            
        except ImportError:
            logger.warning("lexicalrichness nicht installiert, verwende einfache Berechnung")
            return self._analyze_diversity_simple(words)
        except Exception as e:
            logger.warning(f"Fehler bei lexicalrichness: {e}")
            return self._analyze_diversity_simple(words)
        
        # Kombinierte Bewertung (MTLD + HD-D wenn verfügbar)
        if mtld < 50:
            assessment = f"KRITISCH - Sehr geringe Diversität (MTLD={mtld:.1f}"
            severity = "CRITICAL"
        elif mtld < 70:
            assessment = f"WARNUNG - Niedrige Diversität (MTLD={mtld:.1f}"
            severity = "WARNING"
        elif mtld < 100:
            assessment = f"OK - Normale Diversität (MTLD={mtld:.1f}"
            severity = "OK"
        else:
            assessment = f"GUT - Hohe Diversität (MTLD={mtld:.1f}"
            severity = "OK"
        
        # HD-D zur Bewertung hinzufügen
        if hdd is not None:
            assessment += f", HD-D={hdd:.3f})"
        else:
            assessment += ")"
        
        return DiversityResult(
            word_count=len(words),
            unique_words=len(set(words)),
            ttr=ttr,
            mtld=mtld,
            assessment=assessment,
            severity=severity
        )
    
    def _calculate_mtld(self, words: List[str], threshold: float = 0.72) -> float:
        """Vereinfachte MTLD-Berechnung."""
        if len(words) < 10:
            return 0.0
        
        def calculate_factors(word_list: List[str]) -> float:
            factors = 0.0
            start = 0
            
            for i in range(1, len(word_list) + 1):
                segment = word_list[start:i]
                ttr = len(set(segment)) / len(segment)
                
                if ttr <= threshold:
                    factors += 1.0
                    start = i
            
            # Partieller Faktor
            if start < len(word_list):
                segment = word_list[start:]
                if len(segment) > 0:
                    ttr = len(set(segment)) / len(segment)
                    partial = (1 - ttr) / (1 - threshold) if threshold < 1 else 0
                    factors += min(partial, 1.0)
            
            return len(word_list) / factors if factors > 0 else len(word_list)
        
        forward = calculate_factors(words)
        backward = calculate_factors(words[::-1])
        
        return (forward + backward) / 2
