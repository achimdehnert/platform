# ADR-147 Review — Principal Architect Assessment

**Reviewer**: Principal IT-Architekt / Senior Python-Entwickler
**Datum**: 2026-03-26
**ADR**: ADR-147 `iil-concept-templates` — Shared Package für strukturierte Konzept-Vorlagen
**Gesamturteil**: ❌ **CHANGES REQUESTED** — 5 Blocker, 5 Kritisch, 6 Hoch, 4 Medium

---

## 1. Review-Tabelle

### BLOCKER — verhindert korrekte Funktion oder verletzt Platform-Standard

| ID | Befund | Stelle | Korrektur |
|----|--------|--------|-----------|
| **B-01** | `tenant_id = UUIDField` — Platform-Standard verlangt `BigIntegerField(db_index=True)`. content-store (ADR-130) nutzt korrekt `BigIntegerField`. ADR-147 übernimmt den **falschen** risk-hub-Pattern. | `ConceptDocument.tenant_id` (Z.310) | `tenant_id = models.BigIntegerField(db_index=True, verbose_name=_("Tenant ID"))` — risk-hub muss separat migriert werden (eigenes Issue). |
| **B-02** | **Kein `public_id`** — Alle User-Data-Modelle brauchen `public_id = UUIDField(default=uuid4, unique=True, editable=False)` für URL-Exposition. ADR zeigt weder PK noch public_id. | `ConceptDocument` Model (Z.308-324) | BigAutoField PK (Django-Default, nicht überschreiben) + `public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)` |
| **B-03** | **Kein Soft-Delete** — Platform-Standard verlangt `deleted_at` auf allen User-Data-Modellen. Upload-Dateien dürfen nicht hart gelöscht werden (Audit-Trail, Compliance). | `ConceptDocument` Model (Z.308-324) | `deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)` + Manager mit `exclude(deleted_at__isnull=False)` |
| **B-04** | `extracted_data = JSONField` — **BANNED** per DB-001 (platform-context). JSONField ist nur für wirklich unstrukturierte externe API-Payloads erlaubt. Template-Strukturen sind definiert (Pydantic-Schemas vorhanden!). | `ConceptDocument.extracted_data` (Z.317) | `extracted_data_raw = models.TextField(blank=True, default="")` für serialisierten JSON-String. Deserialisierung via Service-Layer zu Pydantic-Schemas. Oder: normalisierte Related-Models für strukturierte Daten. |
| **B-05** | **risk-hub Inkompatibilität**: ADR behauptet "ADR-022 konform: BigAutoField" (Acceptance Criteria Z.348), aber **alle** risk-hub Models nutzen `UUIDField(primary_key=True)` (brandschutz, documents, explosionsschutz). Package-Models mit BigAutoField können nicht via FK auf risk-hub-Models verweisen und umgekehrt. | Acceptance Criteria (Z.348), gesamte risk-hub Codebasis | **Zwei Optionen**: (a) Package liefert Abstract-Models, Consumer definiert PK-Typ → empfohlen. (b) risk-hub-Migration auf BigAutoField vor Integration → zu aufwändig für Phase A. ADR muss dies explizit adressieren. |

### KRITISCH — schwerwiegender Architektur-/Sicherheitsfehler

| ID | Befund | Stelle | Korrektur |
|----|--------|--------|-----------|
| **K-01** | **Kein Service-Layer definiert** — ADR zeigt nur Models und Pydantic-Schemas. Kein `services.py` im Package oder bei Consumern spezifiziert. Business-Logik (Template-Erstellung, PDF-Extraktion, Merging) muss durch Service-Layer fließen (ADR-041). | Package-Struktur (Z.123-138) | `services.py` mit `create_document()`, `extract_text()`, `create_template_from_pdf()`, `merge_templates()`. Views rufen ausschließlich Services auf. |
| **K-02** | **Keine i18n** — Alle Model-Strings hardcoded Deutsch. Platform-Standard: `_()` und `{% trans %}` ab Tag 1. `DocumentCategory` Labels, `verbose_name`, `help_text` — alles ohne i18n. | `DocumentCategory` (Z.297-306), Model Meta | Alle Labels mit `from django.utils.translation import gettext_lazy as _` wrappen. Beispiel: `GRUNDRISS = "grundriss", _("Grundriss (DXF/DWG)")` |
| **K-03** | **Async-API ohne ASGI-Strategie** — `extract_template_from_pdf` und `merge_templates` sind `async def` (Z.240-264). Kein Hinweis wie diese aus Django-Views aufgerufen werden. `asyncio.run()` ist verboten im ASGI-Kontext. | `extractor.py` (Z.239-264) | Sync-Wrapper via `asgiref.async_to_sync` oder Celery-Task. Alternativ: rein synchrone API (pdfplumber ist sync, LLM-Calls via Celery). Empfehlung: **synchrone Kern-API**, Celery-Task für LLM-Calls. |
| **K-04** | **`scope` als freier CharField** — Kein TextChoices, kein Validator. Jeder String akzeptiert → Dateninkonsistenz. | `ConceptDocument.scope` (Z.311) | `TextChoices`-Enum: `BRANDSCHUTZ = "brandschutz"`, `EXPLOSIONSSCHUTZ = "explosionsschutz"`, `AUSSCHREIBUNG = "ausschreibung"`. |
| **K-05** | **Keine Datei-Validierung** — `FileField` ohne Größenlimit oder Typ-Prüfung. Beliebige Dateien hochladbar → Sicherheitsrisiko (ZIP-Bombs, Executables). | `ConceptDocument.file` (Z.315) | `FileField` + Custom-Validator: max 50 MB, erlaubte Extensions (`.pdf`, `.docx`, `.dxf`, `.dwg`, `.jpg`, `.png`), MIME-Type-Check im Service-Layer. |

