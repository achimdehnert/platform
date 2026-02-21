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
| 8082 | dev-hub |
| 8088 | trading-hub |
| 8089 | travel-beat |
| 8090 | risk-hub |
| 8091 | bfagent |
| 8092 | pptx-hub |
| 8093 | wedding-hub |
| 8094 | *nächster freier* |

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
│   │   ├── production.py          # SECURE_*, DATABASE_URL, etc.
│   │   └── test.py                # Test-Settings (WHITENOISE_MANIFEST_STRICT=False etc.)
│   ├── urls.py
│   ├── celery.py                  # Falls Celery benötigt
│   └── wsgi.py
├── apps/                          # Django-Apps
│   └── <app_name>/
│       ├── components/            # ADR-041: Component modules (get_context + fragment_view)
│       └── templatetags/          # ADR-041: <app>_components.py (inclusion tags)
├── templates/                     # Templates at project root
│   └── <app_name>/
│       ├── partials/              # Template partials
│       └── components/            # ADR-041: _<name>.html (underscore prefix!)
├── tests/                         # Test-Infrastruktur (ADR-058)
│   ├── __init__.py
│   ├── conftest.py
│   ├── factories.py
│   └── test_auth.py
├── requirements.txt               # Oder requirements/base.txt + dev.txt
├── requirements-test.txt          # platform-context[testing]>=0.3.1 (ADR-058)
├── docker-compose.prod.yml        # Production Compose (siehe Step 3.3)
├── pyproject.toml                 # Projekt-Metadaten + pytest config
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

**Empfohlen: Split-Settings** (`config/settings/base.py` + `production.py` + `test.py`).

**`config/settings/base.py`** (gemeinsame Settings):

```python
import os

SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production")
DEBUG = os.environ.get("DEBUG", "false").lower() == "true"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost").split(",")
CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()
]

import dj_database_url
DATABASES = {"default": dj_database_url.config(default="sqlite:///db.sqlite3")}
```

**`config/settings/production.py`**:

```python
from .base import *  # noqa: F401,F403

DEBUG = False
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
```

**`config/settings/test.py`** (PFLICHT für pytest):

```python
from .base import *  # noqa: F401,F403

DEBUG = True
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
WHITENOISE_MANIFEST_STRICT = False
STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"
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
IMAGE_TAG=latest
```

### 1.5 `.dockerignore` erstellen (PFLICHT)

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

### 1.6 Test-Infrastruktur einrichten (PFLICHT — ADR-058)

Vollständige Anleitung: `.windsurf/workflows/testing-setup.md`

**Kurzfassung:**

```bash
# requirements-test.txt
platform-context[testing]>=0.3.1
pytest-django>=4.8
factory-boy>=3.3
```

```python
# tests/conftest.py
from platform_context.testing.fixtures import (  # noqa: F401
    admin_client, admin_user, auth_client,
)
import pytest

@pytest.fixture
def user(db):
    from tests.factories import UserFactory
    return UserFactory()
```

```ini
# pyproject.toml
[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "config.settings.test"
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "--tb=short -q"
```

## Step 2: GitHub Actions CI/CD

Erstelle `.github/workflows/ci-cd.yml`:

```yaml
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
  ci:
    name: "CI"
    uses: achimdehnert/platform/.github/workflows/_ci-python.yml@main
    with:
      python_version: "3.12"
      coverage_threshold: 80
      platform_context_version: ">=0.3.1"
      requirements_file: "requirements.txt"
      test_requirements_file: "requirements-test.txt"
      django_settings_module: "config.settings.test"
      skip_tests: ${{ inputs.skip_tests || false }}
      enable_security_scan: true
    secrets: inherit

  build:
    name: "Build"
    needs: [ci]
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    uses: achimdehnert/platform/.github/workflows/_build-docker.yml@main
    with:
      dockerfile: "docker/app/Dockerfile"
      scan_image: true
    secrets: inherit

  deploy:
    name: "Deploy"
    needs: [build]
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    uses: achimdehnert/platform/.github/workflows/_deploy-hetzner.yml@main
    with:
      app_name: <REPO_NAME>
      deploy_path: /opt/<REPO_NAME>
      health_url: https://<DOMAIN>/livez/
      compose_file: docker-compose.prod.yml
      web_service: <REPO_NAME>-web
      run_migrations: true
      enable_rollback: true
    secrets: inherit
```

### GitHub Secrets (MÜSSEN im Repo gesetzt sein)

| Secret | Wert |
|--------|------|
| `DEPLOY_HOST` | `88.198.191.108` |
| `DEPLOY_USER` | `root` |
| `DEPLOY_SSH_KEY` | SSH Private Key |

## Step 3: Docker Setup

### 3.1 Dockerfile (`docker/app/Dockerfile`)

