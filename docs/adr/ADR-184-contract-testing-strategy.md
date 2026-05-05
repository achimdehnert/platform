---
status: accepted
implementation_status: partial
date: 2026-04-02
amended: 2026-04-02
decision-makers: [Achim Dehnert]
consulted: []
informed: []
supersedes: []
related:
  - ADR-057-platform-test-strategy.md
  - ADR-058-platform-test-taxonomy.md
  - ADR-041-service-layer.md
  - ADR-076-bfagent-ci-test-strategy.md
  - ADR-022-code-quality.md
---

# ADR-155: Adopt a Three-Layer Contract Testing Strategy for All Function and Method Calls

## Metadaten

| Attribut          | Wert                                                                                      |
|-------------------|-------------------------------------------------------------------------------------------|
| **Status**        | Accepted                                                                                  |
| **Scope**         | platform-wide (alle Hubs, alle iil-Packages, alle Service-Layer, Celery Tasks, REST APIs) |
| **Erstellt**      | 2026-04-02                                                                                |
| **Autor**         | Achim Dehnert                                                                             |
| **Reviewer**      | Cascade (Principal IT-Architekt), Claude (Review-Befunde)                                                                                         |
| **Supersedes**    | –                                                                                         |
| **Superseded by** | –                                                                                         |
| **Relates to**    | ADR-041 (Service Layer), ADR-057 (Test Strategy), ADR-058 (Test Taxonomy), ADR-076 (bfagent CI), ADR-022 (Code Quality) |

## Repo-Zugehörigkeit

| Repo              | Rolle    | Betroffene Pfade / Komponenten                                              |
|-------------------|----------|-----------------------------------------------------------------------------|
| `iil-testkit`     | Primär   | `iil_testkit/contract/verifier.py`, `iil_testkit/contract/__init__.py`      |
| `platform_context`| Primär   | `platform_context/adapters/base.py`                                         |
| `bfagent`         | Consumer | `tests/contracts/`, `apps/*/adapters/`, `apps/*/services.py`                |
| alle Hub-Repos    | Consumer | `tests/contracts/`, `apps/*/adapters/`, `apps/*/services.py`                |
| alle iil-Packages | Provider | `py.typed`, vollständige Type Annotations, `__all__` Public API             |

---

## Decision Drivers

- **Wiederkehrendes Fehlermuster**: Alle aufgetretenen API-Mismatch-Fehler (falsche Parameternamen, unbekannte Enum-Werte, falsches `**kwargs`-Forwarding) folgen demselben Muster: Consumer kennt die aktuelle Provider-API nicht.
- **Scope-Erweiterung**: Das Mismatch-Problem betrifft nicht nur iil-Package-APIs sondern **alle Aufrufgrenzen**: Service-Layer (views→services→models), Celery Task Signaturen, Inter-Hub REST-Calls und Management Commands.
- **Null Testabdeckung**: Kein einziger Contract-Test existiert plattformweit — Mismatches werden erst in Produktion entdeckt.
- **Breaking Changes ohne Signal**: Parameternamen, Exception-Types und Return-Shapes können sich ändern ohne dass Consumer es merken.
- **Exception-Contracts fehlen**: Service-Layer-Methoden definieren eigene Exceptions (z.B. `DocumentUploadError`), aber kein Test prüft ob Consumer diese korrekt fangen.
- **Return-Shape-Contracts fehlen**: LLM-Services und API-Calls returnen dicts mit erwarteten Keys — Drift bleibt unsichtbar.
- **1-Entwickler-Constraint**: Kein manuelles API-Review vor jedem Update skalierbar; Automatisierung ist zwingend.
- **ADR-058 §A10 (deferred)**: "Celery Payload Contracts" wurde als deferred markiert — dieses ADR schließt diese Lücke.
- **iil-testkit als natürlicher Ort**: Das Shared-Testing-Package ist der richtige Ort für plattformweite Contract-Utilities.

---

## 1. Context and Problem Statement

### 1.1 Fehleranalyse: Aufgetretene API-Mismatches

In mehreren Hub-Sessions traten Fehler auf, die alle dieselbe Ursache haben: **Mismatch zwischen Aufrufer und Aufgerufenem an einer Funktionsgrenze**.

| Fehler | Ursache | Fehlerkategorie | Aufruftyp |
|--------|---------|-----------------|-----------|
| `OutlineGenerator.__init__() got an unexpected keyword argument 'llm_router'` | Parameter heißt `router` | Parametername falsch | Package-API |
| `OutlineGenerator.generate() got an unexpected keyword argument 'framework'` | Parameter heißt `framework_key` | Parametername falsch | Package-API |
| `Unknown framework key: 'scientific_essay'` | Framework nicht in Registry | Ungültiger Enum-Wert | Package-API |
| `Unrecognized request argument supplied: quality` | LLMRouter erwartet `quality_level` | Parametername falsch (Adapter) | Package-API |
| `DocumentUploadError` nicht gefangen in View | View fängt nur `Exception` | Exception-Contract verletzt | Service-Layer |
| `analyze_cv_with_llm()` returned dict ohne `fit_score` Key | LLM-Response-Schema geändert | Return-Shape-Drift | Service-Call |
| Celery Task `analyze_document.delay(doc_id)` → `TypeError` | Task erwartet `document_id` | Parametername falsch | Celery Task |

