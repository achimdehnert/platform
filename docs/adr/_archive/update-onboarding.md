# Analyse: onboard-repo.md + Gap-Analyse wedding-hub

## Teil 1: Kritische Bewertung des Onboarding-Dokuments

### Was gut ist

Das Dokument löst ein reales Problem: Konsistenz über mehrere Repos hinweg. Die Naming Conventions, Port-Map, Verifikations-Checkliste und die Reusable Workflows sind solide Standardisierung.

### Verbesserungsvorschläge für onboard-repo.md

| # | Bereich | Problem | Vorschlag |
|---|---------|---------|-----------|
| **O-01** | Security | `.env.example` enthält echtes Superuser-Passwort (`bfagent2024!`) | Platzhalter verwenden: `CHANGE_ME_BEFORE_DEPLOY` |
| **O-02** | Security | `DEPLOY_USER: root` – SSH als Root ist ein Sicherheitsrisiko | Dedizierten `deploy`-User mit sudo-Rechten empfehlen |
| **O-03** | Dockerfile | `collectstatic ... 2>/dev/null \|\| true` – verschluckt Build-Fehler | Fehler nicht unterdrücken (ohne `\|\| true`) |
| **O-04** | Dockerfile | `build-essential` bleibt im finalen Image (kein Multi-Stage) | Multi-Stage Build: build-deps nur in Builder-Stage |
| **O-05** | Settings | Nur `settings.py` (single file) vorgesehen | Split-Settings (`base/local/production/test`) als Alternative dokumentieren |
| **O-06** | Settings | `dj-database-url` als Pflicht – gut, aber Alternative fehlt | Fallback-Hinweis für Repos die `POSTGRES_*` Einzelvars nutzen |
| **O-07** | Compose | GHCR-Image-Pfad enthält doppelten Repo-Namen: `ghcr.io/.../REPO/REPO-web` | Vereinfachen zu `ghcr.io/achimdehnert/REPO:tag` |
| **O-08** | Entrypoint | `psycopg` im DB-Wait → funktioniert nur wenn psycopg3 installiert | Fallback mit `pg_isready` oder `python -c "import django; ..."` |
| **O-09** | Backup | Backup-Strategie erwähnt aber nicht definiert | backup.md verlinken oder Minimal-Backup-Cron dokumentieren |
| **O-10** | Rollback | `enable_rollback: true` erwähnt, aber Strategie unklar | Rollback-Mechanismus (Image-Tag Pinning, DB-Migration-Reversal) beschreiben |
| **O-11** | Monitoring | Kein Abschnitt zu Logging/Monitoring/Alerting | Minimal: structured logging, optional Sentry/Grafana |
| **O-12** | Settings | `SECURE_PROXY_SSL_HEADER` ist PFLICHT hinter Nginx-Proxy | Im Settings-Block als CRITICAL markieren |

---

## Teil 2: Gap-Analyse wedding-hub → Onboarding-Standard

### Compliance-Matrix

| Anforderung | Onboard-Standard | wedding-hub IST | Status | Aufwand |
|-------------|-----------------|-----------------|--------|---------|
| **Verzeichnisstruktur** | `docker/app/Dockerfile` | `Dockerfile` im Root | ❌ | 10 Min |
| **Entrypoint** | `docker/app/entrypoint.sh` | Nicht vorhanden | ❌ | 20 Min |
| **docker-compose.prod.yml** | Prod-Compose mit Naming | Nur dev `docker-compose.yml` | ❌ | 25 Min |
| **Naming Conventions** | `wedding_hub_web`, `wedding_hub_network` | `django`, `postgres` (generisch) | ❌ | in Compose |
| **CI/CD Reusable Workflows** | `achimdehnert/platform@v1` | Eigene ci.yml Pipeline | ❌ | 15 Min |
| **DATABASE_URL** via `dj-database-url` | Pflicht | Nutzt `POSTGRES_*` Einzelvars | ❌ | 15 Min |
| **SECURE_PROXY_SSL_HEADER** | Pflicht | Fehlt | ❌ | 2 Min |
| **CSRF_TRUSTED_ORIGINS** | Pflicht | Fehlt | ❌ | 2 Min |
| **`/livez/` Health-Endpoint** | Pflicht | Fehlt | ❌ | 2 Min |
| **Non-root Docker User** | Pflicht | Fehlt | ❌ | in Dockerfile |
| **HEALTHCHECK in Dockerfile** | Pflicht | Fehlt | ❌ | in Dockerfile |
| **OCI Labels** | Pflicht | Fehlt | ❌ | in Dockerfile |
| **.env.example** | `DATABASE_URL`, Superuser-Vars | Nur `POSTGRES_*` Vars | ⚠️ | 5 Min |
| **requirements.txt** | Pflicht | `pyproject.toml` | ⚠️ | 5 Min |
| **WhiteNoise** | Empfohlen | In pyproject.toml, aber nicht in Settings | ⚠️ | 5 Min |
| **Gunicorn** | In Dockerfile | Ja, vorhanden | ✅ | — |
| **Celery** | Optional | Ja, konfiguriert | ✅ | — |
| **Redis** | Standard | Ja, vorhanden | ✅ | — |
| **PostgreSQL 16** | Standard | Ja, vorhanden | ✅ | — |