```dockerfile
FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim

LABEL org.opencontainers.image.title="<REPO_NAME>" \
      org.opencontainers.image.description="<DESCRIPTION>" \
      org.opencontainers.image.version="1.0.0"

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local
WORKDIR /app
COPY . .

RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
RUN chown -R appuser:appgroup /app

COPY docker/app/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/livez/')"

USER appuser
EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
CMD ["web"]
```

**KRITISCH:** Healthcheck nutzt `127.0.0.1` (nicht `localhost`) — `localhost` kann HTTP 400 erzeugen wenn ALLOWED_HOSTS es nicht enthält.

### 3.2 `entrypoint.sh`

```bash
#!/bin/bash
set -e

case "$1" in
  web)
    python manage.py migrate --noinput
    python manage.py collectstatic --noinput
    exec gunicorn config.wsgi:application \
      --bind 0.0.0.0:8000 \
      --workers 2 \
      --timeout 120 \
      --access-logfile -
    ;;
  worker)
    exec celery -A config worker --loglevel=info
    ;;
  beat)
    exec celery -A config beat --loglevel=info
    ;;
  *)
    exec "$@"
    ;;
esac
```

### 3.3 `docker-compose.prod.yml`

```yaml
services:
  <REPO>-web:
    image: ghcr.io/achimdehnert/<REPO>:${IMAGE_TAG:-latest}
    container_name: <REPO_UNDERSCORE>_web
    restart: unless-stopped
    env_file: .env.prod
    ports:
      - "127.0.0.1:<PORT>:8000"
    healthcheck:
      test: ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/livez/')\""]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    depends_on:
      <REPO>-db:
        condition: service_healthy
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

  <REPO>-db:
    image: postgres:16-alpine
    container_name: <REPO_UNDERSCORE>_db
    restart: unless-stopped
    env_file: .env.prod
    volumes:
      - <REPO_UNDERSCORE>_pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5
    deploy:
      resources:
        limits:
          memory: 256M
    networks:
      - <REPO_UNDERSCORE>_network

volumes:
  <REPO_UNDERSCORE>_pgdata:

networks:
  <REPO_UNDERSCORE>_network:
    driver: bridge
```

## Step 4: Health-Check Endpoints

### 4.1 Standardisierte Endpoints (N-02)

| Endpoint | Zweck | Prüft | Für |
|----------|-------|-------|-----|
| `/livez/` | Liveness | App-Prozess lebt | **Docker Healthcheck** |
| `/healthz/` | Readiness | App + DB-Verbindung | Monitoring |
| `/health/` | Backwards-Compat | Alias für `/livez/` | Legacy |

**`config/urls.py`:**

```python
from django.http import HttpResponse, JsonResponse
from django.db import connection
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

@csrf_exempt
@require_GET
def liveness(request):
    return HttpResponse("ok")

@csrf_exempt
@require_GET
def readiness(request):
    try:
        connection.ensure_connection()
        return JsonResponse({"status": "ok", "db": "connected"})
    except Exception as e:
        return JsonResponse({"status": "error", "db": str(e)}, status=503)

urlpatterns = [
    path("livez/", liveness, name="liveness"),
    path("healthz/", readiness, name="healthz"),
    path("health/", liveness, name="health-check"),
    # ... andere URLs
]
```

### 4.2 Healthcheck-Regeln (KRITISCH — ADR-022)

| Regel | Begründung |
|-------|------------|
| **IMMER `127.0.0.1` statt `localhost`** | `localhost` kann IPv6 auflösen → Verbindungsfehler |
| **IMMER `python urllib` statt `curl`** | Slim Python-Images haben kein `curl` |
| **`csrf_exempt` + `require_GET`** | Health-Endpoints brauchen kein CSRF, nur GET |
| **Docker-HC nutzt `/livez/`** | Liveness = minimal, keine DB-Abhängigkeit |
| **Monitoring nutzt `/healthz/`** | Readiness = prüft DB, kann 503 zurückgeben |

## Step 5: Server-Infrastruktur einrichten

### 5.1 Deployment-Verzeichnis auf Server erstellen

```bash
ssh root@88.198.191.108 "mkdir -p /opt/<REPO>"
```

### 5.2 `.env.prod` auf Server erstellen

```bash
scp .env.prod root@88.198.191.108:/opt/<REPO>/.env.prod
```

### 5.3 `docker-compose.prod.yml` auf Server kopieren

```bash
scp docker-compose.prod.yml root@88.198.191.108:/opt/<REPO>/docker-compose.prod.yml
```

