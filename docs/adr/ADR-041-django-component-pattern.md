# ADR-041: Django Component Pattern — Reusable UI Blocks

| Metadata | Value |
|----------|-------|
| **Status** | Proposed |
| **Date** | 2026-02-16 |
| **Author** | Achim Dehnert |
| **Reviewers** | — |
| **Supersedes** | — |
| **Related** | ADR-040 (Frontend Completeness Gate), ADR-009 (Deployment Architecture) |

---

## 1. Context

### 1.1 Problem Statement

Django-Templates in der BF Agent Platform enthalten **duplizierte UI-Blöcke**, die über mehrere Templates hinweg copy-pasted werden. Beispiele aus der aktuellen Codebasis:

- **Weltenhub Sidebar** (`trip_detail.html`): Orte, Charaktere, Reisende — identische Darstellung in `trip_detail.html`, `trip_overview.html`, potentiell `story_detail.html`
- **Traveler-Listen**: Einmal als eigenständige Card (Zeile 212-245), einmal im Weltenhub-Block (Zeile 328-352), jeweils mit leicht abweichendem Markup
- **Statistik-Cards**: Identische Muster in `trip_detail`, `dashboard`, `story_progress`

Dieses Pattern widerspricht DRY und führt zu:

| Problem | Auswirkung |
|---------|------------|
| Code-Duplizierung | Änderungen müssen an N Stellen nachgezogen werden |
| Inkonsistente UI | Gleiche Daten, unterschiedliche Darstellung |
| Schwer testbar | Kein isolierter Test eines UI-Blocks möglich |
| KI-Generierung unvollständig | KI "vergisst" Blöcke beim Copy-Paste (→ ADR-040) |
| Keine flexible Varianten | Kein Mechanismus für compact/card/full Darstellung |

### 1.2 Bezug zu ADR-040 (Frontend Completeness Gate)

ADR-040 definiert ein **UI-Manifest** als Single Source of Truth für erwartete Elemente und einen **Completeness Checker** gegen `data-testid`-Attribute. ADR-041 ergänzt dies durch eine **Architektur**, die UI-Blöcke als eigenständige, testbare Module organisiert — damit der Completeness Gate pro Component greifen kann, nicht nur pro Page.

```
ADR-040: WAS muss vorhanden sein?  (Manifest + Checker)
ADR-041: WIE wird es strukturiert? (Component Pattern)
         ↓
Synergie: Manifest pro Component → Checker prüft Components isoliert
          Component = Template + View + Tag + Test + Manifest
```

### 1.3 Betroffene Applikationen

| App | Duplizierte Blöcke (geschätzt) | Priorität |
|-----|-------------------------------|-----------|
| Travel-Beat (DriftTales) | ~15 (Sidebar, Cards, Lists) | **HOCH** |
| Weltenhub (Weltenforger) | ~10 (Entity Cards, Enrichment) | HOCH |
| Risk-Hub (Schutztat) | ~8 (Assessment Cards, Hazard Lists) | MITTEL |
| BF Agent | ~12 (Document Lists, Agent Cards) | MITTEL |

---

## 2. Decision

### 2.1 Architecture Choice

**Wir implementieren ein Django Component Pattern**, das jeden wiederverwendbaren UI-Block als eigenständiges Modul mit drei Zugangswegen definiert:

1. **Custom Inclusion Tag** — Server-side Rendering, kein Extra-Request
2. **HTMX Fragment View** — Lazy-loading, individuell cachebar
3. **Template Include** — Einfachster Weg für statische Partials

Jede Component besteht aus:

```
apps/<app>/
├── components/                     # Component-Module
│   ├── __init__.py                 # Registry + exports
│   ├── weltenhub_sidebar.py        # Logic: data + tag + view
│   ├── traveler_list.py
│   └── stop_timeline.py
├── templates/<app>/
│   └── components/                 # Component-Templates
│       ├── _weltenhub_sidebar.html
│       ├── _weltenhub_sidebar_compact.html
│       ├── _traveler_list.html
│       └── _stop_timeline.html
├── templatetags/
│   └── <app>_components.py         # Registers inclusion tags
└── urls_components.py              # HTMX fragment endpoints
```

