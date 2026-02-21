---
status: accepted
date: 2026-02-21
decision-makers: Achim Dehnert
---

# ADR-028: Platform Context – Konsolidierung der Platform Foundation

_Migration von `bfagent-core` zu `platform-context` als einheitliches Foundation-Package für alle Django-Projekte_

| Feld | Wert |
| --- | --- |
| **ADR-ID** | ADR-028 |
| **Titel** | Platform Context – Konsolidierung der Platform Foundation |
| **Status** | Accepted (v2) |
| **Datum** | 2026-02-12 |
| **Autor** | Achim Dehnert / Claude AI (IT-Architekt-Perspektive) |
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
| `context.py` | Thread-safe Request Context via `contextvars` (tenant_id, user_id, request_id) | Alle 7 Projekte | Keine |
| `middleware.py` | `RequestContextMiddleware` + `SubdomainTenantMiddleware` | Alle 7 Projekte | Keine (liest nur) |
| `db.py` | `set_db_tenant()` / `get_db_tenant()` für Postgres RLS Session-Variable | Alle 7 Projekte | Keine eigene Tabelle (SET LOCAL) |
| `context_processors.py` | Django Template Context Processor für Tenant-Info | Alle 7 Projekte | Keine |
| `audit.py` | `emit_audit_event()` für DSGVO-Compliance Audit Trail | Alle Projekte mit Compliance-Anforderung | Ja – `AuditEvent` Model |
| `outbox.py` | `emit_outbox_event()` für Transactional Outbox Pattern | Projekte mit Event-Publishing | Ja – `OutboxMessage` Model |
| `models.py` | `AuditEvent`, `OutboxMessage` | Projekte mit Audit/Outbox | Ja – DB-Tabellen |
| `admin.py` | Django Admin für AuditEvent, OutboxMessage (read-only) | Projekte mit Audit | Nein |

**Erkenntnis:** ~70% des Codes in `bfagent-core` ist **generische Platform-Infrastruktur**, die unabhängig von BFAgent ist. Nur ~30% (Audit, Outbox) ist Domain-Logik – allerdings ist auch diese generisch genug für alle Projekte (DSGVO-Compliance betrifft jedes Projekt).

### 1.2 Probleme

#### P-01: Irreführender Package-Name

Der Name `bfagent-core` suggeriert "nur für BFAgent", obwohl das Package Platform-weit verwendet wird. Jedes neue Projekt muss ein Package installieren, dessen Name einen anderen Projektnamen trägt:

```python
# risk-hub/settings.py – semantisch falsch:
INSTALLED_APPS = [
    "bfagent_core",  # ← Warum "bfagent" in risk-hub?
]

# risk-hub/requirements.txt
bfagent-core @ git+https://github.com/achimdehnert/platform.git#subdirectory=packages/bfagent-core
```

Dies widerspricht dem PLATFORM_ARCHITECTURE_MASTER Prinzip **Separation of Concerns** (§1.3): Packages sollen nach ihrer Verantwortung benannt sein, nicht nach dem Projekt, in dem sie entstanden sind.

#### P-02: Funktionale Überlappung mit ADR-027

ADR-027 v2 (Shared Backend Services) definiert ein neues Package `django-logging` mit `CorrelationIDMiddleware`, das:

- Eine eigene Correlation-ID generiert (`X-Correlation-ID` Header)
- Tenant-Context in structlog injiziert
- Request/Response-Logging bereitstellt

Das existierende `bfagent-core` implementiert **bereits**:

- Correlation-ID-Generierung in `RequestContextMiddleware` (`X-Request-Id` Header)
- Tenant Context Management via `set_tenant()` / `get_context()`
- Propagation via `contextvars`

**Ergebnis:** Zwei Packages lösen dasselbe Problem mit unterschiedlichen Header-Namen und Mechanismen. Consumer müssen wählen, welche Middleware sie verwenden.

#### P-03: Fehlende Einordnung in Package-Hierarchie

Der PLATFORM_ARCHITECTURE_MASTER (§2.2) definiert eine klare Package-Hierarchie:

```
platform_core          (Basis, keine Abhängigkeiten)
       ↓
platform_users         (→ platform_core)
       ↓
platform_creative      (→ platform_core, platform_users)
```

`bfagent-core` existiert außerhalb dieser Hierarchie. ADR-027 definiert 4 neue Packages, die alle Tenant-Context benötigen, aber `bfagent-core` nicht als Foundation referenzieren.

#### P-04: DSGVO-Compliance ist Platform-Concern

`emit_audit_event()` und das Transactional Outbox Pattern sind nicht BFAgent-spezifisch. Jedes Projekt, das personenbezogene Daten verarbeitet (= alle 7 Projekte), benötigt DSGVO-konforme Audit Trails. Audit und Outbox gehören in ein Platform-Package.

### 1.3 Ziel

Ein korrekt benanntes Foundation-Package `platform-context`, das als **Single Source of Truth** für Request Context, Multi-Tenancy, Audit und Event Publishing dient. Alle neuen ADR-027 Packages bauen auf `platform-context` auf statt eigene Context-Management-Mechanismen zu implementieren.

### 1.4 Anforderungen

| ID | Anforderung | Priorität | Quelle |
| --- | --- | --- | --- |
| R-01 | Zero Breaking Changes am Tag 1 (Compatibility Shim) | 🔴 Kritisch | PLATFORM_ARCHITECTURE_MASTER §1.4 (Zero Breaking Changes) |
| R-02 | Kein Datenverlust bei DB-Migration | 🔴 Kritisch | PLATFORM_ARCHITECTURE_MASTER §1.1 (Database-First) |
| R-03 | Jedes Projekt kann im eigenen Tempo migrieren | 🔴 Kritisch | ADR-009 §1.3 (Maintain app autonomy) |
| R-04 | Klarer Deprecation-Pfad mit Timeline | 🟡 Hoch | ADR-010 (Domain Versioning System) |
| R-05 | ADR-027 Packages definieren Dependency auf `platform-context` | 🟡 Hoch | ADR-027 v2 Review B-01 |
| R-06 | Package-Name reflektiert Verantwortung | 🟡 Hoch | PLATFORM_ARCHITECTURE_MASTER §2.2 |
| R-07 | CI/CD-Pipeline für neue Packages | 🟢 Mittel | ADR-009 §3.1 (Reusable Workflows) |

