# Docker & Deployment — Rules

> Glob-Activated: `Dockerfile`, `docker-compose*.yml`, `.env*`, `scripts/*.sh`, `.github/**`
> ADR-056, ADR-022 — Deployment Preflight + Platform Consistency

## Bash Scripts (CRITICAL)

```bash
#!/bin/bash
set -euo pipefail  # MANDATORY first line after shebang — NEVER omit
```

## Docker Compose — env_file Pattern

```yaml
# CORRECT
services:
  web:
    image: ghcr.io/achimdehnert/${REPO}/${REPO}-web:${IMAGE_TAG}
    env_file: .env.prod     # ALWAYS this
    restart: unless-stopped

# BANNED — ADR-022 violation:
# environment:
#   SECRET_KEY: ${SECRET_KEY}    <- ${VAR} interpolation
#   DATABASE_URL: ${DATABASE_URL} <- ${VAR} interpolation
```

## Dockerfile — Security & Health

```dockerfile
# CORRECT
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://127.0.0.1:8000/livez/ || exit 1

# BANNED — SD-001 CRITICAL:
# StrictHostKeyChecking=no           <- security violation
# Hardcoded 88.198.191.108           <- hardcoded IP
# ENV SECRET_KEY=hardcoded-value     <- hardcoded secret
```

## Health Endpoints (MANDATORY in every repo)

- `/livez/` → liveness (always 200, no DB check)
- `/healthz/` → readiness (checks DB, Redis)
- Both must use `@csrf_exempt` + `@require_GET`

## Deploy Flow

```bash
# 1. Build
docker build -f docker/app/Dockerfile \
    -t ghcr.io/achimdehnert/{repo}/{repo}-web:latest .

# 2. Push
docker push ghcr.io/achimdehnert/{repo}/{repo}-web:latest

# 3. Deploy (on server)
docker compose pull
docker compose up -d --force-recreate

# 4. Verify
curl -f https://{domain}/livez/
```

## BANNED Patterns (check_violations SD-001)

- `StrictHostKeyChecking=no` anywhere
- Hardcoded IP `88.198.191.108` in scripts/Dockerfiles
- `password=`, `SECRET_KEY=`, `API_KEY=` with literal values
- `${VAR}` in compose `environment:` block (use `env_file` instead)
- Missing `set -euo pipefail` in bash scripts