### 2.2 Component Anatomy

Jede Component folgt einem einheitlichen Pattern:

```python
# apps/trips/components/weltenhub_sidebar.py
"""
Weltenhub Sidebar Component.

Zeigt Welt, Orte, Charaktere und Reisende für einen Trip.
Nutzbar als Inclusion Tag, HTMX Fragment oder Template Include.
"""

from __future__ import annotations

from typing import Any

from django.http import HttpRequest
from django.template.response import TemplateResponse

TEMPLATES: dict[str, str] = {
    "default": "trips/components/_weltenhub_sidebar.html",
    "compact": "trips/components/_weltenhub_sidebar_compact.html",
    "card": "trips/components/_weltenhub_sidebar_card.html",
}


def get_context(
    trip: Any,
    user: Any,
    *,
    variant: str = "default",
) -> dict[str, Any]:
    """Single source of truth für Component-Daten.

    Wird von Tag, View und Tests gleichermaßen genutzt.
    """
    from apps.trips.services.trip_context import (
        fetch_weltenhub_data,
    )

    wh = fetch_weltenhub_data(trip, user)
    travelers = (
        trip.travel_party.all()
        .select_related("relation_type", "age_group")
        .order_by("order")
    )

    return {
        "trip": trip,
        "wh_world": wh.world,
        "wh_locations": wh.locations,
        "wh_characters": wh.characters,
        "wh_error": wh.error,
        "travelers": travelers,
        "variant": variant,
        "template_name": TEMPLATES.get(variant, TEMPLATES["default"]),
    }


# --- HTMX Fragment View -------------------------------------------

def fragment_view(
    request: HttpRequest,
    trip_pk: int,
) -> TemplateResponse:
    """HTMX Fragment endpoint for lazy-loading."""
    from apps.trips.models import Trip

    trip = Trip.objects.get(pk=trip_pk, user=request.user)
    variant = request.GET.get("variant", "default")
    ctx = get_context(trip, request.user, variant=variant)
    return TemplateResponse(request, ctx["template_name"], ctx)
```

### 2.3 Template Tag Registration

```python
# apps/trips/templatetags/trip_components.py
"""Component inclusion tags for trip templates."""

from __future__ import annotations

from django import template

register = template.Library()


@register.inclusion_tag(
    "trips/components/_weltenhub_sidebar.html",
    takes_context=True,
)
def weltenhub_sidebar(
    context: dict,
    trip: object,
    variant: str = "default",
) -> dict:
    """Render Weltenhub sidebar for a trip.

    Usage:
        {% load trip_components %}
        {% weltenhub_sidebar trip %}
        {% weltenhub_sidebar trip "compact" %}
    """
    from apps.trips.components.weltenhub_sidebar import (
        TEMPLATES,
        get_context,
    )

    user = context["request"].user
    ctx = get_context(trip, user, variant=variant)
    # Django inclusion_tag doesn't support dynamic template
    # selection natively, so we override via simple_tag
    # for variants. Default variant uses the registered template.
    return ctx


@register.inclusion_tag(
    "trips/components/_traveler_list.html",
    takes_context=True,
)
def traveler_list(
    context: dict,
    trip: object,
    variant: str = "default",
) -> dict:
    """Render traveler list for a trip."""
    from apps.trips.components.traveler_list import (
        get_context,
    )

    user = context["request"].user
    return get_context(trip, user, variant=variant)
```

### 2.4 URL Registration für HTMX Fragments

