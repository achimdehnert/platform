---
status: "proposed"
date: 2026-03-14
decision-makers: [Achim Dehnert]
consulted: []
informed: []
supersedes: []
amends: ["ADR-143-knowledge-hub-outline-integration.md"]
related: ["ADR-143-knowledge-hub-outline-integration.md", "ADR-142-unified-identity-authentik-platform-idp.md", "ADR-132-ai-context-defense-in-depth.md", "ADR-114-discord-ide-like-communication-gateway.md", "ADR-116-dynamic-model-router.md", "ADR-044-mcp-server-lifecycle.md", "ADR-045-secrets-management.md", "ADR-050-hub-to-hub-webhook-auth.md", "ADR-062-celery-async-patterns.md", "ADR-095-aifw-quality-routing.md"]
implementation_status: partial
implementation_evidence:
  - "Phase 1 (Infra) completed via ADR-143: Docker, DNS, Nginx — 2026-03-13"
  - "Phase 2 (OIDC) completed: authentik SSO login working — 2026-03-14"
  - "Phase 3 (Collections) completed: 6 Collections in Outline angelegt — 2026-03-14"
  - "Phase 4 (Runbooks) completed: 2 Runbooks + 1 Lesson Learned erstellt — 2026-03-14"
  - "Phase 5 (API-Token) completed: platform-mcp Token (scope /api/*.*) — 2026-03-14"
  - "Phase 6 (outline_mcp) completed: packages/outline-mcp/, 6 tools, 7 tests green — 2026-03-14"
  - "Phase 7 (Windsurf) completed: mcp_config.json, live-tested search+get+list — 2026-03-14"
  - "Phase 8 (Workflows) completed: /knowledge-capture + /agent-session-start Step 6 — 2026-03-14"
  - "Phase 9-11 pending: research-hub KnowledgeDocument, Celery Enrichment, Git-Sync"
review_status: "reviewed — 12 findings (3B/3K/3H/3M), all addressed in v2"
---

# ADR-145: Knowledge Management — Cascade ↔ Outline Anti-Knowledge-Drain

> **Scope**: Dieses ADR definiert die **Strategie und Workflows** für Knowledge Management
> mit Cascade und Outline. Die **technische Infrastruktur** (Docker, DNS, OIDC, Compose)
> ist in ADR-143 definiert und bereits deployed.

---

## 1. Kontext & Problemstellung

### 1.1 Das Knowledge-Drain-Problem

AI Coding Assistants (Cascade/Windsurf) generieren pro Session **enormes implizites Wissen**:

| Wissenstyp | Beispiel (aus OIDC-Session 2026-03-14) | Halbwertszeit |
|-------------|----------------------------------------|---------------|
| **Architektur-Entscheidungen** | "authentik braucht Signing Key + Scope Mappings auf jedem Provider" | Wochen |
| **Troubleshooting-Wissen** | "self-signed cert hinter Cloudflare Tunnel → NODE_TLS_REJECT_UNAUTHORIZED=0" | Monate |
| **Deployment-Patterns** | "extra_hosts: host-gateway für Container→Host→Nginx Routing" | Permanent |
| **Anti-Patterns** | "OIDC URIs: KEIN Slug im Pfad (/application/o/authorize/)" | Permanent |

Dieses Wissen existiert aktuell in **vier Silos**:

| Silo | Problem |
|------|---------|
| **Chat-Verläufe** (Windsurf) | Vergänglich, nicht durchsuchbar, Kontext geht verloren |
| **Cascade Memories** | Kurze Snippets (~500 Zeichen), nicht teilbar, kein Strukturwissen |
| **Entwickler-Kopf** | Single Point of Failure, nicht skalierbar, nicht teilbar |
| **ADRs + Code** (Git) | Nur finales Ergebnis, kein Troubleshooting-Wissen |

### 1.2 Konkretes Problem: Session-Amnesie

