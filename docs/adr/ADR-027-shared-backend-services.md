# ADR-027: Shared Backend Services für Django-Projekte

_Zentralisierte Cross-Cutting Concerns als modulare Packages_

| Feld | Wert |
| --- | --- |
| **ADR-ID** | ADR-027 |
| **Titel** | Shared Backend Services für Django-Projekte |
| **Status** | Proposed (v2 — nach Review überarbeitet) |
| **Datum** | 2026-02-12 |
| **Review-Datum** | 2026-02-12 |
| **Autor** | Achim Dehnert / Claude AI |
| **Reviewer** | Cascade (IT-Architekt-Perspektive) |
| **Betrifft** | Alle Django-Projekte: bfagent, risk-hub, travel-beat, weltenhub, trading-hub, pptx-hub, wedding-hub |
| **Related ADRs** | ADR-009 (Platform Architecture), ADR-012 (MCP Quality Standards), ADR-021 (Unified Deployment) |
| **Supersedes** | ADR-2026-001 (Entwurf, nicht angenommen) |

---

## Änderungshistorie

| Version | Datum | Änderung |
| --- | --- | --- |
| v1 | 2026-02-12 | Initialer Entwurf (ADR-2026-001) |
| v2 | 2026-02-12 | Vollständige Überarbeitung nach Architecture Review: 4 Blocker und 10 signifikante Findings adressiert. Scope auf alle Projekte erweitert, Multi-Tenancy integriert, Monolith durch modulare Packages ersetzt, Naming korrigiert, Database-First je Modul, realistische Timeline, Migrationsstrategie ergänzt. |

---

## 1. Kontext und Problemstellung

### 1.1 Ausgangslage

Die iil.pet-Plattform umfasst **7 Django-basierte Projekte**, die jeweils eigenständig Backend-Infrastruktur implementieren:

| Projekt | Brand | Health-Endpoint | Logging | Cache | Rate Limiting |
| --- | --- | --- | --- | --- | --- |
| bfagent | BFAgent | `/healthz/` | Django default | Kein | Kein |
| risk-hub | Schutztat | `/health/` | Django default | Redis | DRF Throttling |
| travel-beat | DriftTales | `/health/` | Django default | Redis | View-Dekorator |
| weltenhub | Weltenforger | `/health/` | Django default | Kein | Kein |
| trading-hub | AI-Trades | `/livez/` | Django default | Redis | Kein |
| pptx-hub | Prezimo | (keiner) | Django default | Kein | Kein |
| wedding-hub | (geplant) | (keiner) | Django default | Kein | Kein |

### 1.2 Probleme

- **Code-Duplikation:** Jedes Projekt implementiert Health Checks, Caching und Logging individuell.
- **Inkonsistenz:** 4 verschiedene Health-Endpoint-Pfade. Unterschiedliche Logging-Formate und Rate-Limiting-Ansätze.
- **Wartungsaufwand:** Security-Patches müssen in jedem Projekt einzeln nachgezogen werden.
- **Onboarding:** Neue Projekte starten bei Null.
- **Keine Tenant-Awareness:** Cache-Keys, Log-Context und Rate-Limits berücksichtigen `tenant_id` nicht konsistent (vgl. ADR-009).

### 1.3 Ziel

Modulare Packages für Cross-Cutting Concerns, die in `platform/packages/` leben, `tenant_id`-aware sind und schrittweise adoptierbar sind.

---

## 2. Entscheidungskriterien

- **Ökosystem-Konsistenz:** Einfügen in bestehendes `platform/packages/`-Ökosystem (8 existierende Packages).
- **Modul-Isolation:** Jedes Package unabhängig versioniert. Breaking Change in Cache betrifft nicht Logging.
- **Database-First:** Module mit DB-Aspekten definieren Schema. Module ohne begründen dies.
- **Multi-Tenancy:** Jedes Modul definiert, wie es mit `tenant_id` umgeht.
- **YAGNI:** Nur Module mit ≥2 konkreten Consumern werden implementiert.

---

## 3. Bewertete Optionen

