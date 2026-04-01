---
status: "proposed"
date: 2026-03-25
decision-makers: [Achim Dehnert]
consulted: []
informed: []
supersedes: []
amends: []
related:
  - ADR-149  # Inbound Scan (Phase 1 — liefert InboundScanRecord)
  - ADR-147  # dvelop_mcp (Phase 2 — Gate)
  - ADR-150  # DMS Rollout-Plan (Phase 3)
  - ADR-068  # Adaptive Model Routing (aifw-Kontext)
  - ADR-045  # Secrets Management
staleness_months: 6
drift_check_paths:
  - dms-hub/src/dms_inbound/classify.py
  - dms-hub/src/dms_inbound/tasks.py
---

# ADR-148: Adopt aifw-gestützte Dokumentenklassifikation für d.velop Inbound-Scan

## Metadaten

| Attribut       | Wert                                                               |
|----------------|--------------------------------------------------------------------|
| **Status**     | Proposed                                                           |
| **Scope**      | dms-hub                                                            |
| **Erstellt**   | 2026-03-25                                                         |
| **Autor**      | Achim Dehnert                                                      |
| **Relates to** | ADR-149, ADR-147, ADR-150, ADR-068, ADR-045                        |

## Repo-Zugehörigkeit

| Repo      | Rolle    | Betroffene Pfade                                           |
|-----------|----------|------------------------------------------------------------|
| `dms-hub` | Primär   | `src/dms_inbound/classify.py` (neu), `tasks.py` (erweit.) |
| `platform`| Referenz | `docs/adr/`                                                |

---

## Decision Drivers

- **Manuelles Einsortieren entfällt**: Nach Phase 1 landen alle Scans in
  `INBOX_UNCLASSIFIED` — Mitarbeitende müssen jedes Dokument händisch einer
  d.velop-Kategorie zuweisen. Bei 20+ Scans/Tag ist das ein Engpass.
- **aifw ist verfügbar**: Der LLM-Routing-Stack (ADR-068/095) läuft produktiv.
  Quality Level `MEDIUM` (Claude Sonnet) ist ausreichend für Dokumentenklassifikation —
  kein High-Reasoning, kein neues Modell.
- **Confidence-Schwelle schützt vor Fehlklassifikationen**: Dokumente mit
  `confidence < 0.85` landen in `INBOX_UNCLASSIFIED` statt automatisch kategorisiert
  zu werden — kein stiller Fehler.
- **Gate: Phase 2 Done**: Der MCP-Server muss produktiv sein, damit ein Agent
  Klassifikationsergebnisse direkt im DMS abfragen und korrigieren kann.

---

## 1. Context and Problem Statement

### 1.1 Ist-Zustand nach Phase 2

`InboundScanRecord` hat `status=SUCCESS` und `dms_document_id` — das Dokument
liegt in d.velop unter der Fallback-Kategorie `INBOUND_UNCLASSIFIED`. Die
d.velop-Suchfunktion ist damit eingeschränkt (Suche nach `INBOUND_BESCHEID`
findet dieses Dokument nicht).

### 1.2 Ziel

Nach dem Upload triggert ein zweiter Celery-Task `classify_inbound_document`.
Er sendet die erste Seite des PDFs als Bild an das LLM, erhält eine
strukturierte JSON-Antwort mit `category`, `tags`, `confidence` und patcht
das d.velop-Dokument via REST API mit der korrekten Kategorie.

```
[process_scan_directory]
       │  on_commit()
       ▼
[import_single_scan]         ← Phase 1, bereits in ADR-149
       │  nach SUCCESS
       ▼
[classify_inbound_document]  ← Phase 3, dieses ADR
       │
       ├─ confidence ≥ 0.85 → d.velop PATCH category
       └─ confidence < 0.85 → bleibt INBOUND_UNCLASSIFIED
```

---

## 2. Considered Options

### Option A — aifw MEDIUM + Bild-Prompt (gewählt) ✅

Erste Seite des PDFs als Base64-Bild an Claude Sonnet senden.
Strukturierter JSON-Prompt mit wenigen Beispielen (Few-Shot).

**Pro:**
- Keine externe OCR-Pipeline nötig — LLM liest Bild direkt
- aifw-Routing bereits verfügbar, kein neues Modell einrichten
- Few-Shot-Beispiele im Prompt sind wartbar ohne Code-Deploy

