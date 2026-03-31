---
status: "accepted"
date: 2026-03-31
decision-makers: [Achim Dehnert]
consulted: [Cascade AI]
informed: []
implementation_status: complete
---

# ADR-154: Autonomous Coding Optimization — Information Flow, Error Prevention, Continuous Improvement

## Context and Problem Statement

Cascade (AI Coding Agent) operiert autonom auf 22+ Repos der IIL Platform. Die aktuelle Infrastruktur (MCP-Tools, Knowledge Graph, Memory, Outline, Workflows) wurde organisch gewachsen und weist **systematische Ineffizienzen** auf:

1. **Kalter Session-Start**: Jede Session beginnt ohne Wissen über vorherige Sessions, Fehler oder Entscheidungen
2. **Disconnected Knowledge Stores**: 3 Speicher (Cascade Memory, pgvector, Outline) kennen einander nicht
3. **Post-Mortem statt Prevention**: Architektur-Violations werden erst nach dem Schreiben geprüft
4. **Kein Self-Learning**: Fehler und Korrekturen werden nicht systematisch erfasst
5. **Stale SSOT-Dokumente**: AGENT_HANDOVER.md und CORE_CONTEXT.md driften von repos.json ab
6. **pgvector Memory Store unerreichbar**: `mcp_hub_db` (pgvector:pg16) läuft auf dem Prod-Server (`88.198.191.108:15435`), aber der orchestrator MCP läuft lokal in WSL und versucht `127.0.0.1:15435` — Connection Refused. **Root Cause für leeren Memory Store.**

**Auswirkung**: Vermeidbare Fehler (falsche Ports, fehlende Imports, Rule-Verstöße), Zeitverlust durch wiederholtes Kontext-Laden, keine Verbesserung über Sessions hinweg.

---

## Decision Drivers

* **Fehlerrate senken**: Weniger User-Korrekturen, weniger Rollbacks
* **Time-to-Context reduzieren**: Session-Start von ~5min auf ~30s
* **Knowledge Retention**: Wissen aus Session N muss in Session N+1 verfügbar sein
* **Minimal Overhead**: Optimierungen dürfen den Coding-Flow nicht verlangsamen
* **Bestehende Infrastruktur nutzen**: pgvector, Outline, platform-context MCP existieren bereits

---

## Current State Analysis (5 Dimensions)

### D1: Information Retrieval

| Quelle | Auto-Load | Qualität | Problem |
|--------|-----------|----------|---------|
| Cascade Memories | ✅ | ⚠️ Teils veraltet | Redundante Einträge, keine Versionierung |
| AGENT_HANDOVER.md | ❌ Manuell | ⚠️ Stale | Falsche MCP-Prefixes, fehlende Repos |
| CORE_CONTEXT.md | ❌ Manuell | ❌ Fehlt oft | Nur 2 von 22 Repos haben eins |
| repos.json (KG) | Via MCP | ✅ Aktuell | Keine App-Level-Details (Models, URLs) |
| Outline Wiki | Via MCP | ✅ Gut | Fulltext-only, keine Staleness-Warnung |
| pgvector Memory | Via MCP | ❌ **Leer** | Wird nie beschrieben, nie gelesen |
| GitHub Issues | Via MCP | ✅ Gut | Nur bei explizitem Abruf |

**Lücken:**
- Kein Auto-Detect des aktiven Repos aus Workspace-URI
- Kein "Was hat sich seit letzter Session geändert?"
- Kein Task-Context-Enrichment ("relevante Dateien für Feature X")

### D2: Information Processing

| Tool | Methode | Limitation |
|------|---------|-----------|
| `check_violations` | String-Match | Kein AST, False Positives in Strings/Comments |
| `get_context_for_task` | Repo-Facts + Rules | Topic-Filter = naive Substring-Suche |
| `get_banned_patterns` | Flat List | Kein Fix-Vorschlag, keine Severity pro Pattern |

**Lücken:**
- Keine Pre-Edit-Prüfung (Violations erst nach dem Schreiben)
- Keine Cross-File-Analyse (Service-Layer-Existenz nicht prüfbar)
- Kein Fix-Template bei Violation-Befund

### D3: Information Storage