```python
# apps/trips/urls_components.py
"""HTMX fragment endpoints for trip components."""

from django.urls import path

from apps.trips.components import weltenhub_sidebar, traveler_list

app_name = "trip-components"

urlpatterns = [
    path(
        "<int:trip_pk>/weltenhub-sidebar/",
        weltenhub_sidebar.fragment_view,
        name="weltenhub_sidebar",
    ),
    path(
        "<int:trip_pk>/traveler-list/",
        traveler_list.fragment_view,
        name="traveler_list",
    ),
]
```

### 2.5 Drei Nutzungswege

```html
{# === Weg 1: Inclusion Tag (Server-Side, kein Extra-Request) === #}
{% load trip_components %}
{% weltenhub_sidebar trip %}
{% weltenhub_sidebar trip "compact" %}

{# === Weg 2: HTMX Fragment (Lazy-Loaded, cachebar) === #}
<div hx-get="{% url 'trip-components:weltenhub_sidebar' trip_pk=trip.pk %}"
     hx-trigger="load"
     hx-swap="innerHTML">
    <span class="spinner-border spinner-border-sm"></span> Lade...
</div>

{# === Weg 3: Template Include (einfach, Daten von View) === #}
{% include "trips/components/_weltenhub_sidebar.html" %}
```

### 2.6 Rejected Alternatives

#### React/Vue Components
Abgelehnt: Widerspricht dem Django+HTMX Stack (ADR-009). Würde einen Build-Step, eine JS-Toolchain und eine API-Schicht erfordern. Overhead für den Mehrwert zu hoch.

#### django-components Package
Abgelehnt: Externes Dependency mit eigener Template-Engine und CSS/JS-Bundling. Zu opinionated, zu viel Overhead für unseren Use-Case. Unser Pattern ist leichtgewichtiger und nutzt Django-Bordmittel.

#### Nur Template Includes
Abgelehnt: Löst nur die Template-Duplizierung, nicht die Daten-Duplizierung. Jede View muss weiterhin die Daten separat bereitstellen. Kein isolierter Test möglich.

---

## 3. Implementation

### 3.1 Component Checklist

Jede neue Component MUSS enthalten:

| Artefakt | Pflicht | Beschreibung |
|----------|---------|--------------|
| `get_context()` | **JA** | Single Source of Truth für Daten |
| Template (default) | **JA** | `_<name>.html` mit `data-testid` Attributen |
| Inclusion Tag | **JA** | `{% <name> obj %}` Syntax |
| Fragment View | OPTIONAL | Nur wenn Lazy-Loading sinnvoll |
| Template Varianten | OPTIONAL | `_<name>_compact.html` etc. |
| Unit Test | **JA** | Test für `get_context()` |
| E2E Test | **JA** | Playwright-Test per ADR-040 |
| UI-Manifest Entry | **JA** | Per ADR-040 Completeness Gate |

### 3.2 data-testid Convention

Alle Component-Elemente verwenden `data-testid` per ADR-040:

```
data-testid="<component>-<element>"

Beispiele:
  data-testid="weltenhub-sidebar-world"
  data-testid="weltenhub-sidebar-locations"
  data-testid="weltenhub-sidebar-characters"
  data-testid="weltenhub-sidebar-travelers"
  data-testid="traveler-list-item"
  data-testid="traveler-list-protagonist-badge"
```

### 3.3 Caching Strategy

```python
# Fragment Views können HTTP-Cache nutzen
from django.views.decorators.cache import cache_page

# 5 Minuten Cache für Weltenhub-Daten (ändern sich selten)
@cache_page(300)
def fragment_view(request, trip_pk):
    ...
```

Für Inclusion Tags:
```html
{% load cache %}
{% cache 300 weltenhub_sidebar trip.pk trip.weltenhub_synced_at %}
    {% weltenhub_sidebar trip %}
{% endcache %}
```

### 3.4 Migration bestehender Templates

**Schritt-für-Schritt pro Seite:**

