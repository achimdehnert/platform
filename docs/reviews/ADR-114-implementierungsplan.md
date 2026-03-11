# ADR-114 Implementierungsplan — Produktionsreif

**Version:** 1.0  
**Datum:** 2026-03-08  
**Scope:** Layer 2 LLM Gateway + Security-Hardening für Layer 1+3

---

## Dateibaum — Vollständig

```
orchestrator_mcp/
├── discord/
│   ├── __init__.py
│   ├── bot.py                    # Bot-Init, Command-Tree, Startup
│   ├── guards.py                 # Role-based Access Control   [NEU]
│   ├── rate_limit.py             # Token-Bucket Rate Limiter   [NEU]
│   ├── utils.py                  # Chunker, Embeds, Formatierung [NEU]
│   ├── handlers.py               # Slash Command Handler       [ERWEITERT]
│   └── context_builder.py        # System-Prompt Builder       [NEU]
│
llm_mcp/                          # Neuer FastAPI Microservice (Option A)
├── Dockerfile
├── pyproject.toml
├── llm_mcp/
│   ├── __init__.py
│   ├── main.py                   # FastAPI App
│   ├── routers/
│   │   └── chat.py               # POST /v1/chat
│   ├── services/
│   │   ├── context_service.py    # ADR-Loader + pgvector
│   │   ├── llm_service.py        # OpenRouter Client
│   │   └── prompt_service.py     # System-Prompt Builder
│   ├── models/
│   │   └── schemas.py            # Pydantic Models
│   └── core/
│       ├── config.py             # Settings (pydantic-settings)
│       ├── security.py           # API-Key Auth
│       └── logging.py            # structlog Setup
│
# OPTION B (empfohlen): Celery statt FastAPI
platform_context/                 # Bestehender MCP-Service
└── tasks/
    └── llm_chat.py               # Celery Task für LLM-Chat     [NEU]
│
.github/workflows/
└── cascade-answer-notify.yml     # [ERWEITERT: Timeout + Stale]
│
docker-compose.prod.yml           # [ERWEITERT: llm_mcp Service]
```

---

## Phase 1 — Security-Hardening (1-2 Tage) 🔴 JETZT

**Ziel:** BLOCKER und KRITISCH aus Review beheben, bevor Layer 2 gebaut wird.

### 1.1 Role Guards aktivieren

```bash
# Discord Server: Rollen anlegen
# platform-admin | devops | developer
# Bestehende Nutzer zuordnen
```

Datei: `orchestrator_mcp/discord/guards.py` — siehe Review-Dokument  
Datei: `orchestrator_mcp/discord/handlers.py` — Decorators hinzufügen

### 1.2 Rate Limiter

Datei: `orchestrator_mcp/discord/rate_limit.py` — Token-Bucket  
Integration in alle `/chat`- und `/ask`-Handler.

### 1.3 Health-Check erweitern

`/health` prüft zusätzlich:
- `llm_mcp` Endpoint erreichbar (wenn Phase 2 deployed)
- pgvector Connection
- GitHub API erreichbar

### 1.4 Cascade-Inbox Stale-Bot

`.github/workflows/stale-cascade-inbox.yml`:
- Issues mit `cascade-task` Label + 24h ohne Antwort → Discord Notification
- Nach 72h → Issue automatisch schließen mit Kommentar

---

## Phase 2 — LLM Gateway (3-5 Tage) 🟡 NÄCHSTE SESSION

**Ziel:** `/chat` Command mit vollem Platform-Kontext.

### Entscheidung: Option A oder B

#### Option A: `llm_mcp` FastAPI Service (ADR-Vorschlag)

**Wähle wenn:**
- Layer 2 soll später multi-tenant werden
- Separate API-Keys pro Tenant geplant
- Team will klare Service-Boundary

**Deploy:** Hetzner VPS, eigener Docker-Container, Port 8001 (intern)

#### Option B: Celery Task (Empfehlung)

**Wähle wenn:**
- Bestehende Worker-Infra nutzen (kein neuer Service)
- Einfacher Betrieb, weniger Moving Parts
- Flower-Monitoring bereits vorhanden