### 5.4 Nginx Server-Block erstellen

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
    }
}
```

### 5.5 SSL-Zertifikat holen

```bash
ssh root@88.198.191.108 "certbot certonly --webroot -w /var/www/html -d <DOMAIN> --non-interactive --agree-tos --email achim@dehnert.com"
```

### 5.6 DNS A-Record erstellen

```
<DOMAIN> → 88.198.191.108 (TTL 60)
```

## Step 6: Platform-Integration

### 6.1 registry/repos.yaml aktualisieren (PFLICHT — Single Source of Truth)

Füge das neue Repo in `platform/registry/repos.yaml` ein:

```yaml
- name: <REPO_NAME>
  repo: <REPO_NAME>
  description: <DESCRIPTION>
  github: achimdehnert/<REPO_NAME>
  deployed: true
  url: https://<DOMAIN>
  type: django
  lifecycle: experimental   # → production wenn stabil
  dockerfile: docker/app/Dockerfile
  compose: docker-compose.prod.yml
  coverage_threshold: 80
```

**Danach:** GitHub Action `sync-registry-to-devhub.yml` triggert automatisch → devhub.iil.pet/repos zeigt das neue Repo.

### 6.2 MCP-Orchestrator registrieren

Füge das Repo in `mcp-hub/orchestrator_mcp/local_tools.py` hinzu:

```python
"<REPO>": "/home/dehnert/github/<REPO>",
```

### 6.3 Deploy-Workflow aktualisieren

Füge die neue App zur Tabelle in `.windsurf/workflows/deploy.md` hinzu.

### 6.4 Backup-Workflow aktualisieren

Füge die neue DB zur Tabelle in `.windsurf/workflows/backup.md` hinzu.

### 6.5 Workstation SSH-Setup prüfen (ADR-060)

Sicherstellen dass kein `core.sshCommand` im neuen Repo gesetzt wird:

```bash
# NIEMALS setzen:
# git config core.sshCommand "ssh -i ~/.ssh/github_ed25519 ..."

# Standard: ~/.ssh/config mit id_ed25519 greift automatisch
ssh -T git@github.com  # → Hi achimdehnert!
```

## Step 7: Verifikation

### Checkliste (ALLE Punkte müssen grün sein)

```text
✅ Verifikation für [REPO]

Repo-Struktur:
  [ ] docker/app/Dockerfile existiert (mit 127.0.0.1 Healthcheck)
  [ ] docker/app/entrypoint.sh existiert (chmod +x)
  [ ] docker-compose.prod.yml existiert
  [ ] .github/workflows/ci-cd.yml existiert (coverage_threshold: 80)
  [ ] .env.example existiert
  [ ] /livez/ Health-Endpoint existiert (csrf_exempt, require_GET)
  [ ] pyproject.toml mit [tool.pytest.ini_options]
  [ ] README.md mit Quickstart
  [ ] apps/<app>/components/ Verzeichnis existiert (ADR-041)
  [ ] templates/<app>/components/ Verzeichnis existiert

Testing (ADR-058):
  [ ] requirements-test.txt mit platform-context[testing]>=0.3.1
  [ ] tests/__init__.py existiert
  [ ] tests/conftest.py importiert platform_context.testing.fixtures
  [ ] tests/factories.py mit UserFactory
  [ ] config/settings/test.py mit WHITENOISE_MANIFEST_STRICT=False
  [ ] pytest tests/ -v läuft lokal ohne Fehler

Platform-Integration:
  [ ] platform/registry/repos.yaml Eintrag hinzugefügt
  [ ] devhub.iil.pet/repos zeigt neues Repo (nach GitHub Action)
  [ ] deploy.md Tabelle aktualisiert
  [ ] backup.md Tabelle aktualisiert

Server:
  [ ] /opt/<REPO>/ Verzeichnis existiert
  [ ] .env.prod mit echten Werten
  [ ] docker-compose.prod.yml kopiert
  [ ] Container starten und sind healthy

Netzwerk:
  [ ] DNS A-Record zeigt auf 88.198.191.108
  [ ] Nginx Config deployed
  [ ] SSL-Zertifikat aktiv
  [ ] https://<DOMAIN>/livez/ gibt "ok"

CI/CD:
  [ ] GitHub Secrets gesetzt (DEPLOY_HOST, DEPLOY_USER, DEPLOY_SSH_KEY)
  [ ] Push auf main triggert CI (grün)
  [ ] CD deployt auf Server
  [ ] Kein core.sshCommand in .git/config (ADR-060)
```

## Referenz: Bestehende Repos als Vorlage

| Vorlage für | Bestes Beispiel |
|-------------|----------------|
| CI/CD mit Reusable Workflows | `risk-hub/.github/workflows/` |
| Dockerfile + Entrypoint | `risk-hub/docker/app/` |
| docker-compose.prod.yml | `risk-hub/docker-compose.prod.yml` |
| Test-Infrastruktur (conftest, factories) | `travel-beat/tests/` |
| registry/repos.yaml | `platform/registry/repos.yaml` |
| SSH-Setup | ADR-060 |