**Ohne Knowledge Hub:** Session 1 debuggt OIDC (3h) → Session 2 nächste Woche: doc-hub OIDC → gleiches Debugging. Cascade Memory hat nur *"self-signed cert fix"* als 10-Wort-Snippet.

**Mit Knowledge Hub:** Session 2: `search_knowledge("OIDC authentik troubleshooting")` → Runbook → 10 Min statt 3h.

### 1.3 Cascade Memory vs. Outline — Ergänzung, kein Ersatz

| Aspekt | Cascade Memory | Outline |
|--------|---------------|---------|
| **Format** | Kurze Snippets | Vollständige Dokumente |
| **Struktur** | Flach, Tag-basiert | Hierarchisch (Collections) |
| **Teilbar** | Nein | Ja (OIDC-Login) |
| **Versioniert** | Nein | Ja |
| **Best für** | Session-Kontext, Deployment-Facts | Runbooks, Konzepte, Lessons Learned |

---

## 2. Entscheidung

**Outline als Knowledge Hub für langfristiges, strukturiertes Wissen** — ergänzend zu Cascade Memories.

### 2.1 Knowledge-Kategorien und Speicherort

| Kategorie | Speicherort | Trigger |
|-----------|-------------|---------|
| **Session-Kontext** (Variablennamen, aktuelle Aufgabe) | Cascade Memory | Automatisch |
| **Deployment-Facts** (Container, Ports, Domains) | Cascade Memory | Automatisch |
| **Runbooks** (Troubleshooting, Step-by-Step) | **Outline** | Session-Ende |
| **Architektur-Konzepte** (Designs, Evaluationen) | **Outline** | Beim Konzipieren |
| **Lessons Learned** (Anti-Patterns, Stolperfallen) | **Outline** | Session-Ende |
| **ADR-Drafts** (in Arbeit) | **Outline** → Git | Manuell |
| **ADRs (final)** | Git | Git-Workflow |
| **Hub-Dokumentation** | **Outline** | Bei Deployment |

### 2.2 Verworfene Alternative: Git-only Knowledge Store

| Kriterium | Outline (gewählt) | Git-only |
|-----------|-------------------|----------|
| **Rich Editor** | ✅ Browser | ❌ Nur IDE |
| **Adoptions-Hürde** | ✅ Niedrig | ❌ Hoch |
| **Single Source of Truth** | ⚠️ 2 SSOTs | ✅ 1 SSOT |
| **Implementierungsaufwand** | Mittel | Niedrig |

**Entscheidung**: Outline — Browser-Editor senkt die Hürde für Session-Ende-Ritual.
**Fallback**: Git-only wenn Outline-Betrieb zu aufwendig wird.

---

## 3. Architektur: Knowledge-Loop

### 3.1 Der Knowledge-Loop

```
  SESSION START                    SESSION ENDE
  ┌───────────────┐               ┌───────────────────┐
  │ 1. Memory laden│               │ 3. Memory update   │
  │ 2. outline_mcp:│               │ 4. outline_mcp:    │
  │    search_     │  → ARBEITEN → │    create_runbook() │
  │    knowledge() │               │    create_concept() │
  └───────────────┘               └────────┬──────────┘
                                           │
                                  ┌────────▼──────────┐
                                  │ ASYNC ENRICHMENT    │
                                  │ Webhook → Celery    │
                                  │ → aifw Summary      │
                                  │ → Keywords + ADR-Link│
                                  └────────────────────┘
```

### 3.2 outline_mcp — MCP Server

Registriert als `outline-knowledge` in `.windsurf/mcp.json`.

| Tool | Beschreibung |
|------|-------------|
| `search_knowledge(query, collection?, limit, offset)` | Volltext-Suche |
| `get_document(document_id)` | Markdown-Inhalt abrufen |
| `create_runbook(title, content, related_adrs?)` | Neues Runbook |
| `update_document(document_id, content)` | Dokument aktualisieren |
| `create_concept(title, content, related_adrs?)` | Neues Konzept |
| `list_recent(collection?, limit, offset)` | Zuletzt geänderte Docs |

