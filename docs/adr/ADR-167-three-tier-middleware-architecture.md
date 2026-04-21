---
status: Accepted (Revision v1.1)
date: 2026-04-21
decision-makers: Achim Dehnert, Cascade AI
consulted: []
informed: []
implementation_status: revision_in_progress
amends: ADR-021
supersedes: ADR-167 v1.0 (2026-04-21)
implementation_evidence:
  - "platform_context v0.6.0 (v1.0): HealthBypassMiddleware + SubdomainTenantMiddleware health bypass (22 tests)"
  - "platform_context v0.7.0 (v1.1): dual-mode async/sync, corrected liveness/readiness semantics, method whitelist, text/plain, system checks, Prometheus counter, ReadinessView (62 tests)"
  - "Phase 1 rollout: 9/19 repos on v0.6.0 (risk-hub, bfagent, billing-hub, coach-hub, tax-hub, wedding-hub, writing-hub, pptx-hub, trading-hub)"
  - "tax-hub + trading-hub: local HealthCheckMiddleware replaced with central one"
---

<!-- Drift-Detector-Felder
staleness_months: 6
drift_check_paths:
  - packages/platform-context/src/platform_context/middleware.py
  - packages/platform-context/src/platform_context/health_checks.py
  - packages/platform-context/src/platform_context/health/views.py
  - packages/platform-context/tests/test_middleware.py
supersedes_check: null
-->

# ADR-167 v1.1: Adopt 3-Tier Middleware Standard for Health Probes and Tenant Resolution

> **v1.1 Change Log**
> - **BLOCKER fix:** `/readyz/` removed from default bypass paths; readiness is now an opt-in view that actually checks DB/cache/dependencies.
> - **BLOCKER fix:** `HealthBypassMiddleware` is now dual-mode (sync + async) for ASGI deployments.
> - **CRITICAL fix:** Entkopplung von "Tier" (Architektur) und "Phase" (Rollout) in den Tabellen.
> - **CRITICAL fix:** `ALLOWED_HOSTS`-Erweiterung um `localhost`/`127.0.0.1` nur für `IIL_ENV in {local, ci, docker-internal}`.
> - **HIGH:** Observability via Prometheus-Counter `iil_health_probe_total` + DEBUG-Log.
> - **HIGH:** Django-System-Checks für `HEALTH_PROBE_PATHS` und Middleware-Reihenfolge.
> - **HIGH:** Content-Negotiation (text/plain default, JSON on Accept-Header) + `Cache-Control: no-store`.
> - **MEDIUM:** HTTP-Method-Whitelist (nur GET/HEAD); andere → 405.

## Context and Problem Statement

19 Django-Repositories hatten divergente Middleware-Stacks. Health-Check-Bypasses
wurden individuell in travel-beat (`HealthBypassTenantMiddleware`), research-hub
(`EXEMPT_PATH_PREFIXES`), und bfagent (`.env.prod`-Hack) implementiert.
`ALLOWED_HOSTS`-Fixes mussten quer durch 20 Dateien in 19 Repos angewendet werden.

Es gab keinen Standard, der definiert, welche Middleware ein Repository in
welcher Reihenfolge enthalten muss — was zu inkonsistentem Verhalten bei
Health-Probes, Tenant-Resolution und Request-Context führte.

**v1.1 Zusätzlicher Kontext:** Die ursprüngliche v1.0-Implementierung
hat `/readyz/` mit `/livez/` gleichgestellt (beide returnen statisch `200 OK`).
Das widerspricht Kubernetes-Konvention: Readiness-Probes MÜSSEN
Downstream-Dependencies prüfen (DB, Cache, Message Broker), sonst bekommen
defekte Pods Traffic. v1.1 trennt Liveness (bypass) von Readiness (aktiver Check).

## Decision Drivers

