# ADR-134: Modul-Konfiguration und Monetarisierungsstrategie als shared Package

> **Umnummeriert von ADR-099** (Nummernkonflikt mit ADR-099-devhub-release-management-ui)

| Metadata | Value |
|----------|-------|
| **Status** | Proposed |
| **Date** | 2026-03-04 |
| **Author** | Achim Dehnert |
| **Reviewers** | — |
| **Supersedes** | — |
| **Scope** | platform, risk-hub, cad-hub, weltenhub, nl2cad, drift-tales |
| **Related** | ADR-035 (Shared Django Tenancy), ADR-022 (Platform Consistency), ADR-050 (Hub Landscape) |

---

## 1. Context

Mehrere Repos der BF-Agent-Plattform (risk-hub, cad-hub, nl2cad, weltenhub, drift-tales) realisieren
Module, die:

1. **konfigurierbar** sein müssen (welche Module sind für einen Tenant aktiviert?),
2. **zugangskontrolliert** sind (welcher Nutzer darf ein Modul mit welcher Rolle nutzen?),
3. **monetarisierbar** sind (free / trial / pro / enterprise — mit Ablaufdaten und Lifecycle).

Bislang wird dies in jedem Repo **einzeln und inkonsistent** realisiert. In risk-hub existiert bereits
eine ausgereifte Implementierung als Teil von `django-tenancy` (ADR-035):

- `ModuleSubscription` — welche Module ein Tenant lizenziert hat (`plan_code`, Status-Lifecycle, Ablaufdaten)
- `ModuleMembership` — welcher User Zugang zu einem Modul hat (mit Modul-spezifischer Rolle)
- `ModuleAccessMiddleware` — automatische URL-Prefix-basierte Zugangskontrolle
- `@require_module()` — feingranularer View-Decorator

In cad-hub existiert eine ältere Kopie via `vendor/django_tenancy/` ohne vollständige
`module_access.py`. In weltenhub, drift-tales und nl2cad ist die Funktionalität noch nicht
vorhanden oder abweichend implementiert.

### Aktueller Stand

| Komponente | risk-hub | cad-hub | weltenhub | nl2cad | drift-tales |
|------------|----------|---------|-----------|--------|-------------|
| `ModuleSubscription` | ✅ `django-tenancy` | ⚠️ vendor-Kopie | ❌ | ❌ | ❌ |
| `ModuleMembership` | ✅ `django-tenancy` | ⚠️ vendor-Kopie | ❌ | ❌ | ❌ |
| `ModuleAccessMiddleware` | ✅ vollständig | ⚠️ unvollständig | ❌ | ❌ | ❌ |
| `@require_module()` | ✅ | ⚠️ | ❌ | ❌ | ❌ |
| `plan_code`-Monetarisierung | ✅ | ⚠️ | ❌ | ❌ | ❌ |

**Probleme:**

- **Drift**: Jedes Repo entwickelt die Monetarisierungslogik eigenständig
- **Inkonsistenz**: Kein einheitlicher `plan_code`-Standard, keine gemeinsamen Status-Regeln
- **Doppelaufwand**: Neue Repos (nl2cad, drift-tales) müssen dasselbe von Grund auf bauen
- **Keine Single Source of Truth**: Bug-Fixes und neue Features müssen manuell repliziert werden

---

## 2. Decision

Die Modul-Konfiguration und Monetarisierungsinfrastruktur wird als Teil des
`django-tenancy`-Packages in `platform/packages/django-tenancy/` konsolidiert und versioniert
bereitgestellt. Dies erweitert ADR-035 um die monetarisierungs- und modulspezifischen Komponenten.

### 2.1 Scope des Packages (Erweiterung von ADR-035)

Das bestehende `django-tenancy`-Package wird um folgende Komponenten ergänzt bzw. diese werden
dorthin migriert:

```text
platform/packages/django-tenancy/
└── django_tenancy/
    ├── module_models.py        # ModuleSubscription, ModuleMembership
    ├── module_access.py        # ModuleAccessMiddleware, @require_module()
    └── migrations/
        └── 0002_module_models.py
```

### 2.2 Datenmodell

#### `ModuleSubscription`

| Feld | Typ | Bedeutung |
|------|-----|-----------|
| `organization` | FK | Besitzender Tenant |
| `tenant_id` | UUIDField | Denormalisiert für schnelle Filterung |
| `module` | CharField | Modul-Code (`"risk"`, `"dsb"`, `"worlds"`) — kein FK, Apps definieren eigene Codes |
| `status` | choices | `trial` → `active` → `suspended` |
| `plan_code` | CharField | Billing-Plan (`"free"`, `"pro"`, `"enterprise"`) |
| `trial_ends_at` | DateTimeField | Ende der Testphase |
| `activated_at` | DateTimeField | Aktivierungszeitpunkt |
| `expires_at` | DateTimeField | Hartes Ablaufdatum |

#### `ModuleMembership`

| Feld | Typ | Bedeutung |
|------|-----|-----------|
| `tenant_id` | UUIDField | Denormalisiert |
| `user` | FK | `settings.AUTH_USER_MODEL` |
| `module` | CharField | Modul-Code |
| `role` | choices | `viewer` < `member` < `manager` < `admin` |
| `granted_by` | FK (nullable) | Audit-Trail |
| `expires_at` | DateTimeField | Optionales Ablaufdatum |

### 2.3 Zugangskontrolle

