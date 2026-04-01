# ADR-154: Implementierungsplan — Autonomous Coding Optimization

**Version:** 1.0 (post-review)  
**Datum:** 2026-03-31  
**Status:** Ready for execution (alle BLOCKER/KRITISCH adressiert)

---

## Behobene Review-Findings

| Finding | Lösung | Datei |
|---------|--------|-------|
| R-01: read_secret() | `read_secret()` in allen Credentials | `phase2-memory-service.py`, `phase2-tasks.py` |
| R-02: SSH-Tunnel instabil | systemd user-service + autossh | `phase0-setup-memory-tunnel.sh` |
| R-03: Kein Django-Model | `AgentMemoryEntry` + `AgentSession` mit Platform-Standards | `phase2-models.py` |
| R-04: Synchrone Parallel-Calls | `asyncio.gather()` + `asyncio.wait_for(timeout=3s)` | `phase2-context-service.py` |
| R-05: Shell ohne pipefail | `set -euo pipefail` + trap | alle `.sh` Dateien |
| R-06: UniqueConstraint | `UniqueConstraint(condition=Q(deleted_at__isnull=True))` | `phase2-models.py` |
| R-07: Kein Schema-Gate | `MemoryEntrySchema` (Pydantic v2) | `phase2-memory-service.py` |
| R-08: Keine Fehler-Isolation | Partial-Result-Pattern, `_safe_call()` | `phase2-context-service.py` |
| R-09: Undefinierter Hash | `build_error_pattern_key()` mit SHA256[:16] | `phase2-memory-service.py` |
| R-10: Option C im ADR | Wurde als ABGELEHNT markiert (im ADR updaten) | ADR-154 (manuell) |
| R-11: pgvector Timestamp-Lookup | `AgentSession`-Tabelle mit Index | `phase2-models.py`, `phase2-0001-migration.py` |
| R-12: Metrics Write-Path | Celery Beat Task, bestehende `llm_calls`-Tabelle | `phase2-tasks.py` |
| R-17: Decay undefined | `decay_old_entries()` + Celery Beat | `phase2-memory-service.py`, `phase2-tasks.py` |

---

## Dateistruktur (Ziel-State)

```
iil-platform-stack/
├── platform/
│   ├── scripts/
│   │   ├── phase0-setup-memory-tunnel.sh     ← Phase 0
│   │   ├── generate-agent-handover.sh        ← Phase 1
│   │   └── sync-workflows.sh                 ← (existiert, erweitern)
│   └── data/
│       └── rules.json                        ← Phase 2 (fix_template erweitern)
│
orchestrator_mcp/
├── models.py                                 ← Phase 2 (NEU)
├── tasks.py                                  ← Phase 2 (NEU)
├── migrations/
│   └── 0001_initial.py                       ← Phase 2 (NEU, idempotent)
├── services/
│   ├── memory_service.py                     ← Phase 2 (NEU)
│   └── context_service.py                    ← Phase 2 (NEU)
├── tools/
│   └── memory_tools.py                       ← Phase 2 (NEU: FastMCP tools)
└── clients/
    ├── platform_context_client.py            ← existiert (prüfen)
    ├── outline_client.py                     ← existiert (prüfen)
    └── github_client.py                      ← existiert (prüfen)
```

---

## Phase 0: Blocker beseitigen (~30 min)

### Schritt 0.1: autossh installieren
```bash
sudo apt install autossh -y
```

### Schritt 0.2: Secret hinterlegen
```bash
mkdir -p ~/.secrets
echo "DEIN_DB_PASSWORD" > ~/.secrets/orchestrator_mcp_db_password
chmod 600 ~/.secrets/orchestrator_mcp_db_password
```

### Schritt 0.3: Setup-Script ausführen
```bash
chmod +x platform/scripts/phase0-setup-memory-tunnel.sh
./platform/scripts/phase0-setup-memory-tunnel.sh
```

### Schritt 0.4: Verbindung verifizieren
```bash
source ~/.config/iil/memory-tunnel.env
psql "$ORCHESTRATOR_MCP_MEMORY_DB_URL" -c 'SELECT version();'
```

### Schritt 0.5: ADR-154 Option C als REJECTED markieren
Im ADR-154 die Phase-0-Tabelle aktualisieren:
```markdown
| ~~C: Port auf Prod öffnen~~ | ~~5min~~ | ❌ **REJECTED — Security** | ~~~20ms~~ |
```
**Akzeptanzkriterium Phase 0:** `psql` liefert PostgreSQL-Version. Systemd-Service `active (running)`.

