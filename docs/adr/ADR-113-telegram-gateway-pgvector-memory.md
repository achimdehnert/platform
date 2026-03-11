---
status: accepted
date: 2026-03-08
decision-makers: [Achim Dehnert]
implementation_status: implemented
---

# ADR-113 — Telegram Gateway + pgvector Memory Store

**Status:** Accepted (v2 — Review-Korrekturen eingearbeitet)
**Datum:** 2026-03-08 | **Revision:** 2026-03-08
**Autoren:** Cascade Agent Team
**Review:** Principal IT-Architekt (ADR-113-review-implementation.md)
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
- SQLAlchemy Core direkt (kein ORM-Overhead) — passt zum MCP-Server-Stack
- `orchestrator_mcp` hat bereits `sqlalchemy>=2.0` + `psycopg2-binary` als Dependency

### Warum Telegram statt anderer Kanäle

- Einfachste Bot-Integration (Bot-Token, kein Webhook-Server nötig — Long Polling reicht)
- Bi-direktional: Empfangen + Senden in einem Service
- Gate-Decisions per `/approve task_id` oder `/reject task_id reason`
- GitHub Actions bleibt der Execution-Motor — Telegram ist nur die Mobile-UI

---

## Entscheidung

### Komponente 1: pgvector Memory Store (ADR-112 Migration)

**AGENT_MEMORY.md wird ersetzt durch** ein PostgreSQL-basiertes Memory-System mit Vektor-Embeddings.

**Stack:** SQLAlchemy Core + psycopg3 direkt im `orchestrator_mcp` Python-Paket — kein Django ORM.

```
orchestrator_mcp/memory/
├── __init__.py
├── schema.py      — SQLAlchemy Table-Definition + CREATE TABLE + Indexes
├── store.py       — upsert(), search(), gc(), content_hash-Cache
└── embeddings.py  — EmbeddingClient (OpenAI + Ollama, embed_batch)
```

**Datenbankschema:**

```sql
-- pgvector Extension erforderlich
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE agent_memory_entries (
    id           TEXT PRIMARY KEY,           -- z.B. "T-001"
    tenant_id    INTEGER NOT NULL DEFAULT 1, -- iilgmbh=1; Multi-Tenant ab Phase 2
    entry_type   TEXT NOT NULL,              -- open_task, decision, context, lesson_learned
    title        TEXT NOT NULL,
    content      TEXT NOT NULL,
    agent        TEXT NOT NULL,              -- wer hat geschrieben
    is_active    BOOLEAN NOT NULL DEFAULT TRUE,  -- Soft-Delete (kein hard-delete)
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- kein hard expires_at mehr -- Temporal Decay übernimmt
    half_life_days INTEGER NOT NULL DEFAULT 30,  -- Decay-Halbwertszeit
    tags         TEXT[] NOT NULL DEFAULT '{}',
    related_ids  TEXT[] NOT NULL DEFAULT '{}',
    embedding     vector(1536),              -- OpenAI text-embedding-3-small
    content_hash  TEXT NOT NULL DEFAULT '',  -- SHA-256: Embedding nur neu berechnen wenn geändert
    metadata      JSONB NOT NULL DEFAULT '{}'
);

-- HNSW Index (besser als ivfflat für <100k Entries — kein Rebuild nötig)
CREATE INDEX CONCURRENTLY IF NOT EXISTS agent_memory_embedding_hnsw
  ON agent_memory_entries
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

-- ivfflat NICHT verwenden: lists=100 ist bei <5k Entries kontraproduktiv
-- (mehr Lists als Rows → Query-Performance schlechter als Sequential Scan)

-- Full-Text Search (Hybrid)
CREATE INDEX CONCURRENTLY IF NOT EXISTS agent_memory_fts_idx
  ON agent_memory_entries
  USING gin(to_tsvector('german', content || ' ' || title));

-- Tenant-Filter Index
CREATE INDEX IF NOT EXISTS agent_memory_tenant_idx
  ON agent_memory_entries (tenant_id, entry_type, is_active);
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

Bei `half_life_days=30`: Nach 30 Tagen hat ein Entry noch 50% seines Scores, nach 90 Tagen 12.5%.

**GC-Strategie:** Soft-Delete statt hard-delete — Entries mit `decay_factor < 0.05` werden auf
`is_active = FALSE` gesetzt (reversibel). Kein Datenverlust, Audit-Trail bleibt erhalten.

**`half_life_days` Defaults per `entry_type` (Entscheidung, keine offene Frage):**

| `entry_type` | `half_life_days` | Begründung |
|---|---|---|
| `open_task` | 14 | Tasks werden schnell irrelevant |
| `repo_context` | 7 | Repo-Stand veraltet schnell |
| `context` | 30 | Allgemeiner Kontext, mittel-langlebig |
| `error_pattern` | 90 | Fehler-Muster langlebig |
| `decision` | 180 | Architektur-Entscheidungen bleiben lang relevant |
| `lesson_learned` | 365 | Learnings dauerhaft verfügbar |
| `agent_handoff` | 7 | Session-Übergaben kurzlebig |

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
- `TELEGRAM_ALLOWED_USER_IDS` als `list[int]` in `pydantic-settings` — **kein** String-Vergleich:
  ```python
  telegram_allowed_user_ids: list[int] = Field(default_factory=list)
  # Parsing: [int(x.strip()) for x in env_str.split(",") if x.strip().isdigit()]
  ```
- `update.effective_user.id in settings.telegram_allowed_user_ids` — Integer-Vergleich
- Gate 2+ Befehle (`/deploy`, `/approve` für kritische Tasks) erfordern Bestätigung
- Bot-Token als `SecretStr` in `pydantic-settings` / Windsurf Secrets

**Rate-Limiting (In-Memory via `dict` + `time.time()`):**

| Befehl | Limit |
|---|---|
| `/task` | 10/Stunde — jeder Call triggert GitHub Actions |
| `/deploy` | 2/Stunde |
| `/approve`, `/reject` | 20/Stunde |
| `/memory`, `/health` | 30/Stunde |

Implementierung: `_rate_limits: dict[str, list[float]]` pro User-ID, Timestamps älter als 3600s entfernen.

---

### Komponente 2b: Async-Safety (Bot-Threading)

**NIEMALS `asyncio.run()` im laufenden Event-Loop aufrufen.**

`python-telegram-bot>=21` ist vollständig async. Korrekte Integration:

```python
# bot.py — threading-safe Pattern
_bot_loop: asyncio.AbstractEventLoop | None = None

