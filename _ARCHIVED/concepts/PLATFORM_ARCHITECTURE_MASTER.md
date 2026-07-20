# PLATFORM ARCHITECTURE MASTER
## Travel Beat / drifttales - Konsolidierte Architektur

> **Version:** 1.0  
> **Stand:** 2025-01-27  
> **Konsolidiert aus:**
> - PLATFORM_ARCHITECTURE_REFINED.md
> - TIMING_STORY_PLATFORM_ANALYSIS.md  
> - ENUM_DB_FIRST_COMPLETE.md
> - UNTERLAGEN_OPTIMIERUNG_ZIELSCHNITTSTELLE.md

---

## Inhaltsverzeichnis

1. **Kern-Prinzipien** ← PLATFORM_ARCHITECTURE_REFINED
2. **Monorepo-Struktur** ← PLATFORM_ARCHITECTURE_REFINED + ZIELSCHNITTSTELLE
3. **Daten-Strategie: Spec vs. Derived** ← ZIELSCHNITTSTELLE (NEU!)
4. **Enum-Strategie: Code vs. DB-Lookup** ← ENUM_DB_FIRST_COMPLETE
5. **Pydantic-Django Integration** ← PLATFORM_ARCHITECTURE_REFINED + ZIELSCHNITTSTELLE
6. **Timing/Story Domain** ← TIMING_STORY_PLATFORM_ANALYSIS (bereinigt)
7. **Lookup Tables (DB-Driven)** ← ENUM_DB_FIRST_COMPLETE
8. **Services & Providers** ← ZIELSCHNITTSTELLE + TIMING_STORY
9. **Migration & Versionierung** ← ZIELSCHNITTSTELLE
10. **Observability & Härtung** ← ZIELSCHNITTSTELLE (NEU!)
11. **Implementierungs-Roadmap** ← Konsolidiert

---

## Quellen-Mapping (was kommt woher)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  MASTER-DOKUMENT                         │  QUELLE                          │
├──────────────────────────────────────────┼──────────────────────────────────┤
│  1. Kern-Prinzipien                      │  PLATFORM_ARCHITECTURE_REFINED   │
│     - Database-First                     │                                  │
│     - Separation of Concerns             │                                  │
│     - Zero Breaking Changes              │                                  │
│                                          │                                  │
│  2. Monorepo-Struktur                    │  PLATFORM_ARCHITECTURE_REFINED   │
│     - packages/ vs apps/                 │  + ZIELSCHNITTSTELLE (domain/)   │
│     - Package-Hierarchie                 │                                  │
│                                          │                                  │
│  3. Spec vs. Derived (NEU)               │  ZIELSCHNITTSTELLE               │
│     - Nur Fakten in DB                   │                                  │
│     - Berechnetes zur Laufzeit           │                                  │
│     - Hot Columns Pattern                │                                  │
│                                          │                                  │
│  4. Enum-Strategie                       │  ENUM_DB_FIRST_COMPLETE          │
│     - Code-Enum (Workflow)               │                                  │
│     - DB-Lookup (Content)                │                                  │
│     - Hybrid (Core + Extension)          │                                  │
│                                          │                                  │
│  5. Pydantic-Django Integration          │  PLATFORM_ARCHITECTURE_REFINED   │
│     - PydanticSchemaField                │  + ZIELSCHNITTSTELLE (strict!)   │
│     - Schema-Versionierung               │                                  │
│     - Migrator-Pattern                   │                                  │
│                                          │                                  │
│  6. Timing/Story Domain                  │  TIMING_STORY_PLATFORM_ANALYSIS  │
│     - TimingSpec (Pydantic)              │  (Enums → verweist auf Kap. 4)   │
│     - ChapterSpec                        │                                  │
│     - Provider-Pattern                   │                                  │
│                                          │                                  │
│  7. Lookup Tables                        │  ENUM_DB_FIRST_COMPLETE          │
│     - BaseLookupTable                    │                                  │
│     - Genre, SpiceLevel, etc.            │                                  │
│     - Initial Data Migrations            │                                  │
│                                          │                                  │
│  8. Services & Providers                 │  ZIELSCHNITTSTELLE               │
│     - Provider = Pure Functions          │  + TIMING_STORY                  │
│     - Service = Orchestrierung           │                                  │
│     - Idempotenz + Locking               │                                  │
│                                          │                                  │
│  9. Migration & Versionierung            │  ZIELSCHNITTSTELLE               │
│     - JSON-Schema Migrator               │                                  │
│     - Lazy vs. Eager Write-back          │                                  │
│     - Management Commands                │                                  │
│                                          │                                  │
│  10. Observability (NEU)                 │  ZIELSCHNITTSTELLE               │
│     - Kein Silent Fallback               │                                  │
│     - Strict Mode                        │                                  │
│     - Quarantäne-Pattern                 │                                  │
│     - Logging-Events                     │                                  │
│                                          │                                  │
│  11. Roadmap                             │  ALLE (konsolidiert)             │
│     - Phasen                             │                                  │
│     - Aufwandsschätzung                  │                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Änderungen gegenüber Einzel-Dokumenten

| Dokument | Änderung | Grund |
|----------|----------|-------|
| TIMING_STORY | Enum-Abschnitte entfernt | → Verweist auf Kap. 4 |
| TIMING_STORY | `_version` → `schema_version` | Pydantic v2 Kompatibilität |
| ZIELSCHNITTSTELLE | ReadingContext → DB-Lookup | Database-First Konsistenz |
| ZIELSCHNITTSTELLE | Struktur angepasst | `packages/` statt flach |
| ENUM_DB_FIRST | Integriert | War Ergänzung, jetzt Teil |

---

## Nächste Schritte

- [ ] Kapitel 1: Kern-Prinzipien
- [ ] Kapitel 2: Monorepo-Struktur
- [ ] Kapitel 3: Spec vs. Derived
- [ ] Kapitel 4: Enum-Strategie
- [ ] Kapitel 5: Pydantic-Django
- [ ] Kapitel 6: Timing/Story Domain
- [ ] Kapitel 7: Lookup Tables
- [ ] Kapitel 8: Services & Providers
- [ ] Kapitel 9: Migration
- [ ] Kapitel 10: Observability
- [ ] Kapitel 11: Roadmap
# Kapitel 1: Kern-Prinzipien

---

## 1.1 Database-First

> **Die Datenbank ist die Single Source of Truth.**

### Regeln

1. **Schema-Änderungen zuerst** - Django Migration vor Code
2. **Keine Code-Logik für Daten-Defaults** - DB-Constraints definieren Defaults
3. **FK statt String** - Referenzen als Foreign Keys, nicht als Strings
4. **Validierung in DB** - CHECK Constraints, NOT NULL wo sinnvoll

### Anwendung

```python
# ❌ FALSCH: Default im Code
class Story(models.Model):
    genre = models.CharField(default="romance")  # Woher kommt "romance"?

# ✅ RICHTIG: FK zu Lookup Table
class Story(models.Model):
    genre = models.ForeignKey(
        'Genre',
        on_delete=models.PROTECT,  # Verhindert Löschen wenn referenziert
    )
```

---

## 1.2 Spec vs. Derived

> **In der DB nur Fakten speichern. Alles Berechnete zur Laufzeit.**

### Spec (persistiert)
- Eingabe-Daten, Fakten
- Versioniert (`schema_version`)
- Änderbar durch User/System

### Derived (nicht persistiert)
- Berechnet aus Spec
- Deterministisch reproduzierbar
- Optional cachebar

```python
# Spec: Wird gespeichert
class TimingSpec(BaseModel):
    total_words: int = 30000
    total_chapters: int = 10
    reader_speed_wpm: int = 250

# Derived: Wird berechnet
def get_total_minutes(spec: TimingSpec) -> int:
    return spec.total_words // spec.reader_speed_wpm  # 120 min
```

**Ausnahme: Hot Columns** - Häufig gefilterte Derived-Werte als echte DB-Spalten (mit Sync-Mechanismus).

---

## 1.3 Separation of Concerns

> **Klare Trennung: Presentation → Service → Data**

### Layer

| Layer | Verantwortung | Beispiel |
|-------|---------------|----------|
| **Presentation** | HTTP, Forms, Templates | `views.py`, `forms.py` |
| **Service** | Business Logic, Orchestrierung | `services.py` |
| **Provider** | Pure Functions, Berechnungen | `providers.py` |
| **Selector** | DB-Reads (lesend) | `selectors.py` |
| **Model** | DB-Schema, keine Logik | `models.py` |

### Regeln

```python
# ❌ FALSCH: Logik im Model
class Story(models.Model):
    def generate_chapters(self):  # Business Logic im Model
        ...

# ✅ RICHTIG: Logik im Service
# services/story_generation.py
def generate_chapters(story_id: int) -> Story:
    story = Story.objects.select_for_update().get(id=story_id)
    ...
```

---

## 1.4 Zero Breaking Changes

> **Bestehende APIs und Daten dürfen nicht brechen.**

### Strategien

1. **Additive Changes** - Neue Felder hinzufügen, alte nicht entfernen
2. **Schema-Versionierung** - `schema_version` in JSON-Feldern
3. **Migratoren** - Alte Versionen automatisch upgraden
4. **Soft Deprecation** - `is_active=False` statt Löschen

```python
# Migration v1 → v2
def _v1_to_v2(payload: dict) -> dict:
    payload = dict(payload)
    payload.setdefault("reader_speed_wpm", 250)  # Neues Feld mit Default
    payload["schema_version"] = 2
    return payload
```

---

## 1.5 Fail Loud, Not Silent

> **Keine stillen Defaults bei Fehlern. Explizit scheitern.**

### Regeln

1. **Strict Mode in PROD** - Validation-Fehler = Exception
2. **Kein Silent Fallback** - Nicht `return default_value` bei Invalid
3. **Quarantäne statt 500** - Invalid Records markieren, nicht crashen
4. **Logging** - Jeder Fehler wird geloggt (structured)

```python
# ❌ FALSCH: Silent Fallback
def from_db_value(self, value, ...):
    try:
        return self.schema_class.model_validate(value)
    except ValidationError:
        return self.schema_class()  # 💀 Überschreibt echte Daten!

# ✅ RICHTIG: Explicit Failure
def from_db_value(self, value, ...):
    try:
        return self.schema_class.model_validate(value)
    except ValidationError:
        logger.exception("Invalid payload", extra={"field": self.name})
        if self.strict:
            raise
        return None  # Service muss damit umgehen
```

---

## 1.6 Idempotenz

> **Gleiche Operation mehrfach = gleiches Ergebnis.**

### Anwendung in Services

```python
@transaction.atomic
def ensure_timing_spec(story_id: int) -> Story:
    story = Story.objects.select_for_update().get(id=story_id)
    
    # Idempotent: Nur erstellen wenn nicht vorhanden
    if story.timing_spec is None:
        story.timing_spec = create_default_timing_spec(story)
        story.save(update_fields=["timing_spec"])
    
    return story
```

### Regeln

1. **Check before Write** - Prüfen ob Aktion nötig
2. **Locking** - `select_for_update()` gegen Race Conditions
3. **Deterministische Defaults** - Keine `random()` oder `now()` in Specs
# Kapitel 2: Monorepo-Struktur

---

## 2.1 Übersicht

```
drifttales-platform/
├── packages/                    # Shared Libraries (pip-installierbar)
│   ├── platform_core/           # Basis: Fields, Exceptions, Utils
│   ├── platform_users/          # User, ReaderProfile, Auth
│   └── platform_creative/       # Timing, Story, Lookups, Enums
│
├── apps/                        # Django Apps (Travel Beat spezifisch)
│   ├── trips/                   # Trip-Management
│   ├── stories/                 # Story-Generierung
│   └── reading/                 # Reading Progress
│
├── bf_agent/                    # Separates Projekt (nutzt packages/)
│
└── manage.py
```

---

## 2.2 Package-Hierarchie

```
platform_core          (Basis, keine Abhängigkeiten)
       ↓
platform_users         (→ platform_core)
       ↓
platform_creative      (→ platform_core, platform_users)
       ↓
apps/stories           (→ alle packages)
```

### Regel: Keine Rückwärts-Abhängigkeiten

```python
# ❌ FALSCH: platform_core importiert aus platform_creative
# packages/platform_core/...
from platform_creative.models import Genre  # VERBOTEN!

# ✅ RICHTIG: platform_creative importiert aus platform_core
# packages/platform_creative/...
from platform_core.db.fields import PydanticSchemaField  # OK
```

---

## 2.3 Package: platform_core

```
packages/platform_core/
├── platform_core/
│   ├── __init__.py
│   ├── db/
│   │   ├── __init__.py
│   │   ├── fields.py           # PydanticSchemaField
│   │   └── lookup_tables.py    # BaseLookupTable, LookupTableManager
│   ├── exceptions/
│   │   ├── __init__.py
│   │   └── base.py             # PlatformException, ValidationError
│   ├── utils/
│   │   └── logging.py          # Structured Logging Helpers
│   └── admin/
│       └── lookup_admin.py     # BaseLookupTableAdmin
├── pyproject.toml
└── README.md
```

---

## 2.4 Package: platform_creative

