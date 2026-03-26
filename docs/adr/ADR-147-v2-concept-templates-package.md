---
status: "proposed"
date: 2026-03-26
updated: 2026-03-26
version: 2
decision-makers: [Achim Dehnert]
consulted: []
informed: []
supersedes: []
amends: []
related: ["ADR-130-content-store-shared-persistence.md", "ADR-146-package-consolidation-strategy.md", "ADR-041-django-component-pattern.md", "ADR-022-platform-consistency-standard.md"]
implementation_status: not_started
implementation_evidence: []
review_status: "v1 reviewed — 5 Blocker, 5 Kritisch korrigiert in v2"
---

# ADR-147: `iil-concept-templates` — Shared Package für strukturierte Konzept-Vorlagen (v2)

## Änderungshistorie

| Version | Datum | Änderung |
|---------|-------|----------|
| v1 | 2026-03-26 | Initialer Entwurf |
| v2 | 2026-03-26 | Review-Korrekturen: B-01..B-05 (Blocker), K-01..K-05 (Kritisch), H-01..H-06 (Hoch). Architektur geändert: Pure-Python-Core + Abstract-Django-Models. Bestehende documents-App als primärer Upload-Kanal. Sync-API statt Async. |

---

## Context and Problem Statement

Mehrere Platform-Hubs arbeiten mit **strukturierten Fachkonzepten**, die:

1. **Branchenspezifische Gliederungen** haben (Brandschutz nach MBO, Explosionsschutz nach TRGS 720ff, Ausschreibungen nach VOB/VgV)
2. **Aus Bestandsdokumenten gelernt** werden sollen (Kunden-PDFs → Struktur extrahieren → Template)
3. **Iterativ verfeinert** werden (Upload → LLM-Vorschlag → User-Review → Master-Template)
4. **Mandantenspezifische Varianten** erlauben (Master-Template → Kunden-Fork)

### Bestehende Infrastruktur (v2: vollständig erfasst)

| Hub | Konzept-Model | Dokumenten-System | Template |
|-----|---------------|-------------------|----------|
| **risk-hub** (Brandschutz) | `FireProtectionConcept` | `documents.Document` + S3-Upload ✅ | ❌ keins |
| **risk-hub** (Explosionsschutz) | `ExplosionConcept` | `documents.Document` + `VerificationDocument` ✅ | ❌ keins |
| **ausschreibungs-hub** | (geplant Q2 2026) | (geplant) | ❌ keins |

**Problem**: Template-Logik (Gliederungserkennung, PDF-Extraktion, Framework-Abgleich,
iterative Verfeinerung) müsste in jedem Hub dupliziert werden.

### v2-Korrektur: `documents`-App existiert bereits

risk-hub besitzt eine vollwertige `documents`-App mit S3-Upload, Versionierung
(`DocumentVersion`), SHA-256-Deduplizierung und Service-Layer. Diese wird **nicht
dupliziert**, sondern für Phase A erweitert. Das Package liefert nur die
**domänenunabhängige Kern-Logik** (Schemas, Frameworks, PDF-Extraktion, Merging).

---

## Decision Drivers

- **DRY**: Template-Gliederung, PDF-Extraktion und LLM-Analyse sind domänenübergreifend identisch
- **Bestehende Infrastruktur nutzen**: risk-hub `documents`-App als Upload-Backend
- **outlinefw-Integration**: Framework-Registry + Gliederungs-Generierung via `iil-outlinefw`
- **ADR-146**: Neues Package nur mit klarem Scope und ≥1 Consumer Tag 1, 2. Consumer geplant
- **ADR-022**: BigAutoField, `BigIntegerField` tenant_id, Service-Layer, kein hardcoded SQL
- **ADR-041**: Business-Logik im Service-Layer, nie in Views
- **Platform-Standards**: Soft-Delete, public_id, i18n ab Tag 1

---

## Considered Options

### Option 1 — Pure-Python Package + documents-App-Erweiterung (gewählt)

`iil-concept-templates` als reines Python-Package (Pydantic, kein Django im Core).
Django-Integration via optionales `[django]` Extra mit **Abstract Models**.
Upload läuft über die bestehende risk-hub `documents`-App (erweitert um `concept_ref_id`).

**Pro:**
- Pure Python Core → testbar ohne Django
- Bestehende S3/Upload-Infra wiederverwendet
- Abstract Models → Consumer definiert PK-Typ und FKs (kompatibel mit risk-hub UUIDField-PKs)
- Kein DATABASE_ROUTER nötig

