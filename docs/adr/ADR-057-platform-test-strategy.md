---
status: "proposed"
date: 2026-02-20
decision-makers: [Achim Dehnert]
consulted: []
informed: []
---

# Adopt a four-level test strategy with contract testing to systematically cover multi-repo Django/HTMX services

> **Input**: `docs/adr/inputs/ADR-057-teststrategie-konzeptpapier.md` (2026-02-20)

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
- Option 3 provides contract testing without additional infrastructure (Schemathesis uses existing OpenAPI specs) and is optimal for a small team.
- Option 4 (Pact) is rejected — requires a Pact Broker as additional service to operate. Schemathesis achieves 80% of the value with 20% of the overhead. Pact can be adopted later if the team grows.
- Option 5 (Playwright) is rejected as primary strategy — too slow, too many flaky tests, too much maintenance overhead. Django Test Client + BeautifulSoup covers 95% of HTMX scenarios at 100x the speed. Playwright is reserved for JavaScript-heavy interactions only (Phase 4+).

### Confirmation

Compliance is verified by:

1. **CI gate**: `pytest --cov` runs on every push — build fails if tests fail.
2. **Coverage report**: Coverage XML uploaded as CI artifact on every push.
3. **Coverage gate**: Enforced progressively — 30% (Phase 1, report only) → 50% (Phase 2, warning) → 70% (Phase 3, CI gate) → 80% (long-term).
4. **Contract spec freshness**: Scheduled weekly workflow checks that consumer-side OpenAPI spec copies are up to date with provider.
5. **ADR-054 Architecture Guardian**: Verifies `pytest.ini_options` present in `pyproject.toml` and `DJANGO_SETTINGS_MODULE = "config.settings.test"` set.

### Consequences

* Good, because all three cross-service communication channels are contractually verified.
* Good, because HTMX views are testable without browser automation — Django Test Client + BeautifulSoup is 100x faster than Selenium.
* Good, because the four-phase roadmap allows incremental adoption — Phase 1 delivers value in week 2.
* Good, because Schemathesis generates tests automatically from existing OpenAPI specs — no manual test writing for contract layer.
* Good, because `pytest-xdist` parallelises tests across CPU cores — keeps CI runtime under 5 minutes even at 80% coverage.
* Bad, because Phase 3 (contract tests) requires all API-providing services to maintain OpenAPI specs — additional discipline required.
* Bad, because `shared-libs/shared_contracts/` package must be created and maintained for Celery task schemas.
* Bad, because factory-boy factories must be written for all major models — upfront investment in Phase 1.

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
* Good, because no additional infrastructure — Schemathesis uses existing OpenAPI specs.
* Good, because property-based test generation from specs catches edge cases automatically.
* Good, because BeautifulSoup-based HTMX testing is fast and reliable.
* Bad, because requires OpenAPI spec discipline from all API providers.
* Bad, because `shared_contracts` package adds a cross-repo dependency.

### Option 4 — Pact (Consumer-Driven Contract Testing)

* Good, because bidirectional — both consumer and provider are verified.
* Good, because polyglot — works across languages.
* Bad, because requires Pact Broker as additional service to operate and maintain.
* Bad, because overengineered for a 1–3 person team.
* **Rejected** — can be adopted later if team grows beyond 5 people.

### Option 5 — Playwright/Selenium as primary strategy

* Good, because tests the full browser experience including JavaScript.
* Bad, because slow (minutes per test), flaky, high maintenance overhead.
* Bad, because overkill for HTMX which renders server-side.
* **Rejected** as primary strategy — reserved for JavaScript-heavy interactions only.

---

## More Information

- **Input document**: `docs/adr/inputs/ADR-057-teststrategie-konzeptpapier.md`
- **Related ADRs**: ADR-022 (code quality tooling — ruff, pip-audit already in CI), ADR-056 (CI/CD pipeline hardening), ADR-054 (architecture guardian)
- **Schemathesis docs**: https://schemathesis.readthedocs.io/
- **Pact (future option)**: https://docs.pact.io/ — evaluate when team > 5 people

---

## 2. Implementation Details

### 2.1 Tooling Stack