```
packages/platform_creative/
├── platform_creative/
│   ├── __init__.py
│   │
│   ├── domain/                  # Domain Logic (Pure)
│   │   ├── timing/
│   │   │   ├── __init__.py
│   │   │   ├── spec.py          # TimingSpec (Pydantic, persistiert)
│   │   │   ├── derived.py       # TimingConstraints, Metrics (nicht persistiert)
│   │   │   ├── providers.py     # Pure Functions
│   │   │   ├── migrator.py      # Schema-Migration
│   │   │   └── exceptions.py
│   │   └── story/
│   │       ├── spec.py          # StorySpec, OutlineSpec
│   │       └── providers.py
│   │
│   ├── enums/                   # Code-Enums (Workflow/System)
│   │   ├── __init__.py
│   │   ├── status.py            # StoryStatus, ChapterStatus
│   │   ├── pacing.py            # CorePacingType
│   │   └── story_beat.py        # CoreStoryBeat
│   │
│   ├── models/                  # DB-Lookup Tables
│   │   ├── __init__.py
│   │   ├── genre.py
│   │   ├── spice_level.py
│   │   ├── ending_type.py
│   │   ├── accommodation_type.py
│   │   ├── transport_type.py
│   │   ├── reading_context.py   # DB-Lookup (nicht Code-Enum!)
│   │   └── pacing_extension.py  # Hybrid: DB-Extension
│   │
│   ├── services/                # Orchestrierung (mit DB/IO)
│   │   ├── timing_service.py
│   │   └── lookup_service.py
│   │
│   └── migrations/
│       ├── 0001_initial.py
│       ├── 0002_seed_genres.py
│       └── ...
│
├── pyproject.toml
└── README.md
```

---

## 2.5 App: apps/stories

```
apps/stories/
├── __init__.py
├── models/
│   ├── __init__.py
│   ├── story.py                 # Story Model (FK zu Lookups)
│   └── chapter.py               # Chapter Model
│
├── services/
│   ├── __init__.py
│   ├── generation.py            # StoryGenerationService
│   ├── outline.py               # OutlineService
│   └── chapter_writer.py        # ChapterWriterService
│
├── selectors/
│   ├── __init__.py
│   └── story_selectors.py       # get_story_with_chapters, etc.
│
├── forms.py
├── views.py
├── urls.py
├── admin.py
│
├── templates/
│   └── stories/
│
└── migrations/
```

---

## 2.6 Naming Conventions

### Dateien

| Typ | Pattern | Beispiel |
|-----|---------|----------|
| Model | `{entity}.py` | `story.py`, `chapter.py` |
| Service | `{domain}_service.py` | `timing_service.py` |
| Provider | `{domain}_providers.py` | `timing_providers.py` |
| Selector | `{entity}_selectors.py` | `story_selectors.py` |
| Spec (Pydantic) | `spec.py` oder `{entity}_spec.py` | `timing/spec.py` |
| Derived | `derived.py` | `timing/derived.py` |

### Klassen/Funktionen

| Typ | Pattern | Beispiel |
|-----|---------|----------|
| Pydantic Spec | `{Entity}Spec` | `TimingSpec`, `ChapterSpec` |
| Pydantic Derived | `{Entity}Constraints` | `TimingConstraints` |
| Service | `{action}_{entity}` | `generate_story`, `ensure_timing_spec` |
| Selector | `get_{entity}`, `list_{entities}` | `get_story_by_id`, `list_chapters` |
| Provider | `build_{output}`, `calculate_{metric}` | `build_constraints`, `calculate_minutes` |

---

## 2.7 Import-Beispiele

```python
# In apps/stories/services/generation.py

# Aus platform_core
from platform_core.db.fields import PydanticSchemaField
from platform_core.exceptions import PlatformException

# Aus platform_creative (Domain)
from platform_creative.domain.timing.spec import TimingSpec
from platform_creative.domain.timing.providers import build_constraints

# Aus platform_creative (Enums - nur Workflow!)
from platform_creative.enums.status import StoryStatus, ChapterStatus

# Aus platform_creative (Lookups)
from platform_creative.models import Genre, SpiceLevel

# Aus eigener App
from apps.stories.models import Story, Chapter
from apps.stories.selectors import get_story_with_chapters
```
# Kapitel 3: Spec vs. Derived

---

## 3.1 Grundprinzip

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│   USER INPUT          SPEC (DB)              DERIVED (Runtime)              │
│   ──────────    →     ─────────      →       ────────────────               │
│                                                                              │
│   "10 Kapitel"        total_chapters: 10     chapter_constraints: [...]     │
│   "30.000 Wörter"     total_words: 30000     total_minutes: 120             │
│   "250 WPM"           reader_speed_wpm: 250  chapter_minutes: [12, 12, ...] │
│                                                                              │
│   ✅ Persistiert       ✅ Persistiert         ❌ NICHT persistiert           │
│   ✅ Versioniert       ✅ Versioniert         ✅ Deterministisch berechnet   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3.2 Was gehört in Spec?

### ✅ In Spec (persistieren)

| Typ | Beispiele |
|-----|-----------|
| **User-Eingaben** | `total_chapters`, `total_words`, `reader_speed_wpm` |
| **Referenzen** | `trip_id`, `genre_code`, `source_type` |
| **Konfiguration** | `word_count_tolerance`, `enforce_word_counts` |
| **Metadaten** | `schema_version`, `created_at` |

### ❌ Nicht in Spec (berechnen)

| Typ | Beispiele |
|-----|-----------|
| **Berechnete Werte** | `total_minutes`, `average_chapter_words` |
| **Constraints** | `word_count_min`, `word_count_max` |
| **Ableitungen** | `is_long_story`, `recommended_pacing` |

---

## 3.3 Warum diese Trennung?

### Problem: Persistierte Derived-Werte

```python
# ❌ SCHLECHT: Derived in DB
class Story(models.Model):
    total_words = models.IntegerField()
    reader_speed_wpm = models.IntegerField()
    total_minutes = models.IntegerField()  # 💀 Berechnet!
```

**Probleme:**
1. **Inkonsistenz**: `total_words` ändert sich, `total_minutes` bleibt alt
2. **Sync-Aufwand**: Immer daran denken, beide zu updaten
3. **Bulk Updates**: `Story.objects.update(total_words=X)` vergisst `total_minutes`

### Lösung: Derived zur Laufzeit

```python
# ✅ GUT: Derived berechnet
class Story(models.Model):
    total_words = models.IntegerField()
    reader_speed_wpm = models.IntegerField()
    
    @property
    def total_minutes(self) -> int:
        return self.total_words // self.reader_speed_wpm
```

---

## 3.4 Hot Columns: Die Ausnahme

Manchmal braucht man Derived-Werte für **DB-Queries/Filtering**.

### Wann Hot Columns?

✅ **Ja, Hot Column wenn:**
- Häufig in `WHERE`, `ORDER BY`, `GROUP BY`
- Für Analytics/Dashboards benötigt
- Index-Unterstützung nötig

❌ **Nein, Hot Column wenn:**
- Nur für Anzeige im UI
- Selten benötigt
- Leicht zur Laufzeit berechenbar

### Implementierung

```python
class Story(models.Model):
    # === SPEC (Source of Truth) ===
    timing_spec = PydanticSchemaField(schema_class=TimingSpec)
    
    # === HOT COLUMNS (Derived, aber für Queries) ===
    timing_total_minutes = models.IntegerField(null=True, db_index=True)
    is_travel_synced = models.BooleanField(default=False, db_index=True)
    
    def sync_hot_columns(self):
        """Muss nach jedem Spec-Update aufgerufen werden!"""
        if self.timing_spec:
            self.timing_total_minutes = self.timing_spec.derived_total_minutes()
            self.is_travel_synced = self.timing_spec.is_travel_synced
        else:
            self.timing_total_minutes = None
            self.is_travel_synced = False
```

### Sync-Garantie im Service

```python
# services/timing_service.py

@transaction.atomic
def update_timing_spec(story_id: int, new_spec: TimingSpec) -> Story:
    story = Story.objects.select_for_update().get(id=story_id)
    
    story.timing_spec = new_spec
    story.sync_hot_columns()  # IMMER zusammen!
    
    story.save(update_fields=[
        "timing_spec",
        "timing_total_minutes",
        "is_travel_synced",
    ])
    return story
```

---

## 3.5 Pydantic: Spec-Klasse

```python
# platform_creative/domain/timing/spec.py

from pydantic import BaseModel, Field, model_validator
from typing import List, Optional, Literal

CURRENT_SPEC_VERSION = 2


class ChapterSpec(BaseModel):
    """Kapitel-Spezifikation (persistiert)."""
    chapter_number: int = Field(..., ge=1)
    word_count_target: int = Field(..., ge=0)
    reading_context_code: str = "general"  # FK-Code zu ReadingContext
    story_beat: Optional[str] = None


class TravelMeta(BaseModel):
    """Travel-Sync Metadaten (persistiert)."""
    is_travel_synced: bool = False
    trip_id: Optional[int] = None


class TimingSpec(BaseModel):
    """
    Timing-Spezifikation - wird in DB persistiert.
    
    Enthält NUR Fakten/Inputs, keine berechneten Werte.
    """
    
    # Schema-Version (für Migrationen)
    schema_version: Literal[2] = Field(2, description="Schema-Version")
    
    # Core Facts
    source_type: str = "manual"  # manual, travel_beat, import
    total_chapters: int = Field(..., ge=1)
    total_words: int = Field(..., ge=1)
    reader_speed_wpm: int = Field(250, ge=50, le=1000)
    
    # Kapitel-Details
    chapters: List[ChapterSpec] = Field(default_factory=list)
    
    # Travel-Sync
    travel: Optional[TravelMeta] = None
    
    # === DERIVED METHODS (nicht persistiert) ===
    
    def derived_total_minutes(self) -> int:
        """Berechnet, NICHT in DB."""
        return self.total_words // self.reader_speed_wpm
    
    def derived_chapter_minutes(self) -> dict[int, int]:
        """Berechnet, NICHT in DB."""
        return {
            ch.chapter_number: ch.word_count_target // self.reader_speed_wpm
            for ch in self.chapters
        }
    
    @property
    def is_travel_synced(self) -> bool:
        return bool(self.travel and self.travel.is_travel_synced)
    
    # === VALIDATION ===
    
    @model_validator(mode="after")
    def ensure_chapters(self):
        """Auto-generiert Kapitel wenn nicht vorhanden."""
        if not self.chapters:
            per_chapter = self.total_words // self.total_chapters
            self.chapters = [
                ChapterSpec(
                    chapter_number=i + 1,
                    word_count_target=per_chapter,
                )
                for i in range(self.total_chapters)
            ]
        return self
```

---

## 3.6 Pydantic: Derived-Klassen

```python
# platform_creative/domain/timing/derived.py

from pydantic import BaseModel, Field
from typing import Dict


class ChapterConstraints(BaseModel):
    """Kapitel-Constraints (berechnet, NICHT persistiert)."""
    chapter_number: int
    word_count_min: int
    word_count_max: int
    reading_minutes: int


class TimingConstraints(BaseModel):
    """Timing-Constraints für alle Kapitel."""
    chapters: Dict[int, ChapterConstraints]


class TimingMetrics(BaseModel):
    """Aggregierte Metriken (berechnet)."""
    total_minutes: int
    average_chapter_minutes: float
    chapter_minutes: Dict[int, int]
```

---

## 3.7 Provider: Spec → Derived

```python
# platform_creative/domain/timing/providers.py

from .spec import TimingSpec
from .derived import TimingConstraints, ChapterConstraints, TimingMetrics


def build_constraints(
    spec: TimingSpec,
    tolerance: float = 0.1,
) -> TimingConstraints:
    """
    Pure Function: Spec → Constraints.
    
    Keine DB, kein IO, deterministisch.
    """
    chapters = {}
    
    for ch in spec.chapters:
        target = ch.word_count_target
        chapters[ch.chapter_number] = ChapterConstraints(
            chapter_number=ch.chapter_number,
            word_count_min=int(target * (1 - tolerance)),
            word_count_max=int(target * (1 + tolerance)),
            reading_minutes=target // spec.reader_speed_wpm,
        )
    
    return TimingConstraints(chapters=chapters)


def build_metrics(spec: TimingSpec) -> TimingMetrics:
    """Pure Function: Spec → Metrics."""
    chapter_minutes = {
        ch.chapter_number: ch.word_count_target // spec.reader_speed_wpm
        for ch in spec.chapters
    }
    
    total = sum(chapter_minutes.values())
    avg = total / len(chapter_minutes) if chapter_minutes else 0
    
    return TimingMetrics(
        total_minutes=total,
        average_chapter_minutes=avg,
        chapter_minutes=chapter_minutes,
    )
```

---

## 3.8 Zusammenfassung

| Aspekt | Spec | Derived | Hot Column |
|--------|------|---------|------------|
| **Persistiert** | ✅ Ja | ❌ Nein | ✅ Ja |
| **Quelle** | User/System Input | Berechnung | Berechnung |
| **Änderbar** | ✅ Direkt | ❌ Nur via Spec | ❌ Nur via Sync |
| **Versioniert** | ✅ `schema_version` | - | - |
| **Indexierbar** | ⚠️ GIN (JSONB) | ❌ | ✅ BTree |
| **Beispiele** | `total_words`, `chapters[]` | `total_minutes` | `timing_total_minutes` |
# Kapitel 4: Enum-Strategie