1. Identifiziere duplizierten Block im Template
2. Erstelle Component (`components/<name>.py` + Template)
3. Erstelle Inclusion Tag in `templatetags/`
4. Ersetze den Block im Template durch `{% <tag> %}`
5. Füge `data-testid` Attribute hinzu
6. Schreibe Unit-Test für `get_context()`
7. Aktualisiere UI-Manifest (ADR-040)
8. Verifiziere mit Completeness Checker

**Beispiel — trip_detail.html vorher:**
```html
<!-- 30 Zeilen Weltenhub-Sidebar inline -->
{% if wh_world %}
<div class="mb-3">
    <h6>Welt</h6>
    ...
{% endif %}
{% if wh_locations %}
    ...
{% endif %}
{% if wh_characters %}
    ...
{% endif %}
{% if travelers %}
    ...
{% endif %}
```

**Nachher:**
```html
{% load trip_components %}
{% weltenhub_sidebar trip %}
```

---

## 4. Adoption Strategy

### 4.1 Phasenplan

| Phase | Zeitraum | Scope | Deliverables |
|-------|----------|-------|--------------|
| **Phase 1: Pilot** | Woche 1 | Travel-Beat: `weltenhub_sidebar` | 1 Component, 3 Templates refactored |
| **Phase 2: Core** | Woche 2-3 | Travel-Beat: `traveler_list`, `stop_timeline`, `story_card` | 4 Components, alle Trip-Views refactored |
| **Phase 3: Cross-App** | Woche 4-5 | Weltenhub: `entity_card`, `enrichment_panel` | Components für Weltenforger |
| **Phase 4: Platform** | Woche 6-8 | Shared Components in `platform/` Package | `stat_card`, `data_table`, `empty_state` |

### 4.2 Metriken

| Metrik | Baseline | Ziel |
|--------|----------|------|
| Duplizierte Template-Blöcke | ~45 | 0 |
| Template-Zeilen pro View | ~400 | ~50 (+ Components) |
| Isoliert testbare UI-Blöcke | 0 | >30 |
| Wiederverwendung pro Component | 1x | 2-5x |

---

## 5. Dependencies

| Package | Version | Zweck |
|---------|---------|-------|
| Django | >=5.0 | Inclusion Tags, TemplateResponse |
| HTMX | >=2.0 | Fragment lazy-loading |
| pytest-django | >=4.8 | Component Unit Tests |

Keine zusätzlichen Dependencies erforderlich — rein Django-Bordmittel.

---

## 6. Risks and Mitigations

| Risiko | Schweregrad | Mitigation |
|--------|-------------|------------|
| Over-Engineering: Zu viele kleine Components | MITTEL | Mindestgröße: Block muss an ≥2 Stellen vorkommen |
| N+1 Queries durch Inclusion Tags | HOCH | `get_context()` nutzt `select_related`/`prefetch_related` |
| Template-Varianten-Wildwuchs | MITTEL | Max 3 Varianten pro Component (default, compact, card) |
| Fragment-Endpoints ohne Auth | HOCH | Alle Fragment Views mit `@login_required` |
| Inkonsistenz zwischen Tag und Fragment | MITTEL | Beide nutzen identische `get_context()` Funktion |

---

## 7. References

- [ADR-040: Frontend Completeness Gate](./ADR-040-frontend-completeness-gate.md) — UI-Manifest + Playwright E2E
- [ADR-009: Deployment Architecture](./ADR-009-deployment-architecture.md) — Django + HTMX Stack
- [Django Custom Template Tags](https://docs.djangoproject.com/en/5.0/howto/custom-template-tags/) — Inclusion Tags
- [HTMX Lazy Loading](https://htmx.org/attributes/hx-trigger/) — `hx-trigger="load"` Pattern
- [Django Template Fragment Caching](https://docs.djangoproject.com/en/5.0/topics/cache/#template-fragment-caching)

---

## 8. Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-02-16 | Achim Dehnert | Initial Draft — Component Pattern mit 3 Zugangswegen |