| Kriterium | A: Monorepo-Packages | B: Standalone PyPI | C: Git Submodule | D: Cookiecutter |
| --- | --- | --- | --- | --- |
| Versionierung | ✅ semver per Package | ✅ semver, pip | ⚠️ Git SHA | ❌ Snapshot |
| Ökosystem-Konsistenz | ✅ Bestehendes Pattern | ❌ Neues Repo | ⚠️ Coupled | ✅ Standalone |
| Modul-Isolation | ✅ Pro Package | ⚠️ Ein Package, Extras | ⚠️ Coupled | ✅ Standalone |
| Onboarding | ✅ onboard-repo Integration | ⚠️ Separater Schritt | ⚠️ Git knowledge | ✅ Simple |

**Option B (v1-Ansatz) ABGELEHNT** wegen: Monolith-Library mit shared Versionierung, neues Repo außerhalb `platform/packages/`, problematisches Naming (`iil-django-commons`).

---

## 4. Entscheidung

**Gewählt: Option A — Modulare Packages in `platform/packages/`**

Installation via Git-Subdirectory:

```bash
pip install "git+https://github.com/achimdehnert/platform.git@django-logging-v0.1.0#subdirectory=packages/django-logging"
```

---

## 5. Package-Architektur

### 5.1 Geplante Packages (nur bei ≥2 Consumern)

| Package | Verantwortung | Consumer | Phase |
| --- | --- | --- | --- |
| `django-logging` | Structured JSON Logging, Correlation-ID, Tenant-Context | Alle 7 | **Phase 1** |
| `django-health` | Standardisierter `/health/`-Endpoint | Alle 7 | **Phase 1** |
| `django-cache` | Tenant-aware Cache-Decorators, Invalidation | risk-hub, travel-beat, trading-hub | **Phase 2** |
| `django-ratelimit` | Tenant-aware Rate Limiting, Sliding Window | travel-beat, risk-hub, wedding-hub | **Phase 3** |

**Nicht implementiert (YAGNI):** Email (kein Consumer), Monitoring/Prometheus (kein Stack), Security Headers (Django Built-in reicht), Celery Base Task (zu projektspezifisch).

### 5.2 Naming Conventions

| Aspekt | Konvention | Beispiel |
| --- | --- | --- |
| Verzeichnis | `platform/packages/django-{concern}/` | `platform/packages/django-logging/` |
| Python-Import | `platform_{concern}` | `platform_logging` |
| Settings-Namespace | `PLATFORM_{CONCERN}` | `PLATFORM_LOGGING` |
| Git-Tag | `django-{concern}-v{semver}` | `django-logging-v0.1.0` |

### 5.3 Package-Struktur (Beispiel)

```
platform/packages/django-logging/
├── src/platform_logging/
│   ├── __init__.py              # __version__
│   ├── apps.py                  # PlatformLoggingConfig(AppConfig)
│   ├── conf.py                  # PLATFORM_LOGGING defaults
│   ├── middleware.py             # CorrelationIDMiddleware, RequestLogMiddleware
│   ├── formatters.py            # JSONFormatter, HumanFormatter
│   └── context.py               # TenantContextProcessor
├── tests/
├── pyproject.toml
├── CHANGELOG.md
└── README.md
```

---

## 6. Modul-Spezifikationen

### 6.1 `django-logging` (Phase 1)

**Multi-Tenancy:** `CorrelationIDMiddleware` liest `request.tenant_id` und injiziert es in den structlog-Context. Jede Log-Zeile enthält `tenant_id` automatisch.

```python
class CorrelationIDMiddleware:
    def __call__(self, request):
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        tenant_id = getattr(request, "tenant_id", None)
        structlog.contextvars.bind_contextvars(
            correlation_id=correlation_id,
            tenant_id=str(tenant_id) if tenant_id else "none",
        )
        response = self.get_response(request)
        response["X-Correlation-ID"] = correlation_id
        return response
```

**Database-First:** Keine DB-Tabellen. Logs gehören in Log-Aggregation, nicht in die App-DB. Bewusste Ausnahme, da Log-Persistenz kein Domänen-Concern ist.

**Settings:**

```python
PLATFORM_LOGGING = {
    "FORMAT": "json",              # "json" | "human"
    "LEVEL": "INFO",
    "INCLUDE_TENANT": True,
    "REQUEST_LOG_ENABLED": True,
}
```

### 6.2 `django-health` (Phase 1)

**Vereinheitlichung:** Alle Projekte bekommen `/health/` (Readiness) und `/health/live/` (Liveness).

