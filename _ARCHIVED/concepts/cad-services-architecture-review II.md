# 🔍 Architektur-Review: CAD Services

**Dokument:** `cad-services-architecture.md` v1.0.0  
**Reviewer:** Senior IT-Architekt  
**Datum:** 2026-01-29  
**Status:** Review abgeschlossen

---

## 📊 Gesamtbewertung

| Kategorie | Bewertung | Kommentar |
|-----------|-----------|-----------|
| **Architektur-Konzept** | ⭐⭐⭐⭐ | Solide Grundstruktur, klare Layer |
| **Platform-Konsistenz** | ⭐⭐⭐ | Teilweise Abweichungen von DB-First |
| **Datenmodell** | ⭐⭐⭐⭐ | Gut durchdacht, kleine Lücken |
| **Observability** | ⭐⭐⭐⭐ | Gute Ansätze, Details fehlen |
| **Sicherheit** | ⭐⭐ | Unterbelichtet |
| **Vollständigkeit** | ⭐⭐⭐ | Kritische Aspekte fehlen |

---

## 🔴 Kritische Schwachstellen (Blocker)

### 1. Fehlende Fehlerbehandlung im Parser-Layer

**Problem:** Die Parser-Implementierung zeigt kein Exception-Handling für korrupte/malformed Dateien.

```python
# AKTUELL (Zeile 522-528)
def parse(self, file_path: Path) -> CADParseResult:
    import ifcopenshell
    self._ifc = ifcopenshell.open(str(file_path))  # Was passiert bei CorruptFileError?
```

**Empfehlung:**

```python
def parse(self, file_path: Path) -> CADParseResult:
    """Parst IFC und liefert CADParseResult."""
    import ifcopenshell
    from ifcopenshell.file import IfcOpenShellError
    
    warnings: list[CADWarning] = []
    
    try:
        self._ifc = ifcopenshell.open(str(file_path))
    except IfcOpenShellError as e:
        raise CADParseError(
            code="IFC_PARSE_FAILED",
            message=f"Ungültige IFC-Datei: {e}",
            file_path=str(file_path),
        ) from e
    except FileNotFoundError:
        raise CADParseError(code="FILE_NOT_FOUND", ...)
    except PermissionError:
        raise CADParseError(code="FILE_ACCESS_DENIED", ...)
```

---

### 2. Path Traversal Vulnerability

**Problem:** Keine Validierung der Dateipfade.

```python
# AKTUELL - Kein Schutz
parser.parse(Path(user_input))  # Potential für "../../../etc/passwd"
```

**Empfehlung:**

```python
# cad_services/utils/path_validation.py
from pathlib import Path
import os

def validate_file_path(file_path: Path, allowed_extensions: set[str]) -> Path:
    """
    Validiert Dateipfad gegen Path Traversal.
    
    Raises:
        CADSecurityError: Bei ungültigen Pfaden
    """
    resolved = file_path.resolve()
    
    # 1. Extension Check
    if resolved.suffix.lower() not in allowed_extensions:
        raise CADSecurityError(
            code="INVALID_EXTENSION",
            message=f"Erlaubt: {allowed_extensions}, erhalten: {resolved.suffix}"
        )
    
    # 2. Realpath muss unter allowed_base liegen (SaaS-Context)
    # 3. Keine Symlinks in Produktionsumgebung
    if resolved.is_symlink():
        raise CADSecurityError(code="SYMLINK_NOT_ALLOWED")
    
    return resolved
```

---

### 3. Memory Exhaustion bei großen Dateien

**Problem:** `parse()` lädt alles in Memory. Keine Limits definiert.

**Empfehlung:**

```python
# In BaseParser
MAX_FILE_SIZE_MB = 500  # Konfigurierbar

def parse(self, file_path: Path) -> CADParseResult:
    file_size_mb = file_path.stat().st_size / (1024 * 1024)
    
    if file_size_mb > self.max_file_size_mb:
        raise CADResourceError(
            code="FILE_TOO_LARGE",
            message=f"Max {self.max_file_size_mb}MB, Datei hat {file_size_mb:.1f}MB",
            suggestion="Streaming-Parser verwenden oder Datei aufteilen"
        )
```

---

## 🟠 Wichtige Schwachstellen (Hohe Priorität)

### 4. Inkonsistenz mit Platform Database-First Prinzip

**Problem:** Das Dokument beschreibt `cad-services` als zustandslose Library ohne DB-Integration. Das widerspricht dem Platform-Prinzip "Database is Single Source of Truth".