**Con:**
- Kosten pro Klassifikation ~$0.002–0.005 (Bild-Token)
- Bei sehr schlechter Scan-Qualität kann LLM nicht lesen

### Option B — Textbasiert nach eingebetteter OCR

HP E58650z und iX1600 liefern Searchable-PDFs mit eingebetteten Texten.
Diesen Text an LLM schicken (günstiger, kein Bild).

**Abgelehnt**: Nicht alle Scanner liefern OCR-Text (iX1600 ohne NX Manager).
Textextraktion aus PDF als eigener Step erhöht Komplexität ohne Mehrwert —
Bild-Prompt ist einfacher und robuster.

### Option C — Regelbasierte Klassifikation (Schlüsselwörter)

Einfache String-Matches auf extrahiertem OCR-Text.

**Abgelehnt**: Zu starr für Behördendokumente mit variablem Layout.
Viele Bescheide enthalten das Wort "Bescheid" nicht im Titel.
Fehlklassifikationen sind mit Regeln schwerer debugbar.

---

## 3. Decision Outcome

**Gewählt: Option A.**

Bild-Prompt an aifw MEDIUM. Few-Shot-Beispiele direkt im Prompt,
kein separates Fine-Tuning. `confidence`-Schwelle 0.85 als Gate.

---

## 4. Implementation — Schritte

### Schritt 1 — Model-Erweiterung `InboundScanRecord`

Drei neue Felder per Migration auf die bestehende Tabelle:

```python
# src/dms_inbound/models.py  — Ergänzung
ai_category   = models.CharField(max_length=100, blank=True,
                  help_text="Von LLM vorgeschlagene d.velop-Kategorie-ID")
ai_confidence = models.FloatField(null=True, blank=True,
                  help_text="Konfidenz 0.0–1.0 der Klassifikation")
ai_tags       = models.JSONField(default=list,
                  help_text="Vom LLM extrahierte Schlagworte")
```

```python
# Migration: 0002_inbound_ai_fields.py
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [("dms_inbound", "0001_initial")]
    operations = [
        migrations.AddField("InboundScanRecord", "ai_category",
            models.CharField(max_length=100, blank=True, default="")),
        migrations.AddField("InboundScanRecord", "ai_confidence",
            models.FloatField(null=True, blank=True)),
        migrations.AddField("InboundScanRecord", "ai_tags",
            models.JSONField(default=list)),
    ]
```

---

### Schritt 2 — `classify.py` — Prompt + LLM-Call

