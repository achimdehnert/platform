---
status: "proposed"
date: 2026-03-26
decision-makers: [Achim Dehnert]
consulted: []
informed: []
supersedes: []
amends: []
related: ["ADR-130-content-store-shared-persistence.md", "ADR-146-package-consolidation-strategy.md", "ADR-041-django-component-pattern.md", "ADR-022-platform-consistency-standard.md"]
implementation_status: not_started
implementation_evidence: []
---

# ADR-147: `iil-concept-templates` — Shared Package für strukturierte Konzept-Vorlagen

## Context and Problem Statement

Mehrere Platform-Hubs arbeiten mit **strukturierten Fachkonzepten**, die:

1. **Branchenspezifische Gliederungen** haben (Brandschutz nach MBO, Explosionsschutz nach TRGS 720ff, Ausschreibungen nach VOB/VgV)
2. **Aus Bestandsdokumenten gelernt** werden sollen (Kunden-PDFs → Struktur extrahieren → Template)
3. **Iterativ verfeinert** werden (Upload → LLM-Vorschlag → User-Review → Master-Template)
4. **Mandantenspezifische Varianten** erlauben (Master-Template → Kunden-Fork)

Aktuell hat jeder Hub eigene, isolierte Konzept-Modelle ohne gemeinsame Template-/Dokumenten-Logik:

| Hub | Konzept-Model | Template-System | Dokumenten-Upload |
|-----|---------------|-----------------|-------------------|
| **risk-hub** (Brandschutz) | `FireProtectionConcept` | ❌ keins | ❌ keins |
| **risk-hub** (Explosionsschutz) | `ExplosionConcept` | ❌ keins | `VerificationDocument` (einfach) |
| **ausschreibungs-hub** | (geplant) | ❌ keins | ❌ keins |

**Problem**: Jeder Hub müsste Template-Logik, PDF-Extraktion, LLM-Strukturerkennung und
iterative Verfeinerung eigenständig implementieren — massiver Duplikationsaufwand.

---

## Decision Drivers

- **DRY**: Template-Erstellung, PDF-Extraktion und LLM-Analyse sind domänen-übergreifend identisch
- **Wiederverwendbarkeit**: risk-hub (Brandschutz + Explosionsschutz) und ausschreibungs-hub profitieren sofort; weitere Hubs (coach-hub Coaching-Konzepte, cad-hub Projektvorlagen) können folgen
- **outlinefw-Integration**: `iil-outlinefw` bietet bereits Framework-Registry, Gliederungs-Generierung und Outline-Wiki-Knowledge-Enrichment — diese Infrastruktur soll genutzt werden
- **content-store-Integration**: Versionierte Template-Speicherung via `iil-content-store` (ADR-130) vermeidet erneute Implementierung von SHA-256-Deduplizierung und Versionierung
- **ADR-146 Konformität**: Neues Package muss in die konsolidierte Package-Landschaft passen
- **ADR-022 Konformität**: Django-Models mit BigAutoField, Service-Layer, kein hardcoded SQL

---

## Considered Options

### Option 1 — Shared PyPI Package `iil-concept-templates` (gewählt)

Ein eigenständiges Package in `platform/packages/concept-templates/` mit:
- Pure-Python-Kern (Schemas, Frameworks, Extractor, Merger) — kein Django erforderlich
- Optionale Django-Models via `[django]` Extra
- Integration mit `iil-outlinefw` für Gliederungs-Generierung
- Integration mit `iil-content-store` für versionierte Speicherung

**Pro:**
- Ein Package, N Consumer (risk-hub, ausschreibungs-hub, weitere)
- Klare Trennung: Kern-Logik (pure Python) vs. Django-Integration (optional)
- outlinefw-Ökosystem wird erweitert statt dupliziert
- Testbar ohne Django-Stack

**Contra:**
- Neues Package in der Landschaft (aber ADR-146-konform: klarer Zweck, ≥2 Consumer)
- Dependency auf outlinefw und content-store