**Deploy:** Bestehende Celery Worker, Result-Backend Redis

### 2.1 Context Builder (beide Optionen)

`orchestrator_mcp/discord/context_builder.py`:
- Lädt ADRs aus Filesystem (gecacht, 5min TTL)
- **Filtert Credentials heraus** (Regex auf KEY=, TOKEN=, PASSWORD=)
- pgvector Similarity-Search für relevante Memories
- Token-Budget: max 6000 Tokens für Kontext (GPT-4o: 128k, aber Kosten!)
- Priorität: Neueste ADRs > Relevante Memories > Alte ADRs

### 2.2 Conversation History (pgvector)

Discord Thread ID als Foreign Key in pgvector gespeichert:
```sql
-- In bestehender Memory-Tabelle:
ALTER TABLE discord_memory ADD COLUMN thread_id VARCHAR(20);
ALTER TABLE discord_memory ADD COLUMN user_discord_id VARCHAR(20);
CREATE INDEX idx_discord_memory_thread ON discord_memory(thread_id);
```

### 2.3 `/chat` Command

```
Discord /chat "Wie implementiere ich den QuickCheck-Wizard?"
    → Rate-Limit-Check (B3-Fix)
    → Role-Check (B1-Fix)
    → interaction.defer() (3s Timeout-Bypass)
    → Context Builder: ADRs + pgvector relevante Memories
    → LLM Call (GPT-4o via OpenRouter)
    → Conversation in pgvector speichern (thread_id)
    → send_chunked() mit Discord Embed (B4-Fix)
    → Audit Log
```

---

## Phase 3 — Bidirektionaler Thread (1-2 Wochen)

**Ziel:** Echte Konversation Discord ↔ Cascade.

### 3.1 MCP Tool `discord_notify`

Cascade kann direkt aus der IDE Discord-Messages senden:

```python
# In mcp-hub oder orchestrator_mcp
@mcp.tool()
async def discord_notify(
    channel: str,
    message: str,
    thread_id: str | None = None,
    embed_title: str | None = None,
) -> str:
    """Sendet eine Nachricht in den Discord-Channel."""
    webhook_url = settings.DISCORD_WEBHOOKS[channel]
    payload = build_webhook_payload(message, thread_id, embed_title)
    async with httpx.AsyncClient() as client:
        r = await client.post(webhook_url, json=payload)
    r.raise_for_status()
    return f"Sent to #{channel}"
```

### 3.2 Thread-Persistenz

Discord Thread ID → pgvector:
- `/ask` erstellt GitHub Issue + Discord Thread
- Issue-Nummer ↔ Thread-ID in pgvector verknüpft
- Cascade antwortet → `discord_notify` → gleicher Thread

---

## Phase 4 — IDE App (Langfristig, Low Priority)

Kein Implementierungsplan hier — technisch möglich via Discord Embedded App,
aber Discord-Policy-Änderungen machen das riskant. Review in Q3 2026.

---

## Migrations-Checkliste

```
[ ] Discord Server: Rollen anlegen (platform-admin, devops, developer)
[ ] Discord Bot: Role Guards für alle Commands aktivieren
[ ] Rate Limiter: In alle Handler integriert und getestet
[ ] GitHub: cascade-inbox Repo angelegt
[ ] GitHub: stale-cascade-inbox.yml Workflow aktiv
[ ] llm_mcp ODER Celery Task: deployed und health-geprüft
[ ] pgvector: thread_id Spalte migriert
[ ] /chat: Ende-zu-Ende Test mit echtem Discord-User
[ ] Audit Log: Alle Commands in #log Channel
[ ] Monitoring: Flower / Health-Endpoint zeigt Layer 2 Status
```

---

## Kostenabschätzung Layer 2 (GPT-4o)

| Szenario | Anfragen/Tag | Tokens/Anfrage | Kosten/Monat |
|----------|-------------|----------------|--------------|
| Light (1 User) | 20 | 8.000 | ~$5 |
| Medium (5 User) | 100 | 8.000 | ~$24 |
| Heavy (10 User) | 500 | 8.000 | ~$120 |

**Empfehlung:** Rate-Limit + monatliches Token-Budget-Cap via OpenRouter.
