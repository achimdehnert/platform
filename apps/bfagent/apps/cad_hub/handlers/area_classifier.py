"""
Flächen-Klassifikator für CAD-Layer.

Kategorisiert Layer in verschiedene Flächentypen:
- GRUNDFLÄCHE (Nutzfläche, Bodenfläche)
- DECKENFLÄCHE
- WANDFLÄCHE
- KONSTRUKTION
- TECHNIK
- IGNORIEREN

Hybrid-Ansatz:
1. Regel-basiert (Whitelists/Blacklists)
2. LLM-Fallback für unsichere Fälle
3. Lernen aus LLM-Entscheidungen
"""
import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

CLASSIFIER_DATA_PATH = Path(__file__).parent.parent / "data" / "area_classifier.json"


class AreaCategory(Enum):
    """Kategorien für Flächentypen."""
    GRUNDFLAECHE = "grundfläche"      # Nutzfläche, Bodenfläche, Räume
    DECKENFLAECHE = "deckenfläche"    # Decken, Deckenbeläge
    WANDFLAECHE = "wandfläche"        # Wände, Fassaden
    KONSTRUKTION = "konstruktion"     # Tragwerk, Fundamente
    TECHNIK = "technik"               # Elektro, Sanitär, Heizung
    EINRICHTUNG = "einrichtung"       # Möbel, Symbole
    ANNOTATION = "annotation"         # Text, Bemaßung, Legende
    IGNORIEREN = "ignorieren"         # Hilfslinien, Viewport
    UNBEKANNT = "unbekannt"           # Nicht klassifiziert


@dataclass
class ClassifierRule:
    """Eine Klassifizierungsregel."""
    keywords: list[str]
    category: AreaCategory
    priority: int = 0  # Höher = wird zuerst geprüft
    description: str = ""


@dataclass 
class LearnedClassification:
    """Gelernte Klassifizierung von LLM."""
    layer_name: str
    layer_normalized: str
    category: str
    confidence: float
    source: str  # "llm", "user", "admin"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> dict:
        return asdict(self)