### 1.2 Fünf Aufruftypen im Platform-Ökosystem

```
1. Package-API:      Hub → iil-Package (outlinefw, aifw, promptfw)
2. Service-Layer:    views.py → services.py → models.py (ADR-041)
3. Celery Tasks:     service.delay(args) → task(args)
4. REST API:         Hub A → Hub B /api/v1/endpoint
5. Management Cmd:   call_command("seed_data", tenant_id=1)
```

**Alle fünf Aufruftypen leiden unter demselben Problem: Kein automatischer Mechanismus synchronisiert das Aufrufer-Wissen mit der Aufgerufenen-API.**

### 1.3 Warum das bisher unentdeckt bleibt

1. **Keine Contract-Tests** — ADR-058 §A10 ist deferred.
2. **iil-Packages haben keine `py.typed`-Marker** — mypy kann Typ-Fehler nicht erkennen.
3. **Adapter nutzen `**kwargs`-Forwarding** — Parameternamen werden nie explizit geprüft.
4. **Service-Layer hat keine Exception-Contracts** — welche Exceptions wirft `DocumentService.validate_file()`?
5. **Return-Shapes sind undokumentiert** — `analyze_cv_with_llm()` returned `dict`, aber welche Keys?
6. **CI läuft ohne Contract-Tests** — Integration Tests mocken Interfaces weg.

---

## 2. Considered Options

### Option A: `iil-testkit` ContractVerifier + `@pytest.mark.contract`

Leichtgewichtige, inspect-basierte Contract-Tests direkt in `iil-testkit`. Nur für Package-APIs.

**Pros:** Keine neuen Abhängigkeiten, passt in ADR-057/058 Taxonomie.
**Cons:** Deckt nur Package-APIs ab — nicht Service-Layer, Celery, REST.

### Option B: Pact Framework (Consumer-Driven Contract Testing)

Vollständiges CDCT mit Pact Broker, Consumer-Pacts und Provider-Verification.

**Pros:** Bidirektional, Industry-Standard.
**Cons:** Pact Broker nötig, Overengineered für 1-Entwickler-Team, abgelehnt wie ADR-057 §Option 4.

### Option C: mypy Strict Mode + `py.typed` in allen iil-Packages

Rein statische Analyse.

**Pros:** Fehler zur Compile-Zeit.
**Cons:** Allein nicht ausreichend: Enum-Werte, Return-Shapes, Exceptions nicht prüfbar.

### Option D: Pydantic-validierter `ApiAdapter`-Base-Class in `platform_context`

Adapter-Basisklasse mit explizitem Mapping — kein blindes `**kwargs`.

**Pros:** Runtime-Schutz am Fehlerpunkt.
**Cons:** Nur für Adapter, nicht für Service-Layer oder Celery.

### Option E: Erweiterte Drei-Schichten-Strategie für ALLE Aufruftypen ✅

Kombination A + C + D, erweitert um:
- **Exception-Contracts** — `assert_raises` für Service-Layer
- **Return-Shape-Contracts** — `assert_return_keys` für dict-Rückgaben
- **Callable-Contracts** — `assert_callable_params` für freistehende Funktionen
- **Celery Task-Contracts** — `assert_task_params` für Task-Signaturen
- **REST Schema-Contracts** — Response-Shape-Assertions

**Pros:** Defence-in-Depth für ALLE Aufruftypen, schrittweise einführbar.
**Cons:** Höherer initialer Aufwand — aber das System hat 5 Aufruftypen, nicht nur einen.

---

## 3. Decision Outcome

**Gewählte Option: Option E — Erweiterte Drei-Schichten-Strategie für alle Aufruftypen**

**Begründung:** Option A deckt nur Package-APIs ab (1 von 5 Aufruftypen). Die häufigsten Aufrufe im System sind Service-Layer Calls (ADR-041), nicht Package-APIs. Nur Option E schließt alle beobachteten Fehlerklassen über alle Aufrufgrenzen hinweg.

### Confirmation

1. **CI-Gate Contract-Tests**: `pytest -m contract` im `test-contract`-Job — schlägt fehl wenn keine Contract-Tests vorhanden
2. **mypy-Gate**: `mypy --strict` für `apps/*/adapters/` und `apps/*/services.py`
3. **`ApiAdapter`-Enforcement**: Guardian-Regel prüft kein `**kwargs` in `adapters/*.py`
4. **Drift-Detector**: ADR-059 prüft auf Aktualität — Staleness-Schwelle: 12 Monate

