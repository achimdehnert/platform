# ADR-113 — Telegram Gateway + pgvector Memory Store

**Status:** Accepted  
**Datum:** 2026-03-08  
**Autoren:** Cascade Agent Team  
**Ersetzt:** ADR-112 (AGENT_MEMORY.md Markdown-Store — wird migriert)  
**Inspiriert durch:** OpenClaw Codebase-Analyse (openclaw-main, openclaw-skills-main)

---

## Kontext

### Ausgangslage

ADR-112 implementierte einen ersten Persistent Context Store als `AGENT_MEMORY.md` (Markdown + JSON-Blöcke, Git-tracked). Die OpenClaw-Codebase-Analyse (März 2026) ergab:

1. **Memory-Store als Markdown skaliert nicht** — kein semantisches Retrieval, keine Gewichtung, Merge-Konflikte bei parallelen Agents
2. **Temporal Decay** ist als binäres `expires_at` unzureichend — OpenClaw nutzt exponentielle Score-Gewichtung (`score * e^(-λ * age_days)`)
3. **Mobile Kommunikation fehlt** — kein Kanal für unterwegs (iPad/iPhone → Agent) außer GitHub Mobile
4. **Gate-Decisions per GitHub Issue** sind umständlich — Telegram ermöglicht `/approve`/`/reject` in Sekunden

### Warum PostgreSQL + pgvector statt SQLite

- PostgreSQL bereits auf allen Hubs vorhanden (keine neue Infrastruktur)
- `pgvector` Extension: Vektor-Suche direkt in SQL kombinierbar mit BM25 Full-Text-Search
- Temporal Decay als Query-Strategie statt als separates Feld → sauberer
- Django ORM-Integration über `pgvector` Package

### Warum Telegram statt anderer Kanäle

- Einfachste Bot-Integration (Bot-Token, kein Webhook-Server nötig — Long Polling reicht)
- Bi-direktional: Empfangen + Senden in einem Service
- Gate-Decisions per `/approve task_id` oder `/reject task_id reason`
- GitHub Actions bleibt der Execution-Motor — Telegram ist nur die Mobile-UI

---

## Entscheidung

### Komponente 1: pgvector Memory Store (ADR-112 Migration)

**AGENT_MEMORY.md wird ersetzt durch** ein PostgreSQL-basiertes Memory-System mit Vektor-Embeddings:

```
mcp-hub (Django App: agent_memory)
├── models.py          — AgentMemoryEntry (pgvector Field)
├── services.py        — upsert, query, gc, temporal_score
├── embeddings.py      — OpenAI text-embedding-3-small (1536 dims)
└── migrations/
```

**Datenbankschema:**

```sql
-- pgvector Extension erforderlich
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE agent_memory_entries (
    id           TEXT PRIMARY KEY,
    entry_type   TEXT NOT NULL,
    title        TEXT NOT NULL,
    content      TEXT NOT NULL,
    agent        TEXT NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    half_life_days INTEGER NOT NULL DEFAULT 30,
    tags         TEXT[] NOT NULL DEFAULT '{}',
    related_ids  TEXT[] NOT NULL DEFAULT '{}',
    embedding    vector(1536),
    metadata     JSONB NOT NULL DEFAULT '{}'
);

-- Semantic Search Index
CREATE INDEX ON agent_memory_entries
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);

-- Full-Text Search (Hybrid)
CREATE INDEX ON agent_memory_entries
  USING gin(to_tsvector('german', content || ' ' || title));

-- Tag-Filter
CREATE INDEX ON agent_memory_entries USING gin(tags);
```

**Temporal Decay Query (ersetzt expires_at + GC):**

```sql
SELECT
    id, title, content, entry_type, tags, metadata,
    (1 - (embedding <=> %(query_vec)s)) AS semantic_score,
    exp(
        -0.693 *
        EXTRACT(EPOCH FROM (now() - updated_at)) / 86400.0
        / half_life_days
    ) AS decay_factor,
    (1 - (embedding <=> %(query_vec)s)) *
    exp(
        -0.693 *
        EXTRACT(EPOCH FROM (now() - updated_at)) / 86400.0
        / half_life_days
    ) AS final_score
FROM agent_memory_entries
WHERE (%(filter_type)s IS NULL OR entry_type = %(filter_type)s)
ORDER BY final_score DESC
LIMIT %(limit)s;
```

