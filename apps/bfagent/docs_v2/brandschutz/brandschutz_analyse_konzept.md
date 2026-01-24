# Brandschutz-Experten: Konzeptanalyse & Optimierung

## Executive Summary

Dieses Konzept beschreibt die Erweiterung des Brandschutz-Experten um Analyse-Funktionen für bestehende Brandschutzkonzepte und CAD-Pläne. Das System analysiert hochgeladene Dokumente, identifiziert Schwachstellen und generiert konkrete Handlungsempfehlungen.

**Kernfunktionen:**
- Upload und Analyse von Brandschutzkonzepten (PDF, DOCX)
- CAD-Plan-Analyse (DXF/DWG) für räumliche Brandschutzprüfung
- Automatische Schwachstellen-Erkennung
- Normkonforme Optimierungsvorschläge (LBO, ArbStättV, ASR A2.3)
- Export als strukturierter Prüfbericht

---

## 1. System-Architektur

### 1.1 Übersicht

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    BRANDSCHUTZ-EXPERTE ANALYSEPIPELINE                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────────┐ │
│  │   INPUT     │──▶│  PARSING    │──▶│  ANALYSE    │──▶│    OUTPUT       │ │
│  │             │   │             │   │             │   │                 │ │
│  │ • PDF       │   │ • Text-     │   │ • Norm-     │   │ • Prüfbericht   │ │
│  │ • DOCX      │   │   extraktion│   │   abgleich  │   │ • Optimierung   │ │
│  │ • DXF/DWG   │   │ • CAD-      │   │ • Vollstän- │   │ • Visualisierung│ │
│  │             │   │   analyse   │   │   digkeit   │   │ • Checkliste    │ │
│  └─────────────┘   └─────────────┘   └─────────────┘   └─────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Modul-Struktur

```
brandschutz_experte/
├── __init__.py
├── models/
│   ├── __init__.py
│   ├── document_types.py          # Datenmodelle für Dokumente
│   ├── analysis_result.py         # Analyse-Ergebnisse
│   └── recommendation.py          # Handlungsempfehlungen
├── parsers/
│   ├── __init__.py
│   ├── base_parser.py             # Abstrakte Parser-Klasse
│   ├── pdf_parser.py              # PDF-Extraktion
│   ├── docx_parser.py             # Word-Extraktion
│   └── cad_parser.py              # DXF/DWG-Analyse
├── analyzers/
│   ├── __init__.py
│   ├── base_analyzer.py           # Abstrakte Analyzer-Klasse
│   ├── concept_analyzer.py        # Textbasierte Konzeptanalyse
│   ├── plan_analyzer.py           # CAD-basierte Plananalyse
│   ├── completeness_checker.py    # Vollständigkeitsprüfung
│   └── norm_compliance.py         # Normkonformitätsprüfung
├── knowledge/
│   ├── __init__.py
│   ├── norms.py                   # Normendatenbank (LBO, ASR, etc.)
│   ├── checklists.py              # Prüfchecklisten
│   └── requirements.py            # Anforderungskataloge
├── generators/
│   ├── __init__.py
│   ├── report_generator.py        # Prüfbericht-Erstellung
│   ├── recommendation_engine.py   # Optimierungsvorschläge
│   └── visualization.py           # Plan-Visualisierung
└── cli.py                          # Kommandozeilen-Interface
```

---

## 2. Datenmodelle

### 2.1 Brandschutz-Konzept Struktur