```
3 DISCONNECTED STORES:

┌─────────────────┐     ┌──────────────┐     ┌─────────────────┐
│ Cascade Memory   │     │ pgvector     │     │ Outline Wiki    │
│ (Windsurf)       │     │ (orchestrator)│     │ (knowledge.iil) │
│                  │     │              │     │                 │
│ ✅ Auto-loaded   │     │ ❌ EMPTY      │     │ ✅ Searchable    │
│ ⚠️ Unstructured  │     │ ✅ Semantic   │     │ ⚠️ Manual only   │
│ ❌ No cross-ref  │     │ ✅ Typed      │     │ ✅ Collections   │
│ ❌ ~500 chars    │     │ ✅ Decay-aware│     │ ❌ No auto-write │
└─────────────────┘     └──────────────┘     └─────────────────┘
```

**Lücken:**
- pgvector hat 7 Entry-Types (`error_pattern`, `lesson_learned`, `decision`, ...) — alle leer
- Kein Write-Through zwischen Stores
- Kein automatisches Error-Pattern-Logging

### D4: Error Prevention

| Fehlertyp | Beispiel | Root Cause |
|-----------|---------|-----------|
| Stale Facts | Port 8096 statt 8099 | AGENT_HANDOVER nicht aktuell |
| Falsche MCP-Prefixes | `mcp14_` vs `mcp5_` | Prefixes ändern sich, Memory veraltet |
| Duplicate Creation | 13 ADR-Duplikate in Outline | Sync ohne Exact-Match |
| Missing Context | ORM in View | `get_context_for_task` nicht aufgerufen |
| Wrong Assumptions | `apps/` statt `src/` Layout | repos.json hatte falsche Facts |

**Lücken:**
- Keine Preflight-Checklist vor Edits
- Kein automatischer Post-Edit-Test
- Kein Rollback-Mechanismus in Windsurf

### D5: Continuous Improvement

**Status: Kein Feedback-Loop existiert.**

- User-Korrekturen werden nicht systematisch erfasst
- Keine Qualitäts-Metriken (Error-Rate, Retry-Rate, Time-to-Fix)
- `agent_memory_context` (Top-K relevante Memories) existiert, wird nie gefüttert

---

## Considered Options

### Option A: Inkrementelle Workflow-Erweiterungen
Bestehende Workflows (`session-start`, `session-ende`, `agentic-coding`) um Memory-Calls und Pre-Checks erweitern. Kein neuer Code, nur Workflow-Anpassungen.

### Option B: Unified Context API (neues MCP-Tool)
Ein einziger MCP-Call `get_full_context(repo, task_description)` der Repo-Facts + Rules + pgvector Memory + Outline-Treffer + Git-Diff kombiniert zurückgibt. Zentraler Einstiegspunkt.

### Option C: Self-Learning Agent Loop
Vollständiger Feedback-Loop: Fehler → Error-Pattern → Memory → Prevention. Automatische Lesson-Learned-Erfassung, Qualitäts-Metriken, Delta-Detection.

### Option D: Option A + B + C gestaffelt
3-Phasen-Ansatz: Quick Wins (A) → Unified API (B) → Self-Learning (C).

---

## Decision Outcome

**Chosen option: Option D** — gestaffelte Implementierung in 3 Phasen.

Begründung: Quick Wins sofort wirksam, Unified API als strategisches Fundament, Self-Learning als langfristige Vision. Jede Phase ist für sich abgeschlossen und liefert Mehrwert.

---

## Phase 0: Blocker — pgvector Memory Store erreichbar machen (Aufwand: ~30min)

**Status Quo:**
- `mcp_hub_db` (pgvector:pg16) läuft auf **88.198.191.108:15435**
- orchestrator MCP läuft **lokal in WSL** (als Windsurf MCP-Server via stdio)
- `ORCHESTRATOR_MCP_MEMORY_DB_URL` ist **nicht gesetzt** in der WSL-Umgebung
- Resultat: `RuntimeError("ORCHESTRATOR_MCP_MEMORY_DB_URL ist nicht gesetzt.")` → Memory komplett tot

**Fix-Optionen:**

| Option | Aufwand | Sicherheit | Latenz |
|--------|---------|-----------|--------|
| **A: SSH-Tunnel + autossh** (gewählt) | 10min | ✅ Hoch | ~20ms |
| B: Lokale pgvector-Instanz | 30min | ✅ Hoch | <1ms |
| ~~C: Port auf Prod öffnen~~ | ~~5min~~ | ❌ **REJECTED — Security-Risiko** | ~~~20ms~~ |

