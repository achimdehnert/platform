---
description: Onboard a new or existing repository into the platform ecosystem with consistent CI/CD, Docker, database, Nginx, and naming conventions
---

# Repository Onboarding & Compliance Workflow

## Trigger

User says one of:

**New repo:**
- "Neues Repo onboarden: [name]"
- "Onboard [name] into the platform"
- "Setup [name] wie die anderen Repos"

**Existing repo (platform-konform machen):**
- "[name] platform-konform machen"
- "Reflex review fixen für [name]"
- "Compliance-Onboarding für [name]"

## Mode Detection

Determine the mode based on whether the repo already exists:

```python
# Automatic detection:
repo_path = Path(os.environ.get("GITHUB_DIR", Path.home() / "github")) / repo_name
if (repo_path / ".git").exists():
    mode = "compliance"   # Existing repo → diagnose + fix
else:
    mode = "new"          # New repo → full scaffold
```

| Mode | Behavior |
|------|----------|
| `new` | Full scaffold: create structure, Docker, CI/CD, DNS, deploy |
| `compliance` | Diagnose with `reflex review` → fix only what's missing |

## Step 0: REFLEX Review Diagnostic (compliance mode)

**Skip this step for `new` mode** — jump to Step 0.1.

For existing repos, run `reflex review` first to diagnose what's missing:

// turbo
```bash
cd ${GITHUB_DIR:-$HOME/github}/iil-reflex && .venv/bin/python -m reflex review all <REPO_NAME>
```

This gives a structured list of findings (BLOCK/WARN/INFO). Focus on:
- **BLOCK findings** → must fix before deploy
- **WARN findings** → should fix for compliance
- **INFO findings** → nice-to-have

Present findings summary to user:

```text
📋 REFLEX Review für [name]:

  BLOCK: X findings (müssen gefixt werden)
  WARN:  Y findings (sollten gefixt werden)
  INFO:  Z findings (optional)

Soll ich alle BLOCKs automatisch fixen? [Ja/Nein]
Soll ich auch WARNs fixen? [Ja/Nein]
```

Then execute only the relevant steps below — skip steps where the repo already passes.

For baseline management on first compliance run:

```bash
cd ${GITHUB_DIR:-$HOME/github}/iil-reflex && .venv/bin/python -m reflex review all <REPO_NAME> --init-baseline
```

---

## Step 0.0: GITHUB_DIR + Platform-Umgebung sicherstellen (PFLICHT — allererster Schritt)

> Läuft auf der **Entwickler-Maschine**, NICHT auf dem Server.
> Stellt sicher, dass alle Tools und Pfade stimmen, bevor das Repo angelegt wird.

// turbo
```bash
# 1. GITHUB_DIR sicherstellen
if ! grep -q "GITHUB_DIR" ~/.bashrc 2>/dev/null; then
  echo "" >> ~/.bashrc
  echo "export GITHUB_DIR=\"\$HOME/github\"" >> ~/.bashrc
  echo "⚙️  GITHUB_DIR in ~/.bashrc eingetragen — ggf. auf tatsächlichen Pfad anpassen"
fi
export GITHUB_DIR="${GITHUB_DIR:-$HOME/github}"
echo "✅ GITHUB_DIR=${GITHUB_DIR}"

# 2. Platform-Repo aktuell?
git -C "${GITHUB_DIR}/platform" pull --rebase --quiet && echo "✅ platform aktuell"

# 3. Repo-Verzeichnis vorhanden?
REPO_NAME="<REPO_NAME>"  # ← hier einsetzen
ls "${GITHUB_DIR}/${REPO_NAME}" 2>/dev/null && echo "ℹ️  Repo existiert lokal (compliance mode)" || echo "ℹ️  Repo noch nicht lokal (new mode)"
```

---

## Step 0.1: Gather Information

Ask the user:

```text
📋 Neues Repo: [name]

Ich brauche folgende Infos:
1. App-Beschreibung (1 Satz)
2. Production-Domain (z.B. myapp.iil.pet oder custom-domain.com)
3. Braucht die App Celery/Worker? [Ja/Nein]
4. Braucht die App eine eigene Datenbank? [Ja/Nein] (Standard: Ja)
```

