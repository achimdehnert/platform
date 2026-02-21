---
status: accepted
date: 2026-02-21
decision-makers: Achim Dehnert
---

# ADR-022: Platform Consistency Standard (v3)

- **Status**: Accepted (Phase 0-4 implementiert)
- **Date**: 2026-02-10 (v3: Input-Review eingearbeitet, Referenz-Templates)
- **Updated**: 2026-02-10 (Phase 0-4 abgeschlossen, repo_checker Tool)
- **Supersedes**: ADR-022 v1, v2
- **Relates to**: ADR-021 (Unified Deployment Pattern)

---

## 1. Kontext und Motivation

Die Platform besteht aus 7 Repositories auf einem gemeinsamen Hetzner-Server.
Eine systematische Analyse aller Repos (Dockerfiles, Compose-Files, Settings,
Workflows, Entrypoints, Git-Remotes, Health-Endpoints) am 2026-02-10 ergab
**signifikante Inkonsistenzen in 8 Dimensionen**.

Dieses ADR dokumentiert den **exakten IST-Zustand**, definiert den
**verbindlichen SOLL-Zustand** mit **4 offiziellen Referenz-Templates**,
identifiziert **Generalisierungen** und beschreibt den **Migrationsplan**.

### 1.1 Referenz-Templates

Die folgenden Dateien in `platform/docs/adr/input/` sind die **kanonische
Referenz-Implementierung** fuer alle Projekte:

| Datei | Zweck |
| --- | --- |
| `input/Dockerfile` | Multi-stage, non-root, OCI-Labels, HEALTHCHECK |
| `input/docker-compose.prod.yml` | Migrate-Service, env_file, Memory-Limits |
| `input/entrypoint.sh` | web/worker/beat, set -euo pipefail, Exit-Codes |
| `input/healthz.py` | Liveness/Readiness, HEALTH_PATHS, Middleware-Exclusion |

Jedes Projekt MUSS diese Templates als Basis nutzen und NUR projekt-spezifische
Abweichungen (z.B. zusaetzliche System-Dependencies) vornehmen.

---

## 2. IST-Zustand (faktisch, Stand 2026-02-10)

### 2.1 Git Remote URLs

| Repo | Remote-Typ | Befund |
| --- | --- | --- |
| bfagent | HTTPS+PAT | KRITISCH: Token im Klartext |
| mcp-hub | HTTPS+PAT | KRITISCH: Gleicher Token im Klartext |
| pptx-hub | HTTPS | Nicht konform, kein Token |
| risk-hub | SSH | OK |
| travel-beat | SSH | OK |
| weltenhub | SSH | OK |
| platform | SSH | OK |

### 2.2 Dockerfile-Vergleich

| Dimension | bfagent | risk-hub | travel-beat | weltenhub | pptx-hub |
| --- | --- | --- | --- | --- | --- |
| Pfad | Root | docker/app/ | docker/ | Root | docker/app/ |
| Python | 3.11 | 3.12 | 3.12 | 3.12 | 3.12 |
| Multi-Stage | Nein | Nein | Nein | **Ja** | Nein |
| Non-Root | Nein | Nein | **Ja** | **Ja** | Nein |
| HEALTHCHECK | Nein | Nein | curl /health/ | curl /health/ | python /health/ |
| OCI-Labels | Nein | Nein | Nein | Ja (manuell) | Nein |
| Deps | requirements.txt | pip inline | requirements/prod.txt | requirements.txt+wheels | pyproject.toml |

### 2.3 Docker-Compose Vergleich

