# ADR-028: Platform Context – Konsolidierung der Platform Foundation

_Migration von `bfagent-core` zu `platform-context` als einheitliches Foundation-Package für alle Django-Projekte_

| Feld | Wert |
| --- | --- |
| **ADR-ID** | ADR-028 |
| **Titel** | Platform Context – Konsolidierung der Platform Foundation |
| **Status** | Accepted (v2) |
| **Datum** | 2026-02-12 |
| **Autor** | Achim Dehnert / Cascade (IT-Architekt-Perspektive) |
| **Reviewer** | – |
| **Betrifft** | Alle Django-Projekte: bfagent, risk-hub, travel-beat, weltenhub, trading-hub, pptx-hub, cad-hub |
| **Related ADRs** | ADR-009 (Centralized Deployment Architecture), ADR-022 (Platform Consistency Standard v2), ADR-027 (Shared Backend Services), ADR-010 (Domain Versioning System) |
| **Supersedes** | – (ergänzt `bfagent-core` v0.1.0) |
| **Blocking** | ADR-027 v3 (abhängig von Entscheidung zu `platform-context`) |

---

## Änderungshistorie

| Version | Datum | Änderung |
| --- | --- | --- |
| v1 | 2026-02-12 | Initialer Entwurf. Entstanden aus ADR-027 v2 Review Finding B-01 (Funktionale Überlappung `bfagent-core` ↔ `django-logging`). Option C (Full Move) gewählt nach systematischem Vergleich mit Option B (Extract-Only). |
| v2 | 2026-02-12 | Status → **Accepted**. `platform-context` v0.1.0 erstellt (`packages/platform-context/`). `bfagent-core` v0.2.0 als Compatibility-Shim aktualisiert. audit.py + outbox.py model-agnostisch via Django-Settings. Tests für context-Modul. |

---

## 1. Kontext und Problemstellung

### 1.1 Ausgangslage

Das Package `bfagent-core` (v0.1.0, Pfad `platform/packages/bfagent-core/`) wurde als erstes Shared Package für die BFAgent Platform entwickelt. Es stellt fundamentale Infrastruktur bereit, die **jedes** Django-Projekt der Plattform benötigt:

| Modul | Funktion | Scope | DB-Abhängigkeit |
| --- | --- | --- | --- |
| `context.py` | Thread-safe Request Context via `contextvars` | Alle 7 Projekte | Keine |
| `middleware.py` | `RequestContextMiddleware` + `SubdomainTenantMiddleware` | Alle 7 Projekte | Keine (liest nur) |
| `db.py` | `set_db_tenant()` / `get_db_tenant()` für Postgres RLS | Alle 7 Projekte | Keine eigene Tabelle |
| `context_processors.py` | Django Template Context Processor für Tenant-Info | Alle 7 Projekte | Keine |
| `audit.py` | `emit_audit_event()` für DSGVO-Compliance Audit Trail | Alle Projekte mit Compliance | Ja – `AuditEvent` Model |
| `outbox.py` | `emit_outbox_event()` für Transactional Outbox Pattern | Projekte mit Event-Publishing | Ja – `OutboxMessage` Model |
| `models.py` | `AuditEvent`, `OutboxMessage` | Projekte mit Audit/Outbox | Ja – DB-Tabellen |

**Erkenntnis:** ~70% des Codes in `bfagent-core` ist **generische Platform-Infrastruktur**, die unabhängig von BFAgent ist.

### 1.2 Probleme

- **P-01: Irreführender Package-Name** — `bfagent-core` suggeriert "nur für BFAgent"
- **P-02: Funktionale Überlappung** — ADR-027 `django-logging` vs. `bfagent-core` für Correlation-ID
- **P-03: Fehlende Package-Hierarchie** — `bfagent-core` existiert außerhalb der definierten Hierarchie
- **P-04: DSGVO-Compliance ist Platform-Concern** — Audit gehört nicht in ein app-spezifisches Package

### 1.3 Ziel

Ein korrekt benanntes Foundation-Package `platform-context`, das als **Single Source of Truth** für Request Context, Multi-Tenancy, Audit und Event Publishing dient.

---

## 2. Entscheidung

**Gewählt: Option C – Full Move von `bfagent-core` nach `platform-context`**

Alle Module und Funktionen aus `bfagent-core` werden in `platform-context` verschoben. `bfagent-core` wird zu einem Compatibility Shim mit 3-Monats-Deprecation.

| Kriterium | A: django-logging auf bfagent-core | B: Extract Context only | **C: Full Move (gewählt)** |
| --- | --- | --- | --- |
| Breaking Changes Tag 1 | ✅ Null | ✅ Null | ✅ Null (Re-Exports) |
| Name-Problem gelöst | ❌ | ⚠️ Teilweise | ✅ Vollständig |
| bfagent-core langfristig | Lebt ewig | Audit-Container | Entfernbar +3M |

