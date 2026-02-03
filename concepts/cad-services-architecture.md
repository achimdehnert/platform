# CAD Services - Architektur-Konzept

**Version:** 1.0.0  
**Datum:** 2026-01-29  
**Status:** Review Draft (v1.0)  
**Autor:** Cascade AI  

---

## 1. Executive Summary

Dieses Dokument beschreibt die Architektur für ein **domain-agnostisches CAD-Services Package** auf der Platform-Ebene. Das Package stellt IFC/DXF-Parsing, Element-Normalisierung und Mengenberechnung als wiederverwendbare Services bereit.

**Kernprinzipien:**
- **Separation of Concerns**: Parser-Logik getrennt von Domain-Logik
- **Produktionsstabilität**: Keine Breaking Changes für bestehende BFAgent-Funktionalität
- **SaaS-Ready**: Multi-Tenant-fähig, API-first Design
- **Testbarkeit**: Isolierte Komponenten, Mock-fähig

**Architektur-Entscheidungen (Review-kritisch):**
- **Library-first**: `cad-services` ist zustandslos (kein Cache) und wird als Python-Package integriert.
- **Keine Domain-Logik im Platform Layer**: keine Brandschutz-/ATEX-/DIN-Regeln im Package.
- **Keine MCP-Exposition in Phase 1**: MCP/Server erst, wenn externe Consumer außerhalb des Monorepos bestehen.
- **Keine Async-Parserpflicht**: Parsing ist primär CPU-bound; Async bringt in Phase 1 wenig.
- **CLI Tool (später sinnvoll)**: zur lokalen Analyse/Debugging/Golden-Master-Erzeugung.

---

## 1.1 Scope, Non-Goals und Begriffsdefinitionen

### Scope (Phase 1)
- `cad-services` als **Python-Library** in `platform/packages/`.
- **IFC/DXF importieren** und **normalisieren** (Elements/Properties/Quantities/Minimal-Geometrie-Metadaten).
- **Auditierbarkeit**: `CADParseResult` (Hash, Version, Warnings, Stats).
- **Konfigurierbarkeit**: Mapping-Profile (JSON, versioniert).
- **Berechnungsschicht**: Calculator (Units, computed quantities) getrennt vom Parser.

### Non-Goals (Phase 1)
- Kein Viewer/Rendering.
- Kein Edit/Roundtrip/Export zurück in IFC/DXF.
- Keine Domain-Regeln (Brandschutz/ATEX/DIN/WoFlV/GAEB) im Platform Layer.
- Kein MCP-Server / kein externer Servicebetrieb.
- Kein internes Caching in `cad-services`.

### Begriffe (kurz)
- **Parser**: liest Datei, iteriert Rohdaten, erzeugt `CADParseResult` (ohne Business-Semantik).
- **Extractor**: transformiert Rohdaten zu `CADElement` inkl. Normalisierung.
- **Calculator**: berechnet/ergänzt Quantities (2D/3D/Heuristik), setzt `inputs/formula/confidence`.

### Platform DB-first Konsistenz (Design-Entscheidung)
- `cad-services` bleibt **DB-agnostisch** (Library-first), um auch außerhalb von Django nutzbar zu sein.
- DB-first wird im **Application Layer** umgesetzt (z. B. BFAgent lädt Profile aus DB).
- Dafür definiert `cad-services` ein Repository-Interface; konkrete Implementierungen leben im App-Layer.

---

## 2. Problemstellung

### 2.1 Aktueller Zustand

Der CAD Hub in BFAgent enthält:
- IFC Parser (`ifc_parser.py`, `ifc_complete_parser/`)
- DXF Parser (`dxf_parser.py`, `dxf_analyzer.py`)
- Domain-spezifische Models (Brandschutz, AVB, DIN 277)

**Probleme:**
1. Parser und Domain-Logik vermischt
2. Keine Wiederverwendbarkeit für andere Apps (Risk-Hub, etc.)
3. Quantity-Tracking ohne Herkunft/Methode
4. Hardcodierte Mappings statt konfigurierbarer Profile

### 2.2 Zielzustand

