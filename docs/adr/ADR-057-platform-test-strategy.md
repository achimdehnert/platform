---
status: "accepted"
date: 2026-02-20
amended: 2026-02-20
decision-makers: [Achim Dehnert]
consulted: []
informed: []
---

# Adopt a four-level test strategy with contract testing to systematically cover multi-repo Django/HTMX services

> **Input**: `docs/adr/inputs/ADR-057-teststrategie-konzeptpapier.md` (2026-02-20)
> **Amendment**: Deep review findings applied 2026-02-20 — see §4 for changes.

---

## Context and Problem Statement

The platform consists of 7+ Django service repos (bfagent, travel-beat, weltenhub, risk-hub, cad-hub, trading-hub, pptx-hub) with no unified test strategy. Individual unit tests exist in some repos but there are no shared conventions, no CI integration of tests, and no coverage measurement.

More critically, the services communicate over three channels that are currently completely untested:

1. **REST/JSON APIs** — Service A calls Service B. Schema changes in B break A silently.
2. **Shared Database Views** — Service A reads views owned by Service B. Column renames break A in production.
3. **Celery Tasks cross-service** — Payload changes are invisible to the sender without a contract.

Additionally, the HTMX-heavy frontend (server-rendered HTML fragments) requires a testing approach that does not rely on browser automation.

**Current state**: ~0% systematic test coverage, no CI test gates, no contract verification between services.

---

## Decision Drivers

* **Effectiveness**: Catch the bugs that actually occur in production (cross-service contract breaks, view regressions)
* **Efficiency**: Total CI runtime < 5 minutes — no external infrastructure required
* **Automation**: Fully integrated into existing GitHub Actions CI pipeline
* **Pragmatism**: Implementable by a 1–3 person team without enterprise tooling
* **Incrementalism**: From zero to full coverage in four defined phases over 14 weeks

---

## Considered Options

1. **Status quo** — no systematic testing, fix bugs reactively
2. **Unit + Integration tests only** — pytest + pytest-django, no contract layer
3. **Full test pyramid with contract tests (Schemathesis)** — four levels including cross-service contract verification
4. **Full test pyramid with Pact (Consumer-Driven Contract Testing)** — Pact Broker as additional infrastructure
5. **Browser-based E2E tests (Playwright/Selenium)** — full browser automation as primary test strategy

---

## Decision Outcome

**Chosen option: 3 — Full test pyramid with Schemathesis**, because:

- Option 1 is rejected — cross-service contract breaks are the highest-risk failure class and are invisible without contracts.
- Option 2 is insufficient — does not address the three cross-service communication channels.
- Option 3 provides contract testing without additional infrastructure (Schemathesis uses existing OpenAPI specs via WSGI) and is optimal for a small team.
- Option 4 (Pact) is rejected — requires a Pact Broker as additional service. Schemathesis achieves 80% of the value with 20% of the overhead. Tracked as ADR-05x for future evaluation.
- Option 5 (Playwright) is rejected as primary strategy — too slow, too many flaky tests. Django Test Client + BeautifulSoup covers 95% of HTMX scenarios at 100x the speed. Reserved for JavaScript-heavy interactions only (Phase 4+).

### Confirmation

Compliance is verified by:

1. **CI gate**: `pytest --cov` runs on every push — build fails if tests fail.
2. **Coverage merge**: Unit and integration jobs upload separate `.xml` artifacts; `coverage-report` job merges via `coverage combine`.
3. **Coverage gate**: 30% (Phase 1, report only) → 50% (Phase 2, warning) → 70% (Phase 3, CI gate) → 80% (long-term).
4. **Contract spec freshness**: Scheduled weekly workflow checks consumer-side OpenAPI spec copies against provider.
5. **ADR-054 Architecture Guardian**: Verifies `pytest.ini_options` in `pyproject.toml`, `DJANGO_SETTINGS_MODULE = "config.settings.test"`, and `--dist=loadscope` present when `pytest-xdist` is used.

### Consequences