---

## 4.1 Drei Kategorien

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ENUM KATEGORISIERUNG                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  🔒 CODE-ENUM                    📦 DB-LOOKUP                🔄 HYBRID       │
│  Workflow/System                 Content/Erweiterbar         Core + Extension│
│                                                                              │
│  StoryStatus                     Genre                       PacingType      │
│  ChapterStatus                   SpiceLevel                  StoryBeat       │
│  GenerationPhase                 EndingType                  ReadingContext  │
│                                  AccommodationType                           │
│                                  TransportType                               │
│                                  TriggerCategory                             │
│                                                                              │
│  Änderung = Code-Change          Änderung = Admin-Click      Core: Code      │
│  Hat Workflow-Logik              Keine Code-Logik            Ext: Admin      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4.2 Entscheidungsmatrix

| Frage | Code-Enum | DB-Lookup |
|-------|-----------|-----------|
| Hat State-Machine-Logik? | ✅ | ❌ |
| Wird in `if/switch` verwendet? | ✅ | ❌ |
| Soll Admin neue Werte anlegen? | ❌ | ✅ |
| Braucht i18n (display_name_de)? | ❌ | ✅ |
| Historische Referenzen wichtig? | ❌ | ✅ |
| Änderung ohne Deployment? | ❌ | ✅ |

---

## 4.3 Code-Enums (Workflow/System)

### Wann Code-Enum?

- **State Machine** mit `can_transition_to()`
- **Änderung = Breaking Change** im Workflow
- **Logik gehört zum Wert** (Properties, Methods)

### StoryStatus

```python
# platform_creative/enums/status.py

from enum import Enum
from typing import Set


class StoryStatus(str, Enum):
    """
    Story-Status mit Workflow-Logik.
    
    DRAFT → PENDING → GENERATING → COMPLETED
                  ↘               ↗
                    → FAILED → PENDING
    """
    
    DRAFT = "draft"
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
    
    @property
    def is_terminal(self) -> bool:
        return self in {self.COMPLETED, self.FAILED}
    
    @property
    def can_edit(self) -> bool:
        return self in {self.DRAFT, self.FAILED}
    
    def allowed_transitions(self) -> Set['StoryStatus']:
        transitions = {
            self.DRAFT: {self.PENDING},
            self.PENDING: {self.GENERATING, self.DRAFT},
            self.GENERATING: {self.COMPLETED, self.FAILED},
            self.COMPLETED: set(),
            self.FAILED: {self.PENDING, self.DRAFT},
        }
        return transitions.get(self, set())
    
    def can_transition_to(self, target: 'StoryStatus') -> bool:
        return target in self.allowed_transitions()
```

### Nutzung im Model

```python
# apps/stories/models/story.py

class Story(models.Model):
    status = models.CharField(
        max_length=20,
        choices=[(s.value, s.value.title()) for s in StoryStatus],
        default=StoryStatus.DRAFT.value,
    )
    
    @property
    def status_enum(self) -> StoryStatus:
        return StoryStatus(self.status)
    
    def transition_to(self, new_status: StoryStatus) -> None:
        if not self.status_enum.can_transition_to(new_status):
            raise ValueError(f"Cannot transition from {self.status} to {new_status.value}")
        self.status = new_status.value
```

---

## 4.4 DB-Lookup Tables (Content)

### Wann DB-Lookup?

- **Erweiterbar** ohne Deployment
- **Admin soll pflegen** können
- **Keine Code-Logik** im Wert selbst
- **i18n** (mehrsprachige Anzeigenamen)

### BaseLookupTable

```python
# platform_core/db/lookup_tables.py

from django.db import models
from django.core.cache import cache


class LookupTableManager(models.Manager):
    def get_by_code(self, code: str):
        cache_key = f"lookup:{self.model._meta.db_table}:{code}"
        result = cache.get(cache_key)
        if result is None:
            result = self.filter(code=code).first()
            if result:
                cache.set(cache_key, result, timeout=3600)
        return result
    
    def all_active(self):
        cache_key = f"lookup:{self.model._meta.db_table}:active"
        result = cache.get(cache_key)
        if result is None:
            result = list(self.filter(is_active=True).order_by('sort_order'))
            cache.set(cache_key, result, timeout=3600)
        return result
    
    def choices(self):
        return [(item.code, item.display_name) for item in self.all_active()]


class BaseLookupTable(models.Model):
    """Abstract Base für alle Lookup Tables."""
    
    code = models.CharField(max_length=50, primary_key=True)
    display_name = models.CharField(max_length=100)
    display_name_de = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    
    is_active = models.BooleanField(default=True, db_index=True)
    is_system = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=100)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = LookupTableManager()
    
    class Meta:
        abstract = True
        ordering = ['sort_order', 'display_name']
    
    def __str__(self):
        return self.display_name
    
    def get_display_name(self, lang: str = 'de') -> str:
        if lang == 'de' and self.display_name_de:
            return self.display_name_de
        return self.display_name
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        cache.delete(f"lookup:{self._meta.db_table}:active")
    
    def delete(self, *args, **kwargs):
        if self.is_system:
            raise ValueError("Cannot delete system entry")
        super().delete(*args, **kwargs)
```

### Konkrete Lookup Tables

```python
# platform_creative/models/genre.py

class Genre(BaseLookupTable):
    """Story-Genres (Admin-pflegbar)."""
    
    prompt_template = models.TextField(blank=True)
    default_pacing = models.CharField(max_length=30, default="balanced")
    typical_tropes = models.JSONField(default=list, blank=True)
    
    available_travel_beat = models.BooleanField(default=True)
    available_bf_agent = models.BooleanField(default=True)
    
    class Meta(BaseLookupTable.Meta):
        db_table = 'platform_genre'


# platform_creative/models/spice_level.py

class SpiceLevel(BaseLookupTable):
    """Intimität-Level."""
    
    intensity = models.PositiveSmallIntegerField(default=1)
    prompt_guidance = models.TextField(blank=True)
    age_rating = models.CharField(max_length=10, default="16+")
    
    class Meta(BaseLookupTable.Meta):
        db_table = 'platform_spice_level'


# platform_creative/models/reading_context.py

class ReadingContext(BaseLookupTable):
    """Lese-Kontexte (Transport, Abend, etc.)."""
    
    class Category(models.TextChoices):
        TRANSPORT = "transport"
        EVENING = "evening"
        MORNING = "morning"
        LEISURE = "leisure"
        OTHER = "other"
    
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER)
    recommended_pacing = models.CharField(max_length=30, default="balanced")
    cliffhanger_tendency = models.FloatField(default=0.5)
    default_reading_minutes = models.PositiveIntegerField(default=30)
    
    class Meta(BaseLookupTable.Meta):
        db_table = 'platform_reading_context'
    
    @property
    def is_transport(self) -> bool:
        return self.category == self.Category.TRANSPORT
```

### Nutzung im Story Model

```python
# apps/stories/models/story.py

class Story(models.Model):
    # FK zu Lookup Table (statt CharField mit choices)
    genre = models.ForeignKey(
        'platform_creative.Genre',
        on_delete=models.PROTECT,
        related_name='stories',
    )
    
    spice_level = models.ForeignKey(
        'platform_creative.SpiceLevel',
        on_delete=models.PROTECT,
        related_name='stories',
    )
```

---

## 4.5 Hybrid-Pattern (Core + Extension)

### Wann Hybrid?

- **Core-Werte haben Code-Logik** (prompt_guidance, scene_density)
- **Aber Custom-Erweiterungen** sollen möglich sein

### CorePacingType (Code)

```python
# platform_creative/enums/pacing.py

class CorePacingType(str, Enum):
    """Core Pacing Types mit Logik."""
    
    ACTION = "action"
    EMOTIONAL = "emotional"
    REFLECTIVE = "reflective"
    CLIMAX = "climax"
    RESOLUTION = "resolution"
    
    @property
    def prompt_guidance(self) -> str:
        guidance = {
            self.ACTION: "Schnelles Tempo, kurze Sätze, Spannung.",
            self.EMOTIONAL: "Tiefe Gefühle, innere Monologe.",
            self.REFLECTIVE: "Ruhiger Moment, Nachdenken.",
            self.CLIMAX: "Höhepunkt, alles kommt zusammen.",
            self.RESOLUTION: "Auflösung, emotionale Befriedigung.",
        }
        return guidance[self]
    
    @property
    def scene_density(self) -> str:
        return "high" if self in {self.ACTION, self.CLIMAX} else "low"
```

### PacingTypeExtension (DB)

```python
# platform_creative/models/pacing_extension.py

class PacingTypeExtension(BaseLookupTable):
    """Custom Pacing Types (z.B. atmospheric, romantic)."""
    
    prompt_guidance = models.TextField()
    scene_density = models.CharField(
        max_length=10,
        choices=[('high', 'High'), ('medium', 'Medium'), ('low', 'Low')],
        default='medium',
    )
    
    class Meta(BaseLookupTable.Meta):
        db_table = 'platform_pacing_extension'
```

### Service kombiniert beide

```python
# platform_creative/services/pacing_service.py

from typing import Optional, NamedTuple
from platform_creative.enums.pacing import CorePacingType
from platform_creative.models import PacingTypeExtension


class PacingInfo(NamedTuple):
    code: str
    prompt_guidance: str
    scene_density: str
    is_core: bool


class PacingTypeService:
    @classmethod
    def get_by_code(cls, code: str) -> Optional[PacingInfo]:
        # Erst Core prüfen
        try:
            core = CorePacingType(code)
            return PacingInfo(
                code=core.value,
                prompt_guidance=core.prompt_guidance,
                scene_density=core.scene_density,
                is_core=True,
            )
        except ValueError:
            pass
        
        # Dann DB
        ext = PacingTypeExtension.objects.get_by_code(code)
        if ext:
            return PacingInfo(
                code=ext.code,
                prompt_guidance=ext.prompt_guidance,
                scene_density=ext.scene_density,
                is_core=False,
            )
        
        return None
    
    @classmethod
    def get_all_choices(cls) -> list[tuple[str, str]]:
        choices = [(p.value, p.value.title()) for p in CorePacingType]
        choices += PacingTypeExtension.objects.choices()
        return choices
```

---

## 4.6 Zusammenfassung

| Kategorie | Beispiele | Speicherort | Logik |
|-----------|-----------|-------------|-------|
| **Code-Enum** | StoryStatus, ChapterStatus | Python Enum | `can_transition_to()` |
| **DB-Lookup** | Genre, SpiceLevel, TransportType | Lookup Table | Keine (nur Daten) |
| **Hybrid** | PacingType, StoryBeat | Core: Enum, Ext: DB | Core hat Logik |
# Kapitel 5: Pydantic-Django Integration

---

## 5.1 Übersicht

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│   DJANGO MODEL              PYDANTIC SCHEMA              POSTGRES           │
│   ───────────────           ──────────────               ────────           │
│                                                                              │
│   timing_spec = ...    ←→   TimingSpec(BaseModel)   ←→   JSONB Column       │
│                                                                              │
│   PydanticSchemaField       - Validation                 - GIN Index        │
│   - from_db_value()         - Serialization              - JSONB Operators  │
│   - get_prep_value()        - schema_version                                │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 5.2 PydanticSchemaField (gehärtet)

```python
# platform_core/db/fields.py

import importlib
import logging
from typing import Type, Optional, Any

from django.db import models
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)


class PydanticSchemaField(models.JSONField):
    """
    Django JSONField mit Pydantic-Validation.
    
    Features:
    - Automatische Serialisierung/Deserialisierung
    - Schema-Migration via Migrator
    - Strict Mode (keine silent fallbacks)
    - Structured Logging bei Fehlern
    """
    
    def __init__(
        self,
        schema_class: Type[BaseModel],
        strict: bool = True,
        migrator: Optional[str] = None,
        *args,
        **kwargs,
    ):
        self.schema_class = schema_class
        self.strict = strict
        self.migrator_path = migrator
        self._migrator_instance = None
        super().__init__(*args, **kwargs)
    
    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs['schema_class'] = self.schema_class
        kwargs['strict'] = self.strict
        if self.migrator_path:
            kwargs['migrator'] = self.migrator_path
        return name, path, args, kwargs
    
    def _get_migrator(self):
        """Lazy-load Migrator."""
        if self._migrator_instance is None and self.migrator_path:
            module_path, attr = self.migrator_path.rsplit(":", 1)
            mod = importlib.import_module(module_path)
            self._migrator_instance = getattr(mod, attr)()
        return self._migrator_instance
    
    def from_db_value(
        self,
        value: Any,
        expression,
        connection,
    ) -> Optional[BaseModel]:
        """
        DB → Python: Deserialisierung + Validation.
        
        1. Raw JSON aus DB
        2. Optional: Migration zu aktueller Version
        3. Pydantic Validation
        4. Bei Fehler: Exception (strict) oder None (non-strict)
        """
        if value is None:
            return None
        
        try:
            payload = value
            migrator = self._get_migrator()
            
            # Migration wenn nötig
            if migrator:
                payload, changed = migrator.migrate(payload)
                if changed:
                    logger.info(
                        "Schema migrated",
                        extra={
                            "field": self.name,
                            "schema": self.schema_class.__name__,
                            "from_version": value.get("schema_version"),
                            "to_version": payload.get("schema_version"),
                        },
                    )
            
            # Pydantic Validation
            return self.schema_class.model_validate(payload)
        
        except (ValidationError, Exception) as e:
            logger.exception(
                "Invalid JSON schema payload",
                extra={
                    "field": self.name,
                    "schema": self.schema_class.__name__,
                    "error": str(e),
                },
            )
            
            if self.strict:
                raise
            
            # Non-strict: None zurückgeben (NICHT Default!)
            # Service muss damit umgehen
            return None
    
    def get_prep_value(self, value: Any) -> Optional[dict]:
        """
        Python → DB: Serialisierung.
        
        Akzeptiert:
        - None
        - Pydantic Model Instance
        - Dict (wird validiert)
        """
        if value is None:
            return None
        
        if isinstance(value, self.schema_class):
            return value.model_dump(mode="json")
        
        if isinstance(value, dict):
            # Validieren vor dem Speichern
            validated = self.schema_class.model_validate(value)
            return validated.model_dump(mode="json")
        
        raise ValueError(
            f"Expected {self.schema_class.__name__} or dict, got {type(value)}"
        )
    
    def from_db_value_raw(self, value: Any) -> Optional[dict]:
        """Gibt Raw-JSON zurück (für Debugging/Migration)."""
        return value
```

