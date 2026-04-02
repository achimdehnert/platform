# Architecture Review: ADR-028 — Platform Context

| Feld | Wert |
| --- | --- |
| **Reviewer** | Cascade (IT-Architekt-Perspektive) |
| **Datum** | 2026-02-12 |
| **Reviewed ADR** | ADR-028 v1 — Platform Context Konsolidierung |
| **Methodik** | Source-Code-Analyse `bfagent-core`, Cross-Referenz ADR-009, ADR-022, ADR-027, PLATFORM_ARCHITECTURE_MASTER |
| **Verdict** | **REVISION REQUIRED** — Solides Konzept, aber massive Inventarisierungslücken und Architektur-Vermischung |

---

## Bewertungsskala

| Symbol | Bedeutung |
| --- | --- |
| 🔴 | **Blocker** — muss vor Annahme gelöst werden |
| 🟡 | **Signifikant** — sollte adressiert werden |
| 🟢 | **Minor** — Empfehlung |

---

## 1. BLOCKER: Unvollständige Bestandsaufnahme

### 🔴 B-01: ADR inventarisiert nur ~30% des tatsächlichen Package-Inhalts

ADR-028 §1.1 listet 8 Module. Die Source-Code-Analyse von `platform/packages/bfagent-core/` ergibt **deutlich mehr**:

**Models — ADR kennt 2 von 10:**

| Model | DB-Tabelle | Im ADR? |
| --- | --- | --- |
| `AuditEvent` | `bfagent_core_audit_event` | ✅ |
| `OutboxMessage` | `bfagent_core_outbox_message` | ✅ |
| `Plan` | `bfagent_core_plan` | ❌ |
| `CoreUser` | `bfagent_core_coreuser` | ❌ |
| `Tenant` | `bfagent_core_tenant` | ❌ |
| `TenantMembership` | `bfagent_core_tenantmembership` | ❌ |
| `CorePermission` | `bfagent_core_corepermission` | ❌ |
| `CoreRolePermission` | `bfagent_core_corerolepermission` | ❌ |
| `MembershipPermissionOverride` | `bfagent_core_membershippermissionoverride` | ❌ |
| `PermissionAudit` | `bfagent_core_permissionaudit` | ❌ |

**Weitere fehlende Module:**

| Modul | Inhalt | Im ADR? |
| --- | --- | --- |
| `exceptions.py` | 13 Exception-Klassen (160 Zeilen): PlatformError-Hierarchie mit Tenant-, Membership-, Permission-, User-Errors | ❌ |
| `handlers/tenant.py` | TenantCreateHandler, TenantActivateHandler, TenantSuspendHandler, TenantDeleteHandler mit Command/Result Dataclasses | ❌ |
| `handlers/membership.py` | Membership-Handler | ❌ |
| `handlers/permission.py` | Permission-Handler | ❌ |
| `events/__init__.py` | Event-Definitionen | ❌ |
| `TenantPermissionMiddleware` | 3. Middleware in middleware.py — resolves CoreUser + Permissions pro Request | ❌ |
| Migrations 0001–0008 | 8 Migrations (ADR kennt nur 1 neue) | ❌ |

**Konsequenz:** Die SeparateDatabaseAndState-Migration in §6.3 behandelt nur 2 Tabellen, aber es existieren mindestens 10 mit FK-Beziehungen. Die Compatibility-Shim deckt nur einen Bruchteil der Public API ab.

### 🔴 B-02: SeparateDatabaseAndState für 10 Models statt 2

Die Migration in §6.3 ist für 2 Models spezifiziert. Die tatsächlichen 10 Models haben **Foreign-Key-Beziehungen** (TenantMembership → Tenant, TenantMembership → CoreUser, CoreRolePermission → CorePermission). Die Migration muss:

- Alle 10 Models in korrekter FK-Reihenfolge behandeln
- 8 existierende Migrations im `django_migrations`-Table berücksichtigen
- Index-Namen für alle Models definieren (nicht nur 2)

### 🔴 B-03: Versions-Inkonsistenz

| Quelle | Version |
| --- | --- |
| `pyproject.toml` | `0.1.0` |
| `__init__.py` | `0.2.0` |
| ADR-028 referenziert | "v0.1.0" |
| ADR-028 plant Shim als | "v0.2.0" |

Der Shim v0.2.0 kollidiert mit der existierenden `__version__ = "0.2.0"` in `__init__.py`.