```
┌─────────────────────────────────────────────────────────────┐
│                    PLATFORM LAYER                            │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              cad-services (Package)                  │    │
│  │  - IFC/DXF Parsing (domain-agnostisch)              │    │
│  │  - CADElement Normalisierung                         │    │
│  │  - Quantity Calculation mit Methode/Confidence       │    │
│  │  - Mapping Profile Engine                            │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ pip install / import
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    APPLICATION LAYER                         │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐   │
│  │   BFAgent     │  │   Risk-Hub    │  │  Future App   │   │
│  │   CAD Hub     │  │   Ex-Zonen    │  │               │   │
│  ├───────────────┤  ├───────────────┤  ├───────────────┤   │
│  │ Domain Logic: │  │ Domain Logic: │  │ Domain Logic: │   │
│  │ - Brandschutz │  │ - ATEX        │  │ - ...         │   │
│  │ - DIN 277     │  │ - Gefahrstoff │  │               │   │
│  │ - GAEB/AVA    │  │               │  │               │   │
│  └───────────────┘  └───────────────┘  └───────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Architektur

### 3.1 Package-Struktur

```
platform/packages/cad-services/
├── cad_services/
│   ├── __init__.py              # Public API
│   ├── version.py               # Semantic Versioning
│   │
│   ├── parsers/                 # Format-spezifische Parser
│   │   ├── __init__.py
│   │   ├── base.py              # BaseParser ABC
│   │   ├── ifc_parser.py        # IfcOpenShell-basiert
│   │   └── dxf_parser.py        # ezdxf-basiert
│   │
│   ├── models/                  # Pydantic Data Models
│   │   ├── __init__.py
│   │   ├── element.py           # CADElement
│   │   ├── property.py          # CADProperty
│   │   ├── quantity.py          # CADQuantity
│   │   ├── geometry.py          # BBox, Polygon, Point
│   │   ├── material.py          # CADMaterial
│   │   └── relation.py          # CADRelation
│   │
│   ├── extractors/              # Format → CADElement
│   │   ├── __init__.py
│   │   ├── base.py              # BaseExtractor ABC
│   │   ├── ifc_extractor.py     # IFC → CADElement
│   │   └── dxf_extractor.py     # DXF → CADElement
│   │
│   ├── calculators/             # Mengenberechnung
│   │   ├── __init__.py
│   │   ├── quantity.py          # Länge, Fläche, Volumen
│   │   └── aggregates.py        # Summen, Gruppierung
│   │
│   ├── mapping/                 # Konfigurierbare Mappings
│   │   ├── __init__.py
│   │   ├── profile.py           # MappingProfile
│   │   └── defaults/            # Standard-Profile
│   │       ├── ifc_default.json
│   │       └── dxf_default.json
│   │
│   └── utils/                   # Hilfsfunktionen
│       ├── __init__.py
│       ├── units.py             # Einheiten-Konvertierung
│       └── hash.py              # SHA256 für Dateien
│
├── tests/
│   ├── conftest.py
│   ├── test_parsers/
│   ├── test_extractors/
│   ├── test_calculators/
│   └── fixtures/
│       ├── sample.ifc
│       └── sample.dxf
│
├── pyproject.toml
├── README.md
└── CHANGELOG.md
```

### 3.2 Kern-Datenmodelle (Pydantic)

#### 3.2.1 CADElement

```python
# cad_services/models/element.py
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
from uuid import UUID, uuid4

class ElementCategory(str, Enum):
    """High-level Kategorien (domain-agnostisch)."""
    WALL = "wall"
    DOOR = "door"
    WINDOW = "window"
    SLAB = "slab"
    SPACE = "space"
    COLUMN = "column"
    BEAM = "beam"
    STAIR = "stair"
    ROOF = "roof"
    OPENING = "opening"
    EQUIPMENT = "equipment"
    ZONE = "zone"
    UNKNOWN = "unknown"

class SourceFormat(str, Enum):
    """Quellformat."""
    IFC = "ifc"
    DXF = "dxf"
    DWG = "dwg"

class CADElement(BaseModel):
    """
    Normalisiertes CAD-Element.
    
    Repräsentiert ein Bauelement aus IFC oder DXF in einem
    einheitlichen, domain-agnostischen Format.
    """
    id: UUID = Field(default_factory=uuid4)
    
    # Quelle
    source_format: SourceFormat
    external_id: str  # IFC GUID oder DXF Handle
    
    # Klassifikation
    category: ElementCategory
    element_type: str  # z.B. "IfcWall", "LWPOLYLINE"
    type_name: Optional[str] = None  # z.B. "Außenwand 30cm"
    
    # Identifikation
    name: str = ""
    number: Optional[str] = None
    
    # Räumliche Zuordnung
    storey_id: Optional[str] = None
    storey_name: Optional[str] = None
    space_id: Optional[str] = None
    
    # DXF-spezifisch
    layer: Optional[str] = None
    
    # Properties und Quantities (siehe separate Models)
    properties: list["CADProperty"] = Field(default_factory=list)
    quantities: list["CADQuantity"] = Field(default_factory=list)
    materials: list["CADMaterial"] = Field(default_factory=list)
    
    # Geometrie (minimal)
    geometry: Optional["CADGeometry"] = None

    def get_property(self, name: str, default=None):
        """Convenience accessor for normalized properties."""
        for prop in self.properties:
            if prop.name == name:
                return prop.value
        return default
    
    class Config:
        use_enum_values = True
```

**Explizite Invarianten (hochprior, enforced):**
- `external_id` ist immer gesetzt.
- `source_format` ist konsistent zum Ursprung.
- `CADQuantity.unit` ist konsistent zum `quantity_type`.
- Geometrie ist **optional** – aber wenn vorhanden, muss sie valide sein. Keine stillen Fallbacks.

Empfehlung für Umsetzung: Invarianten via Pydantic-Validatoren erzwingen (positive + negative Tests).

#### 3.2.2 CADProperty

```python
# cad_services/models/property.py
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel

class PropertySource(str, Enum):
    """Herkunft der Property."""
    IFC_PSET = "ifc_pset"           # IFC PropertySet
    IFC_QUANTITY = "ifc_quantity"   # IFC QuantitySet
    IFC_ATTRIBUTE = "ifc_attribute" # IFC Direktattribut
    DXF_LAYER = "dxf_layer"         # DXF Layer-Name
    DXF_BLOCK_ATTR = "dxf_block_attr"  # DXF Block-Attribut
    DXF_XDATA = "dxf_xdata"         # DXF Extended Data
    DXF_TEXT = "dxf_text"           # Extrahiert aus Text
    COMPUTED = "computed"           # Berechnet
    MAPPED = "mapped"               # Aus Mapping-Profil

