"""
Repetition Analyzer - Configuration Module

Zentrale Konfiguration für alle Analyse-Parameter.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import json
from pathlib import Path


@dataclass
class SalienceWeights:
    """Salienz-Gewichte nach Wortklasse (spaCy POS-Tags)."""
    
    DET: float = 0.1      # Artikel
    ADP: float = 0.1      # Präpositionen
    CCONJ: float = 0.1    # Konjunktionen
    SCONJ: float = 0.1    # Subordinierende Konjunktionen
    PART: float = 0.1     # Partikeln
    PUNCT: float = 0.0    # Interpunktion
    SPACE: float = 0.0    # Whitespace
    PRON: float = 0.2     # Pronomen
    AUX: float = 0.3      # Hilfsverben
    VERB: float = 0.5     # Vollverben
    ADV: float = 0.6      # Adverbien
    NOUN: float = 0.7     # Nomen
    ADJ: float = 0.8      # Adjektive
    PROPN: float = 0.4    # Eigennamen
    NUM: float = 0.2      # Zahlen
    INTJ: float = 0.9     # Interjektionen
    X: float = 0.8        # Andere
    
    def get(self, pos_tag: str) -> float:
        return getattr(self, pos_tag, 0.5)


@dataclass
class DistanceWeights:
    """Distanz-Gewichte basierend auf Wortabstand."""
    
    very_close_max: int = 10
    very_close_weight: float = 1.0
    close_max: int = 30
    close_weight: float = 0.8
    medium_max: int = 100
    medium_weight: float = 0.5
    far_max: int = 300
    far_weight: float = 0.3
    very_far_max: int = 1000
    very_far_weight: float = 0.1
    distant_weight: float = 0.05
    
    def get_weight(self, distance: int) -> float:
        if distance <= self.very_close_max:
            return self.very_close_weight
        elif distance <= self.close_max:
            return self.close_weight
        elif distance <= self.medium_max:
            return self.medium_weight
        elif distance <= self.far_max:
            return self.far_weight
        elif distance <= self.very_far_max:
            return self.very_far_weight
        else:
            return self.distant_weight


@dataclass
class AnalysisThresholds:
    """Schwellenwerte für die Analyse."""
    
    word_min_frequency: int = 3
    word_min_salience: float = 0.3
    word_problem_score: float = 0.3
    word_critical_score: float = 0.6
    
    phrase_min_words: int = 3
    phrase_max_words: int = 8
    phrase_min_frequency: int = 2
    phrase_critical_distance: int = 500
    
    semantic_similarity_threshold: float = 0.75
    semantic_min_sentence_length: int = 5
    semantic_max_sentences: int = 1000
    
    mtld_critical: float = 50.0
    mtld_warning: float = 70.0
    mtld_good: float = 100.0


@dataclass
class Config:
    """Hauptkonfiguration für den Repetition Analyzer."""
    
    language: str = "de"
    analysis_level: str = "standard"  # basic, standard, advanced, full
    
    salience: SalienceWeights = field(default_factory=SalienceWeights)
    distance: DistanceWeights = field(default_factory=DistanceWeights)
    thresholds: AnalysisThresholds = field(default_factory=AnalysisThresholds)
    
    ignore_words: List[str] = field(default_factory=lambda: [
        "kapitel", "teil", "ende", "anfang"
    ])
    
    known_leitmotifs: List[str] = field(default_factory=list)
    character_names: List[str] = field(default_factory=list)
    
    # Deutsche Stopwords (erweitert)
    stopwords: set = field(default_factory=lambda: {
        'und', 'der', 'die', 'das', 'ist', 'war', 'sind', 'waren', 'in', 'zu', 'mit', 'auf',
        'für', 'von', 'ein', 'eine', 'einer', 'einem', 'einen', 'er', 'sie', 'es', 'an', 'als', 'auch',
        'so', 'wie', 'bei', 'nach', 'nur', 'noch', 'aber', 'oder', 'nicht', 'wenn', 'dass', 'doch',
        'sich', 'ich', 'mir', 'mich', 'du', 'dir', 'dich', 'wir', 'ihr', 'uns', 'euch',
        'sein', 'seine', 'seiner', 'seinem', 'seinen', 'ihre', 'ihrer', 'ihrem', 'ihren',
        'wird', 'wurde', 'werden', 'hat', 'hatte', 'haben', 'hatten', 'kann', 'konnte',
        'muss', 'musste', 'müssen', 'will', 'wollte', 'soll', 'sollte',
        'den', 'dem', 'des', 'vor', 'aus', 'über', 'unter', 'durch', 'gegen', 'ohne',
        'schon', 'dann', 'immer', 'wieder', 'mehr', 'sehr', 'hier', 'dort', 'jetzt', 'nun',
        'während', 'diesem', 'dieser', 'diese', 'dieses', 'welche', 'welcher'
    })
    
    # Füllwörter die bei Übernutzung problematisch sind
    filler_words: set = field(default_factory=lambda: {
        'plötzlich', 'irgendwie', 'eigentlich', 'wirklich', 'tatsächlich', 'natürlich',
        'offensichtlich', 'anscheinend', 'definitiv', 'absolut', 'total', 'völlig',
        'quasi', 'sozusagen', 'gewissermaßen', 'praktisch', 'grundsätzlich'
    })


# Vordefinierte Profile
PROFILES = {
    'strict': Config(
        analysis_level='standard',
        thresholds=AnalysisThresholds(
            word_min_frequency=2,
            word_problem_score=0.2,
            word_critical_score=0.4,
            phrase_min_frequency=2,
            semantic_similarity_threshold=0.65,
            mtld_warning=80.0,
        )
    ),
    'normal': Config(analysis_level='standard'),
    'relaxed': Config(
        analysis_level='standard',
        thresholds=AnalysisThresholds(
            word_min_frequency=5,
            word_problem_score=0.5,
            word_critical_score=0.8,
            phrase_min_frequency=3,
            semantic_similarity_threshold=0.85,
            mtld_warning=60.0,
        )
    ),
}


def get_config(profile: str = 'normal', analysis_level: str = 'standard') -> Config:
    """Gibt Konfiguration zurück."""
    config = PROFILES.get(profile, PROFILES['normal'])
    config.analysis_level = analysis_level
    return config