---

## 2. Entscheidungskriterien

Gemäß PLATFORM_ARCHITECTURE_MASTER Kern-Prinzipien:

| Prinzip | Anwendung auf diese Entscheidung |
| --- | --- |
| **Database-First** (§1.1) | DB-Tabellen behalten explizite `db_table`-Namen. Kein `ALTER TABLE`. |
| **Separation of Concerns** (§1.3) | Package-Name = Verantwortung. Context + Tenancy + Audit = `platform-context`. |
| **Zero Breaking Changes** (§1.4) | Compatibility Shim mit Re-Exports. Deprecation über 3 Monate. |
| **Fail Loud, Not Silent** (§1.5) | DeprecationWarnings in Logs, nicht stille Weiterleitung. |
| **Idempotenz** (§1.6) | Migration ist idempotent: Mehrfach ausführbar ohne Datenverlust. |

---

## 3. Bewertete Optionen

### 3.1 Optionsmatrix

| Kriterium | A: django-logging auf bfagent-core | B: Extract Context, Audit bleibt | **C: Full Move (gewählt)** |
| --- | --- | --- | --- |
| Breaking Changes Tag 1 | ✅ Null | ✅ Null (Re-Exports) | ✅ Null (Re-Exports) |
| Name-Problem gelöst | ❌ "bfagent" bleibt | ⚠️ Teilweise (Audit noch "bfagent") | ✅ Vollständig |
| INSTALLED_APPS Zielzustand | 2 Packages | 2 Packages | 1 Package |
| DB-Migration nötig | ❌ Keine | ❌ Keine | ⚠️ `SeparateDatabaseAndState` (keine physische DB-Änderung) |
| bfagent-core langfristig | Lebt ewig weiter | Lebt als Audit-Container weiter | Entfernbar nach 3 Monaten |
| Packages im Ökosystem | +0 (bestehend) | +1 (platform-context) | +1 (platform-context), -1 (bfagent-core → Shim) |
| Aufwand | ~2h | ~4h | ~6h |
| ADR-027 Integration | ⚠️ django-logging hängt von "bfagent-core" ab | ✅ django-logging → platform-context | ✅ django-logging → platform-context |

### 3.2 Entscheidung Option A → Abgelehnt

Option A ist die schnellste Lösung, löst aber das Naming-Problem nicht. Mit jedem neuen Projekt wächst die technische Schuld: 7 Projekte installieren `bfagent-core` obwohl nur 1 Projekt "BFAgent" heißt. ADR-027 Packages würden eine Dependency auf ein falsch benanntes Package deklarieren.

### 3.3 Entscheidung Option B → Abgelehnt

Option B löst das Naming-Problem für Context und Middleware, aber nicht für Audit und Outbox. Da DSGVO-Compliance (Audit) ein Platform-Concern ist, der alle 7 Projekte betrifft, ist die Trennung von Audit in `bfagent-core` nicht gerechtfertigt. Das Ergebnis wäre ein Zombie-Package, das nur wegen 2 Modulen existiert.

### 3.4 Entscheidung Option C → Gewählt

**Begründung:**

1. **DB-Risiko ist entschärft:** Die Models verwenden explizite `db_table`-Namen (`"bfagent_core_audit_event"`, `"bfagent_core_outbox_message"`). Kein `ALTER TABLE` nötig. `SeparateDatabaseAndState` ist ein bewährtes Django-Pattern.

2. **Gleicher Tag-1-Komfort wie Option B:** Compatibility Shim mit Re-Exports bedeutet, dass kein Projekt sofort etwas ändern muss.

3. **Sauberer Endzustand:** `bfagent-core` wird nach Deprecation-Phase komplett entfernbar. Kein Zombie-Package.

4. **Audit ist Platform-Concern:** Jedes Projekt mit personenbezogenen Daten braucht Audit Trails. `emit_audit_event()` gehört in `platform-context`.

5. **Einmaliger Mehraufwand gering:** ~2h mehr als Option B (eine `SeparateDatabaseAndState`-Migration + AppConfig-Anpassung).

---

## 4. Entscheidung

**Gewählt: Option C – Full Move von `bfagent-core` nach `platform-context`**

Alle Module, Models und Funktionen aus `bfagent-core` werden in das neue Package `platform-context` verschoben. `bfagent-core` wird zu einem reinen Compatibility Shim, der über einen definierten Deprecation-Pfad (3 Monate) entfernbar wird.

---

## 5. Package-Architektur

### 5.1 Zielstruktur `platform-context`

```
platform/packages/platform-context/
├── src/platform_context/
│   ├── __init__.py              # Public API, __version__ = "0.1.0"
│   ├── apps.py                  # PlatformContextConfig(AppConfig)
│   │
│   ├── # ── Context Management ──────────────────────────
│   ├── context.py               # RequestContext, get_context(), set_*()
│   ├── context_processors.py    # Django Template Context Processor
│   │
│   ├── # ── Multi-Tenancy ───────────────────────────────
│   ├── middleware.py             # RequestContextMiddleware, SubdomainTenantMiddleware
│   ├── db.py                    # set_db_tenant(), get_db_tenant() (Postgres RLS)
│   │
│   ├── # ── Compliance & Events ─────────────────────────
│   ├── audit.py                 # emit_audit_event()
│   ├── outbox.py                # emit_outbox_event()
│   ├── models.py                # AuditEvent, OutboxMessage (db_table bleibt!)
│   ├── admin.py                 # Read-only Admin für Audit/Outbox
│   │
│   └── # ── Migrations ──────────────────────────────────
│       └── migrations/
│           └── 0001_move_from_bfagent_core.py   # SeparateDatabaseAndState
│
├── tests/
│   ├── __init__.py
│   ├── settings.py              # Minimal Django settings für Tests
│   ├── test_context.py
│   ├── test_middleware.py
│   ├── test_db.py
│   ├── test_audit.py
│   └── test_outbox.py
│
├── pyproject.toml
├── CHANGELOG.md
└── README.md
```

