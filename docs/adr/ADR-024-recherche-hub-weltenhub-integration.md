---
status: proposed
date: 2026-02-21
decision-makers: Achim Dehnert
---

# ADR-024: Location-Recherche als Weltenhub-Modul

| Metadata    | Value                                                              |
|-------------|---------------------------------------------------------------------|
| **Status**  | Proposed (v2 — überarbeitet nach Code-Review 2026-02-11)           |
| **Date**    | 2025-06-12 (v2: 2026-02-11)                                       |
| **Author**  | Cascade AI / achimdehnert                                          |
| **Scope**   | weltenhub (primär), travel-beat (Consumer)                         |
| **Related** | ADR-025-tb (3-Phase Story), ADR-026-tb (Enrichment v2)            |

---

## 1. Executive Summary

Weltenhub-Locations benötigen tiefe, faktenbasierte Informationen (Geschichte,
Kultur, Atmosphäre, Insider-Tipps) für authentische Story-Generierung.
Die **Location-Recherche** wird als **Weltenhub-Modul** (`apps/location_research/`)
implementiert — eine Erweiterung des bestehenden Enrichment-Systems.

**Kernentscheidungen:**

1. **Weltenhub** ist Owner der Location-Daten UND der Recherche-Logik
2. Recherche nutzt die bestehende **Enrichment-Infrastruktur** (LLM-Client,
   Audit-Log, DB-driven Actions, Tenant-Isolation)
3. **Kein Cross-Service-Callback** — direkter DB-Zugriff auf `wh_location`
4. **travel-beat** triggert Recherche via Weltenhub REST API
5. **Exit-Strategie**: Modul kann später als eigenes Repo extrahiert werden

---

## 2. Context

### 2.1 Problem Statement

| Problem | Betroffene Apps | Impact |
|---------|-----------------|--------|
| Orte in Stories sind generisch ("kleines Café") statt real ("Café im Römer") | travel-beat | Geringe Authentizität |
| Enrichment v1 (ADR-020) liefert nur Basis-Fakten (Koordinaten, Wetter, Währung) | travel-beat | LLM halluziniert Details |
| Overpass POIs (ADR-026) liefern Namen, aber keine narrativen Beschreibungen | travel-beat | POIs ohne Story-Kontext |
| Weltenhub-Locations haben keine tiefen Beschreibungen | weltenhub | Keine Wiederverwendung |
| Keine zentrale Stelle für Orts-Wissen | alle | Jede App recherchiert selbst |

### 2.2 Bestehende Infrastruktur (verifiziert 2026-02-11)

| Komponente | Status | Pfad |
|-----------|--------|------|
| LLM-Client (OpenAI, Anthropic, Gateway) | ✅ vorhanden | `apps/core/services/llm_client.py` |
| Enrichment-Orchestrator | ✅ vorhanden | `apps/enrichment/services.py` |
| DB-driven Actions (`lkp_enrichment_action`) | ✅ vorhanden | `apps/enrichment/models.py` |
| Audit-Log (`wh_enrichment_log`) | ✅ vorhanden | `apps/enrichment/models.py` |
| Tenant-Isolation (`TenantAwareModel`) | ✅ vorhanden | `apps/core/models/tenant.py` |
| UUID-PKs auf allen Models | ✅ vorhanden | `wh_location.id = uuid` |
| REST API (DRF + drf-spectacular) | ✅ vorhanden | `apps/locations/views.py` |
| Redis (Cache) | ✅ im Compose | `docker-compose.prod.yml` |

### 2.3 Anforderungen

| ID | Anforderung | Priorität |
|----|-------------|-----------|
| R-01 | Tiefe Orts-Recherche (Geschichte, Kultur, Atmosphäre, Insider) | CRITICAL |
| R-02 | Recherche-Ergebnisse auf `wh_location` persistent | CRITICAL |
| R-03 | travel-beat kann Recherche via REST API triggern | HIGH |
| R-04 | Reisetyp-spezifische Recherche (Abenteuer, Kultur, Stadt, Wellness) | HIGH |
| R-05 | Caching: gleiche Location nicht doppelt recherchieren | HIGH |
| R-06 | Tenant-Isolation: Recherche-Daten gehören zum Tenant | HIGH |
| R-07 | LLM-basierte Recherche mit Quellenangaben | MEDIUM |
| R-08 | Batch-Fähigkeit: alle Locations einer Reise auf einmal | MEDIUM |

---

## 3. Entscheidungen