class CADProperty(BaseModel):
    """
    Einzelne Property eines CAD-Elements.
    
    Speichert Herkunft und Original-Kontext für Nachvollziehbarkeit.
    """
    name: str                       # Normalisierter Name
    value: Any                      # Wert (string, number, bool)
    
    # Herkunft
    source: PropertySource
    source_name: Optional[str] = None  # z.B. "Pset_WallCommon"
    original_name: Optional[str] = None  # Original-Key falls gemappt
    
    # Typisierung
    data_type: str = "string"       # string, integer, real, boolean
    unit: Optional[str] = None      # Einheit falls numerisch
    
    class Config:
        use_enum_values = True
```

#### 3.2.3 CADQuantity

```python
# cad_services/models/quantity.py
from decimal import Decimal
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

class QuantityType(str, Enum):
    """Typ der Mengenangabe."""
    LENGTH = "length"
    AREA = "area"
    VOLUME = "volume"
    COUNT = "count"
    HEIGHT = "height"
    WIDTH = "width"
    THICKNESS = "thickness"
    PERIMETER = "perimeter"
    WEIGHT = "weight"

class QuantityMethod(str, Enum):
    """Berechnungsmethode - KRITISCH für Nachvollziehbarkeit."""
    IFC_QUANTITY = "ifc_quantity"       # Aus IFC QuantitySet
    IFC_ATTRIBUTE = "ifc_attribute"     # Aus IFC Attribut
    COMPUTED_GEOMETRY = "computed_geometry"  # Aus 3D-Geometrie berechnet
    COMPUTED_2D = "computed_2d"         # Aus 2D-Geometrie (DXF)
    COMPUTED_HEURISTIC = "computed_heuristic"  # Heuristik (z.B. Fläche * Höhe)
    MANUAL = "manual"                   # Manuell eingegeben

class CADQuantity(BaseModel):
    """
    Mengenangabe mit Herkunft und Konfidenz.
    
    WICHTIG: Jede Quantity dokumentiert ihre Berechnungsmethode,
    damit Anwender die Zuverlässigkeit einschätzen können.
    """
    quantity_type: QuantityType
    value: Decimal
    unit: str                          # m, m², m³, Stk, kg
    
    # Methode und Konfidenz
    method: QuantityMethod
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    
    # Nachvollziehbarkeit
    source_name: Optional[str] = None  # z.B. "Qto_WallBaseQuantities"
    inputs: Optional[dict] = None      # Eingabewerte für Berechnung
    formula: Optional[str] = None      # Formel falls berechnet
    
    class Config:
        use_enum_values = True
```

**Invarianten (merge-blocking):**
- `method` ist immer gesetzt.
- `confidence` ist immer 0..1.
- Units sind passend zum `quantity_type` (z. B. area → m²).
- Für berechnete Quantities gilt: `inputs` + `formula` müssen gesetzt sein.

#### 3.2.4 CADGeometry

```python
# cad_services/models/geometry.py
from typing import Optional
from pydantic import BaseModel

class Point3D(BaseModel):
    """3D-Punkt."""
    x: float
    y: float
    z: float = 0.0

class BoundingBox(BaseModel):
    """Axis-Aligned Bounding Box."""
    min_point: Point3D
    max_point: Point3D
    
    @property
    def width(self) -> float:
        return self.max_point.x - self.min_point.x
    
    @property
    def depth(self) -> float:
        return self.max_point.y - self.min_point.y
    
    @property
    def height(self) -> float:
        return self.max_point.z - self.min_point.z

class CADGeometry(BaseModel):
    """
    Minimale Geometrie-Repräsentation.
    
    Nur für Zuordnung und Plausibilität, NICHT für Rendering.
    """
    bbox: Optional[BoundingBox] = None
    centroid: Optional[Point3D] = None
    
    # 2D Footprint (für Räume, Zonen)
    footprint_points: Optional[list[Point3D]] = None
    footprint_area: Optional[float] = None
```

#### 3.2.5 CADParseResult (Batch-Kontext/Audit)

**Motivation:** Iterator/Listen von Elementen verlieren wichtigen Kontext (Hash, Parser-Version, Warnings, Timing).

```python
# cad_services/models/parse_result.py
from pydantic import BaseModel, Field

class CADWarning(BaseModel):
    code: str
    message: str
    element_external_id: str | None = None


class CADParseStatistics(BaseModel):
    total_elements: int = 0
    elements_by_category: dict[str, int] = Field(default_factory=dict)
    warnings_count: int = 0

    parse_duration_ms: int = 0
    extract_duration_ms: int = 0

    file_size_bytes: int = 0
    memory_peak_mb: float | None = None

    ifc_schema: str | None = None
    ifc_application: str | None = None


class CADParseResult(BaseModel):
    file_hash: str
    source_format: SourceFormat
    parser_version: str
    profile_name: str | None = None
    profile_version: str | None = None

    elements: list[CADElement] = Field(default_factory=list)
    warnings: list[CADWarning] = Field(default_factory=list)
    statistics: CADParseStatistics = Field(default_factory=CADParseStatistics)
