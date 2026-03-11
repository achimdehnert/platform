---
status: accepted
date: 2026-03-08
updated: 2026-03-11
decision-makers: Achim Dehnert
consulted: Cascade
implementation_status: implemented
implementation_evidence:
  - "mcp-hub/discord/: Discord bot with 9 slash commands live"
---

# ADR-114: Discord als verlängertes Cascade IDE

## Status

Accepted — v2.2 (2026-03-11, Phasen 4-7 implementiert)

**Repos:** mcp-hub, platform
**Related:** ADR-113 (Discord Bot), ADR-101 (MCP Platform), ADR-107 (Agent Team), ADR-112 (Skill Registry), ADR-118 (HMAC Auth)

## Context

Die Cascade IDE (Windsurf) ist die leistungsfähigste Schnittstelle zur KI-Assistenz —
voller Codebase-Zugriff, MCP-Tool-Ausführung (SSH, Docker, GitHub, DB, DNS), langer
Kontext und Memory. **Aber sie läuft nur am Desktop.**

**Vision:** Discord wird das **verlängerte IDE** — von überall, jederzeit, mobil.
Nicht nur Notifications empfangen, sondern **mit Cascade chatten und Aktionen ausführen**.

### Capability-Vergleich: Ist vs. Soll

| Fähigkeit | Cascade IDE | Discord v1.0 (Ist) | Discord v2.0 (Soll) |
|---|---|---|---|
| Codebase lesen | ✅ vollständig | ❌ | ⚠️ via `/code` (Snippet-View) |
| Codebase schreiben | ✅ | ❌ | ❌ (nur über Layer 3 Escalation) |
| MCP-Tools ausführen | ✅ 13 Tools, 133 Actions | ❌ | ✅ via LLM Function Calling |
| LLM-Chat mit Kontext | ✅ | ❌ | ✅ `/chat` mit ADRs + Memory |
| Echtzeit-Antwort | ✅ | ❌ (Minuten via GitHub) | ✅ (< 10s via Layer 2) |
| Conversation History | ✅ Session-basiert | ❌ stateless | ✅ Thread-basiert + pgvector |
| Memory (pgvector) | ✅ | ✅ `/memory` | ✅ |
| Mobil / Asynchron | ❌ Desktop-only | ✅ | ✅ |
| Proaktive Kommunikation | ❌ | ✅ `discord_notify` | ✅ |
| Deploy / Infra-Steuerung | ✅ | ⚠️ nur `/deploy` | ✅ `/run` + LLM-Tools |

### Entscheidungstreiber

1. **Mobile IDE-Erfahrung** — Architektur-Fragen, Deployments, Infra-Status von unterwegs
2. **Echtzeit-Chat** — Antworten in Sekunden, nicht Minuten/Stunden
3. **Tool-Zugriff** — MCP-Tools direkt von Discord aus (der IDE-Kern!)
4. **Bidirektional** — Cascade meldet sich proaktiv, User antwortet in Discord
5. **Kein proprietärer Client** — Discord App (iOS/Android/Desktop) reicht

## Decision: 5-Layer Bidirektionale Architektur

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 4 — MCP-Proxy (Tool-Ausführung)                    🔜    │
│  Discord /run → orchestrator_mcp → MCP-Tools                    │
│  deploy_check, docker_manage, git_manage, ssh_manage            │
│  Latenz: 1-10s. Guards: Role-basiert + Approval für destruktiv  │
└─────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 3 — Cascade Bridge (Escalation für komplexe Tasks) ✅    │
│  Discord /ask → GitHub Issue → Cascade in Windsurf → Discord    │
│  Latenz: Minuten. Für Tasks die vollen Codebase-Zugriff brauchen│
└─────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 2 — LLM Chat + Function Calling (PRIMARY PATH)   🔴    │
│  Discord /chat → GPT-4o + Platform-Kontext + MCP-Tool-Calls    │
│  Latenz: 3-15s. Chat mit Kontext, kann Tools aufrufen           │
└─────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 1 — Quick Actions (sofort, kein LLM)               ✅    │
│  /task /approve /reject /deploy /health /status /memory         │
│  Latenz: <1s. Direkte Aktion                                    │
└─────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 0 — Cascade → Discord (proaktiv)                   ✅    │
│  discord_notify MCP Tool — Cascade schreibt aktiv in Discord    │
│  Task-Abschluss, Gate-Fragen, Deploy-Ergebnisse                 │
└─────────────────────────────────────────────────────────────────┘
```

**Primärpfad für "IDE-Chat": Layer 2** — GPT-4o mit Platform-Kontext und Function Calling.
Das LLM entscheidet selbst ob es ein MCP-Tool braucht — **genau wie Cascade in der IDE**.

### Layer 2 vs. Layer 4: Abgrenzung

| Aspekt | Layer 2 (LLM Chat) | Layer 4 (MCP-Proxy `/run`) |
|---|---|---|
| Wer wählt das Tool? | **LLM** entscheidet autonom | **User** spezifiziert explizit |
| Use Case | Natürlicher Chat: "Wie geht's risk-hub?" | Power-User: `/run docker ps risk-hub` |
| Latenz | 3-15s (LLM-Roundtrip) | 1-5s (direkt) |
| Kosten | Token-Verbrauch | Kein LLM nötig |

### Warum Layer 2 der Schlüssel ist

```
User in Discord:  "Wie ist der Health-Status von risk-hub?"