---

## 5.3 Schema-Versionierung

### Im Pydantic Schema

```python
# platform_creative/domain/timing/spec.py

from pydantic import BaseModel, Field
from typing import Literal

CURRENT_VERSION = 2


class TimingSpec(BaseModel):
    """Versioniertes Schema."""
    
    # Version ist TEIL des JSON (nicht excluded!)
    schema_version: Literal[2] = Field(
        default=2,
        description="Schema-Version für Migrationen",
    )
    
    # ... weitere Felder
```

### Warum `schema_version` statt `_version`?

```python
# ❌ PROBLEM: _version wird von Pydantic als private behandelt
class BadSpec(BaseModel):
    _version: int = 2  # Wird NICHT serialisiert!

# ✅ LÖSUNG: Normaler Feldname
class GoodSpec(BaseModel):
    schema_version: int = 2  # Wird serialisiert
```

---

## 5.4 Migrator-Pattern

```python
# platform_creative/domain/timing/migrator.py

from typing import Dict, Any, Tuple, Callable

MigrationFn = Callable[[Dict[str, Any]], Dict[str, Any]]


class MigrationError(Exception):
    pass


class TimingSpecMigrator:
    """
    Migriert alte JSON-Payloads auf aktuelle Schema-Version.
    
    Prinzipien:
    - Jede Version hat explizite Migration
    - Keine Daten gehen verloren
    - Idempotent (mehrfach anwendbar)
    """
    
    current_version = 2
    
    def detect_version(self, payload: Dict[str, Any]) -> int:
        """Erkennt Version aus Payload."""
        # Explizite Version
        if "schema_version" in payload:
            return payload["schema_version"]
        if "_version" in payload:  # Legacy
            return payload["_version"]
        
        # Heuristik für Legacy-Daten ohne Version
        if "travel" in payload and isinstance(payload["travel"], dict):
            return 2
        
        return 1  # Ältestes Format
    
    def migrate(self, payload: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
        """
        Migriert Payload auf aktuelle Version.
        
        Returns:
            (migrated_payload, changed)
        """
        version = self.detect_version(payload)
        changed = False
        
        while version < self.current_version:
            step_fn = self._get_step(version, version + 1)
            payload = step_fn(payload)
            version += 1
            changed = True
        
        # Stelle sicher dass Version gesetzt ist
        payload["schema_version"] = self.current_version
        
        return payload, changed
    
    def _get_step(self, from_v: int, to_v: int) -> MigrationFn:
        """Holt Migration-Funktion für einen Schritt."""
        steps = {
            (1, 2): self._v1_to_v2,
        }
        
        if (from_v, to_v) not in steps:
            raise MigrationError(f"No migration from v{from_v} to v{to_v}")
        
        return steps[(from_v, to_v)]
    
    def _v1_to_v2(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Migration v1 → v2."""
        payload = dict(payload)  # Copy
        
        # Neue Felder mit Defaults
        payload.setdefault("reader_speed_wpm", 250)
        payload.setdefault("source_type", "manual")
        payload.setdefault("chapters", [])
        
        # Restructure: Flache Travel-Felder → travel Object
        if "is_travel_synced" in payload:
            payload["travel"] = {
                "is_travel_synced": bool(payload.pop("is_travel_synced")),
                "trip_id": payload.pop("trip_id", None),
            }
        
        # Legacy-Keys entfernen
        payload.pop("_version", None)
        
        return payload
```

---

## 5.5 Nutzung im Django Model

```python
# apps/stories/models/story.py

from django.db import models
from platform_core.db.fields import PydanticSchemaField
from platform_creative.domain.timing.spec import TimingSpec


class Story(models.Model):
    # ... andere Felder
    
    timing_spec = PydanticSchemaField(
        schema_class=TimingSpec,
        strict=True,  # PROD: True empfohlen
        migrator="platform_creative.domain.timing.migrator:TimingSpecMigrator",
        null=True,
        blank=True,
    )
    
    # Hot Columns für Queries
    timing_total_minutes = models.IntegerField(null=True, db_index=True)
    is_travel_synced = models.BooleanField(default=False, db_index=True)
    
    def sync_timing_hot_columns(self):
        """Synchronisiert Hot Columns aus Spec."""
        spec = self.timing_spec
        if spec:
            self.timing_total_minutes = spec.derived_total_minutes()
            self.is_travel_synced = spec.is_travel_synced
        else:
            self.timing_total_minutes = None
            self.is_travel_synced = False
```

---

## 5.6 Service: Spec-Updates

```python
# apps/stories/services/timing_service.py

from django.db import transaction
from apps.stories.models import Story
from platform_creative.domain.timing.spec import TimingSpec


@transaction.atomic
def update_timing_spec(story_id: int, new_spec: TimingSpec) -> Story:
    """
    Aktualisiert Timing-Spec mit Hot-Column-Sync.
    
    IMMER diese Funktion nutzen, nie story.timing_spec = ... direkt!
    """
    story = Story.objects.select_for_update().get(id=story_id)
    
    story.timing_spec = new_spec
    story.sync_timing_hot_columns()
    
    story.save(update_fields=[
        "timing_spec",
        "timing_total_minutes",
        "is_travel_synced",
        "updated_at",
    ])
    
    return story


@transaction.atomic
def ensure_timing_spec(story_id: int) -> Story:
    """
    Stellt sicher dass Story einen Timing-Spec hat.
    
    Idempotent: Erstellt nur wenn nicht vorhanden.
    """
    story = Story.objects.select_for_update().get(id=story_id)
    
    if story.timing_spec is None:
        story.timing_spec = TimingSpec(
            source_type="manual",
            total_chapters=story.total_chapters or 10,
            total_words=story.total_words or 30000,
        )
        story.sync_timing_hot_columns()
        story.save(update_fields=[
            "timing_spec",
            "timing_total_minutes",
            "is_travel_synced",
        ])
    
    return story
```

---

## 5.7 Postgres Indizes

```sql
-- Migration: JSONB GIN Index für flexible Queries
CREATE INDEX CONCURRENTLY idx_story_timing_spec_gin 
ON stories_story USING GIN (timing_spec);

-- Beispiel-Queries die davon profitieren:
SELECT * FROM stories_story 
WHERE timing_spec @> '{"source_type": "travel_beat"}';

SELECT * FROM stories_story 
WHERE timing_spec -> 'travel' ->> 'is_travel_synced' = 'true';
```

```python
# Django Migration
class Migration(migrations.Migration):
    operations = [
        migrations.RunSQL(
            sql="""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS 
            idx_story_timing_spec_gin ON stories_story USING GIN (timing_spec);
            """,
            reverse_sql="DROP INDEX IF EXISTS idx_story_timing_spec_gin;",
        ),
    ]
```
# Kapitel 6: Timing/Story Domain

---

## 6.1 Übersicht

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  TIMING DOMAIN                                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  SPEC (persistiert)           DERIVED (berechnet)        PROVIDERS          │
│  ─────────────────            ───────────────────        ─────────          │
│                                                                              │
│  TimingSpec                   TimingConstraints          build_constraints() │
│  ├─ schema_version            ├─ chapters{}              build_metrics()     │
│  ├─ total_chapters            │   ├─ word_count_min      calculate_beats()   │
│  ├─ total_words               │   └─ word_count_max                          │
│  ├─ reader_speed_wpm          │                                              │
│  ├─ chapters[]                TimingMetrics                                  │
│  │   ├─ word_count_target     ├─ total_minutes                               │
│  │   └─ reading_context_code  └─ chapter_minutes{}                           │
│  └─ travel                                                                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 6.2 TimingSpec (Persistiert)

```python
# platform_creative/domain/timing/spec.py

from pydantic import BaseModel, Field, model_validator
from typing import List, Optional, Literal

CURRENT_VERSION = 2


class ChapterSpec(BaseModel):
    """Kapitel-Spezifikation."""
    
    chapter_number: int = Field(..., ge=1)
    word_count_target: int = Field(..., ge=100)
    
    # FK-Codes zu Lookup Tables
    reading_context_code: str = "general"
    pacing_code: str = "action"
    
    # Story Structure
    story_beat: Optional[str] = None
    act: Optional[str] = None
    
    # Travel-Sync (optional)
    location_city: Optional[str] = None
    location_country: Optional[str] = None
    reading_date: Optional[str] = None  # ISO date


class TravelMeta(BaseModel):
    """Travel-Sync Metadaten."""
    
    is_travel_synced: bool = False
    trip_id: Optional[int] = None
    enforce_word_counts: bool = True
    word_count_tolerance: float = Field(0.1, ge=0, le=0.5)


class TimingSpec(BaseModel):
    """
    Timing-Spezifikation für eine Story.
    
    Wird in DB persistiert (JSONB).
    Enthält NUR Fakten, keine berechneten Werte.
    """
    
    schema_version: Literal[2] = 2
    
    # Source
    source_type: str = "manual"  # manual, travel_beat, import
    source_id: Optional[str] = None
    
    # Core Parameters
    total_chapters: int = Field(..., ge=1, le=50)
    total_words: int = Field(..., ge=1000)
    reader_speed_wpm: int = Field(250, ge=50, le=1000)
    
    # Structure
    structure_type: str = "save_the_cat"  # save_the_cat, three_act, custom
    
    # Chapters
    chapters: List[ChapterSpec] = Field(default_factory=list)
    
    # Travel
    travel: Optional[TravelMeta] = None
    
    # === Derived Methods (nicht persistiert) ===
    
    def derived_total_minutes(self) -> int:
        return self.total_words // self.reader_speed_wpm
    
    def derived_average_chapter_words(self) -> int:
        if not self.chapters:
            return self.total_words // self.total_chapters
        return sum(c.word_count_target for c in self.chapters) // len(self.chapters)
    
    @property
    def is_travel_synced(self) -> bool:
        return bool(self.travel and self.travel.is_travel_synced)
    
    def get_chapter(self, number: int) -> Optional[ChapterSpec]:
        for ch in self.chapters:
            if ch.chapter_number == number:
                return ch
        return None
    
    # === Validation ===
    
    @model_validator(mode="after")
    def ensure_chapters(self):
        """Auto-generiert Kapitel wenn leer."""
        if not self.chapters and self.total_chapters > 0:
            per_chapter = self.total_words // self.total_chapters
            self.chapters = [
                ChapterSpec(
                    chapter_number=i + 1,
                    word_count_target=per_chapter,
                )
                for i in range(self.total_chapters)
            ]
        return self
    
    @model_validator(mode="after")
    def validate_chapter_numbers(self):
        """Prüft Kapitel-Nummerierung."""
        if self.chapters:
            nums = [c.chapter_number for c in self.chapters]
            if len(set(nums)) != len(nums):
                raise ValueError("Duplicate chapter numbers")
            if sorted(nums) != list(range(1, len(nums) + 1)):
                raise ValueError("Chapter numbers must be 1..n")
        return self
```

---

## 6.3 Derived: Constraints & Metrics

```python
# platform_creative/domain/timing/derived.py

from pydantic import BaseModel
from typing import Dict, Optional


class ChapterConstraints(BaseModel):
    """Constraints für ein Kapitel (berechnet)."""
    
    chapter_number: int
    word_count_target: int
    word_count_min: int
    word_count_max: int
    reading_minutes: int
    
    # Context (aus Lookup)
    reading_context_code: str
    pacing_code: str
    story_beat: Optional[str] = None


class TimingConstraints(BaseModel):
    """Alle Kapitel-Constraints."""
    
    chapters: Dict[int, ChapterConstraints]
    
    def get_chapter(self, number: int) -> Optional[ChapterConstraints]:
        return self.chapters.get(number)


class TimingMetrics(BaseModel):
    """Aggregierte Metriken (berechnet)."""
    
    total_words: int
    total_minutes: int
    total_chapters: int
    
    average_chapter_words: int
    average_chapter_minutes: float
    
    chapter_minutes: Dict[int, int]
    
    words_per_act: Dict[str, int]
```