```

### 3.3 Parser-Architektur

**Review-Feinschnitt Verantwortlichkeiten (SoC, Governance):**
- **Parser**: Datei lesen + rohe Entitäten iterieren ("dumm", stabil, austauschbar).
- **Extractor**: Normalisierung (Mapping/Category/Properties/Quantities aus Rohdaten).
- **Calculator**: Berechnung (Geometrie- und Heuristik-basierte Quantities, Aggregates).
- **Domain-App**: Bewertung/Regeln/Findings.

#### 3.3.1 BaseParser (Abstract)

```python
# cad_services/parsers/base.py
from abc import ABC, abstractmethod
from pathlib import Path
from ..models import CADParseResult

class BaseParser(ABC):
    """
    Abstrakte Basisklasse für CAD-Parser.
    
    Definiert das Interface für alle Format-spezifischen Parser.
    """

    max_file_size_mb: int = 500
    
    @abstractmethod
    def parse(self, file_path: Path) -> CADParseResult:
        """
        Parst eine CAD-Datei und liefert normalisierte Elemente.
        
        Args:
            file_path: Pfad zur CAD-Datei
            
        Returns:
            CADParseResult: inkl. Elemente + Audit-Kontext
        """
        pass
    
    @abstractmethod
    def get_metadata(self, file_path: Path) -> dict:
        """
        Extrahiert Metadaten ohne vollständiges Parsing.
        
        Returns:
            dict mit schema, application, element_counts, etc.
        """
        pass
    
    @abstractmethod
    def validate(self, file_path: Path) -> tuple[bool, list[str]]:
        """
        Validiert eine CAD-Datei.

        Returns:
            (is_valid, error_messages)
        """
        pass
```

### 3.4 Security/Resource-Limits

#### Pfadvalidierung (Helper, App-/Job-Layer Pflicht):

```python
# cad_services/utils/path_validation.py
from pathlib import Path
from ..exceptions import CADSecurityError


def validate_file_path(file_path: Path, allowed_extensions: set[str]) -> Path:
    resolved = file_path.resolve()
    if resolved.suffix.lower() not in allowed_extensions:
        raise CADSecurityError(
            code="INVALID_EXTENSION",
            message=f"Erlaubt: {allowed_extensions}, erhalten: {resolved.suffix}",
        )
    if resolved.is_symlink():
        raise CADSecurityError(code="SYMLINK_NOT_ALLOWED", message="Symlinks sind nicht erlaubt")
    return resolved
```

#### 3.4.1 Observability Hooks (Phase 1)

**Ziel:** `cad-services` bleibt neutral, bietet aber definierte Hooks für strukturierte Events und optionale Metrics.

```python
# cad_services/observability.py
from dataclasses import dataclass
from typing import Protocol


class CADMetricsCollector(Protocol):
    def record_parse_duration(self, source_format: str, duration_ms: int) -> None: ...
    def record_element_count(self, source_format: str, category: str, count: int) -> None: ...
    def record_warning(self, source_format: str, warning_code: str) -> None: ...


@dataclass
class ParseEvent:
    event_type: str  # "parse_started" | "parse_completed" | "parse_failed"
    file_hash: str
    source_format: str
    duration_ms: int | None = None
    element_count: int | None = None
    warning_count: int | None = None
    error_code: str | None = None
```

#### 3.3.2 IFCParser

```python
# cad_services/parsers/ifc_parser.py
from pathlib import Path
from typing import Optional
from .base import BaseParser
from ..models import CADParseResult, CADElement, CADProperty, CADQuantity, ElementCategory