Layer 2 LLM denkt: "Ich brauche deploy_check health risk-hub"
                  → Ruft MCP-Tool auf via Function Calling
                  → Bekommt Ergebnis: "risk-hub: healthy, 3 Container, uptime 14d"
                  → Formatiert Antwort mit Kontext

Discord zeigt:    "✅ risk-hub ist healthy (3 Container, uptime 14 Tage).
                   Letztes Deploy: v1.4.2 vor 3 Tagen."
```

Ohne Layer 2 müsste der User `/health risk-hub` tippen und rohes JSON lesen.
**Mit Layer 2 chattet der User natürlich** — das LLM wählt die Tools.

## Implementierungsstand

### Layer 0 — Cascade → Discord ✅

`discord_notify` MCP Tool in `orchestrator_mcp/server.py`:

```python
discord_notify(
    message="PR erstellt, bitte reviewen.",
    title="✅ Task abgeschlossen",
    level="success",          # info | success | warning | error
    issue_url="https://..."   # optional
)
```

Cascade nutzt dieses Tool eigenständig für:
- Task-Abschluss melden
- Gate-Entscheidungen anfragen
- Deploy-Ergebnisse kommunizieren
- Fragen stellen ohne Desktop-Bindung

### Layer 1 — Quick Actions ✅

Slash Commands (`windsurf-bot` auf hetzner-prod, Guild-only Sync):

| Command | Funktion | Role Guard |
|---|---|---|
| `/health` | Platform Health-Check (alle Layer) | alle |
| `/status` | Offene cascade-task Issues | alle |
| `/memory` | pgvector Semantic Search | alle |
| `/task` | GitHub Actions Workflow starten | developer+ |
| `/deploy` | Service deployen | devops+ |
| `/approve` / `/reject` | Gate-Entscheidungen (ADR-107) | devops+ |
| `/ask` | GitHub Issue Bridge → Cascade | developer+ |
| `/chat` | LLM Gateway (Layer 2) | developer+ |

**Security:** Role Guards (`guards.py`), Token-Bucket Rate Limiter (`rate_limit.py`),
Audit-Log in `#log` Channel.

### Layer 2 — LLM Chat + Function Calling ✅ (Code), ⚠️ (Deploy)

`/chat` Handler in `handlers.py` vollständig implementiert:
- `interaction.defer()` für 3s-Timeout-Bypass ✅
- `build_system_prompt()` mit ADR-Context + pgvector ✅
- Thread-Unterstützung (`thread: bool = False`) ✅
- Chunked Embeds für lange Antworten ✅
- Error-Handling (Timeout, ConnectError, HTTPError) ✅
- **Function Calling** (`enable_tools=True`) ✅
- **Conversation History** via Thread-ID (In-Memory, TTL 1h) ✅
- `context_builder.py` Stack-Info aktualisiert (Django 5.x, Python 3.12) ✅

**5 Tools für LLM Function Calling** (`llm_mcp_service/tools.py`):
- `check_app_health` — /healthz/ + /livez/ für 12 Platform-Apps
- `list_open_issues` — GitHub Issues mit Label-Filter
- `get_file_content` — Code aus GitHub-Repos anzeigen
- `list_repo_structure` — Verzeichnisstruktur
- `search_memory` — pgvector Semantic Search

**Fehlend:** `llm_mcp` Container auf hetzner-prod deployen (docker compose up)

### Layer 3 — Cascade Bridge ✅