```python
# settings.py — coarse URL-prefix guard
MODULE_URL_MAP = {
    "/risk/":       "risk",
    "/dsb/":        "dsb",
    "/worlds/":     "worlds",
    "/api/cad/":    "cad",
}

MIDDLEWARE = [
    "django_tenancy.middleware.SubdomainTenantMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_tenancy.module_access.ModuleAccessMiddleware",  # coarse
]

# views.py — fine-grained role check
from django_tenancy.module_access import require_module

@login_required
@require_module("dsb", min_role="manager")
def mandate_delete(request, pk):
    ...
```

### 2.4 Monetarisierungsstrategie

Der `plan_code` ist ein freies CharField — jedes Repo definiert seine eigenen Plan-Codes.
Die Enforcement-Logik (z.B. Feature-Limits je Plan) liegt in der jeweiligen App-Schicht,
**nicht** im Package. Das Package stellt nur sicher, dass der Zugang auf Subscription-Ebene
kontrolliert wird.

**Empfohlene Standard-Plan-Codes** (plattformweit, nicht erzwungen):

| Code | Bedeutung |
|------|-----------|
| `free` | Kostenloser Zugang, ggf. mit Limits |
| `trial` | Zeitlich begrenzte Testversion (via `trial_ends_at`) |
| `pro` | Bezahltes Einzelprodukt |
| `enterprise` | Volllizenz mit SLA |

### 2.5 Verteilungsstrategie (Git-Dependency → Private PyPI)

**Phase 1 (sofort):** Alle Repos installieren das Package direkt aus dem `platform`-Repo:

```
django-tenancy @ git+https://github.com/achimdehnert/platform.git#subdirectory=packages/django-tenancy@<commit-hash>
```

**Phase 2 (ab v1.0):** Migration auf Private-PyPI-Registry (GitHub Packages / GHCR).

Pinning auf Commit-Hash ist Pflicht — kein implizites `@main`.

### 2.6 Migrationspfad

| Phase | Repo | Aktion | Risiko |
|-------|------|--------|--------|
| 1 | **platform** | `module_models.py` + `module_access.py` aus risk-hub nach `platform/packages/django-tenancy/` übertragen, Tests ergänzen | Keines |
| 2 | **risk-hub** | Lokales `packages/django-tenancy/` entfernen, auf Git-Dependency umstellen | Niedrig — gleicher Code, gleiche `db_table` |
| 3 | **cad-hub** | `vendor/django_tenancy/` entfernen, auf Git-Dependency umstellen | Niedrig |
| 4 | **weltenhub** | Package installieren, Module anlegen | Keines (Greenfield) |
| 5 | **nl2cad** | Package installieren, Module anlegen | Keines (Greenfield) |
| 6 | **drift-tales** | Package installieren, Module anlegen | Keines (Greenfield) |

---

## 3. Implementation

### 3.1 Neue Repos (nl2cad, drift-tales, weltenhub)

```python
# settings.py
INSTALLED_APPS = [
    ...
    "django_tenancy",
]

MIDDLEWARE = [
    ...
    "django_tenancy.middleware.SubdomainTenantMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_tenancy.module_access.ModuleAccessMiddleware",
]

MODULE_URL_MAP = {
    "/worlds/": "worlds",   # Beispiel weltenhub
}
```

```bash
python manage.py migrate  # erstellt tenancy_module_subscription + tenancy_module_membership
```

### 3.2 Bestehende Repos (risk-hub, cad-hub)

```bash
# 1. platform-Package als Dependency eintragen (mit Commit-Hash pinnen)
pip install "django-tenancy @ git+https://github.com/achimdehnert/platform.git@<hash>#subdirectory=packages/django-tenancy"

# 2. Lokale Kopie / vendor/ entfernen
# 3. Imports: from django_tenancy.module_models import ModuleSubscription  (unverändert)
# 4. Migrations prüfen — db_table identisch, kein Schema-Change erforderlich
```

---

## 4. Consequences

### 4.1 Positive

- **Single Source of Truth**: Eine Implementierung für alle Repos, Bug-Fixes propagieren automatisch
- **Einheitliche Monetarisierung**: Konsistentes `plan_code`-Schema plattformweit
- **Onboarding**: Neue Apps brauchen nur `INSTALLED_APPS` + `pip install` + `migrate`
- **Keine Breaking Changes**: `db_table` bleibt `tenancy_module_subscription` / `tenancy_module_membership` — keine Datenmigration nötig bei Migration von risk-hub

### 4.2 Negative

- **Externe Dependency**: Alle Repos hängen am `platform`-Repo für dieses Package
- **Versionierung nötig**: Breaking Changes am Package müssen koordiniert deployt werden
- **platform-Repo Pflege**: Das `platform`-Repo muss aktiv gepflegt werden (CI, Tests)

### 4.3 Mitigation

- **Semantic Versioning** ab v1.0 im `pyproject.toml`
- **CHANGELOG** für das Package führen
- **Pinning**: Repos pinnen auf Commit-Hash oder Tag, kein implizites `@main`
- **Deprecation Policy**: Breaking Changes werden eine Minor-Version vorher angekündigt (Zero Breaking Changes — ADR-022)

---

## 5. Changelog

| Date | Author | Change |
|------|--------|--------|
| 2026-03-04 | Achim Dehnert | Initial draft — aus risk-hub ADR-040 in platform überführt |