### HOCH — signifikante Qualitätsprobleme

| ID | Befund | Stelle | Korrektur |
|----|--------|--------|-----------|
| **H-01** | **Kein `updated_at`** auf `ConceptDocument` — Standard-Audit-Feld fehlt. | Model (Z.308-324) | `updated_at = models.DateTimeField(auto_now=True)` |
| **H-02** | **`upload_to` ohne Tenant-Isolation** — `concept_documents/%Y/%m/` mischt Dateien aller Tenants im selben Verzeichnis. Keine Tenant-Trennung auf Storage-Ebene. | `ConceptDocument.file` (Z.315) | `upload_to=concept_document_upload_path` mit Callable: `f"tenants/{instance.tenant_id}/concept_docs/{instance.public_id}/{filename}"` |
| **H-03** | **Selbstreferenzierende Optional-Dependency** — `full = ["iil-concept-templates[llm,pdf,django,knowledge]"]` ist fragil und erzeugt zirkuläre Auflösung bei manchen pip-Versionen. | `pyproject.toml` (Z.290) | Explizite Deps: `full = ["iil-outlinefw[knowledge]>=0.2.0", "pdfplumber>=0.10", "Django>=4.2", "iil-content-store>=0.1.0"]` |
| **H-04** | **Kein DATABASE_ROUTER** — Unklar ob shared DB (wie content-store) oder App-lokale DB. Bei abstract Models nicht nötig, aber ADR spezifiziert dies nicht. | Package-Architektur | Klare Entscheidung: Abstract-Models (kein Router nötig) oder Concrete + Router. Empfehlung: **Abstract-Models** — Consumer erbt und fügt app-spezifische FKs hinzu. |
| **H-05** | **Consumer-Matrix übertrieben** — "≥2 Consumer ab Tag 1" (Z.66, Z.114), aber ausschreibungs-hub existiert nicht. Tatsächlich 1 Consumer (risk-hub). ADR-146 verlangt klare Consumer-Evidenz. | Consumer-Matrix (Z.269-275) | Ehrlich: "1 Consumer ab Tag 1 (risk-hub), 2. Consumer geplant (ausschreibungs-hub Q2 2026)". Alternativ: Start als risk-hub-interne App, Extraktion bei 2. Consumer (YAGNI). |
| **H-06** | **Bestehendes `documents`-App ignoriert** — risk-hub hat bereits `documents.Document` mit Category-Enum (inkl. `brandschutz`, `explosionsschutz`, `sdb`, `pruefbericht`) und S3-basiertem Upload mit Versionierung. ADR-147 dupliziert dieses System statt es zu erweitern. | ADR Context (Z.27-31) | **Empfehlung**: Bestehende `documents`-App um `concept_ref_id` + `extracted_text` erweitern statt neues Modell. Oder: klare Abgrenzung dokumentieren (documents = fertiges Dokument, ConceptDocument = Arbeitsunterlage für Konzepterstellung). |

### MEDIUM — Verbesserungen ohne Blockiercharakter