* Good, because all three cross-service channels are contractually verified (REST via Schemathesis, DB Views via schema assertions, Celery via JSON Schema).
* Good, because HTMX views are testable without browser automation — Django Test Client + BeautifulSoup is 100x faster than Selenium.
* Good, because Schemathesis uses WSGI injection — no running server needed in CI, more reliable than `base_url`.
* Good, because `pytest-xdist` with `--dist=loadscope` parallelises tests safely without DB race conditions.
* Good, because coverage is correctly merged across parallel CI jobs via artifact combine.
* Bad, because Phase 3 requires all API-providing services to maintain OpenAPI specs.
* Bad, because `shared_contracts` package (task schemas + DB view schemas) must be created and maintained.
* Bad, because factory-boy factories must be written for all major models — upfront investment in Phase 1.
* Bad, because `@pytest.mark.django_db(transaction=True)` is required for cross-service DB view tests — slower than standard TestCase.

---

## Pros and Cons of the Options

### Option 1 — Status quo

* Good, because zero effort.
* Bad, because cross-service contract breaks are invisible until production.
* Bad, because no quality gate — regressions accumulate silently.

### Option 2 — Unit + Integration only

* Good, because simpler setup, no contract infrastructure.
* Good, because covers intra-service bugs effectively.
* Bad, because the three cross-service channels remain unverified.
* Bad, because HTMX view regressions are not caught.

### Option 3 — Full pyramid with Schemathesis (chosen)

* Good, because covers all four test levels including cross-service contracts.
* Good, because no additional infrastructure — Schemathesis uses existing OpenAPI specs via WSGI.
* Good, because property-based test generation from specs catches edge cases automatically.
* Good, because BeautifulSoup-based HTMX testing is fast and reliable.
* Bad, because requires OpenAPI spec discipline from all API providers.
* Bad, because `shared_contracts` package adds a cross-repo dependency.

### Option 4 — Pact (Consumer-Driven Contract Testing)

* Good, because bidirectional — both consumer and provider are verified.
* Good, because polyglot — works across languages.
* Bad, because requires Pact Broker as additional service to operate and maintain.
* Bad, because overengineered for a 1–3 person team.
* **Rejected** — tracked as ADR-05x for evaluation when team grows beyond 5 people.

### Option 5 — Playwright/Selenium as primary strategy

* Good, because tests the full browser experience including JavaScript.
* Bad, because slow (minutes per test), flaky, high maintenance overhead.
* Bad, because overkill for HTMX which renders server-side.
* **Rejected** as primary strategy — reserved for JavaScript-heavy interactions only (Phase 4+).

---

## More Information

- **Input document**: `docs/adr/inputs/ADR-057-teststrategie-konzeptpapier.md`
- **Related ADRs**: ADR-022 (code quality tooling — ruff, pip-audit already in CI), ADR-056 (CI/CD pipeline hardening), ADR-054 (architecture guardian)
- **Deferred**: ADR-05x — Pact Consumer-Driven Contract Testing (evaluate when team > 5 people)
- **Schemathesis docs**: https://schemathesis.readthedocs.io/
- **Reference**: Harry Percival, "Test-Driven Development with Python" — https://www.obeythetestinggoat.com/

---

## 2. Implementation Details

### 2.1 Tooling Stack

| Tool | Version | Purpose | Use Case |
| --- | --- | --- | --- |
| `pytest` | ≥8.0 | Test runner | All |
| `pytest-django` | ≥4.8 | Django integration, DB fixtures | All |
| `pytest-cov` | ≥5.0 | Coverage measurement | All |
| `pytest-xdist` | ≥3.5 | Parallel execution (`-n auto --dist=loadscope`) | All |
| `pytest-randomly` | ≥3.15 | Test order randomisation — detects order dependencies | All |
| `factory-boy` | ≥3.3 | Declarative test data factories | All |
| `responses` | ≥0.25 | HTTP mocking for `requests`-based clients | REST clients |
| `respx` | ≥0.21 | HTTP mocking for `httpx`-based async clients | Async REST clients |
| `schemathesis` | ≥3.30 | Contract testing via WSGI — no running server needed | Contract |
| `jsonschema` | ≥4.21 | Celery task payload + DB view schema validation | Contract |
| `beautifulsoup4` | ≥4.12 | HTMX fragment assertion without browser | Integration |
| `pip-audit` | ≥2.7 | Security scan (already in CI via ADR-022) | Security |

