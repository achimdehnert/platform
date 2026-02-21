---
description: Test-Infrastruktur für neue Repos einrichten (platform_context.testing, ADR-058)
---

# Testing Setup für neue Repos (ADR-058)

Jedes neue Repo MUSS `platform_context.testing` integrieren.
Dieses Dokument wird von `/onboard-repo` in Step 1.6 referenziert.

## Pflicht-Dateien

### `requirements-test.txt`

```text
pytest>=8.0
pytest-django>=4.8
pytest-mock>=3.12
factory-boy>=3.3
platform-context[testing]>=0.3.0
```

### `tests/conftest.py` (Django-App)

```python
# tests/conftest.py — ADR-058 §Confirmation
import pytest

# Shared platform fixtures (platform-context[testing])
from platform_context.testing.fixtures import (  # noqa: F401
    admin_client,
    admin_user,
    auth_client,
    htmx_client,
)

# Repo-specific: user via UserFactory
# Bei Custom User Model (allauth etc.) diese Fixture lokal überschreiben:
@pytest.fixture
def user(db):
    """Standard authenticated user."""
    from tests.factories import UserFactory
    return UserFactory()
```

### `tests/conftest.py` (Nicht-Django, z.B. MCP-Server)

```python
# tests/conftest.py — ADR-058 §Confirmation
# Kein Django → keine Django-Fixtures, nur Assertion-Helpers
import pytest

@pytest.fixture
def assert_json_error():
    from platform_context.testing.assertions import assert_json_error
    return assert_json_error

@pytest.fixture
def assert_celery_dispatched():
    from platform_context.testing.assertions import assert_celery_dispatched
    return assert_celery_dispatched
```

### `tests/factories.py` (Django-App)

```python
# tests/factories.py — ADR-058 §2.5
import factory
from django.contrib.auth.models import User


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user_{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    password = factory.PostGenerationMethodCall("set_password", "testpass123")
    is_active = True
```

### `tests/test_auth.py` (PFLICHT für alle Django-Apps)

```python
"""Auth + access control tests (ADR-058 A2)."""
import pytest
from platform_context.testing.assertions import assert_login_required, assert_no_data_leak

PROTECTED_URLS = [
    "/dashboard/",
    # weitere geschützte URLs ergänzen
]

@pytest.mark.django_db
@pytest.mark.parametrize("url", PROTECTED_URLS)
def test_should_protected_url_require_login(client, url):
    """A2: All protected URLs redirect unauthenticated users to login."""
    assert_login_required(client, url)

@pytest.mark.django_db
def test_should_health_endpoint_be_public(client):
    """U9: /livez/ is reachable without authentication."""
    response = client.get("/livez/")
    assert response.status_code == 200
```

### `pyproject.toml` — pytest-Konfiguration

```toml
[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "config.settings.base"
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*", "test_should_*"]
addopts = "-v --tb=short"
```

## Verfügbare Assertions

| Assertion | Zweck | ADR-058 |
|-----------|-------|--------|
| `assert_login_required(client, url)` | URL erfordert Login | A2 |
| `assert_no_data_leak(client, url, user)` | Cross-User-Isolation | A2 |
| `assert_htmx_fragment(response)` | HTMX-Partial zurückgegeben | U3/U4 |
| `assert_htmx_trigger(response, event)` | HX-Trigger Header gesetzt | U3/U4 |
| `assert_json_error(response, status)` | JSON-Fehlerantwort valide | A6 |
| `assert_celery_dispatched(mock, count)` | Celery-Task dispatched | A10 |
| `assert_graceful_degradation(response)` | Kein 500 bei Fehler | F3 |

## Verfügbare Fixtures

| Fixture | Zweck |
|---------|-------|
| `user` | Standard-User (Django auth) |
| `admin_user` | Superuser |
| `auth_client` | Eingeloggter Django-Client |
| `admin_client` | Eingeloggter Admin-Client |
| `htmx_client` | Client mit `HX-Request: true` Header |

**Hinweis:** Bei Custom User Models die `user`-Fixture lokal überschreiben.
`auth_client`, `admin_client`, `htmx_client` bleiben unverändert nutzbar.

## Tests automatisch im Deployment (CI/CD)

**Tests laufen IMMER vor dem Deploy** — garantiert durch `needs: [ci]` in der Pipeline.

```
push to main
    │
    ▼
[Stage 1: CI]  ← pytest läuft hier
    ├── ruff lint
    ├── pytest tests/ (mit platform_context.testing)
    └── security scan
    │
    ▼ (nur wenn CI grün)
[Stage 2: Build]
    └── docker build + push to GHCR
    │
    ▼ (nur wenn Build grün)
[Stage 3: Deploy]
    ├── docker compose pull + up --force-recreate
    └── health check /livez/ → Rollback wenn 503
```

### Post-Deploy Tests im Container (für DB-abhängige Tests)

```bash
# Manuell nach Deploy:
docker exec <REPO_UNDERSCORE>_web python manage.py test --verbosity=2

# Via deployment-mcp:
mcp5_docker_manage(action="container_exec",
    container_id="<REPO_UNDERSCORE>_web",
    command="python manage.py test apps/ --verbosity=2")
```

**Empfehlung:**
- Unit/Integration-Tests → im CI (vor Deploy, schnell, kein Server nötig)
- DB-Migrations-Tests → im Container nach Deploy (echte DB)
- Smoke-Tests → HTTP-Check auf `/livez/` + `/healthz/` nach Deploy

## Checkliste für neue Repos

```text
Testing (ADR-058):
  [ ] requirements-test.txt mit platform-context[testing]>=0.3.0
  [ ] tests/__init__.py existiert
  [ ] tests/conftest.py importiert platform_context.testing.fixtures
  [ ] tests/factories.py mit UserFactory (+ domain-spezifische Factories)
  [ ] tests/test_auth.py mit assert_login_required für alle geschützten URLs
  [ ] pyproject.toml mit [tool.pytest.ini_options]
  [ ] CI/CD: pytest läuft in Stage 1 (vor Build + Deploy)
```

## Repos als Referenz

| Repo | Besonderheit | Vorlage für |
|------|-------------|-------------|
| `risk-hub` | Multi-Tenant, `tenant_id` fixture | Multi-Tenant Apps |
| `weltenhub` | DRF APIClient, Cross-Tenant-Tests | API-Apps |
| `travel-beat` | Custom User Model, Celery-Tests | Consumer Apps |
| `wedding-hub` | Domain-spezifische Fixtures (org, event, guest) | Event-Apps |
| `mcp-hub` | Kein Django, nur Assertion-Helpers | Python-Libraries |