| Dimension | bfagent | risk-hub | travel-beat | weltenhub | pptx-hub |
| --- | --- | --- | --- | --- | --- |
| Pfad | Root | Root | docker/ (NICHT Root) | Root | Root |
| Duplikate | 0 | 0 | **3** | 0 | 0 |
| version: Key | Nein | Nein | **3.8** (deprecated) | Nein | Nein |
| Migrate-Service | Nein | Nein | Nein | Nein | Nein |
| env-Methode | environment+${VAR} | environment+${VAR} | **Beides** (!) | env_file: .env | env_file: .env.prod |
| Nginx-Port | 8088 (Caddy) | 8090 (direkt) | 8089 (Caddy) | 8081 (direkt) | 8020 (direkt) |
| Image-Tag Var | BFAgent_IMAGE_TAG | IMAGE_TAG | TRAVELBEAT_IMAGE_TAG | IMAGE_TAG | PPTX_HUB_IMAGE_TAG |
| Memory-Limit | 512M | 512M | 512M | **Fehlt** | 512M |
| Logging | json-file | json-file | json-file | **Fehlt** | json-file |
| DB | pg16 (shared) | pg16 (eigen) | **pg15** (eigen) | shared (bfagent_db) | pg16 (eigen) |
| Netzwerk | bf_platform_prod | risk_hub_network | **bfagent_platform** (FALSCH) | bf_platform_prod | keins |

### 2.4 Health-Endpoints

| Repo | /livez/ | /healthz/ | HEALTH_PATHS | csrf_exempt | require_GET |
| --- | --- | --- | --- | --- | --- |
| bfagent | Ja | Ja | Nein | Nein | Nein |
| risk-hub | Ja | Ja | Nein | Nein | Nein |
| travel-beat | Ja | Ja | Nein | Nein | Nein |
| weltenhub | Ja | Ja | Nein | Nein | Nein |
| pptx-hub | **FEHLT** | **FEHLT** | n/a | n/a | n/a |

**Kritisch**: Kein Projekt hat `HEALTH_PATHS` fuer Middleware-Exclusion.
Docker-Healthchecks kommen von `http://127.0.0.1:8000/livez/` — ohne Subdomain.
Die SubdomainTenantMiddleware kann diese Requests ablehnen.

### 2.5 Settings-Struktur

| Repo | DJANGO_SETTINGS_MODULE | Pattern |
| --- | --- | --- |
| bfagent | config.settings | Dispatcher + settings/ dir + settings.py Datei (Konflikt!) |
| risk-hub | config.settings | Einzelne Datei |
| travel-beat | config.settings.production | Split-dir (base/dev/prod/test) |
| weltenhub | config.settings.production | Split-dir (base/dev/prod) |
| pptx-hub | n/a | Kein Django-Config-Pattern |

### 2.6 CI/CD Workflows

| Repo | Platform Reusable Workflows | Status |
| --- | --- | --- |
| risk-hub | ci + build + deploy | Vollstaendig migriert |
| travel-beat | ci + build + deploy | Migriert, skip_tests=true |
| bfagent | Nein (3 eigene Workflows) | Nicht migriert |
| weltenhub | Nein (eigene, Deploy-Stub) | Deploy tut nichts |
| pptx-hub | Nein (eigene, PyPI-fokus) | Kein Server-Deploy |

### 2.7 Entrypoint-Pattern

| Repo | Methode | Migrate bei | Shell | Error-Handling |
| --- | --- | --- | --- | --- |
| bfagent | entrypoint.web.sh | Start | bash, set -euo pipefail | Gut |
| risk-hub | entrypoint.sh (web/worker) | Start | sh, set -e | Basis |
| travel-beat | Dockerfile CMD | Build | n/a | Keins |
| weltenhub | Dockerfile CMD | Build | n/a | Keins |
| pptx-hub | Dockerfile CMD | Nie | n/a | Keins |

### 2.8 Server-Zustand

| App | /opt/-Pfad | Deploy IST |
| --- | --- | --- |
| bfagent | /opt/bfagent-app | git pull + compose (Git auf Server) |
| risk-hub | /opt/risk-hub | Image-Pull via _deploy-hetzner (SAUBER) |
| travel-beat | /opt/travel-beat | Image-Pull via _deploy-hetzner (SAUBER) |
| weltenhub | /opt/weltenhub | tar/scp/build ON SERVER |
| pptx-hub | n/a | Nicht provisioniert |