- **Konsistenz:** Health-Probes (`/livez/`) müssen in allen 19 Repos identisch arbeiten.
- **Kubernetes-Konformität:** Liveness ≠ Readiness (klare Trennung).
- **Defense in Depth:** Docker/LB-Health-Checks müssen alle Downstream-Middleware (Auth, CSRF, Tenant) umgehen.
- **DRY:** Per-Repo Health-Bypass-Hacks (3 verschiedene Implementierungen) verletzen Single-Source-of-Truth.
- **Onboarding:** Neue Repos erhalten Health-Probes durch das Hinzufügen einer Middleware-Zeile.
- **Performance auf ASGI:** Async-natives Dispatch (keine `sync_to_async`-Wrapper für Probes).
- **Tenant-Kompatibilität:** Multi-Tenant-Repos (Tier 2/3) dürfen Health-Probes wegen fehlender Subdomain nicht ablehnen.
- **Security:** Kein Host-Header-Spoofing in Produktion.
- **Observability:** Prometheus-Counter und DEBUG-Log für Troubleshooting.

## Considered Options

(Optionen A/B/C aus v1.0 unverändert gültig. Chosen: **Option B — zentrale
`HealthBypassMiddleware` in `platform_context`**, angepasst in v1.1.)

## Decision Outcome

**Chosen option: B — Zentrale `HealthBypassMiddleware`** in Version 0.7.0 des
Pakets `iil-platform-context`, mit den unter "v1.1 Change Log" aufgelisteten
Korrekturen.

### Implementation

Einführung eines **3-Tier Middleware Standards** in `platform_context`
(Paket `iil-platform-context >= 0.7.0`).

#### Tier 1: Platform Base (alle Repos)

Jedes Django-Repository MUSS `HealthBypassMiddleware` als **erste** Middleware
einbinden. Das garantiert, dass `/livez/` und `/healthz/` immer HTTP 200
ohne DB-Zugriff, Auth oder Tenant-Resolution antworten.

```python
MIDDLEWARE = [
    "platform_context.middleware.HealthBypassMiddleware",  # FIRST — ADR-167
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
```

#### Tier 2: Tenant-Aware (subdomain-based RLS, no schema isolation)

Repos, die Subdomain → `tenant_id`-Resolution via RLS (Row-Level Security)
benötigen, fügen `SubdomainTenantMiddleware` nach `HealthBypassMiddleware`
ein. Health-Pfade werden automatisch umgangen (integriert seit v0.6.0).

```python
MIDDLEWARE = [
    "platform_context.middleware.HealthBypassMiddleware",       # Tier 1
    "platform_context.middleware.SubdomainTenantMiddleware",    # Tier 2
    "django.middleware.security.SecurityMiddleware",
    # ...
]
```

#### Tier 3: Schema Isolation (django-tenants)

Repos, die `django-tenants` für per-Tenant-PostgreSQL-Schemata nutzen, verwenden
`TenantMainMiddleware`. `HealthBypassMiddleware` (first) stellt sicher, dass
Health-Probes die Schema-Resolution umgehen.

```python
MIDDLEWARE = [
    "platform_context.middleware.HealthBypassMiddleware",                 # Tier 1
    "django_tenants.middleware.main.TenantMainMiddleware",                # Tier 3
    "platform_context.tenant_utils.middleware.TenantPropagationMiddleware",
    # ...
]
```

### Tier Assignment (Architektur — dauerhaft)

| Tier | Repos | Rationale |
|------|-------|-----------|
| 1 | pptx-hub, illustration-hub, billing-hub, writing-hub, wedding-hub, recruiting-hub, dms-hub, coach-hub, dev-hub, learn-hub, trading-hub | Single-purpose oder kein Multi-Tenant-Datenmodell |
| 2 | risk-hub, bfagent, ausschreibungs-hub | Subdomain-basierte Tenancy mit RLS (ADR-161), Single-Shared-Schema |
| 3 | travel-beat, tax-hub, cad-hub, weltenhub, research-hub | Full `django-tenants` Schema-Isolation (ADR-072) |

