# ADR-145 Review: Knowledge Management — Cascade ↔ Outline Anti-Knowledge-Drain

**Reviewer:** Principal IT-Architekt  
**Datum:** 2026-03-14  
**Status des ADR:** proposed  
**Reviewed:** ADR-145-knowledge-management-cascade-outline-outline.md

---

## Executive Summary

Das ADR adressiert ein reales, gut beschriebenes Problem (Knowledge Drain / Session-Amnesie) mit
einer architektonisch sinnvollen Entscheidung (Outline als Knowledge Hub + outline_mcp).
Die konzeptionelle Struktur (Knowledge-Loop, Collections, Session-Workflows) ist solide.

**12 Findings identifiziert: 3 BLOCKER · 3 KRITISCH · 3 HOCH · 3 MEDIUM**

Der Kern-Deliverable (outline_mcp FastMCP Server) ist unvollständig spezifiziert und verletzt
drei Platform-Standards. Ohne Korrekturen ist keine produktionsreife Implementierung möglich.

---

## Review-Tabelle

| # | Befund | Severity | Section | Korrektur |
|---|--------|----------|---------|-----------|
| B1 | **`outline-wiki-api` PyPI — unmaintained** Letzter Commit 2022, keine Py 3.12-Kompatibilität getestet, kein async-Support. `asyncio.to_thread()` als Workaround ist unnötig fragil. Platform-Standard: `httpx.AsyncClient` direkt (bereits im Stack). | 🔴 BLOCKER | 3.2 | Direktes `httpx.AsyncClient` gegen Outline REST-API. Keine Drittbibliothek. |
| B2 | **Webhook Phase 5.8 — keine Authentifizierung** Der Outline-Webhook zum research-hub hat keine Auth-Spezifikation. Jeder mit Netzwerkzugriff kann beliebige Dokumente injecten. ADR-050 definiert HMAC-Signatur als Standard für Hub-zu-Hub-Kommunikation. | 🔴 BLOCKER | 5.8 | HMAC-Signatur (`X-Outline-Signature`) + Secret aus `.env` per `decouple.config()`. |
| B3 | **KnowledgeDocument Model (Phase 5.8) — alle Platform-Standards verletzt** Kein `public_id` UUIDField, kein `tenant_id` BigIntegerField, kein `deleted_at`, kein `UniqueConstraint`. Das ist ein User-Data-Model — alle vier Standards sind nicht verhandelbar. | 🔴 BLOCKER | 5.8 | Vollständiges Django-Modell mit allen Platform-Standards (siehe Implementierungsplan). |
| K1 | **Lifespan Hook fehlt** ADR-044 §3.3: Alle Server mit HTTP-Clients MÜSSEN Lifecycle-Hooks via `@asynccontextmanager lifespan` nutzen. `httpx.AsyncClient` muss in `lifespan()` erstellt und geschlossen werden. | 🟠 KRITISCH | 3.2 | `lifespan`-Hook mit `OutlineClient` als `server.state["client"]`. |
| K2 | **Celery Tasks Phase 5.9 — `asyncio.run()` Gefahr** AI-Enrichment (Summary, Keywords) wird LLM-Calls enthalten. Im Celery-Worker-Kontext (ASGI/WSGI-Mix auf CPX52) ist `asyncio.run()` verboten. Explizit: `asgiref.sync.async_to_sync` verwenden (ADR-062, ADR-079 bestätigen den Standard). | 🟠 KRITISCH | 5.9 | `async_to_sync(enrich_document)(...)` in Celery-Task-Körper. aifw-Calls über sync Wrapper. |
| K3 | **Git-Sync Script Phase 5.10 — kein `set -euo pipefail`** Platform-Standard für alle Shell-Skripte. Fehlt komplett in der Spec. Idempotenz-Strategie (was passiert bei Doppelaufruf?) ebenfalls nicht spezifiziert. | 🟠 KRITISCH | 5.10 | Script-Header + `--no-clobber`-Flag für idempotente ADR-Übertragung. |
| H1 | **Outline "Read-Only Mirror" — keine technische Enforcement** Die ADR beschreibt die "ADRs (Read-Only Mirror)" Collection als "nicht editieren", aber Outline hat kein natives Read-Only-Konzept für einzelne Collections. Nutzer können ADRs in Outline ändern — Git-Divergenz. | 🟡 HOCH | 3.3 | ADR-Sync via `documents.update()` überschreibt Outline-Änderungen bei jedem Sync-Lauf (Git als SSOT). Outline-Seite bekommt `[AUTO-GENERATED — Änderungen werden überschrieben]` Header. |
| H2 | **Error Handling in outline_mcp Tools — nicht spezifiziert** Bei Outline-Ausfall, Timeout oder 401 bekommt Cascade eine rohe Python-Exception. ADR-044 §3.4: Keine Exception-Messages oder Stack-Traces an Client. Jedes Tool braucht `try/except` mit sanitisierter Fehlermeldung. | 🟡 HOCH | 3.2 | Jedes Tool: `try/except` → strukturiertes JSON-Error-Objekt. Keine Interna an Cascade. |
| H3 | **Rate Limiting / Retry — nicht spezifiziert** Outline hat undokumentierte Rate Limits. Sequentielle Suchen beim Session-Start können 429 produzieren. Kein Retry-/Backoff-Mechanismus spezifiziert. | 🟡 HOCH | 3.2 | `httpx`-Client mit `tenacity`-Retry: 3 Versuche, exponential backoff 0.5s → 4s. |
| M1 | **Windsurf Workflow-Dateipfade nicht spezifiziert** Phase 5.6/5.7 nennt `/agent-session-start` und `/knowledge-capture` ohne konkreten Pfad. Platform-Standard laut ADR-043: `.windsurf/workflows/<name>.md`. | 🟢 MEDIUM | 3.4, 3.5 | `.windsurf/workflows/agent-session-start.md` (update), `.windsurf/workflows/knowledge-capture.md` (new). |
| M2 | **AI-Enrichment ohne aifw-Integration** Phase 5.9 beschreibt LLM-Calls für Summary/Keywords ohne Erwähnung von `aifw`. Platform-Standard: alle LLM-Calls über `aifw` (ADR-095-097 Quality-Level-Routing). Direkter LLM-Call ist ein Platform-Standard-Verstoß. | 🟢 MEDIUM | 5.9 | `aifw.generate()` mit `quality_level=QualityLevel.MEDIUM` für Enrichment-Tasks. |
| M3 | **`list_recent` fehlt `offset`-Parameter** Ohne Pagination ist das Tool bei >10 Dokumenten unbrauchbar. `limit` allein reicht nicht. | 🟢 MEDIUM | 3.2 | `offset: int = 0` Parameter ergänzen. Outline API unterstützt `offset` nativ. |

