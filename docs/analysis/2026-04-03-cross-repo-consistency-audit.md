# Cross-Repo Consistency Audit — Ist-Zustand & Refactoring-Vorschlag

**Datum:** 2026-04-03
**Scope:** 18 Django-Hub-Repos (Production)
**Methode:** Automatisierter Scan über Verzeichnisstruktur, Dockerfile, docker-compose.prod.yml, Settings, CI/CD, Code-Patterns

---

## 1. Executive Summary

Über 18 Repos hinweg wurden **7 Kategorien** mit signifikanten Inkonsistenzen identifiziert. Die kritischsten Probleme sind:

- **Config-Zugang:** 13/18 Repos nutzen `os.environ` statt `decouple.config()` (ADR-045 Verstoß)
- **Dockerfile-Struktur:** 5 verschiedene Patterns für Base-Image, User, Healthcheck
- **Compose-Naming:** Gemischte Hyphen-/Underscore-Konventionen, teils innerhalb eines Repos
- **Service-Layer:** 8/18 Repos haben keinen Service-Layer (ADR-041 Verstoß)
- **ORM in Views:** 10 Repos mit direkten `objects.`-Aufrufen in Views
- **Fehlende Agent-Docs:** Nur 1/18 Repos hat CORE_CONTEXT.md + AGENT_HANDOVER.md

---

## 2. Ist-Zustand nach Kategorie

### 2.1 Verzeichnisstruktur

| Pattern | Repos | Soll |
|---------|-------|------|
| `manage.py` im Root | 14 | ✅ Standard |
| `manage.py` in `src/` | 2 (137-hub, trading-hub) | ❌ Abweichung |
| `manage.py` fehlt/archiviert | 2 (risk-hub, nl2cad) | ❌ Abweichung |
| `apps/` Verzeichnis | 15 | ✅ Standard |
| Kein `apps/` | 3 (137-hub, risk-hub, trading-hub) | ❌ Abweichung |
| `config/settings/` (Split) | 14 | ✅ Standard |
| `config/settings.py` (Single) | 1 (pptx-hub) | ❌ Abweichung |
| Kein `config/settings` | 3 (137-hub, risk-hub, trading-hub) | ❌ Abweichung |

**Befund:** 3 Repos (137-hub, risk-hub, trading-hub) weichen grundlegend von der Standard-Struktur ab.

### 2.2 Dockerfile

| Aspekt | Ist-Zustand | Soll (ADR-021) |
|--------|-------------|----------------|
| **Base Image** | | |
| `python:3.12-slim` | 13 Repos | ✅ Standard |
| `python:3.11-slim` | 3 (bfagent, illustration-hub, writing-hub) | ❌ Veraltet |
| **Multi-Stage Build** | | |
| Ja (≥2 FROM) | 10 Repos | ✅ Standard |
| Nein (1 FROM) | 8 Repos | ❌ Fehlt |
| **Non-Root User** | | |
| `app:1000` | 9 Repos | ✅ Standard |
| Anderer Name (devhub, coachuser, travelbeat, weltenhub) | 4 Repos | ⚠️ Inkonsistent |
| Kein Non-Root User | 5 (137-hub, bfagent, illustration-hub, trading-hub, wedding-hub) | ❌ Sicherheitsrisiko |
| **HEALTHCHECK** | | |
| Vorhanden | 12 Repos | ✅ Standard |
| Fehlt | 6 (137-hub, illustration-hub, research-hub, trading-hub, wedding-hub, travel-beat*) | ❌ Fehlt |
| **Dockerfile-Pfad** | | |
| `docker/app/Dockerfile` | 7 Repos | Variante A |
| `Dockerfile` (Root) | 9 Repos | Variante B |
| `docker/Dockerfile` | 1 (travel-beat) | Variante C |

**Befund:** Kein einheitlicher Standard für Dockerfile-Pfad, User-Name oder Multi-Stage-Pattern.

### 2.3 docker-compose.prod.yml

