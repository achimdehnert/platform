# ADR-154 Review Response — Cascade Bewertung

**Autor:** Cascade (AI Coding Agent)  
**Datum:** 2026-03-31  
**Bezug:** `00-review-adr-154.md` + `01-impl-plan-adr-154.md`

---

## Gesamtbewertung der Review

**Review-Qualität: 8/10** — Gründlich, die meisten Findings sind valide und wichtig. Aber **R-03 enthält einen fundamentalen Architektur-Irrtum** der sich durch den gesamten Impl-Plan zieht und korrigiert werden muss.

**Impl-Plan-Qualität: 7/10** — Gut strukturiert mit klaren Acceptance Criteria. Aber baut auf dem R-03-Irrtum auf (Django ORM für orchestrator_mcp) und muss architekturell korrigiert werden.

---

## Fundamentaler Architektur-Befund: orchestrator_mcp ≠ Django

### Fakt (Code-verifiziert)

Der `orchestrator_mcp` ist ein **standalone MCP-Server** (Python-Package, läuft via `python -m orchestrator_mcp` als stdio-Prozess). Er verwendet:

- **SQLAlchemy Core** (nicht ORM) — `orchestrator_mcp/memory/schema.py` Zeile 1-115
- **Eigene DDL-Statements** — `CREATE TABLE IF NOT EXISTS agent_memory_entries` mit `TEXT PRIMARY KEY`
- **psycopg3** direkt — kein Django, kein `manage.py`, kein `INSTALLED_APPS`
- **Idempotentes Bootstrap** — `bootstrap(engine)` statt Django-Migrations

Siehe `orchestrator_mcp/memory/store.py` Zeile 11: `Stack: SQLAlchemy Core + psycopg3 (kein Django ORM).`

### Konsequenz für R-03 und Impl-Plan Phase 2

Der Impl-Plan schlägt vor:
```bash
cd iil-orchestrator-mcp
python manage.py startapp orchestrator_mcp  # ← FALSCH
python manage.py migrate orchestrator_mcp   # ← FALSCH
```

**Das ist architekturell falsch.** Es gibt kein `manage.py` im orchestrator_mcp. Django als Dependency hinzufügen würde:
1. Die Lightweight-Architektur des MCP-Servers zerstören
2. Einen zweiten ORM neben dem bereits funktionierenden SQLAlchemy einführen
3. Massive neue Dependencies (Django 5.x, ~50 Pakete) in einen MCP-Server ziehen

### Korrekte Lösung

Die bestehende SQLAlchemy-Core-Architektur beibehalten und **innerhalb dieses Stacks** die Platform-Standards umsetzen:
- `BigInteger` PK → **bereits vorhanden** (`tenant_id BigInteger`, aber `id` ist `TEXT PRIMARY KEY` — das ist die ADR-113-Entscheidung für semantische IDs)
- Soft-Delete → **bereits vorhanden** (`is_active Boolean`)
- `tenant_id` → **bereits vorhanden** (`BigInteger, server_default="1"`)
- UniqueConstraint → via SQLAlchemy + DDL (nicht Django)

---

## Einzelbewertung aller 17 Findings

### BLOCKER (6)

| # | Finding | Bewertung | Korrekte Aktion |
|---|---------|-----------|-----------------|
| **R-01** | `read_secret()` statt env-var | ✅ **VALID** | `read_secret()` Pattern in `_get_engine()` von `store.py` implementieren. Secret aus `~/.secrets/orchestrator_mcp_db_password` lesen, URL daraus zusammenbauen. |
| **R-02** | SSH-Tunnel Reconnect | ✅ **VALID und wichtig** | `autossh` + systemd user-service ist der richtige Ansatz. Ohne Reconnect fällt Memory nach jedem WSL-Restart aus. |
| **R-03** | Django-Model mit Platform-Standards | ❌ **ABGELEHNT — Architektur-Irrtum** | orchestrator_mcp ist KEIN Django-Projekt. SQLAlchemy Core beibehalten. Die Platform-Standards (BigAutoField, public_id) gelten für **Django-Hubs**, nicht für MCP-Server. Relevante Standards (tenant_id, soft-delete, content_hash) sind bereits implementiert. |
| **R-04** | Synchrone Parallel-Calls | ✅ **VALID** | `asyncio.gather()` mit Timeouts ist korrekt. Der orchestrator_mcp server ist bereits async (`async def call_tool()`). Natürlicher Fit. |
| **R-05** | Shell ohne pipefail | ✅ **VALID** | Trivial zu fixen, Platform-Standard. |
| **R-06** | UniqueConstraint auf entry_key | ⚠️ **TEILWEISE VALID** | Die aktuelle Architektur nutzt `id TEXT PRIMARY KEY` mit `entry_key` als `id`. Das IST bereits ein Unique Constraint (PK = unique per Definition). Aber: kein Scoping auf `tenant_id` + `is_active`. Fix: `UNIQUE INDEX ON (id, tenant_id) WHERE is_active = TRUE` via DDL. Kein Django `UniqueConstraint` nötig. |