**Empfehlung:** Versionen synchronisieren. Shim als v0.3.0 planen.

---

## 2. Architekturprinzipien

### 🔴 A-01: Separation of Concerns — Infrastructure vs. Domain vermischt

`platform-context` bündelt vier Architektur-Schichten unter einem Dach:

| Schicht | Module | Gehört zusammen? |
| --- | --- | --- |
| **Infrastructure** | context.py, middleware.py (Request/Subdomain), db.py | ✅ "Context" |
| **Domain Models** | Plan, Tenant, CoreUser, Membership, Permission (10 Models) | ❌ Kein "Context" |
| **Business Logic** | handlers/tenant.py, handlers/membership.py, handlers/permission.py | ❌ Kein "Context" |
| **Cross-Cutting** | audit.py, outbox.py, AuditEvent, OutboxMessage | ⚠️ Grenzfall |

Der Name `platform-context` suggeriert Infrastructure, aber das Package enthält die **gesamte Multi-Tenancy-Domäne** mit Business-Logic (Tenant-Lifecycle, RBAC, Membership-Verwaltung).

**Empfehlung — Zwei Optionen:**

**Option 1: Umbenennen zu `platform-core`** (minimaler Aufwand)
- Akzeptiert die Bündelung, gibt ihr einen ehrlichen Namen
- Konsistent mit PLATFORM_ARCHITECTURE_MASTER §2.2 (`platform_core`)
- Löst gleichzeitig die Hierarchie-Kollision (A-02)

**Option 2: Aufsplitten** (sauberer, mehr Aufwand)

```text
platform-context    → Infrastructure: context.py, 2 Middlewares, db.py
platform-tenancy    → Domain: 10 Models, 3 Handler-Module, Exceptions, TenantPermissionMiddleware
platform-compliance → Cross-Cutting: AuditEvent, OutboxMessage, emit_*()
```

### 🟡 A-02: Package-Hierarchie-Kollision

ADR-028 §5.4 zeigt `platform_core` und `platform-context` als separate Packages. Aber die bfagent-core Models (Plan, Tenant, CoreUser) **sind** genau das, was PLATFORM_ARCHITECTURE_MASTER §2.2 als `platform_core` definiert. Zwei Packages für denselben Inhalt = Konfusion.

### 🟡 A-03: Handler-Pattern komplett ignoriert

Die `handlers/`-Directory implementiert das Command/Result-Pattern (PLATFORM_ARCHITECTURE_MASTER §1.6). 3 Handler-Module mit Dataclass-Commands müssen migriert werden, sind aber nicht spezifiziert.

---

## 3. ADR-022 Governance-Compliance

### 🟡 G-01: HEALTH_PATHS fehlt in SubdomainTenantMiddleware

ADR-022 §3.7 **fordert**:

> *"Die SubdomainTenantMiddleware MUSS HEALTH_PATHS ausschließen."*

Der aktuelle Code in `bfagent-core/middleware.py` hat **keinen** HEALTH_PATHS-Ausschluss. Docker-Healthchecks ohne Subdomain erhalten `403 Forbidden`.

ADR-028 migriert den Code 1:1 **ohne** diesen ADR-022-Compliance-Fix zu adressieren. Die Migration sollte als Gelegenheit genutzt werden, die Compliance-Lücke zu schließen.

### 🟡 G-02: `repo_checker` muss aktualisiert werden

Das `repo_checker`-Tool (ADR-022 §9) prüft auf bestimmte Import-Pfade. Nach der Migration von `bfagent_core.middleware` zu `platform_context.middleware` muss es aktualisiert werden.

### 🟡 G-03: Drei Naming-Patterns im Ökosystem

Nach ADR-027 + ADR-028 existieren drei Konventionen in `platform/packages/`:

| Pattern | Beispiele |
| --- | --- |
| `{project}-{role}` | bfagent-core, bfagent-llm, cad-services |
| `django-{concern}` | django-logging, django-health (ADR-027) |
| `platform-{layer}` | platform-context (ADR-028) |

**Empfehlung:** Ein einheitliches Pattern festlegen (`platform-{concern}` empfohlen).

---

## 4. Compatibility Shim

### 🟡 T-01: Shim deckt nicht alle Public Imports ab

ADR-028 §6.4 definiert Re-Exports für 6 Module. Aber Consumer importieren auch:

- `from bfagent_core.exceptions import TenantNotFoundError`
- `from bfagent_core.handlers.tenant import TenantCreateHandler`
- `from bfagent_core.models import Tenant, CoreUser, Plan`
- `from bfagent_core.middleware import TenantPermissionMiddleware`

Diese fehlen im Shim → **Zero-Breaking-Changes (R-01) verletzt**.

**Empfehlung:** `grep -r "from bfagent_core" --include="*.py"` über alle 7 Repos ausführen. Alle gefundenen Imports im Shim abdecken.

### 🟡 T-02: Interne Cross-Imports nicht migriert

`audit.py` importiert `from bfagent_core.models import AuditEvent`. `middleware.py` importiert `from bfagent_core.context import ...`. `handlers/tenant.py` importiert `from bfagent_core.exceptions import ...`. Alle internen Imports müssen zu `platform_context.*` umgeschrieben werden.

---

## 5. Was gut ist

- ✅ **Problem korrekt erkannt:** `bfagent-core` als Name für ein Platform-Package ist semantisch falsch
- ✅ **SeparateDatabaseAndState als Ansatz:** Korrekte Wahl, um DB-Tabellen nicht physisch zu ändern
- ✅ **Compatibility Shim mit Deprecation-Timeline:** Professioneller Migrationspfad
- ✅ **`db_table` beibehalten:** Pragmatische Entscheidung, die ALTER TABLE vermeidet
- ✅ **ADR-027 Integration klar definiert:** Header-Vereinheitlichung und Middleware-Stack in §8
- ✅ **Rollout-Plan mit Pilotprojekten:** Schrittweise Migration, nicht Big-Bang
- ✅ **Gate-Prüfung vor v1.0.0:** `grep`-basierte Verifikation vor Shim-Entfernung
- ✅ **Anforderungen mit Quellen referenziert:** Traceability zu PLATFORM_ARCHITECTURE_MASTER

---

## 6. Zusammenfassung

| ID | Severity | Bereich | Finding |
| --- | --- | --- | --- |
| B-01 | 🔴 | Bestand | Nur ~30% des Package-Inhalts inventarisiert (2/10 Models, 0/3 Handlers, 0 Exceptions) |
| B-02 | 🔴 | DB-Migration | SeparateDatabaseAndState für 2 statt 10 Models spezifiziert |
| B-03 | 🔴 | Versioning | IST-Version 0.2.0 kollidiert mit geplantem Shim v0.2.0 |
| A-01 | 🔴 | Architektur | Infrastructure + Domain + Business Logic unter "Context" vermischt |
| A-02 | 🟡 | Architektur | Kollision mit geplantem `platform_core` aus Architecture Master |
| A-03 | 🟡 | Architektur | Handler-Pattern (Command/Result) nicht adressiert |
| G-01 | 🟡 | Governance | ADR-022 HEALTH_PATHS-Pflicht nicht in Middleware umgesetzt |
| G-02 | 🟡 | Governance | repo_checker-Tool muss aktualisiert werden |
| G-03 | 🟡 | Naming | Drei verschiedene Naming-Patterns im Ökosystem |
| T-01 | 🟡 | Shim | Fehlende Re-Exports für Exceptions, Handlers, Models, 3. Middleware |
| T-02 | 🟡 | Migration | Interne Cross-Imports nicht dokumentiert |
| T-03 | 🟢 | API | `clear_context` als neue Public API nicht im Changelog |
| T-04 | 🟢 | Integration | ADR-027 muss Header-Name auf X-Request-Id aktualisieren |

**Blocker (🔴): 4** | **Signifikant (🟡): 7** | **Minor (🟢): 2**

---

## 7. Empfehlung: Nächste Schritte

1. **Vollständige Inventarisierung** aller Module, Models, Handlers, Exceptions, Events in bfagent-core
2. **Architektur-Entscheidung:** `platform-core` (monolithisch, ehrlicher Name) oder Drei-Package-Split
3. **Vollständige SeparateDatabaseAndState-Migration** für alle 10 Models mit FK-Reihenfolge
4. **Import-Audit:** `grep -r "from bfagent_core" --include="*.py"` über alle Repos
5. **HEALTH_PATHS-Fix** in SubdomainTenantMiddleware einbauen (ADR-022 Compliance)
6. **Versions-Synchronisation:** pyproject.toml und __init__.py abgleichen
7. **Naming-Convention** für platform/packages/ einheitlich festlegen