---

## Phase 1: Quick Wins (~3h)

### Schritt 1.1: AGENT_HANDOVER Generator deployen
```bash
cp phase1-generate-agent-handover.sh platform/scripts/generate-agent-handover.sh
chmod +x platform/scripts/generate-agent-handover.sh

# Dry-Run testen:
./platform/scripts/generate-agent-handover.sh --dry-run

# In sync-workflows.sh integrieren (ans Ende):
echo "" >> platform/scripts/sync-workflows.sh
echo "./platform/scripts/generate-agent-handover.sh" >> platform/scripts/sync-workflows.sh
```

**Voraussetzung:** `pip install pyyaml jq` im WSL-Environment.

### Schritt 1.2: Windsurf Workflow `session-ende` erweitern
Füge folgende Schritte in `.windsurf/workflows/session-ende.md` hinzu:

```markdown
## Schritt: Session Memory schreiben
Rufe `end_session` MCP-Tool auf:
- repo: [aktuelles Repo aus Workspace]
- task_summary: [Was wurde erledigt]
- decisions_made: [Architektur-Entscheidungen]
- errors_encountered: [Aufgetretene Fehler]
- lessons_learned: [Erkenntnisse für nächste Session]

## Schritt: Error-Patterns erfassen (bei Bug-Fixes)
Falls in dieser Session ein Bug gefixt wurde:
Rufe `log_error_pattern` MCP-Tool auf mit Symptom/Root-Cause/Fix/Prevention.
```

### Schritt 1.3: Windsurf Workflow `session-start` erweitern
Füge nach Repo-Detect-Schritt in `.windsurf/workflows/session-start.md` ein:

```markdown
## Schritt: Warm-Start Memory laden
Rufe `agent_memory_context` MCP-Tool auf:
- task_description: [User-Aufgabe aus erster Nachricht]
- repo: [aktuelles Repo]
- top_k: 5
→ Relevante Memories aus früheren Sessions werden geladen.
```

**Akzeptanzkriterium Phase 1:**
- `./generate-agent-handover.sh --dry-run` produziert valides Markdown ohne Fehler
- `agent_memory_context(task_description="test", repo="risk-hub")` gibt JSON zurück (auch wenn noch leer)

---

## Phase 2: Unified Context API (~6h)

### Schritt 2.1: Django App erstellen (falls noch nicht vorhanden)
```bash
cd iil-orchestrator-mcp
python manage.py startapp orchestrator_mcp
# In INSTALLED_APPS eintragen: "orchestrator_mcp"
```

### Schritt 2.2: Abhängigkeiten installieren
```bash
pip install pgvector openai pydantic>=2.0
# In requirements/base.txt:
# pgvector>=0.3.0
# openai>=1.0.0
# pydantic>=2.0.0
```

### Schritt 2.3: Models deployen
```bash
cp phase2-models.py orchestrator_mcp/models.py
cp phase2-0001-initial-migration.py orchestrator_mcp/migrations/0001_initial.py
python manage.py migrate orchestrator_mcp
```

### Schritt 2.4: Services deployen
```bash
mkdir -p orchestrator_mcp/services
cp phase2-memory-service.py orchestrator_mcp/services/memory_service.py
cp phase2-context-service.py orchestrator_mcp/services/context_service.py
touch orchestrator_mcp/services/__init__.py
```

### Schritt 2.5: FastMCP Tools deployen
```bash
mkdir -p orchestrator_mcp/tools
cp phase2-memory-tools.py orchestrator_mcp/tools/memory_tools.py
touch orchestrator_mcp/tools/__init__.py
```

### Schritt 2.6: Celery Tasks deployen
```bash
cp phase2-tasks.py orchestrator_mcp/tasks.py

# In settings/celery.py CELERY_BEAT_SCHEDULE ergänzen:
# "decay-old-memories-daily": {
#     "task": "orchestrator_mcp.tasks.decay_old_memories",
#     "schedule": crontab(hour=3, minute=0),
#     "kwargs": {"tenant_id": 1},
# }
```

### Schritt 2.7: rules.json fix_templates ergänzen
```bash
# Bestehende rules.json mit neuen fix_template-Feldern mergen:
# Jede Rule bekommt "fix_template": {"code": ..., "since": ..., "docs_url": ...}
# phase2-rules.json als Referenz nutzen
```