class IFCParser(BaseParser):
    """
    IFC Parser basierend auf IfcOpenShell.
    
    Unterstützt: IFC2X3, IFC4, IFC4X1, IFC4X2, IFC4X3
    """
    
    # Mapping IFC-Typen → ElementCategory
    TYPE_MAPPING = {
        "IfcWall": ElementCategory.WALL,
        "IfcWallStandardCase": ElementCategory.WALL,
        "IfcDoor": ElementCategory.DOOR,
        "IfcWindow": ElementCategory.WINDOW,
        "IfcSlab": ElementCategory.SLAB,
        "IfcSpace": ElementCategory.SPACE,
        "IfcColumn": ElementCategory.COLUMN,
        "IfcBeam": ElementCategory.BEAM,
        "IfcStair": ElementCategory.STAIR,
        "IfcRoof": ElementCategory.ROOF,
        "IfcZone": ElementCategory.ZONE,
        # ... weitere
    }
    
    def __init__(self, extract_geometry: bool = False):
        """
        Args:
            extract_geometry: Ob BBox/Centroid berechnet werden soll
                             (Performance-Impact!)
        """
        self.extract_geometry = extract_geometry
        self._ifc = None
        self._unit_scale = 1.0
    
    def parse(self, file_path: Path) -> CADParseResult:
        """Parst IFC und liefert CADParseResult."""
        import ifcopenshell

        from ..exceptions import CADParseError, CADResourceError

        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        if file_size_mb > self.max_file_size_mb:
            raise CADResourceError(
                code="FILE_TOO_LARGE",
                message=f"Max {self.max_file_size_mb}MB, Datei hat {file_size_mb:.1f}MB",
                suggestion="Datei aufteilen oder Import im Job-Layer ausführen",
            )
        
        try:
            self._ifc = ifcopenshell.open(str(file_path))
        except FileNotFoundError as e:
            raise CADParseError(code="FILE_NOT_FOUND", message="Datei nicht gefunden", file_path=str(file_path)) from e
        except PermissionError as e:
            raise CADParseError(code="FILE_ACCESS_DENIED", message="Kein Zugriff auf Datei", file_path=str(file_path)) from e
        except Exception as e:
            raise CADParseError(code="IFC_PARSE_FAILED", message=f"Ungültige IFC-Datei: {e}", file_path=str(file_path)) from e
        self._unit_scale = self._get_unit_scale()
        
        # Hinweis: Parser liefert Rohdaten, Normalisierung im Extractor.
        # In Phase 1 kann das noch als "combined" Implementierung starten,
        # Ziel ist aber: Parser/Extractor strikt trennen.
    
    def _extract_properties(self, element) -> list[CADProperty]:
        """Extrahiert rohe PropertySets eines Elements (keine Normalisierung hier)."""
        properties = []
        
        for pset in element.IsDefinedBy:
            if pset.is_a("IfcRelDefinesByProperties"):
                pset_def = pset.RelatingPropertyDefinition
                if pset_def.is_a("IfcPropertySet"):
                    for prop in pset_def.HasProperties:
                        properties.append(CADProperty(
                            name=prop.Name,
                            value=self._get_property_value(prop),
                            source="ifc_pset",
                            source_name=pset_def.Name,
                        ))
        
        return properties
    
    def _extract_quantities(self, element) -> list[CADQuantity]:
        """Extrahiert rohe QuantitySets eines Elements (method=IFC_QUANTITY)."""
        quantities = []
        
        for qto in element.IsDefinedBy:
            if qto.is_a("IfcRelDefinesByProperties"):
                qto_def = qto.RelatingPropertyDefinition
                if qto_def.is_a("IfcElementQuantity"):
                    for q in qto_def.Quantities:
                        quantities.append(self._parse_quantity(q, qto_def.Name))
        
        return quantities
```

#### 3.3.3 DXFParser

```python
# cad_services/parsers/dxf_parser.py
from pathlib import Path
from typing import Optional
import ezdxf
from .base import BaseParser
from ..models import CADParseResult, CADElement, CADProperty, ElementCategory
from ..mapping import MappingProfile

class DXFParser(BaseParser):
    """
    DXF Parser basierend auf ezdxf.
    
    Parser ist "dumm": extrahiert Rohdaten. Semantik/Regex nur über Profile/Extractor.
    """
    
    def __init__(self, mapping_profile: Optional[MappingProfile] = None):
        """
        Args:
            mapping_profile: Optionales Mapping-Profil für Layer→Typ
        """
        self.profile = mapping_profile or MappingProfile.default()
    
    def parse(self, file_path: Path) -> CADParseResult:
        """Parst DXF und liefert CADParseResult."""
        doc = ezdxf.readfile(str(file_path))
        msp = doc.modelspace()
        
        # Hinweis: entity → raw record; Normalisierung/Mapping im Extractor.
    
    def _entity_to_element(self, entity) -> Optional[CADElement]:
        """Konvertiert DXF-Entity zu CADElement."""
        layer = entity.dxf.layer
        
        # Kategorie aus Mapping-Profil
        category = self.profile.get_category_for_layer(layer)
        
        if entity.dxftype() == "INSERT":
            return self._parse_block_insert(entity, category)
        elif entity.dxftype() == "LWPOLYLINE":
            return self._parse_polyline(entity, category)
        elif entity.dxftype() in ("TEXT", "MTEXT"):
            return self._parse_text(entity)
        # ... weitere
        
        return None
    
    # Wichtig: keine Domain-Regex im Parser.
    # TEXT/MTEXT wird als rohe Property gespeichert, z.B. CADProperty(name="raw_text", source=DXF_TEXT, ...)
    # Die Auswertung (FireRating/ExZone/...) erfolgt in MappingProfile oder in einem konfigurierbaren Extractor-Hook.
```

### 3.4 Mapping-Profile

```python
# cad_services/mapping/profile.py
from pathlib import Path
from typing import Optional
from functools import cached_property
import re
import json
from pydantic import BaseModel
from ..models import ElementCategory

class LayerMapping(BaseModel):
    """Mapping eines Layers zu einer Kategorie."""
    pattern: str  # Regex oder exakter Name
    category: ElementCategory
    properties: dict = {}  # Zusätzliche Properties

