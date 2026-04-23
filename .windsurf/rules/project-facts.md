---
trigger: always_on
---

# Project Facts: platform

> ADRs, architecture docs, shared workflows, repo-registry

## Meta

- **Type**: `infra`
- **GitHub**: `https://github.com/achimdehnert/platform`
- **Branch**: `main` — push: `git push` (SSH-Key konfiguriert)

## Lokale Umgebung (Dev Desktop — adehnert)

- **Pfad**: `~/CascadeProjects/platform` → `$GITHUB_DIR` = `~/CascadeProjects`
- **Venv**: `~/CascadeProjects/platform/.venv/bin/python`
- **MCP-Config**: `~/.codeium/windsurf/mcp_config.json`
- **MCP aktiv**: `mcp0_` = github · `mcp1_` = orchestrator
- **Secrets**: `~/.secrets/` (github_token, outline_api_token, cloudflare_*)
- **Prod-Server**: `root@88.198.191.108` (SSH-Key hinterlegt)

## System (Hetzner Server)

- devuser hat **KEIN sudo-Passwort** → System-Pakete immer via SSH als root:
  ```bash
  ssh root@localhost "apt-get install -y <package>"
  ```

## Secrets / Config

- **Secrets**: `.env` (nicht in Git) — Template: `.env.example`