---

## Zusammenfassung nach Severity

| Severity | Anzahl | Sofort-Aktion |
|----------|--------|--------------|
| 🔴 BLOCKER | 3 | Muss vor Phase-5.4-Start korrigiert sein |
| 🟠 KRITISCH | 3 | Muss vor Phase-5.8-Start korrigiert sein |
| 🟡 HOCH | 3 | In Phase 5.4 mitimplementieren |
| 🟢 MEDIUM | 3 | Kann in Phase 5.4–5.7 nachgezogen werden |

---

## Alternative: Direkte Git-Integration statt Outline

**Beschreibung:** Statt Outline als externen Knowledge Store nutzen — strukturierte Markdown-Dateien
direkt in `platform/docs/knowledge/` (Git). MCP-Server durchsucht Git-Repo via grep/ripgrep +
optionale pgvector-Embeddings in research-hub.

| Kriterium | Outline-Approach (ADR) | Git-only Approach |
|-----------|----------------------|-------------------|
| **Kein Extra-Dependency** | ❌ Outline als zusätzlicher Service | ✅ Nur Git (bereits vorhanden) |
| **Rich Editor** | ✅ Browser-Editor | ❌ Nur IDE / raw Markdown |
| **OIDC-Auth** | ✅ (ADR-142) | N/A |
| **Team-Sharing** | ✅ | ✅ (via Git) |
| **Versionshistorie** | ✅ Outline-intern | ✅ Git-nativ (besser) |
| **Semantische Suche** | ✅ AI-Keywords | ⚠️ Erfordert eigene Embedding-Pipeline |
| **Single Source of Truth** | ⚠️ Outline + Git = 2 SSOTs | ✅ Git = einziger SSOT |
| **Implementierungsaufwand** | MITTEL (outline_mcp + Sync) | NIEDRIG (nur MCP-Server) |

**Empfehlung:** Outline-Approach ist die richtige Entscheidung, weil der Browser-Editor die
kritische Hürde "Disziplin für Session-Ende-Ritual" senkt. Der Nachteil (zwei SSOTs) wird durch
die klare Abgrenzung (ADRs final in Git, alles andere in Outline) beherrschbar.
**Git-only ist ein valider Fallback** wenn Outline-Betrieb zu aufwendig wird.

---

## Implementierungsplan (korrigiert)

### Phase 5.1–5.3: Unchanged (30 min + 1h + 15 min)
Collections in Outline anlegen, erste Runbooks manuell schreiben, API-Token erstellen.

### Phase 5.4: outline_mcp Server (3h → 4h durch Korrekturen)

**Dateipfade:**

```
mcp-hub/
└── outline_mcp/
    ├── src/
    │   └── outline_mcp/
    │       ├── __init__.py         # __version__ = "0.1.0"
    │       ├── __main__.py         # python -m outline_mcp → mcp.run()
    │       ├── server.py           # FastMCP instance + @mcp.tool() + lifespan
    │       ├── settings.py         # pydantic-settings, env-basiert
    │       ├── models.py           # Pydantic I/O-Modelle
    │       └── client.py           # httpx.AsyncClient gegen Outline REST API
    ├── tests/
    │   ├── conftest.py
    │   └── test_tools.py
    └── pyproject.toml
```

### Phase 5.5: Windsurf-Registrierung (1h)
`.windsurf/mcp.json` Update + Integration-Test aller 6 Tools.

### Phase 5.6–5.7: Workflow-Dateien (30 min + 30 min)
`.windsurf/workflows/agent-session-start.md` + `.windsurf/workflows/knowledge-capture.md`

### Phase 5.8: research-hub KnowledgeDocument + Webhook (3h)

**Dateipfade:**

```
research-hub/
└── apps/
    └── knowledge/
        ├── __init__.py
        ├── apps.py
        ├── models.py               # KnowledgeDocument mit allen Platform-Standards
        ├── services.py             # Service-Layer (keine Business-Logik in Views)
        ├── views.py                # Webhook-Endpoint mit HMAC-Auth
        ├── urls.py
        └── migrations/
            └── 0001_initial.py
```

### Phase 5.9: Celery Enrichment (2h)

```
research-hub/
└── apps/
    └── knowledge/
        └── tasks.py                # async_to_sync + aifw für LLM-Calls
```

### Phase 5.10: ADR-Git-Sync (2h)

```
platform/
└── scripts/
    └── sync_adrs_to_outline.sh     # set -euo pipefail, idempotent
```

---

*Review generiert: 2026-03-14 | Nächste Aktion: B1, B2, B3 in Phase 5.4 adressieren vor Implementierungsstart*
