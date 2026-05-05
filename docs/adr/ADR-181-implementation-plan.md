# ADR-147 — Implementierungsplan (produktionsreif)

**Datum**: 2026-03-26
**Basiert auf**: ADR-147-v2 (nach Review-Korrekturen)

---

## Phase A — Package Scaffold + risk-hub Upload-UI (4-6h)

### Schritt A.1: Package erstellen

```
platform/packages/concept-templates/
```

| Datei | Inhalt |
|-------|--------|
| `pyproject.toml` | Siehe ADR-147-v2 |
| `concept_templates/__init__.py` | Version, public API |
| `concept_templates/schemas.py` | Pydantic Schemas (TemplateField, TemplateSection, ConceptTemplate, ExtractionResult, AnalysisResult) |
| `concept_templates/frameworks.py` | BRANDSCHUTZ_MBO, EXSCHUTZ_TRGS720, AUSSCHREIBUNG_VOB |
| `concept_templates/registry.py` | register_framework(), get_framework(), list_frameworks() |
| `concept_templates/validators.py` | validate_upload_file() |
| `concept_templates/export.py` | to_markdown(), to_json(), to_dict() |
| `tests/conftest.py` | Fixtures |
| `tests/test_schemas.py` | Schema-Validierung (≥10 Tests) |
| `tests/test_frameworks.py` | Framework-Integrität (≥6 Tests) |
| `tests/test_registry.py` | Registry CRUD (≥8 Tests) |
| `tests/test_validators.py` | Datei-Validierung (≥8 Tests) |
| `tests/test_export.py` | Export-Formate (≥6 Tests) |
| `README.md` | Dokumentation |

### Schritt A.2: risk-hub — documents-App erweitern

**Datei**: `risk-hub/src/documents/models.py`

```python
# Neues Feld auf Document:
concept_ref_id = models.UUIDField(
    null=True,
    blank=True,
    db_index=True,
    verbose_name=_("Konzept-Referenz"),
    help_text=_("Optional: Verknüpfung zu Brandschutz-/Explosionsschutzkonzept"),
)
scope = models.CharField(
    max_length=30,
    blank=True,
    default="",
    verbose_name=_("Fachbereich"),
    help_text=_("brandschutz, explosionsschutz, etc."),
)
```

**Migration**: `documents/migrations/0003_document_concept_ref.py`

### Schritt A.3: risk-hub — Upload-UI im Brandschutz-Konzept-Detail

**Dateien**:

| Datei | Änderung |
|-------|----------|
| `risk-hub/src/brandschutz/views.py` | `ConceptDocumentUploadView` hinzufügen — ruft `documents.services.upload_document()` auf mit `concept_ref_id=concept.pk` |
| `risk-hub/src/brandschutz/urls.py` | `path("<uuid:concept_pk>/documents/upload/", ...)` |
| `risk-hub/src/templates/brandschutz/concept_detail.html` | "Unterlagen"-Tab mit Upload-Button und Dokumentenliste |
| `risk-hub/src/templates/brandschutz/partials/_tab_documents.html` | Partial für Dokumentenliste (HTMX) |
| `risk-hub/src/templates/brandschutz/document_upload.html` | Upload-Formular |

### Schritt A.4: Tests + Lint

```bash
# Package
cd platform/packages/concept-templates
pytest -v --cov=concept_templates --cov-report=term-missing
ruff check .

# risk-hub
cd risk-hub
ruff check src/brandschutz/ src/documents/
python manage.py test brandschutz documents --settings=config.settings_test
```

### Schritt A.5: Deploy

```bash
# Package auf PyPI
cd platform/packages/concept-templates
hatch build && hatch publish

# risk-hub
git add -A && git commit -m "feat: Unterlagen-Upload für Brandschutzkonzepte (ADR-147 Phase A)"
git push origin main
# CI/CD → deploy
```

---

## Phase B — PDF-Extraktion + Abstract Models (4-6h)

### Schritt B.1: PDF-Extraktor im Package

| Datei | Inhalt |
|-------|--------|
| `concept_templates/extractor.py` | `extract_text_from_pdf()` — synchron, pdfplumber |
| `tests/test_extractor.py` | Tests mit Fixture-PDFs (≥8 Tests) |
| `tests/fixtures/sample_brandschutz.pdf` | Test-PDF |

### Schritt B.2: Abstract Models im Package

| Datei | Inhalt |
|-------|--------|
| `concept_templates/contrib/__init__.py` | — |
| `concept_templates/contrib/django/__init__.py` | — |
| `concept_templates/contrib/django/abstract_models.py` | AbstractConceptDocument, AbstractConceptTemplate |
| `concept_templates/contrib/django/services.py` | upload_concept_document(), analyze_document_structure() |
| `concept_templates/contrib/django/apps.py` | AppConfig |

### Schritt B.3: risk-hub — ConceptDocument-Model (erbt Abstract)

**Datei**: `risk-hub/src/brandschutz/models.py` (ergänzen)

```python
from concept_templates.contrib.django.abstract_models import AbstractConceptDocument


class ConceptDocument(AbstractConceptDocument):
    """Unterlage zu einem Brandschutzkonzept."""

    # risk-hub spezifisch: UUIDField PK (Legacy-Compat)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Override tenant_id für risk-hub UUIDField-Compat
    tenant_id = models.UUIDField(db_index=True, verbose_name=_("Tenant ID"))
    # App-spezifischer FK
    concept = models.ForeignKey(
        FireProtectionConcept,
        on_delete=models.CASCADE,
        related_name="concept_documents",
        verbose_name=_("Brandschutzkonzept"),
    )

    class Meta:
        db_table = "brandschutz_concept_document"
        verbose_name = _("Konzept-Unterlage")
        verbose_name_plural = _("Konzept-Unterlagen")
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["tenant_id", "scope"],
                name="ix_bs_cdoc_tenant_scope",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["concept", "title"],
                name="uq_bs_cdoc_title_per_concept",
            ),
        ]
```