---

## 4. Implementation Details

### 4.1 Schicht 1: Statische Analyse — `py.typed` + mypy

**Provider-Seite (jedes iil-Package):**

```
outlinefw/
├── py.typed                    ← PEP 561 Marker (leere Datei)
├── __init__.py
└── generator.py
```

```python
# outlinefw/generator.py — vollständige Type Annotations (Provider-Pflicht)
from __future__ import annotations

from typing import Any
from aifw import LLMRouter


class OutlineGenerator:
    def __init__(self, router: LLMRouter) -> None:  # ← explizit, kein **kwargs
        self._router = router

    def generate(
        self,
        framework_key: str,
        context: dict[str, Any],
        *,
        quality_level: str = "standard",
    ) -> dict[str, Any]:
        ...
```

**Consumer-Seite (jedes Hub, `pyproject.toml`):**

```toml
# Fix H1: ignore_missing_imports = true als Default — sonst bricht Pipeline
# für alle ungetypten Third-Party-Packages (Django, Celery, etc.)
[tool.mypy]
python_version = "3.12"
strict = true
ignore_missing_imports = true   # WICHTIG: Default true, nur explizit false für py.typed

# Nur py.typed-Packages explizit strikt prüfen
[[tool.mypy.overrides]]
module = "outlinefw.*"
ignore_missing_imports = false   # hat py.typed

[[tool.mypy.overrides]]
module = "aifw.*"
ignore_missing_imports = false   # hat py.typed

[[tool.mypy.overrides]]
module = "platform_context.*"
ignore_missing_imports = false   # hat py.typed

# Ungetypte Third-Party — explizit akzeptieren
[[tool.mypy.overrides]]
module = ["celery.*", "django.*", "redis.*", "boto3.*"]
ignore_missing_imports = true
```

> **Vollständiger Snippet:** `docs/adr/inputs/ADR 115 input/pyproject_mypy_snippet.toml`

### 4.2 Schicht 2: Strukturelle Contract-Tests — `iil-testkit` ContractVerifier

#### 4.2.1 Erweiterter `ContractVerifier` in `iil-testkit`

> **Produktionsreife Implementierung:** `docs/adr/inputs/ADR 115 input/verifier.py` (575 LOC)
> **Review-Fixes:** B1, B2, B3, B4, K1, K3, M3 — siehe `docs/adr/reviews/ADR-155-review.md`

**Klassenhierarchie (v3):**

```
BaseContractVerifier (ABC)            ← Fix M3: Gemeinsames Protocol
├── ContractVerifier(cls)             ← Klassen (Package-APIs, Service-Layer)
├── CallableContractVerifier(func)    ← Freie Funktionen
└── TaskContractVerifier(task)        ← Celery Tasks (Fix B4: inspect.unwrap)

ResponseShapeVerifier(shape)          ← Fix K3: REST Response-Shapes
```

**API-Übersicht `ContractVerifier`:**

```python
from iil_testkit.contract import ContractVerifier

verifier = ContractVerifier(OutlineGenerator)

# Signatur-Checks
verifier.assert_init_params(["router"], exhaustive=True)         # Fix K1: bidirektional
verifier.assert_method_params("generate", ["framework_key", "context"])
verifier.assert_method_exists("generate")
verifier.assert_no_param("generate", "framework")                # str oder Callable

# Enum / Registry
verifier.assert_enum_values(REGISTRY.keys(), ["essay", "report"])
verifier.assert_not_enum_value(REGISTRY.keys(), "scientific_essay")

# Exception-Contracts (Fix B2: assert statt warnings.warn)
verifier.assert_raises("validate_file", [DocumentUploadError])

# Return-Shape (Fix B3: assert statt warnings.warn)
verifier.assert_return_keys("generate", ["content", "chapters"])
verifier.assert_return_annotation("generate", dict[str, Any])    # Fix B1: kein __origin__ Short-Circuit
verifier.assert_return_origin("generate", dict)                  # NEU: Generic-Origin
```

**API-Übersicht `TaskContractVerifier` (Fix B4):**

```python
from iil_testkit.contract import ContractVerifier

# Fix B4: inspect.unwrap() statt getattr(task, "run", task)
verifier = ContractVerifier.for_task(analyze_document_task)
verifier.assert_params(["document_id"])
verifier.assert_no_param("doc_id")
verifier.assert_is_acks_late()          # Platform-Standard
```

**API-Übersicht `ResponseShapeVerifier` (Fix K3):**

```python
from iil_testkit.contract import ResponseShapeVerifier

shape = ResponseShapeVerifier({"fit_score": float, "skills": list, "summary": str})
shape.assert_response(response_dict)          # Prüft Keys
shape.assert_response_types(response_dict)    # Prüft Keys + Typen
shape.assert_status_code(response, 200)       # HTTP Status
```

