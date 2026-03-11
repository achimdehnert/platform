# REVIEW: ADR-109 (Multi-Tenancy) + ADR-110 (i18n) Platform Standard

**Reviewer:** Cascade Agent (platform-context MCP)
**Datum:** 2026-03-08
**Basis:** ADR-109, ADR-110, Input-Files `docs/adr/inputs/Input ADR 109 110/`
**Amends:** ADR-035 (shared-django-tenancy), ADR-022 (platform-consistency)

---

## Übersicht

Die Inputs liefern eine vollständige Referenz-Implementierung für ADR-109 + ADR-110.
Der Review identifiziert Lücken zwischen den ADR-Texten und den konkreten Implementierungen
in den Input-Files.

### Bewertungsmatrix

| Severity | Anzahl | Aktion |
|----------|--------|--------|
| **BLOCKER** | 5 | Muss vor erstem Hub-Rollout behoben sein |
| **HIGH** | 7 | Muss in ADR-Update + Issue |
| **MEDIUM** | 4 | Soll in nächstem Sprint |
| **LOW** | 3 | Nice-to-have |

---

## BLOCKER Findings

### B-1: `tenant_id` Feldtyp widersprüchlich in ADR-109

**ADR-109 schreibt:** `tenant_id = FK auf Organization`
**Input `models_django_tenancy.py` korrigiert:** `tenant_id = BigIntegerField` (kein FK)

**Begründung aus ADR-035 §2.2:**
> `tenant_id = UUIDField(db_index=True)` — Global Rules mandate this; `Organization.id != Organization.tenant_id`

**Input-Models schreiben BigIntegerField** (konsistent mit BigAutoField PK auf Organization).
FK würde ON DELETE CASCADE oder RESTRICT erzwingen und Celery/Cross-DB-Szenarien brechen.

**Fix:** ADR-109 Pflicht-Komponenten-Abschnitt muss auf `BigIntegerField` korrigiert werden.
**Korrekter Code** (aus `models_django_tenancy.py` Z. 206):
```python
tenant_id = models.BigIntegerField(db_index=True, verbose_name=_("Tenant ID"))
```

---

### B-2: Shell-Steps in CI ohne `set -euo pipefail`

**ADR-110 CI-Snippet** fehlt `set -euo pipefail` in jedem `run:`-Block.
**Input `ci_template.yml`** (Z. 61, 68, 80) hat es korrekt.

**Risiko:** Ein fehlgeschlagenes `makemessages` bricht den Build nicht ab — neue unübersetzte Strings landen unbemerkt in Prod.

**Fix:** ADR-110 CI-Snippet aktualisieren. Pflicht laut ADR-022 §Shell-Safety.

---

### B-3: Middleware ohne Fallback für unbekannte Subdomain → 500

**ADR-109** beschreibt nur den Happy Path (Subdomain gefunden).
**Input `middleware.py`** (Z. 151–155) zeigt den Fix:
```python
except TenantNotFound as e:
    logger.info("Tenant not found: %s — redirecting to onboarding", e)
    return HttpResponseRedirect(settings.TENANCY_FALLBACK_URL)
```

**Ohne Fallback** gibt jede ungültige Subdomain einen 500-Fehler in Prod.

**Fix:** ADR-109 Middleware-Spezifikation um Fallback + `TENANCY_FALLBACK_URL` ergänzen.

---

### B-4: `LocaleMiddleware` Reihenfolge nicht spezifiziert in ADR-110

**ADR-110 settings-Snippet** zeigt `LocaleMiddleware` ohne Reihenfolge-Kommentar.
**Kritisch:** `LocaleMiddleware` **muss** nach `SessionMiddleware` und **vor** `SubdomainTenantMiddleware`.

Falsche Reihenfolge → Tenant-Sprache wird nicht aktiviert, Session-Sprache überschreibt Tenant.

**Korrekte Reihenfolge** (aus `settings_template.py` Z. 83–96):
```
SessionMiddleware          ← 1 (Pflicht: vor Locale)
LocaleMiddleware           ← 2 (liest Session-Sprachpräferenz)
SubdomainTenantMiddleware  ← 3 (überschreibt mit Tenant-Sprache)
CommonMiddleware           ← 4
```