### 5.2 Compatibility Shim `bfagent-core` v0.2.0

```
platform/packages/bfagent-core/
├── src/bfagent_core/
│   ├── __init__.py              # Re-Exports + DeprecationWarnings
│   ├── apps.py                  # BfagentCoreCompatConfig (kein eigenes label)
│   ├── context.py               # Re-Export von platform_context.context
│   ├── context_processors.py    # Re-Export von platform_context.context_processors
│   ├── middleware.py             # Re-Export von platform_context.middleware
│   ├── db.py                    # Re-Export von platform_context.db
│   ├── audit.py                 # Re-Export von platform_context.audit
│   ├── outbox.py                # Re-Export von platform_context.outbox
│   ├── models.py                # ENTFERNT (lebt jetzt in platform_context)
│   └── admin.py                 # ENTFERNT (lebt jetzt in platform_context)
│
├── pyproject.toml               # dependencies: ["platform-context>=0.1.0"]
└── CHANGELOG.md
```

### 5.3 Naming Conventions

Gemäß ADR-027 §5.2 und PLATFORM_ARCHITECTURE_MASTER §2.2:

| Aspekt | Konvention | Wert |
| --- | --- | --- |
| Verzeichnis | `platform/packages/{name}/` | `platform/packages/platform-context/` |
| Python-Import | `platform_context` | `from platform_context import get_context` |
| pip-Name | `platform-context` | `pip install platform-context` |
| Git-Tag | `platform-context-v{semver}` | `platform-context-v0.1.0` |
| Django app_label | `platform_context` | `INSTALLED_APPS = ["platform_context"]` |

### 5.4 Package-Hierarchie nach Migration

```
platform/packages/
│
├── platform-context/           ← NEU: Foundation (dieses ADR)
│   ├── Context Management      (contextvars, RequestContext)
│   ├── Multi-Tenancy           (Middleware, RLS)
│   └── Compliance              (Audit, Outbox)
│
├── bfagent-core/               ← v0.2.0: Compatibility Shim (→ entfernbar +3M)
│   └── Re-Exports → platform-context
│
├── django-logging/             ← ADR-027 Phase 1
│   └── depends on: platform-context  (structlog-Brücke, kein eigenes Context-Mgmt)
│
├── django-health/              ← ADR-027 Phase 1
│   └── standalone (kein Context nötig)
│
├── django-cache/               ← ADR-027 Phase 2
│   └── depends on: platform-context  (tenant_id für Cache-Keys)
│
├── django-ratelimit/           ← ADR-027 Phase 3
│   └── depends on: platform-context  (tenant_id für Rate-Limit-Scope)
│
├── bfagent-llm/                ← Bestehendes Package
│   └── depends on: platform-context  (Migration von bfagent-core Imports)
│
├── creative-services/          ← Bestehendes Package (keine Änderung)
├── deployment-core/            ← ADR-009 (keine Änderung)
├── platform_core/              ← PLATFORM_ARCHITECTURE_MASTER (Foundation für creative)
└── sphinx-export/              ← Bestehendes Package (keine Änderung)
```

**Abhängigkeitsregeln** (gemäß PLATFORM_ARCHITECTURE_MASTER §2.2):

```
platform_core           (Basis: Fields, Exceptions – keine Abhängigkeiten)
       ↓
platform-context        (Context, Tenancy, Audit – depends on: Django, structlog)
       ↓
django-logging          (structlog-Integration – depends on: platform-context)
django-cache            (Tenant-aware Cache – depends on: platform-context)
django-ratelimit        (Tenant-aware Rate Limiting – depends on: platform-context)
bfagent-llm             (LLM Framework – depends on: platform-context)
```

**Regel: Keine Rückwärts-Abhängigkeiten.** `platform-context` importiert NICHT aus `django-logging`, `bfagent-llm` oder Consumer-Packages.

---

## 6. Technische Spezifikation

### 6.1 `platform-context` – Kern-Module

#### 6.1.1 `__init__.py` – Public API

```python
"""
platform-context: Foundation package for BF Agent Platform.

Provides:
- Request context management (tenant, user, request_id)
- Multi-tenancy middleware with subdomain resolution
- Postgres RLS session variable management
- Audit event logging for DSGVO compliance
- Transactional outbox pattern for reliable event publishing
"""

from platform_context.context import (
    RequestContext,
    get_context,
    set_request_id,
    set_tenant,
    set_user_id,
    clear_context,
)
from platform_context.audit import emit_audit_event
from platform_context.outbox import emit_outbox_event
from platform_context.db import set_db_tenant, get_db_tenant

__version__ = "0.1.0"

__all__ = [
    # Context
    "RequestContext",
    "get_context",
    "set_request_id",
    "set_tenant",
    "set_user_id",
    "clear_context",
    # Audit
    "emit_audit_event",
    # Outbox
    "emit_outbox_event",
    # DB
    "set_db_tenant",
    "get_db_tenant",
]
```

#### 6.1.2 `apps.py` – Django AppConfig

