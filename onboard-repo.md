---
description: Onboard a new repository into the platform ecosystem with consistent CI/CD, Docker, database, Nginx, and naming conventions
---

# New Repository Onboarding Workflow

## Trigger

User says one of:

- "Neues Repo onboarden: [name]"
- "Onboard [name] into the platform"
- "Setup [name] wie die anderen Repos"

## Step 0: Gather Information

Ask the user:

```text
📋 Neues Repo: [name]

Ich brauche folgende Infos:
1. App-Beschreibung (1 Satz)
2. Production-Domain (z.B. myapp.iil.pet oder custom-domain.com)
3. Braucht die App Celery/Worker? [Ja/Nein]
4. Braucht die App eine eigene Datenbank? [Ja/Nein] (Standard: Ja)
5. Lokaler Port auf dem Server (nächster freier: siehe Port-Map unten)
```

### Port-Map (88.198.191.108)

| Port | App |
|------|-----|
| 8080 | governance |
| 8081 | weltenhub |
| 8088 | trading-hub |
| 8089 | travel-beat |
| 8090 | risk-hub |
| 8091 | bfagent |
| 8092 | pptx-hub |
| 8093 | *nächster freier* |

## Step 1: Repository-Struktur erstellen

Folgende Dateien MÜSSEN existieren — prüfe und erstelle fehlende:

### 1.1 Projektstruktur (Django-Standard)

```text
<repo>/
├── .github/
│   └── workflows/
│       └── ci-cd.yml              # CI/CD Pipeline (siehe Step 2)
├── docker/
│   └── app/
│       ├── Dockerfile             # Production Dockerfile (siehe Step 3)
│       └── entrypoint.sh          # Entrypoint-Script (siehe Step 3)
├── config/                        # Django-Konfiguration
│   ├── __init__.py
│   ├── settings/                  # Split-Settings (EMPFOHLEN)
│   │   ├── __init__.py            # → from .production import * (oder .development)
│   │   ├── base.py                # Gemeinsame Settings
│   │   ├── development.py         # DEBUG=True, sqlite, etc.
│   │   └── production.py          # SECURE_*, DATABASE_URL, etc.
│   ├── urls.py
│   ├── celery.py                  # Falls Celery benötigt
│   └── wsgi.py
├── apps/                          # Django-Apps
│   └── <app_name>/
├── requirements.txt               # Oder requirements/base.txt + dev.txt
├── docker-compose.prod.yml        # Production Compose (siehe Step 3.3)
├── pyproject.toml                 # Projekt-Metadaten
├── .dockerignore                  # PFLICHT — siehe Step 1.5
├── .env.example                   # Beispiel-Umgebungsvariablen
└── README.md
```

### 1.2 Naming Conventions (MANDATORY)

| Element | Konvention | Beispiel |
|---------|-----------|----------|
| **Repo-Name** | lowercase-with-hyphens | `my-app` |
| **Container-Name** | repo_name + suffix (underscore) | `my_app_web`, `my_app_db` |
| **Compose-Service** | repo-name + suffix (hyphen) | `my-app-web`, `my-app-db` |
| **Database-Name** | repo_underscore | `my_app` |
| **DB-User** | repo_underscore | `my_app` |
| **Network** | repo_network (underscore) | `my_app_network` |
| **Volume** | repo_pgdata (underscore) | `my_app_pgdata` |
| **GHCR Image** | `ghcr.io/achimdehnert/<repo>` | `ghcr.io/achimdehnert/my-app` |
| **Server Path** | `/opt/<repo>` | `/opt/my-app` |
| **Nginx Config** | `<domain>.conf` | `my-app.iil.pet.conf` |

### 1.3 Django Settings (MANDATORY)

**Empfohlen: Split-Settings** (`config/settings/base.py` + `production.py`).  
Alternativ: Single `config/settings.py` (z.B. risk-hub).

**`config/settings/base.py`** (gemeinsame Settings):

```python
import os

SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production")
DEBUG = os.environ.get("DEBUG", "false").lower() == "true"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost").split(",")
CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()
]

# Database via DATABASE_URL (Standard)
# Fallback: Individuelle POSTGRES_* Vars möglich, aber DATABASE_URL bevorzugen
import dj_database_url
DATABASES = {"default": dj_database_url.config(default="sqlite:///db.sqlite3")}
```