> **`responses` vs `respx`**: Use `responses` for services using the `requests` library. Use `respx` for services using `httpx` (async Django views, ASGI apps). Both can coexist in the same repo.

**`requirements-test.txt` per service repo** (standardised):

```
pytest>=8.0
pytest-django>=4.8
pytest-cov>=5.0
pytest-xdist>=3.5
pytest-randomly>=3.15
factory-boy>=3.3
responses>=0.25
respx>=0.21
schemathesis>=3.30
jsonschema>=4.21
beautifulsoup4>=4.12
```

### 2.2 Standard pytest Configuration (per service repo)

```toml
# pyproject.toml
[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "config.settings.test"
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "--strict-markers",
    "--tb=short",
    "-ra",
    "--no-header",
    "-n auto",               # pytest-xdist: parallel execution
    "--dist=loadscope",      # Tests in same class on same worker — prevents DB race conditions with postgres
    "--randomly-seed=last",  # Reproduce last failing order: pytest --randomly-seed=last
]
markers = [
    "slow: Tests die > 1s dauern",
    "contract: Contract Tests gegen andere Services",
    "integration: Tests die DB oder externe Services brauchen",
]
filterwarnings = [
    "error",
    "ignore::DeprecationWarning:django.*:",
]

[tool.coverage.run]
source = ["apps"]
omit = [
    "*/migrations/*",
    "*/admin.py",
    "*/apps.py",
    "*/tests/*",
    "config/*",
    "manage.py",
]

[tool.coverage.report]
fail_under = 0    # Phase 1: kein Gate, nur Report
show_missing = true
```

### 2.3 Standard `config/settings/test.py` (per service repo)

```python
# config/settings/test.py
import os
from .base import *  # noqa: F401, F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "test_db",
        "USER": "test_user",
        "PASSWORD": "test_pass",
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": "5432",
    }
}

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
```

### 2.4 Test Pyramid — Django-adjusted Ratios

> In Django, any test using `@pytest.mark.django_db` is technically an integration test. Ratios reflect Django reality, not classical theory (ref: Harry Percival, "Obey the Testing Goat").

| Level | Ratio | Runtime budget | Trigger |
| --- | --- | --- | --- |
| Unit (no DB) | ~40% | < 30s | Every push |
| Integration (with DB) | ~45% | < 2 min | Every push |
| Contract | ~10% | < 1 min | Push to `main` only |
| E2E / Smoke | ~5% | < 2 min | Post-deployment |

**Unit** = Models (validators, properties, `__str__`), Forms, Utils, Serializers, Template Tags — no `@pytest.mark.django_db`.

**Integration** = Views (full request-response cycle), QuerySets, Celery tasks (intra-service), HTMX fragments.

### 2.5 Global Fixtures and Factory Pattern

```python
# tests/conftest.py
import pytest
from tests.factories import UserFactory, AssessmentFactory

@pytest.fixture
def user(db):
    return UserFactory()

@pytest.fixture
def admin_user(db):
    return UserFactory(is_staff=True, is_superuser=True)

@pytest.fixture
def authenticated_client(client, user):
    client.force_login(user)
    return client
```

```python
# tests/factories.py
import factory
from apps.core.models import User, Assessment

class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
    username = factory.Sequence(lambda n: f"user_{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    is_active = True

class AssessmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Assessment
    title = factory.Faker("sentence", nb_words=4)
    created_by = factory.SubFactory(UserFactory)
    status = "draft"
```

### 2.6 HTMX View Testing Pattern