```python
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from enum import Enum
from datetime import date

class BuildingClass(Enum):
    """Gebäudeklassen nach Musterbauordnung"""
    GK1 = "Gebäudeklasse 1"  # freistehend, ≤7m, ≤2 NE
    GK2 = "Gebäudeklasse 2"  # freistehend, ≤7m
    GK3 = "Gebäudeklasse 3"  # ≤7m
    GK4 = "Gebäudeklasse 4"  # ≤13m, ≤400m² NE
    GK5 = "Gebäudeklasse 5"  # sonstige

class RiskLevel(Enum):
    """Risikobewertung"""
    LOW = "gering"
    MEDIUM = "mittel"
    HIGH = "hoch"
    CRITICAL = "kritisch"

class AnalysisStatus(Enum):
    """Status der Analyse"""
    COMPLETE = "vollständig"
    INCOMPLETE = "unvollständig"
    MISSING = "fehlend"
    WARNING = "Hinweis"
    ERROR = "Mangel"

@dataclass
class BuildingInfo:
    """Gebäudeinformationen aus dem Konzept"""
    name: str = ""
    address: str = ""
    building_class: Optional[BuildingClass] = None
    height: Optional[float] = None  # in Metern
    floors_above: Optional[int] = None
    floors_below: Optional[int] = None
    gross_area: Optional[float] = None  # BGF in m²
    usage_types: List[str] = field(default_factory=list)
    special_building: bool = False
    special_building_type: Optional[str] = None

@dataclass
class FireSection:
    """Brandabschnitt"""
    id: str
    name: str
    area: Optional[float] = None
    floors: List[int] = field(default_factory=list)
    fire_resistance_class: str = ""  # z.B. "F90", "REI90"
    description: str = ""

@dataclass
class EscapeRoute:
    """Fluchtweg"""
    id: str
    type: str  # "erster_rw", "zweiter_rw", "notausgang"
    floors_served: List[int] = field(default_factory=list)
    width: Optional[float] = None  # in Metern
    length: Optional[float] = None  # in Metern
    is_smoke_free: bool = False
    has_emergency_lighting: bool = False
    has_safety_signs: bool = False

@dataclass 
class FireProtectionSystem:
    """Brandschutzeinrichtung"""
    type: str  # "BMA", "RWA", "Sprinkler", etc.
    coverage: str  # "vollflächig", "teilweise", "punktuell"
    norm_reference: str = ""
    description: str = ""
    maintenance_interval: Optional[int] = None  # Monate

@dataclass
class FireProtectionConcept:
    """Gesamtes Brandschutzkonzept"""
    # Metadaten
    document_date: Optional[date] = None
    author: str = ""
    version: str = ""
    
    # Gebäude
    building: BuildingInfo = field(default_factory=BuildingInfo)
    
    # Brandschutzmaßnahmen
    fire_sections: List[FireSection] = field(default_factory=list)
    escape_routes: List[EscapeRoute] = field(default_factory=list)
    systems: List[FireProtectionSystem] = field(default_factory=list)
    
    # Extrahierte Inhalte
    raw_text: str = ""
    extracted_sections: Dict[str, str] = field(default_factory=dict)
```

### 2.2 Analyse-Ergebnis Modell

```python
@dataclass
class Finding:
    """Einzelner Befund der Analyse"""
    id: str
    category: str  # "fluchtweg", "brandabschnitt", "technik", etc.
    severity: RiskLevel
    status: AnalysisStatus
    title: str
    description: str
    norm_reference: str = ""
    location: str = ""  # Wo im Dokument/Plan gefunden
    recommendation: str = ""

@dataclass
class AnalysisResult:
    """Gesamtergebnis der Analyse"""
    concept: FireProtectionConcept
    findings: List[Finding] = field(default_factory=list)
    completeness_score: float = 0.0  # 0-100%
    risk_score: float = 0.0  # 0-100
    summary: str = ""
    
    @property
    def critical_findings(self) -> List[Finding]:
        return [f for f in self.findings if f.severity == RiskLevel.CRITICAL]
    
    @property
    def high_risk_findings(self) -> List[Finding]:
        return [f for f in self.findings if f.severity == RiskLevel.HIGH]
```

---

## 3. Implementierungsschritte

### Phase 1: Grundgerüst (Schritt 1-3)

| Schritt | Beschreibung | Aufwand |
|---------|--------------|---------|
| 1.1 | Projektstruktur & Datenmodelle | 1h |
| 1.2 | Base-Parser Klasse | 1h |
| 1.3 | PDF-Parser mit PyMuPDF | 2h |

### Phase 2: Dokumenten-Parser (Schritt 4-6)

| Schritt | Beschreibung | Aufwand |
|---------|--------------|---------|
| 2.1 | DOCX-Parser | 2h |
| 2.2 | CAD-Parser (DXF) | 3h |
| 2.3 | DWG→DXF Konvertierung | 1h |

### Phase 3: Analyse-Engine (Schritt 7-10)

| Schritt | Beschreibung | Aufwand |
|---------|--------------|---------|
| 3.1 | Normendatenbank | 3h |
| 3.2 | Vollständigkeits-Checker | 2h |
| 3.3 | Konzept-Analyzer | 3h |
| 3.4 | Plan-Analyzer (CAD) | 4h |

### Phase 4: Output-Generierung (Schritt 11-13)

| Schritt | Beschreibung | Aufwand |
|---------|--------------|---------|
| 4.1 | Recommendation Engine | 2h |
| 4.2 | Report Generator (DOCX) | 3h |
| 4.3 | CLI & Integration | 2h |

---

**Nächster Schritt:** Möchtest du mit der Implementierung von Phase 1 (Grundgerüst) beginnen?