**Konkret:**
- MappingProfiles werden aus JSON geladen (Zeile 678-681) statt aus DB
- Keine Foreign Keys zu Lookup Tables für `ElementCategory`
- Keine Versionierung der Konfiguration in DB

**Empfehlung:**

```
┌─────────────────────────────────────────────────────────────────┐
│  OPTION A: Library bleibt DB-agnostisch                         │
│  - Profile werden als Parameter übergeben                       │
│  - App-Layer (BFAgent) lädt Profile aus DB                      │
│  - Dokumentieren als explizite Design-Entscheidung              │
│                                                                 │
│  OPTION B: Django-Adapter wie creative-services                 │
│  - cad_services.adapters.django_adapter.py                      │
│  - DjangoMappingProfileRepository                               │
│  - Konsistenz mit Platform-Architektur                          │
└─────────────────────────────────────────────────────────────────┘
```

**Empfohlene Lösung:** Option A mit expliziter Dokumentation + Adapter-Interface:

```python
# cad_services/repositories/base.py
from abc import ABC, abstractmethod

class MappingProfileRepository(ABC):
    """Repository-Interface für Mapping-Profile."""
    
    @abstractmethod
    def get_by_name(self, name: str) -> MappingProfile:
        ...
    
    @abstractmethod
    def get_default(self) -> MappingProfile:
        ...

# cad_services/repositories/file.py
class FileProfileRepository(MappingProfileRepository):
    """Lädt Profile aus JSON-Dateien."""
    ...

# In BFAgent: bfagent/apps/cad_hub/repositories.py
class DjangoProfileRepository(MappingProfileRepository):
    """Lädt Profile aus CADMappingProfile Django Model."""
    ...
```

---

### 5. Fehlende Pydantic-Validatoren für Invarianten

**Problem:** Invarianten werden dokumentiert (Zeile 243-248, 347-351), aber nicht als Pydantic-Validatoren implementiert.

```python
# AKTUELL: Nur Dokumentation
"""
Explizite Invarianten (hochprior, enforced):
- `external_id` ist immer gesetzt.
- CADQuantity.unit ist konsistent zum quantity_type.
"""
```

**Empfehlung:**

```python
from pydantic import BaseModel, field_validator, model_validator

class CADQuantity(BaseModel):
    quantity_type: QuantityType
    value: Decimal
    unit: str
    method: QuantityMethod
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    inputs: dict | None = None
    formula: str | None = None
    
    @field_validator('unit')
    @classmethod
    def validate_unit_consistency(cls, v: str, info) -> str:
        """Unit muss zum quantity_type passen."""
        VALID_UNITS = {
            QuantityType.LENGTH: {"m", "mm", "cm", "ft", "in"},
            QuantityType.AREA: {"m²", "mm²", "cm²", "ft²", "sqm"},
            QuantityType.VOLUME: {"m³", "mm³", "l", "ft³", "cbm"},
            # ...
        }
        qty_type = info.data.get('quantity_type')
        if qty_type and v not in VALID_UNITS.get(qty_type, set()):
            raise ValueError(
                f"Unit '{v}' ungültig für {qty_type}. "
                f"Erlaubt: {VALID_UNITS[qty_type]}"
            )
        return v
    
    @model_validator(mode='after')
    def validate_computed_has_formula(self) -> 'CADQuantity':
        """Berechnete Quantities müssen inputs + formula haben."""
        computed_methods = {
            QuantityMethod.COMPUTED_GEOMETRY,
            QuantityMethod.COMPUTED_2D,
            QuantityMethod.COMPUTED_HEURISTIC,
        }
        if self.method in computed_methods:
            if not self.inputs or not self.formula:
                raise ValueError(
                    f"Method {self.method} erfordert 'inputs' und 'formula'"
                )
        return self
```

---

### 6. Regex-Kompilierung nicht optimiert

**Problem:** In `get_category_for_layer()` (Zeile 683-689) wird `re.match()` bei jedem Aufruf neu kompiliert.

```python
# AKTUELL (langsam bei vielen Elementen)
def get_category_for_layer(self, layer: str) -> ElementCategory:
    import re
    for mapping in self.layer_mappings:
        if re.match(mapping.pattern, layer, re.IGNORECASE):  # Kompiliert jedes Mal!
            return mapping.category
```

**Empfehlung:**