---

## 3. SOLL-Zustand (Ziel-Architektur)

### 3.1 Architektur-Entscheidungen

| # | Entscheidung | Begruendung |
| --- | --- | --- |
| A1 | Migration als separater Compose-Service | Verhindert Race Conditions bei parallelem Start |
| A2 | Entrypoint fuer Prozess-Start, nicht fuer Migrations | Separation of Concerns |
| A3 | collectstatic bei Docker-Build, nicht bei Start | Deterministische Builds, schnellerer Start |
| A4 | HEALTH_PATHS in healthz.py als importierbare Konstante | Middleware-Exclusion ohne Hardcoding |
| A5 | `@csrf_exempt` + `@require_GET` auf Health-Endpoints | Sicherheit: kein CSRF-Token bei Healthchecks, nur GET |
| A6 | `127.0.0.1` statt `localhost` in HEALTHCHECK | Vermeidet DNS-Lookup im Container |
| A7 | `set -euo pipefail` in Entrypoint | Strenge Fehlerbehandlung, undefinierte Vars = Abbruch |
| A8 | `env_file` fuer App-Config, `${VAR}` nur fuer Infra | Klare Trennung, keine Precedence-Bugs |

### 3.2 Generalisiertes Deployment-Pattern

```
git push origin main
  -> _ci-python@v1 (lint+test)
  -> _build-docker@v1 (GHCR push)
  -> _deploy-hetzner@v1 (ssh pull up healthcheck)
```

Auf dem Server:
```
docker compose pull
docker compose up -d
  1. db startet, wird healthy
  2. migrate laeuft, exitiert mit 0
  3. web + worker starten (depends_on: migrate: service_completed_successfully)
  4. Healthcheck auf /livez/ wird gruen
```

### 3.3 Einheitliche Dateistruktur

```
<repo>/
  .github/workflows/ci-cd.yml        # Platform @v1 Workflows
  docker/app/
    Dockerfile                        # → Referenz: input/Dockerfile
    entrypoint.sh                     # → Referenz: input/entrypoint.sh
  docker-compose.prod.yml             # → Referenz: input/docker-compose.prod.yml
  config/settings/                    # Split: base/dev/prod
    __init__.py                       # Env-Dispatcher
  apps/core/healthz.py                # → Referenz: input/healthz.py
  config/urls.py                      # Health-Routes registriert
```

### 3.4 Referenz-Template: Dockerfile

Siehe `input/Dockerfile`. Kernprinzipien:

- **Multi-stage** (builder → production): Build-Tools nicht im Prod-Image
- **python:3.12-slim** als Base (Debian bookworm)
- **Non-root user** `app` (UID/GID 1000)
- **OCI-Labels** mit `ARG APP_NAME` fuer GHCR-Traceability
- **HEALTHCHECK** via `python urllib` auf `http://127.0.0.1:8000/livez/`
- **collectstatic** bei Build-time mit Dummy-Env (nicht im Entrypoint)
- **Kein curl** im Image (kleinere Attack Surface)

Projekt-spezifische Anpassungen NUR bei:
- Zusaetzliche System-Dependencies (z.B. WeasyPrint: libpango, libcairo)
- Zusaetzliche Python-Packages (z.B. bfagent: lokale Packages)
- Build-Args

### 3.5 Referenz-Template: docker-compose.prod.yml

Siehe `input/docker-compose.prod.yml`. Kernprinzipien:

**Architektur: 4 Services (+ optionale)**

| Service | Funktion | Restart |
| --- | --- | --- |
| `migrate` | Einmalige DB-Migration vor App-Start | `no` (exit nach Erfolg) |
| `web` | Gunicorn, abhaengig von migrate success | `unless-stopped` |
| `worker` | Celery Worker (optional) | `unless-stopped` |
| `db` | PostgreSQL 16 | `unless-stopped` |
| `redis` | Cache + Broker (optional) | `unless-stopped` |

**Variablen-Regel (praezisiert):**