**Fix:** ADR-110 Middleware-Abschnitt mit expliziter Reihenfolge + Kommentaren.

---

### B-5: `translation.activate()` ASGI-Thread-unsafe in ADR-110 Tenant-Integration

**ADR-110** schreibt (Z. 107–108):
```python
translation.activate(request.tenant.language)
request.LANGUAGE_CODE = request.tenant.language
```

`translation.activate()` setzt **thread-local state** — in ASGI (Django 5.x async views, Daphne) führt das zu Race Conditions zwischen parallelen Requests.

**Korrekter Fix** (aus `middleware.py` Z. 160–172):
```python
# NUR request.LANGUAGE_CODE setzen — KEIN translation.activate()
request.LANGUAGE_CODE = tenant.language
request._tenant_language = tenant.language  # Cookie wird in process_response gesetzt
# In Views bei Bedarf: with translation.override(lang): ...
```

**Fix:** ADR-110 Tenant-Integration Snippet komplett ersetzen.

---

## HIGH Findings

### H-1: Platform-Standard-Model-Felder fehlen in ADR-109

ADR-109 zeigt nur `tenant_id` FK. `models_django_tenancy.py` zeigt den vollständigen Platform-Standard:
- `id = BigAutoField` (Platform-Pflicht)
- `public_id = UUIDField` (Platform-Pflicht)
- `deleted_at = DateTimeField` (Soft-Delete)
- `TenantManager` mit `for_tenant()` + `active()` QuerySet-Methoden

ADR-109 muss `TenantModel` Abstract Base Class referenzieren.

### H-2: `TenantTestMixin` in `iil-testkit` ist undefiniert

ADR-109 Checkliste nennt `TenantTestMixin` (Z. 65), aber die Klasse existiert noch nicht in `iil-testkit`.
Input `tenant_mixins.py` liefert die vollständige Implementierung mit:
- `create_tenant()`, `set_tenant()`, `make_tenant_request()`
- `assert_tenant_isolated()`, `assert_tenant_visible()`

**Action:** Issue anlegen — `TenantTestMixin` in `iil-testkit` implementieren.

### H-3: `TenancyMode` Strategy fehlt in ADR-109

ADR-109 geht von fest verkabeltem Subdomain-Routing aus.
Input `middleware.py` zeigt `TenancyMode` Enum (Z. 32–45):
- `SUBDOMAIN` = Prod
- `SESSION` = Dev (default in CI)
- `HEADER` = API/CI
- `DISABLED` = billing-hub, dev-hub

Ohne `SESSION`-Mode können Entwickler lokal nicht ohne Subdomain testen.
**Fix:** ADR-109 um `TENANCY_MODE` Setting + Enum erweitern.

### H-4: Migration-Template für bestehende Prod-Daten fehlt

ADR-109 Checkliste (Z. 61) nennt nur `makemigrations`. Für bestehende Hubs mit Prod-Daten
ist ein `SeparateDatabaseAndState`-Pattern zwingend:

1. `ADD COLUMN tenant_id NULL`
2. `RunPython`: bestehende Rows → Default-Tenant
3. `ALTER COLUMN SET NOT NULL` (via `RunSQL`)

Input `0002_add_tenant_id.py` enthält das vollständige idempotente Template.
**Fix:** ADR-109 um Migration-Template-Referenz + Rollback-Anweisung ergänzen.

### H-5: `gettext_lazy` vs `gettext` Unterschied nicht dokumentiert

ADR-110 erwähnt `{% trans %}` in Templates, aber nicht die kritische Python-Seite:
- `gettext_lazy as _` → **Models, Forms** (lazy = bei DB-Zugriff aufgelöst)
- `gettext as _` → **Views, Services** (eager = sofort aufgelöst)

Verwechslung führt zu `translation.lazy_string` Objekten in JSON-Responses.
Input `HUB-ROLLOUT-CHECKLIST.md` Z. 65–66 hat die korrekte Unterscheidung.

### H-6: Language-Switcher Template nicht spezifiziert