---

### Option 2 — Django App direkt in risk-hub

Template-Logik als Django-App `concept_templates` in risk-hub.

**Pro:** Kein neues Package, schnell implementiert

**Contra:**
- ausschreibungs-hub kann nicht nutzen → Duplikation
- Pure-Python-Tests nicht möglich
- Widerspricht DRY bei ≥2 Consumern

**Verworfen**: Löst Wiederverwendbarkeit strukturell nicht.

---

### Option 3 — Erweiterung von content-store

Template-Schemas und LLM-Logik direkt in `iil-content-store` integrieren.

**Pro:** Kein zusätzliches Package

**Contra:**
- content-store ist reine Persistenz (ADR-130) — Domain-Logik widerspricht SRP
- content-store hat keine LLM-Dependency und soll keine bekommen
- Erzwingt LLM-Dependencies auf alle content-store-Consumer

**Verworfen**: Verletzt Single Responsibility.

---

## Decision Outcome

**Gewählt: Option 1** — Eigenständiges Package `iil-concept-templates` mit outlinefw- und content-store-Integration.

### Positive Consequences

- Einheitliches Template-System für Brandschutz, Explosionsschutz und Ausschreibungen
- outlinefw-Ökosystem wächst organisch (Story-Outlines → Fachkonzept-Outlines)
- Iterativer Template-Lernprozess (Upload → Analyse → Verfeinerung → Master) als Kern-Feature
- PDF-Extraktion und LLM-Strukturerkennung sind zentral getestet

### Negative Consequences

- Neues Package erfordert Pflege (mitigiert: klare Scope-Abgrenzung, ≥2 Consumer ab Tag 1)
- Dependencies: outlinefw + content-store (mitigiert: beides optional via Extras)

---

## Implementation Details

### Package-Struktur

```
platform/packages/concept-templates/
├── concept_templates/
│   ├── __init__.py
│   ├── schemas.py              # ConceptTemplate, TemplateSection, TemplateField (pydantic)
│   ├── frameworks.py           # Brandschutz/ExSchutz/Ausschreibungs-Frameworks
│   ├── registry.py             # register_framework(), get_framework()
│   ├── extractor.py            # PDF → Text → structure_json
│   ├── generator.py            # Template + Kontext → Konzept-Gliederung (via outlinefw)
│   ├── merger.py               # N Templates → Master-Template
│   ├── export.py               # to_markdown(), to_json(), to_docx()
│   └── django_models.py        # ConceptTemplate, ConceptDocument (optional [django])
├── pyproject.toml
├── tests/
└── README.md
```

### Kern-Schemas (`schemas.py`)

```python
from pydantic import BaseModel

class TemplateField(BaseModel):
    """Einzelnes Feld innerhalb einer Template-Sektion."""
    name: str
    label: str
    field_type: str  # "text", "number", "date", "choice", "file", "boolean"
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
    fields: list[TemplateField] = []
    subsections: list["TemplateSection"] = []

class ConceptTemplate(BaseModel):
    """Vollständiges Konzept-Template (Master oder Kunden-Variante)."""
    name: str
    scope: str  # "brandschutz", "explosionsschutz", "ausschreibung"
    version: int = 1
    is_master: bool = False
    framework: str = ""  # z.B. "brandschutz_mbo", "exschutz_trgs720"
    sections: list[TemplateSection] = []
    metadata: dict = {}
```

### Vordefinierte Frameworks (`frameworks.py`)