### 3.1 E1: Recherche als Weltenhub-Modul (nicht bfagent)

**Entscheidung:** Die Location-Recherche wird als `apps/location_research/`
innerhalb von **weltenhub** implementiert.

**Begründung (verifiziert gegen Codebase):**

- Weltenhub hat LLM-Client (`apps/core/services/llm_client.py`:
  `LlmRequest`, `generate_text` — Provider-agnostisch)
- Weltenhub hat Enrichment-Orchestrator mit Audit-Log und Tenant-Isolation
- Weltenhub hat direkten DB-Zugriff auf `wh_location` — kein Callback nötig
- Weltenhub hat UUID-PKs — kein Typ-Mismatch
- Weltenhub hat Redis im Compose — Celery-Broker ready

**v1 (verworfen): bfagent als Host** — Code-Review (2026-02-11) ergab:

- bfagent hat keinen LLM-Client (kein `LLMRouter`, kein `ClaudeClient`)
- bfagent hat kein Celery/Redis
- bfagent `apps/research/` ist nicht in `INSTALLED_APPS`, hat keine Tenant-Isolation
- Cross-Service-Callback wäre nötig (Auth-Problem, Retry-Komplexität)

**Alternative (verworfen): Eigenes Repo** — ~5-7 Tage Boilerplate, Callback-Komplexität,
kein direkter DB-Zugriff, zusätzlicher Container auf dem Hetzner-VM.

**Exit-Strategie:** `apps/location_research/` kann jederzeit als eigenes Repo
extrahiert werden, sobald andere Apps (pptx-hub, bfagent) den Dienst benötigen.

### 3.2 E2: Location-Model-Erweiterung

Neue Felder auf `wh_location`:

```python
# weltenhub: apps/locations/models.py — Erweiterung
class Location(TenantAwareModel):
    # ... bestehende Felder (name, description, atmosphere, ...) ...

    # NEU: Recherche-Daten
    research_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Deep research data (validated by ResearchData schema)"
    )
    research_status = models.ForeignKey(
        "lookups.ResearchStatus",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="locations",
        help_text="Current research state"
    )
    researched_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When research was last completed"
    )
```

**Lookup-Table** (konsistent mit `lkp_location_type`, `lkp_scene_type` etc.):

```sql
-- lkp_research_status (via BaseLookup)
INSERT INTO lkp_research_status (code, name, "order", is_active) VALUES
  ('none',    'Nicht recherchiert', 10, true),
  ('pending', 'Recherche läuft',   20, true),
  ('basic',   'Basis-Recherche',   30, true),
  ('deep',    'Tiefe Recherche',   40, true),
  ('failed',  'Fehlgeschlagen',    50, true);
```

**API-Erweiterung** auf bestehendem `LocationViewSet`:

```text
GET  /api/v1/locations/{uuid}/research/        → Recherche-Daten abrufen
POST /api/v1/locations/{uuid}/research/        → Recherche triggern
GET  /api/v1/locations/{uuid}/research/status/  → Recherche-Status
POST /api/v1/locations/batch-research/          → Batch (alle Locations einer Reise)
```

### 3.3 E3: research_data Schema (Pydantic-Vertrag)

Shared Schema als Pydantic-Model für Validierung beim Schreiben und Lesen:

```python
# weltenhub: apps/location_research/schemas.py
from pydantic import BaseModel, ConfigDict, Field


class POIEnriched(BaseModel):
    """Ein narrativ angereicherter Point of Interest."""
    model_config = ConfigDict(frozen=True)

    name: str = Field(description="POI-Name (z.B. 'Römerberg')")
    narrative: str = Field(description="Narrative Beschreibung")
    poi_type: str = Field(description="landmark, restaurant, park, etc.")


class ResearchData(BaseModel):
    """Schema für wh_location.research_data JSONField."""
    model_config = ConfigDict(frozen=True)

    history: str = Field(default="", description="2-3 Sätze Geschichte")
    atmosphere: str = Field(default="", description="Sensorisch: Gerüche, Geräusche")
    insider_tips: list[str] = Field(default_factory=list)
    pois_enriched: list[POIEnriched] = Field(default_factory=list)
    cuisine: list[str] = Field(default_factory=list)
    cultural_notes: str = Field(default="")
    seasonal_info: dict[str, str] = Field(default_factory=dict)
    trip_type_highlights: dict[str, list[str]] = Field(default_factory=dict)
    neighborhoods: list[dict[str, str]] = Field(default_factory=list)
    sensory_details: dict[str, list[str]] = Field(default_factory=dict)
    research_version: int = Field(default=1, description="Schema-Version")
```