```python
"""Django application configuration for platform-context."""

from django.apps import AppConfig


class PlatformContextConfig(AppConfig):
    """
    AppConfig for platform-context.

    Registers AuditEvent and OutboxMessage models.
    Uses explicit app_label to avoid conflicts during migration.
    """

    name = "platform_context"
    verbose_name = "Platform Context"
    default_auto_field = "django.db.models.BigAutoField"
```

#### 6.1.3 `models.py` – Unveränderte DB-Tabellennamen

```python
"""
Core Django models for platform-context.

CRITICAL: db_table names are intentionally kept as "bfagent_core_*"
to avoid database migration. This is a conscious decision documented
in ADR-028 §6.3 (SeparateDatabaseAndState).

These models are used across all Platform hubs for DSGVO compliance
and reliable event publishing.
"""

import uuid
from django.db import models


class AuditEvent(models.Model):
    """
    Audit trail for compliance-relevant mutations.

    Every write operation that affects risk-relevant or personal data
    should create an AuditEvent record for DSGVO compliance.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    actor_user_id = models.UUIDField(null=True, blank=True, db_index=True)

    category = models.CharField(max_length=80, db_index=True)
    action = models.CharField(max_length=80, db_index=True)
    entity_type = models.CharField(max_length=120, db_index=True)
    entity_id = models.UUIDField(db_index=True)

    payload = models.JSONField(default=dict)
    request_id = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        # ─────────────────────────────────────────────────────────
        # INTENTIONALLY kept as "bfagent_core_audit_event".
        # No ALTER TABLE needed. See ADR-028 §6.3.
        # ─────────────────────────────────────────────────────────
        db_table = "bfagent_core_audit_event"
        indexes = [
            models.Index(fields=["tenant_id", "created_at"]),
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["tenant_id", "category", "action"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.category}.{self.action} on {self.entity_type}:{self.entity_id}"


class OutboxMessage(models.Model):
    """
    Transactional outbox for reliable event publishing.

    Events are written within the same transaction as the business
    operation, then published by a background worker.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    topic = models.CharField(max_length=120, db_index=True)
    payload = models.JSONField(default=dict)

    published_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        # ─────────────────────────────────────────────────────────
        # INTENTIONALLY kept as "bfagent_core_outbox_message".
        # No ALTER TABLE needed. See ADR-028 §6.3.
        # ─────────────────────────────────────────────────────────
        db_table = "bfagent_core_outbox_message"
        indexes = [
            models.Index(fields=["tenant_id", "published_at", "created_at"]),
            models.Index(fields=["topic", "created_at"]),
        ]
        ordering = ["created_at"]

    def __str__(self) -> str:
        status = "published" if self.published_at else "pending"
        return f"{self.topic} ({status})"

    @property
    def is_published(self) -> bool:
        return self.published_at is not None
```

### 6.2 `pyproject.toml`

```toml
[project]
name = "platform-context"
version = "0.1.0"
description = "Foundation package for BF Agent Platform: Context, Tenancy, Audit, Outbox"
readme = "README.md"
requires-python = ">=3.11"
license = {text = "MIT"}
authors = [
    {name = "Achim Dehnert", email = "achim@dehnert.com"}
]
classifiers = [
    "Development Status :: 4 - Beta",
    "Framework :: Django :: 5.0",
    "Framework :: Django :: 5.1",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]

dependencies = [
    "Django>=5.0,<6.0",
    "pydantic>=2.0",
    "structlog>=24.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-django>=4.8",
    "pytest-asyncio>=0.23",
    "ruff>=0.4",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/platform_context"]

[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "tests.settings"
python_files = ["test_*.py"]
asyncio_mode = "auto"

[tool.ruff]
line-length = 100
target-version = "py311"
```

### 6.3 DB-Migration: `SeparateDatabaseAndState`

Dies ist das Herzstück der Migration. Die Tabellen existieren bereits physisch in der Datenbank mit den Namen `bfagent_core_audit_event` und `bfagent_core_outbox_message`. Django muss nur wissen, dass diese Tabellen jetzt zum `app_label = "platform_context"` gehören.

```python
# platform-context/src/platform_context/migrations/0001_move_from_bfagent_core.py
"""
Migrate model ownership from bfagent_core to platform_context.

This migration uses SeparateDatabaseAndState to tell Django that the
AuditEvent and OutboxMessage models now live in platform_context,
WITHOUT modifying the actual database tables.

The db_table names remain "bfagent_core_audit_event" and
"bfagent_core_outbox_message" intentionally (see ADR-028 §6.1.3).

IMPORTANT: After running this migration in a project, also run:
    python manage.py migrate bfagent_core zero --fake
to clean up the old migration records from django_migrations.
"""

import uuid
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True
    dependencies = []

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="AuditEvent",
                    fields=[
                        ("id", models.UUIDField(
                            default=uuid.uuid4, editable=False,
                            primary_key=True, serialize=False,
                        )),
                        ("tenant_id", models.UUIDField(db_index=True)),
                        ("actor_user_id", models.UUIDField(
                            blank=True, db_index=True, null=True,
                        )),
                        ("category", models.CharField(
                            db_index=True, max_length=80,
                        )),
                        ("action", models.CharField(
                            db_index=True, max_length=80,
                        )),
                        ("entity_type", models.CharField(
                            db_index=True, max_length=120,
                        )),
                        ("entity_id", models.UUIDField(db_index=True)),
                        ("payload", models.JSONField(default=dict)),
                        ("request_id", models.CharField(
                            blank=True, db_index=True, max_length=64, null=True,
                        )),
                        ("created_at", models.DateTimeField(
                            auto_now_add=True, db_index=True,
                        )),
                    ],
                    options={
                        "db_table": "bfagent_core_audit_event",
                        "ordering": ["-created_at"],
                        "indexes": [
                            models.Index(
                                fields=["tenant_id", "created_at"],
                                name="platform_co_tenant__a1b2c3_idx",
                            ),
                            models.Index(
                                fields=["entity_type", "entity_id"],
                                name="platform_co_entity__d4e5f6_idx",
                            ),
                            models.Index(
                                fields=["tenant_id", "category", "action"],
                                name="platform_co_tenant__g7h8i9_idx",
                            ),
                        ],
                    },
                ),
                migrations.CreateModel(
                    name="OutboxMessage",
                    fields=[
                        ("id", models.UUIDField(
                            default=uuid.uuid4, editable=False,
                            primary_key=True, serialize=False,
                        )),
                        ("tenant_id", models.UUIDField(db_index=True)),
                        ("topic", models.CharField(
                            db_index=True, max_length=120,
                        )),
                        ("payload", models.JSONField(default=dict)),
                        ("published_at", models.DateTimeField(
                            blank=True, db_index=True, null=True,
                        )),
                        ("created_at", models.DateTimeField(
                            auto_now_add=True, db_index=True,
                        )),
                    ],
                    options={
                        "db_table": "bfagent_core_outbox_message",
                        "ordering": ["created_at"],
                        "indexes": [
                            models.Index(
                                fields=["tenant_id", "published_at", "created_at"],
                                name="platform_co_tenant__j1k2l3_idx",
                            ),
                            models.Index(
                                fields=["topic", "created_at"],
                                name="platform_co_topic_c_m4n5o6_idx",
                            ),
                        ],
                    },
                ),
            ],
            # Keine database_operations: Die Tabellen existieren bereits!
            database_operations=[],
        ),
    ]
```