**Option A: SSH-Tunnel (empfohlen)**
```bash
# 1. autossh für Reconnect-Stabilität:
sudo apt install autossh -y

# 2. systemd user-service für Persistenz:
# → platform/scripts/phase0-setup-memory-tunnel.sh

# 3. Credential via read_secret() (R-01):
# Secret in ~/.secrets/orchestrator_mcp_db_password
# store.py baut DB-URL aus read_secret() zusammen

# 4. Env-File generiert von Setup-Script:
# ~/.config/iil/memory-tunnel.env
export ORCHESTRATOR_MCP_MEMORY_DB_URL="postgresql://orchestrator:<pw>@localhost:15435/orchestrator_mcp"
export ORCHESTRATOR_MCP_MEMORY_EMBEDDING_PROVIDER=openai
```
Vorteile: Keine Infra-Änderung, sichere Verbindung, Prod-Daten direkt nutzbar.

**Option B: Lokale pgvector-Instanz**
```bash
docker run -d --name local_pgvector \
  -e POSTGRES_DB=orchestrator_mcp \
  -e POSTGRES_USER=orchestrator \
  -e POSTGRES_PASSWORD=dev-local \
  -p 15435:5432 pgvector/pgvector:pg16
```
Vorteile: Keine Netzwerk-Abhängigkeit, volle Kontrolle.
Nachteile: Separate Daten, kein Sync mit Prod.

**Entscheidung:** Option A (SSH-Tunnel) — einfachste Lösung, Prod-Daten sofort nutzbar, orchestrator und Discord-Bot teilen sich dieselbe Memory-DB.

---

## Phase 1: Quick Wins (Aufwand: ~3h)

### O-1: pgvector Memory aktivieren

**Problem:** `agent_memory_upsert` / `agent_memory_search` existieren, werden nie genutzt.

**Lösung:** Workflow `session-ende` erweitern:
```
# Am Session-Ende automatisch:
agent_memory_upsert(
    entry_key="session:<date>:<repo>",
    entry_type="context",
    title="Session Summary: <repo> — <task>",
    content="<Was gemacht, Entscheidungen, Fehler, Erkenntnisse>",
    tags=["<repo>", "<task_type>"]
)

# Bei Bug-Fix zusätzlich:
agent_memory_upsert(
    entry_key="error:<symptom-hash>",
    entry_type="error_pattern",
    title="Error: <Symptom>",
    content="Symptom: ...\nRoot Cause: ...\nFix: ...\nPrevention: ...",
    tags=["<repo>", "bugfix"]
)
```

### O-2: AGENT_HANDOVER.md auto-generieren

**Problem:** Manuell gepflegte Handover-Docs driften.

**Lösung:** Script `platform/scripts/generate-agent-handover.sh` das aus repos.json + ports.yaml eine aktuelle AGENT_HANDOVER.md generiert. In `sync-workflows.sh` integrieren.

### O-3: Warm-Start mit pgvector

**Problem:** Jede Session startet kalt.

**Lösung:** `session-start` Workflow erweitern:
```
# Nach Repo-Detect:
agent_memory_context(
    task_description="<User-Aufgabe>",
    top_k=5
)
→ Liefert relevante Memories aus vorherigen Sessions
```

---

## Phase 2: Unified Context API (Aufwand: ~6h)

### O-8: Neues Tool `get_full_context`

**Problem:** 4-5 separate MCP-Calls für vollständigen Kontext.

**Lösung:** Neues Tool in `platform_context_mcp` oder `orchestrator_mcp`:

```python
def get_full_context(repo: str, task_description: str) -> dict:
    """One call to rule them all."""
    return {
        "repo_facts": get_repo_facts(repo),
        "applicable_rules": get_rules_for_repo_and_file(repo, file_type),
        "banned_patterns": get_banned_for_context(file_type),
        "memories": agent_memory_context(task_description, top_k=3),
        "outline_hits": search_knowledge(task_description, limit=3),
        "recent_changes": git_log(repo, count=5),
        "open_issues": list_issues(repo, state="open", per_page=5),
    }
```

**Input:** 2 Parameter (repo, task_description)
**Output:** Vollständiger Kontext in einem Response

### O-7: Fix-Templates in rules.json

**Problem:** Violations sagen nur "banned", nicht "use instead".

**Lösung:** Jede Rule bekommt `fix_template`:
```json
{
    "id": "CFG-001",
    "banned": ["os.environ[", "os.environ.get("],
    "fix_template": "from decouple import config\nvalue = config('KEY')",
    "description": "Use decouple.config() instead of os.environ"
}
```

---

## Phase 3: Self-Learning (Aufwand: ~8h)

### O-5: Error-Pattern-DB

Automatische Erfassung bei jedem Bug-Fix:
- **Symptom** (was ging schief)
- **Root Cause** (warum)
- **Fix** (was geholfen hat)
- **Prevention** (wie vermeiden)