```python
# src/dms_inbound/classify.py
from __future__ import annotations
import base64
import io
import json
import logging
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

# ── Konfigurierbares Kategorie-Mapping ───────────────────────────
CATEGORY_MAP: dict[str, str] = {
    "Bebauungsplan":        "INBOUND_BPLAN",
    "Baugenehmigung":       "INBOUND_BAUGENEHMIGUNG",
    "Bescheid":             "INBOUND_BESCHEID",
    "Antrag":               "INBOUND_ANTRAG",
    "Widerspruch":          "INBOUND_WIDERSPRUCH",
    "Protokoll":            "INBOUND_PROTOKOLL",
    "Rechnung":             "INBOUND_RECHNUNG",
    "Vertrag":              "INBOUND_VERTRAG",
    "Dienstanweisung":      "INBOUND_DIENSTANWEISUNG",
    "Pressemitteilung":     "INBOUND_PRESSE",
}

CONFIDENCE_THRESHOLD = 0.85
FALLBACK_CATEGORY    = "INBOUND_UNCLASSIFIED"


@dataclass
class ClassificationResult:
    category_key: str      # Deutsch, z.B. "Bescheid"
    dms_category: str      # d.velop-ID, z.B. "INBOUND_BESCHEID"
    confidence: float      # 0.0–1.0
    tags: list[str]        # Extrahierte Schlagworte
    accepted: bool         # True wenn confidence >= Schwelle


SYSTEM_PROMPT = """\
Du bist ein Klassifikations-Assistent für Behördendokumente.
Analysiere das Bild und antworte ausschließlich mit einem JSON-Objekt — kein Text davor oder danach.

Antworte mit diesem Schema:
{
  "category": "<Kategorie auf Deutsch>",
  "confidence": <0.0 bis 1.0>,
  "tags": ["<Schlagwort1>", "<Schlagwort2>"]
}

Erlaubte Kategorien:
Bebauungsplan, Baugenehmigung, Bescheid, Antrag, Widerspruch,
Protokoll, Rechnung, Vertrag, Dienstanweisung, Pressemitteilung

Wenn keine Kategorie passt oder das Bild nicht lesbar ist, antworte mit:
{"category": "Unbekannt", "confidence": 0.0, "tags": []}

Few-Shot-Beispiele:
- Sichtbar: "Bebauungsplan Nr. 42 Flur 3" → {"category": "Bebauungsplan", "confidence": 0.97, "tags": ["Flur 3"]}
- Sichtbar: "Ihr Antrag vom 12.03.2024 wurde abgelehnt. Bescheid:" → {"category": "Bescheid", "confidence": 0.92, "tags": ["Ablehnung"]}
- Sichtbar: unleserliches handschriftliches Dokument → {"category": "Unbekannt", "confidence": 0.1, "tags": []}
"""


def classify_pdf_first_page(
    pdf_bytes: bytes,
    api_key: str,
    base_url: str = "https://api.anthropic.com",
    model: str = "claude-sonnet-4-20250514",
) -> ClassificationResult:
    """
    Sendet erste PDF-Seite als PNG-Bild an Claude, gibt ClassificationResult zurück.
    Synchron — kein asyncio.run() (Celery-Task-Kontext).
    """
    png_bytes = _pdf_first_page_to_png(pdf_bytes)
    img_b64   = base64.b64encode(png_bytes).decode()

    payload = {
        "model":      model,
        "max_tokens": 256,
        "system":     SYSTEM_PROMPT,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type":       "base64",
                            "media_type": "image/png",
                            "data":       img_b64,
                        },
                    },
                    {"type": "text", "text": "Klassifiziere dieses Dokument."},
                ],
            }
        ],
    }

    with httpx.Client(timeout=30) as client:
        resp = client.post(
            f"{base_url}/v1/messages",
            headers={
                "x-api-key":         api_key,
                "anthropic-version": "2023-06-01",
                "content-type":      "application/json",
            },
            json=payload,
        )
        resp.raise_for_status()

    raw_text = resp.json()["content"][0]["text"].strip()
    return _parse_response(raw_text)


def _parse_response(raw: str) -> ClassificationResult:
    try:
        # Robustes Parsen: JSON auch wenn LLM Markdown-Fences hinzufügt
        raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        data = json.loads(raw)
        key  = data.get("category", "Unbekannt")
        conf = float(data.get("confidence", 0.0))
        tags = data.get("tags", [])
        dms  = CATEGORY_MAP.get(key, FALLBACK_CATEGORY)
        return ClassificationResult(
            category_key=key,
            dms_category=dms if conf >= CONFIDENCE_THRESHOLD else FALLBACK_CATEGORY,
            confidence=conf,
            tags=tags,
            accepted=conf >= CONFIDENCE_THRESHOLD,
        )
    except Exception as exc:
        logger.warning("Klassifikations-Antwort konnte nicht geparst werden: %s — %s", raw, exc)
        return ClassificationResult(
            category_key="Unbekannt",
            dms_category=FALLBACK_CATEGORY,
            confidence=0.0,
            tags=[],
            accepted=False,
        )


def _pdf_first_page_to_png(pdf_bytes: bytes) -> bytes:
    """
    Rendert die erste Seite eines PDFs als PNG.
    Benötigt: pymupdf (fitz) — `pip install pymupdf`
    """
    import fitz  # pymupdf

    doc  = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc[0]
    mat  = fitz.Matrix(2.0, 2.0)   # 2× Zoom = ~150 dpi — ausreichend für OCR-Qualität
    pix  = page.get_pixmap(matrix=mat)
    return pix.tobytes("png")
```

---

### Schritt 3 — Celery-Task `classify_inbound_document`

Wird in `tasks.py` ergänzt — **kein** neuer Task-Typ, nur eine neue
`@shared_task`-Funktion direkt unter `import_single_scan`:

```python
# src/dms_inbound/tasks.py  — Ergänzung

@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    queue="ai",              # eigene Queue — nicht "dms"
    name="dms_inbound.classify_document",
    acks_late=True,
)
def classify_inbound_document(self, *, record_id: str) -> dict:
    """
    Klassifiziert ein bereits in d.velop archiviertes Dokument.
    Patcht die d.velop-Kategorie wenn confidence ≥ 0.85.
    Aufgerufen nach erfolgreichem import_single_scan.
    """
    from platform_context.secrets import read_secret  # noqa: PLC0415
    from .classify import classify_pdf_first_page
    from .models import InboundScanRecord

    try:
        record = InboundScanRecord.objects.get(id=record_id)
    except InboundScanRecord.DoesNotExist:
        logger.error("classify: record %s nicht gefunden", record_id)
        return {"status": "error", "reason": "not_found"}

    # PDF-Bytes aus d.velop holen
    try:
        from dms_hub.client.dvelop_client import DvelopDmsClient  # noqa: PLC0415
        api_key  = read_secret("DVELOP_API_KEY")
        base_url = settings.DVELOP_BASE_URL

        with DvelopDmsClient(base_url=base_url, api_key=api_key) as client:
            pdf_bytes = client.download_file(
                record.dms_repository_id, record.dms_document_id
            )
    except Exception as exc:
        logger.warning("classify: PDF-Download fehlgeschlagen für %s: %s", record_id, exc)
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

    # Klassifikation
    try:
        result = classify_pdf_first_page(
            pdf_bytes=pdf_bytes,
            api_key=read_secret("ANTHROPIC_API_KEY"),
        )
    except Exception as exc:
        logger.warning("classify: LLM-Call fehlgeschlagen für %s: %s", record_id, exc)
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

    # Ergebnis im Record speichern
    InboundScanRecord.objects.filter(id=record_id).update(
        ai_category   = result.dms_category,
        ai_confidence = result.confidence,
        ai_tags       = result.tags,
    )

    # d.velop-Kategorie patchen wenn Konfidenz ausreichend
    if result.accepted:
        try:
            _patch_dvelop_category(record, result.dms_category, api_key, base_url)
            logger.info(
                "classify: %s → %s (confidence=%.2f)",
                record.original_filename, result.dms_category, result.confidence,
            )
        except Exception as exc:
            logger.error("classify: d.velop PATCH fehlgeschlagen: %s", exc)
            # Kein Retry für PATCH — Record-Felder sind bereits gesetzt
            return {"status": "classified_patch_failed", "category": result.dms_category}
    else:
        logger.info(
            "classify: %s → UNCLASSIFIED (confidence=%.2f < %.2f)",
            record.original_filename, result.confidence, 0.85,
        )

    return {
        "status":     "accepted" if result.accepted else "unclassified",
        "category":   result.dms_category,
        "confidence": result.confidence,
        "tags":       result.tags,
    }


def _patch_dvelop_category(
    record: "InboundScanRecord",
    category: str,
    api_key: str,
    base_url: str,
) -> None:
    """Patcht sourceCategory eines bestehenden d.velop-Dokuments."""
    import httpx  # noqa: PLC0415
    url = (
        f"{base_url.rstrip('/')}/dms/r"
        f"/{record.dms_repository_id}/o/{record.dms_document_id}"
    )
    with httpx.Client(timeout=15) as client:
        resp = client.patch(
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type":  "application/hal+json",
                "Origin":        base_url.rstrip("/"),
            },
            json={"sourceCategory": category},
        )
        resp.raise_for_status()
```

---

### Schritt 4 — Task-Dispatch nach erfolgreichem Upload

In `import_single_scan` (ADR-149) am Ende einfügen,
**nach** `record.mark_success(...)`:

```python
# src/dms_inbound/tasks.py — import_single_scan, letzter Block
# ... bestehender Code ...
record.mark_success(dms_doc_id=doc_id, repo_id=repo_id, category="INBOUND_UNCLASSIFIED")

# Phase 3: Klassifikation asynchron anstossen
transaction.on_commit(
    lambda: classify_inbound_document.apply_async(
        kwargs={"record_id": str(record.id)},
        queue="ai",
        countdown=5,        # 5s Verzögerung — d.velop braucht Moment zum Indizieren
    )
)
```

---

### Schritt 5 — Celery-Konfiguration (neue Queue `"ai"`)

