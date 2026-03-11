---
status: "accepted"
date: 2026-02-20
amended: 2026-02-20
decision-makers: [Achim Dehnert]
consulted: []
informed: []
implementation_status: partial
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
    "-n auto",
    "--dist=loadscope",
    "--randomly-seed=last",
]
markers = [
    "unit: Unit tests (no DB, no external services)",
    "integration: Integration tests (DB required)",
    "contract: Contract tests (Schemathesis, run on main only)",
    "slow: Slow tests (skipped by default in dev)",
]
```

> **`--dist=loadscope`**: Required when using `pytest-xdist` with PostgreSQL — prevents DB race conditions by keeping tests from the same module on the same worker.

### 2.3 Standard Test Settings (`config/settings/test.py`)

```python
from .base import *  # noqa: F401,F403

DEBUG = False

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "test_db"),
        "USER": os.environ.get("POSTGRES_USER", "test_user"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "test_pass"),
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

DEFAULT_FILE_STORAGE = "django.core.files.storage.InMemoryStorage"

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

SECURE_SSL_REDIRECT = False
REST_FRAMEWORK = {**globals().get("REST_FRAMEWORK", {}), "DEFAULT_THROTTLE_CLASSES": []}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {"null": {"class": "logging.NullHandler"}},
    "root": {"handlers": ["null"], "level": "CRITICAL"},
}
```

### 2.4 Test Pyramid Ratios (Django-specific)

| Level | Ratio | Examples |
| --- | --- | --- |
| Unit | 40% | Model methods, validators, service functions, pure Python |
| Integration | 45% | Views (Django test client), HTMX fragments, N+1 checks |
| Contract | 10% | Schemathesis API, DB view schema, Celery payload |
| E2E/Smoke | 5% | Post-deploy smoke test script |

> **Django-specific rationale**: Integration tests (views + DB) are cheap in Django because `TestCase` wraps each test in a transaction — no teardown overhead. The 40/45 split reflects this.

### 2.5 Base Fixtures (`tests/conftest.py`)

```python
import pytest

@pytest.fixture
def user(db):
    from tests.factories import UserFactory
    return UserFactory()

@pytest.fixture
def admin_user(db):
    from tests.factories import UserFactory
    return UserFactory(is_staff=True, is_superuser=True)

@pytest.fixture
def authenticated_client(client, user):
    client.force_login(user)
    return client
```

### 2.6 HTMX Fragment Test Pattern

```python
from bs4 import BeautifulSoup

@pytest.mark.django_db
def test_should_render_stop_list_fragment(authenticated_client, trip):
    response = authenticated_client.get(
        f"/trips/{trip.pk}/stops/",
        HTTP_HX_REQUEST="true",
    )
    assert response.status_code == 200
    soup = BeautifulSoup(response.content, "html.parser")
    assert soup.find("ul", {"id": "stop-list"}) is not None

@pytest.mark.django_db
@pytest.mark.integration
def test_should_not_n_plus_one_on_stop_list(authenticated_client, trip, django_assert_num_queries):
    from tests.factories import StopFactory
    StopFactory.create_batch(5, trip=trip)
    with django_assert_num_queries(3):
        authenticated_client.get(f"/trips/{trip.pk}/stops/", HTTP_HX_REQUEST="true")
```

### 2.7 Schemathesis Contract Test Pattern

```python
# tests/contracts/test_api_contract.py
import pytest
import schemathesis
from django.test import Client

@pytest.fixture
def app():
    from config.wsgi import application
    return application

@pytest.mark.contract
@pytest.mark.django_db(transaction=True)
def test_should_api_conform_to_openapi_schema(app, user):
    schema = schemathesis.from_wsgi("/api/schema/?format=json", app)

    @schema.parametrize()
    def test_api(case):
        client = Client()
        client.force_login(user)
        response = case.call_wsgi(app)
        case.validate_response(response)

    test_api()
