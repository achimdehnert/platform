# Tool Consolidation — Gründliche Bewertung & Implementierungsvorschlag

## 1. IST-Analyse: Das Problem ist AKUT

### Aktueller Tool-Count im deployment_mcp

| Kategorie | Tools | Zeilen in tool_registry.py |
|-----------|------:|----------------------------|
| Hetzner Server | 9 | 26-56 |
| Firewall | 7 | 58-82 |
| SSH Keys (Hetzner) | 3 | 84-92 |
| Docker Container | 6 | 94-113 |
| Docker Compose | 6 | 115-134 |
| BF Agent Deploy | 1 | 136-156 |
| PostgreSQL | 9 | 158-196 |
| Environment | 5 | 198-221 |
| Secrets | 3 | 223-235 |
| SSL | 7 | 237-269 |
| DNS Zones | 4 | 271-285 |
| DNS Records | 8 | 287-326 |
| SSH Remote | 6 | 328-360 |
| Git | 13 | 362-438 |
| System | 2 | 440-450 |
| Service | 2 | 452-464 |
| Nginx | 2 | 466-472 |
| Log/Cron | 2 | 474-487 |
| Debug | 1 | 489-492 |
| GitHub Actions | 6 | 496-533 |
| **TOTAL** | **102** | |

### Client-Limits vs. Realität

| Client | Limit | Status |
|--------|------:|--------|
| Windsurf | ~100 | **ÜBERSCHRITTEN** — Tools werden ignoriert |
| Cursor | 40 | **2.5x über Limit** |
| Claude Desktop | 100 | **Knapp überschritten** |
| Claude Code | ~700 Tokens/Tool | **~71.400 Tokens** nur für Tool-Definitionen |

**Fazit: Die Konsolidierung ist kein Nice-to-have, sondern ein Blocker.**

---

## 2. Bewertung des Prototyps

### Stärken (was übernommen werden sollte)

1. **`@action` Decorator** — Elegantes Metadata-System (read_only, destructive, confirm).
   Ermöglicht deklarative Action-Definition und automatische Sicherheitschecks.

2. **`ConsolidatedTool` Basisklasse** — Saubere Abstraktion mit automatischer
   Action-Sammlung via `_collect_actions()`.

3. **Automatische Schema-Generierung** — `build_input_schema()` erzeugt valides
   JSON Schema aus Python Type Hints.

4. **Confirm-Check im Dispatcher** — Destruktive Actions werden automatisch geblockt.
   Kein doppelter Code in jedem Handler.

5. **Demo-Mode** — Alle Tools funktionieren ohne echte Clients. Perfekt für Tests.

6. **Dual-Bridge** — Sowohl FastMCP als auch Raw MCP SDK werden unterstützt.

7. **Gute Testabdeckung** — 78 Tests (36 Base/Hetzner + 42 Docker).

### Schwächen (was geändert werden muss)

#### KRITISCH

| # | Problem | Impact | Lösung |
|---|---------|--------|--------|
| S1 | **Return-Typ ist `str` statt `dict`** | Cascade erwartet JSON-Dicts mit `success`, `error`, etc. Der Prototyp gibt formatierte Strings zurück → verliert strukturierte Daten | Dispatch muss `dict` zurückgeben, Bridge serialisiert zu JSON |
| S2 | **Flaches Schema (Union aller Params)** | Alle Parameter aller Actions werden in ein flaches Schema gemischt. LLM weiß nicht welche Params zu welcher Action gehören | Action-spezifische Param-Beschreibung in der `action.description` |
| S3 | **Keine Output-Truncation** | Production-Tools nutzen `MAX_OUTPUT = 50_000`. Prototyp hat keinen Schutz vor MCP-Overflow | `MAX_OUTPUT` in Basisklasse einbauen |
| S4 | **`host`-Parameter fehlt im Pattern** | Production nutzt überall `host: str | None = None` mit Default aus Settings. Prototyp nutzt `server_name: str = ""` | `host`-Pattern aus Production übernehmen |

#### WICHTIG