```python
# config/settings/base.py — Ergänzung
CELERY_TASK_ROUTES = {
    "dms_archive.tasks.*":   {"queue": "dms"},
    "dms_inbound.tasks.archive_document_to_dms":   {"queue": "dms"},
    "dms_inbound.tasks.process_scan_directory":    {"queue": "dms"},
    "dms_inbound.tasks.import_single_scan":        {"queue": "dms"},
    "dms_inbound.tasks.classify_inbound_document": {"queue": "ai"},  # NEU
}
```

```yaml
# docker-compose.yml — neuer Worker
dms-ai-worker:
  <<: *common
  image: ghcr.io/achimdehnert/dms-hub:${IMAGE_TAG:-develop}
  container_name: dms-hub-ai-worker
  command: celery -A config worker -Q ai -c 2 -l info --without-gossip
  depends_on:
    dms-db:
      condition: service_healthy
    dms-redis:
      condition: service_healthy
  healthcheck:
    test: ["CMD", "celery", "-A", "config", "inspect", "ping",
           "-d", "celery@dms-hub-ai-worker"]
    interval: 60s
    timeout: 15s
    retries: 3
    start_period: 30s
```

---

### Schritt 6 — Tests (`tests/test_classify.py`)

```python
# tests/test_classify.py
import base64
import json
import pytest
import respx
import httpx

from dms_inbound.classify import (
    classify_pdf_first_page,
    ClassificationResult,
    CONFIDENCE_THRESHOLD,
    FALLBACK_CATEGORY,
    _parse_response,
)

API_KEY = "test-key"
BASE    = "https://api.anthropic.com"


def mock_anthropic_response(category: str, confidence: float, tags: list) -> dict:
    return {
        "content": [{"text": json.dumps({
            "category": category, "confidence": confidence, "tags": tags
        })}]
    }


@respx.mock
def test_high_confidence_returns_accepted(tmp_path):
    respx.post(f"{BASE}/v1/messages").mock(
        return_value=httpx.Response(200, json=mock_anthropic_response(
            "Bescheid", 0.93, ["Ablehnung", "2024"]
        ))
    )
    # Minimales gültiges PDF als Stub
    pdf_bytes = b"%PDF-1.4 stub"
    with pytest.MonkeyPatch().context() as mp:
        mp.setattr("dms_inbound.classify._pdf_first_page_to_png",
                   lambda b: b"fake-png-bytes")
        result = classify_pdf_first_page(pdf_bytes, API_KEY, BASE)

    assert result.accepted is True
    assert result.dms_category == "INBOUND_BESCHEID"
    assert result.confidence == 0.93


@respx.mock
def test_low_confidence_returns_unclassified():
    respx.post(f"{BASE}/v1/messages").mock(
        return_value=httpx.Response(200, json=mock_anthropic_response(
            "Bescheid", 0.60, []
        ))
    )
    with pytest.MonkeyPatch().context() as mp:
        mp.setattr("dms_inbound.classify._pdf_first_page_to_png",
                   lambda b: b"fake-png-bytes")
        result = classify_pdf_first_page(b"%PDF-1.4", API_KEY, BASE)

    assert result.accepted is False
    assert result.dms_category == FALLBACK_CATEGORY


def test_parse_response_handles_markdown_fences():
    raw = '```json\n{"category": "Rechnung", "confidence": 0.91, "tags": ["2024"]}\n```'
    r = _parse_response(raw)
    assert r.category_key == "Rechnung"
    assert r.accepted is True


def test_parse_response_handles_invalid_json():
    r = _parse_response("Das ist kein JSON.")
    assert r.dms_category == FALLBACK_CATEGORY
    assert r.confidence == 0.0


def test_parse_response_unknown_category_maps_to_unclassified():
    raw = '{"category": "Kuchenrezept", "confidence": 0.99, "tags": []}'
    r = _parse_response(raw)
    assert r.dms_category == FALLBACK_CATEGORY   # nicht in CATEGORY_MAP
```

---

### Schritt 7 — `requirements.txt` Ergänzung

```
pymupdf>=1.24          # PDF-Rendering (fitz)
```

---

## 5. Migration Tracking