### Automatische Port-Vergabe (ADR-157)

Port wird **automatisch** ermittelt — KEINE manuelle Port-Map mehr nötig:

// turbo
```bash
python ${GITHUB_DIR:-$HOME/github}/platform/infra/scripts/port_audit.py --next-free
```

Den ausgegebenen Port als `prod` UND `staging` in `ports.yaml` eintragen.
Staging-Port = Prod-Port (gleicher Port auf verschiedenen Servern, ADR-157).

**Dann Duplikat-Check:**

// turbo
```bash
python ${GITHUB_DIR:-$HOME/github}/platform/infra/scripts/port_audit.py --offline
```

**Dann Nginx-Configs generieren:**

```bash
python ${GITHUB_DIR:-$HOME/github}/platform/infra/scripts/nginx_gen.py --service <REPO_NAME>
```

**Dann DNS anlegen** (Cloudflare, via Local Script — ADR-156 §8):

```bash
CLOUDFLARE_API_TOKEN=<token> python ${GITHUB_DIR:-$HOME/github}/platform/infra/scripts/dns_staging_sync.py --apply
```

**Dann Registry eintragen:**
- `platform/infra/ports.yaml` — Service-Eintrag
- `platform/registry/github_repos.yaml` — Repo-Eintrag (PFLICHT — SSoT für alle Automationen)
- `python infra/scripts/validate_repos.py` — Konsistenz prüfen

## Step 0.9: Architecture Context laden (iil-adrfw v0.4.0)

Bevor das Repo strukturiert wird — welche ADRs gelten?

**Narrative Zusammenfassung für Onboarding:**
```
MCP: mcp2_adr_narrate(audience="new_dev", domain=null, path_filter=null)
→ Erzeugt eine verständliche Zusammenfassung aller Platform-ADRs
→ Audience "new_dev": erklärt Warum + Was, ohne tiefe Implementierungsdetails
→ Output als Markdown — kann direkt in CORE_CONTEXT.md des neuen Repos übernommen werden
```

**Repo-spezifische ADR-Constraints ermitteln:**
```
MCP: mcp2_adr_query(question="Which architecture rules apply to a new Django hub?", domain="django/models")
→ Liefert die konkreten Rules die beim Scaffolding beachtet werden müssen

MCP: mcp2_adr_query(question="What are the deployment requirements?", domain="deployment")
→ Docker, Compose, Health-Endpoint Requirements für das neue Repo
```

→ Ergebnis zusammenfassen und dem User als "Architecture Briefing" präsentieren.
→ Bei `open_questions` in der Antwort: User darauf hinweisen, dass hier noch keine ADR-Entscheidung existiert.

---

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

### 1.1a Golden-Path-Templates einrichten (NEU 2026-04-28)

**Automatisiert mit `setup_repo.py` — kein manuelles Kopieren:**

```bash
REPO_NAME="<REPO_NAME>"
PORT="<PORT>"   # aus port_audit.py --next-free
PLATFORM_DIR="${GITHUB_DIR:-$HOME/github}/platform"
REPO_PATH="${GITHUB_DIR:-$HOME/github}/${REPO_NAME}"

python3 "$PLATFORM_DIR/scripts/setup_repo.py" "$REPO_NAME" \
  --port="$PORT" \
  --settings="config.settings.test"
```

Erstellt: `Dockerfile`, `docker-compose.prod.yml`, `.github/workflows/ci.yml`,
`.env.example`, `cliff.toml`, `.importlinter`, `renovate.json`

→ Danach Platzhalter in generierten Dateien prüfen (`REPO_NAME`, `PORT` wurden bereits ersetzt).
→ Dann `gen_django_app.py` für die erste App:

```bash
python3 "$PLATFORM_DIR/scripts/gen_django_app.py" "$REPO_NAME" "<app_name>"
```

→ Danach `gen_test_scaffold.py`:

```bash
python3 "$PLATFORM_DIR/scripts/gen_test_scaffold.py" "$REPO_NAME"
```

---

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