**Formel:** `score_final = semantic_similarity * e^(-ln(2)/half_life_days * age_days)`

Bei `half_life_days=30`: Nach 30 Tagen hat ein Entry noch 50% seines Scores,
nach 90 Tagen 12.5%.

**Default half_life_days per entry_type:**

| entry_type | half_life_days | Begründung |
|---|---|---|
| `open_task` | 14 | Tasks werden schnell irrelevant |
| `context` | 30 | Allgemeiner Kontext, mittel-langlebig |
| `decision` | 180 | Architektur-Entscheidungen bleiben lang relevant |
| `lesson_learned` | 365 | Learnings sollen dauerhaft verfügbar bleiben |
| `agent_handover` | 7 | Session-Übergaben sind kurzlebig |

---

### Komponente 2: Telegram Agent Gateway

**Deployment:** Docker Container auf `hetzner-prod`, Teil von `mcp-hub`

**Architektur:**

```
iPhone/iPad
    ↓ Telegram Message
Telegram Bot (mcp-hub telegram_gateway App)
    ├── Command Parser (/task, /status, /approve, /reject, /memory)
    ├── GitHub Actions Dispatcher (via GitHub API)
    └── Response Formatter
            ↓
    GitHub Actions (agent-task-dispatch.yml)
            ↓
    Cascade Agent (Windsurf)
            ↓
    Ergebnis in GitHub Issue + Telegram Reply
```

**Unterstützte Befehle:**

| Befehl | Beschreibung |
|--------|-------------|
| `/task <beschreibung>` | Neuen Agent-Task erstellen (→ GitHub Issue + Workflow) |
| `/status` | Alle laufenden Tasks anzeigen |
| `/approve <task_id> [kommentar]` | Gate-Decision: Freigabe |
| `/reject <task_id> <grund>` | Gate-Decision: Ablehnen |
| `/memory <query>` | pgvector Memory durchsuchen |
| `/memory add <title>: <content>` | Memory-Entry erstellen |
| `/deploy <repo>` | Deployment-Workflow triggern (Gate 2) |
| `/health` | Health-Status aller Deploy-Targets |

**Security:**
- Nur autorisierte `TELEGRAM_ALLOWED_USER_IDS` werden akzeptiert
- Gate 2+ Befehle (`/deploy`, `/approve` für kritische Tasks) erfordern Bestätigung
- Bot-Token in Django Secrets / Windsurf Secrets

---

### Komponente 3: Bi-direktionale Response-Pipeline

Wenn GitHub Actions abgeschlossen:

```yaml
# Am Ende jedes agent-task Workflows:
- name: Notify via Telegram
  if: env.TELEGRAM_BOT_TOKEN != ''
  run: |
    python .github/scripts/telegram_notify.py \
      --chat-id "${{ vars.TELEGRAM_CHAT_ID }}" \
      --message "Task ${{ github.event.issue.number }} abgeschlossen"
```

---

## Implementierungsplan

### Phase 1: pgvector Memory (ADR-112 Migration)

**Dateien:**
```
mcp-hub/apps/agent_memory/
├── __init__.py
├── models.py              # AgentMemoryEntry mit pgvector Field
├── services.py            # query(), upsert(), gc(), semantic_search()
├── embeddings.py          # OpenAI Embedding Client
├── admin.py               # Django Admin für manuelle Einträge
└── migrations/
    └── 0001_initial.py
```

**orchestrator_mcp/skills/session_memory.py** wird umgeschrieben:
- Schreibt nicht mehr in `AGENT_MEMORY.md`
- Ruft `mcp-hub` REST API `/api/agent-memory/` auf
- AGENT_MEMORY.md bleibt als Read-only Fallback für Offline-Betrieb

**Neue orchestrator_mcp Tools:**
- `agent_memory_search` — Semantic Search via pgvector
- `agent_memory_upsert` — Entry erstellen/aktualisieren mit Embedding
- `agent_memory_context` — Top-K relevante Entries für aktuellen Task

### Phase 2: Telegram Bot