**Technische Entscheidungen** (aus Review B1, K1, H2, H3, M3):

| Entscheidung | Begründung |
|-------------|-----------|
| **`httpx.AsyncClient`** statt `outline-wiki-api` | PyPI-Lib unmaintained (2022), kein async, kein Py 3.12 |
| **`@asynccontextmanager lifespan`** | ADR-044 §3.3: HTTP-Client Lifecycle |
| **`tenacity` Retry** (3x, exp. backoff 0.5s→4s) | Outline hat undokumentierte Rate Limits |
| **Sanitized Error Handling** | ADR-044 §3.4: keine Stack-Traces an Client |
| **`pydantic-settings`** für Config | Env-basiert, `OUTLINE_MCP_` Prefix |

**Dateipfade:**
```
mcp-hub/outline_mcp/src/outline_mcp/
  ├── server.py     # FastMCP + lifespan + @mcp.tool()
  ├── client.py     # httpx.AsyncClient + tenacity retry
  ├── settings.py   # pydantic-settings
  └── models.py     # Pydantic I/O-Modelle
```

### 3.3 Collections-Struktur

```
📁 Runbooks                         — Troubleshooting, Step-by-Step
📁 Architektur-Konzepte             — Designs, Evaluationen
📁 Lessons Learned                  — Anti-Patterns, Stolperfallen
📁 ADR-Drafts                       — In-Progress ADRs vor Git-Commit
📁 Hub-Dokumentation                — Pro Hub: Setup, API, Config
    ├── 📁 risk-hub / travel-beat / coach-hub / ...
📁 ADRs (Read-Only Mirror)          — Sync aus Git, AUTO-GENERATED Header
```

> **Read-Only Enforcement (H1)**: Outline hat kein natives Read-Only-Konzept.
> Stattdessen: `sync_adrs_to_outline.sh` überschreibt bei jedem Sync-Lauf.
> Jedes ADR-Dokument erhält den Header:
> `<!-- AUTO-GENERATED — Änderungen werden beim nächsten Sync überschrieben. -->`

### 3.4 Workflows

| Workflow | Dateipfad | Zweck |
|----------|-----------|-------|
| `/agent-session-start` (update) | `.windsurf/workflows/agent-session-start.md` | Schritt 5: Knowledge-Lookup |
| `/knowledge-capture` (neu) | `.windsurf/workflows/knowledge-capture.md` | Session-Ende: Runbook/Concept erstellen |

---

## 4. research-hub Integration

### 4.1 KnowledgeDocument Model

**Alle Platform-Standards** (B3): `BigAutoField PK`, `public_id`, `tenant_id`, `deleted_at`, `UniqueConstraint`.

| Feld-Gruppe | Felder | Hinweis |
|-------------|--------|---------|
| **Platform-Standards** | `public_id` (UUID), `tenant_id` (BigInt, immer 1) | Nicht verhandelbar |
| **Outline-Referenz** | `outline_document_id`, `outline_collection_id`, `title`, `outline_url` | |
| **Kategorisierung** | `status` (draft/active/archived), `doc_type` (7 Typen inkl. runbook, lesson) | TextChoices |
| **ADR-Verknüpfung** | `related_adr_numbers` (ArrayField), `related_hubs` (ArrayField) | DB-001: kein JSONField |
| **AI-Enrichment** | `ai_summary`, `ai_keywords` (JSONField), `ai_enriched_at` | |
| **Sync-State** | `outline_updated_at`, `last_synced_at`, `deleted_at` | Soft-Delete |

**Dateipfade:**
```
research-hub/apps/knowledge/
  ├── models.py      # KnowledgeDocument
  ├── services.py    # Service-Layer (ADR-041)
  ├── views.py       # Webhook mit HMAC-Auth (ADR-050)
  ├── tasks.py       # Celery: sync + enrichment
  └── urls.py
```

### 4.2 Webhook: Outline → research-hub