| Variablen-Typ | Wo definiert | Beispiel |
| --- | --- | --- |
| **Infrastruktur** (Image, Port, Volume) | `${VAR}` in Compose, Wert aus `.env.prod` | `${APP_NAME}`, `${IMAGE_TAG:-latest}`, `${APP_PORT:-8000}` |
| **Applikation** (Secrets, Config) | NUR `env_file: .env.prod` | SECRET_KEY, DATABASE_URL, REDIS_URL |

VERBOTEN: `environment:` mit App-Variablen wie `SECRET_KEY=${SECRET_KEY}`.
Diese Methode hat Precedence-Probleme und dupliziert Werte.

**Pflicht fuer jeden Service:**
- `logging: json-file` mit max-size/max-file
- `deploy.resources.limits.memory`
- `restart` Policy (no, unless-stopped)
- `healthcheck` (fuer db, redis, web)

### 3.6 Referenz-Template: entrypoint.sh

Siehe `input/entrypoint.sh`. Kernprinzipien:

- **`#!/bin/bash`** mit **`set -euo pipefail`** (streng)
- **Env-Validation**: `${DJANGO_SETTINGS_MODULE:?ERROR}` — Fail-fast
- **Migration optional**: `ENTRYPOINT_MIGRATE=true` als Escape-Hatch (Default: false,
  weil Migration im separaten Compose-Service laeuft)
- **3 Modi**: web | worker | beat — via Argument
- **Parametrierbar** via ENV: GUNICORN_WORKERS, GUNICORN_TIMEOUT, CELERY_LOG_LEVEL, etc.
- **Dokumentierte Exit-Codes**: 0 (clean), 1 (args/env), 2 (migration)
- **Fehler auf stderr**: `>&2`

### 3.7 Referenz-Template: healthz.py

Siehe `input/healthz.py`. Kernprinzipien:

- **`HEALTH_PATHS = frozenset({"/livez/", "/healthz/"})`** — importierbare Konstante
  fuer Middleware-Exclusion. Die SubdomainTenantMiddleware MUSS diese Pfade
  ausschliessen, da Docker-Healthchecks ohne Subdomain kommen.
- **`@csrf_exempt`** — Healthchecks haben keinen CSRF-Token
- **`@require_GET`** — nur GET erlaubt, kein POST/PUT Missbrauch
- **Liveness** (`/livez/`): Nur Prozess-Check, keine Dependencies → immer 200
- **Readiness** (`/healthz/`): DB-Check, erweiterbar (Redis, S3, etc.) → 200 oder 503
- **Docstrings** mit Return-Dokumentation

**Middleware-Integration** (in SubdomainTenantMiddleware):

```python
from apps.core.healthz import HEALTH_PATHS

class SubdomainTenantMiddleware:
    def __call__(self, request):
        if request.path in HEALTH_PATHS:
            return self.get_response(request)  # bypass tenant resolution
        # ... normal tenant resolution
```

**URL-Registrierung** (in config/urls.py):

```python
from apps.core.healthz import liveness, readiness

urlpatterns = [
    path("livez/", liveness, name="health-liveness"),
    path("healthz/", readiness, name="health-readiness"),
    # ...
]
```

### 3.8 Port-Registry (korrigiert, basierend auf IST)

| Port | App | Methode | Domain |
| --- | --- | --- | --- |
| 8088 | bfagent | Via Caddy | bfagent.iil.pet |
| 8081 | weltenhub | Direkt | weltenforger.com |
| 8089 | travel-beat | Via Caddy | drifttales.app |
| 8090 | risk-hub | Direkt | schutztat.de |
| 8020 | pptx-hub | Direkt | prezimo.com |

Shared Netzwerk: `bf_platform_prod` (bfagent + weltenhub).
Alle anderen: eigenes Bridge-Netzwerk.

### 3.9 SSH-Standard

Ein Key: `~/.ssh/id_ed25519`