| Aspekt | Ist-Zustand | Soll (ADR-021) |
|--------|-------------|----------------|
| **Service-Naming** | | |
| Nur Hyphen (`web`, `db`) | 3 Repos | ✅ |
| Nur Underscore | 4 Repos | ❌ |
| Gemischt (!) | 11 Repos | ❌❌ Schlimmster Fall |
| **Container-Naming** | | |
| `{repo}_web` Pattern | 16 Repos | ✅ Mehrheit |
| `billing-hub-web` (mit Hyphen) | 1 Repo | ❌ Abweichung |
| **env_file vs environment** | | |
| Nur `env_file` | 5 Repos | ✅ ADR-021 |
| Gemischt | 13 Repos | ❌ Verstoß |
| **${VAR} Interpolation** | | |
| Keine | 3 Repos | ✅ ADR-021 |
| 1–5 Stellen | 11 Repos | ⚠️ |
| 7+ Stellen | 2 (recruiting-hub: 7, trading-hub: 22) | ❌ Hochriskant |
| **Memory-Limits** | | |
| Vorhanden | 14 Repos | ✅ |
| Fehlt | 4 (137-hub, coach-hub, dev-hub, tax-hub teilweise) | ❌ |
| **Separater Migrate-Service** | | |
| Vorhanden | 5 Repos | ✅ Best Practice |
| Fehlt | 13 Repos | ⚠️ |

### 2.4 Settings & Config

| Aspekt | Ist-Zustand | Soll (ADR-045) |
|--------|-------------|----------------|
| **Config-Zugang** | | |
| `decouple.config()` | 5 (dev-hub, learn-hub, recruiting-hub, tax-hub, weltenhub) | ✅ ADR-045 |
| `os.environ.get()` | 13 Repos | ❌ Verstoß |
| **Hardcoded IPs/Hosts** | | |
| 0 Stellen | 5 Repos | ✅ |
| 1–5 Stellen | 8 Repos | ⚠️ |
| 5+ Stellen | 3 (bfagent: 89, dev-hub: 9, illustration-hub: 7) | ❌ Kritisch |
| **print() statt logging** | | |
| 0 Stellen | 14 Repos | ✅ |
| 1–5 Stellen | 2 Repos | ⚠️ |
| 64+ Stellen | 1 (cad-hub: 64) | ❌ |
| 607 Stellen | 1 (bfagent) | ❌❌ Kritisch |

### 2.5 Architektur-Patterns

| Aspekt | Ist-Zustand | Soll (ADR-041) |
|--------|-------------|----------------|
| **Service-Layer** (`services.py`) | | |
| Vorhanden | 10 Repos | ✅ |
| Fehlt komplett | 8 (137-hub, cad-hub, illustration-hub, learn-hub, pptx-hub, risk-hub, trading-hub, travel-beat*) | ❌ ADR-041 |
| **ORM in Views** (`objects.` in views.py) | | |
| 0 Aufrufe | 6 Repos | ✅ |
| 1–20 Aufrufe | 5 Repos | ⚠️ |
| 20–100 Aufrufe | 5 Repos | ❌ |
| 689 Aufrufe | 1 (bfagent) | ❌❌ |
| **DEFAULT_AUTO_FIELD** | | |
| BigAutoField gesetzt | 15 Repos | ✅ |
| Nicht gesetzt / nicht gefunden | 3 (137-hub, risk-hub, trading-hub) | ❌ |

### 2.6 CI/CD & Workflows

| Aspekt | Ist-Zustand | Soll |
|--------|-------------|------|
| **deploy.yml** vorhanden | 14 Repos | ✅ |
| **ci.yml** vorhanden | 13 Repos | ✅ |
| **issue-triage.yml** | 12 Repos | ✅ |
| **ci-cd.yml** (Combined) | 8 Repos | ⚠️ Doppelt mit ci.yml |
| **Kein CI** | 1 (tax-hub) | ❌ |
| **receive-windsurf-rules.yml** | 12 Repos | ⚠️ Nicht überall |

### 2.7 Developer Experience & Dokumentation