```python
from functools import cached_property
import re

class MappingProfile(BaseModel):
    layer_mappings: list[LayerMapping] = []
    
    @cached_property
    def _compiled_patterns(self) -> list[tuple[re.Pattern, ElementCategory]]:
        """Kompiliert Patterns einmalig."""
        return [
            (re.compile(m.pattern, re.IGNORECASE), m.category)
            for m in self.layer_mappings
        ]
    
    def get_category_for_layer(self, layer: str) -> ElementCategory:
        for pattern, category in self._compiled_patterns:
            if pattern.match(layer):
                return category
        return ElementCategory.UNKNOWN
```

---

### 7. CADParseResult.statistics untypisiert

**Problem:** `statistics: dict` (Zeile 420) ist zu generisch.

**Empfehlung:**

```python
class CADParseStatistics(BaseModel):
    """Typisierte Parse-Statistiken."""
    total_elements: int
    elements_by_category: dict[str, int]
    warnings_count: int
    
    # Performance
    parse_duration_ms: int
    extract_duration_ms: int
    
    # Größe
    file_size_bytes: int
    memory_peak_mb: float | None = None
    
    # IFC-spezifisch
    ifc_schema: str | None = None  # "IFC4", "IFC2X3"
    ifc_application: str | None = None

class CADParseResult(BaseModel):
    # ...
    statistics: CADParseStatistics  # Statt dict
```

---

## 🟡 Verbesserungsvorschläge (Mittlere Priorität)

### 8. Fehlende Deprecation-Strategie für BFAgent-Migration

**Problem:** Die Migrationsstrategie (Zeile 696-725) beschreibt Feature-Flags, aber keine API-Deprecation-Warnings.

**Empfehlung:**

```python
# bfagent/apps/cad_hub/services/cad_analyzer.py
import warnings
from django.conf import settings

def get_ifc_parser():
    if settings.USE_CAD_SERVICES_V2:
        from cad_services.parsers import IFCParser
        return IFCParser()
    else:
        warnings.warn(
            "Legacy IFC Parser ist deprecated seit BFAgent 2.5.0. "
            "Setze USE_CAD_SERVICES_V2=True. "
            "Legacy-Support endet in BFAgent 3.0.0.",
            DeprecationWarning,
            stacklevel=2
        )
        from .ifc_parser import IFCParserService
        return IFCParserService()
```

---

### 9. Kein Timeout-Handling für Geometrie-Extraktion

**Problem:** `extract_geometry=True` kann bei komplexen Modellen sehr lange dauern.

**Empfehlung:**

```python
import signal
from contextlib import contextmanager

class GeometryExtractionTimeout(CADError):
    """Timeout bei Geometrie-Extraktion."""
    pass

@contextmanager
def timeout(seconds: int, error_message: str):
    def signal_handler(signum, frame):
        raise GeometryExtractionTimeout(error_message)
    
    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)

class IFCParser(BaseParser):
    def __init__(
        self, 
        extract_geometry: bool = False,
        geometry_timeout_seconds: int = 30,  # NEU
    ):
        self.extract_geometry = extract_geometry
        self.geometry_timeout = geometry_timeout_seconds
    
    def _extract_geometry_safe(self, element) -> CADGeometry | None:
        if not self.extract_geometry:
            return None
        
        with timeout(self.geometry_timeout, f"Geometry timeout for {element.GlobalId}"):
            return self._extract_geometry(element)
```

---

### 10. Forward References in Type Hints nicht aufgelöst

**Problem:** `list["CADProperty"]` (Zeile 225-227) sind String-Forward-References.

**Empfehlung:**

```python
# cad_services/models/element.py
from __future__ import annotations  # PEP 563
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .property import CADProperty
    from .quantity import CADQuantity
    from .material import CADMaterial
    from .geometry import CADGeometry

class CADElement(BaseModel):
    properties: list[CADProperty] = Field(default_factory=list)
    quantities: list[CADQuantity] = Field(default_factory=list)
    # ...
    
    model_config = ConfigDict(
        # Für Pydantic v2: Forward References auflösen
        from_attributes=True,
    )
```

---

### 11. Fehlende Observability-Hooks

**Problem:** Keine strukturierten Logging-Events oder Metrics-Integration.

**Empfehlung:**

