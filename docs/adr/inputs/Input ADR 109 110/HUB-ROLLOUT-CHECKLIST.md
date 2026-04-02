# Hub Rollout Checklist — ADR-109 + ADR-110
**Version:** 2.0 (post-review)
**Gilt für:** weltenhub, pptx-hub, trading-hub, cad-hub, wedding-hub, 137-hub, illustration-hub

---

## Vor dem Rollout: Einmalige Voraussetzungen

- [ ] `django_tenancy` >= 1.x installiert und in `INSTALLED_APPS`
- [ ] Default-Tenant in Prod-DB angelegt:
  ```bash
  set -euo pipefail
  python manage.py create_default_tenant --name="Default" --slug="default" --id=1
  ```
- [ ] DB-Snapshot/Backup erstellt (Pflicht vor Migration auf Prod)
- [ ] `TENANCY_MODE=subdomain` in Prod-Environment-Variables gesetzt
- [ ] Cloudflare Wildcard-DNS `*.hub.domain.tld` → Server (bereits vorhanden laut ADR)

---

## Phase 1 — Settings (ADR-109 + ADR-110, ~30 min)

- [ ] `settings/base.py` aktualisieren:
  - [ ] `USE_I18N = True`, `USE_L10N = True`, `USE_TZ = True`
  - [ ] `LANGUAGES = [("de", "Deutsch"), ("en", "English")]`
  - [ ] `LOCALE_PATHS = [BASE_DIR / "locale"]`
  - [ ] `LANGUAGE_COOKIE_NAME = "iil_lang"` (**nicht** Django-Default `django_language`)
  - [ ] `TENANCY_MODE = os.environ.get("TENANCY_MODE", "session")`
  - [ ] `TENANCY_FALLBACK_URL = "/onboarding/"`
  - [ ] MIDDLEWARE-Reihenfolge prüfen:
    ```
    SessionMiddleware       ← vor LocaleMiddleware
    LocaleMiddleware        ← nach Session, vor Tenancy
    SubdomainTenantMiddleware ← nach Locale
    ```
  - [ ] `"django.template.context_processors.i18n"` in TEMPLATES context_processors

## Phase 2 — Models (ADR-109, ~1h)

- [ ] Alle User-Data-Models erben von `TenantModel` ODER:
  - [ ] `tenant_id = models.BigIntegerField(db_index=True)` hinzufügen (**kein FK**)
  - [ ] `public_id = models.UUIDField(...)` sicherstellen
  - [ ] `deleted_at = models.DateTimeField(null=True, blank=True)` sicherstellen
- [ ] `TenantManager` auf allen relevanten Models
- [ ] `Organization.language` Feld hinzufügen (ADR-110 Tenant-Integration)

## Phase 3 — Migrations (ADR-109, ~30 min + Review)

- [ ] `0002_add_tenant_id.py` Template kopieren und anpassen
- [ ] `python manage.py makemigrations` lokal ausführen
- [ ] Migration-Review: Enthält `SeparateDatabaseAndState`? Enthält `RunPython` mit `reverse_func`?
- [ ] Lokalen Test: `python manage.py migrate` auf leerer Test-DB
- [ ] Staging-Test: Migration auf Staging-DB mit Prod-Datenmenge
- [ ] **Erst dann**: Migration auf Prod (mit DB-Snapshot als Rollback)

## Phase 4 — i18n Template-Strings (ADR-110, ~2-4h)

- [ ] `locale/de/LC_MESSAGES/` Verzeichnis anlegen
- [ ] `locale/en/LC_MESSAGES/` Verzeichnis anlegen
- [ ] `.gitignore` aktualisieren: `*.mo` eintragen (Binärdateien, nicht committen)
- [ ] `python manage.py makemessages -l de -l en --ignore=venv --ignore=node_modules`
- [ ] Templates: alle Hardcode-Strings mit `{% trans %}` wrappen
  - [ ] `{% load i18n %}` am Anfang jedes Templates
  - [ ] Prüfen: `grep -rn '>' templates/ | grep -v '{%' | grep -v '{{' | head -20`
- [ ] Models/Forms: `from django.utils.translation import gettext_lazy as _`
- [ ] Views/Services: `from django.utils.translation import gettext as _`
- [ ] `python manage.py makemessages` erneut ausführen → `.po` Dateien füllen
- [ ] `.po` Dateien übersetzen (DE + EN)
- [ ] `python manage.py compilemessages --locale=de --locale=en`

## Phase 5 — URL-Routing (ADR-110, ~30 min)

- [ ] `urls.py` auf `i18n_patterns()` umstellen
- [ ] `path("i18n/", include("django.conf.urls.i18n"))` hinzufügen
- [ ] Entscheidung: `prefix_default_language=True` (erst) oder `False` (direkt)?
  - Neuer Hub → `False` direkt
  - Bestehender Hub mit Traffic → erst `True` + 301-Redirects, dann `False`
- [ ] Language-Switcher ins Base-Template: `{% include "i18n/language_switcher.html" %}`
- [ ] Org-Switcher ins Base-Template: `{% include "tenancy/org_switcher.html" %}`

## Phase 6 — Tests (ADR-109, ~1h)

- [ ] `from iil_testkit.tenant_mixins import TenantTestMixin` in Test-Setup
- [ ] Für jeden View-Test: `self.set_tenant(self.client, tenant)` vor Request
- [ ] `self.assert_tenant_isolated(MyModel, obj_a, tenant_b)` für kritische Models
- [ ] `@override_settings(LANGUAGE_CODE="en")` für i18n View-Tests
- [ ] `python manage.py test` vollständig grün

## Phase 7 — CI/CD (ADR-110, ~30 min)

- [ ] `ci.yml` aktualisieren: `makemessages` mit `--ignore` Flags
- [ ] `ci.yml`: `git diff --exit-code "*.po"` (nicht `locale/` wegen `.mo`)
- [ ] `Dockerfile`: `compilemessages --locale=de --locale=en`
- [ ] Deployment Agent Trigger testen

## Phase 8 — Subdomain-DNS (ADR-109, ~15 min)

- [ ] Cloudflare: Wildcard `*.hub-name.domain.tld` → Server-IP
- [ ] Test: `curl -H "Host: test-tenant.hub-name.domain.tld" https://hub-name.domain.tld/health/`
- [ ] Ersten Tenant mit Subdomain anlegen und testen

---

## Rollback-Plan (Pflicht dokumentieren vor Prod-Migration)

```bash
set -euo pipefail
# 1. DB-Snapshot wiederherstellen (Hetzner Snapshot oder pg_restore)
# 2. Migration zurückrollen
python manage.py migrate core 0001  # Vorherige Migration
# 3. Settings zurücksetzen
git revert HEAD~1 --no-commit
# 4. Redeploy
```

---

## Definition of Done

- [ ] Alle Tests grün (inkl. Tenant-Isolation-Tests)
- [ ] `makemessages` in CI schlägt nicht an
- [ ] Language-Switcher funktioniert (DE ↔ EN)
- [ ] Org-Switcher funktioniert (falls mehrere Tenants)
- [ ] Tenant A sieht nicht die Daten von Tenant B (manueller Smoke-Test)
- [ ] ADR-109-Compliance in PR-Checklist vermerkt ✅
