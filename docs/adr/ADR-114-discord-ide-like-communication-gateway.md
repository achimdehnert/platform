# ADR-114: Discord als IDE-ähnliches Kommunikations-Gateway zu Cascade

**Status:** Accepted  
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

## Kontext: Capability-Vergleich

| Fähigkeit | Cascade IDE | Discord Bot |
|---|---|---|
| Codebase lesen/schreiben | ✅ vollständig | ❌ |
| Tools ausführen (SSH, Docker, GitHub) | ✅ | ❌ direkt |
| Langer Kontext (ganze Session) | ✅ | ❌ stateless |
| Memory (pgvector) | ✅ | ✅ via `/memory` |
| ADR-Kontext | ✅ automatisch | ⚠️ nur System-Prompt |
| Code ausführen + Ergebnis sehen | ✅ | ❌ |
| Asynchron / mobil | ❌ Desktop-only | ✅ |
| Cascade kann aktiv schreiben | ❌ | ✅ via `discord_notify` |

---

## Entscheidung: 3-Layer Bidirektionale Architektur

```
┌─────────────────────────────────────────────────────────────┐
│  LAYER 3 — Cascade Bridge (höchste Qualität)          ✅    │
│  Discord /ask → GitHub Issue → Cascade → Discord Notify     │
│  Latenz: Minuten. Qualität: IDE-nah (voller Kontext)        │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│  LAYER 2 — LLM Gateway (mittlere Qualität)            🔜    │
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

Der Kanal ist **bidirektional**: Discord kann Tasks an Cascade schicken,
Cascade kann aktiv Discord benachrichtigen — ohne auf den nächsten User-Input zu warten.

---

## Implementierungsstand

### Layer 1 — Sofort-Steuerung ✅

Slash Commands (`windsurf-bot#3564` auf hetzner-prod):

| Command | Funktion |
|---|---|
| `/task` | GitHub Actions Workflow starten |
| `/approve` / `/reject` | Gate-Entscheidungen (ADR-107) |
| `/deploy` | Deployment triggern |
| `/health` | Server-Status |
| `/status` | Offene Issues |
| `/memory` | pgvector Semantic Search |
| `/ask` | GitHub Issue Bridge (→ Layer 3) |

### Layer 3 — Cascade Bridge ✅

```
Discord /ask "Frage"
    → GitHub Issue mit Label cascade-task
    → Cascade sieht Issue in Windsurf
    → Cascade antwortet als Issue-Kommentar
    → cascade-answer-notify.yml Workflow
    → Discord Notification (Webhook)
```

**Label `cascade-task` in 11 Repos:** mcp-hub, bfagent, risk-hub, coach-hub,
billing-hub, pptx-hub, trading-hub, travel-beat, weltenhub, cad-hub, wedding-hub

### IDE → Discord (Cascade spricht aktiv) ✅

`discord_notify` MCP Tool in `orchestrator_mcp/server.py`:

```python
discord_notify(
    message="PR erstellt, bitte reviewen.",
    title="✅ Task abgeschlossen",
    level="success",          # info | success | warning | error
    issue_url="https://..."   # optional
)
```

Cascade nutzt dieses Tool eigenständig um:
- Task-Abschluss zu melden
- Gate-Entscheidungen anzufragen
- Fragen zu stellen ohne den User zu blockieren
- Deploy-Ergebnisse zu kommunizieren

Workflow-Dokumentation: `.windsurf/workflows/discord-notify.md`

### Layer 2 — LLM Gateway 🔜

Geplant für nächste Session:

```
Discord /chat "Frage"
    → orchestrator_mcp/discord/handlers.py cmd_chat()
    → llm_mcp REST-Endpoint /v1/chat
    → GPT-4o + dynamischer System-Prompt
      (ADRs + pgvector Memory + offene Issues)
    → Antwort in Discord (< 5s)
```

Erforderlich: `llm_mcp` FastAPI-Endpoint auf hetzner-prod (~50 LOC)

---

## Discord Server Struktur

```
iilgmbh-agent Server
├── #agent-tasks    ← /ask Antworten + cascade-task Notifications
├── #deployments    ← /deploy, /approve, /reject, GitHub Actions
├── #health         ← /health, automatische Alerts
├── #chat           ← /chat (Layer 2, noch nicht aktiv)
└── #log            ← alle Events (Audit Trail)
```

---

## Ehrliche Qualitätsbewertung

**Was nie IDE-Qualität erreicht:**
- Kein direkter Dateizugriff ohne expliziten Tool-Call
- Kein Live-Codebase-Kontext (nur was in Memory/ADRs steht)
- Kein interaktives Debugging

**Was annähernd IDE-Qualität erreicht (Layer 2+3):**
- Architektur-Fragen, nächste Schritte, ADR-Entscheidungen → **gut**
- Task-Erstellung und Gate-Entscheidungen → **vollwertig**
- Deployment-Steuerung → **vollwertig**
- Cascade-initiated Kommunikation → **neu: vollwertig**

---

## Konsequenzen

**Positiv:**
- Vollständige mobile Steuerung der Plattform von überall
- Bidirektionale asynchrone Zusammenarbeit Mensch ↔ Cascade
- Audit Trail aller Entscheidungen via GitHub Issues
- Cascade kann proaktiv handeln ohne Desktop-Bindung
- Kein proprietärer Client — Discord App reicht

**Risiken:**
- Layer 2 erfordert `llm_mcp` REST-Endpoint (noch nicht gebaut)
- Layer 3: Cascade muss Windsurf aktiv haben um Issues zu sehen
- GitHub Issues als Kommunikationskanal → Lärm im Issue-Tracker

**Mitigation:**
- Separates Repo `cascade-inbox` nur für Discord-Tasks (Phase 2)
- `llm_mcp` als leichtgewichtiger FastAPI-Service
- `discord_notify` überbrückt Latenz: Cascade meldet sich sobald fertig

---

## Verwandte ADRs

- ADR-113: Discord Bot Gateway + pgvector Memory Store
- ADR-101: MCP Platform Konzept
- ADR-107: Extended Agent Team
- ADR-112: Agent Skill Registry + Persistent Context
