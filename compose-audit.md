---
description: Audit all docker-compose.prod.yml files on the production server against ADR-021
---

# /compose-audit

Prüft alle Docker-Compose-Stacks auf dem Prod-Server gegen ADR-021 Compliance.

## Schritte

1. **Alle Compose-Dateien listen**
// turbo
```
mcp0_ssh_manage(action="exec", host="88.198.191.108", command="find /opt -maxdepth 2 -name 'docker-compose*.yml' | sort")
```

2. **Für jede Compose-Datei prüfen** (via `mcp0_ssh_manage file_read`):
   - [ ] `ports:` nur auf `127.0.0.1:XXXX:YYYY` (nie `0.0.0.0`)
   - [ ] `mem_limit` oder `deploy.resources.limits.memory` gesetzt
   - [ ] `healthcheck` für web, db, redis Services
   - [ ] `logging` mit `json-file`, `max-size`, `max-file`
   - [ ] `restart: unless-stopped` auf allen Services
   - [ ] `env_file` statt `environment: ${VAR}` für Secrets
   - [ ] DB-Image kompatibel (postgres:15 oder postgres:16, NICHT mischen)

3. **Port-Abgleich mit ports.yaml**
   - Vergleiche Host-Ports mit `${GITHUB_DIR:-$HOME/github}/platform/infra/ports.yaml`
   - Melde Abweichungen

4. **Report erstellen**
   Format pro Stack:
   ```
   ✅ risk-hub — 7/7 checks passed
   ⚠️ illustration-hub — 5/7 (missing: healthcheck web, logging redis)
   ❌ odoo-hub — 3/7 (0.0.0.0 binding, no mem_limit, no healthcheck)
   ```

5. **Fixes anbieten** — Für jede Abweichung konkreten Fix vorschlagen (NICHT automatisch anwenden)

## Referenzen
- ADR-021: Unified Deployment Pattern
- ADR-056: Docker Security
- Runbook: `df64ebe4-b7de-4cc2-8e76-d25459c044f1` (Compose Audit)