---

## 6.4 Providers (Pure Functions)

```python
# platform_creative/domain/timing/providers.py

from typing import Optional
from .spec import TimingSpec, ChapterSpec
from .derived import TimingConstraints, ChapterConstraints, TimingMetrics


def build_constraints(
    spec: TimingSpec,
    tolerance: Optional[float] = None,
) -> TimingConstraints:
    """
    Berechnet Constraints aus Spec.
    
    Pure Function: Keine DB, kein IO.
    """
    # Tolerance aus Travel-Meta oder Default
    tol = tolerance
    if tol is None:
        tol = spec.travel.word_count_tolerance if spec.travel else 0.1
    
    chapters = {}
    
    for ch in spec.chapters:
        target = ch.word_count_target
        chapters[ch.chapter_number] = ChapterConstraints(
            chapter_number=ch.chapter_number,
            word_count_target=target,
            word_count_min=int(target * (1 - tol)),
            word_count_max=int(target * (1 + tol)),
            reading_minutes=target // spec.reader_speed_wpm,
            reading_context_code=ch.reading_context_code,
            pacing_code=ch.pacing_code,
            story_beat=ch.story_beat,
        )
    
    return TimingConstraints(chapters=chapters)


def build_metrics(spec: TimingSpec) -> TimingMetrics:
    """Berechnet Metriken aus Spec."""
    
    chapter_minutes = {
        ch.chapter_number: ch.word_count_target // spec.reader_speed_wpm
        for ch in spec.chapters
    }
    
    total_minutes = sum(chapter_minutes.values())
    
    # Words per Act
    words_per_act: dict[str, int] = {}
    for ch in spec.chapters:
        act = ch.act or "unknown"
        words_per_act[act] = words_per_act.get(act, 0) + ch.word_count_target
    
    return TimingMetrics(
        total_words=spec.total_words,
        total_minutes=total_minutes,
        total_chapters=spec.total_chapters,
        average_chapter_words=spec.derived_average_chapter_words(),
        average_chapter_minutes=total_minutes / len(chapter_minutes) if chapter_minutes else 0,
        chapter_minutes=chapter_minutes,
        words_per_act=words_per_act,
    )


def calculate_chapter_beats(
    total_chapters: int,
    structure_type: str = "save_the_cat",
) -> list[dict]:
    """
    Berechnet Story Beats für Kapitelanzahl.
    
    Returns: [{chapter_number, beat, act, pacing}, ...]
    """
    
    if structure_type == "save_the_cat":
        return _save_the_cat_beats(total_chapters)
    elif structure_type == "three_act":
        return _three_act_beats(total_chapters)
    else:
        return _default_beats(total_chapters)


def _save_the_cat_beats(total_chapters: int) -> list[dict]:
    """Save the Cat Beat Sheet."""
    
    # Full beats für 15+ Kapitel
    FULL_BEATS = [
        ("opening_image", "act_1", "reflective"),
        ("setup", "act_1", "emotional"),
        ("theme_stated", "act_1", "emotional"),
        ("catalyst", "act_1", "action"),
        ("debate", "act_1", "emotional"),
        ("break_into_two", "act_2a", "action"),
        ("b_story", "act_2a", "emotional"),
        ("fun_and_games", "act_2a", "action"),
        ("midpoint", "act_2a", "climax"),
        ("bad_guys_close_in", "act_2b", "action"),
        ("all_is_lost", "act_2b", "emotional"),
        ("dark_night", "act_2b", "reflective"),
        ("break_into_three", "act_3", "action"),
        ("finale", "act_3", "climax"),
        ("final_image", "act_3", "resolution"),
    ]
    
    # Kondensierte Version für weniger Kapitel
    SHORT_BEATS = [
        ("opening_image", "act_1", "reflective"),
        ("catalyst", "act_1", "action"),
        ("fun_and_games", "act_2a", "action"),
        ("midpoint", "act_2a", "climax"),
        ("all_is_lost", "act_2b", "emotional"),
        ("finale", "act_3", "climax"),
        ("final_image", "act_3", "resolution"),
    ]
    
    beats = FULL_BEATS if total_chapters >= 15 else SHORT_BEATS
    
    result = []
    for i in range(total_chapters):
        beat_idx = int(i * len(beats) / total_chapters)
        beat, act, pacing = beats[beat_idx]
        result.append({
            "chapter_number": i + 1,
            "beat": beat,
            "act": act,
            "pacing": pacing,
        })
    
    return result


def _three_act_beats(total_chapters: int) -> list[dict]:
    """Einfache 3-Akt Struktur."""
    result = []
    
    for i in range(total_chapters):
        progress = i / total_chapters
        
        if progress < 0.25:
            act, pacing = "act_1", "emotional"
        elif progress < 0.75:
            act, pacing = "act_2", "action"
        else:
            act, pacing = "act_3", "climax"
        
        result.append({
            "chapter_number": i + 1,
            "beat": None,
            "act": act,
            "pacing": pacing,
        })
    
    return result


def _default_beats(total_chapters: int) -> list[dict]:
    """Default ohne spezifische Struktur."""
    return [
        {"chapter_number": i + 1, "beat": None, "act": None, "pacing": "action"}
        for i in range(total_chapters)
    ]
```

---

## 6.5 TimingConstraintProvider (Travel Beat)

```python
# platform_creative/domain/timing/providers.py (Fortsetzung)

from typing import List
from platform_creative.models import ReadingContext


def from_reading_slots(
    reading_slots: List[dict],
    reader_speed_wpm: int = 250,
    structure_type: str = "save_the_cat",
    source_type: str = "travel_beat",
    source_id: Optional[str] = None,
) -> TimingSpec:
    """
    Erstellt TimingSpec aus Reading Slots (Travel Beat).
    
    Args:
        reading_slots: [
            {
                "date": "2025-02-15",
                "minutes": 120,
                "slot_type": "transport_flight",
                "city": "Paris",
                "country": "France",
            },
            ...
        ]
    """
    total_chapters = len(reading_slots)
    
    # Beats berechnen
    beats = calculate_chapter_beats(total_chapters, structure_type)
    
    chapters = []
    total_words = 0
    
    for i, slot in enumerate(reading_slots):
        minutes = slot["minutes"]
        word_count = minutes * reader_speed_wpm
        total_words += word_count
        
        beat_info = beats[i] if i < len(beats) else {}
        
        chapters.append(ChapterSpec(
            chapter_number=i + 1,
            word_count_target=word_count,
            reading_context_code=slot.get("slot_type", "general"),
            pacing_code=beat_info.get("pacing", "action"),
            story_beat=beat_info.get("beat"),
            act=beat_info.get("act"),
            location_city=slot.get("city"),
            location_country=slot.get("country"),
            reading_date=slot.get("date"),
        ))
    
    return TimingSpec(
        source_type=source_type,
        source_id=source_id,
        total_chapters=total_chapters,
        total_words=total_words,
        reader_speed_wpm=reader_speed_wpm,
        structure_type=structure_type,
        chapters=chapters,
        travel=TravelMeta(
            is_travel_synced=True,
            trip_id=int(source_id) if source_id else None,
        ),
    )


def from_uniform(
    total_chapters: int,
    total_words: int,
    reader_speed_wpm: int = 250,
    structure_type: str = "save_the_cat",
) -> TimingSpec:
    """
    Erstellt TimingSpec mit gleichmäßiger Verteilung.
    
    Für Stories ohne Travel-Sync.
    """
    per_chapter = total_words // total_chapters
    beats = calculate_chapter_beats(total_chapters, structure_type)
    
    chapters = []
    for i in range(total_chapters):
        beat_info = beats[i] if i < len(beats) else {}
        chapters.append(ChapterSpec(
            chapter_number=i + 1,
            word_count_target=per_chapter,
            pacing_code=beat_info.get("pacing", "action"),
            story_beat=beat_info.get("beat"),
            act=beat_info.get("act"),
        ))
    
    return TimingSpec(
        source_type="manual",
        total_chapters=total_chapters,
        total_words=total_words,
        reader_speed_wpm=reader_speed_wpm,
        structure_type=structure_type,
        chapters=chapters,
    )
```

---

## 6.6 Zusammenfassung

| Komponente | Typ | Persistiert | Zweck |
|------------|-----|-------------|-------|
| `TimingSpec` | Pydantic | ✅ Ja | Fakten/Inputs |
| `ChapterSpec` | Pydantic | ✅ Ja (in Spec) | Kapitel-Details |
| `TravelMeta` | Pydantic | ✅ Ja (in Spec) | Travel-Sync Info |
| `TimingConstraints` | Pydantic | ❌ Nein | Berechnete Limits |
| `TimingMetrics` | Pydantic | ❌ Nein | Aggregierte Werte |
| `build_constraints()` | Provider | - | Spec → Constraints |
| `build_metrics()` | Provider | - | Spec → Metrics |
| `from_reading_slots()` | Provider | - | Slots → Spec |
# Kapitel 7: Lookup Tables - Initial Data

> Siehe Kapitel 4 für BaseLookupTable und Modell-Definitionen.
> Dieses Kapitel zeigt die **Initial Data Migrations**.

---

## 7.1 Genre

```python
# platform_creative/migrations/0002_seed_genres.py

GENRES = [
    {
        'code': 'romance',
        'display_name': 'Romance',
        'display_name_de': 'Liebesroman',
        'prompt_template': '''GENRE: Romance
Fokus auf emotionale Entwicklung und Beziehungsaufbau.
Romantische Spannung, Chemie, bedeutsame Momente.
Happy End oder Happily-Ever-After erwartet.''',
        'default_pacing': 'emotional',
        'is_system': True,
        'sort_order': 1,
    },
    {
        'code': 'thriller',
        'display_name': 'Thriller',
        'display_name_de': 'Thriller',
        'prompt_template': '''GENRE: Thriller
Hochspannend, actionreich, ständige Bedrohung.
Schnelles Tempo, kurze Kapitel, Cliffhanger.
Plot-Twists und unerwartete Wendungen.''',
        'default_pacing': 'action',
        'is_system': True,
        'sort_order': 2,
    },
    {
        'code': 'mystery',
        'display_name': 'Mystery',
        'display_name_de': 'Krimi',
        'prompt_template': '''GENRE: Mystery
Ein Rätsel muss gelöst werden.
Hinweise verteilen, falsche Fährten legen.
Auflösung am Ende.''',
        'default_pacing': 'balanced',
        'is_system': True,
        'sort_order': 3,
    },
    {
        'code': 'romantic_suspense',
        'display_name': 'Romantic Suspense',
        'display_name_de': 'Romantic Suspense',
        'prompt_template': '''GENRE: Romantic Suspense
Kombination aus Romance und Thriller.
Liebesgeschichte vor Spannungshintergrund.
Gefahr bringt Protagonisten zusammen.''',
        'default_pacing': 'balanced',
        'is_system': True,
        'sort_order': 4,
    },
    {
        'code': 'fantasy',
        'display_name': 'Fantasy',
        'display_name_de': 'Fantasy',
        'prompt_template': '''GENRE: Fantasy
Magische Elemente, fantastische Welt.
Klare Regeln für Magie etablieren.
Held auf Reise oder Quest.''',
        'default_pacing': 'balanced',
        'is_system': True,
        'sort_order': 5,
    },
]


def seed_genres(apps, schema_editor):
    Genre = apps.get_model('platform_creative', 'Genre')
    for data in GENRES:
        Genre.objects.update_or_create(code=data['code'], defaults=data)
```

---

## 7.2 SpiceLevel

```python
SPICE_LEVELS = [
    {
        'code': 'none',
        'display_name': 'None',
        'display_name_de': 'Keine expliziten Szenen',
        'intensity': 1,
        'prompt_guidance': 'Keine romantischen oder intimen Szenen.',
        'age_rating': '12+',
        'is_system': True,
        'sort_order': 1,
    },
    {
        'code': 'mild',
        'display_name': 'Mild',
        'display_name_de': 'Angedeutete Intimität',
        'intensity': 2,
        'prompt_guidance': 'Küsse und Umarmungen okay. Intimität nur angedeutet, "Fade to Black".',
        'age_rating': '14+',
        'is_system': True,
        'sort_order': 2,
    },
    {
        'code': 'moderate',
        'display_name': 'Moderate',
        'display_name_de': 'Sinnliche Szenen',
        'intensity': 3,
        'prompt_guidance': 'Sinnliche Szenen erlaubt, aber nicht explizit. Gefühle > Details.',
        'age_rating': '16+',
        'is_system': True,
        'sort_order': 3,
    },
    {
        'code': 'spicy',
        'display_name': 'Spicy',
        'display_name_de': 'Explizite Szenen',
        'intensity': 4,
        'prompt_guidance': 'Explizitere Szenen erlaubt, aber mit emotionalem Kontext.',
        'age_rating': '18+',
        'is_system': True,
        'sort_order': 4,
    },
]
```

---

## 7.3 ReadingContext