**`config/settings/production.py`** (Production-Overrides):

```python
from .base import *  # noqa: F401,F403

DEBUG = False

# CRITICAL: Reverse proxy (Nginx) terminates SSL
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
```

### 1.4 `.env.example` erstellen

```env
# === Django ===
SECRET_KEY=change-me-in-production
DEBUG=false
DJANGO_ALLOWED_HOSTS=<app>.iil.pet,localhost
CSRF_TRUSTED_ORIGINS=https://<app>.iil.pet

# === Superuser (auto-created on first start) ===
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=achim@dehnert.com
DJANGO_SUPERUSER_PASSWORD=CHANGE_ME_BEFORE_DEPLOY

# === Database ===
POSTGRES_DB=<app_underscore>
POSTGRES_USER=<app_underscore>
POSTGRES_PASSWORD=CHANGE_ME
DATABASE_URL=postgres://<app_underscore>:CHANGE_ME@<app>-db:5432/<app_underscore>

# === Redis ===
REDIS_URL=redis://<app>-redis:6379/0

# === GHCR ===
GHCR_OWNER=achimdehnert
GHCR_REPO=<repo-name>
IMAGE_TAG=latest
```

### 1.5 `.dockerignore` erstellen (PFLICHT)

Ohne `.dockerignore` landet `.git/` (~50-200MB), `__pycache__/`, `.env.prod` im Build-Context.

```dockerignore
.git
.gitignore
__pycache__
*.pyc
*.pyo
.env*
!.env.example
.venv
venv
env
node_modules
*.egg-info
.pytest_cache
.mypy_cache
.ruff_cache
docker-compose*.yml
!docker/
docs/
tests/
*.md
!README.md
.windsurf/
```

## Step 2: GitHub Actions CI/CD

Erstelle `.github/workflows/ci-cd.yml` mit Platform Reusable Workflows:

```yaml
# <APP_NAME> CI/CD — Using Platform Reusable Workflows
name: CI/CD Pipeline

permissions:
  contents: read
  packages: write

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  workflow_dispatch:
    inputs:
      skip_tests:
        description: 'Skip tests (emergency only)'
        required: false
        default: false
        type: boolean

jobs:
  # STAGE 1: CI (Lint, Test, Security Scan)
  ci:
    name: "CI"
    uses: achimdehnert/platform/.github/workflows/_ci-python.yml@v1
    with:
      python_version: "3.12"
      coverage_threshold: 0
      requirements_file: "requirements.txt"
      source_dir: "src"
      django_settings_module: "config.settings"
      skip_tests: ${{ inputs.skip_tests || false }}
    secrets: inherit

  # STAGE 2: Build Docker Image → GHCR
  build:
    name: "Build"
    needs: [ci]
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    uses: achimdehnert/platform/.github/workflows/_build-docker.yml@v1
    with:
      dockerfile: "docker/app/Dockerfile"
      scan_image: true
    secrets: inherit

  # STAGE 3: Deploy to Hetzner
  deploy:
    name: "Deploy"
    needs: [build]
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    uses: achimdehnert/platform/.github/workflows/_deploy-hetzner.yml@v1
    with:
      app_name: <REPO_NAME>
      deploy_path: /opt/<REPO_NAME>
      health_url: https://<DOMAIN>/livez/
      compose_file: docker-compose.prod.yml
      web_service: <REPO_NAME>-web
      run_migrations: true
      enable_rollback: true
      notify_slack: false
    secrets:
      HETZNER_HOST: ${{ secrets.DEPLOY_HOST }}
      HETZNER_USER: ${{ secrets.DEPLOY_USER }}
      HETZNER_SSH_KEY: ${{ secrets.DEPLOY_SSH_KEY }}
```

### GitHub Secrets (MÜSSEN im Repo gesetzt sein)

| Secret | Wert |
|--------|------|
| `DEPLOY_HOST` | `88.198.191.108` |
| `DEPLOY_USER` | `root` (O-02: Bei Multi-Server-Setup dedizierten `deploy`-User mit sudo empfehlen) |
| `DEPLOY_SSH_KEY` | SSH Private Key (gleicher wie andere Repos) |

### N-05: Image-Tag-Strategie & Rollback (O-10)

CI/CD soll **zwei Tags** pushen:

- `:latest` — für normales Deployment
- `:sha-<7char>` — für Rollback-Fähigkeit (Git-SHA der letzten 7 Zeichen)

**Manueller Rollback:**

```bash
# Auf Server: vorheriges Image deployen
cd /opt/<REPO>
IMAGE_TAG=sha-abc1234 docker compose -f docker-compose.prod.yml up -d --force-recreate <REPO>-web
```

**DB-Migration-Reversal:** Django-Migrationen sind **nicht** automatisch rückwärtskompatibel.
Bei Schema-Änderungen: `python manage.py migrate <app> <previous_migration>` vor Image-Rollback.

## Step 3: Docker Setup

### 3.1 Dockerfile (`docker/app/Dockerfile`)

```dockerfile
# =============================================================================
# Multi-Stage Build (O-04): build-essential nur in Builder-Stage
# =============================================================================

# --- Stage 1: Builder (compile C-extensions, then discard build-deps) ---
FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --prefix=/install \
    -r /tmp/requirements.txt \
    gunicorn whitenoise

# --- Stage 2: Runtime (slim, no build-essential ~200MB saved) ---
FROM python:3.12-slim AS runtime

# OCI Labels
ARG APP_NAME=<REPO_NAME>
LABEL org.opencontainers.image.source="https://github.com/achimdehnert/${APP_NAME}"
LABEL org.opencontainers.image.description="<APP_DESCRIPTION>"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Runtime-only system deps (libpq for psycopg, add app-specific here)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy pre-built Python packages from builder
COPY --from=builder /install /usr/local

WORKDIR /app

COPY docker/app/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

COPY . /app

# Collect static files at build time (O-03: show errors, don't abort)
RUN DJANGO_SECRET_KEY=build-only \
    DJANGO_SETTINGS_MODULE=config.settings.production \
    DATABASE_URL=sqlite:///dev-null \
    python manage.py collectstatic --noinput \
    || echo "WARN: collectstatic failed (non-fatal at build time)"

# Non-root user
RUN groupadd --gid 1000 app && \
    useradd --uid 1000 --gid 1000 --create-home app && \
    chown -R app:app /app
USER app

EXPOSE 8000

# Health check (ALWAYS localhost, NEVER 127.0.0.1, NEVER curl)
# ⚠️ WARNING: This HEALTHCHECK is inherited by ALL containers using this image.
#    Worker/Beat services MUST override this in docker-compose.prod.yml!
#    See Step 4.2 Healthcheck-Regeln.
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/livez/')" || exit 1

ENTRYPOINT ["/entrypoint.sh"]
CMD ["web"]
```

### 3.2 Entrypoint (`docker/app/entrypoint.sh`)

```bash
#!/bin/sh
set -e

# O-08: DB-Wait via Django (funktioniert mit jedem DB-Backend, kein psycopg-Import nötig)
echo "Waiting for database..."
until python -c "
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()
from django.db import connection
connection.ensure_connection()
" 2>/dev/null; do
    echo "  DB not ready, waiting..."
    sleep 2
done
echo "Database ready!"

# N-07: Migrations NUR im web-Container (verhindert Race-Condition bei parallelem Start)
if [ "$1" = "web" ]; then
    echo "Running migrations..."
    python manage.py migrate --noinput --skip-checks

    # N-04: collectstatic nur wenn nötig (bereits im Docker-Build gelaufen)
    if [ ! -d "/app/staticfiles" ] || [ -z "$(ls -A /app/staticfiles 2>/dev/null)" ]; then
        echo "Collecting static files..."
        python manage.py collectstatic --noinput
    else
        echo "Static files already present, skipping collectstatic"
    fi
fi

# Auto-create superuser if DJANGO_SUPERUSER_USERNAME is set
if [ -n "$DJANGO_SUPERUSER_USERNAME" ]; then
    python -c "
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()
from django.contrib.auth.models import User
username = os.environ['DJANGO_SUPERUSER_USERNAME']
if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(
        username=username,
        email=os.environ.get('DJANGO_SUPERUSER_EMAIL', ''),
        password=os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'changeme'),
    )
    print('Superuser %s created' % username)
else:
    print('Superuser %s already exists' % username)
" || echo "Superuser creation skipped"
fi

if [ "$1" = "web" ]; then
    echo "Starting web server (gunicorn)..."
    exec gunicorn config.wsgi:application \
        --bind 0.0.0.0:8000 \
        --workers "${GUNICORN_WORKERS:-2}" \
        --timeout 120 \
        --access-logfile -
fi

if [ "$1" = "worker" ]; then
    echo "Starting Celery worker..."
    exec celery -A config worker -l info --concurrency 2
fi

if [ "$1" = "beat" ]; then
    echo "Starting Celery beat..."
    exec celery -A config beat -l info
fi

echo "Usage: /entrypoint.sh [web|worker|beat]"
exit 1
```

