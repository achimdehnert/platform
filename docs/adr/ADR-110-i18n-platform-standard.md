---
status: accepted
date: 2026-03-08
decision-makers: [Achim Dehnert]
implementation_status: partial
implementation_evidence:
  - "6/9 UI-Hubs mit i18n: travel-beat, weltenhub, coach-hub, cad-hub, billing-hub, dev-hub"
  - "Fehlend: risk-hub, pptx-hub, trading-hub"
---

# ADR-110: Internationalisierung (i18n) als Plattform-Standard für alle UI-Hubs

- **Status:** Accepted (updated 2026-03-08 — REVIEW-ADR-109-110 BLOCKER fixes)
- **Datum:** 2026-03-08
- **Parallel zu:** ADR-109 (Multi-Tenancy Platform Standard)
- **Betrifft:** alle Django-Hub-Repos mit Frontend-UI
- **Review:** `docs/adr/reviews/REVIEW-ADR-109-110.md`

---

## Kontext

i18n ist in einzelnen Hubs bereits vorhanden, aber nicht plattformweit standardisiert.
Das führt zu inkonsistenter Sprachunterstützung und fehlenden Übersetzungen bei neuen Features.

**Referenz-Implementierung:** `docs/adr/inputs/Input ADR 109 110/`

## Entscheidung

Django i18n nach dem folgenden Plattform-Standard ist **Pflicht** für alle UI-Hubs.

### Pflicht-Stack

| Komponente | Standard |
|-----------|---------|
| Backend | Django `USE_I18N = True`, `USE_L10N = True`, `USE_TZ = True` |
| Sprachen | `de` (default) + `en` (Pflicht), weitere optional per Hub |
| Translation files | `locale/<lang>/LC_MESSAGES/django.po` + `.mo` (`.mo` in `.gitignore`!) |
| Template-Tags | `{% trans %}`, `{% blocktrans %}` — kein Hardcode-Text |
| URL-Prefix | `i18n_patterns()` + `prefix_default_language=False` (neue Hubs) |
| Tenant-Sprache | `Organization.language` → ASGI-safe via Cookie (kein `translation.activate()`) |
| Zahlen/Datum | `USE_TZ = True`, `USE_L10N = True` immer |
| Cookie-Name | `LANGUAGE_COOKIE_NAME = "iil_lang"` (Fix M-3: plattformweit einheitlich) |

### Settings-Standard

```python
# settings.py — Pflicht für alle UI-Hubs
# Referenz: docs/adr/inputs/Input ADR 109 110/settings_template.py
USE_I18N = True
USE_L10N = True
USE_TZ = True

LANGUAGE_CODE = "de"
LANGUAGES = [
    ("de", "Deutsch"),
    ("en", "English"),
]

LOCALE_PATHS = [BASE_DIR / "locale"]

# Fix M-3: Einheitlicher Cookie-Name — kein Konflikt bei mehreren Hubs auf *.domain.tld
LANGUAGE_COOKIE_NAME = "iil_lang"
LANGUAGE_COOKIE_AGE = 60 * 60 * 24 * 365  # 1 Jahr
LANGUAGE_COOKIE_SECURE = True  # prod-settings
```

### Fix B-4: MIDDLEWARE-Reihenfolge (kritisch)

```python
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    # ↓ Session MUSS vor Locale (liest Session-Sprachpräferenz)
    "django.contrib.sessions.middleware.SessionMiddleware",
    # ↓ Locale MUSS nach Session, VOR Tenancy
    "django.middleware.locale.LocaleMiddleware",
    # ↓ Tenancy nach Locale (setzt tenant_id + LANGUAGE_CODE)
    "django_tenancy.middleware.SubdomainTenantMiddleware",
    "django.middleware.common.CommonMiddleware",
    # ...
]
```

**Falsche Reihenfolge:** Tenant-Sprache wird nicht aktiviert, Session-Sprache überschreibt Tenant.

### Fix H-5: `gettext_lazy` vs `gettext`

```python
# Models, Forms — IMMER lazy (bei DB-Zugriff aufgelöst)
from django.utils.translation import gettext_lazy as _
class MyModel(models.Model):
    name = models.CharField(verbose_name=_("Name"), ...)

# Views, Services — eager (sofort aufgelöst, Request-Kontext vorhanden)
from django.utils.translation import gettext as _
def my_view(request):
    message = _("Gespeichert")
```

Verwechslung führt zu `lazy_string`-Objekten in JSON-Responses.

### URL-Routing

```python
# urls.py — Referenz: docs/adr/inputs/Input ADR 109 110/urls_template.py
urlpatterns = [
    path("i18n/", include("django.conf.urls.i18n")),  # set_language POST
    path("admin/", admin.site.urls),
    path("health/", include("django_tenancy.urls.health")),  # außerhalb i18n
    path("onboarding/", include("apps.onboarding.urls")),
] + i18n_patterns(
    path("", include("apps.core.urls")),
    # Fix M-4: prefix_default_language=False für neue Hubs
    # Für bestehende Hubs mit Traffic: 3-Stufen-Migration (s.u.)
    prefix_default_language=False,
)
```

### Fix M-4: `prefix_default_language` Breaking-Change-Strategie

Für **bestehende Hubs** mit gecachten URLs (Google, CDN):
1. `prefix_default_language=True` deployen → alle Sprachen bekommen `/de/`-Prefix
2. 301-Redirects von alten URLs auf neue mit `/de/`-Prefix
3. Nach Ablauf der Cache-TTL: `prefix_default_language=False` aktivieren