| Schritt | Status | Datum | Notiz |
|---------|--------|-------|-------|
| ADR-148 erstellt | ✅ Done | 2026-03-25 | |
| ADR-148 Review | ⬜ Pending | – | Gate: Phase 2 (ADR-147) Done |
| Migration 0002_inbound_ai_fields | ⬜ Pending | – | Schritt 1 |
| classify.py (Prompt + Parse) | ⬜ Pending | – | Schritt 2 |
| classify_inbound_document Task | ⬜ Pending | – | Schritt 3 |
| Task-Dispatch in import_single_scan | ⬜ Pending | – | Schritt 4 |
| Queue "ai" + Worker in Compose | ⬜ Pending | – | Schritt 5 |
| Tests grün (`pytest tests/test_classify.py`) | ⬜ Pending | – | Schritt 6 |
| 10 Testdokumente: ≥ 80 % korrekt | ⬜ Pending | – | **Done-Kriterium** |

---

## 6. Consequences

### 6.1 Good

- Kein manuelles Einsortieren für Dokumente mit `confidence ≥ 0.85`
- `INBOX_UNCLASSIFIED` als explizite Inbox für unsichere Fälle — kein stiller Fehler
- `ai_category`, `ai_confidence`, `ai_tags` in `InboundScanRecord` sind auditierbar
- `CATEGORY_MAP` ist wartbar ohne Code-Deploy (Config-Datei oder DB-Tabelle in Phase 3+)

### 6.2 Bad

- Kosten pro Dokument ~$0.003–0.006 (Bild-Tokens bei Claude Sonnet)
- `pymupdf` erhöht Image-Größe um ~8 MB
- Bei sehr schlechten Scans (zu hell, verdreht) kann LLM nicht klassifizieren
  → fällt sicher auf `INBOX_UNCLASSIFIED` zurück

### 6.3 Nicht in Scope

- Automatisches Re-Training des Kategorie-Mappings
- Benutzer-Feedback-Loop ("Falsch klassifiziert" Button in d.velop)
- Volltext-Extraktion und Metadaten-Anreicherung (ADR-151, geplant)

---

## 7. Risks

| Risiko | W'keit | Impact | Mitigation |
|--------|--------|--------|------------|
| LLM klassifiziert Bescheid als Antrag (False Positive) | Mittel | Mittel | Confidence-Schwelle 0.85; Sachbearbeiter prüft `INBOX_UNCLASSIFIED` täglich |
| ANTHROPIC_API_KEY nicht konfiguriert | Niedrig | Hoch | `read_secret()` wirft expliziten Fehler; Task landet in `FAILED`; kein stiller Fehler |
| d.velop PATCH schlägt fehl (Dokument gesperrt) | Niedrig | Niedrig | Kein Retry für PATCH; Record-Felder bleiben gesetzt; Klassifikation nicht verloren |
| pymupdf-Sicherheitslücke in manipulierten PDFs | Niedrig | Hoch | `pip-audit` in CI (ADR-022); nur interne Scanner als Quelle |

---

## 8. Confirmation

1. `pytest tests/test_classify.py -v` — alle Tests grün, kein echter API-Call
2. 10 repräsentative Testdokumente aus Landratsamt: ≥ 8 korrekt klassifiziert (80 %)
3. `confidence < 0.85` → `dms_category = "INBOUND_UNCLASSIFIED"` — nachweisbar in DB
4. `classify_inbound_document` läuft auf Queue `"ai"`, nicht `"dms"` — via `celery inspect`
5. Kein `asyncio.run()` im Task (ADR-Plattformregel)
6. `ANTHROPIC_API_KEY` nur via `read_secret()` — kein Klartext in Settings

---

## 9. More Information

| Referenz | Inhalt |
|----------|--------|
| ADR-149 | Inbound Scan — `InboundScanRecord`, `import_single_scan` Task |
| ADR-147 | dvelop_mcp — Phase-2-Gate; MCP-Tool für Korrekturen durch Cascade |
| ADR-068 | aifw Quality-Level-Routing — MEDIUM entspricht Claude Sonnet |
| ADR-045 | `read_secret("ANTHROPIC_API_KEY")` — Pflicht |
| ADR-150 | Roadmap: Phase 3 von 5 |
| pymupdf Docs | https://pymupdf.readthedocs.io/ |

---

*Erstellt: 2026-03-25 · Autor: Achim Dehnert · Review: ausstehend*
