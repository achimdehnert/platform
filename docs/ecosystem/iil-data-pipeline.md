# iil Data Pipeline — `ingest → enrich → prefill`

> **Status:** Dokumentation (kein Code-Contract). Stand 2026-06-15.
> Verifiziert gegen die echten Paket-APIs (`iil-ingest` 0.1.0, `iil-enrichment` 0.2.0,
> `iil-fieldprefill` 0.2.0). Quelle dieses Dokuments: platform#553.

Drei eigenständige iil-Pakete bilden logisch **eine** Datenpipeline: ein Rohdokument
wird extrahiert (`iil-ingest`), gegen externe Wissensquellen angereichert
(`iil-enrichment`) und das Ergebnis füllt KI-gestützt Formularfelder
(`iil-fieldprefill`). Jedes Paket ist für sich nutzbar und hat **keine harte
Abhängigkeit** zu den anderen — der Konsument (Django-Hub) verdrahtet sie.

```
   PDF / CSV / XLSX / DOCX                  CAS-Nr / Stoffname            Formularfeld-Kontext
            │                                      │                              │
            ▼                                      ▼                              ▼
   ┌─────────────────┐   IngestedDocument  ┌─────────────────┐  EnrichmentResult ┌─────────────────┐
   │   iil-ingest    │ ───── .content ───► │ iil-enrichment  │ ──── .properties ►│ iil-fieldprefill│
   │  (ADR-170)      │      .text          │   (ADR-169)     │                   │                 │
   │ IngestPipeline  │                     │ EnrichmentReg.  │                   │  prefill_field  │
   └─────────────────┘                     └─────────────────┘                   └─────────────────┘
        Extraktion                          Anreicherung                          Feld-Befüllung
                                                                                        │
                                                                                        ▼
                                                                                  PrefillResult
                                                                                  → Django-Form
```

