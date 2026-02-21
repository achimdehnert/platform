---
status: proposed
date: 2026-02-21
decision-makers: Achim Dehnert
---

# Architecture Decision Record

_Shared Backend Services Library für Django-Projekte_

| | |
|---|---|
| **ADR-ID** | ADR-2026-001 |
| **Titel** | Shared Backend Services Library für Django-Projekte |
| **Status** | Proposed |
| **Datum** | 2026-02-12 |
| **Autor** | Achim Dehnert / Claude AI |
| **Betrifft** | wedding-hub, iil.pet, zukünftige Django-Projekte |

---

## 1. Kontext & Problemstellung

Die iil.pet-Plattform umfasst mehrere Django-basierte Projekte (wedding-hub, zukünftige SaaS-Apps), die jeweils eigenständig Backend-Infrastruktur implementieren: Logging, Caching, Rate Limiting, Health Checks, E-Mail-Versand und Celery-Tasks.

Dies führt zu mehreren Problemen:

- **Code-Duplikation:** Jedes Projekt implementiert dieselben Patterns (structured logging, Redis caching, health endpoints) individuell.
- **Inkonsistenz:** Unterschiedliche Logging-Formate, Health-Check-Strukturen und Error-Handling-Patterns erschweren Operations und Debugging.
- **Wartungsaufwand:** Security-Patches, Dependency-Updates und Best-Practice-Änderungen müssen in jedem Projekt einzeln nachgezogen werden.
- **Onboarding:** Neue Projekte starten bei Null statt auf bewährten Patterns aufzubauen.

Ziel ist eine wiederverwendbare Library, die diese Cross-Cutting Concerns zentralisiert, während die Projekte ihre Domänen-Logik eigenständig halten.

---

## 2. Entscheidungskriterien

- Versionierung & Pinning: Projekte müssen eine spezifische Version pinnen können (Stabilität).
- DRY-Updates: Ein `pip upgrade` soll genügen, um alle Verbesserungen zu erhalten.
- Isolation: Klare API-Grenze zwischen Library und Consumer-Projekt.
- CI/CD-Unabhängigkeit: Library und Projekte haben eigene Pipelines.
- Konfigurierbarkeit: Jedes Projekt kann Defaults überschreiben (z.B. Log-Level, Cache-TTL).
- Minimale Abhängigkeiten: Optionale Extras für Module, die nicht jedes Projekt braucht.

---

## 3. Bewertete Optionen

| Kriterium | A: PyPI Package | B: Git Submodule | C: Cookiecutter | D: Monorepo |
|---|---|---|---|---|
| Versionierung | ✅ semver, pip | ⚠️ Git SHA | ❌ Snapshot | ⚠️ Monorepo tags |
| DRY Updates | ✅ pip upgrade | ⚠️ submodule pull | ❌ Regenerate | ✅ Shared code |
| Isolation | ✅ Clean boundary | ⚠️ Coupled | ✅ Standalone | ❌ Tight coupling |
| CI/CD | ✅ Independent | ⚠️ Complex | ✅ Independent | ⚠️ Matrix builds |
| Onboarding | ✅ pip install | ⚠️ Git knowledge | ✅ Simple | ❌ Full clone |
| Customization | ✅ Settings/hooks | ✅ Fork possible | ✅ At generation | ⚠️ Flags needed |

### 3.1 Option A: Private PyPI Package (iil-django-commons)

Ein eigenständiges Python-Package, gehostet als privates GitHub-Repository mit pip-Install via Git-URL. Semantic Versioning, eigene CI/CD-Pipeline, klare API.

Projekte installieren via: `pip install git+https://github.com/achimdehnert/iil-django-commons.git@v0.3.0`

### 3.2 Option B: Git Submodule

Shared Code als Git-Submodule in jedem Projekt eingebunden. Direkter Zugriff auf den Quellcode, aber komplexe Synchronisation und fehleranfällig bei CI/CD.

### 3.3 Option C: Cookiecutter Template

Ein Projekttemplate, das beim Erstellen neuer Projekte die Backend-Services mit-generiert. Gut für Bootstrapping, aber keine zentralen Updates nach Generierung.

### 3.4 Option D: Monorepo

Alle Projekte in einem Repository mit Shared-Code-Verzeichnis. Maximale Code-Sharing, aber hohe Komplexität bei CI/CD und Deployment.

---

## 4. Entscheidung

**Gewählt: Option A – Private PyPI Package** mit Cookiecutter-Starter (Option C) als Ergänzung für neue Projekte.

Begründung: Maximale Isolation bei minimalem Wartungsaufwand. Semantic Versioning ermöglicht kontrollierte Updates. Optionale Extras halten die Abhängigkeiten schlank. Die Cookiecutter-Ergänzung stellt sicher, dass neue Projekte sofort mit Best Practices starten.

---

## 5. Package-Architektur: iil-django-commons

