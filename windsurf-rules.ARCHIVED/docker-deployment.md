# Docker & Deployment -- Rules

> Glob-Activated: `Dockerfile`, `docker-compose*.yml`, `.env*`, `scripts/*.sh`, `.github/**`
> ADR-056, ADR-022, ADR-094 -- Deployment Preflight + Platform Consistency + Migration Safety

## Bash Scripts (CRITICAL)

```bash
#!/bin/bash
set -euo pipefail  # MANDATORY first line after shebang -- NEVER omit
```

## Docker Compose -- env_file Pattern

```yaml
# CORRECT
services:
  web:
    image: ghcr.io/achimdehnert/${REPO}-web:${IMAGE_TAG}
    env_file: .env.prod     # ALWAYS this
    restart: unless-stopped

# BANNED -- ADR-022 violation:
# environment:
#   SECRET_KEY: ${SECRET_KEY}    <- ${VAR} interpolation
#   DATABASE_URL: ${DATABASE_URL} <- ${VAR} interpolation
```

## Dockerfile -- Security & Health

```dockerfile
# CORRECT
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://127.0.0.1:8000/livez/ || exit 1

# BANNED -- SD-001 CRITICAL:
# StrictHostKeyChecking=no           <- security violation
# Hardcoded 88.198.191.108           <- hardcoded IP
# ENV SECRET_KEY=hardcoded-value     <- hardcoded secret
# RUN pip install package==0.0.1 --no-deps  <- unpinned dependencies
```

## Health Endpoints (MANDATORY in every repo)

- `/livez/` -> liveness (always 200, no DB check)
- `/healthz/` -> readiness (checks DB, Redis)
- Both must use `@csrf_exempt` + `@require_GET`

## Deploy Flow (ADR-094)

```bash
# 0. Pre-flight: Migration conflict check
python manage.py migrate --check 2>&1 | grep -E "Conflict|Error" && exit 1 || true

# 1. Read image tag FROM compose file (single source of truth)
IMAGE=$(grep "image:" docker-compose.prod.yml | grep "web" | awk '{print $2}')
IMAGE=${IMAGE/\$\{IMAGE_TAG:-latest\}/latest}
echo "Building: $IMAGE"

# 2. Build with EXACT tag from compose file
docker build -t "$IMAGE" .

# 3. Deploy -- stop+rm required (force-recreate alone reuses cached image!)
docker stop {container} && docker rm {container}
docker compose -f docker-compose.prod.yml up -d {service}

# 4. Verify image matches (CRITICAL check)
sleep 20
docker inspect {container} --format '{{.State.Health.Status}}'
```

## Migration Conflicts (ADR-094)

```bash
# Before every docker build -- check for conflicting leaf nodes
python manage.py showmigrations 2>&1 | grep "Conflicting" && \
    python manage.py makemigrations --merge --no-input

# Missing dependency stub pattern:
# If NodeNotFoundError: 'app.00NN_name' not found -> create stub migration:
# apps/{app}/migrations/00NN_{name}.py with operations=[] and dep on last real migration
# Then add merge migration: 00NN+1_merge_{stub}_{leaf}.py

# Fake-apply (PROD EMERGENCY ONLY -- must fix migration afterwards):
# docker exec {db} psql -U {user} -d {db} -c \
#   "INSERT INTO django_migrations (app,name,applied) VALUES ('{app}','{name}',NOW()) ON CONFLICT DO NOTHING;"
```

## BANNED Patterns (check_violations SD-001)

- `StrictHostKeyChecking=no` anywhere
- Hardcoded IP `88.198.191.108` in scripts/Dockerfiles
- `password=`, `SECRET_KEY=`, `API_KEY=` with literal values
- `${VAR}` in compose `environment:` block (use `env_file` instead)
- Missing `set -euo pipefail` in bash scripts
- `docker build -t {tag}` where tag differs from compose `image:` field
- `docker compose up -d --force-recreate` without prior `stop/rm` when image was rebuilt locally