def _run_bot_in_thread(app: Application) -> None:
    global _bot_loop
    loop = asyncio.new_event_loop()
    _bot_loop = loop          # Referenz speichern für stop_bot()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(app.run_polling(
            allowed_updates=["message"],
            drop_pending_updates=True,
        ))
    finally:
        _bot_loop = None
        loop.close()

def stop_bot() -> None:
    if _bot_application and _bot_loop:  # gespeicherte Loop-Referenz
        asyncio.run_coroutine_threadsafe(_bot_application.stop(), _bot_loop)
```

Django-Code in Handlers via `asyncio.to_thread()` (kein `sync_to_async` — kein Django).

---

### Komponente 3: Bi-direktionale Response-Pipeline

Wenn GitHub Actions abgeschlossen:

```yaml
# Am Ende jedes agent-task Workflows:
- name: Notify via Telegram
  if: env.TELEGRAM_BOT_TOKEN != ''
  run: |
    set -euo pipefail
    python .github/scripts/telegram_notify.py \
      --chat-id "${{ vars.TELEGRAM_CHAT_ID }}" \
      --message "Task ${{ github.event.issue.number }} abgeschlossen"
```

> Platform-Standard: `set -euo pipefail` in **jedem** `run:` Block — verhindert stille Fehler.

---

## Implementierungsplan

### Phase 1: pgvector Memory — `orchestrator_mcp/memory/`

**Stack:** SQLAlchemy Core + psycopg3 (kein Django ORM)

**Dateien in `mcp-hub/orchestrator_mcp/memory/`:**
```
orchestrator_mcp/memory/
├── __init__.py
├── schema.py       # SQLAlchemy Table + CREATE TABLE + HNSW Index (RunSQL)
├── store.py        # upsert(), search(), gc() — content_hash Cache eingebaut
└── embeddings.py   # OpenAI + Ollama EmbeddingClient, embed_batch()
```

**`store.py` Kernlogik — content_hash Cache + embedding defer:**
```python
def upsert(*, entry_key: str, content: str, ...) -> None:
    new_hash = hashlib.sha256(content.encode()).hexdigest()
    existing = _get_by_key(entry_key)  # SELECT ohne embedding-Spalte (defer)
    if existing and existing["content_hash"] == new_hash:
        return  # Content unverändert — kein API-Call, kein DB-Write
    embedding = client.embed(content)  # nur wenn nötig
    _write(entry_key=entry_key, content=content,
           content_hash=new_hash, embedding=embedding, ...)