**Contra:**
- Migrations leben im Consumer, nicht im Package
- Django-Extra optional → Consumer muss Abstract Model selbst erben

---

### Option 2 — Django App direkt in risk-hub

**Verworfen**: Löst Wiederverwendbarkeit nicht (ausschreibungs-hub).

### Option 3 — Erweiterung von content-store

**Verworfen**: Verletzt SRP (content-store = Persistenz, kein Domain-Logik).

### Option 4 — outlinefw Extension (`[concepts]` Extra)

Package-Logik direkt in outlinefw als Extra.

**Pro:** Kein neues Package
**Contra:** outlinefw-Scope wird unklar (Story-Outlines ≠ Fachkonzepte), PDF-Extraktion gehört nicht in Outline-Lib

**Verworfen**: Scope-Verwässerung.

---

## Decision Outcome

**Gewählt: Option 1** — Pure-Python Package `iil-concept-templates` + risk-hub `documents`-App-Erweiterung.

### Positive Consequences

- Einheitliche Template-Schemas für Brandschutz, Explosionsschutz und Ausschreibungen
- outlinefw-Ökosystem wächst organisch
- Bestehende documents-Infrastruktur wiederverwendet
- Pure Python Core: einfach testbar, keine Django-Dependency im Kern

### Negative Consequences

- Neues Package (mitigiert: klarer Scope, 1 Consumer Tag 1, 2. geplant)
- Abstract Models erfordern Consumer-seitige Migration (mitigiert: einmalig, scaffold via Workflow)

---

## Implementation Details

### Package-Struktur

```
platform/packages/concept-templates/
├── concept_templates/
│   ├── __init__.py              # Version, public API
│   ├── schemas.py               # Pydantic v2 Schemas (TemplateField, TemplateSection, ConceptTemplate)
│   ├── frameworks.py            # Vordefinierte Frameworks (MBO, TRGS720, VOB)
│   ├── registry.py              # register_framework(), get_framework(), list_frameworks()
│   ├── extractor.py             # PDF → Text (pdfplumber, synchron)
│   ├── analyzer.py              # Text → ConceptTemplate (LLM-Call via Callable, synchron)
│   ├── merger.py                # N Templates → Master-Template
│   ├── export.py                # to_markdown(), to_json(), to_dict()
│   ├── validators.py            # File-Validierung (Größe, Typ, MIME)
│   ├── contrib/
│   │   └── django/
│   │       ├── __init__.py
│   │       ├── abstract_models.py  # AbstractConceptDocument, AbstractConceptTemplate
│   │       ├── services.py         # Service-Layer für Django-Integration
│   │       └── apps.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_schemas.py
│   ├── test_frameworks.py
│   ├── test_registry.py
│   ├── test_extractor.py
│   ├── test_analyzer.py
│   ├── test_merger.py
│   ├── test_export.py
│   └── test_validators.py
├── pyproject.toml
└── README.md
```

### Kern-Schemas (`schemas.py`) — v2 korrigiert

```python
"""Pydantic v2 schemas for concept templates."""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class ConceptScope(StrEnum):
    """Fachbereich eines Konzepts."""

    BRANDSCHUTZ = "brandschutz"
    EXPLOSIONSSCHUTZ = "explosionsschutz"
    AUSSCHREIBUNG = "ausschreibung"


class FieldType(StrEnum):
    """Unterstützte Feldtypen in Template-Sektionen."""

    TEXT = "text"
    TEXTAREA = "textarea"
    NUMBER = "number"
    DATE = "date"
    CHOICE = "choice"
    FILE = "file"
    BOOLEAN = "boolean"


class TemplateField(BaseModel):
    """Einzelnes Feld innerhalb einer Template-Sektion."""

    name: str
    label: str
    field_type: FieldType
    required: bool = False
    default: str | None = None
    choices: list[str] | None = None
    help_text: str = ""


class TemplateSection(BaseModel):
    """Kapitel/Abschnitt eines Konzept-Templates."""

    name: str
    title: str
    description: str = ""
    required: bool = True
    order: int = 0
    fields: list[TemplateField] = Field(default_factory=list)
    subsections: list[TemplateSection] = Field(default_factory=list)


class ConceptTemplate(BaseModel):
    """Vollständiges Konzept-Template (Master oder Kunden-Variante)."""

    name: str
    scope: ConceptScope
    version: str = "1.0"
    is_master: bool = False
    framework: str = ""
    framework_version: str = "1.0"
    valid_from: date | None = None
    valid_until: date | None = None
    sections: list[TemplateSection] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class ExtractionResult(BaseModel):
    """Ergebnis einer PDF-Text-Extraktion."""

    text: str
    page_count: int
    metadata: dict = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class AnalysisResult(BaseModel):
    """Ergebnis einer LLM-Strukturanalyse."""

    proposed_template: ConceptTemplate
    confidence: float = Field(ge=0.0, le=1.0)
    gaps: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
```

