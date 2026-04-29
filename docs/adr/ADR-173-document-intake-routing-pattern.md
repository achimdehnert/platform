---
status: Proposed
date: 2026-04-29
decision-makers: Achim Dehnert
consulted: []
informed: []
implementation_status: planned
<!-- Drift-Detector-Felder
staleness_months: 6
drift_check_paths:
  - risk-hub/src/intake/
  - risk-hub/src/intake/handlers/
supersedes_check: null
-->
---

# ADR-173: Document Intake Routing Pattern

## Context and Problem Statement

ADR-170 (`iil-ingest`) löst: *"Wie extrahiere ich Text und klassifiziere ein Dokument?"*

Noch ungelöst: *"Was passiert mit dem `IngestedDocument` danach?"*

In risk-hub muss ein hochgeladenes Dokument (SDB, Lieferschein, bestehendes
Ex-Schutzdokument, etc.) in bis zu 4 Bereiche gleichzeitig einfließen:

| Ziel | App | Beispiel |
|------|-----|---------|
| SDS anlegen/aktualisieren | `substances` | SDB von BASF hochladen → SDS-Eintrag |
| Kataster-Eintrag | `explosionsschutz` | Ex-Zonen-Dokument → Kataster |
| Ex-Schutzdoku | `projects` | Bestehendes ExDoc → als Template |
| Template generieren | `projects` | Generisches Dokument → neues Template |

Heute hat jeder Bereich seinen eigenen Upload — oder keinen. Ergebnis: Daten-Silos,
manuelle Mehrfach-Erfassung, kein Zusammenführen möglich.

## Decision Drivers

- **Single Upload → Multi-Target**: Eine Datei soll N Verarbeitungs-Handler anstoßen
- **Erweiterbarkeit**: Neue Targets (GBU, Betriebsanweisung, ...) = 1 neue Handler-Klasse
- **iil-ingest nutzen**: Extraktion + Klassifikation bereits gelöst (ADR-170)
- **LLM-gestützte Vorauswahl**: Cerebras `llama3.1-8b` (~0.3s) schlägt passende Targets vor
- **Kein Over-Engineering**: Phase 1 synchron, kein Celery

## Considered Options

### Option A: Multi-Target Intake Routing als Django-Pattern (empfohlen)
Handler-Protocol + Django-App `intake` pro Hub. Intern, nicht sofort Package.

### Option B: Pro-App-Upload beibehalten
Jede App behält eigenen Upload → Silos bleiben, kein Zusammenführen.
**Abgelehnt.**

### Option C: Sofort als `iil-intake` Package
Business-Logik (SDS-Felder, Kataster-Struktur) zu hub-spezifisch für Generalisierung.
**Zurückgestellt** — erst wenn 2+ weitere Repos dasselbe Pattern nutzen.

### Option D: Celery async ab Phase 1
Overhead zu groß, sync mit HTMX-Feedback reicht für einzelne Dateien.
**Zurückgestellt auf Phase 3.**

## Decision Outcome

**Gewählte Option: Option A — Django-App `intake` als zentraler Eingangskanal.**

Pilot: risk-hub. Pattern wird dokumentiert; sobald 2+ weitere Repos es nutzen →
Extraktion als `iil-intake` Package (analog ADR-169/ADR-170).

### Confirmation

- `intake`-App in risk-hub registriert (`INSTALLED_APPS`)
- `IntakeUpload` + `IntakeResult` Modelle migriert
- Upload-View liefert HTMX-Partial (kein full-page-reload)
- Mindestens 1 Handler (ExDocHandler) funktionsfähig
- `pytest tests/intake/` ≥ 80% Coverage

---

## Architecture

### Schichtenmodell

```
File-Upload (HTMX Drag&Drop)
        ↓
iil-ingest: extract + classify          ← ADR-170
        ↓
LLM-Tipp: suggested_targets             ← Cerebras llama3.1-8b via aifw
        ↓
Nutzer wählt/bestätigt Targets          ← HTMX Checkbox-UI
        ↓
IntakeService.route(upload)
        ↓ ↓ ↓ ↓
  SDS  Kataster  ExDoc  Template        ← Handler (je 1 Klasse)
        ↓
HTMX-Ergebnisliste mit Links
```

### Handler Protocol

```python
from typing import Protocol
from .models import IntakeUpload, IntakeResult

class IntakeHandler(Protocol):
    target_code: str        # z.B. "sds", "exdoc", "kataster"
    label: str              # z.B. "SDS anlegen/aktualisieren"
    icon: str               # Lucide-Icon-Name für UI

    def can_handle(self, doc_type: str) -> bool:
        """Gibt True zurück wenn dieser Handler für den erkannten Typ sinnvoll ist."""
        ...

    def run(self, upload: IntakeUpload) -> IntakeResult:
        """Verarbeitet den Upload und erstellt/aktualisiert den Ziel-Record."""
        ...
```

### DB-Modelle

