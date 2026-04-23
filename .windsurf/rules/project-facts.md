---
trigger: always_on
---

# Project Facts: platform

> ADRs, architecture docs, shared workflows, repo-registry

## Meta

- **Type**: `infra`
- **GitHub**: `https://github.com/achimdehnert/platform`
- **Branch**: `main` — push: `git push` (SSH-Key konfiguriert)

## System (Hetzner Server)

- devuser hat **KEIN sudo-Passwort** → System-Pakete immer via SSH als root:
  ```bash
  ssh root@localhost "apt-get install -y <package>"
  ```

## Secrets / Config

- **Secrets**: `.env` (nicht in Git) — Template: `.env.example`
