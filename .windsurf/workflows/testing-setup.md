---
description: Test-Infrastruktur für neue Repos einrichten (iil-testkit, ADR-058)
---

# Testing Setup für neue Repos (ADR-058)

Jedes neue Repo MUSS `iil-testkit` integrieren.
Dieses Dokument wird von `/onboard-repo` in Step 1.6 referenziert.

> **Automatisierung:** Der `scaffold-tests` Workflow erstellt automatisch einen PR
> wenn ein neues Repo in `repo-registry.yaml` eingetragen wird.
> Manuell: `gh workflow run scaffold-tests.yml -f repo_name=<name>`

## Pflicht-Dateien

### `requirements-test.txt`

```text
iil-testkit[smoke]>=0.4.0,<1
pytest>=8.0
pytest-django>=4.8
pytest-cov>=5.0
pytest-xdist>=3.0
beautifulsoup4>=4.12
factory-boy>=3.3
```

### `tests/conftest.py` (Django-App)

```python
# tests/conftest.py — ADR-058 §Confirmation
# Stellt alle Fixtures bereit: auth_client, staff_client, db_user, admin_user
pytest_plugins = ["iil_testkit.fixtures"]
```

### `tests/conftest.py` (Nicht-Django, z.B. MCP-Server)

```python
# tests/conftest.py — ADR-058 §Confirmation (ohne Django)
import pytest
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

## Verfügbare Assertions (`from iil_testkit.assertions import ...`)

| Assertion | Zweck | ADR |
|-----------|-------|-----|
| `assert_redirects_to_login(response)` | URL erfordert Login | ADR-058 A2 |
| `assert_htmx_response(response)` | HTMX-Partial — kein `<html>` | ADR-048 |
| `assert_data_testids(response)` | Alle `hx-*` Elemente haben `data-testid` | ADR-048 |
| `assert_no_n_plus_one(queries, threshold)` | N+1 Query-Detektion | ADR-058 |
| `assert_form_error(response, field, msg)` | Formularfehler-Check | ADR-058 |

## Verfügbare Fixtures (`pytest_plugins = ["iil_testkit.fixtures"]`)

| Fixture | Zweck |
|---------|-------|
| `db_user` | Standard-User (Django auth) |
| `staff_user` | User mit `is_staff=True` |
| `admin_user` | User mit `is_superuser=True` |
| `api_client` | Nicht-eingeloggter Django-Client |
| `auth_client` | Eingeloggter Django-Client (als `db_user`) |
| `staff_client` | Eingeloggter Django-Client (als `staff_user`) |

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
    ├── pytest tests/ (mit iil-testkit)
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
mcp__deployment-mcp__docker_manage(action="container_exec",
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
  [ ] requirements-test.txt mit iil-testkit[smoke]>=0.4.0
  [ ] tests/__init__.py existiert
  [ ] tests/conftest.py: pytest_plugins = ["iil_testkit.fixtures"]
  [ ] tests/factories.py mit UserFactory (+ domain-spezifische Factories)
  [ ] tests/test_views_smoke.py mit discover_smoke_urls()
  [ ] tests/test_views_htmx.py mit HTMX_URLS befüllt
  [ ] pyproject.toml mit [tool.pytest.ini_options] + DJANGO_SETTINGS_MODULE
  [ ] CI/CD: pytest läuft in Stage 1 (vor Build + Deploy)
```

> **Scaffold-Vorlage:** `platform/docs/templates/django_test_scaffold/`
> **Auto-PR:** `gh workflow run scaffold-tests.yml -f repo_name=<name>`

## Repos als Referenz

| Repo | Besonderheit | Vorlage für |
|------|-------------|-------------|
| `risk-hub` | Multi-Tenant, `tenant_id` fixture | Multi-Tenant Apps |
| `weltenhub` | DRF APIClient, Cross-Tenant-Tests | API-Apps |
| `travel-beat` | Custom User Model, Celery-Tests | Consumer Apps |
| `wedding-hub` | Domain-spezifische Fixtures (org, event, guest) | Event-Apps |
| `mcp-hub` | Kein Django, nur Assertion-Helpers | Python-Libraries |