```python
class IntakeUpload(models.Model):
    facility = models.ForeignKey("tenancy.Facility", on_delete=models.PROTECT)
    original_filename = models.CharField(max_length=255)
    file = models.FileField(upload_to="intake/%Y/%m/")

    # iil-ingest Ergebnis
    doc_type = models.CharField(max_length=100, blank=True)
    doc_type_confidence = models.CharField(max_length=10, blank=True)  # HIGH/MEDIUM/LOW
    extracted_text = models.TextField(blank=True)

    # Routing
    suggested_targets = models.JSONField(default=list)   # LLM-Vorschlag
    selected_targets = models.JSONField(default=list)    # Nutzer-Auswahl

    status = models.CharField(
        max_length=20,
        choices=[("pending","Pending"),("processing","Processing"),
                 ("done","Fertig"),("error","Fehler")],
        default="pending",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Intake Upload"


class IntakeResult(models.Model):
    upload = models.ForeignKey(IntakeUpload, on_delete=models.CASCADE,
                               related_name="results")
    target_code = models.CharField(max_length=50)       # "sds", "exdoc", ...
    status = models.CharField(
        max_length=10,
        choices=[("ok","OK"),("error","Fehler"),("skipped","Übersprungen")],
    )
    result_id = models.IntegerField(null=True, blank=True)  # PK des erstellten Objekts
    result_url = models.CharField(max_length=500, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("upload", "target_code")]
        verbose_name = "Intake Result"
```

### Handler Registry

```python
# intake/registry.py
_REGISTRY: dict[str, IntakeHandler] = {}

def register(handler: IntakeHandler) -> None:
    _REGISTRY[handler.target_code] = handler

def get_handler(target_code: str) -> IntakeHandler | None:
    return _REGISTRY.get(target_code)

def all_handlers() -> list[IntakeHandler]:
    return list(_REGISTRY.values())
```

### IntakeService

```python
# intake/services.py
def ingest_file(upload: IntakeUpload) -> None:
    """Phase 1: iil-ingest + LLM-Vorschlag. Kein Routing."""
    from ingest import IngestPipeline
    from aifw.service import sync_completion

    with upload.file.open("rb") as f:
        doc = IngestPipeline().run(f.read(), upload.original_filename)

    upload.doc_type = doc.doc_type
    upload.doc_type_confidence = doc.confidence
    upload.extracted_text = doc.content.text
    upload.suggested_targets = _suggest_targets(doc)   # LLM-Call
    upload.save()


def route(upload: IntakeUpload) -> list[IntakeResult]:
    """Phase 2: Routing zu ausgewählten Handlers."""
    results = []
    for target_code in upload.selected_targets:
        handler = get_handler(target_code)
        if handler is None:
            continue
        result = handler.run(upload)
        result.save()
        results.append(result)
    upload.status = "done" if all(r.status == "ok" for r in results) else "error"
    upload.save(update_fields=["status", "updated_at"])
    return results
```

### Registrierte Handler (Phase 1 → Phase 2)

| Phase | Code | Handler | App |
|-------|------|---------|-----|
| 1 | `exdoc` | `ExDocIntakeHandler` | `projects` |
| 2 | `sds` | `SdsIntakeHandler` | `substances` |
| 2 | `kataster` | `KatasterIntakeHandler` | `explosionsschutz` |
| 2 | `template` | `TemplateIntakeHandler` | `projects` |

### HTMX UI-Flow

```
GET  /intake/new/                 → Upload-Formular (Drag&Drop)
POST /intake/upload/              → ingest_file() → Partial: Target-Auswahl
POST /intake/<pk>/route/          → route() → Partial: Ergebnisliste
GET  /intake/<pk>/status/         → Polling-Partial (optional Phase 3)
```

## Abgrenzung zu bestehenden Systemen

| System | Rolle | Verhältnis |
|--------|-------|-----------|
| **iil-ingest** (ADR-170) | Extraktion + Klassifikation | Wird von IntakeService genutzt |
| **iil-enrichment** (ADR-169) | Record → externe API | Sequenziell nach Intake: ingest → SDS anlegen → enrichment |
| **paperless-docs** | ARCHIVE: OCR, Speichern, Suchen | Komplementär — Intake ist PROCESSING |
| **aifw** | LLM-Routing | Target-Vorschlag via `intake_routing` Action |

## Konsequenzen

### Positiv
- Zentraler Upload-Punkt für alle Dateitypen
- Jeder neue Handler = 1 Python-Klasse, kein View/Template-Umbau
- `iil-ingest` wird einmalig aufgerufen → alle Handler nutzen denselben Text
- LLM-Vorauswahl reduziert manuelle Arbeit

### Negativ / Risiken
- Phase 1 synchron → bei großen PDFs (>50 Seiten) HTTP-Timeout möglich
  → Mitigation: Timeout-Warnung im UI + Phase 3 Celery
- `IntakeResult.result_id` ist kein echter FK → Generic Relation in Phase 3

## Implementierungsplan

| Phase | Aufgabe | Aufwand |
|-------|---------|---------|
| 1 | `intake` App: models, migrations, services, registry | 1h |
| 1 | ExDocIntakeHandler | 1h |
| 1 | HTMX Upload-UI + Target-Auswahl + Ergebnisliste | 2h |
| 1 | Tests: ≥80% Coverage | 1h |
| 2 | SdsIntakeHandler, KatasterIntakeHandler | 2h |
| 3 | Celery async, `iil-intake` Package-Evaluation | TBD |

## More Information

- **ADR-170**: iil-ingest — Extraktion + Klassifikation (Basis-Layer)
- **ADR-169**: iil-enrichment — Pattern-Vorbild für Handler-Protocol
- **ADR-048**: HTMX Playbook — UI-Konventionen
- **Pilot**: risk-hub `intake`-App
- **Zukünftig**: `iil-intake` Package wenn 2+ weitere Repos
