---
id: ADR-100
title: "iil-testkit — Shared Test Factory Package für alle Platform-Repos"
status: accepted
date: 2026-03-05
author: Achim Dehnert
owner: Achim Dehnert
decision-makers: [Achim Dehnert]
consulted: []
informed: [bfagent, travel-beat, weltenhub, risk-hub, coach-hub, dev-hub, pptx-hub, trading-hub, billing-hub, illustration-hub, odoo-hub]
scope: alle Django-Hub-Repos der Platform
tags: [testing, factory-boy, pytest, testkit, shared-package, pypi]
related: [ADR-057, ADR-084, ADR-096]
supersedes: []
amends: [ADR-057]
last_verified: 2026-03-05
---

# ADR-100: iil-testkit — Shared Test Factory Package für alle Platform-Repos

| Field | Value |
|-------|-------|
| Status | **Accepted** |
| Date | 2026-03-05 |
| Author | Achim Dehnert |
| Scope | Alle Django-Hub-Repos (`bfagent`, `travel-beat`, `weltenhub`, `risk-hub`, `coach-hub`, `dev-hub`, `pptx-hub`, `trading-hub`, `billing-hub`, `illustration-hub`, `odoo-hub`, `cad-hub`, `mcp-hub`, `nl2cad`, `wedding-hub`, `137-hub`) |
| Amends | ADR-057 (Test Strategy — fügt Factory-Konventionen hinzu) |
| Related | ADR-084 (illustration-fw als PyPI Package), ADR-096 (authoringfw Architektur) |

---

## Kontext

### Problem

Analyse der bestehenden `tests/factories.py` Dateien in den Platform-Repos zeigt:

1. **Copy-Paste-Duplizierung**: `UserFactory` ist in `bfagent`, `travel-beat`, `weltenhub` identisch — jede Änderung muss mehrfach gemacht werden.
2. **Inkonsistente Qualität**: `skip_postgeneration_save` (notwendig ab factory-boy 3.3.x) fehlt in 2 von 3 bestehenden `factories.py`.
3. **Fehlende Repos**: 5 Django-Repos (`dev-hub`, `risk-hub`, `pptx-hub`, `trading-hub`, `coach-hub`) haben gar keine `factories.py` — Tests greifen direkt auf `User.objects.create_user()` zurück.
4. **Keine Convention-Durchsetzung**: Test-Naming (`test_should_*` lt. ADR-057) wird nicht automatisch geprüft.
5. **Bestehende PyPI-Lösungen ungeeignet**: `model-bakery` und `mixer` generieren automatisch ohne explizites Muster — schwer wartbar. `django-factory-boy` (v1.0) ist zu minimalistisch.

### Warum ein eigenes Package (und nicht Templates)?

| Ansatz | Problem |
|---|---|
| Template-Distribution | Muss bei Änderungen manuell in alle Repos gepusht werden |
| Copy-Paste | Bereits gescheitert — 3 leicht verschiedene Versionen |
| `model-bakery` / `mixer` | Kein explizites Factory-Muster, keine Konvention |
| **`iil-testkit`** | Einmalige Änderung, alle Repos profitieren via pip upgrade |

---

## Entscheidung

**`iil-testkit`** wird als neues PyPI-Package (`pip install iil-testkit`) entwickelt und in alle Django-Hub-Repos als `requirements-test.txt` Dependency aufgenommen.

### Package-Struktur

```
iil-testkit/
├── iil_testkit/
│   ├── __init__.py
│   ├── factories.py      # UserFactory, TenantFactory (platform-standard)
│   ├── fixtures.py       # pytest fixtures: db_user, tenant_user, api_client
│   ├── plugin.py         # pytest-Plugin: test_should_* naming enforcer
│   └── assertions.py     # Helpers: assert_redirects_to_login, assert_htmx_response
├── pyproject.toml
├── tests/
└── README.md
```

### Kanonische Factories

```python
# iil_testkit/factories.py
import factory
from django.contrib.auth import get_user_model

User = get_user_model()

class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True  # factory-boy >= 3.3.x

    username = factory.Sequence(lambda n: f"user_{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    password = factory.PostGenerationMethodCall("set_password", "testpass123")
    is_active = True

class TenantFactory(factory.django.DjangoModelFactory):
    """Erfordert apps.tenants.models.Tenant im Ziel-Repo."""
    class Meta:
        model = "tenants.Tenant"

    name = factory.Sequence(lambda n: f"Tenant {n}")
    slug = factory.Sequence(lambda n: f"tenant-{n}")
    is_active = True
```

### Repo-spezifische Erweiterung

```python
# tests/factories.py in bfagent (nach Migration)
from iil_testkit.factories import UserFactory  # importiert, nicht kopiert

class BookProjectFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "bfagent.BookProjects"
    user = factory.SubFactory(UserFactory)
    ...
```

### pytest-Plugin (Naming Convention)

```python
# iil_testkit/plugin.py — via entry_points registriert
def pytest_collection_modifyitems(items):
    for item in items:
        if isinstance(item, pytest.Function):
            if not item.name.startswith("test_should_"):
                item.warn(PytestWarning(
                    f"Convention: '{item.name}' sollte 'test_should_' beginnen (ADR-057)"
                ))
```

---

## Konsequenzen

### Positiv
- **Single Source of Truth** für `UserFactory` und `TenantFactory`
- **Automatische Convention-Prüfung** ohne manuelle Konfiguration
- **Konsistente `skip_postgeneration_save`** in allen Repos
- **Erweiterbar**: neue shared Fixtures zentral hinzufügbar
- **Analog zu `aifw`/`authoringfw`**: bekanntes Package-Pattern, Release-Workflow vorhanden

### Negativ / Risiken
- Zusätzliche Dependency in `requirements-test.txt` aller Repos
- Breaking Change wenn `TenantFactory` das `tenants`-App-Modell nicht findet — wird per `ImportError` mit klarer Meldung abgefangen
- Initialer Migrationsaufwand: bestehende `factories.py` in 3 Repos auf Import umstellen

### Migration

1. `iil-testkit` v0.1.0 auf PyPI veröffentlichen
2. In allen Repos `requirements-test.txt` ergänzen: `iil-testkit>=0.1.0`
3. Bestehende `factories.py` in `bfagent`, `travel-beat`, `weltenhub` auf `from iil_testkit.factories import UserFactory` umstellen
4. Neue `factories.py` in `dev-hub`, `risk-hub`, `pptx-hub`, `trading-hub`, `coach-hub` anlegen

---

## Alternativen verworfen

| Alternative | Grund |
|---|---|
| `model-bakery` | Auto-generiert ohne Kontrolle, kein explizites Muster |
| `mixer` | Gleiche Schwäche wie model-bakery |
| Template-Distribution via GitHub | Manueller Sync bei Änderungen |
| Kein Package (Status quo) | Copy-Paste-Problem bleibt bestehen |

---

*ADR-100 | Platform Coding Agent System | 2026-03-05*