### KRITISCH (4)

| # | Finding | Bewertung | Korrekte Aktion |
|---|---------|-----------|-----------------|
| **R-07** | Schema-Validation vor Write | ✅ **VALID** | Pydantic v2 Schema als Gate vor `upsert()`. Einfach: Pydantic-Model in `orchestrator_mcp/memory/validators.py`, Aufruf in `upsert()`. |
| **R-08** | Fehler-Isolation in get_full_context | ✅ **VALID und kritisch** | Partial-Result-Pattern mit `_safe_call()` + `_warnings` Liste. Ein kaputter Outline-Call darf nicht den gesamten Context killen. |
| **R-09** | Deterministische Hash-Funktion | ✅ **VALID** | `hashlib.sha256(f"{repo}:{error_type}:{file_path}".encode()).hexdigest()[:16]` als `entry_key` für error_patterns. Gut durchdacht. |
| **R-10** | Option C als REJECTED markieren | ✅ **VALID** | Trivial, sofort umsetzbar. |

### HOCH (3)

| # | Finding | Bewertung | Korrekte Aktion |
|---|---------|-----------|-----------------|
| **R-11** | AgentSession-Tabelle | ✅ **VALID** | Dedizierte `agent_sessions`-Tabelle (SQLAlchemy DDL, nicht Django-Model). Felder: `id SERIAL`, `repo TEXT`, `task TEXT`, `started_at TIMESTAMPTZ`, `ended_at TIMESTAMPTZ`. Index auf `started_at`. |
| **R-12** | Metrics Write-Path | ✅ **VALID** | Bestehende `llm_calls`-Tabelle nutzen. Kein neuer Grafana-Write-User nötig. |
| **R-13** | O-6 fehlt in Priority Matrix | ✅ **VALID** | In ADR aufnehmen, Phase 2, 1h Aufwand. |

### MEDIUM (4)

| # | Finding | Bewertung | Korrekte Aktion |
|---|---------|-----------|-----------------|
| **R-14** | i18n-Markierung | ❌ **ABGELEHNT** | orchestrator_mcp ist ein MCP-Server für AI-Agent-Konsum, KEINE User-facing Django-App. Die Responses sind technischer JSON/Text für Cascade. `_()` ist hier sinnlos und würde Complexity ohne Nutzen hinzufügen. |
| **R-15** | fix_template als Objekt | ✅ **VALID** | `{"code": "...", "since": "django-5.0", "docs_url": "..."}` ist besser als plain String. Einfach in `rules.json` umzusetzen. |
| **R-16** | Diagramm-Clarity | ✅ **VALID** | Klärung: `platform_context_mcp.get_repo_facts()` (lokal, in-memory JSON-Load) vs. MCP-Call. |
| **R-17** | Decay nicht implementiert | ⚠️ **TEILWEISE VALID** | `gc()` existiert bereits in `store.py` (Zeile 285-329) — macht exakt das: `is_active = FALSE` bei `decay_factor < 0.05`. Fehlt: periodischer Trigger. Lösung: **Cron-Job oder Aufruf in `session-ende`**, NICHT Celery (gibt es nicht im orchestrator_mcp). |

---

## Score-Zusammenfassung

| Kategorie | Original | Nach Prüfung | Kommentar |
|-----------|----------|--------------|-----------|
| BLOCKER | 6 | **4** | R-03 abgelehnt (Architektur-Irrtum), R-06 nur DDL-Index nötig |
| KRITISCH | 4 | **4** | Alle valid |
| HOCH | 3 | **3** | Alle valid |
| MEDIUM | 4 | **3** | R-14 abgelehnt (kein i18n für MCP-Server) |

**14 von 17 Findings akzeptiert, 2 abgelehnt, 1 abgestuft.**

---

## Korrigierter Implementierungsplan

### Phase 0: pgvector-Konnektivität (~30min)