USER appuser
EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
CMD ["web"]
```

**KRITISCH — KEIN `HEALTHCHECK` IM DOCKERFILE:**
- `HEALTHCHECK` im Dockerfile gilt für **alle** Container die aus dem Image starten (web, worker, beat).
- Worker und Beat haben keinen Web-Server → Healthcheck schlägt fehl → Restart-Loop.
- **Regel:** Healthchecks IMMER in `docker-compose.prod.yml` pro Service definieren, NIE im Dockerfile.

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
    mkdir -p /celerybeat
    chown -R appuser:appgroup /celerybeat 2>/dev/null || true
    exec celery -A config beat --loglevel=info \
      --schedule=/celerybeat/celerybeat-schedule
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
      - bf_platform_prod

  <REPO>-db:
    image: postgres:16-alpine
    container_name: <REPO_UNDERSCORE>_db
    restart: unless-stopped
    env_file: .env.prod
    volumes:
      - <REPO_UNDERSCORE>_pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5
    deploy:
      resources:
        limits:
          memory: 256M
    networks:
      - bf_platform_prod

  <REPO>-redis:
    image: redis:7-alpine
    container_name: <REPO_UNDERSCORE>_redis
    restart: unless-stopped
    networks:
      - bf_platform_prod

volumes:
  <REPO_UNDERSCORE>_pgdata:

networks:
  bf_platform_prod:
    external: true
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
]
```

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

### 6.1 Registry aktualisieren (PFLICHT — beide Dateien, keine Ausnahme)

> **Warum beide?** `github_repos.yaml` ist SSoT für alle Plattform-Automationen:
> `runner-health.yml` (täglicher Label-Check), `sync-workflows.sh`, concurrency-batch-fixes.
> Fehlt ein Repo hier → runner-health ignoriert es → stuck deploys nicht erkannt.
> **Kein "Operator" nötig — Onboarding IS die Registrierung.**

#### 6.1a `platform/registry/repos.yaml` (Catalog-Sync)

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

#### 6.1b `platform/registry/github_repos.yaml` (Automation SSoT — PFLICHT)

```yaml
# In django_apps: section eintragen:
django_apps:
  <REPO_NAME>:
    github: achimdehnert/<REPO_NAME>
    description: <DESCRIPTION>
    deployed: true
    domain: <DOMAIN>
    port: <PORT>
    lifecycle: experimental
```

```bash
# Konsistenz prüfen nach dem Eintrag:
python ${GITHUB_DIR:-$HOME/github}/platform/infra/scripts/validate_repos.py
```

> **Ohne diesen Eintrag:** `runner-health.yml` ignoriert das Repo täglich.
> Der nächste Runner-Health-Run meldet `⚠️ UNREGISTERED RUNNER` als Drift-Warning —
> aber dann ist der Schaden bereits eingetreten. **Besser: hier eintragen, Drift-Warning nie sehen.**

### 6.2 MCP-Orchestrator registrieren

Füge das Repo in `mcp-hub/orchestrator_mcp/local_tools.py` hinzu:

```python
"<REPO>": "${GITHUB_DIR:-$HOME/github}/<REPO>",
```

### 6.3 Deploy-Workflow aktualisieren

Füge die neue App zur Tabelle in `.windsurf/workflows/deploy.md` hinzu.

### 6.4 Backup-Workflow aktualisieren

Füge die neue DB zur Tabelle in `.windsurf/workflows/backup.md` hinzu.

### 6.5 Outline Repo-Steckbrief erstellen (PFLICHT — ADR-145)

Erstelle einen Repo-Steckbrief in Outline (Runbooks Collection) damit Cascade bei jeder Session sofort den Kontext hat:

```
outline-knowledge: create_runbook(
    title="Repo-Steckbrief: <REPO_NAME>",
    content="# <REPO_NAME> — Repo-Steckbrief\n\n> **Zweck:** <DESCRIPTION>\n> Suche hier wenn du am <REPO_NAME> arbeitest.\n\n## Quick Facts\n\n| Key | Value |\n|-----|-------|\n| **Repo** | achimdehnert/<REPO_NAME> |\n| **Domain** | <DOMAIN> |\n| **Port** | <PORT> |\n| **Stack** | Django 5.x, ... |\n| **Server** | 88.198.191.108, /opt/<REPO_NAME> |\n\n## Features\n\n- ...\n\n## Frameworks\n\n- ...\n\n## Bekannte Einschränkungen\n\n- ...\n\n## Nächste Schritte\n\n- ...",
    related_adrs="120"
)
```

### 6.6 ADR Architecture Narrative generieren (iil-adrfw)

```
MCP: mcp2_adr_narrate(
    audience="new_dev",
    domain="<domain>",
    scope_label="<REPO_NAME>"
)
```

### 6.7 REFLEX Review Setup (PFLICHT — ADR-165)

**6.7.1 Dev-Dependency hinzufügen:**

```bash
echo "iil-reflex>=0.5.0" >> <REPO>/requirements-dev.txt
```

**6.7.2 reflex.yaml generieren:**

// turbo
```bash
cd ${GITHUB_DIR:-$HOME/github}/iil-reflex && .venv/bin/python -m reflex init \
    --hub <REPO_NAME> \
    --tier <TIER> \
    --port <PORT> \
    --output ${GITHUB_DIR:-$HOME/github}/<REPO_NAME>/reflex.yaml
```

**6.7.3 Initial Baseline setzen:**

// turbo
```bash
cd ${GITHUB_DIR:-$HOME/github}/iil-reflex && .venv/bin/python -m reflex review all <REPO_NAME> --init-baseline
```

### 6.8 Windsurf Platform-Integration (PFLICHT — neues Repo weiß sofort alles)

// turbo
```bash
REPO_NAME="<REPO_NAME>"  # ← hier einsetzen
REPO_PATH="${GITHUB_DIR:-$HOME/github}/${REPO_NAME}"

# 1. Repo in repo-registry.yaml eintragen (falls noch nicht drin)
grep -q "name: ${REPO_NAME}" "${GITHUB_DIR:-$HOME/github}/platform/scripts/repo-registry.yaml" \
  && echo "ℹ️  ${REPO_NAME} bereits in registry" \
  || echo "⚠️  Bitte ${REPO_NAME} manuell in platform/scripts/repo-registry.yaml eintragen"

# 2. .windsurf/ Verzeichnis anlegen
mkdir -p "${REPO_PATH}/.windsurf/workflows"
echo "✅ .windsurf/workflows/ angelegt"

# 3. Workflow-Symlinks verteilen
GITHUB_DIR="${GITHUB_DIR:-$HOME/github}" \
  bash "${GITHUB_DIR:-$HOME/github}/platform/scripts/sync-workflows.sh" "${REPO_NAME}" \
  2>&1 | grep -E "LINK|REPLACE|WARN" | head -20
echo "✅ Workflow-Symlinks deployed"

# 4. project-facts.md generieren
python3 "${GITHUB_DIR:-$HOME/github}/platform/scripts/gen_project_facts.py" \
  --repo "${REPO_NAME}" 2>/dev/null
echo "✅ project-facts.md generiert"
```

### 6.9 Branch Protection einrichten (PFLICHT — ADR-174, alle Repos)

**GitHub → [Repo] → Settings → Branches → Add rule:**

```
Branch name pattern:  main

☑ Require a pull request before merging
☑ Require status checks to pass before merging
  Required checks:
    → "QM Gate — ASSUMPTION Check (ADR-174)"
  ☑ Require branches to be up to date before merging
☑ Do not allow bypassing the above settings
```

---

## Step 7: Verifikation

→ **[`docs/onboarding/onboard-repo-checklist.md`](../../docs/onboarding/onboard-repo-checklist.md)**

**Quick-Check vor Abschluss:**

// turbo
```bash
set -euo pipefail
REPO_NAME="<REPO_NAME>"
cd ${GITHUB_DIR:-$HOME/CascadeProjects}/iil-reflex
.venv/bin/python -m reflex review all "$REPO_NAME" --fail-on block
```

Sobald grün → Baseline setzen + Onboarding abschließen.