### Schritt 2.8: FastMCP Server registrieren
In `.windsurf/mcp_config.json` (oder Windsurf MCP Settings) prüfen ob
`orchestrator_mcp` als MCP-Server mit den neuen Tools `get_full_context`,
`agent_memory_upsert`, `agent_memory_search`, `agent_memory_context`,
`log_error_pattern`, `end_session` registriert ist.

**Akzeptanzkriterium Phase 2:**
```python
# Smoke-Test:
from orchestrator_mcp.services.memory_service import MemoryService
entry = MemoryService.upsert_entry({
    "entry_key": "test:smoke:abc123def456",
    "entry_type": "context",
    "title": "Smoke Test Entry",
    "content": "Dies ist ein Test-Eintrag für Phase 2 Smoke-Test.",
    "tags": ["test", "smoke"],
    "repo": "iil-platform-stack",
    "tenant_id": 1,
})
assert entry.public_id is not None
results = MemoryService.search_similar("test eintrag", tenant_id=1, top_k=1)
assert len(results) >= 1
print("✅ Phase 2 Smoke-Test bestanden")
```

---

## Phase 3: Self-Learning (~8h) — Roadmap

| Feature | Beschreibung | Aufwand | Abhängigkeit |
|---------|-------------|---------|-------------|
| O-9: Delta-Detection | Session-Start vergleicht mit letzter `AgentSession` | 2h | Phase 2 |
| O-10: Korrektur-Feedback | User-Korrektur → `lesson_learned` in Memory | 4h | Phase 2 |
| O-11: Quality Dashboard | Grafana-Panels: error_count, correction_count per Session | 2h | Phase 2 |

**O-11 Write-Path-Lösung (R-12):**
Metriken werden in bestehende `llm_calls`-Tabelle als zusätzliche Felder geschrieben
(kein neuer Write-User für Grafana nötig). Grafana liest weiterhin read-only.

---

## Acceptance Criteria (Gesamt)

| Kriterium | Test |
|-----------|------|
| Phase 0: Tunnel aktiv | `systemctl --user is-active iil-memory-tunnel` → `active` |
| Phase 0: DB erreichbar | `psql $ORCHESTRATOR_MCP_MEMORY_DB_URL -c 'SELECT 1'` → OK |
| Phase 1: Handover aktuell | `./generate-agent-handover.sh && diff AGENT_HANDOVER.md <(git show HEAD:AGENT_HANDOVER.md)` zeigt Diff |
| Phase 2: Memory write | `MemoryService.upsert_entry(...)` → entry.public_id nicht None |
| Phase 2: Memory search | `MemoryService.search_similar("test", 1)` → Liste (auch leer) ohne Exception |
| Phase 2: Full context | `get_full_context("risk-hub", "add feature X")` → dict mit `success: true` |
| Phase 2: Partial degradation | Ein Backend down → Response enthält `_warnings`, kein 500 |
| Phase 2: Schema validation | `MemoryService.upsert_entry({...invalid...})` → `ValidationError`, kein DB-Write |
| Phase 2: Migration idempotent | `python manage.py migrate orchestrator_mcp` zweimal ohne Fehler |
| Phase 2: Decay | `decay_old_entries(tenant_id=1)` → int ≥ 0, kein Exception |

---

## Konfigurationsreferenz

```bash
# ~/.config/iil/memory-tunnel.env (generiert von phase0-setup-memory-tunnel.sh)
ORCHESTRATOR_MCP_MEMORY_DB_URL=postgresql://orchestrator:<pw>@localhost:15435/orchestrator_mcp
ORCHESTRATOR_MCP_MEMORY_EMBEDDING_PROVIDER=openai

# ~/.secrets/orchestrator_mcp_db_password (chmod 600)
<password>

# ~/.secrets/OPENAI_API_KEY (chmod 600, für Embedding-Generierung)
sk-...
```

---

## Verwandte ADRs

- ADR-066: AI Engineering Squad
- ADR-068: Adaptive Model Routing
- ADR-080: Multi-Agent Coding Team
- ADR-094: AI Context Amnesia Prevention
- ADR-100: iil-testkit
- ADR-108: Agent QA Cycle
- ADR-142: authentik Identity Provider
- ADR-145: Knowledge Capture