```python
import pytest
from bs4 import BeautifulSoup

@pytest.mark.django_db
class TestAssessmentListView:

    def test_authenticated_user_sees_own_assessments(self, authenticated_client, user):
        from tests.factories import AssessmentFactory
        AssessmentFactory(created_by=user, title="Mein Assessment")
        AssessmentFactory()  # other user — must not appear

        response = authenticated_client.get("/assessments/")

        assert response.status_code == 200
        soup = BeautifulSoup(response.content, "html.parser")
        rows = soup.select("table tbody tr")
        assert len(rows) == 1
        assert "Mein Assessment" in rows[0].text

    def test_unauthenticated_user_is_redirected(self, client):
        response = client.get("/assessments/")
        assert response.status_code == 302
        assert "/login/" in response.url

    def test_htmx_partial_returns_fragment(self, authenticated_client):
        response = authenticated_client.get(
            "/assessments/",
            HTTP_HX_REQUEST="true",
            HTTP_HX_TARGET="assessment-list",
        )
        assert response.status_code == 200
        assert b"<html" not in response.content
        assert BeautifulSoup(response.content, "html.parser").select_one("#assessment-list") is not None

    def test_list_view_does_not_trigger_n_plus_one(self, authenticated_client, django_assert_num_queries):
        from tests.factories import AssessmentFactory
        AssessmentFactory.create_batch(10)
        with django_assert_num_queries(3):  # adjust to actual baseline
            authenticated_client.get("/assessments/")
```

### 2.7 Contract Testing — REST/JSON APIs (Schemathesis via WSGI)

> **Critical**: Use `app=` to inject the WSGI app directly — no running server needed in CI.

```python
# tests/contracts/test_api_provider.py
import schemathesis
from config.wsgi import application

schema = schemathesis.from_path("openapi.yaml", app=application)

@schema.parametrize()
def test_api_conforms_to_spec(case):
    response = case.call_and_validate()
```

Consumer side uses `responses` (sync) or `respx` (async) to mock the provider.

**Spec freshness check** (weekly scheduled workflow):

```yaml
on:
  schedule:
    - cron: "0 6 * * 1"
jobs:
  check-specs:
    runs-on: self-hosted
    steps:
      - uses: actions/checkout@v4
      - run: |
          curl -sf https://raw.githubusercontent.com/achimdehnert/<provider>/main/openapi.yaml \
            -o /tmp/latest-spec.yaml
          diff tests/contracts/specs/<provider>-openapi.yaml /tmp/latest-spec.yaml \
            || (echo "::warning::API spec outdated" && exit 1)
```

### 2.8 Contract Testing — Shared Database Views

**Versioning**: DB view schemas versioned as Python dicts in `platform/shared_contracts/db_views.py`. View owner updates on schema change; consumers test against it.

```python
# platform/shared_contracts/db_views.py
VIEW_CONTRACTS = {
    "v_active_assessments": {
        "owner": "risk-hub",
        "version": "1.0.0",
        "columns": {
            "id": "integer",
            "title": "character varying",
            "status": "character varying",
            "created_at": "timestamp with time zone",
            "zone_count": "integer",
        },
    },
}
```

**Provider test**:

```python
# tests/contracts/test_db_view_contract.py
import pytest
from django.db import connection
from shared_contracts.db_views import VIEW_CONTRACTS

@pytest.mark.django_db
def test_v_active_assessments_schema_matches_contract():
    contract = VIEW_CONTRACTS["v_active_assessments"]
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_name = %s ORDER BY ordinal_position",
            ["v_active_assessments"],
        )
        actual = {row[0]: row[1] for row in cursor.fetchall()}
    for col_name, col_type in contract["columns"].items():
        assert col_name in actual, f"Column '{col_name}' missing from view"
        assert actual[col_name] == col_type
```

**Consumer test**:

```python
# tests/contracts/test_db_view_consumer.py
import pytest

@pytest.mark.django_db(transaction=True)
def test_query_against_view_schema():
    # conftest creates a fake view matching the contract schema
    from apps.reporting.queries import get_active_assessments
    results = get_active_assessments()
    assert hasattr(results[0], "title")
    assert hasattr(results[0], "zone_count")
```

> **`transaction=True`**: Cross-service DB view tests require `@pytest.mark.django_db(transaction=True)` — standard `TestCase` wraps everything in a transaction invisible to other connections.