### Schritt B.4: Extrahierten Text im UI anzeigen

**Dateien**:

| Datei | Änderung |
|-------|----------|
| `risk-hub/src/brandschutz/views.py` | Upload-View erweitern: PDF → Text-Extraktion via Service |
| `risk-hub/src/templates/brandschutz/partials/_tab_documents.html` | Extrahierter Text anzeigen (collapsible) |

---

## Phase C — LLM-Analyse + Template-Verfeinerungs-UI (8-12h)

### Schritt C.1: Analyzer im Package

| Datei | Inhalt |
|-------|--------|
| `concept_templates/analyzer.py` | `analyze_text()` — synchron, LLM via Callable |
| `concept_templates/merger.py` | `merge_templates()` — N Templates → Master |
| `tests/test_analyzer.py` | Tests mit Mock-LLM (≥10 Tests) |
| `tests/test_merger.py` | Merge-Tests (≥6 Tests) |

**Analyzer-Signatur (synchron, K-03 konform)**:

```python
def analyze_text(
    text: str,
    scope: str,
    llm_callable: Callable[[str], str] | None = None,
    reference_framework: str = "",
) -> AnalysisResult:
    """
    Analyze text to extract concept template structure.

    llm_callable: Sync function(prompt) -> response_text.
    If None, falls back to rule-based keyword extraction.
    """
```

### Schritt C.2: Celery-Task für LLM-Analyse

**Datei**: `risk-hub/src/brandschutz/tasks.py`

```python
from celery import shared_task

@shared_task(bind=True, max_retries=2, soft_time_limit=120)
def analyze_document_task(self, document_id: str, framework: str = "") -> dict:
    """Async LLM-Analyse via Celery — nie asyncio.run()."""
    from concept_templates.contrib.django.services import analyze_document_structure
    # ... LLM-Callable setup via llm-mcp ...
```

### Schritt C.3: Template-Vorschlag-UI

| Datei | Inhalt |
|-------|--------|
| `risk-hub/src/templates/brandschutz/template_proposal.html` | Vorgeschlagene Gliederung, editierbar |
| `risk-hub/src/templates/brandschutz/partials/_template_section.html` | Einzelne Sektion (HTMX inline-edit) |
| `risk-hub/src/brandschutz/views.py` | `TemplateProposalView`, `TemplateRefineView` |

---

## Phase D — ausschreibungs-hub Integration (4-6h)

Scope: Wenn ausschreibungs-hub existiert, ConceptDocument-Model erben +
Framework `ausschreibung_vob` nutzen. Identischer Flow wie risk-hub Phase B.

---

## Abhängigkeiten

```
Phase A ────────────► Phase B ────────────► Phase C
  │                     │                     │
  │ iil-concept-templates 0.1.0               │ 0.2.0 (+ analyzer)
  │ (schemas, frameworks,                     │
  │  registry, validators)                    │
  │                     │                     │
  │                     │ iil-concept-templates[pdf] 0.1.0
  │                     │ (+ extractor, abstract models)
  │                     │
  └──────────────────────────────────────────► Phase D
                                                │
                                     ausschreibungs-hub nutzt 0.2.0+
```

---

## Risiken und Mitigationen

| Risiko | Wahrscheinlichkeit | Mitigation |
|--------|-------------------|------------|
| risk-hub UUIDField-PKs inkompatibel | Hoch (existiert) | Abstract Models: Consumer überschreibt PK + tenant_id Typ |
| pdfplumber scheitert an Scans | Mittel | Warning + OCR-Fallback in Phase C (tesseract optional) |
| LLM-Analyse liefert unbrauchbare Struktur | Mittel | Fallback: regelbasierte Keyword-Extraktion; User-Review obligatorisch |
| ausschreibungs-hub entsteht nie | Niedrig | Package hat Wert für risk-hub allein (2 Scopes: Brandschutz + Ex) |

---

## Checkliste pro Phase

### Phase A ✅-Kriterien
- [ ] `concept_templates` Package installierbar
- [ ] 3 Frameworks registriert und abrufbar
- [ ] File-Validator testet Größe + Extensions
- [ ] Export: to_markdown(), to_json(), to_dict()
- [ ] risk-hub: Upload-Button auf Brandschutz-Konzept-Detail
- [ ] risk-hub: Dokumentenliste auf Konzept-Detail
- [ ] ruff clean, ≥80% Coverage
- [ ] Deployed auf schutztat.de

### Phase B ✅-Kriterien
- [ ] PDF-Text-Extraktion funktioniert end-to-end
- [ ] Abstract Models: public_id, soft-delete, i18n, kein JSONField
- [ ] ConceptDocument in risk-hub mit FK zu FireProtectionConcept
- [ ] Extrahierter Text im UI sichtbar
- [ ] Migration idempotent

### Phase C ✅-Kriterien
- [ ] LLM-Analyse liefert AnalysisResult mit proposed_template
- [ ] Celery-Task für async LLM-Call (kein asyncio.run())
- [ ] Template-Vorschlag-UI mit Edit-Möglichkeit
- [ ] Template-Merge: N Dokumente → 1 Master
- [ ] Verfeinerungsloop: Edit → Re-Analyze → Final