```python
BRANDSCHUTZ_MBO = ConceptTemplate(
    name="Brandschutzkonzept §14 MBO",
    scope="brandschutz",
    is_master=True,
    framework="brandschutz_mbo",
    sections=[
        TemplateSection(name="standort", title="1. Standortbeschreibung", required=True, fields=[
            TemplateField(name="address", label="Adresse", field_type="text", required=True),
            TemplateField(name="building_class", label="Gebäudeklasse", field_type="choice",
                         choices=["GK1", "GK2", "GK3", "GK4", "GK5"]),
            TemplateField(name="usage_type", label="Nutzungsart", field_type="text"),
        ]),
        TemplateSection(name="brandabschnitte", title="2. Brandabschnitte", required=True),
        TemplateSection(name="fluchtwege", title="3. Flucht- und Rettungswege", required=True),
        TemplateSection(name="massnahmen", title="4. Brandschutzmaßnahmen", required=True, subsections=[
            TemplateSection(name="baulich", title="4.1 Bauliche Maßnahmen"),
            TemplateSection(name="technisch", title="4.2 Anlagentechnische Maßnahmen"),
            TemplateSection(name="organisatorisch", title="4.3 Organisatorische Maßnahmen"),
        ]),
        TemplateSection(name="loescheinrichtungen", title="5. Löscheinrichtungen", required=False),
        TemplateSection(name="prueffristen", title="6. Prüffristen", required=False),
    ],
)

EXSCHUTZ_TRGS720 = ConceptTemplate(
    name="Explosionsschutzkonzept TRGS 720ff",
    scope="explosionsschutz",
    is_master=True,
    framework="exschutz_trgs720",
    sections=[
        TemplateSection(name="stoffdaten", title="1. Stoffdaten und Eigenschaften", required=True),
        TemplateSection(name="zoneneinteilung", title="2. Zoneneinteilung", required=True),
        TemplateSection(name="zuendquellen", title="3. Zündquellenanalyse", required=True),
        TemplateSection(name="primaer", title="4. Primärer Explosionsschutz", required=True),
        TemplateSection(name="sekundaer", title="5. Sekundärer Explosionsschutz", required=True),
        TemplateSection(name="konstruktiv", title="6. Konstruktiver Explosionsschutz"),
        TemplateSection(name="betriebsanweisungen", title="7. Betriebsanweisungen"),
    ],
)

AUSSCHREIBUNG_VOB = ConceptTemplate(
    name="Ausschreibung nach VOB/A",
    scope="ausschreibung",
    is_master=True,
    framework="ausschreibung_vob",
    sections=[
        TemplateSection(name="auftraggeber", title="1. Auftraggeber", required=True),
        TemplateSection(name="leistungsbeschreibung", title="2. Leistungsbeschreibung", required=True),
        TemplateSection(name="mengen", title="3. Mengen und Massen", required=True),
        TemplateSection(name="vertragsbedingungen", title="4. Vertragsbedingungen", required=True),
        TemplateSection(name="eignungskriterien", title="5. Eignungskriterien"),
        TemplateSection(name="zuschlagskriterien", title="6. Zuschlagskriterien"),
        TemplateSection(name="fristen", title="7. Fristen und Termine"),
        TemplateSection(name="anlagen", title="8. Anlagen und Nachweise"),
    ],
)
```

### Iterativer Lernprozess (`extractor.py`)

```python
async def extract_template_from_pdf(
    pdf_bytes: bytes,
    scope: str,
    llm_router: AsyncLLMRouter,
    reference_framework: str | None = None,
) -> ConceptTemplate:
    """
    PDF → Text → LLM → ConceptTemplate.

    1. Text-Extraktion via pdfplumber
    2. LLM-Prompt: Gliederung erkennen
    3. Abgleich mit Reference-Framework (optional)
    4. Lücken-Erkennung und Empfehlungen
    """
    ...

async def merge_templates(
    templates: list[ConceptTemplate],
    llm_router: AsyncLLMRouter,
) -> ConceptTemplate:
    """
    N Templates → 1 Master-Template.
    Findet gemeinsame Sektionen, optionale Varianten, branchenspez. Extras.
    """
    ...
```

### Consumer-Matrix