```

> **WSGI injection**: `schemathesis.from_wsgi()` injects directly into the Django WSGI app — no running server required in CI.

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

> **Last updated**: 2026-02-20 — Phase 1 + Phase 2 complete for all 7 service repos.

### Phase 1 — Test Infrastructure

| Item | weltenhub | travel-beat | bfagent | risk-hub | cad-hub | trading-hub | pptx-hub |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `requirements-test.txt` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (via pyproject) |
| `pytest.ini` / `pyproject.toml` pytest config | ✅ | ✅ | ✅ | ✅ | ✅ | — (existing) | ✅ (existing) |
| `config/settings/test.py` | ✅ | ✅ | ✅ | ✅ (settings_test.py) | ✅ | — (own module) | n/a |
| `tests/conftest.py` + `tests/factories.py` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (existing) |
| CI wired to `_ci-python.yml@main` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — (PyPI publish, no Django) |

### Phase 2 — Model + View Tests

| Item | weltenhub | travel-beat | bfagent | risk-hub | cad-hub | trading-hub | pptx-hub |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Model tests (core models) | ✅ World/Tenant | ✅ Trip/Stop/Transport | ✅ BookProject | ✅ Assessment/Hazard | ✅ (view tests) | — | n/a |
| View tests (login, ownership, N+1) | ✅ DRF API | ✅ HTMX views | ✅ Django views | — | ✅ | — | n/a |
| Property tests (`@property` methods) | — | ✅ duration_days, reading_minutes | — | ✅ risk_score | — | — | n/a |
| Schemathesis contract test | ✅ | — | — | — | — | — | n/a |
| Coverage target 50% reached | 🔴 | 🔴 | 🔴 | 🔴 | 🔴 | 🔴 | 🔴 |

### Phase 3 — Contract Tests (pending)

| Item | Status |
| --- | --- |
| `openapi.yaml` für alle API-anbietenden Services | 🔴 Not started |
| Schemathesis Provider-Tests via WSGI pro API-Service | 🔴 Not started |
| `platform/shared_contracts/task_schemas.py` erstellen | ✅ Done |
| `platform/shared_contracts/db_views.py` erstellen | ✅ Done |
| JSON Schema Validation in Celery Sender/Empfänger | 🔴 Not started |
| DB View Contract Tests (Provider + Consumer, `transaction=True`) | 🔴 Not started |
| Wöchentlicher Spec-Sync-Check Workflow | 🔴 Not started |

### Phase 4 — Hardening (pending)

| Item | Status |
| --- | --- |
| `scripts/smoke-test.sh` mit parametrisiertem `LOGIN_PATH` | ✅ Done (platform/scripts/) |
| Coverage Gate 70% aktivieren (`fail_under = 70`) | 🔴 Not started |
| pytest-xdist + pytest-randomly aktivieren | 🔴 Not started |

### Repo-spezifische Besonderheiten

| Repo | Besonderheit |
| --- | --- |
| **risk-hub** | `src/`-Layout; Settings monolithisch (`config/settings.py` → `config/settings_test.py`); SQLite für Unit-Tests |
| **cad-hub** | `apps/`-Layout; `config/settings/test.py` (split); `django_tenancy` Middleware |
| **trading-hub** | `src/trading_hub/`-Layout; eigenes Settings-Modul `trading_hub.django.settings`; TimescaleDB (Integration-Tests brauchen timescaledb Image) |
| **pptx-hub** | Python-Package (kein Django); eigene `ci.yml` mit `uv`/PyPI-Publish; kein `pytest-django` nötig |
| **weltenhub** | Multi-Tenant (UUID FK); DRF API ViewSets; Schemathesis Contract-Test vorhanden |
| **travel-beat** | Custom `AUTH_USER_MODEL = accounts.User`; HTMX Views; allauth |
| **bfagent** | Standard Django auth; kein HTMX; `src/`-Layout mit `apps/bfagent/` |

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
