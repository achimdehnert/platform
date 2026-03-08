# ADR-110: Internationalisierung (i18n) als Plattform-Standard für alle UI-Hubs

- **Status:** Accepted
- **Datum:** 2026-03-08
- **Parallel zu:** ADR-109 (Multi-Tenancy Platform Standard)
- **Betrifft:** alle Django-Hub-Repos mit Frontend-UI

---

## Kontext

Identisch zu Multi-Tenancy (ADR-109): i18n ist in einzelnen Hubs bereits vorhanden,
aber nicht plattformweit standardisiert. Das führt zu inkonsistenter Sprachunterstützung,
doppeltem Aufwand und fehlenden Übersetzungen bei neuen Features.

**Analogie zu ADR-109:** So wie jeder Hub Multi-Tenancy braucht, braucht jeder Hub
eine konsistente i18n-Infrastruktur — auch wenn initial nur `de` + `en` unterstützt werden.

## Entscheidung

Django i18n nach dem folgenden Plattform-Standard ist **Pflicht** für alle UI-Hubs.

### Pflicht-Stack

| Komponente | Standard |
|-----------|---------|
| Backend | Django `USE_I18N = True`, `USE_L10N = True` |
| Sprachen | `de` (default) + `en` (Pflicht), weitere optional |
| Translation files | `locale/<lang>/LC_MESSAGES/django.po` + `.mo` |
| Template-Tags | `{% trans %}`, `{% blocktrans %}` — kein Hardcode-Text |
| URL-Prefix | `i18n_patterns()` → `/de/`, `/en/` oder Session-based |
| Tenant-Sprache | `Organization.language` FK → User-Präferenz überschreibt Default |
| Zahlen/Datum | `USE_TZ = True`, `USE_L10N = True` immer |

### Settings-Standard

```python
# settings.py — Pflicht für alle UI-Hubs
USE_I18N = True
USE_L10N = True
USE_TZ = True

LANGUAGE_CODE = "de"
LANGUAGES = [
    ("de", "Deutsch"),
    ("en", "English"),
]

LOCALE_PATHS = [BASE_DIR / "locale"]

MIDDLEWARE = [
    # ... vor SessionMiddleware
    "django.middleware.locale.LocaleMiddleware",
    # ...
]
```

### URL-Routing

```python
# urls.py
from django.conf.urls.i18n import i18n_patterns
from django.urls import include, path

urlpatterns = [
    path("i18n/", include("django.conf.urls.i18n")),  # set_language view
] + i18n_patterns(
    path("", include("apps.core.urls")),
    # alle App-URLs hier
    prefix_default_language=False,  # /de/ weglassen für default
)
```

### Template-Standard

```html
{% load i18n %}

<!-- Einzelner String -->
<h1>{% trans "Dashboard" %}</h1>

<!-- Mit Variable -->
{% blocktrans with name=user.name %}Hallo {{ name }}{% endblocktrans %}

<!-- Language Switcher (Pflicht im Base-Template) -->
{% include "i18n/language_switcher.html" %}
```

### Tenant-Integration (mit ADR-109)

```python
# Organization-Model Erweiterung
class Organization(models.Model):
    # ... existing fields
    language = models.CharField(
        max_length=8,
        choices=settings.LANGUAGES,
        default="de",
    )
```

```python
# SubdomainTenantMiddleware Erweiterung
def process_request(self, request):
    # ... tenant_id setzen
    if hasattr(request, "tenant") and request.tenant.language:
        translation.activate(request.tenant.language)
        request.LANGUAGE_CODE = request.tenant.language
```

### Rollout-Reihenfolge (parallel zu ADR-109)

| Prio | Repo | Sprachen | Besonderheit |
|------|------|---------|-------------|
| ✅ | `coach-hub` | de, en | Prüfen ob vollständig |
| ✅ | `risk-hub` | de, en | Prüfen ob vollständig |
| ✅ | `research-hub` | de, en | Prüfen ob vollständig |
| 1 | `weltenhub` | de, en | Creative content → ggf. mehr Sprachen |
| 2 | `pptx-hub` | de, en | UI-Strings prioritär |
| 3 | `trading-hub` | de, en | Zahlenformat wichtig |
| 4 | `cad-hub` | de, en | Technische Begriffe |
| 5 | `wedding-hub` | de, en, fr? | Emotionaler Content |
| 6 | `137-hub` | de, en | |
| 7 | `illustration-hub` | de, en | |
| – | `dev-hub` | de | Intern, en optional |

### Migration-Checkliste je Repo

- [ ] `settings.py`: `USE_I18N`, `LANGUAGES`, `LOCALE_PATHS`, `LocaleMiddleware`
- [ ] `urls.py`: `i18n_patterns()` + `i18n/` URL
- [ ] `locale/de/LC_MESSAGES/django.po` initialisieren (`makemessages -l de`)
- [ ] `locale/en/LC_MESSAGES/django.po` initialisieren (`makemessages -l en`)
- [ ] Templates: alle Hardcode-Strings mit `{% trans %}` wrappen
- [ ] Language-Switcher ins Base-Template
- [ ] `Organization.language` Feld (wenn ADR-109 implementiert)
- [ ] `compilemessages` in CI/CD (`Dockerfile`: `RUN python manage.py compilemessages`)
- [ ] Tests: `@override_settings(LANGUAGE_CODE="en")` für kritische Views

### CI/CD-Integration

```dockerfile
# Dockerfile — Pflicht nach collectstatic
RUN python manage.py compilemessages
```

```yaml
# GitHub Actions — Pflicht in CI
- name: Check translations
  run: |
    python manage.py makemessages -l de -l en --no-location
    git diff --exit-code locale/  # schlägt fehl wenn neue Strings unübersetzt
```

## Konsequenzen

**Positiv:**
- Plattformweite Mehrsprachigkeit ohne Mehraufwand bei neuen Features
- Tenant-Sprache überschreibt Default → B2B-ready
- Zahlen/Datums-Formate korrekt für alle Märkte
- `makemessages` in CI verhindert vergessene Übersetzungen

**Negativ / Aufwand:**
- Initiales Wrapping aller Template-Strings (~2-4h pro Hub)
- `.po`-Dateien müssen gepflegt werden
- `compilemessages` verlängert Docker-Build minimal (~5s)

## Abgrenzung

- **Übersetzungsinhalt** (User-generated content) ist **nicht** Scope dieses ADR
- **RTL-Sprachen** (Arabisch, Hebräisch) erfordern separates ADR (Frontend-Anpassungen)
- **Automatische Übersetzung via LLM** ist Scope ADR-11x (zukünftig)

---
*ADR-110 | Platform Architecture | 2026-03-08*