Aus dem Impl-Plan **korrekt übernommen**:
1. `autossh` installieren
2. Secret in `~/.secrets/orchestrator_mcp_db_password` hinterlegen
3. systemd user-service `iil-memory-tunnel.service` erstellen
4. `~/.config/iil/memory-tunnel.env` generieren
5. **NEU: `read_secret()` Funktion** in `orchestrator_mcp/memory/store.py` statt `os.environ.get()`

**Akzeptanzkriterium:** `systemctl --user is-active iil-memory-tunnel` → `active` UND `agent_memory_search(query="test")` → JSON ohne Error.

### Phase 1: Quick Wins (~2h)

| # | Was | Wo | Aufwand |
|---|-----|-----|---------|
| 1.1 | `session-ende.md` erweitern: `agent_memory_upsert` + `gc()` Aufruf | `platform/.windsurf/workflows/session-ende.md` | 30min |
| 1.2 | `session-start.md` erweitern: `agent_memory_context` Warm-Start | `platform/.windsurf/workflows/session-start.md` | 15min |
| 1.3 | `generate-agent-handover.sh` Script erstellen | `platform/scripts/generate-agent-handover.sh` | 45min |
| 1.4 | Option C im ADR als REJECTED markieren (R-10) | `ADR-154` | 5min |
| 1.5 | O-6 in Priority Matrix aufnehmen (R-13) | `ADR-154` | 5min |

**Keine neuen Python-Dateien nötig** — nur Workflow-Ergänzungen + 1 Shell-Script.

### Phase 2: Verbesserungen am orchestrator_mcp (~5h)

| # | Was | Wo | Aufwand |
|---|-----|-----|---------|
| 2.1 | `read_secret()` in `store.py` (R-01) | `orchestrator_mcp/memory/store.py` | 30min |
| 2.2 | Pydantic v2 Validator (R-07) | `orchestrator_mcp/memory/validators.py` (NEU) | 1h |
| 2.3 | `agent_sessions` DDL-Tabelle (R-11) | `orchestrator_mcp/memory/schema.py` | 30min |
| 2.4 | `get_full_context()` async mit Partial-Result (R-04, R-08) | `orchestrator_mcp/server.py` (neues Tool) | 2h |
| 2.5 | `fix_template` als Objekt in `rules.json` (R-15) | `platform_context_mcp/graph/rules.json` | 30min |
| 2.6 | Unique-Index DDL ergänzen (R-06) | `orchestrator_mcp/memory/schema.py` | 15min |
| 2.7 | Diagramm im ADR korrigieren (R-16) | `ADR-154` | 15min |

### Phase 3: Self-Learning (~6h) — Roadmap

| # | Was | Aufwand | Abhängigkeit |
|---|-----|---------|-------------|
| 3.1 | Error-Pattern-DB mit SHA-Hash-Key (R-09) | 2h | Phase 2.2 |
| 3.2 | Delta-Detection via `agent_sessions` (R-11) | 2h | Phase 2.3 |
| 3.3 | Quality Metrics in `llm_calls` (R-12) | 1h | Phase 2 |
| 3.4 | `gc()` periodisch triggern (R-17) — Cron oder session-ende | 30min | Phase 0 |
| 3.5 | Korrektur-Feedback-Loop | 2h | Phase 2.4 |

---

## Architektur-Entscheidung (explizit festgehalten)

**orchestrator_mcp bleibt SQLAlchemy Core — kein Django ORM.**

Begründung:
1. MCP-Server sind Lightweight-Prozesse (stdio), nicht Django-Webapps
2. SQLAlchemy Core Memory Store existiert und funktioniert (store.py, 329 Zeilen)
3. Django als Dependency würde ~50 Pakete hinzufügen ohne Mehrwert
4. Platform-Standards die für Django-Hubs gelten (BigAutoField, admin, migrations) sind für MCP-Server nicht anwendbar
5. Die relevanten Standards (tenant_id, soft-delete, content_hash, Indexes) sind bereits in SQLAlchemy implementiert

**Platform-Standards die gelten:**
- `read_secret()` für Credentials ✅
- `set -euo pipefail` in Shell-Scripts ✅
- Pydantic v2 Validation ✅
- Idempotente Schema-Creation ✅ (bereits vorhanden via `CREATE TABLE IF NOT EXISTS`)

**Platform-Standards die NICHT gelten (MCP-Server ≠ Django-Hub):**
- `BigAutoField` (TEXT PK ist ADR-113 Entscheidung für semantische IDs)
- `public_id UUID` (nicht relevant für interne Memory-Entries)
- Django Migrations (SQLAlchemy DDL + `IF NOT EXISTS`)
- `_()` i18n (kein User-facing Output)
- Celery (kein Django-Worker-Kontext)