**Warum das sicher ist:**

| Aspekt | Erklärung |
| --- | --- |
| `state_operations` | Teilt Django mit: "Diese Models gehören jetzt zu `platform_context`" |
| `database_operations = []` | Die physischen Tabellen werden **nicht** verändert |
| `db_table = "bfagent_core_*"` | Tabellennamen bleiben identisch – keine Daten-Migration nötig |
| Index-Namen | Neue Index-Namen mit `platform_co_` Prefix. Django ignoriert physisch vorhandene Indizes mit altem Namen, solange das Schema passt. |

### 6.4 Compatibility Shim: `bfagent-core` v0.2.0

#### 6.4.1 `__init__.py`

```python
"""
bfagent-core v0.2.0 – Compatibility Shim.

DEPRECATED: All functionality has moved to platform-context (ADR-028).
This package exists only for backward compatibility during the
3-month deprecation period.

Migration guide:
    # VORHER:
    from bfagent_core.context import get_context
    from bfagent_core.audit import emit_audit_event

    # NACHHER:
    from platform_context import get_context
    from platform_context.audit import emit_audit_event

Timeline:
    v0.2.0  – Re-Exports + DeprecationWarnings (jetzt)
    v1.0.0  – Re-Exports entfernt (frühestens 3 Monate nach v0.2.0)
"""

import warnings

warnings.warn(
    "bfagent_core is deprecated. Use platform_context instead. "
    "See ADR-028 for migration guide.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export everything for backward compatibility
from platform_context import (  # noqa: F401, E402
    RequestContext,
    get_context,
    set_request_id,
    set_tenant,
    set_user_id,
    clear_context,
    emit_audit_event,
    emit_outbox_event,
    set_db_tenant,
    get_db_tenant,
)

__version__ = "0.2.0"

__all__ = [
    "RequestContext",
    "get_context",
    "set_request_id",
    "set_tenant",
    "set_user_id",
    "clear_context",
    "emit_audit_event",
    "emit_outbox_event",
    "set_db_tenant",
    "get_db_tenant",
]
```

#### 6.4.2 Sub-Module Re-Exports

Jedes Sub-Modul des Shims leitet an `platform_context` weiter:

```python
# bfagent_core/context.py
"""DEPRECATED: Use platform_context.context instead."""
from platform_context.context import *  # noqa: F401,F403

# bfagent_core/middleware.py
"""DEPRECATED: Use platform_context.middleware instead."""
from platform_context.middleware import *  # noqa: F401,F403

# bfagent_core/db.py
"""DEPRECATED: Use platform_context.db instead."""
from platform_context.db import *  # noqa: F401,F403

# bfagent_core/audit.py
"""DEPRECATED: Use platform_context.audit instead."""
from platform_context.audit import *  # noqa: F401,F403

# bfagent_core/outbox.py
"""DEPRECATED: Use platform_context.outbox instead."""
from platform_context.outbox import *  # noqa: F401,F403

# bfagent_core/context_processors.py
"""DEPRECATED: Use platform_context.context_processors instead."""
from platform_context.context_processors import *  # noqa: F401,F403
```

#### 6.4.3 `apps.py` – Verhindert Model-Collision

```python
"""DEPRECATED Django AppConfig for backward compatibility."""

from django.apps import AppConfig


class BfagentCoreCompatConfig(AppConfig):
    """
    Compatibility AppConfig that registers no models.

    Models now live in platform_context. This AppConfig exists only
    so that INSTALLED_APPS = ["bfagent_core"] doesn't crash.

    IMPORTANT: This config has NO models. If both "platform_context"
    and "bfagent_core" are in INSTALLED_APPS, there is no conflict
    because only platform_context registers the models.
    """

    name = "bfagent_core"
    label = "bfagent_core_compat"  # Distinct label to avoid collision
    verbose_name = "BFAgent Core (Deprecated – use platform_context)"

    def ready(self):
        import warnings
        warnings.warn(
            "bfagent_core is deprecated. Remove from INSTALLED_APPS "
            "and use 'platform_context' instead. See ADR-028.",
            DeprecationWarning,
            stacklevel=2,
        )
```

#### 6.4.4 `pyproject.toml` v0.2.0