### Rollout Phases (zeitlich — einmalig)

**Phase 1 (v0.6.0, abgeschlossen):** 9 Repos auf ursprüngliche Middleware migriert.

**Phase 2 (v0.7.0, geplant):** Alle 19 Repos auf `iil-platform-context 0.7.0`
upgraden. Das umfasst sowohl die Tier-1-Migration (10 ausstehende Repos) als
auch das Upgrade der 9 bereits migrierten Repos von v0.6.0 auf v0.7.0 wegen
der BREAKING CHANGES (`/readyz/` nicht mehr bypassed, Default-Format ist jetzt
`text/plain`).

### `HealthBypassMiddleware` Details (v0.7.0)

- Kurzschließt Requests auf `HEALTH_PROBE_PATHS` mit `"ok\n"` (text/plain).
- Default-Pfade: `/livez/`, `/healthz/` (keine Readiness-Pfade mehr!).
- Konfigurierbar über `settings.HEALTH_PROBE_PATHS` (frozenset).
- HTTP-Methoden-Whitelist: nur `GET` und `HEAD`, andere → `405 Method Not Allowed`.
- Content-Negotiation: `Accept: application/json` → JSON-Response; sonst text/plain.
- Response-Header: `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`.
- Kein DB-Zugriff, keine Auth, keine Tenant-Resolution.
- **Dual-Mode:** sync + async (ASGI-nativ) via `@sync_and_async_middleware`.
- **Observability:** Prometheus-Counter `iil_health_probe_total{path,mode}` +
  strukturiertes DEBUG-Log.
- **Validation:** Django-System-Check (`E167.*`/`W167.*`) prüft Konfiguration beim
  Startup.
- **Tests:** 62 Unit-Tests (sync/async × method × path-form × config × edge cases).

### Readiness Probes (Repo-Verantwortung)

Readiness muss aktive Dependency-Checks durchführen. Dazu stellt v0.7.0
die `ReadinessView` als **Opt-in** bereit:

```python
# <repo>/config/urls.py
urlpatterns = [
    # ...,
    path("readyz/", include("platform_context.health.urls")),
]
```

Die `ReadinessView` führt standardmäßig `SELECT 1` auf `default`-DB aus.
Repos können zusätzliche Checks via `settings.HEALTH_READINESS_CHECKS`
registrieren (Liste dotted-paths auf Callables, die `(name, ok, detail)`
zurückgeben).

Bei Fehler: HTTP 503 mit JSON-Body `{"status": "degraded", "checks": [...]}`.

### Defense in Depth: `ALLOWED_HOSTS` (v1.1 korrigiert)

Die `ALLOWED_HOSTS`-Erweiterung um `localhost` / `127.0.0.1` erfolgt **nur**
in internen Umgebungen:

```python
IIL_ENV = os.environ.get("IIL_ENV", "prod").lower()
_ALLOW_INTERNAL_HOSTS = frozenset({"local", "ci", "docker-internal"})

if IIL_ENV in _ALLOW_INTERNAL_HOSTS:
    for _host in ("localhost", "127.0.0.1"):
        if _host not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(_host)
```

In Produktion (`IIL_ENV=prod`) wird **kein** localhost akzeptiert. Traefik
sendet den korrekten Host-Header, und Health-Probes laufen über den
Service-Namen im Docker-Netz. Das eliminiert den Host-Header-Spoofing-Vektor.

## Consequences

### Good

- Konsistentes Verhalten: Health-Probes arbeiten in allen 19 Repos identisch.
- Korrekte Kubernetes-Semantik: Liveness ≠ Readiness.
- ASGI-Performance: Async-nativ, keine Thread-Pool-Blockade.
- Observability: Prometheus-Counter + Startup-Validation.
- Sicherheit: Kein Host-Header-Spoofing in Produktion.
- Single Source of Truth: Middleware-Logik lebt in `platform_context`, nicht repo-lokal.
- Onboarding: Neue Repos erhalten Health-Probes durch eine Middleware-Zeile.