**`__init__.py` (Fix H4):**

```python
# iil_testkit/contract/__init__.py
from iil_testkit.contract.verifier import (
    BaseContractVerifier,
    CallableContractVerifier,
    ContractVerifier,
    ResponseShapeVerifier,
    TaskContractVerifier,
)

__all__ = [
    "BaseContractVerifier",
    "CallableContractVerifier",
    "ContractVerifier",
    "ResponseShapeVerifier",
    "TaskContractVerifier",
]
```

**Bidirektionale Parameter-Prüfung (Fix K1):**

```python
# exhaustive=True prüft BEIDE Richtungen:
# 1. Consumer erwartet Parameter die nicht existieren (Standard)
# 2. Provider hat neue Required-Params die Consumer nicht kennt (NEU)

verifier.assert_init_params(["router"], exhaustive=True)
# → Wenn Provider jetzt __init__(self, router, tenant_id) hat:
#    AssertionError: Provider hat neue Required-Parameter: ['tenant_id']
```

#### 4.2.2 Test-Struktur pro Hub

```
tests/
├── contracts/                              ← Schicht 2: Strukturelle Contract-Tests
│   ├── conftest.py                         ← pytest.mark.contract Marker-Registration
│   ├── test_outlinefw_contract.py          ← Package-API Contracts
│   ├── test_aifw_contract.py               ← Package-API Contracts
│   ├── test_document_service_contract.py   ← Service-Layer Contracts (NEU)
│   ├── test_csv_import_contract.py         ← Service-Layer Contracts (NEU)
│   ├── test_celery_tasks_contract.py       ← Celery Task Contracts (NEU)
│   └── test_llm_service_contract.py        ← Funktions-Contracts (NEU)
├── integration/
└── unit/
```

#### 4.2.2b `conftest.py` — Marker-Registration (Fix H3)

```python
# tests/contracts/conftest.py
import pytest

def pytest_configure(config: pytest.Config) -> None:
    """Registriert plattformweite pytest-Marker."""
    config.addinivalue_line(
        "markers",
        "contract: Contract-Tests — prüfen Signaturen, Exceptions und Shapes an "
        "Aufrufgrenzen (Package-APIs, Service-Layer, Celery Tasks, REST). "
        "ADR-155. Läuft in test-contract CI-Job.",
    )
```

> Ohne diese Registrierung: `PytestUnknownMarkWarning` (default) oder Fehler (`--strict-markers` in CI).

#### 4.2.3 Contract-Test: Package-API (wie Konzept)

```python
# tests/contracts/test_outlinefw_contract.py
"""
Contract-Tests: writing-hub (Consumer) ↔ outlinefw (Provider)

Verwandte Fehler (historisch):
  - OutlineGenerator.__init__() got an unexpected keyword argument 'llm_router'
  - OutlineGenerator.generate() got an unexpected keyword argument 'framework'
  - Unknown framework key: 'scientific_essay'
"""
import pytest
from iil_testkit.contract import ContractVerifier


pytestmark = pytest.mark.contract


@pytest.fixture(scope="module")
def outline_verifier() -> ContractVerifier:
    from outlinefw import OutlineGenerator
    return ContractVerifier(OutlineGenerator)


class TestOutlineGeneratorInit:
    def test_accepts_router_param(self, outline_verifier: ContractVerifier) -> None:
        outline_verifier.assert_init_params(["router"])

    def test_rejects_llm_router_alias(self, outline_verifier: ContractVerifier) -> None:
        from outlinefw import OutlineGenerator
        outline_verifier.assert_no_param(OutlineGenerator.__init__, "llm_router")


class TestOutlineGeneratorGenerate:
    def test_accepts_framework_key_param(self, outline_verifier: ContractVerifier) -> None:
        outline_verifier.assert_method_params("generate", ["framework_key", "context"])

    def test_rejects_framework_alias(self, outline_verifier: ContractVerifier) -> None:
        from outlinefw import OutlineGenerator
        outline_verifier.assert_no_param(OutlineGenerator.generate, "framework")
```

#### 4.2.4 Contract-Test: Service-Layer (NEU)

