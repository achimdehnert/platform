# ADR-114: Discord als IDE-ähnliches Kommunikations-Gateway zu Cascade

**Status:** Proposed  
**Datum:** 2026-03-08  
**Autoren:** achim_73814 + Cascade  
**Kontext:** ADR-113 (Discord Bot Gateway), ADR-101 (MCP Platform), ADR-107 (Agent Team)

---

## Problemstellung

Die Cascade IDE (Windsurf) ist die leistungsfähigste Schnittstelle zur KI-Assistenz —
sie hat vollen Codebase-Zugriff, Tool-Ausführung, langen Kontext und Memory.
Aber sie läuft nur am Desktop.

**Ziel:** Eine mobile, asynchrone Kommunikationsschicht, die möglichst nah an die
IDE-Qualität herankommt — ohne Desktop-Bindung.

---

## Kontext: Was Cascade in der IDE kann, was Discord nicht kann

| Fähigkeit | Cascade IDE | Discord Bot (aktuell) |
|---|---|---|
| Codebase lesen/schreiben | ✅ vollständig | ❌ |
| Tools ausführen (SSH, Docker, GitHub) | ✅ | ❌ direkt |
| Langer Kontext (ganze Session) | ✅ | ❌ stateless |
| Memory (pgvector) | ✅ | ✅ via /memory |
| ADR-Kontext | ✅ automatisch | ⚠️ nur System-Prompt |
| Code ausführen + Ergebnis sehen | ✅ | ❌ |
| Asynchron / mobil | ❌ Desktop-only | ✅ |

---

## Entscheidung: 3-Layer Discord Gateway Architektur

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 3 — Cascade Bridge (höchste Qualität)                │
│  Discord /ask → GitHub Issue → Cascade antwortet → Discord  │
│  Latenz: Minuten. Qualität: IDE-nah (voller Kontext)        │
└─────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 2 — LLM Gateway (mittlere Qualität)                  │
│  Discord /chat → llm_mcp (GPT-4o + Platform-Kontext)        │
│  Latenz: Sekunden. Qualität: gut für Fragen/Planung         │
└─────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 1 — Steuerung (sofort)                               │
│  Discord /task /approve /reject /deploy /health /status     │
│  Latenz: <1s. Qualität: Aktion-Ausführung, kein LLM         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Layer-Details

### Layer 1 — Sofort-Steuerung (bereits implementiert ✅)

Slash Commands ohne LLM:
- `/task` — GitHub Actions Workflow starten
- `/approve` `/reject` — Gate-Entscheidungen
- `/deploy` — Deployment triggern
- `/health` — Server-Status
- `/status` — Offene Issues
- `/memory` — pgvector Suche

### Layer 2 — LLM Gateway (nächster Schritt)

Neuer Command `/chat` der `llm_mcp` auf hetzner-prod aufruft.

**System-Prompt enthält:**
- Alle ADRs als Kontext (via `platform-context` MCP)
- Repo-Struktur und aktueller Stand (aus pgvector Memory)
- Platform Stack (Django, HTMX, Docker, etc.)
- Bekannte offene Tasks (aus GitHub Issues)

**Implementierung:**
```
Discord /chat "Frage"
    → orchestrator_mcp/discord/handlers.py cmd_chat()
    → httpx POST llm_mcp/chat (hetzner-prod intern)
    → GPT-4o mit vollem Platform-Kontext
    → Antwort in Discord (< 5s)
```

**Erforderliche Komponenten:**
- `llm_mcp` REST-Endpoint `/chat` auf hetzner-prod
- Dynamischer System-Prompt aus ADR-Dateien + pgvector Memory
- Context-Window Management (neueste ADRs + relevante Memories)

### Layer 3 — Cascade Bridge (bereits implementiert ✅)

`/ask` Command → GitHub Issue `[cascade-task]` → Cascade antwortet in Windsurf →
`cascade-answer-notify.yml` Workflow → Discord Notification.

**Erweiterung (Phase 2):**
- MCP Tool `discord_notify` — Cascade kann direkt aus der IDE eine Discord
  Nachricht senden wenn ein Issue bearbeitet wird