### 2.9 Contract Testing — Celery Task Payloads

```python
# platform/shared_contracts/task_schemas.py
TASK_SCHEMAS = {
    "generate_zone_report": {
        "type": "object",
        "required": ["assessment_id", "zone_ids", "requested_by"],
        "properties": {
            "assessment_id": {"type": "integer"},
            "zone_ids": {"type": "array", "items": {"type": "integer"}},
            "requested_by": {"type": "string", "format": "email"},
        },
        "additionalProperties": False,
    },
}
```

Both sender and receiver validate via `jsonschema.validate(payload, TASK_SCHEMAS["..."])`.

### 2.10 CI Pipeline Integration

> **Coverage merge**: Unit and integration jobs run in parallel, upload separate XML artifacts. `coverage-report` job merges them.

```yaml
jobs:
  lint:
    runs-on: self-hosted
    steps:
      - uses: actions/checkout@v4
      - run: ruff check . && ruff format --check .

  test-unit:
    runs-on: self-hosted
    needs: lint
    steps:
      - uses: actions/checkout@v4
      - run: pip install -r requirements.txt -r requirements-test.txt
      - run: pytest -m "not integration and not contract and not slow" --cov --cov-report=xml:coverage-unit.xml
      - uses: actions/upload-artifact@v4
        with: { name: coverage-unit, path: coverage-unit.xml }

  test-integration:
    runs-on: self-hosted
    needs: lint
    services:
      postgres:
        image: postgres:16
        env: { POSTGRES_DB: test_db, POSTGRES_USER: test_user, POSTGRES_PASSWORD: test_pass }
        ports: ["5432:5432"]
        options: --health-cmd pg_isready --health-interval 5s --health-retries 5
      redis:
        image: redis:7
        ports: ["6379:6379"]
    steps:
      - uses: actions/checkout@v4
      - run: pip install -r requirements.txt -r requirements-test.txt
      - run: pytest -m "integration" --cov --cov-report=xml:coverage-integration.xml
      - uses: actions/upload-artifact@v4
        with: { name: coverage-integration, path: coverage-integration.xml }

  coverage-report:
    runs-on: self-hosted
    needs: [test-unit, test-integration]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with: { name: coverage-unit }
      - uses: actions/download-artifact@v4
        with: { name: coverage-integration }
      - run: pip install coverage && coverage combine coverage-unit.xml coverage-integration.xml && coverage report

  test-contract:
    runs-on: self-hosted
    needs: [test-unit, test-integration]
    if: github.ref == 'refs/heads/main'
    services:
      postgres:
        image: postgres:16
        env: { POSTGRES_DB: test_db, POSTGRES_USER: test_user, POSTGRES_PASSWORD: test_pass }
        ports: ["5432:5432"]
        options: --health-cmd pg_isready --health-interval 5s --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - run: pip install -r requirements.txt -r requirements-test.txt
      - run: pytest -m "contract"

  security:
    runs-on: self-hosted
    needs: lint
    steps:
      - uses: actions/checkout@v4
      - run: pip-audit -r requirements.txt
```

### 2.11 Smoke Test Script

```bash
#!/usr/bin/env bash
# scripts/smoke-test.sh
# Usage: ./scripts/smoke-test.sh <base-url> [login-path]
# login-path default: /accounts/login/ (allauth); bfagent uses /login/
set -euo pipefail

BASE_URL="${1:?Usage: smoke-test.sh <base-url> [login-path]}"
LOGIN_PATH="${2:-/accounts/login/}"

echo "=== Smoke Tests: ${BASE_URL} ==="
curl --fail --silent -o /dev/null "${BASE_URL}/livez/"    && echo "✓ /livez/" || exit 1
curl --fail --silent -o /dev/null "${BASE_URL}/"          && echo "✓ /" || exit 1
curl --fail --silent "${BASE_URL}${LOGIN_PATH}" \
  | grep -q "csrfmiddlewaretoken"                         && echo "✓ CSRF token" || exit 1
echo "=== All smoke tests passed ==="
```