> ⚠️ **Wichtig — keine geteilten Typen (Stand 2026-06-15):** `IngestedDocument`,
> `EnrichmentResult` und `PrefillResult` sind **disjunkt**. Es gibt heute **keinen
> automatischen Typ-Fluss** zwischen den Paketen; jeder Pfeil oben ist eine vom
> Konsumenten geschriebene Brücke (z. B. CAS-Nummer aus `IngestedDocument.content.text`
> extrahieren, an `enrich()` geben). Die Vereinheitlichung der Schnittstellen-Schemata
> ist **Folgearbeit** (siehe [ADR-243 — Shared Runtime Core](../adr/ADR-243-shared-runtime-core-iil-corefw.md),
> platform PR #551), nicht Stand dieser Pakete.

## Die drei Stufen

### 1. `iil-ingest` — Extraktion (ADR-170)

Erkennt MIME-Typ, extrahiert Text/Tabellen, klassifiziert das Dokument gegen Profile.

```python
from ingest import IngestPipeline, IngestedDocument
from ingest.extractors import PdfExtractor  # weitere: Csv/Excel/Docx/Ocr

pipeline = IngestPipeline(extractors=[PdfExtractor()])
doc: IngestedDocument = pipeline.run(data=pdf_bytes, filename="sds.pdf")

doc.content.text      # extrahierter Volltext (str)
doc.content.tables    # list[list[list[str]]]
doc.doc_type          # Klassifikation (str), z. B. "UNKNOWN" ohne Classifier
doc.confidence        # "HIGH" | "MEDIUM" | "LOW" | "UNKNOWN"
```

**Output-Typ** `IngestedDocument`: `source_name`, `content: ExtractedContent`,
`doc_type`, `confidence`, `score`, `matched_profiles`, `extra`.
`ExtractedContent`: `raw_bytes`, `text`, `tables`, `metadata`, `mime_type`,
`page_count`, `extraction_errors`.

### 2. `iil-enrichment` — Anreicherung (ADR-169)

Schlägt einen **natural key** (z. B. CAS-Nummer) gegen Provider (GESTIS, PubChem)
nach und liefert strukturierte, typisierte Properties.

```python
from enrichment import EnrichmentRegistry, EnrichmentResult, default_registry

registry: EnrichmentRegistry = default_registry()
# domain ∈ {"substance", "sds"} (GESTIS); enrich() = alle Provider, enrich_merged() = zusammengeführt
result: EnrichmentResult = registry.enrich_merged(domain="sds", natural_key="67-56-1")

result.source                 # "GESTIS" (komma-separiert nach Merge)
result.confidence             # 0.0–1.0
result.properties             # dict[str, PropertyValue]
result.properties["flash_point"].value  # z. B. 11.0
result.properties["flash_point"].unit   # "°C"
```

**Output-Typ** `EnrichmentResult` (frozen): `source`, `confidence`,
`properties: dict[str, PropertyValue]`, `raw_sections`, `natural_key`, `enriched_at`.
`PropertyValue` (frozen): `value`, `unit`, `section`, `value_type`, `note` — mit
`.to_dict()` für JSONB-Speicherung.

### 3. `iil-fieldprefill` — Feld-Befüllung

Orchestriert Retriever-Kontext → Prompt-Bau → `aifw`-LLM-Call und liefert den
generierten Feldinhalt.

```python
from fieldprefill import prefill_field, PrefillResult

res: PrefillResult = prefill_field(
    field_key="lagerklasse",
    prompt="Bestimme die TRGS-510-Lagerklasse aus dem Sicherheitsdatenblatt.",
    action_code="risk.sds.fieldprefill",
    extracted_texts=[doc.content.text],          # aus Stufe 1
    context={"flash_point": "11 °C", "cas": "67-56-1"},  # aus Stufe 2
    response_format="text",
)

res.content        # generierter Feldinhalt (str)
res.success        # bool: content vorhanden und kein error
res.as_dict()      # JSON-Inhalt geparst (bei response_format="json")
```

**Output-Typ** `PrefillResult` (Pydantic v2, frozen): `content`, `tokens_used`,
`model`, `latency_ms`, `field_key`, `cached`, `error`. Public außerdem:
`prefill_fields` (mehrere Felder), `aprefill_field` (async).

## End-to-End-Beispiel: SDS → Lagerklasse-Vorschlag

Realistischer Fluss, wie ihn `risk-hub` fährt (PDF-Sicherheitsdatenblatt → befülltes
Django-Formularfeld). Die **Brücken** zwischen den Stufen sind hervorgehoben.

```python
import re
from ingest import IngestPipeline
from ingest.extractors import PdfExtractor
from enrichment import default_registry
from fieldprefill import prefill_field

# --- Stufe 1: Extraktion ---
doc = IngestPipeline(extractors=[PdfExtractor()]).run(data=pdf_bytes, filename="methanol-sds.pdf")
sds_text = doc.content.text

# --- Brücke 1→2: natural key (CAS) aus dem Volltext ziehen ---
cas_match = re.search(r"\b\d{1,7}-\d{2}-\d\b", sds_text)
cas = cas_match.group(0) if cas_match else ""

# --- Stufe 2: Anreicherung ---
enriched = default_registry().enrich_merged(domain="sds", natural_key=cas)

# --- Brücke 2→3: Properties in Prefill-Kontext übersetzen ---
context = {k: f"{v.value} {v.unit}".strip() for k, v in enriched.properties.items()}

# --- Stufe 3: Feld-Befüllung ---
result = prefill_field(
    field_key="lagerklasse",
    prompt="Leite die TRGS-510-Lagerklasse aus SDS-Volltext und Stoffdaten ab.",
    action_code="risk.sds.fieldprefill",
    extracted_texts=[sds_text],
    context=context,
)

if result.success:
    form.initial["lagerklasse"] = result.content
```

> Jeder Import oben existiert in den veröffentlichten Paketen (verifiziert 2026-06-15
> gegen `ingest/__init__.py`, `enrichment/__init__.py`, `fieldprefill/__init__.py`).

## Schnittstellen-Contracts & Semver

| Übergang | Was wandert | Form | Wer baut die Brücke |
|---|---|---|---|
| ingest → enrich | natural key (CAS/Stoffname) | `str` (vom Konsumenten aus `content.text` extrahiert) | Konsument |
| enrich → prefill | Stoffdaten | `dict[str, PropertyValue]` → flacher `context: dict[str,str]` + `extracted_texts` | Konsument |
| prefill → App | Feldinhalt | `PrefillResult.content` → Django `form.initial[...]` | Konsument |

- **Semver-Erwartung:** Alle drei Pakete folgen SemVer. Die **Output-Dataclasses**
  (`IngestedDocument`, `EnrichmentResult`, `PrefillResult`) sind der öffentliche
  Vertrag — Feld-Entfernung/Umbenennung = **Major**. Neue optionale Felder = Minor.
- Da die Pakete **keine** gegenseitige Pin haben, koordiniert der Konsument die
  kompatiblen Versionen (heute manuell; künftig zentral via Renovate-Gruppe `iil-*`
  und ggf. `iil-corefw`, ADR-243).

## Konsumenten-Matrix (Stand 2026-06-15, verifiziert via Import-Scan)

| Hub | `iil-ingest` | `iil-enrichment` | `iil-fieldprefill` |
|---|:---:|:---:|:---:|
| **risk-hub** | ✅ | ✅ | ✅ (voller Pfad) |
| ausschreibungs-hub | ✅ | — | — |
| dms-hub | ✅ | — | — |
| travel-beat | — | ✅ | — |
| writing-hub | — | — | ✅ |
| bfagent (eingefroren) | — | ✅ | — |

`risk-hub` ist heute der einzige Konsument der **kompletten** Pipeline.

## Verweise

- [ADR-170 — iil-ingest](../adr/ADR-170-iil-ingest-document-ingestion-package.md) · [ADR-169 — Enrichment Agent Pattern](../adr/ADR-169-enrichment-agent-pattern.md)
- [ADR-243 — Shared Runtime Core (iil-corefw)](../adr/ADR-243-shared-runtime-core-iil-corefw.md) (geplante Schema-Vereinheitlichung)
- Paket-READMEs: `iil-ingest`, `iil-enrichment`, `iil-fieldprefill` (Abschnitt „Ecosystem")

> `iil-fieldprefill` hat (Stand 2026-06-15) keinen dedizierten platform-ADR; die
> Paket-interne `ADR-107`-Referenz im Quellcode ist eine Fehlreferenz (ADR-107
> behandelt das Agent-Team, nicht Field-Prefill).
