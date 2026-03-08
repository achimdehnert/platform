# ADR-114: Discord als IDE-ähnliches Kommunikations-Gateway zu Cascade

**Status:** Accepted  
**Datum:** 2026-03-09  
**Autoren:** achim_73814 + Cascade  
**Kontext:** ADR-113 (Discord Bot Gateway), ADR-101 (MCP Platform), ADR-107 (Agent Team)

---

## Problemstellung

Die Cascade IDE (Windsurf) ist die leistungsfähigste Schnittstelle zur KI-Assistenz —
sie hat vollen Codebase-Zugriff, Tool-Ausführung, langen Kontext und Memory.
Aber sie läuft nur am Desktop.

**Ziel:** Eine mobile, asynchrone, bidirektionale Kommunikationsschicht, die möglichst
nah an die IDE-Qualität herankommt — ohne Desktop-Bindung.

---

## Kontext: Capability-Vergleich

| Fähigkeit | Cascade IDE | Discord Bot |
|---|---|---|
| Codebase lesen/schreiben | ✅ vollständig | ❌ |
| Tools ausführen (SSH, Docker, GitHub) | ✅ | ❌ direkt |
| Langer Kontext (ganze Session) | ✅ | ❌ stateless |
| Memory (pgvector) | ✅ | ✅ via `/memory` |
| ADR-Kontext | ✅ automatisch | ✅ via `context_builder` (Layer 2) |
| Code ausführen + Ergebnis sehen | ✅ | ❌ |
| Asynchron / mobil | ❌ Desktop-only | ✅ |
| Cascade schreibt aktiv | ❌ | ✅ via `discord_notify` MCP Tool |

---

## Entscheidung: 3-Layer Bidirektionale Architektur

```
┌─────────────────────────────────────────────────────────────┐
│  LAYER 3 — Cascade Bridge (höchste Qualität)          ✅    │
│  Discord /ask → GitHub Issue → Cascade → Discord Notify     │
│  Latenz: Minuten. Qualität: IDE-nah (voller Kontext)        │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│  LAYER 2 — LLM Gateway (mittlere Qualität)            ✅    │
│  Discord /chat → llm_mcp (GPT-4o + Platform-Kontext)        │
│  Latenz: Sekunden. Qualität: gut für Fragen/Planung         │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│  LAYER 1 — Sofort-Steuerung                           ✅    │
│  Discord /task /approve /reject /deploy /health /status     │
│  Latenz: <1s. Kein LLM — direkte Aktion                     │
└─────────────────────────────────────────────────────────────┘

IDE → Discord: discord_notify MCP Tool (direkt aus Windsurf) ✅
```

Der Kanal ist **bidirektional**: Discord sendet Tasks an Cascade,
Cascade schreibt aktiv in Discord — ohne auf User-Input zu warten.

---

## Security-Architektur (ADR-114 Review — alle BLOCKER behoben)

### B1 — Role-based Access Control ✅
`orchestrator_mcp/discord/guards.py` — `@require_role` Decorator:

| Command | Erforderliche Rollen |
|---|---|
| `/deploy` `/approve` `/reject` | `platform-admin`, `devops` |
| `/task` `/chat` `/ask` | `platform-admin`, `devops`, `developer` |
| `/health` `/status` `/memory` | alle |

### B2 — Async-safe HTTP ✅
Alle Handler: `httpx.AsyncClient` mit `await` — kein `asyncio.run()`.
`interaction.response.defer()` umgeht Discord 3s Timeout.

### B3 — Token-Bucket Rate Limiter ✅
`orchestrator_mcp/discord/rate_limit.py` — `@rate_limit` Decorator:

| Command | Burst | Refill |
|---|---|---|
| `/chat` | 5 | 1 alle 2s |
| `/ask` | 3 | 1 alle 5s |
| `/deploy` | 2 | 1 alle 10s |

### B4 — Discord Message Chunking ✅
`orchestrator_mcp/discord/utils.py` — `send_chunked()` + `build_llm_embed()`:
Splittet bei 4000 Zeichen (Embed-Limit), nie mitten in einer Zeile.

### K1 — Secrets-Filter im System-Prompt ✅
`orchestrator_mcp/discord/context_builder.py` — `_filter_secrets()`:
Entfernt API Keys, Tokens, IPs, SSH-Keys aus ADR-Inhalten vor LLM-Übermittlung.

### K3 — Stale-Bot ✅
`.github/workflows/cascade-inbox-stale.yml`:
- 24h ohne Antwort → Label `stale` + Discord Warning
- 72h ohne Antwort → Auto-Close mit Kommentar

---

## Layer 2 — LLM Gateway: Implementierung

```
Discord /chat "Frage"
    → @require_role("chat") + @rate_limit("chat")
    → interaction.response.defer()
    → context_builder.build_system_prompt()
      (ADRs gecacht 5min + pgvector Similarity + offene Issues)
    → httpx POST llm_mcp:8001/v1/chat
      (Bearer: LLM_MCP_API_KEY, X-Correlation-ID)
    → GPT-4o via OpenRouter
    → build_llm_embed() mit Chunking
    → Discord (optional: Thread)
    → _audit_log() in #log Channel
```