class MappingProfile(BaseModel):
    """
    Konfigurierbares Mapping-Profil.
    
    Ermöglicht kundenspezifische Konfiguration ohne Code-Änderung.
    """
    name: str
    version: str = "1.0"
    
    # Layer → Kategorie
    layer_mappings: list[LayerMapping] = []
    
    # Property-Key Normalisierung
    property_aliases: dict[str, str] = {}  # {"Feuerwiderstand": "FireRating"}
    
    # Einheiten
    default_length_unit: str = "m"
    default_area_unit: str = "m²"
    
    @classmethod
    def default(cls) -> "MappingProfile":
        """Standard-Profil für deutsche CAD-Pläne."""
        return cls(
            name="default_de",
            layer_mappings=[
                LayerMapping(pattern=r"WAND.*", category=ElementCategory.WALL),
                LayerMapping(pattern=r"MAUER.*", category=ElementCategory.WALL),
                LayerMapping(pattern=r"FENSTER.*", category=ElementCategory.WINDOW),
                LayerMapping(pattern=r"TUER.*", category=ElementCategory.DOOR),
                LayerMapping(pattern=r"DOOR.*", category=ElementCategory.DOOR),
                LayerMapping(pattern=r"RAUM.*", category=ElementCategory.SPACE),
                LayerMapping(pattern=r"SPACE.*", category=ElementCategory.SPACE),
                LayerMapping(pattern=r"EX[-_]?ZONE.*", category=ElementCategory.ZONE),
            ],
            property_aliases={
                "Feuerwiderstand": "FireRating",
                "Brandschutzklasse": "FireRating",
                "Raumname": "Name",
                "Raumnummer": "Number",
            }
        )
    
    @classmethod
    def from_json(cls, path: Path) -> "MappingProfile":
        """Lädt Profil aus JSON-Datei."""
        with open(path) as f:
            return cls(**json.load(f))

    @cached_property
    def _compiled_patterns(self) -> list[tuple[re.Pattern, ElementCategory]]:
        """Kompiliert Regex Patterns einmalig (Performance bei vielen Entities)."""
        return [(re.compile(m.pattern, re.IGNORECASE), m.category) for m in self.layer_mappings]
    
    def get_category_for_layer(self, layer: str) -> ElementCategory:
        """Ermittelt Kategorie für einen Layer."""
        for pattern, category in self._compiled_patterns:
            if pattern.match(layer):
                return category
        return ElementCategory.UNKNOWN
```

### 3.5 MappingProfile Repository Interface (DB-first im App-Layer)

`cad-services` bleibt DB-agnostisch, stellt aber ein Interface bereit, damit Apps (z. B. BFAgent) Profile **aus DB** laden können.

```python
# cad_services/repositories/base.py
from abc import ABC, abstractmethod
from ..mapping import MappingProfile


class MappingProfileRepository(ABC):
    @abstractmethod
    def get_by_name(self, name: str) -> MappingProfile:
        raise NotImplementedError

    @abstractmethod
    def get_default(self) -> MappingProfile:
        raise NotImplementedError
```

```python
# cad_services/repositories/file.py
from pathlib import Path
from .base import MappingProfileRepository
from ..mapping import MappingProfile


class FileProfileRepository(MappingProfileRepository):
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir

    def get_by_name(self, name: str) -> MappingProfile:
        return MappingProfile.from_json(self.base_dir / f"{name}.json")

    def get_default(self) -> MappingProfile:
        return MappingProfile.default()
```

---

## 4. Integration in BFAgent

### 4.1 Migrationsstrategie (Produktionsstabilität!)

**Phase 1: Parallel-Betrieb (2 Wochen)**
- `cad-services` als optionale Dependency
- Bestehende Parser bleiben aktiv
- Feature-Flag für neuen Parser

```python
# bfagent/apps/cad_hub/services/cad_analyzer.py
from django.conf import settings

if settings.USE_CAD_SERVICES_V2:
    from cad_services.parsers import IFCParser
else:
    from .ifc_parser import IFCParserService as IFCParser
```

**Phase 2: Validierung (1 Woche)**
- Vergleich alte vs. neue Parser-Ergebnisse
- Automatisierte Diff-Tests
- Manuelle Stichproben

**Phase 3: Umstellung (1 Woche)**
- Feature-Flag aktivieren
- Alte Parser als Fallback behalten
- Monitoring

**Phase 4: Cleanup (nach 1 Monat)**
- Alte Parser entfernen
- Dokumentation aktualisieren

### 4.2 Domain-spezifische Erweiterung

```python
# bfagent/apps/cad_hub/services/brandschutz_analyzer.py
from cad_services.models import CADElement, CADProperty
from dataclasses import dataclass
from typing import List

@dataclass
class BrandschutzFinding:
    """Domain-spezifisches Finding."""
    rule_code: str
    severity: int  # 1=Info, 2=Warning, 3=Error
    element_id: str
    message: str
    details: dict = None

class BrandschutzAnalyzer:
    """
    Brandschutz-spezifische Analyse.
    
    Nutzt cad-services für Parsing, fügt Domain-Logik hinzu.
    """
    
    RULES = {
        "BS001": {
            "name": "Feuerwiderstand fehlt",
            "severity": 3,
            "applies_to": ["wall", "door"],
        },
        "BS002": {
            "name": "Brandabschnitt nicht zugeordnet",
            "severity": 2,
            "applies_to": ["space"],
        },
        # ... weitere Regeln
    }
    
    def analyze(self, elements: List[CADElement]) -> List[BrandschutzFinding]:
        """Führt Brandschutz-Analyse durch."""
        findings = []
        
        for element in elements:
            findings.extend(self._check_fire_rating(element))
            findings.extend(self._check_zone_assignment(element))
        
        return findings
    
    def _check_fire_rating(self, element: CADElement) -> List[BrandschutzFinding]:
        """Prüft ob Feuerwiderstand vorhanden."""
        if element.category not in ["wall", "door"]:
            return []
        
        fire_rating = element.get_property("FireRating")
        if not fire_rating:
            return [BrandschutzFinding(
                rule_code="BS001",
                severity=3,
                element_id=element.external_id,
                message=f"{element.name}: Feuerwiderstand fehlt",
            )]
        
        return []