```
Discord /ask "Review ADR-120 und fixe die BLOCKs"
    → GitHub Issue #42 mit Label cascade-task
    → Cascade sieht Issue in Windsurf (manuell oder automatisiert)
    → Cascade führt Task aus (voller Codebase-Zugriff!)
    → Issue-Kommentar mit Ergebnis
    → cascade-answer-notify.yml → Discord Notification
```

**Label `cascade-task` in 18 Django-Hub-Repos (ADR-120):** mcp-hub, bfagent,
risk-hub, coach-hub, billing-hub, pptx-hub, trading-hub, travel-beat, weltenhub,
cad-hub, wedding-hub, dev-hub, nl2cad, illustration-hub, 137-hub, writing-hub,
research-hub, ausschreibungs-hub

**Wann Layer 3 statt Layer 2:**
- Task braucht Code-Änderungen (Dateien erstellen/editieren)
- Task braucht mehrere Schritte über verschiedene Repos
- Task braucht IDE-spezifische Features (Debugging, Tests laufen lassen)

### Layer 4 — MCP-Proxy ✅ (Code)

`/run` Meta-Command implementiert:

```
/run deploy-check health risk-hub     → deploy_check(action="health", repo="risk-hub")
/run docker ps risk-hub               → docker_manage(action="compose_ps", app="risk-hub")
/run git status bfagent               → git_manage(action="status", repo="bfagent")
/run health-dashboard                 → system_manage(action="health_dashboard")
```

**Security-Konzept:**

| Tool-Kategorie | Erlaubte Rollen | Approval nötig? |
|---|---|---|
| Lesend (status, ps, health, log) | developer+ | Nein |
| Deploy (compose_up, restart) | devops+ | Nein |
| Destruktiv (compose_down, drop, delete) | platform-admin | ✅ Discord Button |
| SSH exec | platform-admin | ✅ Discord Button |

Destruktive Aktionen zeigen einen Embed mit Buttons:
```
⚠️ Destruktive Aktion: docker compose down risk-hub
[✅ Bestätigen] [❌ Abbrechen]  (30s Timeout)
```

## Discord Server Struktur

```
iilgmbh-agent Server
├── #cascade-chat   ← /chat (Layer 2 — Primärkanal für IDE-Chat)
├── #agent-tasks    ← /ask Antworten + cascade-task Notifications
├── #deployments    ← /deploy, /approve, /reject, /run deploy-*
├── #health         ← /health, automatische Alerts, /run health-*
├── #infra          ← /run docker/git/ssh (Layer 4)
└── #log            ← Audit Trail aller Commands + Tool-Calls
```

## Ehrliche Qualitätsbewertung

**Was nie Discord-IDE erreicht (und auch nicht muss):**
- Kein interaktives Debugging
- Kein Live-Codebase-Editing (dafür Layer 3 Escalation)
- Kein Diff-Viewer (zu komplex für Discord Embeds)
- Kein paralleles Tool-Calling wie in Windsurf

**Was Discord-IDE vollwertig kann (v2.0):**
- ✅ Architektur-Fragen, Planung, ADR-Entscheidungen (Layer 2 Chat)
- ✅ MCP-Tool-Ausführung: Health, Status, Logs, Deployments (Layer 2 + 4)
- 🔜 Code-Snippets anzeigen via GitHub API (Phase 7)
- ✅ Task-Erstellung und Gate-Entscheidungen (Layer 1)
- ✅ Proaktive Cascade-Kommunikation (Layer 0)
- ✅ Komplexe Tasks an Windsurf delegieren (Layer 3)
- ✅ Conversation History mit Thread-Kontext

**Qualitäts-Matrix:**

| Use Case | Cascade IDE | Discord v2.0 | Gap |
|---|---|---|---|
| "Wie deploye ich risk-hub?" | ✅ | ✅ Layer 2 | keins |
| "Zeig mir den Health-Status" | ✅ | ✅ Layer 2+4 | keins |
| "Fixe den Bug in services.py" | ✅ | ⚠️ Layer 3 (Minuten) | Latenz |
| "Erstelle ein neues ADR" | ✅ | ⚠️ Layer 3 (Minuten) | Latenz |
| "Starte risk-hub Container neu" | ✅ | ✅ Layer 4 | keins |
| "Reviewe den PR" | ✅ | ⚠️ Layer 3 | Latenz |

## Consequences

### Positiv