```python
READING_CONTEXTS = [
    # Transport
    {'code': 'transport_flight', 'display_name': 'Flight', 'display_name_de': 'Flug',
     'category': 'transport', 'recommended_pacing': 'action', 'cliffhanger_tendency': 0.8,
     'default_reading_minutes': 120, 'is_system': True, 'sort_order': 1},
    {'code': 'transport_train', 'display_name': 'Train', 'display_name_de': 'Zug',
     'category': 'transport', 'recommended_pacing': 'balanced', 'cliffhanger_tendency': 0.6,
     'default_reading_minutes': 90, 'is_system': True, 'sort_order': 2},
    {'code': 'transport_bus', 'display_name': 'Bus', 'display_name_de': 'Bus',
     'category': 'transport', 'recommended_pacing': 'action', 'cliffhanger_tendency': 0.7,
     'default_reading_minutes': 60, 'is_system': True, 'sort_order': 3},
    
    # Evening
    {'code': 'evening_hotel', 'display_name': 'Hotel Evening', 'display_name_de': 'Abend im Hotel',
     'category': 'evening', 'recommended_pacing': 'emotional', 'cliffhanger_tendency': 0.3,
     'default_reading_minutes': 45, 'is_system': True, 'sort_order': 10},
    {'code': 'evening_resort', 'display_name': 'Resort Evening', 'display_name_de': 'Abend im Resort',
     'category': 'evening', 'recommended_pacing': 'reflective', 'cliffhanger_tendency': 0.2,
     'default_reading_minutes': 60, 'is_system': True, 'sort_order': 11},
    
    # Leisure
    {'code': 'pool_beach', 'display_name': 'Pool/Beach', 'display_name_de': 'Pool/Strand',
     'category': 'leisure', 'recommended_pacing': 'action', 'cliffhanger_tendency': 0.5,
     'default_reading_minutes': 90, 'is_system': True, 'sort_order': 20},
    
    # General
    {'code': 'general', 'display_name': 'General', 'display_name_de': 'Allgemein',
     'category': 'other', 'recommended_pacing': 'balanced', 'cliffhanger_tendency': 0.5,
     'default_reading_minutes': 30, 'is_system': True, 'sort_order': 99},
]
```

---

## 7.4 AccommodationType & TransportType

```python
ACCOMMODATION_TYPES = [
    {'code': 'hotel', 'display_name': 'Hotel', 'display_name_de': 'Hotel',
     'evening_reading_minutes': 45, 'morning_reading_minutes': 20,
     'comfort_level': 4, 'icon': 'bi-building', 'is_system': True, 'sort_order': 1},
    {'code': 'resort', 'display_name': 'Resort', 'display_name_de': 'Resort',
     'evening_reading_minutes': 60, 'morning_reading_minutes': 30,
     'comfort_level': 5, 'icon': 'bi-umbrella', 'is_system': True, 'sort_order': 2},
    {'code': 'airbnb', 'display_name': 'Airbnb', 'display_name_de': 'Ferienwohnung',
     'evening_reading_minutes': 50, 'morning_reading_minutes': 25,
     'comfort_level': 4, 'icon': 'bi-house', 'is_system': True, 'sort_order': 3},
    {'code': 'hostel', 'display_name': 'Hostel', 'display_name_de': 'Hostel',
     'evening_reading_minutes': 30, 'morning_reading_minutes': 10,
     'comfort_level': 2, 'icon': 'bi-people', 'is_system': True, 'sort_order': 4},
]

TRANSPORT_TYPES = [
    {'code': 'flight', 'display_name': 'Flight', 'display_name_de': 'Flug',
     'reading_efficiency': 0.8, 'typical_duration_minutes': 180,
     'comfort_level': 4, 'icon': 'bi-airplane', 'is_system': True, 'sort_order': 1},
    {'code': 'train', 'display_name': 'Train', 'display_name_de': 'Zug',
     'reading_efficiency': 0.9, 'typical_duration_minutes': 120,
     'comfort_level': 5, 'icon': 'bi-train-front', 'is_system': True, 'sort_order': 2},
    {'code': 'bus', 'display_name': 'Bus', 'display_name_de': 'Bus',
     'reading_efficiency': 0.6, 'typical_duration_minutes': 90,
     'comfort_level': 2, 'icon': 'bi-bus-front', 'is_system': True, 'sort_order': 3},
    {'code': 'car', 'display_name': 'Car (Passenger)', 'display_name_de': 'Auto (Beifahrer)',
     'reading_efficiency': 0.5, 'typical_duration_minutes': 120,
     'comfort_level': 3, 'icon': 'bi-car-front', 'is_system': True, 'sort_order': 4},
    {'code': 'ferry', 'display_name': 'Ferry', 'display_name_de': 'Fähre',
     'reading_efficiency': 0.85, 'typical_duration_minutes': 180,
     'comfort_level': 4, 'icon': 'bi-water', 'is_system': True, 'sort_order': 5},
]
```

---

## 7.5 PacingTypeExtension (Hybrid)

```python
PACING_EXTENSIONS = [
    {
        'code': 'atmospheric',
        'display_name': 'Atmospheric',
        'display_name_de': 'Atmosphärisch',
        'prompt_guidance': 'Langsam, sinnlich, Fokus auf Setting und Atmosphäre.',
        'scene_density': 'low',
        'is_system': True,
        'sort_order': 10,
    },
    {
        'code': 'romantic',
        'display_name': 'Romantic',
        'display_name_de': 'Romantisch',
        'prompt_guidance': 'Chemie zwischen Charakteren, Spannung, zarte Momente.',
        'scene_density': 'medium',
        'is_system': True,
        'sort_order': 11,
    },
    {
        'code': 'mysterious',
        'display_name': 'Mysterious',
        'display_name_de': 'Mysteriös',
        'prompt_guidance': 'Hinweise streuen, Fragen aufwerfen, Suspense aufbauen.',
        'scene_density': 'medium',
        'is_system': True,
        'sort_order': 12,
    },
]
```
# Kapitel 8: Services & Providers

---

## 8.1 Begriffe

| Begriff | Verantwortung | I/O | Beispiel |
|---------|---------------|-----|----------|
| **Provider** | Pure Berechnungen | Keine | `build_constraints(spec)` |
| **Service** | Orchestrierung, DB, LLM | Ja | `generate_story(story_id)` |
| **Selector** | Lesende DB-Queries | Read-only | `get_story_with_chapters(id)` |

---

## 8.2 Provider-Pattern

### Regeln

1. **Keine DB** - Providers haben keinen Zugriff auf Django ORM
2. **Keine I/O** - Keine HTTP, keine Filesystem-Zugriffe
3. **Deterministisch** - Gleiche Inputs = Gleiche Outputs
4. **Testbar** - Unit-Tests ohne Fixtures/Mocks

### Beispiel

```python
# platform_creative/domain/timing/providers.py

from .spec import TimingSpec
from .derived import TimingConstraints


def build_constraints(spec: TimingSpec, tolerance: float = 0.1) -> TimingConstraints:
    """
    Pure Function: Spec → Constraints.
    
    ✅ Keine DB
    ✅ Keine I/O
    ✅ Deterministisch
    """
    chapters = {}
    for ch in spec.chapters:
        target = ch.word_count_target
        chapters[ch.chapter_number] = ChapterConstraints(
            chapter_number=ch.chapter_number,
            word_count_min=int(target * (1 - tolerance)),
            word_count_max=int(target * (1 + tolerance)),
        )
    return TimingConstraints(chapters=chapters)
```

### Test

```python
# tests/domain/timing/test_providers.py

def test_build_constraints_deterministic():
    spec = TimingSpec(total_chapters=3, total_words=9000)
    
    result1 = build_constraints(spec, tolerance=0.1)
    result2 = build_constraints(spec, tolerance=0.1)
    
    assert result1 == result2  # Deterministisch
    assert result1.chapters[1].word_count_min == 2700  # 3000 * 0.9
    assert result1.chapters[1].word_count_max == 3300  # 3000 * 1.1
```

---

## 8.3 Service-Pattern

### Regeln

1. **Orchestrierung** - Koordiniert Providers, Selectors, DB
2. **Transaktionen** - `@transaction.atomic` für Konsistenz
3. **Locking** - `select_for_update()` gegen Race Conditions
4. **Idempotenz** - Mehrfach aufrufbar mit gleichem Ergebnis

### Beispiel: Timing Service

```python
# apps/stories/services/timing_service.py

from django.db import transaction
from apps.stories.models import Story
from platform_creative.domain.timing.spec import TimingSpec
from platform_creative.domain.timing.providers import build_constraints


@transaction.atomic
def ensure_timing_spec(story_id: int) -> Story:
    """
    Stellt sicher dass Story einen Timing-Spec hat.
    
    Idempotent: Erstellt nur wenn nicht vorhanden.
    """
    story = Story.objects.select_for_update().get(id=story_id)
    
    if story.timing_spec is None:
        story.timing_spec = TimingSpec(
            source_type="manual",
            total_chapters=story.total_chapters or 10,
            total_words=story.total_words or 30000,
        )
        story.sync_timing_hot_columns()
        story.save(update_fields=["timing_spec", "timing_total_minutes", "is_travel_synced"])
    
    return story


@transaction.atomic
def update_timing_spec(story_id: int, new_spec: TimingSpec) -> Story:
    """
    Aktualisiert Timing-Spec mit Hot-Column-Sync.
    """
    story = Story.objects.select_for_update().get(id=story_id)
    
    story.timing_spec = new_spec
    story.sync_timing_hot_columns()
    story.save(update_fields=["timing_spec", "timing_total_minutes", "is_travel_synced"])
    
    return story


def get_timing_constraints(story_id: int) -> TimingConstraints:
    """
    Holt Timing-Constraints für eine Story.
    
    Kombiniert DB-Read (Selector) mit Berechnung (Provider).
    """
    story = Story.objects.get(id=story_id)
    
    if story.timing_spec is None:
        raise ValueError(f"Story {story_id} has no timing_spec")
    
    return build_constraints(story.timing_spec)
```

### Beispiel: Generation Service

```python
# apps/stories/services/generation_service.py

from django.db import transaction
from apps.stories.models import Story, Chapter
from platform_creative.enums.status import StoryStatus, ChapterStatus
from platform_creative.domain.timing.providers import build_constraints


class StoryGenerationService:
    """Orchestriert Story-Generierung."""
    
    @transaction.atomic
    def start_generation(self, story_id: int) -> Story:
        """Startet Generierung (PENDING → GENERATING)."""
        story = Story.objects.select_for_update().get(id=story_id)
        
        # Status-Transition validieren
        if not story.status_enum.can_transition_to(StoryStatus.GENERATING):
            raise ValueError(f"Cannot start generation in status {story.status}")
        
        # Timing-Spec sicherstellen
        if story.timing_spec is None:
            raise ValueError("Cannot generate without timing_spec")
        
        story.status = StoryStatus.GENERATING.value
        story.generation_started = timezone.now()
        story.save(update_fields=["status", "generation_started"])
        
        return story
    
    @transaction.atomic
    def complete_generation(self, story_id: int) -> Story:
        """Markiert Generierung als abgeschlossen."""
        story = Story.objects.select_for_update().get(id=story_id)
        
        story.status = StoryStatus.COMPLETED.value
        story.generation_completed = timezone.now()
        story.total_words = sum(ch.word_count for ch in story.chapters.all())
        story.save(update_fields=["status", "generation_completed", "total_words"])
        
        return story
    
    @transaction.atomic
    def fail_generation(self, story_id: int, error: str) -> Story:
        """Markiert Generierung als fehlgeschlagen."""
        story = Story.objects.select_for_update().get(id=story_id)
        
        story.status = StoryStatus.FAILED.value
        story.generation_error = error
        story.save(update_fields=["status", "generation_error"])
        
        return story
```

---

## 8.4 Selector-Pattern

### Regeln

1. **Read-Only** - Keine Schreiboperationen
2. **Optimiert** - `select_related`, `prefetch_related`
3. **Typisiert** - Klare Return-Typen

### Beispiel

```python
# apps/stories/selectors/story_selectors.py

from typing import Optional, List
from django.db.models import QuerySet, Prefetch
from apps.stories.models import Story, Chapter


def get_story_by_id(story_id: int) -> Optional[Story]:
    """Holt Story by ID."""
    return Story.objects.filter(id=story_id).first()


def get_story_with_chapters(story_id: int) -> Optional[Story]:
    """Holt Story mit allen Kapiteln (optimiert)."""
    return Story.objects.prefetch_related(
        Prefetch('chapters', queryset=Chapter.objects.order_by('number'))
    ).filter(id=story_id).first()


def get_story_with_timing(story_id: int) -> Optional[Story]:
    """Holt Story mit Timing-relevanten Daten."""
    return Story.objects.select_related(
        'genre', 'spice_level', 'ending_type'
    ).filter(id=story_id).first()


def list_stories_for_user(user_id: int, status: Optional[str] = None) -> QuerySet[Story]:
    """Listet Stories eines Users."""
    qs = Story.objects.filter(user_id=user_id).order_by('-created_at')
    
    if status:
        qs = qs.filter(status=status)
    
    return qs


def list_pending_stories() -> QuerySet[Story]:
    """Listet alle Stories die auf Generierung warten."""
    return Story.objects.filter(
        status=StoryStatus.PENDING.value
    ).select_related('user', 'trip').order_by('created_at')
```

---

## 8.5 Zusammenspiel