**Multi-Tenancy:** Nicht relevant. Health Checks prüfen Infrastructure, nicht Tenant-Daten. Endpoint liegt **außerhalb** der Tenant-Middleware.

**Database-First:** Keine eigenen Tabellen. Checks sind Read-only (`SELECT 1`).

**Settings:**

```python
PLATFORM_HEALTH = {
    "CHECKS": ["database", "redis"],
    "ENDPOINT": "/health/",
}
```

### 6.3 `django-cache` (Phase 2)

**Multi-Tenancy (KRITISCH):** Cache-Keys MÜSSEN `tenant_id` enthalten:

```python
@cached_view(ttl=300)
def guest_list(request):
    ...
# Generierter Key: "t:{tenant_id}:{path}"

def invalidate_tenant_cache(tenant_id: str, pattern: str = "*"):
    cache.delete_pattern(f"t:{tenant_id}:{pattern}")
```

**Database-First:** Keine DB-Tabellen. Cache ist ephemeral (Derived, nicht Spec gemäß ADR-009).

**Settings:**

```python
PLATFORM_CACHE = {
    "DEFAULT_TTL": 300,
    "TENANT_AWARE": True,
}
```

### 6.4 `django-ratelimit` (Phase 3)

**Multi-Tenancy:** Rate Limits per Tenant-Scope:

| Scope | Key-Struktur | Verwendung |
| --- | --- | --- |
| `tenant` | `rl:{tenant_id}:{endpoint}` | Alle User eines Tenants teilen Limit |
| `user` | `rl:{tenant_id}:{user_id}:{endpoint}` | Per User innerhalb Tenant |
| `global` | `rl:global:{endpoint}` | Absolutes Limit |

**Database-First:** Keine DB-Tabellen. Zähler in Redis (TTL-basiert). Bei Redis-Ausfall: Fail-Open.

**Settings:**

```python
PLATFORM_RATELIMIT = {
    "DEFAULT": "100/h",
    "SCOPE": "tenant",
    "FAIL_OPEN": True,
    "PATHS": {"/api/": "60/min", "/auth/login/": "5/min"},
}
```

---

## 7. Bestandsprojekt-Migration

### 7.1 Phase 1 (Logging + Health) — Alle Projekte

| Projekt | Aufwand | Änderungen |
| --- | --- | --- |
| bfagent | 15 Min | INSTALLED_APPS + Middleware + `/healthz/` → `/health/` redirect |
| risk-hub | 10 Min | INSTALLED_APPS + Middleware + Health-URL anpassen |
| travel-beat | 10 Min | INSTALLED_APPS + Middleware + Health-URL beibehalten |
| weltenhub | 10 Min | INSTALLED_APPS + Middleware |
| trading-hub | 15 Min | INSTALLED_APPS + Middleware + `/livez/` → `/health/` redirect |
| pptx-hub | 10 Min | INSTALLED_APPS + Middleware + Health-URL neu |
| wedding-hub | 10 Min | INSTALLED_APPS + Middleware + Health-URL neu |

**Gesamt Phase 1:** ~80 Minuten für alle 7 Projekte.

### 7.2 Abwärtskompatibilität

Legacy-Endpoints erhalten permanente Redirects:

```python
# urls.py (Übergangsphase)
urlpatterns = [
    path("", include("platform_health.urls")),
    path("healthz/", RedirectView.as_view(url="/health/", permanent=True)),
]
```

---

## 8. Onboarding-Integration

Erweiterung des bestehenden `onboard-repo.md`-Workflows:

| # | Anforderung | Prüfung |
| --- | --- | --- |
| ON-01 | `platform-django-logging` in requirements | grep |
| ON-02 | `platform-django-health` in requirements | grep |
| ON-03 | `platform_logging` in INSTALLED_APPS | Settings-Check |
| ON-04 | `CorrelationIDMiddleware` in MIDDLEWARE | Settings-Check |
| ON-05 | `/health/` Endpoint erreichbar | `curl -s /health/` |

---

## 9. Rollout-Plan

| Phase | Scope | Timeline | Deliverables |
| --- | --- | --- | --- |
| **Phase 1** | `django-logging` + `django-health` | Woche 1–2 | 2 Packages, CI, Tests |
| **Phase 1b** | Rollout alle 7 Projekte | Woche 3 | Migration abgeschlossen |
| **Phase 2** | `django-cache` | Woche 5–6 (bei Bedarf) | Tenant-aware Caching |
| **Phase 3** | `django-ratelimit` | Woche 8+ (bei Bedarf) | Tenant-aware Rate Limiting |