ADR-110 nennt `{% include "i18n/language_switcher.html" %}` ohne den Template-Inhalt.
Input `language_switcher.html` liefert die Referenz-Implementierung mit:
- `{% get_current_language %}` + `{% get_available_languages %}`
- CSRF-Token im `set_language` POST
- `next` Hidden-Field (gleiche Seite nach Sprachwechsel)
- ARIA-Labels (Accessibility)

### H-7: `compilemessages` ohne `--locale` Flags kompiliert System-Locales

ADR-110 Dockerfile-Snippet: `RUN python manage.py compilemessages`
Ohne `--locale` Flags versucht Django **alle** System-Locales zu kompilieren → Build-Fehler auf
minimalen Images ohne vollständige locale-Daten.

Input `Dockerfile` Z. 60:
```dockerfile
RUN python manage.py compilemessages --locale=de --locale=en
```

---

## MEDIUM Findings

### M-1: `unique_together` statt `UniqueConstraint` in ADR-109

ADR-109 zeigt keine Constraints. `models_django_tenancy.py` Z. 110–125 zeigt:
```python
models.UniqueConstraint(
    fields=["slug"],
    condition=models.Q(deleted_at__isnull=True),
    name="unique_active_org_slug",
)
```
`unique_together` ist deprecated seit Django 4.x. Platform-Standard ist `UniqueConstraint`.

### M-2: `.mo` Dateien in `.gitignore` nicht erwähnt

ADR-110 empfiehlt `compilemessages` im Dockerfile, aber vergisst zu sagen:
`.mo` Dateien (Binär) **nicht committen** — sie werden bei Docker-Build generiert.
`HUB-ROLLOUT-CHECKLIST.md` Z. 60 hat den korrekten `.gitignore`-Eintrag.

### M-3: `LANGUAGE_COOKIE_NAME` plattformweit nicht standardisiert

ADR-110 nutzt Django-Default `django_language`. Bei mehreren Hubs auf derselben Domain
(`*.domain.tld`) überschreiben sie sich gegenseitig.

Input `settings_template.py` Z. 56:
```python
LANGUAGE_COOKIE_NAME = "iil_lang"  # Plattformweit einheitlich
```

### M-4: `prefix_default_language=False` Breaking-Change-Risiko nicht dokumentiert

ADR-110 empfiehlt direkt `prefix_default_language=False`. Bei bestehenden Hubs mit
gecachten URLs (Google, CDN) ist das ein Breaking Change.

Input `urls_template.py` Z. 8–13 dokumentiert die 3-stufige Migrations-Strategie:
1. `True` deployen (alle Sprachen bekommen `/de/` Prefix)
2. 301-Redirects von alten URLs
3. Nach Cache-TTL: `False` aktivieren

---

## LOW Findings

### L-1: `django_tenancy.context_processors.tenant` fehlt in ADR-109

ADR-109 nennt den `org_switcher.html` Include, aber `request.tenant` ist im Template
nur verfügbar wenn `django_tenancy.context_processors.tenant` in `TEMPLATES['context_processors']`.

### L-2: Wildcard-DNS Test-Befehl fehlt

ADR-109 Checkliste (Z. 66) nennt DNS-Eintrag aber keinen Validierungsbefehl.
`HUB-ROLLOUT-CHECKLIST.md` Z. 99:
```bash
curl -H "Host: test-tenant.hub-name.domain.tld" https://hub-name.domain.tld/health/
```

### L-3: `billing-hub` Ausnahme-Architektur nicht beschrieben

ADR-109 sagt "separates ADR nötig" für billing-hub. Interim-Lösung via
`TENANCY_MODE=disabled` + `TENANT_ISOLATION_MODE=disabled` ist implementierbar
ohne eigenes ADR — sollte dokumentiert werden.

---

## Konformität mit bestehenden ADRs