| # | Problem | Impact | Lösung |
|---|---------|--------|--------|
| S5 | **Client-Interface stimmt nicht** | Prototyp: `self._client.list_servers()`. Production: `SSHClient` mit `client.run(cmd)` | Adapter-Pattern oder Production-Clients direkt nutzen |
| S6 | **FastMCP-Bridge: Handler-Signatur** | `handler(arguments: dict = {})` — FastMCP erwartet benannte Parameter | Bridge muss FastMCP-kompatible Signatur generieren |
| S7 | **Kein Allowlist-Support** | Production hat `DEPLOYMENT_MCP_TOOL_ALLOWLIST`. Prototyp ignoriert das | Allowlist in Bridge integrieren |
| S8 | **Separate Codebase** | Prototyp liegt in `platform/docs/tool_consolidation/` — nicht im `mcp-hub` wo er hingehört | Nach `mcp-hub/deployment_mcp/src/deployment_mcp/consolidated/` verschieben |

---

## 3. Optimaler Implementierungsvorschlag

### Architektur-Entscheidung: Hybrid-Ansatz

**Nicht** den Prototyp 1:1 nach Production kopieren, sondern:

1. **`ConsolidatedTool` + `@action`** aus dem Prototyp übernehmen (bereinigt)
2. **Bestehende Tool-Handler wiederverwenden** — kein Neuschreiben der SSH-Commands
3. **`tool_registry.py` erweitern** um konsolidierte Specs zu generieren
4. **Schrittweise Migration** — alte + neue Tools koexistieren via Allowlist

### Ziel-Architektur

```text
deployment_mcp/src/deployment_mcp/
├── server.py                    # MCP Server (kaum Änderungen)
├── tool_registry.py             # Erweitert: consolidated specs
├── consolidated/                # NEU
│   ├── __init__.py
│   ├── base.py                  # ConsolidatedTool + @action (bereinigt)
│   ├── bridge.py                # MCP SDK Registration
│   ├── server_tool.py           # 9 Hetzner Server actions → 1 tool
│   ├── firewall_tool.py         # 7 Firewall actions → 1 tool
│   ├── docker_tool.py           # 12 Container+Compose actions → 1 tool
│   ├── database_tool.py         # 9 PostgreSQL actions → 1 tool
│   ├── network_tool.py          # 19 SSL+DNS actions → 1 tool
│   ├── env_tool.py              # 8 Env+Secret actions → 1 tool
│   ├── ssh_tool.py              # 6 SSH Remote actions → 1 tool
│   ├── git_tool.py              # 13 Git actions → 1 tool
│   ├── system_tool.py           # 8 System+Nginx+Log+Cron → 1 tool
│   └── cicd_tool.py             # 6 GitHub Actions + 1 BFAgent → 1 tool
└── tools/                       # Bestehend (unverändert!)
    ├── hetzner_tools.py
    ├── docker_tools.py
    ├── git_tools.py
    └── ...
```

### Reduktion

| Kategorie | Vorher | Nachher | Actions |
|-----------|-------:|--------:|--------:|
| Hetzner Server | 9 | 1 `server_manage` | 9 |
| Firewall | 7 | 1 `firewall_manage` | 7 |
| Docker | 12 | 1 `docker_manage` | 12 |
| PostgreSQL | 9 | 1 `database_manage` | 9 |
| SSL + DNS | 19 | 1 `network_manage` | 19 |
| Env + Secrets | 8 | 1 `env_manage` | 8 |
| SSH Remote | 6 | 1 `ssh_manage` | 6 |
| Git | 13 | 1 `git_manage` | 13 |
| System | 8 | 1 `system_manage` | 8 |
| CI/CD + Deploy | 7 | 1 `cicd_manage` | 7 |
| Debug | 1 | 1 `mcp_runtime_info` | 1 |
| **TOTAL** | **102** | **11** | 99 |

**Reduktion: 89%** (102 → 11 Tools)

### Kritische Design-Änderungen vs. Prototyp

#### 1. Return-Typ: `dict` statt `str`

```python
# PROTOTYP (falsch für Production):
@action("list", "List servers", read_only=True)
async def list_servers(self) -> str:
    return "2 servers found"

# PRODUCTION (richtig):
@action("list", "List servers", read_only=True)
async def list_servers(self, **kwargs) -> dict[str, Any]:
    return await server_list(**kwargs)  # Bestehende Funktion!
```