def search(*, query: str, ...) -> list[dict]:
    # SELECT id, title, content, entry_type, tags, final_score
    # embedding-Spalte (6KB/Entry) wird NICHT geladen — nur für Ähnlichkeits-Berechnung
    # im WHERE/ORDER BY via pgvector Operator (<=>), nicht im Resultset
    ...
```

**Neue `orchestrator_mcp` Tools (in `server.py` v3.3):**
- `agent_memory_search` — Semantic Search mit Temporal Decay
- `agent_memory_upsert` — Entry erstellen/aktualisieren (content_hash-gesichert)
- `agent_memory_context` — Top-K relevante Entries für aktuellen Task

**`orchestrator_mcp/skills/session_memory.py`** wird umgeschrieben:
- Schreibt nicht mehr in `AGENT_MEMORY.md`
- Ruft `store.upsert()` direkt auf (kein REST-Umweg)
- `AGENT_MEMORY.md` bleibt als Read-only Fallback (`SKILL_MEMORY_BACKEND=markdown`)

### Phase 1b: Migration Script AGENT_MEMORY.md → pgvector

**`orchestrator_mcp/memory/migrate_from_md.py`** (eigenständiges Python-Script):
```
Usage: python -m orchestrator_mcp.memory.migrate_from_md \
    --file AGENT_MEMORY.md --dry-run
```
- Liest JSON-Blöcke aus `AGENT_MEMORY.md` (ADR-112 Format)
- Idempotent: `get_or_create` via `entry_key`
- Batch-Embedding für Effizienz
- `--dry-run` Mode ohne DB-Writes

### Phase 2: Telegram Bot — `orchestrator_mcp/telegram/`

**Stack:** `python-telegram-bot>=21`, `pydantic-settings`, `tenacity` für Retry

**Dateien in `mcp-hub/orchestrator_mcp/telegram/`:**
```
orchestrator_mcp/telegram/
├── __init__.py     # python -m orchestrator_mcp.telegram Entry Point
├── settings.py     # TelegramSettings (pydantic-settings, list[int] für IDs)
├── bot.py          # Application + threading-safe Loop-Management
├── handlers.py     # cmd_* mit Rate-Limiting via dict+time.time()
└── dispatcher.py   # GitHub API Trigger mit tenacity Retry (3 Versuche)
```

**Docker-Service in `docker-compose.yml`:**
```yaml
telegram-bot:
  build: .
  command: python -m orchestrator_mcp.telegram
  restart: unless-stopped
  environment:
    - ORCHESTRATOR_MCP_TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
    - ORCHESTRATOR_MCP_TELEGRAM_ALLOWED_USER_IDS=${TELEGRAM_ALLOWED_USER_IDS}
    - ORCHESTRATOR_MCP_GITHUB_TOKEN=${GITHUB_TOKEN}
    - ORCHESTRATOR_MCP_OPENAI_API_KEY=${OPENAI_API_KEY}
    - ORCHESTRATOR_MCP_MEMORY_DB_URL=${DATABASE_URL}
  healthcheck:
    test: ["CMD", "python", "-c",
           "import httpx; httpx.get('https://api.telegram.org', timeout=5)"]
    interval: 60s
    timeout: 10s
    retries: 3
    start_period: 30s
  depends_on:
    db:
      condition: service_healthy