### Datei-Validierung (`validators.py`)

```python
"""File validation for concept document uploads."""

from __future__ import annotations

import logging
from pathlib import PurePath

logger = logging.getLogger(__name__)

# 50 MB max
MAX_FILE_SIZE_BYTES: int = 50 * 1024 * 1024

ALLOWED_EXTENSIONS: frozenset[str] = frozenset({
    ".pdf", ".docx", ".doc", ".xlsx", ".xls",
    ".dxf", ".dwg",
    ".jpg", ".jpeg", ".png", ".tiff",
    ".txt", ".csv",
})

ALLOWED_MIME_PREFIXES: frozenset[str] = frozenset({
    "application/pdf",
    "application/vnd.openxmlformats",
    "application/msword",
    "application/vnd.ms-excel",
    "image/",
    "text/",
    "application/octet-stream",  # DXF/DWG
})


class FileValidationError(ValueError):
    """Raised when file validation fails."""


def validate_upload_file(
    filename: str,
    size_bytes: int,
    content_type: str = "",
) -> None:
    """
    Validate an uploaded file.

    Raises FileValidationError on invalid files.
    """
    ext = PurePath(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise FileValidationError(
            f"Dateityp '{ext}' nicht erlaubt. "
            f"Erlaubt: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    if size_bytes > MAX_FILE_SIZE_BYTES:
        max_mb = MAX_FILE_SIZE_BYTES // (1024 * 1024)
        raise FileValidationError(
            f"Datei zu groß ({size_bytes // (1024 * 1024)} MB). "
            f"Maximum: {max_mb} MB."
        )

    if content_type:
        if not any(content_type.startswith(p) for p in ALLOWED_MIME_PREFIXES):
            logger.warning(
                "Unexpected MIME type: %s for %s", content_type, filename,
            )
```

### Abstract Django Models (`contrib/django/abstract_models.py`) — v2 korrigiert