```python
# cad_services/observability.py
from dataclasses import dataclass
from typing import Protocol, Any
import structlog

logger = structlog.get_logger(__name__)

class CADMetricsCollector(Protocol):
    """Interface für Metrics (Prometheus, StatsD, etc.)."""
    
    def record_parse_duration(self, format: str, duration_ms: int) -> None: ...
    def record_element_count(self, format: str, category: str, count: int) -> None: ...
    def record_warning(self, format: str, warning_code: str) -> None: ...

@dataclass
class ParseEvent:
    """Strukturiertes Event für Logging/Tracing."""
    event_type: str  # "parse_started", "parse_completed", "parse_failed"
    file_hash: str
    source_format: str
    duration_ms: int | None = None
    element_count: int | None = None
    warning_count: int | None = None
    error_code: str | None = None
    
    def log(self):
        logger.info(
            self.event_type,
            **{k: v for k, v in self.__dict__.items() if v is not None}
        )
```

---

## 🟢 Kleinere Verbesserungen

### 12. `Config` → `model_config` (Pydantic v2)

```python
# ALT (Pydantic v1 style)
class CADElement(BaseModel):
    class Config:
        use_enum_values = True

# NEU (Pydantic v2)
class CADElement(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
```

---

### 13. Fehlende `__repr__` für Debugging

```python
class CADElement(BaseModel):
    # ...
    
    def __repr__(self) -> str:
        return (
            f"CADElement(category={self.category}, "
            f"name='{self.name}', external_id='{self.external_id}')"
        )
```

---

### 14. CLI Tool fehlt

Das Dokument erwähnt ein CLI Tool (Zeile 25), aber keine Spezifikation.

**Empfehlung:**

```python
# cad_services/cli.py
import typer
from pathlib import Path
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="CAD Services CLI")
console = Console()

@app.command()
def parse(
    file: Path = typer.Argument(..., help="IFC/DXF Datei"),
    format: str = typer.Option(None, help="Format (auto-detect wenn leer)"),
    output: Path = typer.Option(None, "-o", help="Output JSON"),
    geometry: bool = typer.Option(False, help="Geometrie extrahieren"),
):
    """Parst eine CAD-Datei und gibt Zusammenfassung aus."""
    ...

@app.command()
def validate(file: Path):
    """Validiert eine CAD-Datei ohne vollständiges Parsing."""
    ...

@app.command()
def golden_master(
    file: Path,
    output: Path,
    profile: Path = typer.Option(None),
):
    """Erzeugt Golden-Master JSON für Regression-Tests."""
    ...
```

---

## 📋 Zusammenfassung der Empfehlungen

| # | Priorität | Kategorie | Empfehlung |
|---|-----------|-----------|------------|
| 1 | 🔴 Kritisch | Robustheit | Exception-Handling für Parser |
| 2 | 🔴 Kritisch | Sicherheit | Path Traversal Schutz |
| 3 | 🔴 Kritisch | Ressourcen | File Size Limits |
| 4 | 🟠 Hoch | Architektur | Repository-Pattern für Profile |
| 5 | 🟠 Hoch | Validierung | Pydantic-Validatoren implementieren |
| 6 | 🟠 Hoch | Performance | Regex vorkompilieren |
| 7 | 🟠 Hoch | Typisierung | CADParseStatistics statt dict |
| 8 | 🟡 Mittel | Migration | Deprecation Warnings |
| 9 | 🟡 Mittel | Robustheit | Geometry-Timeout |
| 10 | 🟡 Mittel | Code-Qualität | Forward References |
| 11 | 🟡 Mittel | Observability | Strukturiertes Logging |
| 12-14 | 🟢 Nice-to-have | Diverses | Pydantic v2, repr, CLI |

---

## ✅ Stärken des Dokuments

1. **Klare Layer-Trennung** (Parser → Extractor → Calculator)
2. **Gute Audit-Trail-Konzepte** (CADParseResult mit Hash, Version, Warnings)
3. **Solide Migrationsstrategie** mit Feature-Flags und Shadow-Mode
4. **Umfassende PR-Checklist** (Zeile 1058-1092)
5. **Realistische Roadmap** mit Sprint-fähigen Milestones

---

## 🎯 Empfohlene nächste Schritte

1. **Sofort (vor Implementierung):**
   - Kritische Schwachstellen 1-3 ins Konzept einarbeiten
   - Security-Kapitel ergänzen
   - Exception-Hierarchie definieren

2. **Milestone 0 erweitern:**
   - `cad_services/exceptions.py` mit CADError-Hierarchie
   - `cad_services/utils/path_validation.py`
   - Basis-Logging mit structlog

3. **Milestone 1 erweitern:**
   - Pydantic-Validatoren für alle Invarianten
   - `CADParseStatistics` statt `dict`
   - Negative Tests für alle Validatoren

---

**Review abgeschlossen.**

*Erstellt am 2026-01-29 durch Architektur-Review*
