# Changelog — platform

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [2026.04.26] — 2026-04-26

### Added
- pgvector-Standort in `AGENT_HANDOVER.md`, `MULTI_ENV_SETUP.md` und `mcp-tools.md` dokumentiert (Container `mcp_hub_db`, Tunnel `:15435`)
- `ssh-tunnel-postgres` systemd-Service auf dev desktop eingerichtet (autostart, reconnect)

### Fixed
- `docs/MULTI_ENV_SETUP.md`: Tunnel-Befehl korrigiert (`:5432` → `:15435`)
- `README.md`: Hardcoded `/home/devuser/shared/secrets/` → `~/.secrets/`, doppelter `scripts/`-Eintrag entfernt

---

## [2026.04.23.2] — 2026-04-23

### Added
- `bootstrap.sh` — einmaliges Setup auf neuem Computer (GITHUB_DIR, Workflows, project-facts)
- `README.md` Quick Start Sektion mit bootstrap.sh Anleitung
- `session-start.md` Bootstrap-Referenz für neue Computer

### Fixed
- `scripts/gen_project_facts.py`: Hardcoded `/home/devuser/github` → `$GITHUB_DIR` (dynamisch)
- `docu-update-agent`: LLM via `aifw` statt direktem OpenAI-Call
- `docu-update-agent`: Model-Override für standalone aifw (ohne Django)

---

## [2026.04.23.1] — 2026-04-23

### Added
- `docu-update-agent.yml` GitHub Actions Workflow (Trigger: Label `docu-update`)
- `.github/scripts/docu_update_agent.py` — deterministischer CI/CD Agent ohne LLM
- `docu-update-agent` Stufe 2: gpt-4o-mini LLM für intelligente Docu-Updates
- Grok Fast (`$0.0002/1k`) in `orchestrator_mcp/tools.py` als Lightweight-Modell
- `cascade-auftraege.md` Phase 0: GitHub Issues Queue mit grok_fast

### Fixed
- `.windsurf/` Dateien: 11x `/home/dehnert/`, 2x `/home/devuser/`, 7x falsche MCP-Prefixes bereinigt
- `docu-update-agent`: Safety Gate — nur Issues mit Label `docu-update` werden verarbeitet
- 9 offene `docu-update` Issues verarbeitet und geschlossen