```python
# tests/contracts/test_document_service_contract.py
"""
Contract-Tests: views.py (Consumer) ↔ DocumentService (Provider)

Prüft dass die Service-Layer-API stabil bleibt:
  - Methodennamen existieren
  - Parameter stimmen
  - Erwartete Exceptions werden geworfen
  - Return-Shapes sind dokumentiert
"""
import pytest
from iil_testkit.contract import ContractVerifier


pytestmark = pytest.mark.contract


@pytest.fixture(scope="module")
def doc_service_verifier() -> ContractVerifier:
    from apps.candidates.services import DocumentService
    return ContractVerifier(DocumentService)


class TestDocumentServiceMethods:
    """Prüft dass alle vom Consumer genutzten Methoden existieren."""

    def test_validate_file_exists(self, doc_service_verifier: ContractVerifier) -> None:
        doc_service_verifier.assert_method_exists("validate_file")

    def test_extract_text_exists(self, doc_service_verifier: ContractVerifier) -> None:
        doc_service_verifier.assert_method_exists("extract_text")

    def test_analyze_document_exists(self, doc_service_verifier: ContractVerifier) -> None:
        doc_service_verifier.assert_method_exists("analyze_document")

    def test_analyze_document_params(self, doc_service_verifier: ContractVerifier) -> None:
        doc_service_verifier.assert_method_params("analyze_document", ["document"])


class TestDocumentServiceExceptions:
    """Prüft Exception-Contracts (welche Exceptions kann der Consumer erwarten?)."""

    def test_validate_file_raises_upload_error(self, doc_service_verifier: ContractVerifier) -> None:
        from apps.candidates.services import DocumentUploadError
        doc_service_verifier.assert_raises("validate_file", [DocumentUploadError])

    def test_upload_error_is_exception(self) -> None:
        from apps.candidates.services import DocumentUploadError
        assert issubclass(DocumentUploadError, Exception)
```

#### 4.2.5 Contract-Test: Freistehende Funktionen (NEU)

```python
# tests/contracts/test_llm_service_contract.py
"""
Contract-Tests: DocumentService (Consumer) ↔ analyze_cv_with_llm() (Provider)

Prüft dass die LLM-Service-Funktion die erwartete Signatur hat
und die erwarteten Keys im Return-Dict liefert.
"""
import pytest
from iil_testkit.contract import ContractVerifier


pytestmark = pytest.mark.contract


class TestAnalyzeCvWithLlm:
    def test_params(self) -> None:
        from apps.candidates.llm_service import analyze_cv_with_llm
        verifier = ContractVerifier.for_callable(analyze_cv_with_llm)
        verifier.assert_params(["text", "project_requirements"])

    def test_no_param_cv_text(self) -> None:
        """Historisch: Parameter hieß mal 'cv_text' statt 'text'."""
        from apps.candidates.llm_service import analyze_cv_with_llm
        verifier = ContractVerifier.for_callable(analyze_cv_with_llm)
        verifier.assert_no_param("cv_text")
```

#### 4.2.6 Contract-Test: Celery Tasks (NEU — schließt ADR-058 §A10)

```python
# tests/contracts/test_celery_tasks_contract.py
"""
Contract-Tests: Service-Layer (Consumer) ↔ Celery Tasks (Provider)

Schließt ADR-058 §A10 (Celery Payload Contracts — bisher deferred).

Pattern:
  Consumer: analyze_document_task.delay(document_id=42)
  Provider: def analyze_document_task(document_id: int) -> None
  Contract: Parameter 'document_id' existiert, 'doc_id' nicht
"""
import pytest
from iil_testkit.contract import ContractVerifier


pytestmark = pytest.mark.contract


class TestAnalyzeDocumentTask:
    def test_params(self) -> None:
        from apps.candidates.tasks import analyze_document_task
        verifier = ContractVerifier.for_task(analyze_document_task)
        verifier.assert_params(["document_id"])

    def test_no_param_doc_id(self) -> None:
        """'doc_id' war eine falsche Consumer-Annahme."""
        from apps.candidates.tasks import analyze_document_task
        verifier = ContractVerifier.for_task(analyze_document_task)
        verifier.assert_no_param("doc_id")
```

### 4.3 Schicht 3: Runtime-Schutz — `ApiAdapter`-Basisklasse

#### 4.3.1 Basisklasse in `platform_context`

> **Produktionsreife Implementierung:** `docs/adr/inputs/ADR 115 input/api_adapter_base.py` (106 LOC)

```python
# platform_context/adapters/base.py — API-Übersicht

class ApiAdapter(ABC):
    """Basisklasse für alle Adapter zwischen Hub und iil-Package.

    Subklassen MÜSSEN:
    1. Alle Provider-Parameter explizit in der Methodensignatur benennen
    2. Kein **kwargs an Provider-Calls durchreichen
    3. Parameter-Mapping mit Kommentar dokumentieren:
         # Consumer '<name>' → Provider '<name>'
    4. Von dieser Basisklasse erben

    Subklassen DÜRFEN NICHT:
    - **kwargs aus Consumer-Calls blind an Provider weiterreichen
    - Provider-Parameternamen direkt dem Consumer exponieren (Leaky Abstraction)
    - Provider-Imports im Consumer-Code (nur über Adapter)
    """

    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    def _log_call(self, method: str, **consumer_params: Any) -> None: ...
    def _log_provider_error(self, method: str, error: Exception, **consumer_params: Any) -> None: ...
```

#### 4.3.2 Architecture-Guardian-Regel (Fix K2)