---

## 10. Risiken und Mitigationen

| Risiko | Impact | Mitigation |
| --- | --- | --- |
| Over-Engineering | Hoch | YAGNI: nur 2 Module in Phase 1. Weitere nur bei ≥2 Consumern. |
| Breaking Changes | Mittel | Semver per Package. Consumer pinnen auf Minor. |
| Verwaiste Library | Hoch | Phase 1 bewusst klein. Nur starten wenn Pilotprojekte bestätigt. |
| Tenant-Data-Leak (Cache) | Kritisch | `tenant_id` mandatory in Cache-Keys. Integration-Tests. |
| Redis-Ausfall | Mittel | Fail-Open für Rate Limiting. Logging ohne Redis. Health meldet Status. |

---

## 11. Technische Abgrenzung

**Was dieses ADR NICHT ist:**

- Kein Monitoring-Stack-ADR (Prometheus + Grafana erfordert eigenes Infra-ADR)
- Kein Email-Service-ADR (erst bei konkretem Consumer)
- Kein Security-Hardening-ADR (Django SecurityMiddleware + Config reicht)
- Kein Celery-Pattern-ADR (zu projektspezifisch)

---

## 12. Review-Dokumentation

### 12.1 Adressierte Blocker (🔴)

| ID | Finding | Maßnahme in v2 |
| --- | --- | --- |
| S-01 | Bestehende 6 Projekte ignoriert | Scope auf alle 7 Projekte erweitert (Sektion 1.1, 7) |
| S-02 | Bestehende Package-Strategie ignoriert | Packages in `platform/packages/` statt eigenem Repo (Sektion 4, 5) |
| A-01 | Database-First nicht adressiert | DB-Bewertung pro Modul mit Begründung (Sektion 6.1–6.4) |
| A-02 | Multi-Tenancy ausgeblendet | `tenant_id` in jedem Modul spezifiziert (Sektion 6.1–6.4) |

### 12.2 Adressierte signifikante Findings (🟡)

| ID | Finding | Maßnahme in v2 |
| --- | --- | --- |
| F-01 | ADR-Nummerierung inkonsistent | Umbenannt zu ADR-027 (sequentiell) |
| S-03 | Onboarding-Workflow nicht referenziert | Sektion 8: onboard-repo Integration |
| A-03 | Monolith-Library statt Micro-Packages | Aufgeteilt in 4 unabhängige Packages |
| A-04 | Service-Layer-Pattern nicht beachtet | Middleware-Pattern beibehalten (akzeptabel für Infrastructure), EmailService entfernt |
| N-01 | Package-Name problematisch | `platform_{concern}` statt `iil_commons` |
| N-02 | Flat Settings-Dict | Per-Modul Namespace: `PLATFORM_LOGGING`, `PLATFORM_HEALTH`, etc. |
| T-01 | 6/8 Module sind dünne Wrapper | Reduziert auf 4 Module mit echtem Mehrwert |
| T-02 | Email-Modul premature | Entfernt (YAGNI) |
| R-01 | Unrealistischer Timeline | Von 8 Wochen/8 Module auf 3 Wochen/2 Module (Phase 1) |
| R-02 | Migrationsstrategie fehlt | Sektion 7: Migration pro Projekt mit Aufwandschätzung |

### 12.3 Adressierte Minor Findings (🟢)

| ID | Finding | Maßnahme in v2 |
| --- | --- | --- |
| F-02 | Fehlende Pflichtfelder | Related ADRs, Review-Datum, Supersedes ergänzt |
| T-03 | Prometheus ohne Stack | Monitoring-Modul entfernt, Verweis auf separates Infra-ADR |

---

## 13. Nächste Schritte

1. ADR-027 v2 reviewen und Entscheidung treffen
2. `platform/packages/django-logging/` erstellen mit `pyproject.toml` + CI
3. `platform/packages/django-health/` erstellen
4. Pilotintegration in travel-beat und risk-hub
5. Rollout auf restliche 5 Projekte
6. `onboard-repo.md` Workflow erweitern