**Validierung:** Beim Schreiben via `ResearchData.model_validate(data)`,
beim Lesen defensiv via `ResearchData.model_validate(location.research_data)`.

### 3.4 E4: Datenfluss — Kein Callback, direkter DB-Zugriff

```text
┌──────────────┐           ┌──────────────────────────────────┐
│  travel-beat  │           │           weltenhub               │
│  (DriftTales) │           │                                  │
│               │           │  ┌──────────┐ ┌───────────────┐ │
│ Stop-Import   │──(1)─────►│  │ Location │ │ location_     │ │
│ oder Story-   │   REST    │  │ REST API │ │ research/     │ │
│ Generierung   │           │  │          │►│               │ │
│               │           │  │ POST     │ │ Researcher    │ │
│               │           │  │/research/│ │ (LLM-Client)  │ │
│               │           │  │          │◄│               │ │
│               │◄──(2)─────│  │ research │ │ Direkt auf DB │ │
│               │   REST    │  │ _data    │ │ schreiben     │ │
│ Story-Prompt  │           │  └──────────┘ └───────────────┘ │
│ mit realen    │           │                                  │
│ Ortsdaten     │           │                                  │
└──────────────┘           └──────────────────────────────────┘

(1) travel-beat → weltenhub: POST /api/v1/locations/{uuid}/research/
    → Weltenhub ruft LocationResearcher intern auf
    → Researcher schreibt research_data direkt auf wh_location
(2) travel-beat ← weltenhub: GET /api/v1/locations/{uuid}/
    → Angereicherte Location-Daten im Story-Kontext
```

**Kein Callback nötig** — der Researcher hat direkten DB-Zugriff auf `wh_location`.

**Trigger-Mechanismen:**

| Trigger | Wer | Wann | Wie |
|---------|-----|------|-----|
| Story-Generierung | travel-beat | Phase 1 (Storyline) | `POST /locations/{uuid}/research/` |
| Manuell | weltenhub UI | User klickt "Recherchieren" | HTMX-Button → View → Researcher |
| Batch | Admin/Cron | Nightly | Management Command: alle `research_status=none` |

### 3.5 E5: Modul-Architektur (`apps/location_research/`)

```text
weltenhub/
├── apps/
│   ├── locations/           # bestehend (Model, API, Serializer)
│   ├── enrichment/          # bestehend (LLM-Orchestrator, Audit-Log)
│   └── location_research/   # NEU
│       ├── __init__.py
│       ├── apps.py
│       ├── schemas.py       # ResearchData Pydantic-Schema (E3)
│       ├── services/
│       │   ├── __init__.py
│       │   ├── researcher.py        # LocationResearcher (Haupt-Service)
│       │   ├── poi_enricher.py      # POI-Narrative-Generierung
│       │   └── country_resolver.py  # Hierarchie → Country-Name
│       ├── views.py         # DRF ViewSet-Actions für /research/
│       ├── urls.py
│       ├── management/
│       │   └── commands/
│       │       └── research_locations.py  # Batch-Command
│       └── tests/
│           ├── test_researcher.py
│           └── test_schemas.py
```

**Kein eigenes Model** — nutzt `wh_location.research_data` + `wh_enrichment_log`.

#### 3.5.1 LocationResearcher Service

```python
# weltenhub: apps/location_research/services/researcher.py
import uuid
from django.utils import timezone
from apps.core.services.llm_client import LlmRequest, generate_text
from apps.enrichment.models import EnrichmentLog
from apps.locations.models import Location
from ..schemas import ResearchData


class LocationResearcher:
    """Recherchiert tiefe Ortsinformationen via LLM.

    Nutzt den bestehenden llm_client (Provider-agnostisch).
    Schreibt direkt auf wh_location.research_data.
    """

    def research(
        self,
        location_id: uuid.UUID,
        trip_types: list[str] | None = None,
        user=None,
    ) -> ResearchData:
        location = Location.all_objects.select_related(
            "location_type", "research_status"
        ).get(id=location_id)

        # Cache-Check
        if (
            location.research_status
            and location.research_status.code == "deep"
        ):
            return ResearchData.model_validate(
                location.research_data
            )

        # Country via Hierarchie auflösen (nicht parent.name!)
        country = self._resolve_country(location)

        # LLM-Recherche
        result = self._call_llm(location.name, country, trip_types)

        # Direkt auf Location schreiben
        location.research_data = result.model_dump()
        location.researched_at = timezone.now()
        # research_status → "deep" (FK lookup)
        from apps.lookups.models import ResearchStatus
        location.research_status = ResearchStatus.objects.get(
            code="deep"
        )
        location.save(update_fields=[
            "research_data", "research_status",
            "researched_at", "updated_at",
        ])

        return result

    def _resolve_country(self, location: Location) -> str:
        """Traversiere Hierarchie bis location_type='country'."""
        parent = location.parent
        while parent:
            if (
                parent.location_type
                and parent.location_type.code == "country"
            ):
                return parent.name
            parent = parent.parent
        return ""
```

