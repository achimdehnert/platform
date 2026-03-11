---
status: "accepted"
date: 2026-02-21
amended: 2026-03-11
decision-makers: [Achim Dehnert]
consulted: []
informed: []
supersedes: []
amends: []
related: ["ADR-022-platform-consistency-standard.md", "ADR-041-service-layer-pattern.md"]
implementation_status: implemented
implementation_evidence:
  - "Own repo: https://github.com/achimdehnert/iil-django-commons (v0.3.0)"
  - "Mirror: platform/packages/iil-django-commons/ (Monorepo)"
  - "8 Module: logging, health, cache, ratelimit, security, email, tasks, monitoring"
  - "31 Tests (30 passed, 1 skipped), CI Pipeline Python 3.11+3.12"
  - "Consumer 1: billing-hub (LIVE billing.iil.pet) — INSTALLED_APPS, Middleware, Health, IIL_COMMONS"
  - "HEALTH_PATHS-Filter in RequestLogMiddleware (Review-Finding behoben 2026-03-11)"
---

# ADR-131: Shared Backend Services Library für Django-Projekte

> **Amended 2026-03-11**: Review-Bereinigung — Metadaten korrigiert, Projektstruktur an
> Implementierung angepasst, Rollout-Plan aktualisiert, offene Fragen entschieden.
>
> *Umnummeriert von ADR-091 (Nummernkonflikt mit ADR-091-platform-operations-hub).*

---

## 1. Kontext & Problemstellung

Die IIL-Plattform umfasst 18+ Django-basierte Hub-Projekte, die jeweils eigenständig Backend-Infrastruktur implementieren: Logging, Caching, Rate Limiting, Health Checks, E-Mail-Versand und Celery-Tasks.

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

Projekte installieren via: `pip install -e platform/packages/iil-django-commons` (Monorepo)
oder `pip install git+https://github.com/achimdehnert/platform.git@main#subdirectory=packages/iil-django-commons` (pinned)

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
| **iil_commons.logging** | Structured JSON logging, Correlation-ID Middleware, Request/Response logging | python-json-logger |
| **iil_commons.cache** | Redis cache patterns, `@cached_view`, `@cached_method`, `invalidate_pattern()` | django-redis |
| **iil_commons.ratelimit** | Rate limiting Middleware + Decorator, Per-user/IP/endpoint throttling, Retry-After headers | redis |
| **iil_commons.health** | Standardized `/livez/`, `/healthz/`, `/readyz/` endpoints, DB/Redis/Celery checks | keine |
| **iil_commons.email** | Transactional email abstraction, Provider-agnostic (SMTP, Resend) | resend (optional) |
| **iil_commons.tasks** | Celery base task, Auto-retry mit exponential Backoff, Correlation-ID Propagation | celery |
| **iil_commons.monitoring** | Prometheus metrics, Request counter/latency/in-progress, `/metrics/` endpoint | prometheus-client |
| **iil_commons.security** | CSP, Security headers middleware (`X-Content-Type-Options`, `X-Frame-Options`, etc.) | keine |

### 5.1 Projektstruktur

```
platform/packages/iil-django-commons/
├── src/iil_commons/
│   ├── __init__.py          # __version__ = "0.3.0"
│   ├── apps.py              # IilCommonsConfig (auto-setup logging on ready())
│   ├── settings.py          # IIL_COMMONS dict mit typed defaults
│   ├── logging/
│   │   ├── config.py        # setup_logging() — JSON + Human Formatter
│   │   └── middleware.py     # CorrelationIDMiddleware, RequestLogMiddleware
│   ├── cache/
│   │   ├── decorators.py    # @cached_view, @cached_method
│   │   └── invalidation.py  # invalidate_pattern() (django-redis)
│   ├── ratelimit/
│   │   ├── middleware.py     # RateLimitMiddleware (fixed-window)
│   │   └── decorators.py    # @rate_limit(requests, window, key)
│   ├── health/
│   │   ├── views.py         # /livez/, /healthz/, /readyz/
│   │   ├── checks.py        # DatabaseCheck, RedisCheck, CeleryCheck
│   │   └── urls.py          # Drop-in URL patterns
│   ├── email/
│   │   └── service.py       # EmailService (SMTP + Resend), EmailMessage dataclass
│   ├── tasks/
│   │   └── base.py          # BaseTask (auto-retry, exponential backoff, correlation-id)
│   ├── monitoring/
│   │   ├── middleware.py     # PrometheusMiddleware (no-op ohne prometheus_client)
│   │   └── views.py         # metrics_view für /metrics/ endpoint
│   └── security/
│       └── middleware.py     # SecurityHeadersMiddleware, CSP (konfigurierbar)
├── tests/                       # 10 Test-Dateien, 31 Tests
├── pyproject.toml               # PEP 621, optional extras: cache, ratelimit, monitoring, email, logging, all
├── README.md
└── CHANGELOG.md
```