- **HMAC-SHA256** Signatur-Verifikation (B2, ADR-050)
- Secret via `decouple.config("OUTLINE_WEBHOOK_SECRET")`
- Events: `documents.create`, `documents.update`, `documents.delete`
- Async: `sync_outline_document_task.delay(doc_id)` — nicht blockierend

### 4.3 Celery: Sync + AI-Enrichment

| Entscheidung | Begründung |
|-------------|-----------|
| **`async_to_sync`** statt `asyncio.run()` | K2: ADR-062, Celery-Worker-Kontext |
| **`aifw.generate(quality_level=QualityLevel.MEDIUM)`** | M2: ADR-095, kein direkter LLM-Call |
| **Summary + Keywords als separate Prompts** | Fokussierte Ergebnisse, unabhängig retry-bar |
| **Staleness-Check** (24h) | Re-Enrichment nur wenn veraltet |

### 4.4 ADR-Git-Sync

Script: `platform/scripts/sync_adrs_to_outline.sh` (K3, bereits implementiert)

- `set -euo pipefail` (Platform-Standard)
- `--dry-run` und `--adr ADR-XXX` Flags
- Idempotent: `documents.search` → vorhanden? `update` : `create`
- Exit-Codes: 0=ok, 2=missing env, 3=missing tool, 4=not found, 5=errors

---

## 5. Abgrenzung: Was NICHT in Outline gehört

| Was | Wo stattdessen |
|-----|----------------|
| **Finalisierte ADRs** | Git (`platform/docs/adr/`) |
| **Code-Snippets** | Git Repos |
| **Secrets/Credentials** | `.env` (ADR-045) |
| **Temporäre Session-Notizen** | Cascade Memory |
| **Automatisch generierte Logs** | Grafana/Prometheus |

---

## 6. Abgrenzung: ADR-143 vs ADR-145

| Aspekt | ADR-143 | ADR-145 (dieses ADR) |
|--------|---------|---------------------|
| **Fokus** | Technische Infrastruktur | Strategie + Workflows |
| **Inhalt** | Docker, DNS, OIDC, Compose, Nginx | Knowledge-Loop, MCP-Design, Enrichment |
| **Status** | partial (Phase 1-3 done) | partial (Phase 1-2 done via ADR-143) |
| **Ziel** | "Outline läuft" | "Outline wird produktiv genutzt" |

---

## 7. Implementierungsplan

### Abgeschlossene Phasen (via ADR-143)

| Phase | Inhalt | Status |
|-------|--------|--------|
| **1** | Outline Docker Compose, DNS, Nginx, Backup | ✅ Done (2026-03-13) |
| **2** | OIDC via authentik (3 Root Causes gefixt) | ✅ Done (2026-03-14) |

### Offene Phasen

| Phase | Inhalt | Aufwand | Abhängigkeit |
|-------|--------|---------|-------------|
| **3** | Collections-Struktur in Outline anlegen | 30 min | Phase 2 ✅ |
| **4** | Erste Runbooks manuell erstellen (OIDC, RLS, Tunnel) | 1h | Phase 3 |
| **5** | Outline API-Token erstellen | 15 min | Phase 3 |
| **6** | outline_mcp FastMCP Server (httpx, lifespan, retry) | **4h** | Phase 5 |
| **7** | outline_mcp in Windsurf registrieren + testen | 1h | Phase 6 |
| **8** | Workflow-Dateien (session-start update + knowledge-capture) | 1h | Phase 7 |
| **9** | research-hub: KnowledgeDocument + HMAC-Webhook | 3h | Phase 3 |
| **10** | Celery: AI-Enrichment via aifw | 2h | Phase 9 |
| **11** | ADR-Git-Sync deployen + testen | 1h | Phase 9 |

**Gesamt: ~15h** verteilt auf 3 Milestones:

| Milestone | Phasen | Ergebnis | Aufwand |
|-----------|--------|----------|---------|
| **Quick Wins** | 3-5 | Collections + erste Runbooks + API-Token | 1h 45min |
| **Cascade-Integration** | 6-8 | outline_mcp aktiv, Knowledge-Loop funktioniert | 6h |
| **Vollautomatisierung** | 9-11 | Webhook-Sync, AI-Enrichment, ADR-Mirror | 6h |

---

## 8. Metriken

| Metrik | Ziel |
|--------|------|
| **Runbooks erstellt** | ≥ 2 pro Woche |
| **Knowledge-Hits** (search mit Treffern) | ≥ 50% Hit-Rate |
| **Wiederholtes Debugging** | 0 nach 4 Wochen |
| **Session-Startup-Zeit** | < 5 Min (mit Kontext) |

---

## 9. Risiken & Gegenmaßnahmen

| Risiko | Gegenmaßnahme |
|--------|---------------|
| **Runbooks veralten** | AI-Enrichment markiert Alter, Review-Reminder nach 90 Tagen |
| **Zu viel Noise** | Quality Gate: nur echte Lessons Learned |
| **Outline-Ausfall** | Cascade Memories als Fallback, tägliches Backup |
| **Adoption scheitert** | Quick Wins zuerst, Wert beweisen vor Automatisierung |

---

## 10. Konsequenzen

### Positiv

- **Knowledge Drain → Knowledge Loop**: Wissen bleibt erhalten und wächst
- **Cascade wird schlauer**: Zugriff auf Runbooks, Konzepte, Lessons Learned
- **Team-ready**: Wissen ist teilbar (OIDC-Login)
- **ADR-132 gelöst**: AI Context Amnesia adressiert

### Negativ

- **Disziplin nötig**: Session-Ende-Ritual muss konsequent durchgeführt werden
- **Pflege-Aufwand**: Runbooks müssen aktuell gehalten werden
- **Zusätzliches Tool**: Outline neben Git, Discord, Grafana

---

## 11. Review-Findings Tracker

| # | Finding | Severity | Adressiert in |
|---|---------|----------|---------------|
| B1 | `outline-wiki-api` → `httpx.AsyncClient` | 🔴 BLOCKER | §3.2 |
| B2 | Webhook HMAC-SHA256 Auth | 🔴 BLOCKER | §4.2 |
| B3 | KnowledgeDocument Platform-Standards | 🔴 BLOCKER | §4.1 |
| K1 | Lifespan-Hook httpx.AsyncClient | 🟠 KRITISCH | §3.2 |
| K2 | Celery `async_to_sync` | 🟠 KRITISCH | §4.3 |
| K3 | Git-Sync `set -euo pipefail` | 🟠 KRITISCH | §4.4 |
| H1 | ADR Mirror Read-Only Enforcement | 🟡 HOCH | §3.3 |
| H2 | Sanitized Error Handling | 🟡 HOCH | §3.2 |
| H3 | Rate Limiting + Retry | 🟡 HOCH | §3.2 |
| M1 | Workflow-Dateipfade | 🟢 MEDIUM | §3.4 |
| M2 | AI-Enrichment via aifw | 🟢 MEDIUM | §4.3 |
| M3 | `list_recent` offset | 🟢 MEDIUM | §3.2 |

---

## 12. Referenzen

- ADR-143: Knowledge-Hub — Outline Wiki (technische Infrastruktur)
- ADR-142: Unified Identity — authentik als Platform IdP
- ADR-132: AI Context Defense-in-Depth
- ADR-044: MCP Server Lifecycle Hooks
- ADR-045: Secrets Management · ADR-050: Webhook Auth · ADR-062: Celery Patterns · ADR-095: aifw Routing
- `docs/guides/oidc-authentik-integration.md` — OIDC Pattern Guide
- `docs/adr/inputs/dms/konzept-outline-research-hub.md` — Ursprungs-Konzept (enthält vollständigen Code)
- `platform/scripts/sync_adrs_to_outline.sh` — Git-Sync Script