> **Produktionsreife Implementierung:** `docs/adr/inputs/ADR 115 input/no_kwargs_forwarding.py` (126 LOC)
> **Fix K2:** Erweiterte Pattern-Erkennung — 3 Regex statt 1, erkennt auch indirektes Forwarding.

```python
# dev-hub: apps/architecture_guardian/rules/no_kwargs_forwarding.py

# Fix K2: 3 Patterns statt 1 — erkennt direktes UND indirektes Forwarding
_PATTERNS = [
    ("Direktes return-Forwarding",
     re.compile(r"return\s+self\._\w+\.\w+\([^)]*\*\*kwargs[^)]*\)", re.MULTILINE)),
    ("Indirektes Forwarding via Zuweisung",
     re.compile(r"\w+\s*=\s*self\._\w+\.\w+\([^)]*\*\*kwargs[^)]*\)", re.MULTILINE)),
    ("Reines **kwargs-Forwarding",
     re.compile(r"self\._\w+\.\w+\(\*\*kwargs\)", re.MULTILINE)),
]

# Erlaubte Ausnahme: Zeile enthält '# adr155-allow-kwargs'
_ALLOWLIST_COMMENT = "# adr155-allow-kwargs"

def check(repo_path: Path) -> list[dict[str, str]]: ...      # Returns violations mit file, line, pattern, code
def check_as_strings(repo_path: Path) -> list[str]: ...       # Convenience-Wrapper
# CLI: python no_kwargs_forwarding.py /path/to/repo → exit 0/1
```

### 4.4 CI-Pipeline Integration (Fix H1, M1)

> **Produktionsreife Implementierung:** `docs/adr/inputs/ADR 115 input/ci_contract_jobs.yml` (106 LOC)

```yaml
# .github/workflows/_ci-python.yml (Erweiterung)

  # ── Contract-Tests (ADR-155) ─────────────────────────────────────────
  test-contract:
    runs-on: [self-hosted, hetzner, dev]
    needs: [test-unit]
    steps:
      - uses: actions/checkout@v4
      - name: Install dependencies
        run: pip install -r requirements.txt -r requirements-test.txt
      - name: Run Contract Tests
        # Fix ADR-076: exit code 5 = keine Tests gefunden → als Fehler behandeln
        run: |
          set -euo pipefail
          pytest tests/contracts/ \
            -m contract -v --tb=short --no-header \
            --strict-markers -p no:warnings 2>&1
          code=$?
          if [ $code -eq 5 ]; then
            echo "❌ ADR-155: Keine Contract-Tests in tests/contracts/"
            exit 1
          fi
          exit $code
      # Fix H1: mypy NUR für eigene Code-Layer — nicht für alle Imports
      # Fix M1: Konsistent mit Confirmation §2 (adapters/ + services/)
      - name: mypy — Adapter Layer (strict)
        run: |
          set -euo pipefail
          if find apps -name "*.py" -path "*/adapters/*" | grep -q .; then
            mypy apps/*/adapters/ --strict --config-file pyproject.toml --no-error-summary
          fi
      - name: mypy — Service Layer (non-strict, progressiv)
        run: |
          set -euo pipefail
          if find apps -name "services.py" | grep -q .; then
            mypy apps/*/services.py --config-file pyproject.toml \
              --ignore-missing-imports --no-error-summary \
              || echo "⚠️  mypy Service-Layer: Warnungen (non-blocking bis Phase 2)"
          fi

  # ── Architecture Guardian (ADR-054) — erweitert um ADR-155-Regeln ───
  architecture-guardian:
    runs-on: [self-hosted, hetzner, dev]
    needs: [lint]
    steps:
      - uses: actions/checkout@v4
      - name: Guardian — kein **kwargs-Forwarding (ADR-155 §4.3, Fix K2)
        run: |
          set -euo pipefail
          if find apps -name "*.py" -path "*/adapters/*" | grep -q .; then
            python dev-hub/apps/architecture_guardian/rules/no_kwargs_forwarding.py .
          fi
      - name: Guardian — Contract-Tests vorhanden (ADR-155 §4.6)
        run: |
          set -euo pipefail
          contract_count=$(find tests/contracts/ -name "test_*.py" 2>/dev/null | wc -l)
          if [ "$contract_count" -eq 0 ]; then
            echo "❌ ADR-155: tests/contracts/ enthält keine Contract-Tests."
            exit 1
          fi
          echo "✓ ADR-155: ${contract_count} Contract-Test-Datei(en) gefunden."
      - name: Guardian — py.typed in iil-Package-Abhängigkeiten (ADR-155 §4.1)
        run: |
          set -euo pipefail
          for pkg in outlinefw aifw promptfw authoringfw weltenfw; do
            pkg_path=$(python -c "import importlib.util; s=importlib.util.find_spec('${pkg}'); print(s.submodule_search_locations[0] if s else '')" 2>/dev/null || echo "")
            if [ -n "$pkg_path" ] && [ ! -f "${pkg_path}/py.typed" ]; then
              echo "⚠️  ADR-155: Package '${pkg}' hat kein py.typed"
            fi
          done
```