### 5.2 Installation & Konfiguration

Consumer-Projekte installieren das Package mit optionalen Extras:

```bash
# Minimal (logging + health)
pip install -e platform/packages/iil-django-commons

# Mit Cache-Support
pip install -e "platform/packages/iil-django-commons[cache]"

# Vollausstattung
pip install -e "platform/packages/iil-django-commons[all]"
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

## 6. Consumer-Integration (Beispiel)

Die Migration erfolgt schrittweise. Bestehende Eigenimplementierungen werden durch Library-Aufrufe ersetzt:

**Phase 1** – Logging ersetzen: LOGGING-Dict in settings.py durch `iil_commons` AppConfig Auto-Setup ersetzen. `CorrelationIDMiddleware` + `RequestLogMiddleware` einfügen.

**Phase 2** – Health Checks: Eigene Health-Endpoints durch `include("iil_commons.health.urls")` ersetzen. Redis + Celery Checks aktivieren.

**Phase 3** – Caching: Redis-Cache für häufig aufgerufene Views. Cache-Invalidierung bei Model-Saves via `invalidate_pattern()`.

**Phase 4** – Rate Limiting + Monitoring: API-Endpoints schützen. Prometheus-Metriken für Dashboard.

---

## 7. Rollout-Plan

| Phase | Scope | Status | Datum | Deliverables |
|---|---|---|---|---|
| **Phase 1** | Logging + Health + Cache | ✅ done | 2026-02-27 | v0.1.0, 12 Tests |
| **Phase 2** | Rate Limiting + Security | ✅ done | 2026-02-27 | v0.2.0, +9 Tests (22 total) |
| **Phase 3** | Email + Tasks + Monitoring | ✅ done | 2026-02-27 | v0.3.0, +9 Tests (31 total) |
| **Phase 4** | Consumer-Integration (erster Hub) | 🔲 pending | — | Hub-Integration, Validation, PyPI/Wheel |

---

## 8. Risiken & Mitigationen

- **Over-Engineering:** YAGNI — Module nur bei konkretem Bedarf in einem Consumer aktivieren. Optional Extras halten Dependencies schlank.
- **Breaking Changes:** Semantic Versioning + CHANGELOG. Major-Upgrades nur mit Migration Guide. Consumer pinnen auf Minor-Version.
- **Vendor Lock-in:** Abstraktion über Interfaces. Provider austauschbar (SMTP ↔ Resend). Graceful Degradation bei fehlenden optionalen Dependencies.
- **Testbarkeit:** Eigene Test-Suite (31 Tests). Consumer-Tests mocken Library-Interfaces. Integration-Tests in CI.
- **Debugging:** HumanFormatter für lokale Entwicklung. Source-Installation: `pip install -e platform/packages/iil-django-commons`.

---

## 9. Entschiedene Fragen

- **Hosting:** Monorepo-Package in `platform/packages/iil-django-commons/`. Distribution als Wheel oder Git-Subdirectory-Install. Kein separater PyPI-Index nötig.
- **Scope:** Alle 8 Module in 3 Phasen implementiert (v0.1.0→v0.3.0). Consumer-Integration steht aus.
- **Monitoring-Stack:** Prometheus-Integration via optionalem `prometheus_client`. Grafana-Setup ist Consumer-Verantwortung.
- **Naming:** `iil-django-commons` (Package-Name), `iil_commons` (Python-Import).

---

## 10. Nächste Schritte

1. ~~ADR reviewen und Entscheidung treffen~~ ✅ accepted
2. ~~Phase 1–3 Module implementieren~~ ✅ v0.3.0 (2026-02-27)
3. **Phase 4: Ersten Consumer-Hub integrieren** (z.B. billing-hub oder research-hub)
4. Wheel bauen und in Hub-Repos als Dependency einbinden
5. `BaseTask.__call__` auf Celery-Lifecycle-Hooks umstellen (Review-Finding)
6. `HEALTH_PATHS`-Filter in `RequestLogMiddleware` einbauen (Health-Request-Spam vermeiden)