```toml
[project]
name = "bfagent-core"
version = "0.2.0"
description = "DEPRECATED: Compatibility shim for platform-context. See ADR-028."
requires-python = ">=3.11"
license = {text = "MIT"}

dependencies = [
    "platform-context>=0.1.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/bfagent_core"]
```

#### 6.4.5 `models.py` und `admin.py` – ENTFERNT

Die Dateien `models.py` und `admin.py` werden aus `bfagent-core` **komplett entfernt** (nicht re-exportiert), da Django Models nur von einem `app_label` registriert sein dürfen. Die `BfagentCoreCompatConfig` mit `label = "bfagent_core_compat"` stellt sicher, dass Django keine Model-Collision erkennt.

---

## 7. Consumer-Migrationspfad

### 7.1 Migration pro Projekt

Jedes Projekt kann im eigenen Tempo migrieren. Drei Varianten sind möglich:

#### Variante A: Sofort vollständig migrieren (empfohlen)

```python
# 1. requirements.txt / pyproject.toml
- bfagent-core @ git+...#subdirectory=packages/bfagent-core
+ platform-context @ git+https://github.com/achimdehnert/platform.git#subdirectory=packages/platform-context

# 2. settings.py
INSTALLED_APPS = [
-   "bfagent_core",
+   "platform_context",
    ...
]

MIDDLEWARE = [
-   "bfagent_core.middleware.RequestContextMiddleware",
-   "bfagent_core.middleware.SubdomainTenantMiddleware",
+   "platform_context.middleware.RequestContextMiddleware",
+   "platform_context.middleware.SubdomainTenantMiddleware",
    ...
]

TEMPLATES = [{
    "OPTIONS": {
        "context_processors": [
-           "bfagent_core.context_processors.tenant_context",
+           "platform_context.context_processors.tenant_context",
        ],
    },
}]

# 3. Alle Imports aktualisieren (grep -r "bfagent_core" --include="*.py")
- from bfagent_core.context import get_context, set_tenant
+ from platform_context import get_context, set_tenant

- from bfagent_core.audit import emit_audit_event
+ from platform_context.audit import emit_audit_event

- from bfagent_core.db import set_db_tenant
+ from platform_context.db import set_db_tenant

# 4. DB-Migration ausführen
python manage.py migrate platform_context    # SeparateDatabaseAndState (no-op auf DB)
python manage.py migrate bfagent_core zero --fake  # Alte Migration-Records bereinigen
```

**Aufwand pro Projekt:** ~15 Minuten (grep + replace + migrate)

#### Variante B: Erstmal nichts ändern (Shim fängt ab)

```python
# requirements.txt – bfagent-core v0.2.0 zieht platform-context automatisch
bfagent-core>=0.2.0 @ git+...#subdirectory=packages/bfagent-core

# settings.py – KEINE Änderung nötig
INSTALLED_APPS = ["bfagent_core", ...]  # DeprecationWarning in Logs

# Code – KEINE Änderung nötig
from bfagent_core.context import get_context  # DeprecationWarning, funktioniert
```

**Aufwand:** 0 Minuten. Migration wird aufgeschoben.

#### Variante C: Schrittweise migrieren

```python
# Phase 1: Dependency hinzufügen, INSTALLED_APPS umstellen
INSTALLED_APPS = ["platform_context", ...]  # NEU
# + manage.py migrate platform_context + bfagent_core zero --fake

# Phase 2 (eigenes Tempo): Imports Datei für Datei umstellen
# grep -r "bfagent_core" --include="*.py" | wc -l  → Fortschritt tracken
```

### 7.2 Aufwandschätzung pro Projekt

| Projekt | Variante A (sofort) | bfagent_core Imports (geschätzt) | Risiko |
| --- | --- | --- | --- |
| bfagent | 20 Min | ~15 Stellen | Niedrig (Hauptconsumer) |
| risk-hub | 15 Min | ~10 Stellen | Niedrig |
| travel-beat | 15 Min | ~8 Stellen | Niedrig |
| weltenhub | 10 Min | ~5 Stellen | Niedrig |
| trading-hub | 10 Min | ~5 Stellen | Niedrig |
| pptx-hub | 10 Min | ~3 Stellen | Niedrig |
| cad-hub | 10 Min | ~3 Stellen | Niedrig |
| bfagent-llm (Package) | 10 Min | ~2 Stellen | Niedrig |

**Gesamt Phase 1 (alle Projekte, Variante A):** ~100 Minuten

### 7.3 Sonderfall: `bfagent-llm`

Das Package `bfagent-llm` (v0.1.0) hat eine Abhängigkeit auf `bfagent-core`:

```toml
# bfagent-llm/pyproject.toml – aktuell
dependencies = [
    "Django>=5.0,<6.0",
    # ... (bfagent-core ist implizite Abhängigkeit)
]
```

**Migration:** `bfagent-llm` aktualisiert seinen Import und deklariert explizit die Dependency auf `platform-context`:

```toml
# bfagent-llm/pyproject.toml – nach Migration
dependencies = [
    "Django>=5.0,<6.0",
    "platform-context>=0.1.0",
    # ...
]
```

---

## 8. ADR-027 Integration

### 8.1 Auswirkung auf `django-logging`

ADR-027 v3 (nach Überarbeitung gemäß B-01) definiert `django-logging` als **dünne structlog-Brücke**, die auf `platform-context` aufbaut:

```python
# django-logging/src/platform_logging/middleware.py
import structlog
from platform_context import get_context


class StructlogContextMiddleware:
    """
    Brücke: Propagiert platform_context.RequestContext → structlog contextvars.

    MUSS nach RequestContextMiddleware + SubdomainTenantMiddleware stehen.
    Generiert KEINE eigene Correlation-ID – nutzt die aus platform-context.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        ctx = get_context()
        structlog.contextvars.bind_contextvars(
            request_id=ctx.request_id or "none",
            tenant_id=str(ctx.tenant_id) if ctx.tenant_id else "none",
            tenant_slug=ctx.tenant_slug or "none",
            user_id=str(ctx.user_id) if ctx.user_id else "anonymous",
        )
        response = self.get_response(request)
        structlog.contextvars.clear_contextvars()
        return response
```