```python
# apps/stories/views.py

from django.views import View
from apps.stories.services.timing_service import ensure_timing_spec, get_timing_constraints
from apps.stories.services.generation_service import StoryGenerationService
from apps.stories.selectors import get_story_with_chapters


class StoryDetailView(View):
    def get(self, request, story_id):
        # Selector: Optimierter DB-Read
        story = get_story_with_chapters(story_id)
        
        if not story:
            raise Http404()
        
        # Provider: Pure Berechnung (via Service)
        constraints = get_timing_constraints(story_id)
        
        return render(request, 'stories/detail.html', {
            'story': story,
            'constraints': constraints,
        })


class StartGenerationView(View):
    def post(self, request, story_id):
        # Service: Orchestrierung mit Locking
        service = StoryGenerationService()
        
        try:
            story = service.start_generation(story_id)
            # Celery Task starten...
            return redirect('story-detail', story_id=story_id)
        except ValueError as e:
            messages.error(request, str(e))
            return redirect('story-detail', story_id=story_id)
```
# Kapitel 9: Migration & Versionierung

---

## 9.1 Übersicht

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  JSON SCHEMA MIGRATION                                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   DB (v1 JSON)          MIGRATOR              PYDANTIC (v2)                 │
│   ────────────    →     ────────    →         ─────────────                 │
│                                                                              │
│   {"total": 30000,      detect_version()      TimingSpec(                   │
│    "is_travel": true}   _v1_to_v2()            schema_version=2,            │
│                         migrate()               total_words=30000,          │
│                                                 travel={is_travel_synced}   │
│                                               )                              │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 9.2 Migrator-Implementierung

```python
# platform_creative/domain/timing/migrator.py

from typing import Dict, Any, Tuple, Callable, Optional
import logging

logger = logging.getLogger(__name__)

MigrationFn = Callable[[Dict[str, Any]], Dict[str, Any]]


class MigrationError(Exception):
    """Fehler bei Schema-Migration."""
    pass


class TimingSpecMigrator:
    """
    Migriert JSON-Payloads zwischen Schema-Versionen.
    
    Prinzipien:
    1. Explizite Schritte (v1→v2, v2→v3, ...)
    2. Keine Daten gehen verloren
    3. Idempotent
    4. Logging für Audit
    """
    
    current_version = 2
    
    def detect_version(self, payload: Dict[str, Any]) -> int:
        """
        Erkennt Schema-Version aus Payload.
        
        Prüft in Reihenfolge:
        1. Explizites schema_version Feld
        2. Legacy _version Feld
        3. Heuristik basierend auf Feldstruktur
        """
        # Explizite Version
        if "schema_version" in payload:
            return int(payload["schema_version"])
        
        # Legacy Format
        if "_version" in payload:
            return int(payload["_version"])
        
        # Heuristik: v2 hat 'travel' als Object
        if "travel" in payload and isinstance(payload.get("travel"), dict):
            return 2
        
        # Heuristik: v1 hat flache 'is_travel_synced'
        if "is_travel_synced" in payload:
            return 1
        
        # Default: Ältestes Format
        return 1
    
    def migrate(self, payload: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
        """
        Migriert Payload auf aktuelle Version.
        
        Returns:
            Tuple[migrated_payload, changed]
        """
        original_version = self.detect_version(payload)
        version = original_version
        changed = False
        
        # Schrittweise Migration
        while version < self.current_version:
            next_version = version + 1
            step_fn = self._get_step(version, next_version)
            
            logger.info(
                f"Migrating timing_spec v{version} → v{next_version}",
                extra={"from_version": version, "to_version": next_version}
            )
            
            payload = step_fn(payload)
            version = next_version
            changed = True
        
        # Version setzen
        payload["schema_version"] = self.current_version
        
        if changed:
            logger.info(
                f"Migration complete: v{original_version} → v{self.current_version}",
                extra={"original_version": original_version}
            )
        
        return payload, changed
    
    def _get_step(self, from_v: int, to_v: int) -> MigrationFn:
        """Holt Migration-Funktion für einen Schritt."""
        steps: Dict[Tuple[int, int], MigrationFn] = {
            (1, 2): self._v1_to_v2,
            # Zukünftig: (2, 3): self._v2_to_v3,
        }
        
        key = (from_v, to_v)
        if key not in steps:
            raise MigrationError(f"No migration path from v{from_v} to v{to_v}")
        
        return steps[key]
    
    def _v1_to_v2(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Migration v1 → v2.
        
        Änderungen:
        - reader_speed_wpm: Neues Feld (Default: 250)
        - source_type: Neues Feld (Default: "manual")
        - travel: Flache Felder → Nested Object
        - _version → schema_version
        """
        payload = dict(payload)  # Kopie
        
        # Neue Felder mit Defaults
        payload.setdefault("reader_speed_wpm", 250)
        payload.setdefault("source_type", "manual")
        payload.setdefault("structure_type", "save_the_cat")
        payload.setdefault("chapters", [])
        
        # Travel-Felder restructurieren
        if "is_travel_synced" in payload or "trip_id" in payload:
            payload["travel"] = {
                "is_travel_synced": bool(payload.pop("is_travel_synced", False)),
                "trip_id": payload.pop("trip_id", None),
                "enforce_word_counts": payload.pop("enforce_word_counts", True),
                "word_count_tolerance": payload.pop("word_count_tolerance", 0.1),
            }
        
        # Legacy-Keys entfernen
        payload.pop("_version", None)
        payload.pop("version", None)
        
        return payload
```

---

## 9.3 Migrations-Strategien

### Lazy Migration (bei Read)

```python
# Automatisch in PydanticSchemaField.from_db_value()

def from_db_value(self, value, expression, connection):
    if value is None:
        return None
    
    migrator = self._get_migrator()
    if migrator:
        payload, changed = migrator.migrate(value)
        # changed=True → wird beim nächsten Save persistiert
    
    return self.schema_class.model_validate(payload)
```

**Vorteile:** Kein Batch-Job nötig, automatisch
**Nachteile:** Migration erst bei Read, nicht in DB persistiert bis Save

### Eager Migration (Batch)

```python
# management/commands/migrate_timing_specs.py

from django.core.management.base import BaseCommand
from apps.stories.models import Story
from platform_creative.domain.timing.migrator import TimingSpecMigrator


class Command(BaseCommand):
    help = "Migriert alle Timing-Specs auf aktuelle Version"
    
    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--batch-size', type=int, default=100)
    
    def handle(self, *args, **options):
        migrator = TimingSpecMigrator()
        dry_run = options['dry_run']
        batch_size = options['batch_size']
        
        stats = {'migrated': 0, 'skipped': 0, 'errors': 0}
        
        # Nur Stories mit timing_spec
        stories = Story.objects.exclude(timing_spec__isnull=True)
        
        for story in stories.iterator(chunk_size=batch_size):
            try:
                raw = story.timing_spec  # Raw dict via from_db_value_raw
                if raw is None:
                    continue
                
                migrated, changed = migrator.migrate(raw)
                
                if changed:
                    if not dry_run:
                        # Direkt in DB updaten (bypass Model)
                        Story.objects.filter(id=story.id).update(
                            timing_spec=migrated
                        )
                    stats['migrated'] += 1
                    self.stdout.write(f"Migrated Story {story.id}")
                else:
                    stats['skipped'] += 1
                    
            except Exception as e:
                stats['errors'] += 1
                self.stderr.write(f"Error Story {story.id}: {e}")
        
        self.stdout.write(self.style.SUCCESS(
            f"Done: {stats['migrated']} migrated, {stats['skipped']} skipped, {stats['errors']} errors"
        ))
```

**Vorteile:** Alle Daten auf neuestem Stand, kontrolliert
**Nachteile:** Braucht Batch-Job, DB-Last

### Empfehlung

1. **Lazy Migration** für Kompatibilität (alte Daten funktionieren)
2. **Eager Migration** nach Deployment (alle auf neuesten Stand)
3. **Monitoring** für nicht-migrierte Records

---

## 9.4 Write-Back Strategien

### Option A: Save-Hook

```python
class Story(models.Model):
    def save(self, *args, **kwargs):
        # Hot Columns synchronisieren
        if self.timing_spec:
            self.sync_timing_hot_columns()
        super().save(*args, **kwargs)
```

**Problem:** Bulk Updates überspringen `save()`

### Option B: Service-Enforcement

```python
# IMMER Service nutzen, nie Model direkt

@transaction.atomic
def update_timing_spec(story_id: int, spec: TimingSpec) -> Story:
    story = Story.objects.select_for_update().get(id=story_id)
    story.timing_spec = spec
    story.sync_timing_hot_columns()
    story.save(update_fields=["timing_spec", "timing_total_minutes", ...])
    return story
```

**Empfohlen:** Konsistent, explizit

### Option C: DB Trigger (PostgreSQL)

```sql
CREATE OR REPLACE FUNCTION sync_timing_hot_columns()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.timing_spec IS NOT NULL THEN
        NEW.timing_total_minutes := (NEW.timing_spec->>'total_words')::int / 
                                    COALESCE((NEW.timing_spec->>'reader_speed_wpm')::int, 250);
        NEW.is_travel_synced := COALESCE((NEW.timing_spec->'travel'->>'is_travel_synced')::boolean, false);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_sync_timing_hot_columns
BEFORE INSERT OR UPDATE ON stories_story
FOR EACH ROW EXECUTE FUNCTION sync_timing_hot_columns();
```

**Vorteile:** Garantiert konsistent, auch bei Bulk
**Nachteile:** Logik in DB, schwerer zu testen
# Kapitel 10: Observability & Härtung

---

## 10.1 Kein Silent Fallback

> **Prinzip:** Bei Fehlern explizit scheitern, nicht still Defaults zurückgeben.

### ❌ FALSCH: Silent Fallback

```python
def from_db_value(self, value, ...):
    try:
        return self.schema_class.model_validate(value)
    except ValidationError:
        return self.schema_class()  # 💀 Überschreibt echte Daten beim nächsten Save!
```

### ✅ RICHTIG: Explicit Failure

```python
def from_db_value(self, value, ...):
    try:
        return self.schema_class.model_validate(value)
    except ValidationError as e:
        logger.exception("Invalid payload", extra={"field": self.name, "error": str(e)})
        
        if self.strict:
            raise  # PROD: Exception
        
        return None  # DEV: None (nicht Default!)
```

**Warum `None` statt Default?**
- `None` zwingt Service zur expliziten Behandlung
- Default würde beim nächsten `save()` echte Daten überschreiben

---

## 10.2 Strict Mode

### Konfiguration

```python
# settings.py

PYDANTIC_SCHEMA_STRICT = env.bool("PYDANTIC_SCHEMA_STRICT", default=True)

# In PydanticSchemaField
class PydanticSchemaField(models.JSONField):
    def __init__(self, ..., strict: bool = None, ...):
        if strict is None:
            strict = getattr(settings, 'PYDANTIC_SCHEMA_STRICT', True)
        self.strict = strict
```

### Umgebungen

| Umgebung | strict | Verhalten |
|----------|--------|-----------|
| **PROD** | `True` | Exception bei Invalid → 500 |
| **STAGING** | `True` | Exception, aber testbar |
| **DEV** | `False` | `None` + Log |

---

## 10.3 Quarantäne-Pattern

Bei Invalid Payload: Story markieren statt crashen.

### Implementierung

```python
# platform_creative/enums/status.py

class StoryStatus(str, Enum):
    # ... bestehende Status
    TIMING_INVALID = "timing_invalid"  # Neuer Status


# apps/stories/models/story.py

class Story(models.Model):
    timing_validation_error = models.TextField(blank=True)
    
    def mark_timing_invalid(self, error: str):
        """Markiert Story als invalid (Quarantäne)."""
        self.status = StoryStatus.TIMING_INVALID.value
        self.timing_validation_error = error
        self.save(update_fields=["status", "timing_validation_error"])


# PydanticSchemaField mit Quarantäne

class PydanticSchemaField(models.JSONField):
    def from_db_value(self, value, expression, connection):
        if value is None:
            return None
        
        try:
            # Migration + Validation
            migrator = self._get_migrator()
            payload = value
            if migrator:
                payload, _ = migrator.migrate(payload)
            return self.schema_class.model_validate(payload)
        
        except (ValidationError, Exception) as e:
            logger.exception("Invalid payload", extra={
                "field": self.name,
                "model": self.model.__name__,
            })
            
            if self.strict:
                # Option: Quarantäne statt Exception
                if hasattr(self.model, 'mark_timing_invalid'):
                    # Funktioniert nicht direkt hier - besser im Service
                    pass
                raise
            
            return None
```

### Admin UI für Quarantäne

```python
# apps/stories/admin.py

@admin.register(Story)
class StoryAdmin(admin.ModelAdmin):
    list_filter = ['status']
    
    actions = ['repair_timing_spec']
    
    @admin.action(description="Repair Timing Spec")
    def repair_timing_spec(self, request, queryset):
        repaired = 0
        for story in queryset.filter(status=StoryStatus.TIMING_INVALID.value):
            try:
                # Versuche Migration/Repair
                if story.timing_spec is None:
                    story.timing_spec = create_default_timing_spec(story)
                story.status = StoryStatus.DRAFT.value
                story.timing_validation_error = ""
                story.save()
                repaired += 1
            except Exception as e:
                self.message_user(request, f"Failed for {story.id}: {e}", level='error')
        
        self.message_user(request, f"Repaired {repaired} stories")
```