| Modul | Verantwortung | Abhängigkeiten |
|---|---|---|
| **iil_commons.logging** | Structured JSON logging, Correlation-ID Middleware, Request/Response logging | structlog, python-json-logger |
| **iil_commons.cache** | Redis cache patterns, Cache decorators, Invalidation helpers, Warm-up commands | django-redis |
| **iil_commons.ratelimit** | Rate limiting Middleware, Per-user/IP/endpoint throttling, Retry-After headers | Redis |
| **iil_commons.health** | Standardized /livez/, /readyz/ endpoints, DB/Redis/Celery checks | keine |
| **iil_commons.email** | Transactional email abstraction, Provider-agnostic (SMTP, Resend, Postmark), Template rendering | keine |
| **iil_commons.tasks** | Celery task base class, Auto-retry, Dead-letter queue, Monitoring hooks | celery |
| **iil_commons.monitoring** | Prometheus metrics, Custom counters, Django middleware für request metrics | prometheus-client |
| **iil_commons.security** | CORS, CSP, Security headers middleware, Input sanitization | keine |

### 5.1 Projektstruktur

```
iil-django-commons/
├── src/iil_commons/
│   ├── __init__.py          # version, auto-discovery
│   ├── apps.py              # Django AppConfig
│   ├── settings.py          # Default settings (IIL_COMMONS_*)
│   ├── logging/
│   │   ├── __init__.py
│   │   ├── config.py        # setup_logging(), LOGGING dict
│   │   ├── middleware.py     # CorrelationIDMiddleware, RequestLogMiddleware
│   │   └── formatters.py    # JSONFormatter, HumanFormatter
│   ├── cache/
│   │   ├── __init__.py
│   │   ├── decorators.py    # @cached_view, @cached_method
│   │   ├── invalidation.py  # pattern-based cache invalidation
│   │   └── warmup.py        # Management command: cache_warmup
│   ├── ratelimit/
│   │   ├── __init__.py
│   │   ├── middleware.py     # RateLimitMiddleware
│   │   └── decorators.py    # @rate_limit(requests=100, window=3600)
│   ├── health/
│   │   ├── __init__.py
│   │   ├── views.py         # /livez/, /readyz/
│   │   └── checks.py        # DatabaseCheck, RedisCheck, CeleryCheck
│   ├── email/
│   │   ├── __init__.py
│   │   ├── service.py       # EmailService (provider-agnostic)
│   │   └── providers/       # SMTP, Resend, Postmark adapters
│   ├── tasks/
│   │   ├── __init__.py
│   │   ├── base.py          # BaseTask (retry, DLQ, logging)
│   │   └── monitoring.py    # Task success/failure hooks
│   ├── monitoring/
│   │   ├── __init__.py
│   │   ├── middleware.py     # PrometheusMiddleware
│   │   └── metrics.py       # request_count, latency, error_rate
│   └── security/
│       ├── __init__.py
│       ├── middleware.py     # SecurityHeadersMiddleware, CSP
│       └── sanitize.py      # Input sanitization helpers
├── tests/
├── pyproject.toml               # PEP 621, optional extras
├── README.md
└── CHANGELOG.md
```

### 5.2 Installation & Konfiguration

Consumer-Projekte installieren das Package mit optionalen Extras:

```bash
# Minimal (logging + health)
pip install git+https://github.com/achimdehnert/iil-django-commons.git@v0.3.0

# Vollausstattung
pip install "iil-django-commons[cache,ratelimit,monitoring,email]@git+..."
```

In `settings.py` des Consumer-Projekts:

```python
INSTALLED_APPS = [
    "iil_commons",            # Auto-discovers modules
    ...
]

MIDDLEWARE = [
    "iil_commons.logging.middleware.CorrelationIDMiddleware",
    "iil_commons.logging.middleware.RequestLogMiddleware",
    "iil_commons.ratelimit.middleware.RateLimitMiddleware",
    "iil_commons.security.middleware.SecurityHeadersMiddleware",
    ...
]

# Override defaults (all optional)
IIL_COMMONS = {
    "LOG_FORMAT": "json",          # "json" | "human"
    "LOG_LEVEL": "INFO",
    "CACHE_DEFAULT_TTL": 300,
    "RATE_LIMIT_DEFAULT": "100/h",
    "HEALTH_CHECKS": ["db", "redis", "celery"],
    "EMAIL_PROVIDER": "resend",    # "smtp" | "resend" | "postmark"
}
```

### 5.3 Modul-Details

#### Structured Logging

JSON-Logging mit Correlation-ID für Request-Tracing über alle Services. Jeder HTTP-Request bekommt eine eindeutige ID, die durch alle Logs, Celery-Tasks und externe API-Calls propagiert wird.

- CorrelationIDMiddleware: Generiert/liest X-Correlation-ID Header
- RequestLogMiddleware: Loggt Request/Response mit Timing, Status, User
- JSONFormatter: Structured output für Logstash/Grafana Loki
- HumanFormatter: Lesbares Format für lokale Entwicklung
- Celery Integration: Correlation-ID wird in Task-Headers propagiert

#### Redis Cache Patterns

Dekorator-basiertes Caching mit automatischer Key-Generierung und pattern-basierter Invalidierung:

```python
from iil_commons.cache import cached_view, invalidate_pattern

@cached_view(ttl=300, key_func=lambda r: f"guests:{r.organization.pk}")
def guest_list(request):
    ...

# Invalidate all guest caches for an org when data changes
invalidate_pattern(f"guests:{org.pk}:*")
```

#### Rate Limiting

Redis-backed Rate Limiting mit Sliding Window. Konfigurierbar per View, User, IP oder API-Key:

```python
from iil_commons.ratelimit import rate_limit

@rate_limit(requests=10, window=60, key="user")  # 10/min per user
def api_endpoint(request):
    ...

# Middleware-Level für globales Limiting
IIL_COMMONS = {
    "RATE_LIMIT_DEFAULT": "100/h",
    "RATE_LIMIT_PATHS": {
        "/api/": "60/min",
        "/guest/login/": "5/min",
    }
}
```

#### Health Checks

Standardisierte Kubernetes-kompatible Endpoints:

- `/livez/` – Liveness: App-Prozess läuft (immer 200)
- `/readyz/` – Readiness: Alle Dependencies verfügbar (DB, Redis, Celery)
- Erweiterbar: Custom Checks (z.B. Disk Space, External APIs)
- JSON-Response mit Details pro Check, HTTP 503 wenn einer fehlschlägt

#### Monitoring (Prometheus)

Out-of-the-box Prometheus-Metriken über PrometheusMiddleware:

- `http_requests_total{method, path, status}` – Request Counter
- `http_request_duration_seconds{method, path}` – Latenz-Histogramm
- `http_requests_in_progress{method}` – Concurrent Requests Gauge
- `celery_task_total{task, status}` – Task Success/Failure Counter
- `/metrics/` Endpoint für Prometheus Scraping

---

## 6. Integration in wedding-hub

Die Migration erfolgt schrittweise. Bestehende Eigenimplementierungen werden durch Library-Aufrufe ersetzt:

**Phase 1** – Logging ersetzen: LOGGING-Dict in settings.py durch `iil_commons.logging.setup_logging()` ersetzen. CorrelationIDMiddleware einfügen.

**Phase 2** – Health Checks: Eigenen `/livez/` Lambda durch `iil_commons.health.urls` ersetzen. Redis + Celery Checks aktivieren.

**Phase 3** – Caching: Redis-Cache für GuestListView, Timeline, Analytics. Cache-Invalidierung bei Model-Saves via Django Signals.

**Phase 4** – Rate Limiting + Monitoring: Guest-Login und API-Endpoints schützen. Prometheus-Metriken für Dashboard.

---

## 7. Rollout-Plan

| Phase | Scope | Timeline | Deliverables |
|---|---|---|---|
| **Phase 1** | Logging + Health + Cache | Woche 1–2 | iil-django-commons v0.1.0, wedding-hub Integration, CI Pipeline |
| **Phase 2** | Rate Limiting + Security | Woche 3–4 | v0.2.0, Middleware Stack, Security-Hardening |
| **Phase 3** | Email + Tasks + Monitoring | Woche 5–6 | v0.3.0, Celery Patterns, Prometheus Endpoint |
| **Phase 4** | Second Project Integration | Woche 7–8 | Validation, Docs, Cookiecutter Starter |

---

## 8. Risiken & Mitigationen

- **Over-Engineering:** Start mit nur 3 Modulen (Logging, Health, Cache). Weitere Module nur bei konkretem Bedarf in einem zweiten Projekt. YAGNI-Prinzip.
- **Breaking Changes:** Semantic Versioning + CHANGELOG. Major-Upgrades nur mit Migration Guide. Consumer pinnen auf Minor-Version (`>=0.2.0,<0.3.0`).
- **Vendor Lock-in:** Abstraktion über Interfaces. Provider sind austauschbar (SMTP ↔ Resend, structlog ↔ stdlib logging).
- **Testbarkeit:** Library hat eigene Test-Suite (pytest). Consumer-Tests mocken Library-Interfaces. Integration-Tests in CI.
- **Debugging:** HumanFormatter für lokale Entwicklung. Source-Installation möglich: `pip install -e ../iil-django-commons`.

---

## 9. Offene Fragen zur Entscheidung

- PyPI-Hosting: Privates GitHub-Package oder separater PyPI-Index (z.B. Gemfury, Hetzner)? → Empfehlung: GitHub als Git-Dependency (kein extra Service).
- Scope Phase 1: Logging + Health + Cache als Minimal-Start oder direkt alle Module? → Empfehlung: Minimal-Start.
- Monitoring-Stack: Prometheus + Grafana on Hetzner oder externer Service? → Empfehlung: Hetzner Docker Compose (Prometheus + Grafana als Sidecars).
- Naming: `iil-django-commons` vs. `iil-backend-commons` vs. project-spezifischer Name?

---

## 10. Nächste Schritte

1. ADR reviewen und Entscheidung treffen (Optionen, offene Fragen)
2. Repository `iil-django-commons` erstellen mit `pyproject.toml` + CI
3. Phase 1 Module implementieren (Logging, Health, Cache)
4. wedding-hub migrieren (settings.py, middleware, health check)
5. Validierung an zweitem Projekt