class AreaClassifier:
    """
    Klassifiziert CAD-Layer in Flächenkategorien.
    
    Strategie:
    1. Exakte Matches (gelernte Klassifizierungen)
    2. Keyword-Regeln (Whitelists pro Kategorie)
    3. LLM-Fallback (optional, für unsichere Fälle)
    4. Lernen: Speichert LLM-Entscheidungen
    """
    
    # Kategorisierte Keyword-Listen
    CATEGORY_RULES: dict[AreaCategory, list[str]] = {
        # GRUNDFLÄCHE - echte Nutzflächen
        AreaCategory.GRUNDFLAECHE: [
            # Deutsch
            "grundfläche", "grundflaeche", "bodenfläche", "bodenflaeche",
            "nutzfläche", "nutzflaeche", "nuf", "nrf",
            "bodenplatte", "bodenplatten",
            "raum", "räume", "raeume", "room",
            "wohnfläche", "wohnflaeche", "wohnraum",
            "geschossfläche", "geschossflaeche",
            # Raumtypen
            "büro", "buero", "office",
            "flur", "corridor", "gang",
            "küche", "kueche", "kitchen",
            "bad", "badezimmer", "bathroom", "wc", "toilette",
            "schlafzimmer", "schlaf", "bedroom",
            "wohnzimmer", "wohn", "living",
            "esszimmer", "essen", "dining",
            "kinderzimmer", "kind",
            "arbeitszimmer", "arbeit",
            "lager", "lagerraum", "storage",
            "keller", "kellerraum", "basement",
            "dachboden", "dachgeschoss", "attic",
            "garage", "carport",
            "terrasse", "balkon", "loggia",
            "eingang", "entrance", "foyer",
            "empfang", "reception",
        ],
        
        # DECKENFLÄCHE
        AreaCategory.DECKENFLAECHE: [
            "decke", "decken", "ceiling",
            "deckenfläche", "deckenflaeche",
            "deckenbelag", "deckenaufbau",
            "deckenkonstruktion",
            "abhangdecke", "abhängedecke",
            "akustikdecke",
        ],
        
        # WANDFLÄCHE  
        AreaCategory.WANDFLAECHE: [
            "wand", "wände", "waende", "wall",
            "wandfläche", "wandflaeche",
            "außenwand", "aussenwand", "exterior",
            "innenwand", "interior",
            "trennwand", "partition",
            "fassade", "facade",
            "sandwichwand", "sandwich",
            "brüstung", "bruestung", "parapet",
        ],
        
        # KONSTRUKTION
        AreaCategory.KONSTRUKTION: [
            "konstruktion", "construction",
            "tragwerk", "struktur", "structure",
            "fundament", "foundation",
            "stütze", "stuetze", "column", "pillar",
            "träger", "traeger", "beam",
            "balken", "joist",
            "bewehrung", "reinforcement",
            "schalung", "formwork",
            "beton", "concrete",
            "stahl", "steel",
            "holzbau", "timber",
        ],
        
        # TECHNIK
        AreaCategory.TECHNIK: [
            "elektro", "electric", "electrical",
            "sanitär", "sanitaer", "sanitary", "plumbing",
            "heizung", "heating", "hvac",
            "lüftung", "lueftung", "ventilation",
            "klima", "climate", "aircon",
            "sprinkler", "brandschutz", "fire",
            "entwässerung", "entwaesserung", "drainage",
            "rohr", "leitung", "pipe",
            "kanal", "duct",
            "schacht", "shaft",
        ],
        
        # EINRICHTUNG
        AreaCategory.EINRICHTUNG: [
            "möbel", "moebel", "furniture",
            "einrichtung", "interior",
            "küchenmöbel", "kuechenmoebel",
            "badmöbel", "badmoebel",
            "schrank", "cabinet",
            "tisch", "table",
            "stuhl", "chair",
            "sofa", "couch",
            "bett", "bed",
            "regal", "shelf",
        ],
        
        # ANNOTATION
        AreaCategory.ANNOTATION: [
            "text", "beschriftung", "annotation", "label",
            "bemaßung", "bemassung", "dimension", "dim",
            "symbol", "symbole",
            "schraffur", "hatch", "pattern",
            "legende", "legend",
            "titel", "title",
            "rahmen", "frame", "border",
            "logo", "stamp",
            "notiz", "note", "comment",
            "ergänzung", "ergaenzung", "supplement",
            "maßstab", "massstab", "scale",
            "north", "nord", "compass",
        ],
        
        # IGNORIEREN
        AreaCategory.IGNORIEREN: [
            "viewport", "defpoints",
            "hilfslinie", "hilfslin", "auxiliary",
            "achse", "axis", "grid",
            "raster", "gridline",
            "schnitt", "section",
            "ansicht", "view", "elevation",
            "detail",
            "0", "layer0",  # Standard-Layer oft ignorieren
        ],
    }
    
    def __init__(self, data_path: Path = None, use_llm: bool = False):
        self.data_path = data_path or CLASSIFIER_DATA_PATH
        self.use_llm = use_llm
        self.learned: dict[str, LearnedClassification] = {}
        self._load()
    
    def _load(self):
        """Lädt gelernte Klassifizierungen."""
        try:
            if self.data_path.exists():
                with open(self.data_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data.get("learned", []):
                        lc = LearnedClassification(**item)
                        self.learned[lc.layer_normalized] = lc
                logger.info(f"[AreaClassifier] Loaded {len(self.learned)} learned classifications")
        except Exception as e:
            logger.warning(f"[AreaClassifier] Could not load: {e}")
    
    def _save(self):
        """Speichert gelernte Klassifizierungen."""
        try:
            self.data_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.data_path, "w", encoding="utf-8") as f:
                json.dump({
                    "version": "1.0",
                    "updated_at": datetime.now().isoformat(),
                    "learned": [lc.to_dict() for lc in self.learned.values()],
                }, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[AreaClassifier] Could not save: {e}")
    
    @staticmethod
    def normalize(name: str) -> str:
        """Normalisiert Layer-Namen für Vergleich."""
        import re
        if not name:
            return ""
        # Lowercase
        normalized = name.lower().strip()
        # Remove numbers at start (like "324 - ")
        normalized = re.sub(r'^\d+[\s\-_\.]*', '', normalized)
        # Remove special chars
        normalized = re.sub(r'[^\w\s]', ' ', normalized)
        # Collapse whitespace
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized
    
    def classify(self, layer_name: str) -> tuple[AreaCategory, float]:
        """
        Klassifiziert einen Layer-Namen.
        
        Returns:
            (Kategorie, Konfidenz 0-1)
        """
        if not layer_name:
            return AreaCategory.IGNORIEREN, 1.0
        
        normalized = self.normalize(layer_name)
        layer_lower = layer_name.lower()
        
        # 1. TEXT-Formatierung erkennen (z.B. \A1;{\pql;)
        if layer_name.startswith("\\") or "{\\p" in layer_name or "\\f" in layer_name:
            return AreaCategory.ANNOTATION, 1.0
        
        # 2. Exaktes Match in gelernten Klassifizierungen
        if normalized in self.learned:
            lc = self.learned[normalized]
            try:
                return AreaCategory(lc.category), lc.confidence
            except ValueError:
                pass
        
        # 3. Keyword-basierte Klassifizierung
        best_category = AreaCategory.UNBEKANNT
        best_score = 0.0
        
        for category, keywords in self.CATEGORY_RULES.items():
            for keyword in keywords:
                if keyword in layer_lower or keyword in normalized:
                    # Längere Keywords = höhere Konfidenz
                    score = len(keyword) / max(len(normalized), 1)
                    score = min(score * 1.5, 0.95)  # Max 0.95 für Regeln
                    
                    if score > best_score:
                        best_score = score
                        best_category = category
        
        if best_category != AreaCategory.UNBEKANNT:
            return best_category, best_score
        
        # 4. LLM-Fallback (wenn aktiviert und unsicher)
        if self.use_llm and best_score < 0.5:
            llm_result = self._classify_with_llm(layer_name)
            if llm_result:
                category, confidence = llm_result
                # Lernen für nächstes Mal
                self.learn(layer_name, category.value, confidence, source="llm")
                return category, confidence
        
        return AreaCategory.UNBEKANNT, 0.0
    
    def _classify_with_llm(self, layer_name: str) -> Optional[tuple[AreaCategory, float]]:
        """
        Klassifiziert mit LLM (falls verfügbar).
        
        Returns:
            (Kategorie, Konfidenz) oder None
        """
        try:
            # Versuche zuerst den existierenden LLM-Client
            try:
                from apps.bfagent.services.llm_client import generate_text
            except ImportError:
                # Fallback: Direkter OpenAI-Aufruf
                import os
                import openai
                
                api_key = os.environ.get("OPENAI_API_KEY")
                if not api_key:
                    logger.debug("[AreaClassifier] No OpenAI API key available")
                    return None
                
                client = openai.OpenAI(api_key=api_key)
                
                def generate_text(prompt, max_tokens=50):
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=max_tokens,
                        temperature=0.1,
                    )
                    return response.choices[0].message.content
            
            prompt = f"""Klassifiziere diesen CAD-Layer-Namen in EINE Kategorie.

Layer-Name: "{layer_name}"

Kategorien:
- grundfläche: Nutzfläche, Bodenfläche, Räume (Büro, Flur, Bad, Küche, etc.)
- deckenfläche: Decken, Deckenbeläge, Deckenaufbauten
- wandfläche: Wände, Fassaden, Außenwände, Innenwände
- konstruktion: Tragwerk, Fundamente, Stützen, Träger
- technik: Elektro, Sanitär, Heizung, Lüftung
- einrichtung: Möbel, Einrichtung
- annotation: Text, Bemaßung, Symbole, Legende, Schraffur
- ignorieren: Hilfslinien, Viewport, Defpoints

Antworte NUR mit dem Kategorienamen (kleingeschrieben), z.B.: grundfläche
Keine Erklärung, nur das eine Wort."""

            response = generate_text(prompt, max_tokens=20)
            if response:
                response_lower = response.strip().lower().replace("ä", "a").replace("ö", "o").replace("ü", "u")
                
                # Mapping für verschiedene Schreibweisen
                category_map = {
                    "grundflache": AreaCategory.GRUNDFLAECHE,
                    "grundfläche": AreaCategory.GRUNDFLAECHE,
                    "deckenflache": AreaCategory.DECKENFLAECHE,
                    "deckenfläche": AreaCategory.DECKENFLAECHE,
                    "wandflache": AreaCategory.WANDFLAECHE,
                    "wandfläche": AreaCategory.WANDFLAECHE,
                    "konstruktion": AreaCategory.KONSTRUKTION,
                    "technik": AreaCategory.TECHNIK,
                    "einrichtung": AreaCategory.EINRICHTUNG,
                    "annotation": AreaCategory.ANNOTATION,
                    "ignorieren": AreaCategory.IGNORIEREN,
                }
                
                for key, cat in category_map.items():
                    if key in response_lower:
                        logger.info(f"[AreaClassifier] LLM: '{layer_name}' → {cat.value}")
                        return cat, 0.85
            
        except Exception as e:
            logger.warning(f"[AreaClassifier] LLM classification failed: {e}")
        
        return None
    
    def learn(self, layer_name: str, category: str, confidence: float = 0.9, source: str = "user"):
        """
        Speichert gelernte Klassifizierung.
        
        Args:
            layer_name: Original Layer-Name
            category: Kategorie-Wert (z.B. "grundfläche")
            confidence: Konfidenz 0-1
            source: Quelle ("user", "llm", "admin")
        """
        normalized = self.normalize(layer_name)
        
        self.learned[normalized] = LearnedClassification(
            layer_name=layer_name,
            layer_normalized=normalized,
            category=category,
            confidence=confidence,
            source=source,
        )
        self._save()
        logger.info(f"[AreaClassifier] Learned: '{layer_name}' → {category}")
    
    def is_floor_area(self, layer_name: str) -> bool:
        """Prüft ob Layer eine Grundfläche/Nutzfläche ist."""
        category, confidence = self.classify(layer_name)
        return category == AreaCategory.GRUNDFLAECHE and confidence > 0.3
    
    def is_excluded(self, layer_name: str) -> bool:
        """Prüft ob Layer ausgeschlossen werden soll."""
        category, _ = self.classify(layer_name)
        return category in [
            AreaCategory.ANNOTATION,
            AreaCategory.IGNORIEREN,
            AreaCategory.EINRICHTUNG,
        ]
    
    def get_stats(self) -> dict:
        """Statistiken über Klassifizierungen."""
        category_counts = {}
        for lc in self.learned.values():
            category_counts[lc.category] = category_counts.get(lc.category, 0) + 1
        
        return {
            "total_learned": len(self.learned),
            "by_category": category_counts,
            "by_source": {
                "llm": sum(1 for lc in self.learned.values() if lc.source == "llm"),
                "user": sum(1 for lc in self.learned.values() if lc.source == "user"),
                "admin": sum(1 for lc in self.learned.values() if lc.source == "admin"),
            },
        }


# Singleton
_classifier: Optional[AreaClassifier] = None

def get_area_classifier(use_llm: bool = False) -> AreaClassifier:
    """Gibt Singleton AreaClassifier zurück."""
    global _classifier
    if _classifier is None:
        _classifier = AreaClassifier(use_llm=use_llm)
    return _classifier