### 4.5 Contract-Typen Übersicht

| Contract-Typ | Verifier | Prüft | Beispiel |
|-------------|----------|-------|----------|
| **Package-API** | `ContractVerifier(Class)` | Init-Params, Method-Params, Enum-Values | `OutlineGenerator`, `LLMRouter` |
| **Service-Layer** | `ContractVerifier(Service)` | Method-Exists, Params, Exceptions | `DocumentService`, `CSVImportService` |
| **Freie Funktion** | `ContractVerifier.for_callable(fn)` | Params, Return-Type | `analyze_cv_with_llm()` |
| **Celery Task** | `ContractVerifier.for_task(task)` | Task-Params, No-Wrong-Param, acks_late | `analyze_document_task` |
| **REST Schema** | `ResponseShapeVerifier(shape)` (Fix K3) | Keys, Typen, Status-Code | `GET /api/v1/candidates/` |

### 4.6 Checkliste für neue Aufrufgrenzen

Bei **jeder** neuen Integration — egal ob Package, Service, Task oder REST:

```
□ 1. Contract-Test-Datei anlegen: tests/contracts/test_<component>_contract.py
□ 2. @pytest.mark.contract gesetzt
□ 3. Parameternamen aller genutzten Methoden/Funktionen geprüft
□ 4. Historische Fehler-Namen mit assert_no_param() dokumentiert
□ 5. Exception-Contract dokumentiert (assert_raises für Service-Layer)
□ 6. Return-Shape dokumentiert (assert_return_keys für dict-Rückgaben)
□ 7. Bei Adaptern: Von ApiAdapter erben, kein **kwargs-Forwarding
□ 8. mypy --strict läuft ohne Fehler
□ 9. py.typed im Provider-Package vorhanden
```

---

## 5. Migration Tracking

| Repo / Component                  | Phase | Status        | Datum      | Notizen                                          |
|-----------------------------------|-------|---------------|------------|--------------------------------------------------|
| `iil-testkit` — ContractVerifier  | 1     | 🔲 offen      | –          | `iil_testkit/contract/verifier.py` (erweitert)   |
| `iil-testkit` — `__init__` Export | 1     | 🔲 offen      | –          | `from iil_testkit.contract import ContractVerifier` |
| `platform_context` — ApiAdapter   | 1     | 🔲 offen      | –          | `platform_context/adapters/base.py`              |
| `bfagent` — outlinefw Contract    | 2     | 🔲 offen      | –          | Package-API Contract                             |
| `bfagent` — aifw Contract         | 2     | 🔲 offen      | –          | Package-API Contract                             |
| `bfagent` — Service-Layer Contr.  | 2     | 🔲 offen      | –          | Service-Layer Contracts (NEU)                    |
| `bfagent` — Celery Task Contracts | 2     | 🔲 offen      | –          | Schließt ADR-058 §A10 (NEU)                     |
| `recruiting-hub` — Service Contr. | 2     | 🔲 offen      | –          | DocumentService, CSVImportService, llm_service   |
| `_ci-python.yml` — contract Job   | 1     | 🔲 offen      | –          | exit-code-5-Behandlung                           |
| `_ci-python.yml` — mypy adapters  | 1     | 🔲 offen      | –          | `mypy apps/*/adapters/ --strict`                 |
| Guardian-Regel no_kwargs          | 3     | 🔲 offen      | –          | Nach Phase 1+2 Stabilisierung                    |
| alle weiteren Hub-Repos           | 3     | 🔲 offen      | –          | Nach bfagent + recruiting-hub als Referenz       |
| iil-Packages — `py.typed`         | 2     | 🔲 offen      | –          | outlinefw, aifw, promptfw als erste Kandidaten   |

---

## 6. Consequences

### 6.1 Good

- **Alle historischen Fehler wären verhindert worden**: Parameternamen via Layer 1+2, Enum-Werte via Layer 2, Adapter via Layer 3.
- **Alle 5 Aufruftypen abgedeckt**: Package-API, Service-Layer, Celery, freie Funktionen, REST.
- **Exception-Contracts** verhindern unbehandelte Exceptions in Views — Consumer weiß welche Fehler zu fangen sind.
- **Return-Shape-Contracts** dokumentieren dict-Strukturen die sonst nur implizit bekannt sind.
- **Celery Task-Contracts** schließen ADR-058 §A10 — keine separate Lösung nötig.
- **Breaking Changes werden sofort sichtbar**: Contract-Tests schlagen bei Signatur-Änderungen fehl.
- **Tests dokumentieren Consumer-Erwartungen**: `assert_no_param(..., "llm_router")` ist lebendige Dokumentation.
- **Schrittweise einführbar**: Layer 2 (iil-testkit) kann ohne Layer 1 (py.typed) starten.

