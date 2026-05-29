# Changelog — platform

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [2026.05.18] — 2026-05-18

### Added
- `policies/`: Org-weite Policy-Dateien (`llm-routing`, `session-routing`,
  `adr-threshold`, `platform-agents`, `claude-skills`, `orchestrator` + README)
  von der unversionierten `~/.claude/policies/` hierher vendored — **SSoT jetzt
  versioniert**. Lokale Anbindung via Symlink in den pinned platform-Worktree
  (Muster wie `~/.claude/commands`→`platform-workflows`); `inject_policies.py`
  + `claude-policy` lesen den Pfad unverändert. Phase 2a von dev-hub#51 —
  CI-Auto-Sync nach Orchestrator-Memory folgt als Phase 2b (eigenes ADR).
  Kein ADR für 2a (Datei-Vendoring, folgt etabliertem Muster — `adr-threshold`).
- **ADR-209** + `.github/workflows/sync-policies-to-orchestrator.yml`: Phase 2b
  von dev-hub#51 — bei Merge auf `main` mit `policies/**` synct ein Workflow
  auf dem `[self-hosted, prod]`-Runner die Policies via `claude-policy push`
  automatisch in den Orchestrator-Memory (ADR-113). Idempotent (content_hash).
  `tools/claude-policy`: zwei rückwärtskompatible Env-Vars — `ORCH_LOCAL=1`
  (docker exec lokal, kein SSH/Key auf dem prod-Runner) und `CLAUDE_POLICY_DIR`
  (Policy-Quelle = Checkout statt `~/.claude/policies`). Behebt die manuelle
  Push-Drift (gemergte Policy ≠ was Agenten sehen) — letztes Stück dev-hub#51.

---

## [2026.05.17] — 2026-05-17

### Changed
- `adr-review`: zweistufige **Eskalation**. Günstiger Erstpass (qwen-3-235b);
  zweiter Pass mit stärkerem Flatrate-Modell (`cerebras/zai-glm-4.7`, env-
  übersteuerbar) bei Label `adr-deep-review`, >1 ADR-Datei oder Score <
  Schwelle (`ADR_REVIEW_ESCALATE_BELOW`, default 6). Kommentar nennt Modell +
  Grund. Schließt die Frontier-Lücke bewusst **nicht** (README-Disclaimer).
  Reine Konfig-/Routing-Ergänzung — kein ADR (internes CI-Tool, Muster-Folge).
- `adr-review`: Default-Modelle umgestellt — `ADR_REVIEW_MODEL`
  `cerebras/qwen-3-235b…` → `groq/llama-3.3-70b-versatile` (Cerebras-EOL des
  qwen-Modells 2026-05-27), `ADR_REVIEW_FALLBACK` → `cerebras/llama3.1-8b`
  (Cross-Provider-Failover, Policy-Tier-1b). Deckt sich mit ADR-208-Resolver
  (`iil/adr-review`). Kein ADR (Daten-/Default-Fix, Muster-Folge).

### Fixed
- `tools/claude-policy`: Skript von No-Op-Stub → **funktionsfähig**. Transport:
  SSH + `docker exec` gegen Prod-Container `mcp_hub_orchestrator_http` (gleiches
  Postgres-Backend wie die MCP-Tools), Aufruf von
  `orchestrator_mcp.memory.store.upsert/search`. Script via stdin, Policy-Inhalt
  base64-inline (kein `cat >`-Staging — ssh re-parst argv, `>` würde sonst auf
  dem Prod-Host statt im Container landen; Bug im Live-Test gefunden + behoben).
  Idempotent via content_hash. `CLAUDE_POLICY_STUB=1` behält In-Claude-Pfad.
  README an Realität angepasst (vorheriges „autonomes CLI nicht möglich" war
  falsch). Verifiziert: list/push/diff Round-Trip, 6 Policies konvergieren.
  Behebt den von #186 mitgelieferten Stub; ersetzt mcp-hub#60 (falsches Repo).
  Refs dev-hub#51. Kein ADR (Tooling-Fix, Muster-Folge).

---

## [2026.05.16] — 2026-05-16

### Added
- `packages/adr-review/` — minimales CLI für KI-gestützte ADR-Reviews auf PRs
  (konsumiert von `.github/workflows/adr-review.yml`; das Paket fehlte bisher,
  der Workflow-Guard überspringt nur). Reviewt geänderte ADR-Dateien, upsertet
  einen PR-Kommentar, setzt Score-Label. Informativ/non-blocking by default;
  `--fail-under N` optional. Tests + README dabei. Kein ADR nötig (internes
  CI-Tool, ein Repo, kein Public-Surface).

### Changed
- adr-review LLM-Pfad: **Flatrate via litellm → Cerebras/Groq** statt Anthropic
  (Plattform-`llm-routing`-Policy). `ANTHROPIC_API_KEY` entfernt — aus
  Paket-Deps, CLI, Workflow-Env *und* als GitHub-Secret gelöscht. Default
  `cerebras/qwen-3-235b-a22b-instruct-2507` + Groq-Fallback, env-übersteuerbar.

---

## [2026.04.28] — 2026-04-28

### Added
- `push_project_facts.py` (`.github/scripts/`) — generiert `project-facts.md` via GitHub API und
  pusht sie automatisch in alle Django-Repos (kein lokaler Checkout nötig)
- `gen-project-facts.yml` GitHub Actions Workflow — läuft wöchentlich Mo 04:00 UTC + `workflow_dispatch`
  mit optionalem `target_repo` Input; erkennt Django-Version, HTMX-Detection, Settings-Modul, Apps
- `run_prompt.py` (`scripts/`) — generiert optimierte, selbstenthaltende Prompts via
  Groq Llama-3.3-70B (kostenlos, Free Tier); Fallback auf Template-Generierung ohne LLM-Key
- `/prompt` Workflow (`prompt.md`) — 2-Call-Optimierung (statt 5 MCP-Calls), Affected-Files-Suche
  via `mcp0_search_code`, Komplexitäts-Routing, ~60% weniger Cascade-Tokens pro Aufruf
- `~/.secrets/groq_api_key` als neues lokales Secret für `run_prompt.py`
- `project-facts.md` in `risk-hub` live gepusht (Pilot)

### Changed
- README: Repo-Zahl 41 → 45, Scripts-Tabelle aktualisiert, `/prompt` Sektion ergänzt,
  `groq_api_key` in Secrets-Liste

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