| ADR | Konformität | Anmerkung |
|-----|-------------|-----------|
| ADR-022 (Platform Consistency) | ⚠️ Teilweise | B-2 (Shell-Safety) verletzt |
| ADR-035 (django-tenancy) | ⚠️ Teilweise | B-1 (FK vs BigIntegerField) widerspricht §2.2 |
| ADR-048 (HTMX Playbook) | ✅ | Language-Switcher als Form POST kompatibel |
| ADR-057 (Test Strategy) | ⚠️ Teilweise | H-2 (TenantTestMixin fehlt in iil-testkit) |
| ADR-058 (Test Taxonomy) | ✅ | TenantTestMixin Mixin-Pattern konform |
| ADR-107 (Deployment Agent) | ✅ | `compilemessages` in Dockerfile, Health-Path exempt |
| ADR-108 (QA Cycle) | ✅ | Checklist entspricht QA-Gate-Anforderungen |

---

## Notwendige ADR-Updates

### ADR-109 muss aktualisiert werden:

1. **Pflicht-Komponenten**: `BigIntegerField` statt FK, `TenantModel` Abstract Base
2. **`TenancyMode` Enum**: `SUBDOMAIN / SESSION / HEADER / DISABLED`
3. **Middleware-Fallback**: `TENANCY_FALLBACK_URL` + TenantNotFound → Redirect
4. **Migration-Template**: Referenz auf `0002_add_tenant_id.py` Pattern
5. **Context Processor**: `django_tenancy.context_processors.tenant` in TEMPLATES

### ADR-110 muss aktualisiert werden:

1. **Middleware-Reihenfolge**: Session → Locale → Tenancy explizit
2. **Tenant-Language Fix**: Kein `translation.activate()` → nur `request.LANGUAGE_CODE`
3. **`gettext_lazy` vs `gettext`**: Dokumentation der Unterscheidung
4. **`--locale` Flags**: `compilemessages` und `makemessages` immer mit expliziten Locales
5. **`LANGUAGE_COOKIE_NAME = "iil_lang"`**: Plattformweiter Standard
6. **`prefix_default_language` Migration**: 3-Stufen-Strategie für bestehende Hubs

---

## GitHub Issues (anzulegen)

| ID | Titel | Severity | Repo |
|----|-------|----------|------|
| ISS-1 | `TenantTestMixin` in `iil-testkit` implementieren | HIGH | testkit |
| ISS-2 | ADR-109: tenant_id BigIntegerField (kein FK) korrigieren | BLOCKER | platform |
| ISS-3 | ADR-110: ASGI-safe Tenant-Language (kein translation.activate) | BLOCKER | platform |
| ISS-4 | ADR-110: Middleware-Reihenfolge Session→Locale→Tenancy | BLOCKER | platform |
| ISS-5 | django_tenancy Package in platform/packages/ anlegen | HIGH | platform |
| ISS-6 | weltenhub: ADR-109+110 Rollout (Phase 1) | HIGH | weltenhub |
| ISS-7 | pptx-hub: ADR-109+110 Rollout (Phase 2) | HIGH | pptx-hub |

---

## Implementierungs-Referenz

Die Input-Files unter `docs/adr/inputs/Input ADR 109 110/` sind **produktionsreife Templates**:

| File | Verwendung |
|------|-----------|
| `models_django_tenancy.py` | → `platform/packages/django-tenancy/django_tenancy/models.py` |
| `middleware.py` | → `platform/packages/django-tenancy/django_tenancy/middleware.py` |
| `tenant_mixins.py` | → `testkit/iil_testkit/tenant_mixins.py` |
| `settings_template.py` | → Jedes Hub-Repo: `config/settings/base.py` |
| `0002_add_tenant_id.py` | → Jedes Hub-Repo: Migration-Template |
| `ci_template.yml` | → Jedes Hub-Repo: `.github/workflows/ci.yml` |
| `Dockerfile` | → Jedes Hub-Repo: `Dockerfile` |
| `language_switcher.html` | → `platform/packages/django-tenancy/templates/i18n/language_switcher.html` |
| `urls_template.py` | → Jedes Hub-Repo: `config/urls.py` |
| `HUB-ROLLOUT-CHECKLIST.md` | → Pflicht-Checkliste für jeden Hub-Rollout |

---
*REVIEW-ADR-109-110 | 2026-03-08 | Cascade Agent*