### 8.2 Ziel-Middleware-Stack nach Migration

```python
MIDDLEWARE = [
    # 1. platform-context: Request Context + Tenant Resolution
    "platform_context.middleware.RequestContextMiddleware",      # request_id, user_id
    "platform_context.middleware.SubdomainTenantMiddleware",     # tenant_id, RLS

    # 2. django-logging: structlog-Integration (ADR-027)
    "platform_logging.middleware.StructlogContextMiddleware",    # Binds context → structlog
    "platform_logging.middleware.RequestLogMiddleware",          # Request/Response logging

    # 3. Django Standard
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    # ...
]
```

### 8.3 Header-Vereinheitlichung

| Aspekt | bfagent-core v0.1.0 | ADR-027 v2 (django-logging) | Zielzustand (nach ADR-028) |
| --- | --- | --- | --- |
| Header-Name | `X-Request-Id` | `X-Correlation-ID` | `X-Request-Id` (platform-context ist SSOT) |
| Generierung | `RequestContextMiddleware` | `CorrelationIDMiddleware` | `RequestContextMiddleware` (platform-context) |
| structlog-Binding | Nicht vorhanden | In Middleware | `StructlogContextMiddleware` (django-logging) |
| Tenant-Injection | `SubdomainTenantMiddleware` | `CorrelationIDMiddleware` | `SubdomainTenantMiddleware` (platform-context) |

---

## 9. Deprecation-Timeline

| Version | Zeitpunkt | Verhalten | Consumer-Aktion |
| --- | --- | --- | --- |
| **platform-context v0.1.0** | Tag 1 | Neues Package verfügbar | Pilotprojekte migrieren |
| **bfagent-core v0.2.0** | Tag 1 | Re-Exports + `DeprecationWarning` | Nichts (Shim fängt ab) |
| **bfagent-core v0.3.0** | +6 Wochen | Warnings werden `FutureWarning` (lauter) | Import-Migration starten |
| **bfagent-core v1.0.0** | +3 Monate | Re-Exports **entfernt**. Package ist leer. | MUSS migriert sein |
| **bfagent-core (entfernt)** | +4 Monate | Package aus `platform/packages/` gelöscht | – |

**Gate für v1.0.0:** Erst wenn `grep -r "bfagent_core" --include="*.py"` in **allen** 7 Repositories + `bfagent-llm` null Ergebnisse liefert.

Gemäß PLATFORM_ARCHITECTURE_MASTER §1.4 (Zero Breaking Changes): Die Deprecation-Phase stellt sicher, dass kein Projekt durch die Migration bricht. Erst nach bestätigter Migration aller Consumer werden Re-Exports entfernt.

---

## 10. Rollout-Plan

| Tag | Aufgabe | Deliverable | Verantwortung |
| --- | --- | --- | --- |
| **1** | `platform-context` Package erstellen: alle Module aus `bfagent-core` kopieren | Neues Package mit identischer Funktionalität | Entwicklung |
| **1** | `SeparateDatabaseAndState` Migration schreiben | `0001_move_from_bfagent_core.py` | Entwicklung |
| **1** | Tests für `platform-context` (übernommen aus `bfagent-core/tests/`) | Grüne Testsuite | Entwicklung |
| **1** | `bfagent-core` v0.2.0: Dependency + Re-Exports + DeprecationWarnings | `pyproject.toml`, `__init__.py`, entfernte `models.py` | Entwicklung |
| **2** | Pilot: **travel-beat** migrieren (Variante A) | INSTALLED_APPS, MIDDLEWARE, Imports, `migrate` | Entwicklung |
| **2** | Pilot: **risk-hub** migrieren (Variante A) | INSTALLED_APPS, MIDDLEWARE, Imports, `migrate` | Entwicklung |
| **3** | Smoke-Test: Beide Pilotprojekte auf Staging deployen | Health Checks grün, Audit-Events werden geschrieben | QA |
| **3-5** | Rollout restliche 5 Projekte + `bfagent-llm` | Alle Consumer migriert | Entwicklung |
| **5** | `onboard-repo.md` aktualisieren: `platform-context` statt `bfagent-core` | Onboarding-Guide | Dokumentation |
| **+6W** | `bfagent-core` v0.3.0: `FutureWarning` statt `DeprecationWarning` | Release | Entwicklung |
| **+3M** | Verifikation: alle Consumer migriert (`grep` in allen Repos) | Clean-Report | QA |
| **+3M** | `bfagent-core` v1.0.0: Re-Exports entfernt | Release | Entwicklung |
| **+4M** | `bfagent-core` Package aus Repository entfernen | Cleanup | Entwicklung |

---

## 11. CI/CD-Integration

### 11.1 Package-CI

Gemäß ADR-009 §3.1 nutzt `platform-context` die Reusable Workflows:

```yaml
# platform/.github/workflows/ci-platform-context.yml
name: CI – platform-context
on:
  push:
    paths: ["packages/platform-context/**"]
  pull_request:
    paths: ["packages/platform-context/**"]

jobs:
  ci:
    uses: ./.github/workflows/_ci-python.yml
    with:
      python_version: "3.12"
      working_directory: packages/platform-context
      coverage_threshold: 90
    secrets: inherit
```

### 11.2 Kompatibilitätsmatrix

| Dimension | Unterstützt |
| --- | --- |
| Python | 3.11, 3.12 |
| Django | 5.0, 5.1 |
| PostgreSQL | 15, 16 |
| structlog | ≥24.0 |

---