| Aspekt | Ist-Zustand | Soll |
|--------|-------------|------|
| **CORE_CONTEXT.md** | 1/18 (writing-hub) | ❌ |
| **AGENT_HANDOVER.md** | 1/18 (writing-hub) | ❌ |
| **catalog-info.yaml** | 16/18 | ✅ Fast komplett |
| **conftest.py** (Root) | 3/18 | ⚠️ |
| **tests/ Verzeichnis** | 16/18 | ✅ Fast komplett |
| **ruff.toml** (eigene Datei) | 3/18 (in pyproject: 15) | ✅ Akzeptabel |

---

## 3. Risikobewertung

### 🔴 Kritisch (Sofort-Handlung)

| # | Problem | Betroffene Repos | ADR | Impact |
|---|---------|-------------------|-----|--------|
| K1 | `os.environ` statt `decouple` | 13 Repos | ADR-045 | Secrets-Leak-Risiko, Inkonsistenz |
| K2 | Kein Non-Root User in Dockerfile | 5 Repos | ADR-021 | Container-Escape-Risiko |
| K3 | 607× `print()` in bfagent | bfagent | ADR-041 | Kein strukturiertes Logging |
| K4 | 89× Hardcoded IPs in bfagent | bfagent | ADR-045 | Deployment-Bruch bei IP-Wechsel |
| K5 | `${VAR}` Interpolation in Compose | 13 Repos | ADR-021 | Secrets in docker-inspect sichtbar |

### 🟡 Hoch (Nächster Sprint)

| # | Problem | Betroffene Repos | ADR | Impact |
|---|---------|-------------------|-----|--------|
| H1 | Kein Service-Layer | 8 Repos | ADR-041 | Business-Logik in Views, untestbar |
| H2 | ORM direkt in Views | 10 Repos | ADR-041 | Tight Coupling, keine Abstraktion |
| H3 | Gemischte Compose-Naming | 11 Repos | ADR-021 | Verwirrung, Script-Brüche |
| H4 | Python 3.11 statt 3.12 | 3 Repos | - | EOL-Risiko |
| H5 | Fehlender HEALTHCHECK | 6 Repos | ADR-021 | Keine Auto-Recovery |

### 🟢 Mittel (Backlog)

| # | Problem | Betroffene Repos | Impact |
|---|---------|-------------------|--------|
| M1 | Kein CORE_CONTEXT.md | 17 Repos | Agent-Onboarding langsam |
| M2 | Inkonsistenter Dockerfile-Pfad | Alle | Kein automatisierbarer Build |
| M3 | Kein separater Migrate-Service | 13 Repos | Migration-Fehler crashen Web |
| M4 | Fehlende Memory-Limits | 4 Repos | OOM-Risiko |

---

## 4. Soll-Zustand: Platform Blueprint

### 4.1 Standard-Verzeichnisstruktur

```
{repo}/
├── apps/
│   ├── core/
│   │   ├── views.py          # Health-Endpoints, Dashboard
│   │   ├── services.py       # Business-Logik
│   │   ├── urls.py
│   │   └── healthz.py        # /livez/ + /healthz/
│   └── {domain}/
│       ├── models.py
│       ├── services.py        # ← PFLICHT (ADR-041)
│       ├── views.py
│       ├── urls.py
│       └── admin.py
├── config/
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py            # decouple.config() only
│   │   ├── development.py
│   │   ├── test.py
│   │   └── staging.py
│   ├── urls.py
│   └── wsgi.py
├── docker/
│   └── app/
│       └── Dockerfile         # ← Einheitlicher Pfad
├── templates/
├── static/
├── tests/
├── docker-compose.prod.yml
├── docker-compose.yml
├── manage.py
├── requirements.txt
├── pyproject.toml
├── conftest.py
├── CORE_CONTEXT.md
├── AGENT_HANDOVER.md
├── catalog-info.yaml
└── README.md
```

### 4.2 Standard-Dockerfile (Template)