| Tool | Version | Purpose |
| --- | --- | --- |
| `pytest` | ≥8.0 | Test runner |
| `pytest-django` | ≥4.8 | Django integration, DB fixtures |
| `pytest-cov` | ≥5.0 | Coverage measurement |
| `pytest-xdist` | ≥3.5 | Parallel execution (`-n auto`) |
| `pytest-randomly` | ≥3.15 | Test order randomisation — detects order dependencies |
| `factory-boy` | ≥3.3 | Declarative test data factories |
| `responses` | ≥0.25 | HTTP mocking for outgoing REST calls |
| `schemathesis` | ≥3.30 | Contract testing from OpenAPI spec |
| `jsonschema` | ≥4.21 | Celery task payload validation |
| `beautifulsoup4` | ≥4.12 | HTMX fragment assertion without browser |
| `pip-audit` | ≥2.7 | Security scan (already in CI via ADR-022) |

**`requirements-test.txt` per service repo** (standardised):

```
pytest>=8.0
pytest-django>=4.8
pytest-cov>=5.0
pytest-xdist>=3.5
pytest-randomly>=3.15
factory-boy>=3.3
responses>=0.25
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

### 2.3 Directory Structure (per service repo)

```
<service>/
├── apps/
│   └── <app>/
│       └── tests/
│           ├── __init__.py
│           ├── conftest.py
│           ├── test_models.py
│           ├── test_forms.py
│           ├── test_views.py
│           └── test_utils.py
├── tests/
│   ├── conftest.py          # Global fixtures
│   ├── factories.py         # factory-boy factories
│   └── contracts/
│       ├── test_api_contract.py      # Schemathesis provider tests
│       └── specs/
│           └── <other-service>-openapi.yaml  # Consumer-side spec copies
├── pyproject.toml
└── openapi.yaml             # This service's API spec (if API provider)
```

### 2.4 Naming Convention

```python
# ✅ Correct: describes behaviour
def test_user_cannot_register_with_existing_email(): ...
def test_htmx_partial_returns_fragment_not_full_page(): ...
def test_expired_assessment_returns_inactive_status(): ...

# ❌ Wrong: too generic
def test_model(): ...
def test_save(): ...
```

### 2.5 HTMX View Testing Pattern

```python
import pytest
from bs4 import BeautifulSoup
from tests.factories import UserFactory, AssessmentFactory

@pytest.mark.django_db
class TestAssessmentListView:

    def test_authenticated_user_sees_own_assessments(self, client):
        user = UserFactory()
        AssessmentFactory(created_by=user, title="Mein Assessment")
        AssessmentFactory()  # other user — must not appear

        client.force_login(user)
        response = client.get("/assessments/")

        assert response.status_code == 200
        soup = BeautifulSoup(response.content, "html.parser")
        rows = soup.select("table tbody tr")
        assert len(rows) == 1
        assert "Mein Assessment" in rows[0].text

    def test_htmx_partial_returns_fragment(self, client):
        user = UserFactory()
        client.force_login(user)

        response = client.get(
            "/assessments/",
            HTTP_HX_REQUEST="true",
            HTTP_HX_TARGET="assessment-list",
        )

        assert response.status_code == 200
        assert b"<html" not in response.content
        soup = BeautifulSoup(response.content, "html.parser")
        assert soup.select_one("#assessment-list") is not None
```

### 2.6 Contract Testing — REST/JSON APIs (Schemathesis)

**Provider side** (in the API-providing service repo):

```python
# tests/contracts/test_api_provider.py
import schemathesis

schema = schemathesis.from_path("openapi.yaml", base_url="http://localhost:8000")

@schema.parametrize()
def test_api_conforms_to_spec(case):
    response = case.call_and_validate()
```

**Consumer side** (in the calling service repo):

```python
# tests/contracts/test_<provider>_client.py
import responses

@responses.activate
def test_fetch_from_provider():
    responses.add(responses.GET, "http://provider:8000/api/v1/items/",
                  json={"results": [{"id": 1, "status": "active"}]}, status=200)
    from apps.integrations.provider_client import ProviderClient
    result = ProviderClient().get_items()
    assert result[0]["status"] == "active"
```

**Spec freshness check** (scheduled weekly):

```yaml
# .github/workflows/check-contract-specs.yml
on:
  schedule:
    - cron: "0 6 * * 1"
