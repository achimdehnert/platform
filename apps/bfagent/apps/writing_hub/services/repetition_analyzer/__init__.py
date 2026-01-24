"""
Repetition Analyzer - Integriert in BFAgent Lektorat

Stufenweise Analyse-Level:
- basic: Keine ML-Dependencies (Distanz, Phrasen, einfaches MTLD)
- standard: +lexicalrichness (volle MTLD/HD-D)
- advanced: +spaCy (POS-Salienz, Strukturanalyse)
- full: +Ollama Embeddings (Semantische Duplikate)
"""

from .config import Config, get_config, PROFILES
from .analyzer import RepetitionAnalyzer

__all__ = [
    'Config',
    'get_config', 
    'PROFILES',
    'RepetitionAnalyzer',
]

__version__ = '1.0.0'