```dockerfile
# --- Stage 1: Builder ---
FROM python:3.12-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# --- Stage 2: Runtime ---
FROM python:3.12-slim
LABEL org.opencontainers.image.source="https://github.com/achimdehnert/{repo}"
LABEL org.opencontainers.image.description="{Repo Description}"

RUN groupadd -g 1000 app && useradd -u 1000 -g app -m app
WORKDIR /app
COPY --from=builder /install /usr/local
COPY . .
RUN python manage.py collectstatic --noinput 2>/dev/null || true

USER app:1000
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=30s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/livez/')"

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2"]
```

### 4.3 Standard-Compose-Naming

```yaml
services:
  {repo}-web:                           # Hyphens für Services
    container_name: {repo_under}_web    # Underscores für Container
    env_file: .env.prod                 # NIEMALS environment: ${VAR}
    deploy:
      resources:
        limits:
          memory: 512M

  {repo}-migrate:                       # Separater Migrate-Service
    container_name: {repo_under}_migrate

  {repo}-db:
    container_name: {repo_under}_db

  {repo}-redis:
    container_name: {repo_under}_redis
```

### 4.4 Standard-Settings (decouple)

```python
from decouple import config, Csv

SECRET_KEY = config("SECRET_KEY")
DEBUG = config("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", cast=Csv())
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("POSTGRES_DB"),
        "USER": config("POSTGRES_USER"),
        "PASSWORD": config("POSTGRES_PASSWORD"),
        "HOST": config("POSTGRES_HOST", default="db"),
        "PORT": config("POSTGRES_PORT", default="5432"),
    }
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
```

---

## 5. Implementierungsvorschlag

### Phase 1: Security & Stabilität (1–2 Wochen)

**Prio K1–K5 — Automatisierbar mit Script**

| Task | Repos | Aufwand | Methode |
|------|-------|---------|---------|
| Non-Root User in Dockerfile | 5 Repos | 1h/Repo | Template-Patch |
| HEALTHCHECK in Dockerfile | 6 Repos | 30min/Repo | Template-Patch |
| `os.environ` → `decouple.config()` | 13 Repos | 2h/Repo | Semi-automatisch |
| `${VAR}` aus Compose entfernen → `env_file` | 13 Repos | 1h/Repo | Semi-automatisch |
| Python 3.11 → 3.12 Upgrade | 3 Repos | 1h/Repo | Dockerfile + Test |

**Geschätzter Gesamtaufwand:** ~40h (≈ 1 Entwicklerwoche)

### Phase 2: Architektur-Hygiene (2–4 Wochen)

**Prio H1–H5 — Manuelles Refactoring**

| Task | Repos | Aufwand | Methode |
|------|-------|---------|---------|
| Service-Layer einführen | 8 Repos | 4h/Repo | Extract Method |
| ORM aus Views → Services | 10 Repos | 3h/Repo | Schrittweises Refactoring |
| Compose-Naming vereinheitlichen | 11 Repos | 1h/Repo | Rename + Server-Update |
| `print()` → `logging` (bfagent, cad-hub) | 2 Repos | 8h total | Search & Replace |
| Hardcoded IPs entfernen | 5 Repos | 2h/Repo | Config-Externalisierung |

**Geschätzter Gesamtaufwand:** ~80h (≈ 2 Entwicklerwochen)

### Phase 3: Platform-Konvergenz (4–8 Wochen)

**Prio M1–M4 — Infrastruktur-Verbesserung**

| Task | Repos | Aufwand | Methode |
|------|-------|---------|---------|
| CORE_CONTEXT.md generieren | 17 Repos | 1h/Repo | docs-agent Template |
| AGENT_HANDOVER.md generieren | 17 Repos | 1h/Repo | docs-agent Template |
| Dockerfile-Pfad vereinheitlichen | 9 Repos | 30min/Repo | mv + CI-Update |
| Separaten Migrate-Service | 13 Repos | 1h/Repo | Compose-Patch |
| Memory-Limits ergänzen | 4 Repos | 30min/Repo | Compose-Patch |
| Verzeichnisstruktur 137-hub, risk-hub, trading-hub | 3 Repos | 8h/Repo | Großes Refactoring |

**Geschätzter Gesamtaufwand:** ~80h (≈ 2 Entwicklerwochen)

---

## 6. Automatisierungs-Tooling