---

## 3. Migration Tracking

| Item | Status | Phase |
| --- | --- | --- |
| `requirements-test.txt` standardisiert in allen Service-Repos | 🔴 Not started | 1 |
| `pyproject.toml` pytest-Konfiguration (§2.2 Template) in allen Repos | 🔴 Not started | 1 |
| `config/settings/test.py` (§2.3 Template) in allen Repos erstellen | 🔴 Not started | 1 |
| `tests/conftest.py` + `tests/factories.py` Basis in allen Repos | 🔴 Not started | 1 |
| `_ci-python.yml` um test-unit + test-integration + coverage-report + security Jobs erweitern | 🔴 Not started | 1 |
| View-Tests für Top-10-Views pro Service (inkl. HTMX + N+1-Check) | 🔴 Not started | 2 |
| Model-Tests für alle Custom Validatoren und Manager | 🔴 Not started | 2 |
| Coverage-Ziel 50% erreicht | 🔴 Not started | 2 |
| `openapi.yaml` für alle API-anbietenden Services | 🔴 Not started | 3 |
| Schemathesis Provider-Tests via WSGI pro API-Service | 🔴 Not started | 3 |
| `platform/shared_contracts/task_schemas.py` erstellen | 🔴 Not started | 3 |
| `platform/shared_contracts/db_views.py` erstellen | 🔴 Not started | 3 |
| JSON Schema Validation in Celery Sender/Empfänger | 🔴 Not started | 3 |
| DB View Contract Tests (Provider + Consumer, `transaction=True`) | 🔴 Not started | 3 |
| Wöchentlicher Spec-Sync-Check Workflow | 🔴 Not started | 3 |
| `scripts/smoke-test.sh` mit parametrisiertem `LOGIN_PATH` | 🔴 Not started | 4 |
| Coverage Gate 70% aktivieren (`fail_under = 70`) | 🔴 Not started | 4 |
| pytest-xdist + pytest-randomly aktivieren | 🔴 Not started | 4 |

---

## 4. Review Amendments (2026-02-20)

Applied after deep review against `docs/templates/adr-review-checklist.md` + established best practices:

| # | Finding | Fix applied |
| --- | --- | --- |
| R1 | `pytest -n auto` + PostgreSQL causes race conditions without `--dist=loadscope` | Added `--dist=loadscope` to `addopts` in §2.2 |
| R2 | `--cov-append` across separate CI jobs does not work — coverage lost | Replaced with per-job XML artifacts + `coverage combine` in `coverage-report` job (§2.10) |
| R3 | Schemathesis used `base_url=` requiring a running server | Changed to `app=application` (WSGI injection) in §2.7 |
| R4 | DB-View-Contract code and versioning decision missing from §2 | Added §2.8 with `shared_contracts/db_views.py`, provider test, consumer test, `transaction=True` note |
| R5 | `config/settings/test.py` content not specified | Added §2.3 with standard template (MD5 hasher, locmem email, eager Celery, InMemoryStorage) |
| R6 | `pytest-randomly` missing `--randomly-seed=last` for debugging | Added to `addopts` in §2.2 |
| R7 | Smoke test `/accounts/login/` not universal (bfagent uses `/login/`) | Added `LOGIN_PATH` parameter to `smoke-test.sh` (§2.11) |
| R8 | `httpx` vs `requests` mocking decision missing | Added `respx` to tooling stack with explicit use-case distinction (§2.1) |
| R9 | Factory fixtures not shown as `@pytest.fixture` — boilerplate in tests | Added `tests/conftest.py` fixture pattern in §2.5 |
| R10 | `assertNumQueries` / N+1 detection not mentioned | Added `django_assert_num_queries` example to HTMX test pattern (§2.6) |
| R11 | Pact deferred without ADR placeholder | Added "ADR-05x" reference in Decision Outcome and More Information |
| R12 | Test pyramid ratio 60/25/10/5 not Django-appropriate | Adjusted to 40/45/10/5 with Django-specific rationale (§2.4) |
