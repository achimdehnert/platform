# Perfect Prompt: Optimales Testing für ein Django-Repo

> Verwendung: Diesen Prompt an Cascade übergeben, `<REPO_NAME>` ersetzen.
> Alle Constraints sind eingebettet — kein Session-Kontext nötig.

---

## Prompt (copy-paste ready)

```
Implementiere vollständiges Test-Setup für das Django-Repo "<REPO_NAME>".

### Kontext

Wir arbeiten auf der IIL Platform (achimdehnert/*). Das Repo liegt unter
${GITHUB_DIR:-~/CascadeProjects}/<REPO_NAME>.

Vorhandene Infrastruktur (NICHT neu implementieren):
- iil-testkit v0.4.0 (PyPI: iil-testkit[smoke]) stellt bereit:
  - Fixtures: auth_client, staff_client, api_client, db_user, staff_user, admin_user
  - Assertions: assert_htmx_response(), assert_data_testids(), assert_redirects_to_login(),
    assert_no_n_plus_one(), assert_form_error()
  - URL-Discovery: discover_smoke_urls() — auto-findet alle parameterfreien Routes
  - Naming-Enforcement: test_should_* Convention ist auto-aktiv wenn iil-testkit installiert
- platform/docs/templates/django_test_scaffold/ — Referenz-Scaffold (nicht kopieren, selbst anpassen)

### Was zu tun ist

**Schritt 1: Repo analysieren**
Lese (MUSS vor jedem anderen Schritt):
- <REPO_NAME>/apps/ — alle Apps und ihre Models, Views, URLs
- <REPO_NAME>/config/urls.py — URL-Struktur und Namespaces
- <REPO_NAME>/pyproject.toml — Settings-Modul ermitteln (DJANGO_SETTINGS_MODULE)
- Prüfe: Gibt es bereits tests/? Falls ja: was fehlt?

**Schritt 2: Pflicht-Dateien erstellen/ergänzen**

`requirements-test.txt` (erstellen falls fehlt):
```
iil-testkit[smoke]>=0.4.0,<1
pytest>=8.0
pytest-django>=4.8
pytest-cov>=5.0
pytest-xdist>=3.0
beautifulsoup4>=4.12
factory-boy>=3.3
```

`tests/__init__.py` (leer)

`tests/conftest.py`:
```python
pytest_plugins = ["iil_testkit.fixtures"]
```

`pyproject.toml` — [tool.pytest.ini_options] ergänzen:
```toml
[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "<ermittelt aus Schritt 1>"
python_files = ["test_*.py"]
python_functions = ["test_should_*"]
addopts = ["--strict-markers", "--tb=short", "-ra", "--no-header",
           "--cov", "--cov-report=term-missing", "--cov-fail-under=80"]
markers = ["unit: Unit-Tests", "integration: Integration-Tests (DB)",
           "contract: Contract-Tests", "slow: Tests > 5s"]
testpaths = ["tests"]
```

**Schritt 3: tests/factories.py** (repo-spezifisch)
- UserFactory aus iil_testkit.factories importieren und re-exportieren
- Für jedes Domain-Model eine Factory erstellen (z.B. TripFactory, ProjectFactory)
- Naming: `class <Model>Factory(DjangoModelFactory):`
- Pflicht-Pattern: `factory.Sequence` für eindeutige Strings, `SubFactory` für FKs

**Schritt 4: tests/test_views_smoke.py**
```python
import pytest
from iil_testkit.smoke import discover_smoke_urls

@pytest.mark.parametrize("url", discover_smoke_urls())
@pytest.mark.django_db
def test_should_view_return_200(url: str, auth_client) -> None:
    response = auth_client.get(url)
    assert response.status_code in (200, 302)

@pytest.mark.parametrize("url", discover_smoke_urls())
@pytest.mark.django_db
def test_should_unauthenticated_be_redirected(url: str, api_client) -> None:
    from iil_testkit.assertions import assert_redirects_to_login
    response = api_client.get(url)
    if response.status_code == 302:
        assert_redirects_to_login(response)
```

**Schritt 5: tests/test_views_htmx.py**
- Finde alle Views die HTMX-Partials liefern (erkennbar an hx-post/hx-get in Templates)
- Trage diese URLs in HTMX_URLS ein
- Teste: assert_htmx_response() + assert_data_testids() (ADR-048)

**Schritt 6: tests/test_<hauptapp>.py** (min. 1 Service-Layer-Test pro App)
- Teste Services (NICHT direkt ORM in Views — ADR Service Layer)
- Naming: test_should_<expected_behavior>
- Markers: @pytest.mark.django_db für DB-Tests
- Max 5 Assertions pro Test-Funktion
- Teste: Happy Path + mind. 1 Edge Case pro Service-Funktion

### Constraints (ALLE sind nicht verhandelbar)

ARCHITEKTUR:
- Service Layer: views.py → services.py → models.py — ORM NIE direkt in Views testen
- Tests testen SERVICES, nicht direkt Models.objects.*
- Keine unittest.TestCase — nur pytest-Funktionen

NAMING:
- ALLE Test-Funktionen: test_should_<expected_behavior>
  Beispiel: test_should_return_404_when_trip_not_found
  NICHT: test_trip_detail, test_login

HTMX (ADR-048):
- Partials: kein <html>/<head>/<body> in Antwort → assert_htmx_response()
- Alle hx-* Elemente haben data-testid → assert_data_testids()

QUALITÄT:
- Max 30 Zeilen pro Test-Funktion
- Max 5 Assertions pro Test-Funktion
- Alle externen Services mocken (kein echtes HTTP, kein echtes LLM)
- @pytest.mark.django_db auf ALLEN Tests die DB nutzen

### Acceptance Criteria (Done = alle erfüllt)

[ ] pytest tests/ läuft durch ohne Fehler (rc=0)
[ ] discover_smoke_urls() findet mindestens 1 URL
[ ] Alle Smoke-Tests bestehen (HTTP 200/302)
[ ] Coverage >= 80% für services.py in jeder App
[ ] Kein Test heißt test_<x> ohne test_should_ prefix
[ ] requirements-test.txt hat iil-testkit[smoke]>=0.4.0,<1
[ ] pyproject.toml hat [tool.pytest.ini_options] mit DJANGO_SETTINGS_MODULE
[ ] python3 platform/scripts/teste_repo.py <REPO_NAME> endet mit Exit-Code 0

### Was NICHT zu tun ist

- NICHT platform_context.testing verwenden (veraltet → iil-testkit)
- NICHT manage.py test verwenden
- NICHT unittest.TestCase verwenden
- NICHT ORM direkt in Tests (Trip.objects.filter...) — Factories nutzen
- NICHT Fixtures hardcoden (keine test_user = User.objects.create_user("max",...))
- NICHT Test-Dateien für nicht-existente Features schreiben
- NICHT requirements-test.txt in requirements.txt integrieren (getrennt halten)
```

---

## Kurzversion (für schnelle Onboarding-PRs)

```
Füge minimales Test-Setup zu <REPO_NAME> hinzu.

Installiere iil-testkit[smoke]>=0.4.0,<1 und erstelle:
1. tests/conftest.py mit `pytest_plugins = ["iil_testkit.fixtures"]`
2. tests/test_views_smoke.py mit discover_smoke_urls() + test_should_view_return_200
3. requirements-test.txt mit iil-testkit[smoke]>=0.4.0,<1 + pytest>=8.0 + pytest-django>=4.8
4. pyproject.toml [tool.pytest.ini_options] mit DJANGO_SETTINGS_MODULE aus config/settings/

Nenne alle Tests test_should_<expected_behavior>.
Validiere mit: python3 ~/CascadeProjects/platform/scripts/teste_repo.py <REPO_NAME>
```

---

## Varianten

### Für Multi-Tenant-Repos (weltenhub, risk-hub)

Ergänze im Prompt nach "Constraints":

```
MULTI-TENANCY (ADR-009):
- Alle Queries filtern nach tenant_id
- Teste: User von Tenant A kann Daten von Tenant B NICHT sehen
- Factory: TenantFactory aus iil_testkit.contrib.tenants
- Jeder Test der tenant-isolierte Views testet braucht zwei User (A + B)
```

### Für API-Repos mit DRF

Ergänze im Prompt nach fixtures:

```
DRF-FIXTURES:
- Verwende drf_auth_client statt auth_client für API-Endpoints
- Teste: Response-Schema mit response.json() assertions
- Optional: Schemathesis für Contract-Tests (@pytest.mark.contract)
```

### Für Repos ohne Django (Libraries, MCP-Server)

```
Kein Django → kein pytest-django, kein DJANGO_SETTINGS_MODULE.
Verwende nur: pytest>=8.0, iil-testkit>=0.4.0,<1 (ohne [smoke])
Teste: Public API der Library (importierbare Funktionen/Klassen)
Naming: test_should_<expected_behavior> bleibt Pflicht
```