| Ziel | Methode |
| --- | --- |
| GitHub | git config --global url."git@github.com:".insteadOf "https://..." |
| Hetzner | ~/.ssh/config Host-Eintrag |
| deployment-mcp | DEPLOYMENT_MCP_SSH_KEY_PATH env var |
| GitHub Actions | secrets.DEPLOY_SSH_KEY (pro Repo) |

### 3.10 CI/CD Workflow Standard

```yaml
# .github/workflows/ci-cd.yml — Alle Projekte nutzen dieses Pattern
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
        description: "Skip tests (emergency only)"
        required: false
        default: false
        type: boolean
jobs:
  ci:
    uses: achimdehnert/platform/.github/workflows/_ci-python.yml@v1
    with:
      python_version: "3.12"
      # Projekt-spezifisch:
      requirements_file: "requirements.txt"
      source_dir: "apps"
      django_settings_module: "config.settings.test"
      skip_tests: ${{ inputs.skip_tests || false }}
    secrets: inherit
  build:
    needs: [ci]
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    uses: achimdehnert/platform/.github/workflows/_build-docker.yml@v1
    with:
      dockerfile: "docker/app/Dockerfile"
      scan_image: true
    secrets: inherit
  deploy:
    needs: [build]
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    uses: achimdehnert/platform/.github/workflows/_deploy-hetzner.yml@v1
    with:
      app_name: "<APP>"
      deploy_path: "/opt/<APP>"
      health_url: "https://<DOMAIN>/healthz/"
      compose_file: "docker-compose.prod.yml"
      run_migrations: true
      enable_rollback: true
    secrets:
      HETZNER_HOST: ${{ secrets.DEPLOY_HOST }}
      HETZNER_USER: ${{ secrets.DEPLOY_USER }}
      HETZNER_SSH_KEY: ${{ secrets.DEPLOY_SSH_KEY }}
```

---

## 4. Delta-Matrix: IST zu SOLL pro Repo

### 4.1 bfagent (hoechster Aufwand)

| Aktion | Aufwand | Prio |
| --- | --- | --- |
| Git Remote SSH + PAT rotieren | 5 min | SOFORT |
| Dockerfile → input/Dockerfile (multi-stage, 3.12, non-root, OCI) | 30 min | Hoch |
| environment: → env_file: .env.prod | 20 min | Hoch |
| Migrate-Service in Compose ergaenzen | 10 min | Hoch |
| healthz.py → input/healthz.py (HEALTH_PATHS, csrf_exempt, require_GET) | 10 min | Hoch |
| Entrypoint → input/entrypoint.sh (kein migrate, set -euo pipefail) | 10 min | Hoch |
| CI/CD → Platform @v1 Workflows | 15 min | Mittel |
| Server: Git-Repo entfernen, nur compose+.env | 30 min | Mittel |

### 4.2 risk-hub (geringster Aufwand, Referenz)

| Aktion | Aufwand | Prio |
| --- | --- | --- |
| environment: → env_file: .env.prod | 15 min | Hoch |
| Migrate-Service in Compose, migrate aus Entrypoint entfernen | 10 min | Hoch |
| healthz.py: HEALTH_PATHS + csrf_exempt + require_GET ergaenzen | 5 min | Hoch |
| Dockerfile → multi-stage + non-root + OCI-Labels | 15 min | Mittel |
| Image-Name vereinfachen | 5 min | Niedrig |

### 4.3 travel-beat (Aufraeumen)

| Aktion | Aufwand | Prio |
| --- | --- | --- |
| Compose → Root, Duplikate loeschen, version: entfernen | 10 min | SOFORT |
| Netzwerk bfagent_platform → travelbeat_network korrigieren | 5 min | SOFORT |
| Compose: Migrate-Service ergaenzen, env_file konsolidieren | 15 min | Hoch |
| healthz.py: HEALTH_PATHS + csrf_exempt + require_GET | 5 min | Hoch |
| Entrypoint → input/entrypoint.sh | 10 min | Hoch |
| Postgres 15 → 16 | DB-Dump | Niedrig |
| CI skip_tests: true → false | Variabel | Mittel |