- Bidirektionaler Thread: Discord Antwort → neuer Issue-Kommentar → Discord

---

## Geplante Discord Server Struktur

```
iilgmbh-agent Server
├── #agent-tasks        ← /ask Antworten, cascade-task Notifications
├── #deployments        ← /deploy, /approve, /reject, GitHub Actions
├── #health             ← /health, automatische Alerts
├── #chat               ← /chat (Layer 2 LLM Gateway)
└── #log                ← alle Events (Audit Trail)
```

---

## Implementierungsplan

### Phase 1 — Basis (DONE ✅)
- [x] Discord Bot mit 7 Slash Commands (`/task`, `/approve`, `/reject`,
      `/deploy`, `/health`, `/status`, `/memory`)
- [x] `/ask` → GitHub Issue → Cascade antwortet → Discord
- [x] `cascade-answer-notify.yml` Workflow
- [x] Label `cascade-task` in mcp-hub
- [x] Bot auf hetzner-prod deployed (windsurf-bot#3564)

### Phase 2 — LLM Gateway (nächste Session)
- [ ] `llm_mcp` REST-Endpoint `/v1/chat` mit dynamischem Platform-Kontext
- [ ] `/chat` Command im Discord Bot (< 5s Antwortzeit)
- [ ] System-Prompt: ADRs + pgvector Memory + offene Issues kombiniert
- [ ] Label `cascade-task` in allen Repos (bfagent, risk-hub, etc.)
- [ ] Separates Repo `cascade-inbox` für Discord-Tasks (kein Issue-Lärm)

### Phase 3 — Bidirektionaler Thread (Zukunft)
- [ ] MCP Tool `discord_notify` in orchestrator_mcp
- [ ] Discord Thread pro Issue (Konversations-History bleibt erhalten)
- [ ] Kontext-Persistenz: Discord Thread ID in pgvector gespeichert
- [ ] `/ask` Antworten direkt im selben Discord Thread

### Phase 4 — Discord Activity (Langfristig)
- [ ] Discord Embedded App mit Live-Preview von Deployments
- [ ] Diff-Viewer für PRs direkt in Discord
- [ ] Agent-Status Board (welcher Agent arbeitet gerade woran)

---

## Ehrliche Bewertung der Qualitätsgrenzen

**Was nie IDE-Qualität erreicht:**
- Kein direkter Dateizugriff ohne expliziten Tool-Call
- Kein Live-Codebase-Kontext (nur was in Memory/ADRs dokumentiert ist)
- Kein interaktives Debugging

**Was annähernd IDE-Qualität erreicht (mit Layer 2+3):**
- Architektur-Fragen, nächste Schritte, ADR-Entscheidungen → **gut**
- Task-Erstellung und Gate-Entscheidungen → **vollwertig**
- Deployment-Steuerung → **vollwertig**
- Planung neuer Features → **gut** (mit Platform-Kontext)

---

## Konsequenzen

**Positiv:**
- Volle mobile Steuerung der Plattform von überall
- Asynchrone Zusammenarbeit Mensch ↔ Cascade
- Vollständiger Audit Trail via GitHub Issues
- Kein proprietärer Client nötig — Discord App genügt

**Risiken:**
- Layer 2 erfordert `llm_mcp` REST-Endpoint (noch nicht gebaut)
- Latenz bei Layer 3 (Cascade muss am Desktop aktiv sein)
- GitHub Issues als Kommunikationskanal → Lärm im Issue-Tracker

**Mitigation:**
- `cascade-inbox` Repo nur für Discord-Tasks
- `llm_mcp` als leichtgewichtiger FastAPI-Service (< 100 LOC)
- Layer 3 nur für komplexe Tasks, Layer 2 für schnelle Fragen

---

## Verwandte ADRs

- ADR-113: Discord Bot Gateway + pgvector Memory Store
- ADR-101: MCP Platform Konzept
- ADR-107: Extended Agent Team
- ADR-112: Agent Skill Registry + Persistent Context