```python
"""Abstract Django models for concept documents and templates.

Consumer apps inherit these and add app-specific ForeignKeys and PK types.

Platform standards enforced:
- public_id UUIDField (B-02)
- deleted_at soft-delete (B-03)
- BigIntegerField tenant_id (B-01) — Note: risk-hub uses UUIDField,
  consumer may override tenant_id type if needed for legacy compat.
- i18n via gettext_lazy (K-02)
- No JSONField for structured data (B-04)
- UniqueConstraint not unique_together
"""

from __future__ import annotations

import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _


def _concept_doc_upload_path(instance, filename: str) -> str:
    """Tenant-isolated upload path (H-02)."""
    return (
        f"tenants/{instance.tenant_id}/"
        f"concept_docs/{instance.public_id}/{filename}"
    )


class ConceptScope(models.TextChoices):
    """Fachbereich (K-04: TextChoices statt freier CharField)."""

    BRANDSCHUTZ = "brandschutz", _("Brandschutz")
    EXPLOSIONSSCHUTZ = "explosionsschutz", _("Explosionsschutz")
    AUSSCHREIBUNG = "ausschreibung", _("Ausschreibung")


class DocumentCategory(models.TextChoices):
    """Dokumenten-Kategorie für Konzept-Unterlagen."""

    GRUNDRISS = "grundriss", _("Grundriss (DXF/DWG)")
    PRODUKTDATENBLATT = "produktdatenblatt", _("Produktdatenblatt")
    SICHERHEITSDATENBLATT = "sdb", _("Sicherheitsdatenblatt")
    STANDORTBESCHREIBUNG = "standort", _("Standortbeschreibung")
    PRUEFBERICHT = "pruefbericht", _("Prüfbericht")
    BEHOERDLICHE_AUFLAGE = "auflage", _("Behördliche Auflage")
    LEISTUNGSVERZEICHNIS = "lv", _("Leistungsverzeichnis")
    BESTANDSKONZEPT = "bestandskonzept", _("Bestehendes Konzept (Vorlage)")
    SONSTIGES = "sonstiges", _("Sonstiges")


class SoftDeleteManager(models.Manager):
    """Manager that excludes soft-deleted records by default."""

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class AbstractConceptDocument(models.Model):
    """
    Abstract base for concept-related documents.

    Consumer inherits and adds:
    - Concrete PK (BigAutoField default or UUIDField for risk-hub compat)
    - ForeignKey to concept model (e.g. FireProtectionConcept)
    - db_table in Meta
    """

    public_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        verbose_name=_("Public ID"),
    )
    # Default: BigIntegerField per platform standard.
    # risk-hub consumer may override to UUIDField for legacy compat.
    tenant_id = models.BigIntegerField(
        db_index=True,
        verbose_name=_("Tenant ID"),
    )
    scope = models.CharField(
        max_length=30,
        choices=ConceptScope.choices,
        verbose_name=_("Fachbereich"),
    )
    category = models.CharField(
        max_length=30,
        choices=DocumentCategory.choices,
        default=DocumentCategory.SONSTIGES,
        verbose_name=_("Kategorie"),
    )
    title = models.CharField(
        max_length=255,
        verbose_name=_("Titel"),
    )
    file = models.FileField(
        upload_to=_concept_doc_upload_path,
        verbose_name=_("Datei"),
    )
    file_size_bytes = models.BigIntegerField(
        default=0,
        verbose_name=_("Dateigröße (Bytes)"),
    )
    content_type = models.CharField(
        max_length=120,
        blank=True,
        default="",
        verbose_name=_("MIME-Type"),
    )
    extracted_text = models.TextField(
        blank=True,
        default="",
        verbose_name=_("Extrahierter Text"),
        help_text=_("Via pdfplumber extrahierter Volltext"),
    )
    # B-04: Kein JSONField! Serialisierter JSON-String für LLM-Extraktion.
    extracted_data_raw = models.TextField(
        blank=True,
        default="",
        verbose_name=_("Extrahierte Daten (JSON)"),
        help_text=_("Serialisiertes JSON der LLM-Strukturanalyse"),
    )

    # Audit fields
    created_by_id = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Erstellt von (User-ID)"),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Erstellt am"),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Aktualisiert am"),
    )
    # B-03: Soft-Delete
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_("Gelöscht am"),
    )

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.title} ({self.get_category_display()})"

    def soft_delete(self) -> None:
        """Mark as deleted without removing from DB."""
        from django.utils import timezone

        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at", "updated_at"])


class AbstractConceptTemplate(models.Model):
    """
    Abstract base for persisted concept templates.

    Stores the pydantic ConceptTemplate as serialized JSON in structure_raw.
    """

    public_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        verbose_name=_("Public ID"),
    )
    tenant_id = models.BigIntegerField(
        db_index=True,
        verbose_name=_("Tenant ID"),
        help_text=_("0 = plattformweites Master-Template"),
    )
    name = models.CharField(
        max_length=255,
        verbose_name=_("Name"),
    )
    scope = models.CharField(
        max_length=30,
        choices=ConceptScope.choices,
        verbose_name=_("Fachbereich"),
    )
    framework = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name=_("Framework"),
        help_text=_("z.B. brandschutz_mbo, exschutz_trgs720"),
    )
    framework_version = models.CharField(
        max_length=20,
        blank=True,
        default="1.0",
        verbose_name=_("Framework-Version"),
    )
    version = models.PositiveIntegerField(
        default=1,
        verbose_name=_("Version"),
    )
    is_master = models.BooleanField(
        default=False,
        verbose_name=_("Master-Template"),
    )
    # B-04: TextField statt JSONField für Template-Struktur
    structure_raw = models.TextField(
        blank=True,
        default="",
        verbose_name=_("Struktur (JSON)"),
        help_text=_("Serialisiertes ConceptTemplate-Schema"),
    )
    source_document_ids = models.TextField(
        blank=True,
        default="",
        verbose_name=_("Quell-Dokument-IDs"),
        help_text=_("Komma-separierte public_ids der Quelldokumente"),
    )

    created_by_id = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Erstellt von (User-ID)"),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Erstellt am"),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Aktualisiert am"),
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_("Gelöscht am"),
    )

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} v{self.version} ({self.get_scope_display()})"

    def get_structure(self):
        """Deserialize structure_raw to ConceptTemplate schema."""
        if not self.structure_raw:
            return None
        import json

        from concept_templates.schemas import ConceptTemplate

        return ConceptTemplate.model_validate_json(self.structure_raw)

    def set_structure(self, template) -> None:
        """Serialize ConceptTemplate schema to structure_raw."""
        self.structure_raw = template.model_dump_json(indent=2)
```

