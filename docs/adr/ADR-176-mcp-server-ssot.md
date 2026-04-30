---
status: accepted
date: 2026-04-30
deciders: Achim Dehnert
consulted: —
informed: Alle Plattform-Entwickler
---

# ADR-176 — MCP-Server SSoT: platform = Konfig, mcp-hub = Code

## Context and Problem Statement

Vor diesem ADR war die MCP-Server-Landschaft über mehrere Orte verteilt:

- MCP-Server-Code teils in `mcp-hub/`, teils in `platform/packages/outline-mcp/`
- Start-Scripts teils in `~/.local/bin/`, teils in `mcp-hub/`
- Keine zentrale Doku, welcher Server wo wohnt
- Secrets (API-Tokens) hardcoded in `~/.codeium/windsurf/mcp_config.json`
- Prefix-Mapping (`mcp0_`..`mcp6_`) environment-spezifisch, aber nicht konsistent dokumentiert
- 7 experimentelle Module in `mcp-hub/` ohne Registrierung + Status

Resultat: Drift, Token-Leak-Risiko, verwaiste Pfade (`platform/packages/outline-mcp` existiert gar nicht).

## Decision Drivers

- **Single Source of Truth** je Concern (Code vs. Konfig vs. Doku)
- **Security**: keine Secrets in committed / config-exportbaren Dateien
- **Onboarding**: neuer Entwickler soll in <15 Min verstehen, welche MCP-Server existieren
- **Konsistenz** mit platform-weiten Konventionen (ADR-009 Service-Layer, ADR-022 Compose, ADR-071 Code Quality)

## Considered Options

### Option A — Alles in `platform/`
Pro: Ein Repo. Contra: platform ist Meta-Repo (ADRs, Workflows, Registry), kein Code-Monorepo. Blow-up.

### Option B — Jeder MCP-Server als eigenes Repo
Pro: klare Grenzen. Contra: 10+ Repos, jeder mit eigener Venv, CI/CD, Release-Prozess → Operativer Overhead zu hoch.

### Option C — `mcp-hub` = Code, `platform` = Konfig + Doku (gewählt)
Pro: Eine Venv für alle Server, eine Release-Pipeline, eine Test-Suite. Platform bleibt Meta-Repo.
Contra: Keiner relevant.

## Decision Outcome

**Gewählt: Option C.**

### Verantwortlichkeiten

| Concern | Repo | Pfad |
|---|---|---|
| **MCP-Server-Code** | `achimdehnert/mcp-hub` | `<name>_mcp/` — eines pro Server |
| **Shared Base Lib** | `achimdehnert/mcp-hub` | `mcp_base/` |
| **Start-Scripts** | `achimdehnert/mcp-hub` | `scripts/start-<name>-mcp.sh` |
| **Konfig-Templates** | `achimdehnert/platform` | `templates/mcp_config.*.json` |
| **Sync-Script** | `achimdehnert/platform` | `scripts/sync-mcp-config.sh` |
| **Server-Inventar** | `achimdehnert/platform` | `docs/mcp/SERVERS.md` |
| **Configuration-Guide** | `achimdehnert/platform` | `docs/mcp/CONFIGURATION.md` |
| **Development-Guide** | `achimdehnert/platform` | `docs/mcp/DEVELOPMENT.md` |
| **Live-Config** (nie committed!) | Lokal | `~/.codeium/windsurf/mcp_config.json` |

### Secret-Pattern

**Verboten:** Tokens in `mcp_config.json` Git-sichtbar.

**Pattern:** Start-Scripts in `mcp-hub/scripts/` laden Secrets zur Laufzeit aus `~/.secrets/<name>`:

```bash
#!/bin/bash
set -euo pipefail
export OUTLINE_API_TOKEN="$(cat ~/.secrets/outline_api_token)"
cd "${GITHUB_DIR:-$HOME/github}/mcp-hub"
source .venv/bin/activate
python -m outline_mcp
```

`mcp_config.json` ruft nur das Start-Script auf, kein Secret im Env-Block.

### Prefix-Regel

Prefix = Reihenfolge in `mcp_config.json`. **Pro Environment kann die Reihenfolge abweichen.** Dokumentiert in `platform/docs/mcp/SERVERS.md`.

| Environment | Dokumentierte Prefix-Zuordnung |
|---|---|
| WSL / Prod | `mcp0_`=deployment, `mcp1_`=github, `mcp2_`=orchestrator, ... |
| Dev Desktop | `mcp0_`=github, `mcp1_`=orchestrator, ... |

### Neuer MCP-Server — Minimalprozess

1. Ordner `mcp-hub/<name>_mcp/` anlegen mit `__init__.py`, `__main__.py`, `README.md`
2. `README.md` Status-Banner: `> **Status:** 🚧 In Entwicklung` oder `✅ Production`
3. In `platform/docs/mcp/SERVERS.md` eintragen
4. In `platform/templates/mcp_config.<env>.json` eintragen
5. Start-Script `mcp-hub/scripts/start-<name>-mcp.sh`
6. Dependencies zu `mcp-hub/pyproject.toml` hinzufügen

## Consequences

**Positiv**
- Klare SSoT — jeder weiß wo was liegt
- Secrets bleiben aus Git-Artefakten raus
- Eine Venv für alle Server → weniger Wartung
- Templates machen Config reproduzierbar pro Environment

**Negativ**
- Migrations-Aufwand einmalig (outline-mcp aus `_ARCHIVED` zurückholen)
- Entwickler müssen `sync-mcp-config.sh` aufrufen statt `mcp_config.json` direkt editieren

## Compliance

- [x] ADR-009 Service-Layer: nicht relevant (Infrastruktur-ADR)
- [x] ADR-071 Code-Quality: Commits mit `[TAG]` Konvention
- [x] ADR-045 Config via Environment: Secrets aus `~/.secrets/`, nicht hardcoded

## Related

- ADR-015 Platform Component Discovery (registry_mcp)
- ADR-145 Outline Wiki Integration
- ADR-159 Shared Secrets Pattern