Für **neue Hubs**: direkt `False` verwenden.

### Template-Standard

```html
{% load i18n %}
<h1>{% trans "Dashboard" %}</h1>
{% blocktrans with name=user.name %}Hallo {{ name }}{% endblocktrans %}

<!-- Fix H-6: Language-Switcher (Pflicht im Base-Template) -->
{% include "i18n/language_switcher.html" %}
<!-- Referenz: docs/adr/inputs/Input ADR 109 110/language_switcher.html -->
```

### Fix B-5: Tenant-Language ASGI-safe (kein `translation.activate()`)

```python
# FALSCH (thread-local, ASGI-unsafe):
translation.activate(request.tenant.language)  # ← VERBOTEN

# KORREKT (aus middleware.py):
# Nur request.LANGUAGE_CODE setzen — LocaleMiddleware aktiviert die Sprache.
# Cookie setzen so dass LocaleMiddleware beim nächsten Request die Tenant-Sprache liest.
request.LANGUAGE_CODE = tenant.language
request._tenant_language = tenant.language  # → Cookie in process_response

# In Views bei Bedarf:
with translation.override(tenant.language):
    return render(request, "template.html", context)
```

`translation.activate()` setzt thread-local State — in ASGI (Django 5.x async views, Daphne)
führt das zu Race Conditions zwischen parallelen Requests.

### Rollout-Reihenfolge (parallel zu ADR-109)

| Prio | Repo | Sprachen | Besonderheit |
|------|------|---------|-------------|
| ✅ | `coach-hub` | de, en | Vollständigkeit prüfen |
| ✅ | `risk-hub` | de, en | Vollständigkeit prüfen |
| ✅ | `research-hub` | de, en | Vollständigkeit prüfen |
| 1 | `weltenhub` | de, en | Creative content → ggf. mehr Sprachen |
| 2 | `pptx-hub` | de, en | UI-Strings prioritär |
| 3 | `trading-hub` | de, en | Zahlenformat wichtig |
| 4 | `cad-hub` | de, en | Technische Begriffe |
| 5 | `wedding-hub` | de, en, fr? | Emotionaler Content |
| 6 | `137-hub` | de, en | |
| 7 | `illustration-hub` | de, en | |
| – | `dev-hub` | de | Intern, en optional |

### Migration-Checkliste je Repo

- [ ] `settings.py`: `USE_I18N`, `LANGUAGES`, `LOCALE_PATHS`, `LocaleMiddleware` (B-4 Reihenfolge!)
- [ ] `settings.py`: `LANGUAGE_COOKIE_NAME = "iil_lang"` (M-3)
- [ ] `urls.py`: `i18n_patterns()` + `i18n/` URL + `prefix_default_language` Strategie (M-4)
- [ ] `locale/de/LC_MESSAGES/` + `locale/en/LC_MESSAGES/` anlegen
- [ ] `.gitignore`: `*.mo` eintragen (Binärdateien — nicht committen)
- [ ] `python manage.py makemessages -l de -l en --ignore=venv --ignore=node_modules`
- [ ] Templates: Hardcode-Strings mit `{% trans %}` wrappen
- [ ] Models/Forms: `gettext_lazy as _` (H-5)
- [ ] Views/Services: `gettext as _` (H-5)
- [ ] Language-Switcher ins Base-Template (H-6)
- [ ] `Organization.language` Feld + ASGI-safe Middleware (B-5, wenn ADR-109 implementiert)
- [ ] `compilemessages --locale=de --locale=en` in Dockerfile (H-7)
- [ ] CI: `makemessages` mit `--ignore` Flags + `git diff --exit-code "*.po"` (B-2, B-6)
- [ ] Tests: `@override_settings(LANGUAGE_CODE="en")` für kritische Views

### Fix B-2 + B-6: CI/CD-Integration

```yaml
# .github/workflows/ci.yml
# Referenz: docs/adr/inputs/Input ADR 109 110/ci_template.yml
- name: "Check translations"
  run: |
    set -euo pipefail
    python manage.py makemessages \
      --locale=de --locale=en --no-location \
      --ignore=venv --ignore=node_modules --ignore=staticfiles
    # Fix B-6: Nur .po Dateien prüfen (NICHT .mo Binärdateien)
    git diff --exit-code "*.po"
```

### Fix H-7: Dockerfile

```dockerfile
# Fix H-7: Nur definierte Locales kompilieren (nicht alle System-Locales)
# Fix B-2: set -euo pipefail
RUN set -euo pipefail && \
    python manage.py compilemessages --locale=de --locale=en
```

## Konsequenzen

**Positiv:**
- Plattformweite Mehrsprachigkeit ohne Mehraufwand bei neuen Features
- Tenant-Sprache via Cookie — ASGI-safe, kein Thread-State
- Einheitlicher Cookie-Name verhindert Cross-Hub-Konflikte
- `makemessages` in CI verhindert vergessene Übersetzungen

**Negativ / Aufwand:**
- Initiales Wrapping aller Template-Strings (~2–4h pro Hub)
- `.po`-Dateien müssen gepflegt werden
- `compilemessages` verlängert Docker-Build minimal (~5s)

## Abgrenzung

- **Übersetzungsinhalt** (User-generated content) ist nicht Scope dieses ADR
- **RTL-Sprachen** erfordern separates ADR (Frontend-Anpassungen)
- **Automatische Übersetzung via LLM** ist Scope ADR-11x (zukünftig)

---
*ADR-110 | Platform Architecture | 2026-03-08 | Updated after REVIEW-ADR-109-110*