### Service-Layer (`contrib/django/services.py`) — K-01 korrigiert

```python
"""Service layer for concept template Django integration (ADR-041).

All business logic goes through this module.
Views call services — never Model.objects directly.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from django.core.files.uploadedfile import UploadedFile
from django.db import transaction

from concept_templates.extractor import extract_text_from_pdf
from concept_templates.validators import FileValidationError, validate_upload_file

if TYPE_CHECKING:
    from django.db import models

logger = logging.getLogger(__name__)


def upload_concept_document(
    *,
    model_class: type[models.Model],
    tenant_id: int,
    scope: str,
    category: str,
    title: str,
    file: UploadedFile,
    concept_fk_field: str = "",
    concept_fk_value=None,
    created_by_id: int | None = None,
) -> models.Model:
    """
    Upload and create a ConceptDocument.

    Validates file, extracts text from PDFs, creates model instance.
    Uses the consumer's concrete model class (not the abstract base).
    """
    # K-05: File validation
    validate_upload_file(
        filename=file.name,
        size_bytes=file.size,
        content_type=file.content_type or "",
    )

    extracted_text = ""
    if file.name.lower().endswith(".pdf"):
        try:
            result = extract_text_from_pdf(file.read())
            extracted_text = result.text
            file.seek(0)  # Reset after read
        except Exception as exc:
            logger.warning("PDF text extraction failed: %s", exc)

    kwargs = {
        "tenant_id": tenant_id,
        "scope": scope,
        "category": category,
        "title": title,
        "file": file,
        "file_size_bytes": file.size,
        "content_type": file.content_type or "",
        "extracted_text": extracted_text,
        "created_by_id": created_by_id,
    }
    if concept_fk_field and concept_fk_value is not None:
        kwargs[concept_fk_field] = concept_fk_value

    with transaction.atomic():
        instance = model_class(**kwargs)
        instance.full_clean()
        instance.save()

    logger.info(
        "ConceptDocument created: %s (scope=%s, category=%s, %d bytes)",
        instance.public_id,
        scope,
        category,
        file.size,
    )
    return instance


def analyze_document_structure(
    *,
    document,
    llm_callable=None,
    reference_framework: str = "",
) -> dict:
    """
    Analyze a document's extracted text to propose a template structure.

    llm_callable: Sync function(prompt: str) -> str
    Falls back to rule-based extraction if no LLM provided.
    """
    if not document.extracted_text:
        return {"error": "No extracted text available"}

    from concept_templates.analyzer import analyze_text

    result = analyze_text(
        text=document.extracted_text,
        scope=document.scope,
        llm_callable=llm_callable,
        reference_framework=reference_framework,
    )

    # Persist raw analysis result (B-04: TextField, not JSONField)
    document.extracted_data_raw = json.dumps(
        result.model_dump(), ensure_ascii=False, indent=2,
    )
    document.save(update_fields=["extracted_data_raw", "updated_at"])

    return result.model_dump()
```

### Synchrone Kern-API (`extractor.py`) — K-03 korrigiert

```python
"""PDF text extraction — synchronous API.

K-03 fix: No async. pdfplumber is sync, LLM calls go through
Celery tasks or sync callables — never asyncio.run().
"""

from __future__ import annotations

import logging

from concept_templates.schemas import ExtractionResult

logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_bytes: bytes) -> ExtractionResult:
    """
    Extract text from PDF bytes using pdfplumber.

    Synchronous — safe for Django views and Celery tasks.
    """
    try:
        import pdfplumber
    except ImportError as exc:
        raise ImportError(
            "pdfplumber required: pip install iil-concept-templates[pdf]"
        ) from exc

    warnings: list[str] = []
    pages_text: list[str] = []

    try:
        import io

        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            page_count = len(pdf.pages)
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text:
                    pages_text.append(text)
                else:
                    warnings.append(f"Seite {i + 1}: kein Text extrahiert (Scan?)")
    except Exception as exc:
        logger.warning("PDF extraction failed: %s", exc)
        return ExtractionResult(
            text="",
            page_count=0,
            warnings=[f"PDF-Extraktion fehlgeschlagen: {exc}"],
        )

    return ExtractionResult(
        text="\n\n".join(pages_text),
        page_count=page_count,
        metadata={"pages_with_text": len(pages_text)},
        warnings=warnings,
    )
```