---

## 10.4 Structured Logging

### Events

| Event | Level | Extra Fields |
|-------|-------|--------------|
| `timing_spec.invalid_payload` | ERROR | story_id, field, schema, error |
| `timing_spec.migrated` | INFO | story_id, from_version, to_version |
| `timing_spec.quarantined` | WARNING | story_id, error |
| `story_generation.started` | INFO | story_id, user_id |
| `story_generation.completed` | INFO | story_id, duration_seconds, tokens |
| `story_generation.failed` | ERROR | story_id, error, step |

### Implementierung

```python
# platform_core/utils/logging.py

import logging
import json
from typing import Any, Dict


class StructuredLogger:
    """Logger mit strukturierten Extra-Feldern."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
    
    def _log(self, level: int, event: str, message: str, **extra):
        self.logger.log(
            level,
            f"[{event}] {message}",
            extra={"event": event, **extra}
        )
    
    def info(self, event: str, message: str, **extra):
        self._log(logging.INFO, event, message, **extra)
    
    def warning(self, event: str, message: str, **extra):
        self._log(logging.WARNING, event, message, **extra)
    
    def error(self, event: str, message: str, **extra):
        self._log(logging.ERROR, event, message, **extra)


# Nutzung
logger = StructuredLogger(__name__)

logger.info(
    "timing_spec.migrated",
    f"Migrated Story {story_id}",
    story_id=story_id,
    from_version=1,
    to_version=2,
)
```

### JSON Formatter für Produktion

```python
# settings/production.py

LOGGING = {
    'version': 1,
    'formatters': {
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json',
        },
    },
    'loggers': {
        'platform_creative': {
            'handlers': ['console'],
            'level': 'INFO',
        },
    },
}
```

---

## 10.5 Monitoring Dashboard

### Metriken

```python
# Prometheus Metrics (wenn verwendet)

from prometheus_client import Counter, Histogram

timing_spec_migrations = Counter(
    'timing_spec_migrations_total',
    'Total timing spec migrations',
    ['from_version', 'to_version']
)

timing_spec_validation_errors = Counter(
    'timing_spec_validation_errors_total',
    'Timing spec validation errors',
    ['schema', 'field']
)

story_generation_duration = Histogram(
    'story_generation_duration_seconds',
    'Story generation duration',
    buckets=[10, 30, 60, 120, 300, 600]
)
```

### SQL Queries für Dashboard

```sql
-- Stories mit Invalid Timing
SELECT COUNT(*) as invalid_count
FROM stories_story
WHERE status = 'timing_invalid';

-- Migration Backlog
SELECT 
    timing_spec->>'schema_version' as version,
    COUNT(*) as count
FROM stories_story
WHERE timing_spec IS NOT NULL
GROUP BY timing_spec->>'schema_version';

-- Stories ohne Timing-Spec
SELECT COUNT(*) as missing_spec
FROM stories_story
WHERE timing_spec IS NULL
AND status NOT IN ('draft');
```

---

## 10.6 Alerts

### Kritische Alerts

```yaml
# alert_rules.yml (Prometheus/Grafana)

groups:
  - name: timing_spec
    rules:
      - alert: HighValidationErrorRate
        expr: rate(timing_spec_validation_errors_total[5m]) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High timing spec validation error rate"
      
      - alert: MigrationBacklog
        expr: count(stories_story{timing_spec_version!="2"}) > 100
        for: 1h
        labels:
          severity: warning
        annotations:
          summary: "Large migration backlog"
```

### Sentry Integration

```python
# Bei Validation-Error

import sentry_sdk

try:
    spec = TimingSpec.model_validate(payload)
except ValidationError as e:
    sentry_sdk.capture_exception(e, extra={
        "story_id": story_id,
        "payload": payload,
    })
    raise
```
# Kapitel 11: Implementierungs-Roadmap

---

## 11.1 Übersicht

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  GESAMTAUFWAND: ~17-20 TAGE                                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Phase 1: Foundation (4 Tage)                                               │
│  ├─ BaseLookupTable + PydanticSchemaField                                   │
│  └─ Migrator-Pattern                                                        │
│                                                                              │
│  Phase 2: Lookup Tables (3 Tage)                                            │
│  ├─ Genre, SpiceLevel, EndingType                                           │
│  ├─ AccommodationType, TransportType, ReadingContext                        │
│  └─ Initial Data Migrations                                                 │
│                                                                              │
│  Phase 3: Enums & Hybrid (2 Tage)                                           │
│  ├─ Code-Enums (Status)                                                     │
│  ├─ Hybrid-Pattern (PacingType, StoryBeat)                                  │
│  └─ Services (PacingTypeService)                                            │
│                                                                              │
│  Phase 4: Timing Domain (4 Tage)                                            │
│  ├─ TimingSpec, ChapterSpec, TravelMeta                                     │
│  ├─ Derived (Constraints, Metrics)                                          │
│  └─ Providers                                                               │
│                                                                              │
│  Phase 5: Model Refactoring (3 Tage)                                        │
│  ├─ Story Model (FK zu Lookups, TimingSpec)                                 │
│  ├─ Chapter Model                                                           │
│  └─ Data Migration                                                          │
│                                                                              │
│  Phase 6: Integration & Tests (3-4 Tage)                                    │
│  ├─ Services anpassen                                                       │
│  ├─ Views/Forms anpassen                                                    │
│  └─ Tests                                                                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 11.2 Phase 1: Foundation (4 Tage)

### Tag 1-2: platform_core

```bash
# Struktur erstellen
packages/platform_core/
├── platform_core/
│   ├── __init__.py
│   ├── db/
│   │   ├── __init__.py
│   │   ├── fields.py           # PydanticSchemaField
│   │   └── lookup_tables.py    # BaseLookupTable
│   └── exceptions/
│       └── base.py
└── pyproject.toml
```

**Deliverables:**
- [ ] `BaseLookupTable` mit Caching
- [ ] `LookupTableManager`
- [ ] `PydanticSchemaField` (strict, migrator)
- [ ] Unit Tests

### Tag 3-4: Migrator-Pattern

```bash
packages/platform_creative/
├── domain/
│   └── timing/
│       ├── migrator.py
│       └── exceptions.py
```

**Deliverables:**
- [ ] `TimingSpecMigrator`
- [ ] `detect_version()`, `migrate()`, `_v1_to_v2()`
- [ ] Unit Tests für Migration

---

## 11.3 Phase 2: Lookup Tables (3 Tage)

### Tag 5-6: Models

```bash
packages/platform_creative/
├── models/
│   ├── __init__.py
│   ├── genre.py
│   ├── spice_level.py
│   ├── ending_type.py
│   ├── accommodation_type.py
│   ├── transport_type.py
│   └── reading_context.py
```

**Deliverables:**
- [ ] Alle Lookup Table Models
- [ ] Django Migrations
- [ ] Admin-Registrierung

### Tag 7: Initial Data

```bash
packages/platform_creative/
└── migrations/
    ├── 0002_seed_genres.py
    ├── 0003_seed_spice_levels.py
    ├── 0004_seed_reading_contexts.py
    └── 0005_seed_travel_types.py
```

**Deliverables:**
- [ ] Seed Migrations für alle Lookup Tables
- [ ] Verifizierung der Daten

---

## 11.4 Phase 3: Enums & Hybrid (2 Tage)

### Tag 8: Code-Enums

```bash
packages/platform_creative/
└── enums/
    ├── __init__.py
    ├── status.py           # StoryStatus, ChapterStatus
    └── generation.py       # GenerationPhase
```

**Deliverables:**
- [ ] `StoryStatus` mit `can_transition_to()`
- [ ] `ChapterStatus`
- [ ] `GenerationPhase` mit `progress_range`

### Tag 9: Hybrid-Pattern

```bash
packages/platform_creative/
├── enums/
│   ├── pacing.py           # CorePacingType
│   └── story_beat.py       # CoreStoryBeat
├── models/
│   └── pacing_extension.py
└── services/
    └── pacing_service.py
```

**Deliverables:**
- [ ] `CorePacingType` mit `prompt_guidance`
- [ ] `PacingTypeExtension` (DB)
- [ ] `PacingTypeService` kombiniert beide
- [ ] Seed Data für Extensions

---

## 11.5 Phase 4: Timing Domain (4 Tage)

### Tag 10-11: Specs

```bash
packages/platform_creative/
└── domain/
    └── timing/
        ├── spec.py         # TimingSpec, ChapterSpec, TravelMeta
        └── derived.py      # TimingConstraints, TimingMetrics
```

**Deliverables:**
- [ ] `TimingSpec` (Pydantic, versioniert)
- [ ] `ChapterSpec`, `TravelMeta`
- [ ] `TimingConstraints`, `TimingMetrics`
- [ ] Validators

### Tag 12-13: Providers

```bash
packages/platform_creative/
└── domain/
    └── timing/
        └── providers.py
```

**Deliverables:**
- [ ] `build_constraints()`
- [ ] `build_metrics()`
- [ ] `calculate_chapter_beats()`
- [ ] `from_reading_slots()`
- [ ] `from_uniform()`
- [ ] Unit Tests (deterministisch)

---

## 11.6 Phase 5: Model Refactoring (3 Tage)

### Tag 14: Story Model

```python
# apps/stories/models/story.py

class Story(models.Model):
    # FK zu Lookups (statt CharField)
    genre = models.ForeignKey('platform_creative.Genre', ...)
    spice_level = models.ForeignKey('platform_creative.SpiceLevel', ...)
    
    # TimingSpec (JSONField mit Pydantic)
    timing_spec = PydanticSchemaField(schema_class=TimingSpec, ...)
    
    # Hot Columns
    timing_total_minutes = models.IntegerField(null=True, db_index=True)
    is_travel_synced = models.BooleanField(default=False, db_index=True)
```

**Deliverables:**
- [ ] Story Model angepasst
- [ ] Chapter Model angepasst
- [ ] Django Migration

### Tag 15-16: Data Migration

```python
# Migration: CharField → ForeignKey, alte Daten migrieren

def migrate_genre_to_fk(apps, schema_editor):
    Story = apps.get_model('stories', 'Story')
    Genre = apps.get_model('platform_creative', 'Genre')
    
    for story in Story.objects.all():
        genre = Genre.objects.get(code=story.genre_old)
        story.genre = genre
        story.save(update_fields=['genre'])
```

**Deliverables:**
- [ ] Data Migration Script
- [ ] Rollback Script
- [ ] Verifikation

---

## 11.7 Phase 6: Integration & Tests (3-4 Tage)

### Tag 17-18: Services & Views

**Deliverables:**
- [ ] `TimingService` anpassen
- [ ] `StoryGenerationService` anpassen
- [ ] Forms mit `ModelChoiceField`
- [ ] Views anpassen

### Tag 19-20: Tests

**Deliverables:**
- [ ] Unit Tests für Providers
- [ ] Integration Tests für Services
- [ ] Migration Tests (v1 → v2)
- [ ] E2E Tests für Story-Erstellung

---

## 11.8 Checkliste

### Foundation
- [ ] `BaseLookupTable` mit Caching
- [ ] `PydanticSchemaField` (strict, migrator)
- [ ] `TimingSpecMigrator`

### Lookup Tables
- [ ] Genre, SpiceLevel, EndingType
- [ ] AccommodationType, TransportType
- [ ] ReadingContext
- [ ] Initial Data Migrations

### Enums
- [ ] StoryStatus, ChapterStatus (Code-Enum)
- [ ] CorePacingType, CoreStoryBeat (Hybrid)
- [ ] PacingTypeExtension (DB)
- [ ] PacingTypeService

### Timing Domain
- [ ] TimingSpec, ChapterSpec, TravelMeta
- [ ] TimingConstraints, TimingMetrics
- [ ] Providers (build_constraints, build_metrics, etc.)

### Model Refactoring
- [ ] Story: FK zu Lookups
- [ ] Story: timing_spec (PydanticSchemaField)
- [ ] Story: Hot Columns
- [ ] Data Migration

### Integration
- [ ] Services anpassen
- [ ] Views/Forms anpassen
- [ ] Tests

### Observability
- [ ] Structured Logging
- [ ] Monitoring Queries
- [ ] Alerts (optional)

---

## 11.9 Risiken & Mitigations

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|--------|------------|
| Data Migration Fehler | Mittel | Hoch | Backup, Rollback-Script, Dry-Run |
| Performance (Caching) | Niedrig | Mittel | Load-Tests, Cache-Monitoring |
| Breaking Changes | Niedrig | Hoch | Zero-Breaking-Change Strategie |
| FK-Constraints blockieren | Niedrig | Mittel | `on_delete=PROTECT`, Admin-Prozess |

---

## 11.10 Quick Wins (sofort umsetzbar)

1. **Logging hinzufügen** - Structured Logging für Timing-Operationen
2. **Strict Mode** - `PYDANTIC_SCHEMA_STRICT=True` in PROD
3. **`_version` → `schema_version`** - Im bestehenden Code
4. **Hot Columns** - `timing_total_minutes`, `is_travel_synced` hinzufügen
5. **Admin für Genres** - Lookup Table Migration vorbereiten