| Consumer | Scope | Ab wann |
|----------|-------|---------|
| **risk-hub** (Brandschutz) | `brandschutz` | Phase A (sofort) |
| **risk-hub** (Explosionsschutz) | `explosionsschutz` | Phase A (sofort) |
| **ausschreibungs-hub** | `ausschreibung` | Phase B (Q2 2026) |
| **coach-hub** (Coaching-Konzepte) | `coaching` | Phase C (optional) |
| **cad-hub** (Projektvorlagen) | `cad_project` | Phase C (optional) |

### Dependencies

```toml
[project]
name = "iil-concept-templates"
version = "0.1.0"
dependencies = ["pydantic>=2.0"]

[project.optional-dependencies]
llm = ["iil-outlinefw>=0.2.0"]
pdf = ["pdfplumber>=0.10"]
django = ["Django>=4.2", "iil-content-store>=0.1.0"]
knowledge = ["iil-outlinefw[knowledge]>=0.2.0"]
full = ["iil-concept-templates[llm,pdf,django,knowledge]"]
dev = ["pytest>=8.0", "pytest-asyncio>=0.23", "ruff>=0.4"]
```

### Unterlagen-Upload (Django Model, `[django]` Extra)

```python
class DocumentCategory(models.TextChoices):
    GRUNDRISS = "grundriss", "Grundriss (DXF/DWG)"
    PRODUKTDATENBLATT = "produktdatenblatt", "Produktdatenblatt"
    SICHERHEITSDATENBLATT = "sdb", "Sicherheitsdatenblatt"
    STANDORTBESCHREIBUNG = "standort", "Standortbeschreibung"
    PRUEFBERICHT = "pruefbericht", "Prüfbericht"
    BEHOERDLICHE_AUFLAGE = "auflage", "Behördliche Auflage"
    LEISTUNGSVERZEICHNIS = "lv", "Leistungsverzeichnis"
    BESTANDSKONZEPT = "bestandskonzept", "Bestehendes Konzept (Vorlage)"
    SONSTIGES = "sonstiges", "Sonstiges"

class ConceptDocument(models.Model):
    """Unterlage zu einem Schutz-/Ausschreibungskonzept."""
    tenant_id = models.UUIDField(db_index=True)
    scope = models.CharField(max_length=30)  # brandschutz, explosionsschutz, ausschreibung
    concept_ref_id = models.UUIDField(db_index=True)  # FK zum jeweiligen Konzept
    category = models.CharField(max_length=30, choices=DocumentCategory.choices)
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to="concept_documents/%Y/%m/")
    extracted_text = models.TextField(blank=True, default="")
    extracted_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "concept_templates"
        indexes = [
            models.Index(fields=["tenant_id", "scope", "concept_ref_id"]),
        ]
```

---

## Phased Rollout

| Phase | Inhalt | Aufwand | Abhängigkeiten |
|-------|--------|---------|----------------|
| **A** | Schemas + Frameworks + Django Models + Upload-UI in risk-hub | 4-6h | — |
| **B** | PDF-Extraktor + "Aus Vorlage erstellen" in risk-hub | 4-6h | pdfplumber |
| **C** | LLM-Analyse + Template-Editor + Merger + outlinefw-Integration | 8-12h | outlinefw, llm-mcp |
| **D** | ausschreibungs-hub Integration | 4-6h | Phase A |

---

## Acceptance Criteria

1. `iil-concept-templates` ist auf PyPI veröffentlicht
2. ≥3 vordefinierte Frameworks (Brandschutz MBO, ExSchutz TRGS720, Ausschreibung VOB)
3. risk-hub nutzt Package für Template-basierte Konzepterstellung (Brandschutz + ExSchutz)
4. PDF-Upload + Text-Extraktion funktioniert end-to-end
5. LLM-basierte Strukturerkennung liefert valides `ConceptTemplate` aus beliebigem Konzept-PDF
6. ≥80% Test-Coverage auf Package-Ebene
7. ADR-022 konform: BigAutoField, Service-Layer, Django ORM