### 4.4 weltenhub (Server-Migration)

| Aktion | Aufwand | Prio |
| --- | --- | --- |
| Compose: Migrate-Service, Memory-Limits, Logging, env_file .env.prod | 15 min | Hoch |
| Dockerfile → docker/app/, Entrypoint → input/entrypoint.sh | 15 min | Hoch |
| healthz.py: HEALTH_PATHS + csrf_exempt + require_GET | 5 min | Hoch |
| CI/CD Deploy-Stub → Platform @v1 | 15 min | Hoch |
| Server: rsync → Image-Pull (compose+.env only) | 45 min | Hoch |

### 4.5 pptx-hub (Provisioning)

| Aktion | Aufwand | Prio |
| --- | --- | --- |
| Git Remote → SSH | 1 min | SOFORT |
| healthz.py komplett implementieren (input/healthz.py) | 15 min | Hoch |
| Compose: Migrate-Service nach Template | 10 min | Hoch |
| CI/CD → Platform @v1 + Docker-Build + Deploy | 20 min | Mittel |
| Server provisionieren | 30 min | Mittel |

### 4.6 mcp-hub (lokal)

| Aktion | Aufwand | Prio |
| --- | --- | --- |
| Git Remote → SSH + PAT rotieren | 5 min | SOFORT |
| settings.py SSH-Key default → id_ed25519 | 1 min | SOFORT |

---

## 5. Identifizierte Generalisierungen

| # | Pattern | Best-of Quelle | Anwenden auf |
| --- | --- | --- | --- |
| G1 | Multi-stage Dockerfile mit OCI-Labels | weltenhub + input/Dockerfile | Alle 5 Projekte |
| G2 | Non-root User (app:1000) | weltenhub + travel-beat | bfagent, risk-hub, pptx-hub |
| G3 | Separater Migrate-Service (nicht Entrypoint) | input/docker-compose.prod.yml | Alle 5 Projekte |
| G4 | Entrypoint: set -euo pipefail + Exit-Codes + Env-Validation | input/entrypoint.sh | Alle 5 Projekte |
| G5 | Platform Reusable CI/CD Workflows | risk-hub + travel-beat | bfagent, weltenhub, pptx-hub |
| G6 | env_file fuer App-Config, ${VAR} nur fuer Infra | input/docker-compose.prod.yml | bfagent, risk-hub, travel-beat |
| G7 | HEALTH_PATHS + csrf_exempt + require_GET | input/healthz.py | Alle 5 Projekte |
| G8 | HEALTHCHECK: python urllib auf 127.0.0.1 (kein curl) | input/Dockerfile | Alle Dockerfiles |
| G9 | IMAGE_TAG als einziger Tag-Variablenname | input/docker-compose.prod.yml | bfagent, travel-beat, pptx-hub |
| G10 | collectstatic nur Build-time, nie Entrypoint | input/Dockerfile + entrypoint.sh | risk-hub, bfagent |
| G11 | Named Volumes mit ${APP_NAME}_* Prefix | input/docker-compose.prod.yml | Alle 5 Projekte |

---

## 6. Identifizierte Optimierungen

| # | Optimierung | Begruendung | Risiko |
| --- | --- | --- | --- |
| O1 | Shared DB (bfagent+weltenhub) aufbrechen | Migrations-Kollision, keine Isolation | Mittel |
| O2 | CONN_MAX_AGE=600 in Django-Settings | Default 0 = neue Connection pro Request | Keins |
| O3 | curl aus allen Dockerfiles entfernen | Kleinere Attack Surface, python urllib reicht | Keins |
| O4 | Caddy-Proxy evaluieren (bfagent+travel-beat) | Extra Layer vs Nginx direkt | Niedrig |
| O5 | GitHub Org-Level Secrets statt Repo-Level | DRY fuer DEPLOY_HOST/USER/KEY | Keins |
| O6 | Settings __init__.py Dispatcher (liest DJANGO_ENV) | Einheitliches DJANGO_SETTINGS_MODULE | Keins |