### Dependencies (`pyproject.toml`) — H-03 korrigiert

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "iil-concept-templates"
version = "0.1.0"
description = "Shared schemas, frameworks and extraction for structured concept templates (ADR-147)"
readme = "README.md"
license = {text = "Proprietary"}
requires-python = ">=3.11"
authors = [
    { name = "Achim Dehnert", email = "achim.dehnert@iil.gmbh" },
]
dependencies = [
    "pydantic>=2.0",
]

[project.optional-dependencies]
pdf = ["pdfplumber>=0.10"]
llm = ["iil-outlinefw>=0.2.0"]
django = ["Django>=4.2"]
knowledge = [
    "iil-outlinefw[knowledge]>=0.2.0",
]
# H-03: Explicit deps statt self-reference
full = [
    "pdfplumber>=0.10",
    "iil-outlinefw[knowledge]>=0.2.0",
    "Django>=4.2",
]
dev = [
    "pytest>=8.0",
    "pytest-cov>=5.0",
    "ruff>=0.4",
]

[tool.hatch.build.targets.wheel]
packages = ["concept_templates"]

[tool.ruff]
target-version = "py311"
line-length = 120

[tool.ruff.lint]
select = ["E", "F", "I", "W", "B", "UP"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

### Consumer-Matrix — H-05 korrigiert (ehrlich)

| Consumer | Scope | Status | Ab wann |
|----------|-------|--------|---------|
| **risk-hub** (Brandschutz) | `brandschutz` | **existiert** | Phase A |
| **risk-hub** (Explosionsschutz) | `explosionsschutz` | **existiert** | Phase A |
| **ausschreibungs-hub** | `ausschreibung` | **geplant** | Phase D (Q2 2026) |
| coach-hub | `coaching` | spekulativ | frühestens Q3 2026 |

---

## Phased Rollout

| Phase | Inhalt | Dateien | Aufwand |
|-------|--------|---------|---------|
| **A** | Package scaffolden: Schemas + Frameworks + Registry + Validators. risk-hub: `documents.Document` um `concept_ref_id` erweitern. Upload-UI im Brandschutz-Konzept-Detail. | `platform/packages/concept-templates/*`, `risk-hub/src/documents/models.py`, `risk-hub/src/brandschutz/views.py` | 4-6h |
| **B** | PDF-Extractor + Abstract Models. risk-hub: ConceptDocument-Model (erbt Abstract), Service-Layer, Text-Anzeige im UI. | `concept_templates/extractor.py`, `concept_templates/contrib/django/*`, `risk-hub/src/brandschutz/models.py` | 4-6h |
| **C** | LLM-Analyse: Analyzer + Template-Vorschlag-UI + Verfeinerungs-Flow. Celery-Task für LLM-Calls. | `concept_templates/analyzer.py`, `concept_templates/merger.py`, `risk-hub/src/brandschutz/tasks.py` | 8-12h |
| **D** | ausschreibungs-hub Integration: ConceptDocument-Model, Upload-UI, Framework `ausschreibung_vob`. | `ausschreibungs-hub/src/ausschreibung/models.py` | 4-6h |

---

## Acceptance Criteria

1. `iil-concept-templates` installierbar via `pip install iil-concept-templates`
2. ≥3 vordefinierte Frameworks (Brandschutz MBO, ExSchutz TRGS720, Ausschreibung VOB)
3. risk-hub nutzt Package für Unterlagen-Upload im Brandschutz-Konzept
4. PDF-Upload + Text-Extraktion funktioniert end-to-end
5. ≥80% Test-Coverage auf Package-Ebene
6. **Platform-Konformität**:
   - BigAutoField PK + public_id (oder risk-hub UUIDField-Compat via Abstract)
   - Service-Layer (ADR-041)
   - Soft-Delete (deleted_at)
   - i18n (`_()` auf allen Labels)
   - Kein JSONField (B-04)
   - File-Validierung (K-05)
7. Kein `asyncio.run()` — alle APIs synchron, LLM via Celery-Task