**Compliance: 4/18 (22%)** – erheblicher Anpassungsbedarf.

---

## Teil 3: Priorisierte Änderungen für wedding-hub

### Phase 1: Kritische Compliance (Blocker für Deployment)

| # | Änderung | Dateien | Aufwand |
|---|----------|---------|---------|
| **W-01** | Production Settings vervollständigen | `config/settings/production.py` | 5 Min |
| | → `SECURE_PROXY_SSL_HEADER`, `CSRF_TRUSTED_ORIGINS`, `DATABASE_URL` via `dj-database-url` | | |
| **W-02** | `/livez/` Health-Endpoint | `config/urls.py` | 2 Min |
| **W-03** | `.env.example` erweitern | `.env.example` | 5 Min |
| | → `DATABASE_URL`, `CSRF_TRUSTED_ORIGINS`, Superuser-Vars | | |

### Phase 2: Docker-Compliance

| # | Änderung | Dateien | Aufwand |
|---|----------|---------|---------|
| **W-04** | Dockerfile nach `docker/app/Dockerfile` verschieben | neuer Pfad + Inhalt | 15 Min |
| | → Non-root User, HEALTHCHECK, OCI Labels, entrypoint.sh | | |
| **W-05** | `docker/app/entrypoint.sh` erstellen | neues Script | 10 Min |
| | → DB-Wait, migrate, collectstatic, superuser auto-create | | |
| **W-06** | `docker-compose.prod.yml` erstellen | neue Datei | 15 Min |
| | → Naming Conventions, Networks, Resource Limits, Port 8093 | | |

### Phase 3: CI/CD Umstellung

| # | Änderung | Dateien | Aufwand |
|---|----------|---------|---------|
| **W-07** | CI/CD auf Reusable Workflows umstellen | `.github/workflows/ci-cd.yml` | 10 Min |
| | → `_ci-python.yml`, `_build-docker.yml`, `_deploy-hetzner.yml` | | |

### Phase 4: Dependency-Anpassung

| # | Änderung | Dateien | Aufwand |
|---|----------|---------|---------|
| **W-08** | `requirements.txt` generieren aus pyproject.toml | `requirements.txt` | 5 Min |
| **W-09** | `dj-database-url` + `whitenoise` zu Dependencies | `pyproject.toml` + `requirements.txt` | 5 Min |

---

## Entscheidungspunkte

Vor der Umsetzung müssen diese Fragen geklärt werden:

1. **Settings-Architektur**: wedding-hub hat Split-Settings (`base/local/production/test`). Onboarding-Standard sieht single `settings.py` vor. **Empfehlung:** Split beibehalten (ist professioneller), aber `dj-database-url` + fehlende Security-Settings in `production.py` nachrüsten.

2. **Port-Zuweisung**: Nächster freier Port ist `8093`. Ist das für wedding-hub reserviert?

3. **Domain**: Wird wedding-hub unter `wedding-hub.iil.pet` oder `wedding-hub.de` deployed?

4. **Celery**: wedding-hub braucht Celery (Emails, Exports). Soll ein Worker-Service in die prod-Compose?

5. **`daphne`-Dependency**: Aktuell in Core-Dependencies, aber ASGI/Channels nicht genutzt. Entfernen?