### 6.1 Platform Compliance Checker (Vorschlag)

```bash
# Vorschlag: platform-lint CLI
platform-lint check --repo /path/to/repo

# Prüft:
# ✅ Dockerfile: Multi-Stage, python:3.12-slim, Non-Root, HEALTHCHECK
# ✅ Compose: env_file statt environment, keine ${VAR}, Memory-Limits
# ✅ Settings: decouple statt os.environ, kein Hardcoding
# ✅ Architecture: Service-Layer vorhanden, kein ORM in Views
# ✅ Docs: CORE_CONTEXT.md, AGENT_HANDOVER.md, catalog-info.yaml
```

### 6.2 Reusable Scaffolding

Ein `cookiecutter`-Template oder `platform scaffold` Command der ein neues Repo mit korrekter Struktur erzeugt, damit neue Repos automatisch compliant sind.

---

## 7. Priorisierte Quick-Wins (sofort umsetzbar)

1. **Dockerfile Non-Root Fix** — 5 Repos, je 3 Zeilen ändern
2. **HEALTHCHECK ergänzen** — 6 Repos, je 2 Zeilen ändern
3. **`${VAR}` aus Compose entfernen** — grep + replace
4. **CORE_CONTEXT.md per Template** — docs-agent kann das generieren
5. **Memory-Limits ergänzen** — 4 Repos, Copy-Paste aus Template

---

## Anhang: Repo-Compliance-Matrix

| Repo | Structure | Dockerfile | Compose | Settings | Service-Layer | Health | Agent-Docs | Score |
|------|-----------|------------|---------|----------|---------------|--------|------------|-------|
| 137-hub | ❌ | ❌ | ⚠️ | ❌ | ❌ | ❌ | ❌ | 0/7 |
| billing-hub | ✅ | ⚠️ | ⚠️ | ❌ | ✅ | ✅ | ❌ | 3/7 |
| bfagent | ✅ | ❌ | ⚠️ | ❌ | ⚠️ | ✅ | ❌ | 2/7 |
| cad-hub | ✅ | ✅ | ⚠️ | ❌ | ❌ | ✅ | ❌ | 3/7 |
| coach-hub | ✅ | ⚠️ | ⚠️ | ❌ | ✅ | ✅ | ❌ | 3/7 |
| dev-hub | ✅ | ⚠️ | ⚠️ | ✅ | ✅ | ✅ | ❌ | 4/7 |
| illustration-hub | ✅ | ❌ | ⚠️ | ❌ | ❌ | ❌ | ❌ | 1/7 |
| learn-hub | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | 4/7 |
| pptx-hub | ⚠️ | ✅ | ⚠️ | ❌ | ❌ | ✅ | ❌ | 2/7 |
| recruiting-hub | ✅ | ✅ | ⚠️ | ✅ | ✅ | ✅ | ❌ | 5/7 |
| research-hub | ✅ | ⚠️ | ⚠️ | ❌ | ✅ | ✅ | ❌ | 3/7 |
| risk-hub | ❌ | ✅ | ⚠️ | ❌ | ❌ | ✅ | ❌ | 1/7 |
| tax-hub | ✅ | ✅ | ⚠️ | ✅ | ✅ | ✅ | ❌ | 5/7 |
| trading-hub | ❌ | ❌ | ⚠️ | ❌ | ❌ | ❌ | ❌ | 0/7 |
| travel-beat | ✅ | ⚠️ | ⚠️ | ❌ | ✅ | ✅ | ❌ | 3/7 |
| wedding-hub | ✅ | ❌ | ⚠️ | ❌ | ✅ | ❌ | ❌ | 2/7 |
| weltenhub | ✅ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ❌ | 3/7 |
| writing-hub | ✅ | ❌ | ⚠️ | ❌ | ⚠️ | ✅ | ✅ | 3/7 |

**Durchschnitt: 2.6 / 7** — deutlicher Handlungsbedarf.

**Top-Performer:** recruiting-hub (5/7), tax-hub (5/7)
**Schlusslichter:** 137-hub (0/7), trading-hub (0/7)