```

### Phase 3: GitHub Actions Response Pipeline

**Ergänzungen in bestehenden Workflows:**
- `agent-task-dispatch.yml`: Telegram-Notification bei Abschluss
- `agent-task-issue.yml`: Telegram-Notification bei Gate-Requests
- `agent-gate-decision.yml`: Telegram-Push wenn `/approve` oder `/reject` via Issue-Kommentar

### Phase 4: orchestrator_mcp v3.3 + Dokumentation

- `server.py` v3.3: `agent_memory_search`, `agent_memory_upsert`, `agent_memory_context` registrieren
- `AGENT_HANDOVER.md`: Telegram-Befehle dokumentieren
- `AGENT_MEMORY.md`: Migration via `migrate_from_md.py` ausführen
- `pyproject.toml`: `python-telegram-bot>=21.0`, `tenacity>=8.0`, `psycopg[binary]>=3.1` ergänzen

---

## Technische Dependencies

```toml
# orchestrator_mcp/pyproject.toml — dependencies Ergänzungen
"psycopg[binary]>=3.1.0",   # psycopg3 (Upgrade von psycopg2-binary)
"pgvector>=0.3.0",           # pgvector Python Client (SQL Helper)
"openai>=1.0.0",             # Embeddings API (text-embedding-3-small)
"python-telegram-bot>=21.0", # Telegram Bot Framework (async)
"tenacity>=8.0.0",           # Retry-Logik für GitHub API Calls
"httpx>=0.27.0",             # Async HTTP für /health Command
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
- **Semantisches Retrieval**: Agent findet relevante Memories anhand von Bedeutung, nicht Stichwörtern
- **Temporal Decay**: Alte Entries degradieren graduell statt abrupt zu verschwinden
- **Mobile-first**: Voller Agent-Zugriff vom iPhone/iPad — ohne GitHub App erforderlich
- **Gate-Decisions in Sekunden**: `/approve 42` statt Issue-Comment auf GitHub
- **Kein neuer Server**: Telegram Bot läuft als Container auf hetzner-prod

### Negativ / Risiken
- **Embedding Kosten**: OpenAI Embeddings nur bei Content-Änderung (content_hash Cache) — effektiv nahe $0 im Normalbetrieb
- **pgvector Installation**: Einmalig auf hetzner-prod, einfacher Server-Umbau
- **Telegram-Abhängigkeit**: Single Point of Mobile Access — bei Bot-Ausfall GitHub Mobile als Fallback
- **Kein Offline-Betrieb**: pgvector benötigt DB-Verbindung (AGENT_MEMORY.md als Fallback)

### Nicht betroffen
- Bestehende ADR-112 Skills (`base.py`, `__init__.py`, `repo_scan.py`) bleiben erhalten
- GitHub Actions Workflows bleiben der Execution-Motor
- Windsurf Cascade als primäre IDE-Schnittstelle bleibt unverändert
- Gate-System ADR-107 bleibt — Telegram ist nur zusätzlicher Input-Kanal

---

## Rollback-Plan

1. `AGENT_MEMORY.md` bleibt als Fallback — Migration-Script ist reversibel
2. Telegram Bot: `docker stop telegram-bot` — alle anderen Services unberührt
3. pgvector Queries: Feature-Flag `SKILL_MEMORY_BACKEND=markdown|pgvector` (default: `pgvector`)

---

## Entschiedene Fragen (waren offen in v1/v2)

- ✅ `half_life_days` Defaults per `entry_type`: siehe Tabelle in Komponente 1
- ✅ Migration: automatisiert via `migrate_from_md.py` (idempotent, `--dry-run`)
- ✅ Stack: SQLAlchemy Core + psycopg3 direkt — kein Django ORM
- ✅ Vektor-Index: HNSW (nicht ivfflat) für <100k Entries
- ✅ GC-Strategie: Soft-Delete via `is_active=FALSE` (decay_factor < 0.05)
- ✅ tenant_id: INTEGER DEFAULT 1 im Schema (iilgmbh=1, Multi-Tenant ab Phase 2)
- ✅ Embedding-Provider: **OpenAI `text-embedding-3-small`** (1536 dims)
  — `OPENAI_API_KEY` bereits vorhanden (aifw Package), kein zusätzlicher Service nötig
- ✅ Telegram-Zugang: Einzelperson (`TELEGRAM_ALLOWED_USER_IDS` — komma-separierte IDs)

## Offene Fragen

keine — alle Entscheidungen getroffen.

---

## Verwandte ADRs

- ADR-107: Extended Agent Team + Deployment Agent
- ADR-108: Orchestrator MCP Server
- ADR-112: Agent Skill Registry + Persistent Context Store (wird migriert)
- ADR-062: Central Billing Service (billing-hub Postgres-Architektur als Referenz)