- **Echtes mobiles IDE** — Chatten + Aktionen von überall
- **Bidirektional** — Cascade meldet sich proaktiv, User antwortet
- **MCP-Tool-Zugriff** — 13 Tools, 133 Actions von Discord aus
- **Echtzeit** — Layer 2 antwortet in 3-15 Sekunden
- **Audit Trail** — Alle Commands + Tool-Calls im `#log` Channel
- **Kein proprietärer Client** — Discord App (iOS/Android/Desktop/Web)
- **Escalation-Path** — Komplexe Tasks automatisch an Windsurf delegieren

### Negativ / Risiken

- Layer 2 erfordert `llm_mcp` Deployment (FastAPI + GPU/API-Kosten)
- Function Calling erhöht LLM-Token-Verbrauch (~2x pro Tool-Call)
- Layer 3 Latenz bleibt (Cascade muss Windsurf aktiv haben)
- MCP-Proxy: destruktive Aktionen brauchen robustes Approval-System
- Discord API Rate Limits (50 Requests/Sekunde pro Bot)

### Mitigation

- **Token-Budget:** OpenRouter mit monatlichem Cap (Start: $25/Monat)
- **Rate Limiting:** Token-Bucket pro User + Command (`rate_limit.py`)
- **Approval-Flow:** Discord Buttons für destruktive Aktionen (30s Timeout)
- **Escalation:** Layer 2 erkennt "das braucht Code-Änderungen" → empfiehlt `/ask`
- **Stale-Bot:** cascade-task Issues ohne Antwort nach 24h → Discord Alert

## Implementierungsplan

| Phase | Inhalt | Aufwand | Status |
|-------|--------|---------|--------|
| 0 | Layer 0 + 1: Bot, Commands, Guards, Rate Limiter | 3d | ✅ Done |
| 1 | Layer 3: `/ask` → GitHub Issue → Cascade → Discord | 1d | ✅ Done |
| 2 | `discord_notify` MCP Tool (Cascade → Discord) | 0.5d | ✅ Done |
| 3 | `llm_mcp` FastAPI Service (Code) | 2d | ✅ Code done |
| 4 | Function Calling: 5 Tools + LLM-Loop (max 3 Runden) | 3d | ✅ Code done |
| 5 | Conversation History (Thread-ID, In-Memory, TTL 1h) | 1d | ✅ Code done |
| 6 | Layer 4: `/run` Meta-Command (health, issues, structure) | 2d | ✅ Code done |
| 7 | `/code` Command (GitHub API + Syntax-Highlighting) | 0.5d | ✅ Code done |

**Verbleibend:** Deploy auf hetzner-prod (`docker compose up`)
**Commit:** mcp-hub `491e90b` (2026-03-11)

## Betroffene Repos

- `mcp-hub` — Discord Bot, Handler, Guards, Rate Limiter, Context Builder, MCP-Proxy
- `platform` — ADR, Workflows (`cascade-answer-notify.yml`, `stale-cascade-inbox.yml`)
- `llm_mcp` (in mcp-hub) — FastAPI-Service für Layer 2

## Verwandte ADRs

- ADR-113: Discord Bot Gateway + pgvector Memory Store
- ADR-101: MCP Platform Konzept
- ADR-107: Extended Agent Team
- ADR-112: Agent Skill Registry + Persistent Context
- ADR-118: HMAC Auth (Vorbild für Inter-App Security)
- ADR-120: Unified Deployment Pipeline (Deploy-Steuerung via Discord)

## Review-History

| Datum | Version | Reviewer | Urteil | Link |
|-------|---------|----------|--------|------|
| 2026-03-08 | v1.0 | Cascade | ✅ initial accepted | [Review](../reviews/ADR-114-discord-ide-like-communication-gateway.md) |
| 2026-03-11 | v1.0 → v2.0 | Cascade | ❌ → Rewrite (4 BLOCKs: MADR-Frontmatter, Layer-3-Latenz, MCP-Tool-Zugriff, Stack-Info) | [Review](../reviews/ADR-114-review-2026-03-11.md) |
| 2026-03-11 | v2.0 → v2.1 | Cascade | ⚠️ → Fixes (Encoding, Repo-Liste 18 statt 11, Code-Snippets Status, Layer-Abgrenzung) | — |
| 2026-03-11 | v2.1 → v2.2 | Cascade | ✅ Phasen 4-7 implementiert (mcp-hub `491e90b`) | — |