### Bad (Breaking Changes in v0.7.0)

- Repos mit hart-codiertem JSON-Parsing auf `/livez/` müssen entweder
  `HEALTH_RESPONSE_FORMAT = "json"` setzen oder `Accept: application/json`
  senden.
- Repos, die sich auf `/readyz/` als Statisch-200 verlassen haben, müssen
  `platform_context.health.urls` einbinden oder ihre k8s-Probes auf `/livez/`
  umstellen.
- POST/PUT/DELETE auf `/livez/` antworten jetzt `405` statt `200`.

### Confirmation

Compliance wird verifiziert durch:

1. **Automated:** `curl -s -o /dev/null -w "%{http_code}" -H "Host: localhost" http://127.0.0.1:<port>/livez/` returnt `200` für alle deployten Repos.
2. **CI:** `grep -q "HealthBypassMiddleware" <settings_file>` in Repo-CI oder Drift-Detector.
3. **System Check:** `python manage.py check` returnt keine `E167.*`/`W167.*`-Warnings.
4. **Manuell:** `MIDDLEWARE[0]` in den Settings jedes Repos ist `"platform_context.middleware.HealthBypassMiddleware"`.

## Migration Tracking (Phase 2: v0.7.0)

| Repo | Tier | v0.6.0 Status | v0.7.0 Target |
|------|------|---------------|---------------|
| risk-hub | 2 | ✅ | ⬜ |
| bfagent | 2 | ✅ | ⬜ |
| billing-hub | 1 | ✅ | ⬜ |
| coach-hub | 1 | ✅ | ⬜ |
| tax-hub | 3 | ✅ | ⬜ |
| wedding-hub | 1 | ✅ | ⬜ |
| writing-hub | 1 | ✅ | ⬜ |
| pptx-hub | 1 | ✅ | ⬜ |
| trading-hub | 1 | ✅ | ⬜ |
| ausschreibungs-hub | 2 | ⬜ | ⬜ |
| cad-hub | 3 | ⬜ | ⬜ |
| dev-hub | 1 | ⬜ | ⬜ |
| dms-hub | 1 | ⬜ | ⬜ |
| illustration-hub | 1 | ⬜ | ⬜ |
| learn-hub | 1 | ⬜ | ⬜ |
| recruiting-hub | 1 | ⬜ | ⬜ |
| research-hub | 3 | ⬜ | ⬜ |
| travel-beat | 3 | ⬜ | ⬜ |
| weltenhub | 3 | ⬜ | ⬜ |

## Open Questions

1. **PyPI Publish:** Wann wird `iil-platform-context` auf GitHub Packages PyPI
   publiziert? Das eliminiert das git-clone-from-monorepo Pattern in
   Dockerfiles. Aufgeschoben — verfolgt als Phase 3 in einem zukünftigen ADR.
2. **Kubernetes-Adoption:** Sobald Platform auf k8s migriert wird (derzeit
   Docker Compose + Traefik auf Hetzner), Readiness-Probes auf
   `path: /readyz/` umstellen und Startup-Probe (k8s 1.16+) auf `/livez/`
   evaluieren.

## More Information

- **ADR-021 (amended by this ADR):** Health Probes Convention.
- **ADR-056:** Multi-Tenancy — `TenantPropagationMiddleware` für Service-zu-Service-Aufrufe.
- **ADR-072:** Schema Isolation — `django-tenants` für Tier-3-Repos.
- **ADR-146:** Platform Packages — `iil-platform-context` als Shared Package.
- **ADR-161:** RLS Policies — Row-Level-Security für Tier-2-Repos.
- **Implementation:** `platform/packages/platform-context/src/platform_context/middleware.py`
- **Tests:** `platform/packages/platform-context/tests/test_middleware.py` (62 Tests)
- **Metrics:** Prometheus Counter `iil_health_probe_total{path,mode}`.
- **Kubernetes Probe Docs:** https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/