### 6.2 Bad

- **Pflege-Aufwand bei API-Änderungen**: Contract-Tests müssen aktualisiert werden — aber das ist das **gewollte Signal**.
- **Initialer Aufwand**: Alle bestehenden Aufrufgrenzen benötigen nachträgliche Contract-Tests.
- **Fünf Verifier-Klassen**: Erhöht Lernkurve für neue Entwickler — aber API ist konsistent.

### 6.3 Nicht in Scope

- Semantische Contract-Tests (Rückgabewert-Inhalte, Seiteneffekte) — Phase 2 / separates ADR
- Pact Broker (ADR-057: evaluate when Team > 5 Personen)
- Performance-Contracts (Antwortzeiten, Memory-Verbrauch)

---

## 7. Risks

| Risiko | W'keit | Impact | Mitigation |
|--------|--------|--------|-----------|
| Contract-Tests werden nicht geschrieben | Mittel | Hoch | CI-Gate: leere `tests/contracts/` → Build-Fehler |
| iil-Package hat kein `py.typed` | Hoch | Mittel | `ignore_missing_imports = false` + Provider-Update priorisieren |
| Adapter-Basisklasse wird umgangen (direkte Calls) | Mittel | Hoch | Guardian-Regel + Code Review |
| Exception-Contracts veralten | Mittel | Mittel | Contract-Tests schlagen fehl → Review erzwungen |
| False Sense of Security | Niedrig | Mittel | Scope ist Signatur + Exception + Shape — nicht Semantik |

---

## 8. Confirmation

1. **CI-Gate Contract-Tests**: `pytest -m contract --strict-markers` — exit code 5 → Build-Fehler (Fix ADR-076)
2. **mypy-Gate Adapters**: `mypy apps/*/adapters/ --strict --config-file pyproject.toml` — kein Merge bei Typ-Fehler (Fix H1: `ignore_missing_imports=true` als Default)
3. **mypy Service-Layer**: `mypy apps/*/services.py` — non-strict, progressiv (Fix M1: konsistent mit §2)
4. **Guardian no-kwargs**: `python no_kwargs_forwarding.py .` — 3 Patterns inkl. indirektes Forwarding (Fix K2)
5. **Guardian Contract-Test-Existenz**: `find tests/contracts/ -name 'test_*.py'` → min. 1 Datei
6. **Drift-Detector**: ADR-059 prüft auf Aktualität — Staleness-Schwelle: 12 Monate

---

## 9. More Information

- ADR-041: Service Layer — views→services→models (häufigster Aufruftyp)
- ADR-057: Platform Test Strategy — §Option 4: Pact deferred
- ADR-058: Platform Test Taxonomy — §A10 Celery Payload Contracts (jetzt geschlossen durch dieses ADR)
- ADR-076: bfagent CI — exit-code-5-Behandlung
- ADR-054: Architecture Guardian — Guardian-Regel no_kwargs_forwarding
- ADR-059: Drift-Detector — Staleness-Monitoring
- PEP 561: https://peps.python.org/pep-0561/ — `py.typed` Spezifikation
- Konzeptpapier (Input): `docs/adr/inputs/ADR-155-api-contract-testing.md`
- Review-Befunde: `docs/adr/reviews/ADR-155-review.md` (4 BLOCKER, 3 KRITISCH, 4 HOCH, 4 MEDIUM)
- Implementation-Review: `docs/adr/reviews/ADR-155-implementation-review.md` (Review-Tabelle + Implementierungsplan)
- Produktionsreife Dateien: `docs/adr/inputs/ADR 115 input/` (7 Dateien, alle Fixes)

---

## 10. Changelog

| Datum      | Autor          | Änderung                                      |
|------------|----------------|-----------------------------------------------|
| 2026-04-02 | Achim Dehnert  | Initial: Konzeptpapier (nur Package-APIs)     |
| 2026-04-02 | Achim Dehnert  | v2: Erweiterung auf alle 5 Aufruftypen — Service-Layer, Celery, freie Funktionen, REST |
| 2026-04-02 | Cascade        | v3: Review eingearbeitet — 4 BLOCKER (B1-B4), 3 KRITISCH (K1-K3), 4 HOCH (H1-H4), 4 MEDIUM (M1-M4) behoben. BaseContractVerifier ABC, ResponseShapeVerifier, exhaustive-Mode, inspect.unwrap() für Celery, assert statt warnings.warn, mypy Scope-Fix, Guardian 3-Pattern, conftest.py |

---

<!--
  Drift-Detector-Felder (ADR-059):
  - staleness_months: 12
  - drift_check_paths:
      - iil-testkit/iil_testkit/contract/verifier.py
      - platform_context/platform_context/adapters/base.py
      - bfagent/tests/contracts/
      - recruiting-hub/tests/contracts/
  - supersedes_check: true
-->