**Dateien:**
```
mcp-hub/apps/telegram_gateway/
├── __init__.py
├── bot.py                 # python-telegram-bot Application
├── handlers.py            # Command Handler (/task, /approve, etc.)
├── dispatcher.py          # GitHub Actions Trigger via GitHub API
├── formatter.py           # Response-Formatting (Markdown → Telegram HTML)
└── management/
    └── commands/
        └── run_telegram_bot.py   # Django Management Command
```

**Docker-Service in `docker-compose.yml`:**
```yaml
telegram-bot:
  build: .
  command: python manage.py run_telegram_bot
  environment:
    - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
    - TELEGRAM_ALLOWED_USER_IDS=${TELEGRAM_ALLOWED_USER_IDS}
    - GITHUB_TOKEN=${GITHUB_TOKEN}
  restart: unless-stopped
  depends_on:
    - db
```

### Phase 3: GitHub Actions Response Pipeline

**Ergänzungen in bestehenden Workflows:**
- `agent-task-dispatch.yml`: Telegram-Notification bei Abschluss
- `agent-task-issue.yml`: Telegram-Notification bei Gate-Requests
- `agent-gate-decision.yml`: Telegram-Push wenn `/approve` oder `/reject`
  via Issue-Kommentar

### Phase 4: orchestrator_mcp v3.3 Integration

- `server.py` v3.3: `agent_memory_search`, `agent_memory_upsert` registrieren
- `AGENT_HANDOVER.md`: Telegram-Befehle dokumentieren
- `AGENT_MEMORY.md`: Migration-Script (MD → pgvector)

---

## Technische Dependencies

```toml
# mcp-hub/requirements.txt Ergänzungen
pgvector>=0.3.0            # Django pgvector Field
openai>=1.0.0              # Embeddings API
python-telegram-bot>=21.0  # Telegram Bot Framework (async)
```

**Server-Voraussetzungen:**
```bash
# hetzner-prod: pgvector Extension installieren
sudo apt install postgresql-16-pgvector
# oder via Docker:
# image: pgvector/pgvector:pg16
```

---

## Konsequenzen

### Positiv
- **Semantisches Retrieval**: Agent findet relevante Memories anhand von
  Bedeutung, nicht Stichwörtern
- **Temporal Decay**: Alte Entries degradieren graduell statt abrupt zu
  verschwinden
- **Mobile-first**: Voller Agent-Zugriff vom iPhone/iPad
- **Gate-Decisions in Sekunden**: `/approve 42` statt Issue-Comment auf GitHub
- **Kein neuer Server**: Telegram Bot läuft als Container auf hetzner-prod

### Negativ / Risiken
- **Embedding Kosten**: OpenAI Embeddings bei jedem Upsert
  (~$0.0001/Entry, vernachlässigbar)
- **pgvector Installation**: Einmalig auf hetzner-prod
- **Telegram-Abhängigkeit**: Bei Bot-Ausfall GitHub Mobile als Fallback
- **Kein Offline-Betrieb**: pgvector benötigt DB-Verbindung
  (AGENT_MEMORY.md als Fallback)

### Nicht betroffen
- Bestehende ADR-112 Skills (`base.py`, `__init__.py`, `repo_scan.py`)
- GitHub Actions Workflows bleiben der Execution-Motor
- Windsurf Cascade als primäre IDE-Schnittstelle
- Gate-System ADR-107 — Telegram ist nur zusätzlicher Input-Kanal

---

## Rollback-Plan

1. `AGENT_MEMORY.md` bleibt als Fallback — Migration-Script ist reversibel
2. Telegram Bot: `docker stop telegram-bot` — alle anderen Services unberührt
3. Feature-Flag `SKILL_MEMORY_BACKEND=markdown|pgvector` (default: `pgvector`)

---

## Offene Fragen

- [ ] Embedding-Provider: OpenAI `text-embedding-3-small` (1536 dims)
  oder lokales Modell via Ollama?
- [ ] Telegram Chat-ID: Einzelperson oder Gruppe (mehrere autorisierte Agents)?
- [ ] Migration: `AGENT_MEMORY.md` T-001 Entry → pgvector
  (automatisiert oder manuell?)

---

## Verwandte ADRs

- ADR-107: Extended Agent Team + Deployment Agent
- ADR-108: Orchestrator MCP Server
- ADR-112: Agent Skill Registry + Persistent Context Store (wird migriert)
- ADR-062: Central Billing Service (billing-hub Postgres-Architektur als Referenz)