---

## 3. Package-Architektur

### 3.1 Zielstruktur `platform-context` v0.1.0

```
platform/packages/platform-context/
├── src/platform_context/
│   ├── __init__.py              # Public API
│   ├── apps.py                  # PlatformContextConfig
│   ├── context.py               # RequestContext, get_context(), set_*()
│   ├── context_processors.py    # Django Template Context Processor
│   ├── middleware.py             # RequestContextMiddleware, SubdomainTenantMiddleware
│   ├── db.py                    # set_db_tenant(), get_db_tenant() (Postgres RLS)
│   ├── audit.py                 # emit_audit_event() (model-agnostic)
│   ├── outbox.py                # emit_outbox_event() (model-agnostic)
│   └── exceptions.py            # PlatformError hierarchy
├── tests/
│   ├── test_context.py
│   └── test_middleware.py
├── pyproject.toml
└── README.md
```

### 3.2 Compatibility Shim `bfagent-core` v0.2.0

```
platform/packages/bfagent-core/
├── src/bfagent_core/
│   ├── __init__.py              # Re-Exports + DeprecationWarnings
│   ├── context.py               # Re-Export von platform_context.context
│   ├── middleware.py             # Re-Export + TenantPermissionMiddleware (bfagent-specific)
│   ├── db.py                    # Re-Export von platform_context.db
│   ├── audit.py                 # Re-Export von platform_context.audit
│   ├── outbox.py                # Re-Export von platform_context.outbox
│   ├── context_processors.py    # Re-Export von platform_context.context_processors
│   └── exceptions.py            # Re-Export von platform_context.exceptions
├── pyproject.toml               # dependencies: ["platform-context>=0.1.0"]
└── README.md
```

### 3.3 Key Design Decisions

- **audit.py und outbox.py sind model-agnostisch** — Konfiguration via `PLATFORM_AUDIT_MODEL` und `PLATFORM_OUTBOX_MODEL` in Django-Settings
- **TenantPermissionMiddleware bleibt in bfagent-core** — Hängt von bfagent-spezifischen Models (CoreUser, TenantMembership) ab
- **Alle Module emittieren DeprecationWarnings** bei Import über den alten Pfad

---

## 4. Consumer-Migrationspfad

### Variante A: Sofort migrieren (empfohlen)

```python
# settings.py
INSTALLED_APPS = [
    "platform_context",  # statt "bfagent_core"
]

MIDDLEWARE = [
    "platform_context.middleware.RequestContextMiddleware",
    "platform_context.middleware.SubdomainTenantMiddleware",
]

# Alle Imports aktualisieren
from platform_context import get_context, set_tenant
from platform_context.audit import emit_audit_event
```

### Variante B: Shim nutzen (keine Änderung nötig)

```python
# bfagent-core v0.2.0 zieht platform-context automatisch
# Alle bestehenden Imports funktionieren weiter mit DeprecationWarning
```

### Aufwand pro Projekt: ~15 Minuten (grep + replace)

---

## 5. Deprecation-Timeline

| Version | Zeitpunkt | Verhalten |
| --- | --- | --- |
| **platform-context v0.1.0** | Tag 1 | Neues Package verfügbar |
| **bfagent-core v0.2.0** | Tag 1 | Re-Exports + `DeprecationWarning` |
| **bfagent-core v0.3.0** | +6 Wochen | `FutureWarning` (lauter) |
| **bfagent-core v1.0.0** | +3 Monate | Re-Exports entfernt |

---

## 6. Implementierungsstatus

### ✅ Abgeschlossen

- [x] `packages/platform-context/` Package erstellt (v0.1.0)
- [x] Module: context, middleware, db, audit, outbox, context_processors, exceptions
- [x] audit.py + outbox.py model-agnostisch (PLATFORM_AUDIT_MODEL, PLATFORM_OUTBOX_MODEL)
- [x] Tests: test_context.py, test_middleware.py
- [x] `bfagent-core` v0.2.0: Compatibility-Shim mit Re-Exports
- [x] `bfagent-core` pyproject.toml: Dependency auf platform-context
- [x] TenantPermissionMiddleware bleibt in bfagent-core (model-spezifisch)

### 🔲 Verbleibend

- [ ] SeparateDatabaseAndState Migration für AuditEvent/OutboxMessage Models
- [ ] Consumer-Migration: Pilotprojekte (travel-beat, risk-hub)
- [ ] Consumer-Migration: Restliche Projekte
- [ ] Onboarding-Guide aktualisieren

---

## 7. Referenzen

- `packages/platform-context/` — Neues Foundation-Package
- `packages/bfagent-core/` — Compatibility-Shim (v0.2.0)
- ADR-027 — Shared Backend Services (django-logging baut auf platform-context auf)
- ADR-022 — Platform Consistency Standard