jobs:
  check-specs:
    runs-on: self-hosted
    steps:
      - uses: actions/checkout@v4
      - name: Compare specs with provider
        run: |
          curl -sf https://raw.githubusercontent.com/achimdehnert/<provider>/main/openapi.yaml \
            -o /tmp/latest-spec.yaml
          diff tests/contracts/specs/<provider>-openapi.yaml /tmp/latest-spec.yaml \
            || (echo "::warning::API spec outdated — update tests/contracts/specs/" && exit 1)
```

### 2.7 Contract Testing — Celery Task Payloads

Shared schemas in `platform/shared_contracts/task_schemas.py` (new package):

```python
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

Both sender and receiver validate against this schema using `jsonschema.validate()`.

### 2.8 CI Pipeline Integration

Extension of `_ci-python.yml` shared workflow:

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
    services:
      postgres:
        image: postgres:16
        env: { POSTGRES_DB: test_db, POSTGRES_USER: test_user, POSTGRES_PASSWORD: test_pass }
        ports: ["5432:5432"]
        options: --health-cmd pg_isready --health-interval 5s --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - run: pip install -r requirements.txt -r requirements-test.txt
      - run: pytest -m "not integration and not contract and not slow" --cov -n auto
      - run: coverage xml
      - uses: actions/upload-artifact@v4
        with: { name: coverage-report, path: coverage.xml }

  test-integration:
    runs-on: self-hosted
    needs: lint
    services:
      postgres: { ... }
      redis: { image: "redis:7", ports: ["6379:6379"] }
    steps:
      - uses: actions/checkout@v4
      - run: pip install -r requirements.txt -r requirements-test.txt
      - run: pytest -m "integration" --cov --cov-append

  test-contract:
    runs-on: self-hosted
    needs: [test-unit, test-integration]
    if: github.ref == 'refs/heads/main'
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

`lint`, `test-unit`, `test-integration`, `security` run in parallel. `test-contract` runs after unit+integration, on `main` only.

### 2.9 Smoke Test Script

```bash
# scripts/smoke-test.sh
BASE_URL="${1:?Usage: smoke-test.sh <base-url>}"
curl --fail -s -o /dev/null "${BASE_URL}/livez/"   || exit 1
curl --fail -s -o /dev/null "${BASE_URL}/"          || exit 1
curl --fail -s "${BASE_URL}/accounts/login/" | grep -q "csrfmiddlewaretoken" || exit 1
echo "Smoke tests passed"
```

---

## 3. Migration Tracking

| Item | Status | Phase |
| --- | --- | --- |
| `requirements-test.txt` standardisiert in allen Service-Repos | 🔴 Not started | 1 |
| `pyproject.toml` pytest-Konfiguration (§2.2 Template) in allen Repos | 🔴 Not started | 1 |
| `config/settings/test.py` in allen Repos erstellen | 🔴 Not started | 1 |
| `tests/conftest.py` + `tests/factories.py` Basis in allen Repos | 🔴 Not started | 1 |
| `_ci-python.yml` um test-unit + test-integration + security Jobs erweitern | 🔴 Not started | 1 |
| View-Tests für Top-10-Views pro Service (inkl. HTMX) | 🔴 Not started | 2 |
| Model-Tests für alle Custom Validatoren und Manager | 🔴 Not started | 2 |
| Coverage-Ziel 50% erreicht | 🔴 Not started | 2 |
| `openapi.yaml` für alle API-anbietenden Services | 🔴 Not started | 3 |
| Schemathesis Provider-Tests pro API-Service | 🔴 Not started | 3 |
| `platform/shared_contracts/task_schemas.py` erstellen | 🔴 Not started | 3 |
| JSON Schema Validation in Celery Sender/Empfänger | 🔴 Not started | 3 |
| Wöchentlicher Spec-Sync-Check Workflow | 🔴 Not started | 3 |
| `scripts/smoke-test.sh` + Post-Deploy-Integration | 🔴 Not started | 4 |
| Coverage Gate 70% aktivieren | 🔴 Not started | 4 |
| pytest-xdist + pytest-randomly aktivieren | 🔴 Not started | 4 |