| ID | Befund | Stelle | Korrektur |
|----|--------|--------|-----------|
| **M-01** | `metadata: dict = {}` in Pydantic-Schema — funktional korrekt (Pydantic kopiert), aber `Field(default_factory=dict)` ist expliziter. | `schemas.py` (Z.173) | `metadata: dict = Field(default_factory=dict)` |
| **M-02** | `field_type: str` als freier String — keine Typ-Sicherheit. | `TemplateField.field_type` (Z.149) | `field_type: Literal["text", "number", "date", "choice", "file", "boolean"]` |
| **M-03** | **Keine Framework-Versionierung** — Was passiert wenn MBO geändert wird? Kein `framework_version` oder `valid_from`/`valid_until`. | `ConceptTemplate` Schema (Z.165-173) | `framework_version: str = "1.0"` + `valid_from: date | None = None` |
| **M-04** | **Kein `__str__`** auf `ConceptDocument` Model. | Model (Z.308-324) | `def __str__(self) -> str: return f"{self.title} ({self.get_category_display()})"` |

---

## 2. Architektur-Alternative

### Alternative A: Erweiterung der bestehenden `documents`-App (empfohlen für Phase A)

risk-hub hat bereits eine voll funktionsfähige `documents`-App mit:
- S3-basiertem Upload mit Versionierung (`DocumentVersion`)
- Category-Enum inkl. `brandschutz`, `explosionsschutz`, `sdb`, `pruefbericht`
- Service-Layer (`documents/services.py`)
- SHA-256 Deduplizierung
- Tenant-Isolation

**Vorschlag**: `documents.Document` um `concept_ref_id` erweitern + `extracted_text` Feld.
Das Package `iil-concept-templates` liefert dann **nur** die Pure-Python-Logik:
- Pydantic-Schemas (TemplateSection, TemplateField, ConceptTemplate)
- Framework-Registry + vordefinierte Frameworks
- PDF-Text-Extraktor (pdfplumber)
- LLM-Struktur-Analysator
- Template-Merger
- Export (Markdown, JSON)

**Keine Django-Models im Package** — die leben im Consumer (risk-hub `documents`-App).

**Trade-off**:
- ✅ Kein neues Django-Model, kein Migration-Overhead
- ✅ Bestehende S3-Infrastruktur wiederverwendet
- ✅ Package bleibt pure Python (einfacher zu testen, kein Django-Dependency im Core)
- ❌ Enge Kopplung an risk-hub `documents`-App (andere Hubs brauchen eigene Models)

### Alternative B: Abstract Django Models im Package

Package liefert `AbstractConceptDocument` als Basis:

```python
class AbstractConceptDocument(models.Model):
    """Abstract base — Consumer erbt und fügt app-spezifische FKs hinzu."""
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    tenant_id = models.BigIntegerField(db_index=True)
    scope = models.CharField(max_length=30, choices=ConceptScope.choices)
    category = models.CharField(max_length=30, choices=DocumentCategory.choices)
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to=_upload_path)
    extracted_text = models.TextField(blank=True, default="")
    extracted_data_raw = models.TextField(blank=True, default="")
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
```

Consumer in risk-hub:
```python
class ConceptDocument(AbstractConceptDocument):
    concept = models.ForeignKey(FireProtectionConcept, on_delete=models.CASCADE, ...)

    class Meta:
        db_table = "brandschutz_concept_document"
```

**Trade-off**:
- ✅ Wiederverwendbar über Hubs hinweg
- ✅ Consumer fügt eigene FKs + PK-Typ hinzu (kompatibel mit risk-hub UUIDField)
- ✅ Kein DATABASE_ROUTER nötig
- ❌ Django-Dependency im Package (optional via `[django]` Extra)
- ❌ Migrations leben im Consumer, nicht im Package

### Empfehlung

**Phase A**: Alternative A — bestehende `documents`-App erweitern + pure Python Package.
**Phase B+**: Alternative B — Abstract Models im Package für ausschreibungs-hub.

---

## 3. Gesamtbewertung

### Was gut ist
- ✅ Problemerkennung korrekt: Template-Duplikation über Hubs ist real
- ✅ outlinefw-Integration sinnvoll (Framework-Registry Pattern)
- ✅ Pydantic-Schemas als Pure-Python-Kern — richtige Schichtung
- ✅ Phased Rollout statt Big Bang
- ✅ Vordefinierte Frameworks für 3 Domänen

### Was überarbeitet werden muss
- ❌ 5 Blocker gegen Platform-Standards (PK, tenant_id, soft-delete, JSONField, risk-hub-Kompatibilität)
- ❌ Bestehende `documents`-App ignoriert → Duplikation statt Erweiterung
- ❌ Kein Service-Layer spezifiziert
- ❌ Keine i18n
- ❌ Async-Strategie undefiniert
- ❌ Consumer-Count übertrieben

### Nächster Schritt
ADR v2 mit Blocker-Korrekturen erstellen → Separate Datei `ADR-147-v2-concept-templates-package.md`.