## 12. Risiken und Mitigationen

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
| --- | --- | --- | --- |
| `SeparateDatabaseAndState` Reihenfolge falsch | Niedrig | Hoch (Django versucht Tabellen neu anzulegen) | Deployment-Script mit expliziter Reihenfolge: `migrate platform_context` → `migrate bfagent_core zero --fake` |
| Beide AppConfigs in INSTALLED_APPS | Mittel | Mittel (Model-Collision) | `BfagentCoreCompatConfig` hat `label = "bfagent_core_compat"` und keine Models → keine Collision |
| Consumer vergisst Migration, deployed mit altem Code | Niedrig | Niedrig (Shim funktioniert) | `DeprecationWarning` in Logs → Monitoring-Alert |
| Index-Namen-Konflikt bei `SeparateDatabaseAndState` | Niedrig | Mittel | Index-Namen in Migration explizit mit neuem Prefix. PostgreSQL ignoriert Duplikate wenn Schema passt. |
| `bfagent-llm` hat implizite `bfagent_core`-Dependency | Mittel | Mittel | `bfagent-llm` wird in Phase 1 (Tag 3-5) explizit migriert |
| Deprecation-Timeline zu kurz | Niedrig | Mittel | 3 Monate ist konservativ für 7 Projekte mit je ~15 Min Aufwand. Gate-Prüfung vor v1.0.0. |

---

## 13. Konsequenzen

### 13.1 Positiv

- **Korrekte Benennung:** Jedes Projekt installiert `platform-context` – der Name reflektiert die Verantwortung.
- **Single Source of Truth:** Ein Package für Context, Tenancy, Audit. ADR-027 Packages haben eine klare Dependency.
- **Saubere Hierarchie:** `platform-context` fügt sich in PLATFORM_ARCHITECTURE_MASTER §2.2 Package-Hierarchie ein.
- **DSGVO-Compliance als Platform-Feature:** Audit ist nicht mehr an "BFAgent" gebunden, sondern Platform-Infrastruktur.
- **ADR-027 entblockt:** `django-logging` kann als dünne structlog-Brücke auf `platform-context` aufbauen, ohne eigenes Context-Management.
- **Langfristige Reduktion:** Nach Deprecation-Phase entfällt `bfagent-core` vollständig (1 Package weniger zu pflegen).

### 13.2 Negativ

- **Einmaliger Migrationsaufwand:** ~100 Minuten für alle 7 Projekte (Variante A).
- **Temporäre Komplexität:** Während der Deprecation-Phase existieren 2 Packages (`platform-context` + `bfagent-core` Shim).
- **DB-Tabellennamen bleiben "bfagent_core_*":** Kosmetischer Nachteil, der bewusst in Kauf genommen wird, um `ALTER TABLE` zu vermeiden.

### 13.3 Mitigation

| Nachteil | Mitigation |
| --- | --- |
| Migrationsaufwand | Shim ermöglicht Zero-Pressure-Migration. Kein Projekt muss sofort migrieren. |
| Temporäre Komplexität | Klar definierte Deprecation-Timeline mit Gate-Prüfung vor Entfernung. |
| Kosmetische Tabellennamen | Dokumentiert im Model-Docstring. Kein funktionaler Nachteil. Späterer Rename per `ALTER TABLE RENAME` möglich, aber nicht nötig. |

---

## 14. Technische Abgrenzung

**Was dieses ADR ist:**
- Konsolidierung von `bfagent-core` in `platform-context`
- Definition des Compatibility Shims und Deprecation-Pfads
- Klärung der Dependency-Hierarchie für ADR-027 Packages

**Was dieses ADR NICHT ist:**
- Kein ADR für structlog-Integration (das ist ADR-027 `django-logging`)
- Kein ADR für Health-Check-Endpoints (das ist ADR-027 `django-health`)
- Kein Rename der DB-Tabellen (bewusst ausgeschlossen)
- Keine funktionale Erweiterung von `bfagent-core` (identische API)

---

## 15. Offene Fragen

| # | Frage | Empfehlung | Entscheidung |
| --- | --- | --- | --- |
| 1 | Soll `platform-context` eine Dependency auf `platform_core` haben? | Nein – `platform_core` (PLATFORM_ARCHITECTURE_MASTER §2.3) enthält `BaseLookupTable` und `PydanticSchemaField`, die `platform-context` nicht braucht. Beide sind Foundation-Packages auf gleicher Ebene. | Offen |
| 2 | Sollen die `db_table`-Namen langfristig zu `platform_context_*` umbenannt werden? | Nicht jetzt. Kann in einer späteren Phase per `ALTER TABLE RENAME` erfolgen, bringt aber keinen funktionalen Vorteil. | Offen |
| 3 | Soll `bfagent-llm` auch umbenannt werden? | Perspektivisch ja (`platform-llm`), aber eigenes ADR. Scope dieses ADR ist nur `bfagent-core`. | Ausgeklammert |

---

## 16. Referenzen

- [PLATFORM_ARCHITECTURE_MASTER](../PLATFORM_ARCHITECTURE_MASTER.md) – Kern-Prinzipien, Package-Hierarchie
- [ADR-009: Centralized Deployment Architecture](./ADR-009-deployment-architecture.md) – Reusable Workflows, deployment-core
- [ADR-027: Shared Backend Services v2](./ADR-027-shared-backend-services.md) – Review Finding B-01 (Auslöser dieses ADR)
- [Django SeparateDatabaseAndState](https://docs.djangoproject.com/en/5.1/ref/migration-operations/#separatedatabaseandstate) – Django-Dokumentation
- [bfagent-core v0.1.0 Source](../packages/bfagent-core/) – Bestehender Quellcode

---

## 17. Changelog

| Datum | Autor | Änderung |
| --- | --- | --- |
| 2026-02-12 | Achim Dehnert / Claude AI | Initialer Entwurf (v1). Entstanden aus ADR-027 v2 Review. |
