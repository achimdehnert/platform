---
id: ADR-100
title: "iil-testkit — Shared Test Factory Package für alle Platform-Repos"
status: accepted
date: 2026-03-05
reviewed: 2026-03-05
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
| Reviewed | 2026-03-05 (K1–K3, H1–H3, M1–M3 adressiert) |
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
3. **Fehlende Repos**: 5 Django-Repos (`dev-hub`, `risk-hub`, `pptx-hub`, `trading-hub`, `coach-hub`) haben gar keine `factories.py`.
4. **Keine Convention-Durchsetzung**: Test-Naming (`test_should_*` lt. ADR-057) wird nicht automatisch geprüft.
5. **Bestehende PyPI-Lösungen ungeeignet**: `model-bakery` und `mixer` generieren automatisch ohne explizites Muster.

### Warum ein eigenes Package (und nicht Templates)?

| Ansatz | Problem |
|---|---|
| Template-Distribution | Muss bei Änderungen manuell in alle Repos gepusht werden |
| Copy-Paste | Bereits gescheitert — 3 leicht verschiedene Versionen |
| `model-bakery` / `mixer` | Kein explizites Factory-Muster, keine Konvention |
| **`iil-testkit`** | Einmalige Änderung, alle Repos profitieren via pip upgrade |

---

## Entscheidung

**`iil-testkit`** wird als neues PyPI-Package entwickelt und in alle Django-Hub-Repos als `requirements-test.txt` Dependency aufgenommen.

### Pin-Strategie (K3)

```
iil-testkit>=0.1.0,<0.2.0
```

Upper Bound **zwingend** — jedes Minor-Increment kann Breaking Changes enthalten. Bump nach CHANGELOG-Review.

### Package-Struktur

```
iil-testkit/
├── iil_testkit/
│   ├── __init__.py          # __version__, __all__
│   ├── py.typed             # PEP 561 — mypy/pyright support
│   ├── factories.py         # UserFactory, StaffUserFactory, AdminUserFactory
│   ├── contrib/
│   │   └── tenants.py       # TenantFactory — expliziter Import, keine implizite Kopplung
│   ├── fixtures.py          # pytest fixtures: db_user, staff_user, api_client
│   ├── plugin.py            # pytest-Plugin: test_should_* enforcer (error mode)
│   └── assertions.py        # assert_redirects_to_login, assert_htmx_response, ...
├── pyproject.toml
├── CHANGELOG.md
├── tests/
└── README.md
```

### Kanonische Factories

```python
# iil_testkit/factories.py
import factory
from django.contrib.auth import get_user_model

class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = get_user_model()
        skip_postgeneration_save = True
        # skip_postgeneration_save verhindert einen zweiten save()-Aufruf durch
        # PostGenerationMethodCall (set_password). Ohne dieses Flag triggert
        # factory-boy >= 3.3 post_save Signale doppelt. (K3/M2)

    username = factory.Sequence(lambda n: f"user_{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    password = factory.PostGenerationMethodCall("set_password", "testpass123")
    is_active = True
```

### TenantFactory — Optionale Kopplung (K1)

`TenantFactory` ist **nicht** in `iil_testkit.factories` enthalten. Das verhindert `ImportError`
beim Import in Repos ohne `tenants`-App, der den gesamten Test-Run abbricht.

```python
# Repos MIT tenants-App (weltenhub):
from iil_testkit.contrib.tenants import TenantFactory

# Repos OHNE tenants-App (dev-hub, pptx-hub, trading-hub):
from iil_testkit.factories import UserFactory  # kein TenantFactory-Import
```

`TenantFactory._create()` / `._build()` prüft zur Laufzeit ob `tenants` in `INSTALLED_APPS`
und wirft `RuntimeError` mit klarer Fehlermeldung (nicht `ImportError` beim Laden).

### pytest-Plugin — Enforcement (K2)

Das Plugin läuft im **Error-Modus** (Standard) — Violations brechen den Test-Run mit `pytest.fail()`.

```python
# iil_testkit/plugin.py
def pytest_collection_modifyitems(config, items):
    violations = [...]
    if violations:
        mode = config.getini("iil_naming_mode") or "error"
        if mode == "error":
            pytest.fail(f"Naming convention violations (ADR-057):\n...")
```

Konfiguration in `pyproject.toml`:
```toml
[tool.pytest.ini_options]
iil_naming_mode = "error"   # default — Verletzungen brechen CI
# iil_naming_mode = "warn"  # opt-down für Legacy-Repos mit vielen alten Tests
```