```

---

## 5. API Design

### 5.1 Public API (cad-services)

```python
# cad_services/__init__.py
"""
CAD Services - Domain-agnostisches CAD Parsing.

Beispiel:
    from cad_services import IFCParser, DXFParser, MappingProfile
    from pathlib import Path
    
    parser = IFCParser()
    result = parser.parse(Path("model.ifc"))
    for element in result.elements:
        print(element.category, element.name)
"""

from .parsers import IFCParser, DXFParser
from .models import (
    CADElement,
    CADProperty,
    CADQuantity,
    CADGeometry,
    ElementCategory,
    QuantityMethod,
)
from .mapping import MappingProfile
from .calculators import QuantityCalculator

__all__ = [
    # Parsers
    "IFCParser",
    "DXFParser",
    # Models
    "CADElement",
    "CADProperty",
    "CADQuantity",
    "CADGeometry",
    "ElementCategory",
    "QuantityMethod",
    # Mapping
    "MappingProfile",
    # Calculators
    "QuantityCalculator",
]

__version__ = "0.1.0"
```

### 5.2 Verwendung in BFAgent

```python
# Beispiel: IFC analysieren
from cad_services import IFCParser, MappingProfile
from pathlib import Path

# Parser mit Custom-Profil
profile = MappingProfile.from_json(Path("kunde_xyz_profile.json"))
parser = IFCParser()

# Parsen
parse_result = parser.parse(Path("model.ifc"))
elements = parse_result.elements

# Domain-Analyse
from apps.cad_hub.services import BrandschutzAnalyzer
analyzer = BrandschutzAnalyzer()
findings = analyzer.analyze(elements)

# Speichern in DB
from apps.cad_hub.models import BrandschutzMangel
for finding in findings:
    BrandschutzMangel.objects.create(
        pruefung=pruefung,
        regel_code=finding.rule_code,
        schweregrad=finding.severity,
        element_guid=finding.element_id,
        beschreibung=finding.message,
    )
```

---

## 6. Testing-Strategie

### 6.1 Unit Tests (cad-services)

```python
# tests/test_parsers/test_ifc_parser.py
import pytest
from pathlib import Path
from cad_services import IFCParser, ElementCategory

@pytest.fixture
def sample_ifc():
    return Path(__file__).parent.parent / "fixtures" / "sample.ifc"

def test_parse_walls(sample_ifc):
    parser = IFCParser()
    result = parser.parse(sample_ifc)
    elements = result.elements
    
    walls = [e for e in elements if e.category == ElementCategory.WALL]
    assert len(walls) > 0
    
    for wall in walls:
        assert wall.external_id  # IFC GUID
        assert wall.source_format == "ifc"

def test_quantity_has_method(sample_ifc):
    """Jede Quantity muss eine Methode haben."""
    parser = IFCParser()
    result = parser.parse(sample_ifc)
    elements = result.elements
    
    for element in elements:
        for qty in element.quantities:
            assert qty.method is not None
            assert qty.confidence >= 0.0
            assert qty.confidence <= 1.0
```

**Ergänzung (Review): Golden-Master / Snapshot Tests (Pflicht)**
- Gleiches IFC/DXF + gleiches Profil → gleiches Normalisat (stabiler JSON-Dump).
- Snapshot/Schema-Stabilität: Änderungen sind erklärpflichtig (Changelog/PR).
- Diff-Harness: alt vs. neu Parserergebnisse (counts + stichprobenartige Feldvergleiche, Reihenfolge tolerant).

### 6.2 Integration Tests (BFAgent)

```python
# bfagent/apps/cad_hub/tests/test_brandschutz_analyzer.py
import pytest
from cad_services import CADElement, ElementCategory
from apps.cad_hub.services import BrandschutzAnalyzer

def test_missing_fire_rating_finding():
    """Wand ohne Feuerwiderstand erzeugt Finding."""
    wall = CADElement(
        source_format="ifc",
        external_id="abc123",
        category=ElementCategory.WALL,
        element_type="IfcWall",
        name="Außenwand",
        properties=[],  # Kein FireRating!
    )
    
    analyzer = BrandschutzAnalyzer()
    findings = analyzer.analyze([wall])
    
    assert len(findings) == 1
    assert findings[0].rule_code == "BS001"
    assert findings[0].severity == 3