### 3.3 `docker-compose.prod.yml`

```yaml
services:
  # N-03: ALLE Variablen via env_file, KEINE ${VAR} Interpolation in environment-Blöcken.
  #        Docker Compose liest ${VAR} aus .env (nicht .env.prod!).
  #        Daher: ln -sf .env.prod .env ODER nur env_file nutzen.

  <REPO>-db:
    image: postgres:16-alpine
    container_name: <REPO_UNDERSCORE>_db
    restart: unless-stopped
    env_file: .env.prod
    volumes:
      - <REPO_UNDERSCORE>_pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-<REPO_UNDERSCORE>}"]
      interval: 5s
      timeout: 3s
      retries: 30
    deploy:
      resources:
        limits:
          memory: 512M
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
    networks:
      - <REPO_UNDERSCORE>_network

  <REPO>-redis:
    image: redis:7-alpine
    container_name: <REPO_UNDERSCORE>_redis
    restart: unless-stopped
    command: ["redis-server", "--maxmemory", "128mb", "--maxmemory-policy", "allkeys-lru"]
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 30
    deploy:
      resources:
        limits:
          memory: 192M
    logging:
      driver: json-file
      options:
        max-size: "5m"
        max-file: "2"
    networks:
      - <REPO_UNDERSCORE>_network

  <REPO>-web:
    # O-07: Einfacher GHCR-Pfad (konsistent mit Naming-Table)
    image: ghcr.io/achimdehnert/<REPO>:${IMAGE_TAG:-latest}
    container_name: <REPO_UNDERSCORE>_web
    restart: unless-stopped
    env_file: .env.prod
    depends_on:
      <REPO>-db:
        condition: service_healthy
      <REPO>-redis:
        condition: service_healthy
    entrypoint: ["/entrypoint.sh"]
    command: ["web"]
    ports:
      - "127.0.0.1:<PORT>:8000"
    healthcheck:
      test: ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8000/livez/')\""]
      interval: 15s
      timeout: 5s
      retries: 3
      start_period: 30s
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M
    logging:
      driver: json-file
      options:
        max-size: "20m"
        max-file: "5"
    networks:
      - <REPO_UNDERSCORE>_network

  # --- Celery Worker (if needed) ---
  <REPO>-worker:
    image: ghcr.io/achimdehnert/<REPO>:${IMAGE_TAG:-latest}
    container_name: <REPO_UNDERSCORE>_worker
    restart: unless-stopped
    env_file: .env.prod
    entrypoint: ["/entrypoint.sh"]
    command: ["worker"]
    healthcheck:
      test: ["CMD-SHELL", "celery -A config inspect ping --timeout 10 2>/dev/null | grep -q OK"]
      interval: 60s
      timeout: 15s
      retries: 3
      start_period: 30s
    depends_on:
      <REPO>-db:
        condition: service_healthy
      <REPO>-redis:
        condition: service_healthy
    deploy:
      resources:
        limits:
          memory: 384M
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
    networks:
      - <REPO_UNDERSCORE>_network

  # --- Celery Beat (if needed) ---
  <REPO>-beat:
    image: ghcr.io/achimdehnert/<REPO>:${IMAGE_TAG:-latest}
    container_name: <REPO_UNDERSCORE>_beat
    restart: unless-stopped
    env_file: .env.prod
    entrypoint: ["/entrypoint.sh"]
    command: ["beat"]
    healthcheck:
      test: ["CMD-SHELL", "python -c \"import os; os.kill(1, 0)\""]
      interval: 60s
      timeout: 5s
      retries: 3
      start_period: 30s
    depends_on:
      <REPO>-db:
        condition: service_healthy
      <REPO>-redis:
        condition: service_healthy
    deploy:
      resources:
        limits:
          memory: 256M
    logging:
      driver: json-file
      options:
        max-size: "5m"
        max-file: "2"
    networks:
      - <REPO_UNDERSCORE>_network

volumes:
  <REPO_UNDERSCORE>_pgdata:

networks:
  <REPO_UNDERSCORE>_network:
    driver: bridge
```