#### 2. Bestehende Handler wrappen statt neu schreiben

```python
class ServerTool(ConsolidatedTool):
    category = "server"

    @action("list", "List all Hetzner Cloud servers", read_only=True)
    async def list_action(self, **kwargs) -> dict:
        from ..tools.hetzner_tools import server_list
        return await server_list(**kwargs)

    @action("delete", "Delete server", destructive=True)
    async def delete_action(self, **kwargs) -> dict:
        from ..tools.hetzner_tools import server_delete
        return await server_delete(**kwargs)
```

#### 3. Schema-Verbesserung: Params pro Action dokumentieren

```python
def get_tool_description(self) -> str:
    lines = [f"{self.description}\n\nActions:"]
    for name, meta in sorted(self._actions.items()):
        sig = inspect.signature(meta.handler)
        params = [p for p in sig.parameters if p != "self"]
        param_str = f" ({', '.join(params)})" if params else ""
        prefix = "[!]" if meta.destructive else "[R]" if meta.read_only else "[W]"
        lines.append(f"  {prefix} {name}{param_str}: {meta.description}")
    return "\n".join(lines)
```

### Implementierungs-Phasen

#### Phase 1: Base + Bridge (1h)
- `consolidated/base.py` — bereinigter ConsolidatedTool (dict-return, MAX_OUTPUT, host-pattern)
- `consolidated/bridge.py` — Raw MCP SDK Integration
- Tests für Base

#### Phase 2: Wrapper-Tools (2h)
- Alle 10 ConsolidatedTool-Subklassen
- Jede Action delegiert an bestehende Tool-Funktion
- Keine Code-Duplikation

#### Phase 3: Integration in server.py (30min)
- `CONSOLIDATED_MODE` Environment-Variable
- `True` → 11 konsolidierte Tools
- `False` → 102 einzelne Tools (Fallback)
- Schrittweise Umstellung

#### Phase 4: Tests (1h)
- 1 Testklasse pro ConsolidatedTool
- Dispatch-Tests (happy path + error)
- Confirm-Check-Tests
- Schema-Validierung

#### Phase 5: Sphinx-Doku Update (30min)
- `mcp-tools.md` aktualisieren
- Konsolidierungstabelle einfügen
- Migrations-Guide für andere MCP-Server

### Migrations-Strategie

```python
# server.py — Phase 3
CONSOLIDATED = os.environ.get("DEPLOYMENT_MCP_CONSOLIDATED", "false") == "true"

if CONSOLIDATED:
    from .consolidated.bridge import register_all
    register_all(server, TOOL_HANDLERS)
else:
    # Bestehende 102 Tools (unverändert)
    ...
```

**Vorteil:** Zero-Risk-Rollout. Env-Variable steuert ob alt oder neu.

---

## 4. Empfehlung

| Aspekt | Entscheidung |
|--------|-------------|
| **Wo implementieren?** | `mcp-hub/deployment_mcp/src/deployment_mcp/consolidated/` |
| **Bestehende Tools ändern?** | NEIN — Wrapper-Pattern nutzt bestehende Funktionen |
| **Wann umschalten?** | Env-Variable `DEPLOYMENT_MCP_CONSOLIDATED=true` |
| **Prototyp-Code übernehmen?** | `base.py` (bereinigt), `@action` decorator (1:1) |
| **Prototyp-Code verwerfen?** | Demo-Mode, `fastmcp_bridge.py`, Emoji-Formatierung |
| **Tests übernehmen?** | Test-Pattern ja, aber neue Tests für Production-Wrapper |
| **Priorität?** | **HOCH** — 102 Tools überschreiten alle Client-Limits |

---

## 5. Nächster Schritt

Soll ich mit Phase 1 starten? Die Implementierung wird:
1. `consolidated/base.py` — Bereinigter ConsolidatedTool
2. `consolidated/bridge.py` — MCP SDK Integration
3. Ein Proof-of-Concept mit `server_tool.py` (9 Actions → 1 Tool)
4. Tests die gegen den echten Server via MCP laufen