Opt-out einzelner Tests: `@pytest.mark.no_naming_convention`
Opt-out global: `pytest --relax-naming`

### Assertions (H3)

```python
# iil_testkit/assertions.py — vollständige Public API
assert_redirects_to_login(response, next_url=None)  # Redirect zu Login prüfen
assert_htmx_response(response, status_code=200)     # HTMX-Partial (kein <html>)
assert_no_n_plus_one(queries, threshold=5)          # N+1-Guard via Query-Count
assert_form_error(response, field, message)         # Formular-Fehlerprüfung
```

### Versionsstrategie (K3)

Semantic Versioning: `MAJOR.MINOR.PATCH`

| Änderung | Version |
|----------|---------|
| Neues `assert_*` / neue Factory-Subklasse | PATCH |
| Neues Modul in `contrib/` | MINOR |
| Umbenennung / Entfernung aus `__all__` | MAJOR |
| `UserFactory.username`-Format-Änderung | MAJOR |
| Plugin-Default von `warn` → `error` | MAJOR |

`CHANGELOG.md` ist Pflicht bei jedem Release. GitHub Release Notes werden aus CHANGELOG generiert.

### pyproject.toml Kern (H2)

```toml
[project.entry-points."pytest11"]
iil-testkit = "iil_testkit.plugin"  # Auto-Registrierung — kein manuelles conftest.py

[tool.pytest.ini_options]
iil_naming_mode = "error"
addopts = "--cov=iil_testkit --cov-fail-under=80"
```

### PyPI-Index (M3)

`iil-testkit` wird auf dem **öffentlichen PyPI** veröffentlicht. Der Package-Name ist eindeutig
(keine Kollision nachgewiesen, Stand 2026-03-05). Kein privater Index notwendig — analog zu
`iil-aifw`, `iil-authoringfw`.

---

## Konsequenzen

### Positiv
- **Single Source of Truth** für `UserFactory`, `StaffUserFactory`, `AdminUserFactory`
- **Automatische Convention-Prüfung** mit `pytest.fail()` — CI bricht bei Verletzungen
- **Konsistente `skip_postgeneration_save`** in allen Repos (M2: verhindert Doppel-Signals)
- **Optionale Kopplung**: `TenantFactory` nur in Repos mit `tenants`-App
- **Mypy-kompatibel** via `py.typed` (PEP 561)
- **CI Coverage Gate** 80% auf `iil-testkit` selbst

### Negativ / Risiken
- Zusätzliche Dependency in `requirements-test.txt` aller Repos
- Plugin im `error`-Modus kann Legacy-Repos mit alten Test-Namen initial blockieren
  → Mitigation: `iil_naming_mode = "warn"` in `pyproject.toml` des Legacy-Repos setzen
- Breaking-Change-Risiko bei Minor-Upgrades wenn keine Upper Bound gesetzt

### Migration

1. `iil-testkit` v0.1.0 auf PyPI veröffentlichen (nach PyPI Trusted Publisher Setup)
2. In allen Repos `requirements-test.txt` ergänzen: `iil-testkit>=0.1.0,<0.2.0`
3. Bestehende `factories.py` in `bfagent`, `travel-beat` auf `from iil_testkit.factories import UserFactory` umstellen ✅
4. `weltenhub`: `from iil_testkit.contrib.tenants import TenantFactory` ✅
5. Neue `factories.py` in `dev-hub`, `risk-hub`, `pptx-hub`, `trading-hub`, `coach-hub` anlegen
6. `iil_naming_mode = "warn"` in Repos mit Legacy-Tests, schrittweise auf `"error"` migrieren

---

## Alternativen verworfen

| Alternative | Grund |
|---|---|
| `model-bakery` | Auto-generiert ohne Kontrolle, kein explizites Muster |
| `mixer` | Gleiche Schwäche wie model-bakery |
| Template-Distribution via GitHub | Manueller Sync bei Änderungen |
| `TenantFactory` in `factories.py` (try/except) | Import-Error bricht gesamten Test-Run (K1) |
| Plugin nur `warn()` | Warnings werden in CI ignoriert (K2) |
| Kein Package (Status quo) | Copy-Paste-Problem bleibt bestehen |

---

*ADR-100 v1.1 | Platform Coding Agent System | 2026-03-05*
*Review-Findings K1–K3, H1–H3, M1–M3 adressiert — freigegeben für v0.1.0 Release*