## Step 4: Health-Check Endpoints & Regeln

### 4.1 Standardisierte Endpoints (N-02)

Jedes Repo MUSS diese 3 Endpoints haben:

| Endpoint | Zweck | Prüft | Für |
|----------|-------|-------|-----|
| `/livez/` | Liveness | App-Prozess lebt | **Docker Healthcheck** |
| `/healthz/` | Readiness | App + DB-Verbindung | Monitoring, Alerting |
| `/health/` | Backwards-Compat | Alias für `/livez/` | Legacy-URLs |

**`config/urls.py`:**

```python
from django.http import HttpResponse, JsonResponse
from django.db import connection

def liveness(request):
    return HttpResponse("ok")

def readiness(request):
    try:
        connection.ensure_connection()
        return JsonResponse({"status": "ok", "db": "connected"})
    except Exception as e:
        return JsonResponse({"status": "error", "db": str(e)}, status=503)

urlpatterns = [
    path("livez/", liveness, name="liveness"),
    path("healthz/", readiness, name="healthz"),
    path("health/", liveness, name="health-check"),  # backwards compat
    # ... andere URLs
]
```

### 4.2 Healthcheck-Regeln (KRITISCH)

| Regel | Begründung |
|-------|------------|
| **IMMER `localhost` statt `127.0.0.1`** | Django ALLOWED_HOSTS hat oft nur `localhost`, nicht `127.0.0.1` → HTTP 400 |
| **IMMER `python urllib` statt `curl`** | Slim Python-Images haben kein `curl` installiert |
| **IMMER Compose-HC für Worker/Beat** | Dockerfile-HC wird von ALLEN Containern geerbt — Worker/Beat haben kein Gunicorn → port 8000 nicht offen |
| **Worker-HC: `celery inspect ping`** | Prüft ob Worker tatsächlich Aufgaben verarbeitet |
| **Beat-HC: `os.kill(1, 0)`** | Prüft ob PID 1 (Celery Beat) lebt — beat hat keinen inspect-Endpoint |
| **Docker-HC nutzt `/livez/`** | Liveness = minimal, schnell, keine DB-Abhängigkeit |
| **Monitoring nutzt `/healthz/`** | Readiness = prüft DB, kann 503 zurückgeben |

### 4.3 Logging-Empfehlung (O-11)

**Minimum** (bereits in Compose-Templates):

- JSON-Logging via Docker `json-file` Driver mit `max-size`/`max-file`
- Gunicorn `--access-logfile -` (stdout)

**Empfohlen** für neue Repos:

```python
# config/settings/base.py
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "root": {"level": "INFO", "handlers": ["console"]},
}
```

**Optional:** Sentry für Error-Tracking (`sentry-sdk[django]` in requirements).

## Step 5: Server-Infrastruktur einrichten

### 5.1 Deployment-Verzeichnis auf Server erstellen

```bash
ssh root@88.198.191.108 "mkdir -p /opt/<REPO>"
```

### 5.2 `.env.prod` auf Server erstellen

Kopiere `.env.example` → `.env.prod` mit echten Werten:

```bash
scp .env.prod root@88.198.191.108:/opt/<REPO>/.env.prod
```

### 5.3 `docker-compose.prod.yml` auf Server kopieren

```bash
scp docker-compose.prod.yml root@88.198.191.108:/opt/<REPO>/docker-compose.prod.yml
```

### 5.4 Nginx Server-Block erstellen

Erstelle `/etc/nginx/sites-enabled/<DOMAIN>.conf`:

```nginx
server {
    listen 80;
    server_name <DOMAIN>;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name <DOMAIN>;

    ssl_certificate /etc/letsencrypt/live/<DOMAIN>/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/<DOMAIN>/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    client_max_body_size 100M;

    location / {
        proxy_pass http://127.0.0.1:<PORT>;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 5s;
        proxy_read_timeout 120s;
        proxy_next_upstream error timeout http_502;
        proxy_next_upstream_tries 2;
    }
}
```

### 5.5 SSL-Zertifikat holen (vor HTTPS-Aktivierung)