---

## 7. Migrationsplan (priorisiert)

### Phase 0: Sicherheit (SOFORT, 10 min, kein Risiko)

- Git Remotes auf SSH: bfagent, mcp-hub, pptx-hub
- PAT Token auf GitHub rotieren (ghp_GFg... revoken)
- deployment-mcp settings.py SSH-Key default → id_ed25519

### Phase 1: Health-Endpoints haerten (30 min, niedriges Risiko)

- Alle 4 Projekte: healthz.py auf input/healthz.py upgraden (HEALTH_PATHS, csrf_exempt, require_GET)
- pptx-hub: healthz.py komplett neu implementieren
- Middleware-Exclusion in SubdomainTenantMiddleware einbauen

### Phase 2: Compose-Architektur (1h, niedriges Risiko)

- Alle Projekte: Migrate-Service nach input/docker-compose.prod.yml Template
- travel-beat: Compose → Root, Duplikate loeschen, version: entfernen, Netzwerk fixen
- weltenhub: Memory-Limits + Logging, env_file → .env.prod
- Entrypoints auf input/entrypoint.sh umstellen (migrate entfernen)

### Phase 3: Dockerfile-Generalisierung (1-2h, mittleres Risiko)

- Alle auf input/Dockerfile Template (multi-stage, non-root, OCI-Labels)
- bfagent: Python 3.11 → 3.12
- Dockerfile-Pfad einheitlich: docker/app/Dockerfile
- collectstatic nur Build-time

### Phase 4: CI/CD-Migration (1h, niedriges Risiko)

- bfagent: Eigene Workflows → Platform @v1
- weltenhub: Deploy-Stub → Platform @v1
- pptx-hub: Docker-Build + Deploy erstellen
- travel-beat: skip_tests: true → false

### Phase 5: Server-Bereinigung (1-2h, mittleres Risiko)

- bfagent: Git-Repo auf Server → compose+.env only
- weltenhub: rsync → Image-Pull
- Erst neuen Deploy verifizieren, dann alten Source archivieren

### Phase 6: Optimierungen (bei Bedarf)

- weltenhub eigene DB-Instanz
- CONN_MAX_AGE in allen Projekten
- Org-Level Secrets
- pptx-hub Server-Provisioning

---

## 8. Compliance-Checkliste

Jedes Projekt gilt als ADR-022 compliant wenn alle Punkte erfuellt sind:

```
[ ] Git remote ist SSH (git@github.com:...)
[ ] Dockerfile: docker/app/Dockerfile basiert auf input/Dockerfile
    - Multi-stage, python:3.12-slim, non-root (app:1000), OCI-Labels
    - HEALTHCHECK: python urllib auf 127.0.0.1:8000/livez/ (kein curl)
    - collectstatic bei Build-time
[ ] Entrypoint: docker/app/entrypoint.sh basiert auf input/entrypoint.sh
    - set -euo pipefail, DJANGO_SETTINGS_MODULE Validation
    - Kein migrate (laeuft als Compose-Service)
    - web/worker/beat Modi, dokumentierte Exit-Codes
[ ] docker-compose.prod.yml basiert auf input/docker-compose.prod.yml
    - EINE Datei im Root, kein version: Key
    - Separater migrate Service (restart: no, service_completed_successfully)
    - env_file: .env.prod fuer App-Config
    - ${VAR} nur fuer Infrastruktur (APP_NAME, IMAGE_TAG, APP_PORT)
    - Alle Services: logging + memory limits + restart policy
    - Port-Binding: 127.0.0.1:<PORT>:8000
    - Named Volumes mit ${APP_NAME}_* Prefix
[ ] healthz.py basiert auf input/healthz.py
    - HEALTH_PATHS = frozenset fuer Middleware-Exclusion
    - @csrf_exempt + @require_GET Dekoratoren
    - Liveness (/livez/) + Readiness (/healthz/)
[ ] SubdomainTenantMiddleware excludiert HEALTH_PATHS
[ ] CI/CD: Platform _ci-python + _build-docker + _deploy-hetzner @v1
[ ] Server: nur compose + .env + scripts/ (kein Source-Code)
[ ] Settings: config/settings/ Verzeichnis (base/dev/prod)
```