**Neuer Microservice `llm_mcp`:**
- `llm_mcp/main.py` — FastAPI + structlog + OpenRouter Client
- `llm_mcp/Dockerfile` — python:3.12-slim, non-root User
- `docker-compose.llm-mcp.yml` — internes Netz, kein Traefik-Expose
- Volume: `/opt/platform/adrs:/app/adrs:ro`

**Noch ausstehend für Live-Betrieb:**
```bash
# .env.llm_mcp anlegen auf hetzner-prod:
LLM_MCP_API_KEY=<zufälliger interner key>
LLM_MCP_OPENROUTER_API_KEY=<openrouter key>

# Deployen:
docker compose -f docker-compose.prod.yml -f docker-compose.llm-mcp.yml up -d
```

---

## Discord Server Struktur

```
iilgmbh-agent Server
├── #agent-tasks    ← /ask Antworten + cascade-task Notifications
├── #deployments    ← /deploy, /approve, /reject, GitHub Actions
├── #health         ← /health, automatische Alerts
├── #chat           ← /chat (Layer 2 LLM Gateway)
└── #log            ← Audit Trail aller Commands
```

Discord Rollen anlegen: `platform-admin`, `devops`, `developer`

---

## Implementierungsstand

### Phase 1 — Basis ✅
- [x] Discord Bot mit 9 Slash Commands (windsurf-bot#3564, hetzner-prod)
- [x] `/ask` → GitHub Issue → Cascade → cascade-answer-notify Workflow
- [x] Label `cascade-task` in 11 Repos
- [x] `discord_notify` MCP Tool (IDE → Discord direkt)
- [x] `.windsurf/workflows/discord-notify.md`

### Phase 2 — Security Hardening + LLM Gateway ✅
- [x] `guards.py` — Role-based Access Control (B1)
- [x] `rate_limit.py` — Token-Bucket Rate Limiter (B3)
- [x] `utils.py` — Message Chunker + strukturierte Embeds (B4)
- [x] `context_builder.py` — ADR-Loader + Secrets-Filter (K1)
- [x] `handlers.py` — vollständig async, alle BLOCKER behoben (B2)
- [x] `llm_mcp/main.py` — FastAPI LLM Gateway Service
- [x] `cascade-inbox-stale.yml` — 24h/72h Stale-Bot (K3)
- [x] Tests: `tests/test_llm_mcp.py` (14 Tests)

### Phase 3 — llm_mcp Live-Betrieb 🔜
- [ ] `.env.llm_mcp` auf hetzner-prod setzen
- [ ] `docker compose ... -f docker-compose.llm-mcp.yml up -d`
- [ ] Discord Rollen `platform-admin`, `devops`, `developer` anlegen
- [ ] `/chat` Ende-zu-Ende testen
- [ ] ORCHESTRATOR_MCP_DISCORD_LLM_MCP_API_KEY in GitHub Secrets

### Phase 4 — Bidirektionaler Thread (Zukunft)
- [ ] Discord Thread ID in pgvector gespeichert
- [ ] `/ask` Antworten im selben Thread
- [ ] Conversation History für `/chat`

---

## Kostenabschätzung Layer 2

| Szenario | Anfragen/Tag | Tokens/Anfrage | Kosten/Monat |
|---|---|---|---|
| Light (1 User) | 20 | 8.000 | ~$5 |
| Medium (5 User) | 100 | 8.000 | ~$24 |
| Heavy (10 User) | 500 | 8.000 | ~$120 |

**Schutz:** Rate-Limit + monatliches Token-Budget-Cap via OpenRouter.

---

## Ehrliche Qualitätsbewertung

**Was nie IDE-Qualität erreicht:**
- Kein direkter Dateizugriff ohne expliziten Tool-Call
- Kein Live-Codebase-Kontext (nur was in Memory/ADRs steht)
- Kein interaktives Debugging

**Was annähernd IDE-Qualität erreicht:**
- Architektur-Fragen, nächste Schritte, ADR-Entscheidungen → **gut** (Layer 2)
- Task-Erstellung und Gate-Entscheidungen → **vollwertig** (Layer 1+3)
- Deployment-Steuerung → **vollwertig** (Layer 1)
- Cascade-initiated Kommunikation → **vollwertig** (`discord_notify`)

---

## Konsequenzen

**Positiv:**
- Vollständige mobile Plattform-Steuerung von überall
- Bidirektionale asynchrone Zusammenarbeit Mensch ↔ Cascade
- Vollständiger Audit Trail in `#log` Channel
- Produktionsreife Security: RBAC + Rate-Limit + Secret-Filter

**Risiken:**
- `llm_mcp` erfordert OpenRouter API Key + manuelles Deployment
- Layer 3: Cascade muss Windsurf aktiv haben um Issues zu sehen
- Discord Rollen müssen manuell angelegt werden

**Mitigation:**
- `llm_mcp` fällt graceful zurück: ConnectError → "nutze /ask für Cascade"
- Stale-Bot schließt unbearbeitete Issues nach 72h

---

## Verwandte ADRs

- ADR-113: Discord Bot Gateway + pgvector Memory Store
- ADR-101: MCP Platform Konzept
- ADR-107: Extended Agent Team
- ADR-112: Agent Skill Registry + Persistent Context