#### 3.5.2 LLM-Prompt (als `lkp_enrichment_action` Seed)

```sql
INSERT INTO lkp_enrichment_action
  (code, name, entity_type, system_prompt, user_prompt_template,
   target_fields, max_tokens, temperature, icon, "order", is_active)
VALUES (
  'location_deep_research',
  'Tiefe Orts-Recherche',
  'location',
  'Du bist ein erfahrener Reiseschriftsteller und Kulturexperte.
Antworte NUR als valides JSON.',
  'Recherchiere {name} in {country} für eine Reisegeschichte.
Reisetyp: {trip_types}

JSON-Schema:
{
  "history": "2-3 Sätze zur Geschichte",
  "atmosphere": "Gerüche, Geräusche, Stimmung",
  "insider_tips": ["Tipp 1", "Tipp 2", "Tipp 3"],
  "cuisine": ["Gericht 1", "Gericht 2"],
  "cultural_notes": "Kulturelle Besonderheiten",
  "seasonal_info": {"summer": "...", "winter": "..."},
  "neighborhoods": [{"name": "...", "character": "..."}],
  "sensory_details": {"sounds": [...], "smells": [...], "sights": [...]}
}

WICHTIG: Nur REALE, überprüfbare Informationen.',
  '[{"label": "RESEARCH", "field": "research_data"}]',
  2000, 0.4, 'bi-search', 10, true
);
```

---

## 4. Alternativen

| Alternative | Bewertung | Grund für Ablehnung |
|------------|----------|---------------------|
| **bfagent-Modul (v1)** | Verworfen | Kein LLM-Client, kein Celery, keine Tenant-Isolation (Code-Review F1-F5) |
| Eigenes Repo | Sauber | ~5-7 Tage Boilerplate, Callback-Komplexität, kein direkter DB-Zugriff |
| Recherche direkt in travel-beat | Einfach | Kein Caching über Apps hinweg, keine Wiederverwendung |
| Recherche als MCP-Tool | Leicht | Keine DB, kein Caching, kein Task-Management |
| Externer Service (SaaS) | Professionell | Kosten, Vendor Lock-in, Datenschutz |

---

## 5. Kosten

| Komponente | Kosten pro Location | Kosten für 24 Locations |
|-----------|--------------------|-----------------------|
| Basis-Recherche (LLM, ~2000 Token) | ~$0.03 | ~$0.72 |
| POI-Anreicherung (optional) | ~$0.02 | ~$0.48 |
| Trip-Typ-Recherche (optional) | ~$0.02 | ~$0.48 |
| **Gesamt** | **~$0.07** | **~$1.68** |

**Amortisierung:** Recherche ist einmalig pro Location.
Zweiter Trip nach Frankfurt → $0.00 (Cache via `research_status=deep`).

---

## 6. Risiken

| Risiko | Impact | Mitigation |
|--------|--------|-----------|
| LLM halluziniert Fakten | Hoch | OSM/Overpass-Daten (verifiziert) als Basis, LLM nur für Atmosphäre/Narrative |
| research_data Schema-Drift | Mittel | Pydantic `ResearchData` Schema (E3), `research_version` Pflichtfeld |
| Weltenhub-Worker blockiert durch LLM-Call | Mittel | Celery-Worker (Redis-Broker bereits im Compose), Timeout 60s |
| Hohe LLM-Kosten bei vielen Locations | Niedrig | Cache via `research_status`, Tier-Gating (deep nur bei Bedarf) |
| Country falsch aufgelöst | Niedrig | `_resolve_country()` traversiert Hierarchie (nicht `parent.name`) |

---

## 7. Migration & Rollout

### 7.1 Phase 1: Model + Lookup (0.5 Tage)

- `lkp_research_status` Lookup-Table erstellen (Seed-Migration)
- `research_data` JSONField, `research_status` FK, `researched_at` auf `wh_location`
- Django-Migration generieren + deployen
- **Risiko:** Minimal — 3 neue nullable Spalten, kein Datenverlust