### Aktueller Compliance-Status (Stand 2026-02-10, nach Phase 0-4)

| Feature | bfagent | risk-hub | travel-beat | weltenhub | pptx-hub |
| --- | --- | --- | --- | --- | --- |
| OCI Labels | ✅ | ✅ | ✅ | ✅ | ✅ |
| HEALTHCHECK 127.0.0.1 | ✅ | ✅ | ✅ | ✅ | ✅ |
| Non-root USER | ⚠️ exempt | ✅ | ✅ | ✅ | ✅ |
| env_file: .env.prod | ❌ ${VAR} | ❌ ${VAR} | ✅ | ✅ | ✅ |
| healthz.py (HEALTH_PATHS) | ✅ | ✅ | ✅ | ✅ | ✅ |
| @csrf_exempt + @require_GET | ✅ | ✅ | ✅ | ✅ | ✅ |
| deploy-remote.sh | ✅ | ✅ | ✅ | ✅ | ⏭️ N/A |
| CI/CD @v1 | ✅ | ✅ | ✅ | ✅ hybrid | PyPI |
| IMAGE_TAG standardisiert | ✅ | ✅ | ✅ | ✅ | ✅ |

**Verbleibende Abweichungen (tracked, nicht kritisch):**

1. bfagent + risk-hub: `environment:` mit `${VAR}` statt `env_file`
2. bfagent llm-gateway: Healthcheck nutzt `curl` (Go-Image)
3. bfagent: Non-root USER exempt (Python 3.11 Risiko)
4. pptx-hub: Kein `deploy-remote.sh` (noch nicht auf Hetzner)

---

## 9. Automatisierte Compliance-Pruefung

### repo_checker CLI Tool

Pfad: `platform/tools/repo_checker.py`

Prueft alle 5 Repos automatisch auf ADR-022 Compliance:

```bash
# Alle Repos pruefen
python3 tools/repo_checker.py

# Einzelnes Repo
python3 tools/repo_checker.py /path/to/repo

# JSON-Output
python3 tools/repo_checker.py --json
```

**Pruefkategorien:**

| Kategorie | Pruefungen |
| --- | --- |
| compose | IMAGE_TAG, env_file, healthcheck IP/endpoint, urllib |
| dockerfile | OCI Labels, HEALTHCHECK (multi-line), non-root USER |
| cicd | Platform @v1 Workflows, health_url /livez/ |
| health | healthz.py, HEALTH_PATHS, csrf_exempt, require_GET |
| deploy | deploy-remote.sh Existenz + IMAGE_TAG |
| config | manage.py, wsgi.py, urls.py mit /livez/ |

**MCP-Integration:** Verfuegbar als `check_repos` Tool im orchestrator_mcp.

**Letzter Lauf (2026-02-10):** 88 OK, 1 Warning, 0 Errors.

---

## 10. Entscheidungsgruende

- **Sicherheit**: PAT-Tokens, fehlende csrf_exempt, fehlende HEALTH_PATHS
- **Zuverlaessigkeit**: Migrate-Service verhindert Race Conditions bei parallelem Start
- **Wartbarkeit**: 4 kanonische Templates statt 5 individuelle Implementierungen
- **Robustheit**: set -euo pipefail, Exit-Codes, Env-Validation im Entrypoint
- **Multi-Tenancy**: HEALTH_PATHS Middleware-Exclusion fuer Docker-Healthchecks
- **DRY**: Platform Reusable Workflows, Named Volumes, einheitliche Variablennamen
- **Onboarding**: Template kopieren, APP_NAME aendern, deployen
- **Automatisierung**: repo_checker + MCP-Tools fuer konsistente Pruefung