Erst HTTP-only Config deployen, dann:

```bash
ssh root@88.198.191.108 "certbot certonly --webroot -w /var/www/html -d <DOMAIN> --non-interactive --agree-tos --email achim@dehnert.com"
```

Dann HTTPS-Config deployen + `nginx -t && nginx -s reload`.

### 5.6 DNS A-Record erstellen

```
<DOMAIN> → 88.198.191.108 (TTL 60)
```

Via Hetzner DNS API oder mcp5_network_manage.

## Step 6: Platform-Integration

### 6.1 MCP-Orchestrator registrieren (CRITICAL)

Füge das Repo in **zwei Dateien** im `mcp-hub` Repo hinzu:

1. `orchestrator_mcp/local_tools.py` — `_ALLOWED_REPOS` dict:
```python
"<REPO>": "/home/dehnert/github/<REPO>",
```

2. `orchestrator_mcp/server.py` — `run_git` Tool-Schema `enum`:
```python
"<REPO>",
```

Dann `mcp10_run_git` für mcp-hub committen + pushen.
**Ohne diesen Schritt funktioniert `mcp10_run_git(repo="<REPO>")` nicht!**

### 6.2 Deploy-Workflow aktualisieren

Füge die neue App zur Tabelle in `.windsurf/workflows/deploy.md` hinzu:

```markdown
| <REPO> | 88.198.191.108 | /opt/<REPO> | docker-compose.prod.yml | https://<DOMAIN>/ |
```

### 6.3 Backup-Workflow aktualisieren

Füge die neue DB zur Tabelle in `.windsurf/workflows/backup.md` hinzu:

```markdown
| <REPO> | <DB_NAME> | /opt/backups/<REPO>/ |
```

### 6.4 ADR-Scope registrieren

Falls App-spezifische ADRs erwartet, Scope in `.windsurf/workflows/adr.md` hinzufügen.

### 6.5 SSH/Deployment Memory aktualisieren

Erstelle/aktualisiere Memory mit:
- Container-Namen
- Deploy-Commands
- Credentials (falls Admin-User)
- Production-URLs

## Step 7: Verifikation

### Checkliste (ALLE Punkte müssen grün sein)

```text
✅ Verifikation für [REPO]

Repo-Struktur:
  [ ] docker/app/Dockerfile existiert
  [ ] docker/app/entrypoint.sh existiert (chmod +x)
  [ ] docker-compose.prod.yml existiert
  [ ] .github/workflows/ci-cd.yml existiert
  [ ] .env.example existiert
  [ ] /livez/ Health-Endpoint existiert
  [ ] pyproject.toml mit korrekten Metadaten
  [ ] README.md mit Quickstart

Server:
  [ ] /opt/<REPO>/ Verzeichnis existiert
  [ ] .env.prod mit echten Werten
  [ ] docker-compose.prod.yml kopiert
  [ ] Container starten und sind healthy

Netzwerk:
  [ ] DNS A-Record zeigt auf 88.198.191.108
  [ ] Nginx Config deployed
  [ ] SSL-Zertifikat aktiv
  [ ] HTTPS-Redirect funktioniert
  [ ] https://<DOMAIN>/livez/ gibt "ok"

CI/CD:
  [ ] GitHub Secrets gesetzt (DEPLOY_HOST, DEPLOY_USER, DEPLOY_SSH_KEY)
  [ ] Push auf main triggert CI
  [ ] CI baut Docker Image → GHCR
  [ ] CD deployt auf Server

Platform:
  [ ] deploy.md Tabelle aktualisiert
  [ ] backup.md Tabelle aktualisiert
  [ ] Memory mit Container-/Deploy-Infos erstellt
```

## Referenz: Bestehende Repos als Vorlage

| Vorlage für | Bestes Beispiel |
|-------------|----------------|
| CI/CD mit Reusable Workflows | `risk-hub/.github/workflows/docker-build.yml` |
| Dockerfile + Entrypoint | `risk-hub/docker/app/` |
| docker-compose.prod.yml | `risk-hub/docker-compose.prod.yml` |
| CI Pipeline (eigenständig) | `travel-beat/.github/workflows/ci.yml` |
| CD Pipeline (eigenständig) | `travel-beat/.github/workflows/cd-production.yml` |
| Nginx + SSL Setup | Gerade für bfagent-Subdomains gemacht |