Vor jedem neuen Task: `agent_memory_search(query="<ähnliches Problem>", entry_type="error_pattern")`.

### O-9: Delta-Detection

Beim Session-Start automatisch prüfen:
- Git-Log seit letzter Session (via pgvector timestamp)
- Neue/geschlossene Issues
- Geänderte ADRs oder Workflows
- Rote Tests

### O-10: Korrektur-Feedback-Loop

Wenn User eine Korrektur macht:
1. Cascade erkennt die Korrektur
2. `agent_memory_upsert(entry_type="lesson_learned")`
3. Relevante SSOT (repos.json, Memory) wird aktualisiert
4. Optional: Outline Lesson Learned erstellt

### O-11: Quality Dashboard

Metriken in Grafana (bestehendes Setup):
- Errors pro Session
- User-Korrekturen pro Session
- Retry-Rate (verify_task Fails)
- Time-to-Context (Session-Start bis erstem Edit)
- Violations-Hit-Rate (wie oft werden Rules getriggert)

---

## Implementation Priority Matrix

| ID | Vorschlag | Impact | Aufwand | Phase |
|----|----------|--------|---------|-------|
| O-1 | pgvector Memory aktivieren | ⭐⭐⭐⭐⭐ | 1h | 1 |
| O-2 | AGENT_HANDOVER auto-generieren | ⭐⭐⭐⭐ | 1h | 1 |
| O-3 | Warm-Start mit pgvector | ⭐⭐⭐⭐ | 30min | 1 |
| O-4 | Pre-Edit Violation Check | ⭐⭐⭐⭐⭐ | 2h | 2 |
| O-5 | Error-Pattern-DB | ⭐⭐⭐⭐ | 2h | 3 |
| O-6 | CORE_CONTEXT Generator | ⭐⭐⭐⭐ | 2h | 2 |
| O-7 | Fix-Templates in rules.json | ⭐⭐⭐⭐ | 2h | 2 |
| O-8 | Unified Context API | ⭐⭐⭐⭐⭐ | 6h | 2 |
| O-9 | Delta-Detection | ⭐⭐⭐⭐ | 4h | 3 |
| O-10 | Korrektur-Feedback-Loop | ⭐⭐⭐ | 4h | 3 |
| O-11 | Quality Dashboard | ⭐⭐⭐ | 8h | 3 |

---

## Architecture Diagram (Target State)

```
                    ┌──────────────────────────┐
                    │   Cascade (Windsurf IDE)  │
                    └────────────┬─────────────┘
                                 │ MCP stdio
                    ┌────────────▼─────────────┐
                    │  get_full_context() (O-8) │ ← ONE CALL (async)
                    │  orchestrator_mcp/server  │
                    └────────────┬─────────────┘
                                 │ asyncio.gather() (R-04)
              ┌──────────┬───────┼───────┬──────────┐
              ▼          ▼       ▼       ▼          ▼
        ┌──────────┐ ┌────────┐ ┌─────┐ ┌────────┐ ┌──────┐
        │get_repo_ │ │pgvector│ │Outline││Git Log │ │Issues│
        │facts()   │ │(Memory)│ │(Wiki) ││(Delta) │ │(GH)  │
        │local JSON│ │SQL+SSH │ │HTTP   ││SSH     │ │HTTP  │
        └──────────┘ └────────┘ └───────┘└────────┘ └──────┘
              ↑            ▲
         repos.json        │ Write (session-ende)
         (Disk, <1ms)      │
              ┌────────────┴───────────────┐
              │ session-ende (O-1)         │
              │ error-pattern-log (O-5)    │
              │ correction-capture (O-10)  │
              │ gc() decay cleanup (R-17)  │
              └────────────────────────────┘
```

Anmerkungen zum Diagramm (R-16):
- `get_repo_facts()` liest `repos.json` lokal von Disk (platform_context_mcp), kein Netzwerk-Call
- pgvector wird via SSH-Tunnel + autossh erreicht (Phase 0)
- Alle 5 Backend-Calls laufen parallel via `asyncio.gather()` mit 3s Timeout (R-04)
- Partial-Result-Pattern: ein fehlerhafter Call liefert `null` + `_warnings`, kein Gesamtfehler (R-08)

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| pgvector Memory wird zu groß | Langsame Suche | Temporal Decay aktiv, max 1000 Entries, alte archivieren |
| Unified API zu langsam (5 Backend-Calls) | Session-Start verzögert | `asyncio.gather()` + `wait_for(timeout=3s)` pro Call (R-04) |
| SSH-Tunnel fällt aus nach WSL-Restart | Memory komplett offline | `autossh` + systemd user-service mit `Restart=always` (R-02) |
| Invalide Daten in Memory Store | Garbage-Entries, falsche Suchtreffer | Pydantic v2 Schema-Gate vor jedem Write (R-07) |
| Error-Patterns werden zu generisch | Nutzlose Treffer | Structured Tags, Repo-spezifische Filterung |
| AGENT_HANDOVER Generator driftet | Falsche Fakten | Generator liest aus SSOT (repos.json), nie manuell |