```

---

## 7. Deployment & Versionierung

### 7.1 Semantic Versioning

- **MAJOR**: Breaking Changes (API-Änderungen)
- **MINOR**: Neue Features (rückwärtskompatibel)
- **PATCH**: Bugfixes

### 7.2 Release-Prozess

1. Feature-Branch → `develop`
2. Tests grün → Merge
3. Release-Branch → Version bump
4. Tag → PyPI/GHCR publish
5. BFAgent: Dependency Update

### 7.3 Dependency in BFAgent

```toml
# bfagent/pyproject.toml
[project.dependencies]
cad-services = ">=0.1.0,<1.0.0"  # Pinned auf Minor
```

---

## 8. Risiken & Mitigationen

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|--------|------------|
| IfcOpenShell-Inkompatibilität | Mittel | Hoch | Version pinnen, Tests |
| Performance bei großen IFC | Mittel | Mittel | Streaming-Parser, Lazy Loading |
| Mapping-Profile unvollständig | Hoch | Niedrig | Default-Profile, Fallback |
| Breaking Changes | Niedrig | Hoch | Semantic Versioning, Deprecation Warnings |

---

## 8.1 Security & Threat Model (Phase 1, merge-blocking)

- **Path Traversal**: `cad-services` selbst nimmt `Path` entgegen; im App-/Job-Layer sind Pfade strikt zu validieren (Whitelist Extensions, keine Symlinks).
- **Resource Exhaustion**: maximale Dateigröße, Geometrie optional (Default aus), klare Fehlercodes (`CADResourceError`).
- **Sensitive Data**: keine Raw-File-Contents in Logs; nur Hash/Metadaten.

---

## 9. Offene Fragen (Review)

1. **MCP-Integration**: Empfehlung Phase 1: **Nein** (library-first). Server später.
2. **Geometrie-Tiefe**: Geometrie ist optional und muss messbar sein (timings), Default: minimal.
3. **Async-Support**: Empfehlung Phase 1: **Nein**.
4. **Caching**: `cad-services` ist zustandslos; Caching gehört in App/Job Layer.

---

## 10. Nächste Schritte

Nach Freigabe dieses Konzepts:

1. [ ] Package-Struktur erstellen
2. [ ] Pydantic Models implementieren
3. [ ] IFC Parser migrieren
4. [ ] DXF Parser migrieren
5. [ ] Tests schreiben
6. [ ] BFAgent-Integration
7. [ ] Dokumentation

---

## 11. Roadmap (Sprint-fähig, production-safety)

**Leitplanken / Definition of Done (für alle Milestones):**
- Keine Silent-Fallbacks: Fehler/Warnungen explizit.
- Invarianten enforced und getestet (inkl. negative Pfade).
- Reproduzierbarkeit: Golden Master / Snapshot.
- Messbarkeit: `CADParseResult.statistics` enthält counts + duration.

### Milestone 0 — Foundations (0.5–1 Sprint)
- Package Skeleton & CI
- `pyproject.toml` mit Abhängigkeiten (IfcOpenShell/ezdxf/pydantic)
- `version.py` / Changelog / Smoke Tests
- Exceptions (`cad_services/exceptions.py`) + Pfadvalidierung Helper
- Minimal Observability Hook (structured logging Interface)

### Milestone 1 — Kernmodell & Contracts (1 Sprint)
- Pydantic Models + Invarianten
- `CADParseResult` + Warning-Contract
- `CADParseStatistics` (typed) statt dict
- Snapshot/Schema Tests + Negative Tests für Invarianten
- Repository-Interface für Mapping Profiles (DB-first im App-Layer)

### Milestone 2 — IFC Migration (1–2 Sprints)
- Parser/Extractor Schichtung (IFC)
- Roh-Quantities (`method=IFC_QUANTITY`), keine Geometrie default
- Diff-Harness alt vs. neu

### Milestone 3 — DXF Migration (1–2 Sprints)
- MappingProfile Engine (Schema, Versionierung, Regex compiled cache)
- DXF Parser: roh, keine Domain-Regex
- Extractor Hook / Profile Regeln für Text-Semantik

### Milestone 4 — Calculator Layer (1 Sprint)
- Unit-Konvertierung
- Computed Quantities (2D/Geometry/Heuristic) + formula/inputs
- Transparente Confidence-Scoring Regeln

### Milestone 5 — BFAgent Integration & Parallelbetrieb (1–2 Sprints)
- Feature Flag `USE_CAD_SERVICES_V2`
- Shadow Mode (beide Parser laufen, nur einer aktiv)
- Logging/Metrics: duration, element_count, warning_count, diff_score(optional)
- Rollback: Flag aus → sofort altes Verhalten

### Milestone 6 — Cleanup & Hardening
- Deprecation + Migration Guide
- Version-Policy scharf stellen
- Alte Parser entfernen oder klar deprecated

---

## 12. PR-Checklist (merge-blocking)

### A. Architektur & Grenzen
- Parser/Extractor/Calculator Grenzen eingehalten.
- Keine Domain-Logik im `cad-services`.
- Public API Änderungen bewusst (Breaking? → MAJOR + Notes).

### B. Datenmodell & Invarianten
- Neue Felder haben klare Semantik.
- Invarianten enforced.
- `CADQuantity`: method/confidence/unit/inputs/formula Regeln eingehalten.

### C. Fehler, Warnings, Observability
- Keine Silent-Fallbacks.
- Parser liefern `CADParseResult` inkl. warnings/statistics.

### D. Tests (Pflicht)
- Unit-Tests + negative Pfade.
- Golden-Master/Snapshot aktualisiert und erklärt.
- Diff-Harness Test (wenn Parser betroffen).

### E. Performance & Ressourcen
- Kein unnötiges O(N²) in Hot Paths.
- Regex nicht pro Entity neu kompilieren.
- Geometrie-Extraktion optional und dokumentiert.

### F. Versionierung & Release
- Version bump korrekt.
- Changelog Eintrag vorhanden.
- Dependencies kompatibel dokumentiert (IfcOpenShell Version!).

### G. Security & SaaS-Readiness
- Keine unsafe file handling (Traversal etc.).
- Keine sensitiven Daten in Logs.
- File-Size Limits aktiv (oder bewusst im App-/Job-Layer enforced und dokumentiert).


---

**Ende des Konzeptdokuments**