### 7.2 Phase 2: `apps/location_research/` Modul (1.5 Tage)

- Modul-Skeleton: `schemas.py`, `services/researcher.py`, `views.py`
- `LocationResearcher` mit bestehenden `llm_client` integrieren
- `lkp_enrichment_action` Seed: `location_deep_research`
- `country_resolver.py`: Hierarchie-Traversierung
- In `INSTALLED_APPS` registrieren

### 7.3 Phase 3: API + UI (1 Tag)

- DRF ViewSet-Actions: `research`, `research_status` auf `LocationViewSet`
- HTMX-Button "Recherchieren" auf Location-Detail-Page
- Batch-Endpoint: `POST /api/v1/locations/batch-research/`

### 7.4 Phase 4: travel-beat Integration (1 Tag)

- travel-beat Orchestrator: `research_status` prüfen vor Story-Generierung
- travel-beat: `research_data` in Story-Prompt injizieren
- Optional: Celery-Worker für async LLM-Calls ergänzen

### 7.5 Phase 5: Tests (1 Tag)

- `test_schemas.py`: Pydantic-Schema Validierung
- `test_researcher.py`: Mock-LLM, Cache-Check, Country-Resolver
- `test_views.py`: API-Endpoints, Auth, Tenant-Isolation

---

## 8. Abgrenzung

- **ADR-025 (travel-beat)**: 3-Phasen-Pipeline **konsumiert** Recherche-Daten
- **ADR-026 (travel-beat)**: Enrichment v2 **triggert** Recherche via API
- Dieses ADR ändert **nicht** die Story-Generierung (das ist ADR-025)
- Dieses ADR ändert **nicht** die Enrichment-Pipeline (das ist ADR-026)
- Dieses ADR erweitert das `wh_location`-Model und fügt ein neues Weltenhub-Modul hinzu

---

## 9. Umsetzungsreihenfolge

| # | Aufgabe | Repo | Aufwand |
|---|---------|------|---------|
| 1 | `lkp_research_status` Lookup-Table + Seed | weltenhub | 0.25 Tage |
| 2 | `wh_location`: 3 neue Felder + Migration | weltenhub | 0.25 Tage |
| 3 | `apps/location_research/schemas.py` (Pydantic) | weltenhub | 0.25 Tage |
| 4 | `LocationResearcher` Service + `country_resolver` | weltenhub | 1 Tag |
| 5 | DRF ViewSet-Actions + HTMX-Button | weltenhub | 0.5 Tage |
| 6 | `lkp_enrichment_action` Seed: `location_deep_research` | weltenhub | 0.25 Tage |
| 7 | travel-beat: research_data in Story-Prompt | travel-beat | 0.5 Tage |
| 8 | Management Command: `research_locations` (Batch) | weltenhub | 0.25 Tage |
| 9 | Tests (Schema, Researcher, API, Integration) | weltenhub | 1 Tag |

**Geschätzter Gesamtaufwand: ~4.25 Tage** (vs. ~11 Tage in v1)

---

## 10. Review-Befunde (v1 → v2)

Folgende Befunde aus dem Code-Review (2026-02-11) wurden in v2 adressiert:

| # | Befund (v1) | Fix (v2) |
|---|------------|---------|
| F1 | LLMRouter/ClaudeClient existieren nicht in bfagent | Weltenhub hat `llm_client.py` ✅ |
| F2 | Celery/Redis existieren nicht in bfagent | Weltenhub hat Redis im Compose ✅ |
| F3 | UUID vs. int PK-Mismatch | `location_id: uuid.UUID` ✅ |
| F4 | `apps/recherche/` vs. `apps/research/` Naming-Konflikt | Neues Modul: `apps/location_research/` ✅ |
| F5 | Keine Tenant-Isolation in bfagent | `TenantAwareModel` in Weltenhub ✅ |
| F6 | Unauthentifizierter Callback PUT | Kein Callback nötig (direkter DB-Zugriff) ✅ |
| F7 | `parent.name` ≠ Country | `_resolve_country()` traversiert Hierarchie ✅ |
| F8 | research_data ohne Schema-Validierung | Pydantic `ResearchData` Schema (E3) ✅ |
| F9 | CharField statt Lookup-Table | `lkp_research_status` FK ✅ |
| F10 | Synchroner requests.post ohne Error-Handling | Kein HTTP-Call (lokal im selben Prozess) ✅ |