---

## Implementation Status

| Phase | Inhalt | Status | Commits |
|-------|--------|--------|---------|
| **Phase 0** | pgvector-Konnektivität: autossh + systemd, read_secret(), TEXT[]-Bug, Pydantic Validator | ✅ Done | mcp-hub `fc860a6` |
| **Phase 1** | Workflows: session-ende (Memory Write, Error-Patterns, gc()), session-start (Warm-Start), Fulltext-Fallback | ✅ Done | mcp-hub `fc860a6`, platform `2814a86` |
| **Phase 2** | orchestrator erweitern: agent_sessions DDL (R-11), get_full_context Tool (R-04/R-08), fix_template (R-15), Unique-Index (R-06) | ✅ Done | mcp-hub `187f000` |
| **Phase 3** | Self-Learning: log_error_pattern (R-09), find_similar_errors, get_session_delta, session_stats, FTS simple | ✅ Done | mcp-hub `9bd2a96` |
| **Review** | Auto-bootstrap, rowcount scope, validated params, FTS german→simple | ✅ Done | mcp-hub `9bd2a96`, platform `cd9724c` |
| **Optimierung** | Semantic Search: OPENAI_API_KEY secrets fallback, CAST vector fix, Embedding-Backfill, error_pattern embeddings | ✅ Done | mcp-hub `4ed423b` |

### Verifiziert (MCP-Tools)
- `agent_memory_upsert` → ✅ ok:true
- `agent_memory_search` → ✅ **Semantic Search aktiv** (cosine similarity + temporal decay)
- `agent_memory_context` → ✅ Top-K relevante Entries
- `session_start/end` → ✅ Python-verifiziert (3 Sessions)
- `get_full_context` → ⏳ nach nächstem Windsurf-Neustart
- `log_error_pattern` → ✅ SHA-Hash-Dedup + Embedding
- `find_similar_errors` → ✅ Semantic + Fulltext + repo-Filter
- `get_session_delta` → ✅ Entries seit letzter Session
- `session_stats` → ✅ Quality Metrics (sessions=3, entries=7)

### Outline Knowledge Capture
- Lesson Learned: `76fcd0cd` — psycopg3 + SQLAlchemy Core Inkompatibilitäten

---

## Review History

| Datum | Reviewer | Dokument | Ergebnis |
|-------|----------|----------|----------|
| 2026-03-31 | Principal IT Architect | `reviews/00-review-adr-154.md` | 6 BLOCKER, 4 KRITISCH → Revisions nötig |
| 2026-03-31 | Cascade (Code-verifiziert) | `reviews/01-cascade-response-adr-154.md` | 14/17 akzeptiert, 2 abgelehnt (R-03 Django-Irrtum, R-14 i18n), 1 abgestuft |
| 2026-03-31 | Cascade (Impl.) | Phase 0+1+2 implementiert | 5 Bugs gefixt, 6 Smoke-Tests bestanden, 4 Commits gepusht |
| 2026-03-31 | Cascade (Impl.) | Phase 3 + Review | 4 neue MCP-Tools, FTS simple, auto-bootstrap, 7 Smoke-Tests bestanden |
| 2026-03-31 | Cascade (Opt.) | Semantic Search aktiviert | OPENAI_API_KEY, CAST vector, Backfill, 10 Entries mit Embeddings |

**Architektur-Entscheidung aus Review:** orchestrator_mcp bleibt **SQLAlchemy Core** — kein Django ORM. MCP-Server ≠ Django-Hub. Details in `01-cascade-response-adr-154.md`.

---

## Links

- ADR-066: AI Engineering Squad
- ADR-068: Adaptive Model Routing
- ADR-080: Multi-Agent Coding Team
- ADR-108: Agent QA Cycle
- ADR-113: pgvector Memory Store
- ADR-145: Knowledge Capture
- Outline: Platform Repo Directory (`d4c31417`)
- Outline: ADR-154 Konzept (`0befbd1a`)
