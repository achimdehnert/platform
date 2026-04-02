---
status: proposed
date: 2026-04-02
amended: –
decision-makers: [Achim Dehnert]
consulted: []
informed: []
supersedes: []
related:
  - ADR-057-platform-test-strategy.md
  - ADR-058-platform-test-taxonomy.md
  - ADR-076-bfagent-ci-test-strategy.md
---

# ADR-155: Adopt a Three-Layer API Contract Testing Strategy for iil-Package Integrations

## Metadaten

| Attribut          | Wert                                                                                      |
|-------------------|-------------------------------------------------------------------------------------------|
| **Status**        | Proposed                                                                                  |
| **Scope**         | platform-wide (alle Hubs als Consumer, alle iil-Packages als Provider)                   |
| **Erstellt**      | 2026-04-02                                                                                |
| **Autor**         | Achim Dehnert                                                                             |
| **Reviewer**      | –                                                                                         |
| **Supersedes**    | –                                                                                         |
| **Superseded by** | –                                                                                         |
| **Relates to**    | ADR-057 (Test Strategy), ADR-058 (Test Taxonomy), ADR-076 (bfagent CI), ADR-022 (Code Quality) |

## Repo-Zugehörigkeit

| Repo              | Rolle    | Betroffene Pfade / Komponenten                                              |
|-------------------|----------|-----------------------------------------------------------------------------|
| `iil-testkit`     | Primär   | `iil_testkit/contract/`, `iil_testkit/contract/verifier.py`                 |
| `platform_context`| Primär   | `platform_context/adapters/base.py`                                         |
| `bfagent`         | Consumer | `tests/contracts/`, `apps/writing_hub/adapters/`                            |
| alle Hub-Repos    | Consumer | `tests/contracts/`, `apps/*/adapters/`                                      |
| alle iil-Packages | Provider | `py.typed`, vollständige Type Annotations, `__all__` Public API             |

---

## Decision Drivers

- **Wiederkehrendes Fehlermuster**: Alle aufgetretenen API-Mismatch-Fehler (falsche Parameternamen, unbekannte Enum-Werte, falsches `**kwargs`-Forwarding) folgen demselben Muster: Consumer kennt die aktuelle Provider-API nicht.
- **Null Testabdeckung**: Kein einziger Contract-Test existiert plattformweit — Mismatches werden erst in Produktion entdeckt.
- **Breaking Changes ohne Signal**: iil-Package-Updates können Parameternamen ändern ohne dass Consumer-Repos es sofort merken.
- **1-Entwickler-Constraint**: Kein manuelles API-Review vor jedem Package-Update skalierbar; Automatisierung ist zwingend.
- **ADR-058 §A10 (deferred)**: "Celery Payload Contracts" wurde als deferred markiert — dieses ADR schließt die allgemeinere Lücke.
- **iil-testkit als natürlicher Ort**: Das Shared-Testing-Package ist der richtige Ort für plattformweite Contract-Utilities.

---

## 1. Context and Problem Statement

### 1.1 Fehleranalyse: Aufgetretene API-Mismatches

In mehreren Hub-Sessions traten Fehler auf, die alle dieselbe Ursache haben: **API-Mismatch zwischen Hub-Consumer und iil-Package-Provider**.

| Fehler | Ursache | Fehlerkategorie |
|--------|---------|-----------------|
| `OutlineGenerator.__init__() got an unexpected keyword argument 'llm_router'` | Parameter heißt `router` | Parametername falsch |
| `OutlineGenerator.generate() got an unexpected keyword argument 'framework'` | Parameter heißt `framework_key` | Parametername falsch |
| `Unknown framework key: 'scientific_essay'` | Framework nicht in Registry | Ungültiger Enum-Wert |
| `Unrecognized request argument supplied: quality` | LLMRouter erwartet `quality_level` | Parametername falsch (Adapter) |

**Alle vier Fehler hätten durch automatisierte Contract-Tests verhindert werden können.**

### 1.2 Generisches Fehlermuster

```
Hub (Consumer)              iil-Package (Provider)
─────────────────           ──────────────────────
calls: fn(llm_router=…)  ≠  def fn(router=…)         ← Parametername-Drift
calls: fn(quality=…)     ≠  def fn(quality_level=…)   ← Adapter forwarded **kwargs blind
calls: key="scientific_essay" ≠ VALID_KEYS = {...}    ← Enum-Wert nicht synchronisiert
```

Der Kern: **Kein automatischer Mechanismus synchronisiert das Consumer-Wissen mit der Provider-API.**

### 1.3 Warum das bisher unentdeckt bleibt

1. **Keine Contract-Tests** — ADR-058 §A10 ist deferred.
2. **iil-Packages haben keine `py.typed`-Marker** — mypy kann Typ-Fehler nicht erkennen.
3. **Adapter nutzen `**kwargs`-Forwarding** — Parameternamen werden nie explizit geprüft.
4. **CI läuft ohne Package-Mock-Tests** — Integration Tests mocken Packages weg.

---

## 2. Considered Options

### Option A: `iil-testkit` ContractVerifier + `@pytest.mark.contract` (empfohlen)

Leichtgewichtige, inspect-basierte Contract-Tests direkt in `iil-testkit`. Jeder Hub schreibt `tests/contracts/test_<package>_contract.py` gegen einen `ContractVerifier`-Helfer aus dem Testkit.

**Pros:**
- Keine neuen Abhängigkeiten — nutzt `inspect`, `pytest`, `pydantic` (bereits vorhanden)
- Passt exakt in ADR-057/058 `@pytest.mark.contract`-Taxonomie
- `ContractVerifier`-Helfer in `iil-testkit` einmalig implementiert, von allen Hubs genutzt
- Fehlermeldungen sind präzise und actionable (zeigen exakt welcher Parameter falsch ist)
- Kein Broker, kein Server, keine externe Infrastruktur

**Cons:**
- Erfordert manuelle Pflege bei Provider-API-Änderungen
- Prüft nur Signaturen — keine semantischen Contracts (Rückgabewert-Shapes)

### Option B: Pact Framework (Consumer-Driven Contract Testing)

Vollständiges CDCT mit Pact Broker, Consumer-Pacts und Provider-Verification.

**Pros:**
- Bidirektional — Provider verifiziert gegen Consumer-Pacts automatisch
- Polyglot, Industry-Standard

**Cons:**
- Benötigt Pact Broker als zusätzlichen Service (Hetzner VM oder SaaS)
- Erheblicher Setup-Overhead für 1-Entwickler-Team
- Overengineered für interne Packages ohne externe Teams
- **Abgelehnt** — wie ADR-057 §Option 4: "evaluate wenn Team > 5 Personen"

### Option C: mypy Strict Mode + `py.typed` in allen iil-Packages

Rein statische Analyse: Provider-Packages erhalten `py.typed`-Marker + vollständige Type Annotations; Hubs laufen mit `mypy --strict`.

**Pros:**
- Fehler zur Compile-Zeit — kein Testlauf nötig
- Null Laufzeit-Overhead
- Erzwingt Dokumentation der API durch Typ-Annotations

**Cons:**
- Allein nicht ausreichend: Enum-Werte, Registry-Inhalte und dynamische Parameter nicht durch mypy prüfbar
- Erfordert vollständige Annotation aller iil-Packages (erheblicher Aufwand)
- Falsche Type-Stubs silently wrong

### Option D: Pydantic-validierter `ApiAdapter`-Base-Class in `platform_context`

Adapter-Basisklasse mit explizitem Pydantic-Parametermapping — kein blindes `**kwargs`-Forwarding.

**Pros:**
- Runtime-Schutz direkt am Fehlerpunkt
- Mapping ist selbstdokumentierend
- Pydantic-Fehlermeldungen sind präzise

**Cons:**
- Schützt nur den Adapter-Layer — nicht Direktaufrufe ohne Adapter
- Allein nicht ausreichend (entdeckt Fehler erst zur Laufzeit)

### Option E: Kombination A + C + D (vollständige Drei-Schichten-Strategie) ✅

Alle drei Schichten kombiniert:
1. **Statisch (C)**: `py.typed` + mypy → Fehler zur Import-Zeit
2. **Strukturell (A)**: `ContractVerifier` in `iil-testkit` → Fehler in CI
3. **Runtime (D)**: `ApiAdapter`-Basisklasse → Fehler am ersten Aufruf

**Pros:**
- Defence-in-Depth: Jede Schicht fängt andere Fehlerklassen
- Schrittweise einführbar (Schicht 1 → 2 → 3)
- Kein neuer externer Service

**Cons:**
- Höherer initialer Aufwand
- Drei Mechanismen die gepflegt werden müssen

---

## 3. Decision Outcome

**Gewählte Option: Option E — Drei-Schichten-Strategie (statisch + strukturell + runtime)**

**Begründung:** Option A allein ist zu spät (Laufzeit-Fehler in Tests). Option C allein ist zu unvollständig (keine Enum-Werte). Option D allein schützt nur Adapter-Layer. Nur die Kombination schließt alle vier beobachteten Fehlerklassen. Option B (Pact) ist für das Team und die Infrastruktur überproportioniert.

### Confirmation

1. **CI-Gate Contract-Tests**: `pytest -m contract` im `test-contract`-Job von `_ci-python.yml` — schlägt fehl wenn kein Hub Contract-Tests für seine iil-Package-Integrationen hat (leere `tests/contracts/` → ADR-Verstoß)
2. **mypy-Gate**: `mypy --strict` läuft in `_ci-python.yml` für alle Hubs — Typ-Fehler blockieren Merge
3. **`ApiAdapter`-Enforcement**: Architecture-Guardian-Regel (ADR-054) prüft via `grep` dass kein `**kwargs` in `adapters/*.py` ohne explizites Mapping vorkommt
4. **Drift-Detector**: Dieses ADR wird von ADR-059 auf Aktualität geprüft — Staleness-Schwelle: 12 Monate

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
[tool.mypy]
strict = true
ignore_missing_imports = false   # ← py.typed Packages werden strikt geprüft

[[tool.mypy.overrides]]
module = "outlinefw.*"
ignore_missing_imports = false   # explizit: Package hat py.typed
```

**Was mypy findet:**

```python
# writing_hub/services.py
gen = OutlineGenerator(llm_router=router)  # mypy: Unexpected keyword argument "llm_router"
gen.generate(framework="essay")            # mypy: Unexpected keyword argument "framework"
```

### 4.2 Schicht 2: Strukturelle Contract-Tests — `iil-testkit` ContractVerifier

#### 4.2.1 `ContractVerifier` in `iil-testkit`

```python
# iil_testkit/contract/verifier.py
"""
Platform-weiter Contract-Verifier für iil-Package API-Signaturen.

Verwendung:
    from iil_testkit.contract import ContractVerifier

    verifier = ContractVerifier(MyClass)
    verifier.assert_init_params(["router", "config"])
    verifier.assert_method_params("generate", ["framework_key", "context"])
    verifier.assert_enum_values(MyClass.VALID_KEYS, ["essay", "report"])
    verifier.assert_no_param(MyClass.generate, "framework")  # Häufiger Fehler
"""
from __future__ import annotations

import inspect
from typing import Any, Callable


class ContractVerifier:
    """Prüft API-Signaturen eines Provider-Objekts gegen Consumer-Erwartungen."""

    def __init__(self, cls: type) -> None:
        self._cls = cls
        self._name = cls.__qualname__

    # ── Signatur-Checks ──────────────────────────────────────────────────────

    def assert_init_params(self, expected: list[str]) -> None:
        """Prüft dass __init__ genau die erwarteten Parameter hat."""
        self._assert_params(self._cls.__init__, expected, f"{self._name}.__init__")

    def assert_method_params(self, method_name: str, expected: list[str]) -> None:
        """Prüft dass eine Methode die erwarteten Parameter hat."""
        method = getattr(self._cls, method_name)
        self._assert_params(method, expected, f"{self._name}.{method_name}")

    def assert_no_param(self, method: Callable[..., Any], wrong_name: str) -> None:
        """Prüft dass ein bekannter Migrations-Fehler-Parametername NICHT existiert."""
        sig = inspect.signature(method)
        params = set(sig.parameters.keys()) - {"self", "cls"}
        assert wrong_name not in params, (
            f"{method.__qualname__}: Parameter '{wrong_name}' sollte nicht existieren. "
            f"Verfügbare Parameter: {sorted(params)}"
        )

    # ── Enum / Registry-Checks ───────────────────────────────────────────────

    def assert_enum_values(
        self, actual_values: set[str] | list[str], expected_subset: list[str]
    ) -> None:
        """Prüft dass erwartete Werte in einem Registry/Enum vorhanden sind."""
        actual = set(actual_values)
        missing = set(expected_subset) - actual
        assert not missing, (
            f"{self._name}: Fehlende Werte in Registry: {sorted(missing)}. "
            f"Verfügbare Werte: {sorted(actual)}"
        )

    def assert_not_enum_value(
        self, actual_values: set[str] | list[str], wrong_value: str
    ) -> None:
        """Prüft dass ein bekannter falscher Wert NICHT in der Registry ist."""
        actual = set(actual_values)
        assert wrong_value not in actual, (
            f"{self._name}: Wert '{wrong_value}' existiert in Registry — "
            f"war das eine versehentliche Umbenennung?"
        )

    # ── Typ-Checks ───────────────────────────────────────────────────────────

    def assert_return_annotation(self, method_name: str, expected_type: type) -> None:
        """Prüft den Rückgabetyp einer Methode (wenn annotiert)."""
        method = getattr(self._cls, method_name)
        sig = inspect.signature(method)
        annotation = sig.return_annotation
        if annotation is inspect.Parameter.empty:
            raise AssertionError(
                f"{self._name}.{method_name}: Keine Return-Annotation vorhanden. "
                f"iil-Packages müssen vollständig annotiert sein (py.typed Standard)."
            )
        assert annotation == expected_type or (
            hasattr(annotation, "__origin__")
        ), (
            f"{self._name}.{method_name}: Return-Typ {annotation!r} ≠ erwartet {expected_type!r}"
        )

    # ── Internes ─────────────────────────────────────────────────────────────

    def _assert_params(
        self, func: Callable[..., Any], expected: list[str], label: str
    ) -> None:
        sig = inspect.signature(func)
        actual = [p for p in sig.parameters.keys() if p not in ("self", "cls")]
        missing = [p for p in expected if p not in actual]
        unexpected_wrong = []  # Dokumentiere bekannte falsche Namen

        assert not missing, (
            f"{label}: Fehlende Parameter: {missing}. "
            f"Tatsächliche Signatur: {actual}. "
            f"Hinweis: Parametername im Hub anpassen."
        )
```

#### 4.2.2 Test-Struktur pro Hub

```
tests/
├── contracts/                          ← Schicht 2: Strukturelle Contract-Tests
│   ├── conftest.py                     ← pytest.mark.contract Marker-Registration
│   ├── test_outlinefw_contract.py
│   ├── test_aifw_contract.py
│   ├── test_promptfw_contract.py
│   └── test_authoringfw_contract.py    ← neu wenn authoringfw implementiert
├── integration/                        ← ADR-057: Integration-Tests
└── unit/                               ← ADR-057: Unit-Tests
```

#### 4.2.3 Konkretes Contract-Test-Beispiel

```python
# tests/contracts/test_outlinefw_contract.py
"""
Contract-Tests: writing-hub (Consumer) ↔ outlinefw (Provider)

Zweck: Prüft dass die Consumer-Annahmen über die outlinefw-API korrekt sind.
       Schlägt bei Package-Update mit Breaking Change sofort fehl.

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
    """Prüft __init__-Signatur gegen Consumer-Erwartungen."""

    def test_accepts_router_param(self, outline_verifier: ContractVerifier) -> None:
        """Consumer nutzt 'router', nicht 'llm_router'."""
        outline_verifier.assert_init_params(["router"])

    def test_rejects_llm_router_alias(self, outline_verifier: ContractVerifier) -> None:
        """Stellt sicher dass der historische Fehler-Name nicht existiert."""
        from outlinefw import OutlineGenerator
        outline_verifier.assert_no_param(OutlineGenerator.__init__, "llm_router")


class TestOutlineGeneratorGenerate:
    """Prüft generate()-Signatur gegen Consumer-Erwartungen."""

    def test_accepts_framework_key_param(self, outline_verifier: ContractVerifier) -> None:
        """Consumer nutzt 'framework_key', nicht 'framework'."""
        outline_verifier.assert_method_params("generate", ["framework_key", "context"])

    def test_rejects_framework_alias(self, outline_verifier: ContractVerifier) -> None:
        """Stellt sicher dass der historische Fehler-Name nicht existiert."""
        from outlinefw import OutlineGenerator
        outline_verifier.assert_no_param(OutlineGenerator.generate, "framework")

    def test_rejects_chapter_count_alias(self, outline_verifier: ContractVerifier) -> None:
        """'chapter_count' existiert nicht — war eine Consumer-Annahme."""
        from outlinefw import OutlineGenerator
        outline_verifier.assert_no_param(OutlineGenerator.generate, "chapter_count")


class TestOutlineFrameworkRegistry:
    """Prüft Registry-Werte gegen Consumer-Erwartungen."""

    def test_valid_framework_keys_present(self, outline_verifier: ContractVerifier) -> None:
        """Alle vom Consumer genutzten Framework-Keys müssen in der Registry existieren."""
        from outlinefw import FRAMEWORK_REGISTRY
        outline_verifier.assert_enum_values(
            FRAMEWORK_REGISTRY.keys(),
            expected_subset=["essay", "report", "blog_post"],  # Consumer-Nutzung
        )

    def test_scientific_essay_not_valid(self, outline_verifier: ContractVerifier) -> None:
        """'scientific_essay' war ein historischer Fehler-Wert."""
        from outlinefw import FRAMEWORK_REGISTRY
        outline_verifier.assert_not_enum_value(
            FRAMEWORK_REGISTRY.keys(), "scientific_essay"
        )
```

#### 4.2.4 aifw LLMRouter Contract-Test

```python
# tests/contracts/test_aifw_contract.py
"""
Contract-Tests: Hub (Consumer) ↔ aifw LLMRouter (Provider)

Verwandte Fehler (historisch):
  - Unrecognized request argument supplied: quality  (erwartet: quality_level)
"""
import pytest
from iil_testkit.contract import ContractVerifier


pytestmark = pytest.mark.contract


class TestLLMRouterCompletion:
    def test_accepts_quality_level_not_quality(self) -> None:
        from aifw import LLMRouter
        import inspect

        sig = inspect.signature(LLMRouter.completion)
        params = set(sig.parameters.keys())
        assert "quality_level" in params, (
            "LLMRouter.completion erwartet 'quality_level', nicht 'quality'. "
            "Adapter muss explizit mappen."
        )
        assert "quality" not in params, (
            "Fehler-Alias 'quality' in LLMRouter.completion gefunden — "
            "wurde der Adapter korrekt migriert?"
        )
```

### 4.3 Schicht 3: Runtime-Schutz — `ApiAdapter`-Basisklasse

#### 4.3.1 Basisklasse in `platform_context`

```python
# platform_context/adapters/base.py
"""
ApiAdapter-Basisklasse für alle Hub ↔ iil-Package Adapter.

Erzwingt explizites Parameter-Mapping — kein blindes **kwargs-Forwarding.

Anti-Pattern (verboten):
    def completion(self, messages, **kwargs):
        return self._router.completion(messages=messages, **kwargs)  # ❌

Korrekt:
    def completion(self, messages: list[dict], quality: Quality) -> str:
        return self._router.completion(
            messages=messages,
            quality_level=quality.value,  # ✅ explizites Mapping
        )
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class ApiAdapter(ABC):
    """
    Basisklasse für alle Adapter zwischen Hub und iil-Package.

    Subklassen MÜSSEN:
    1. Alle Provider-Parameter explizit in der Methodensignatur benennen
    2. Kein **kwargs an Provider-Calls durchreichen
    3. Parameter-Mapping in der Methode dokumentieren (Kommentar: # Consumer → Provider)

    Subklassen DÜRFEN NICHT:
    - **kwargs aus Consumer-Calls blind an Provider weiterreichen
    - Provider-Parameternamen direkt dem Consumer exponieren
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name des Provider-Packages (für Logging und Fehler-Messages)."""
        ...

    def _log_call(self, method: str, **consumer_params: Any) -> None:
        """Debug-Logging für alle Adapter-Aufrufe (nur im DEBUG-Level)."""
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                "ApiAdapter call",
                extra={
                    "provider": self.provider_name,
                    "method": method,
                    "params": list(consumer_params.keys()),
                },
            )
```

#### 4.3.2 Konkreter Adapter — Explizites Mapping

```python
# apps/writing_hub/adapters/outline_adapter.py
from __future__ import annotations

from enum import Enum
from typing import Any

from platform_context.adapters.base import ApiAdapter


class Quality(str, Enum):
    DRAFT = "draft"
    STANDARD = "standard"
    PREMIUM = "premium"


class OutlineAdapter(ApiAdapter):
    """
    Adapter: writing-hub (Consumer) ↔ outlinefw.OutlineGenerator (Provider)

    Mapping-Tabelle:
      Consumer-Parameter    → Provider-Parameter
      ─────────────────────────────────────────────
      quality: Quality      → quality_level: str (quality.value)
      framework: str        → framework_key: str  (identisch, Alias vermeiden)
      llm_router: Router    → router: Router       (ältere Consumer-Annahme)
    """

    @property
    def provider_name(self) -> str:
        return "outlinefw"

    def __init__(self, router: Any) -> None:  # Consumer-Begriff: router
        from outlinefw import OutlineGenerator

        # ← Explizites Mapping: Consumer-"router" → Provider-"router" (identisch hier)
        self._generator = OutlineGenerator(router=router)

    def generate_outline(
        self,
        framework: str,           # Consumer-Begriff
        context: dict[str, Any],
        quality: Quality = Quality.STANDARD,
    ) -> dict[str, Any]:
        self._log_call("generate_outline", framework=framework, quality=quality)

        return self._generator.generate(
            framework_key=framework,          # Consumer "framework" → Provider "framework_key"
            context=context,
            quality_level=quality.value,      # Consumer Quality enum → Provider str
        )
```

#### 4.3.3 Architecture-Guardian-Regel (ADR-054)

```python
# dev-hub: apps/architecture_guardian/rules/no_kwargs_forwarding.py
"""
Guardian-Regel: Kein **kwargs-Forwarding in Adapter-Dateien.

Prüft alle apps/*/adapters/*.py — findet Muster wie:
  return self._provider.method(**kwargs)
  return self._provider.method(messages=messages, **kwargs)
"""
import re
from pathlib import Path


PATTERN = re.compile(
    r"return\s+self\._\w+\.\w+\([^)]*\*\*kwargs[^)]*\)",
    re.MULTILINE,
)


def check(repo_path: Path) -> list[str]:
    violations = []
    for adapter_file in repo_path.glob("apps/*/adapters/*.py"):
        content = adapter_file.read_text()
        if PATTERN.search(content):
            violations.append(
                f"{adapter_file.relative_to(repo_path)}: "
                f"Blindes **kwargs-Forwarding verboten (ADR-155 §4.3)"
            )
    return violations
```

### 4.4 CI-Pipeline Integration

```yaml
# .github/workflows/_ci-python.yml (Erweiterung — bestehender Reusable Workflow)

  test-contract:
    runs-on: [self-hosted, hetzner, dev]
    needs: [test-unit]
    steps:
      - uses: actions/checkout@v4

      - name: Install dependencies
        run: |
          pip install -r requirements.txt -r requirements-test.txt

      - name: Run Contract Tests
        # exit code 5 = keine Tests gefunden → als Fehler behandeln (ADR-076 §6)
        run: |
          pytest tests/contracts/ \
            -m contract \
            -v \
            --tb=short \
            --no-header \
            -p no:warnings 2>&1; \
          code=$?; \
          [ $code -eq 5 ] && { echo "FEHLER: Keine Contract-Tests in tests/contracts/ — ADR-155 erfordert mindestens 1 Contract-Test pro iil-Package-Integration"; exit 1; }; \
          exit $code

      - name: mypy Contract-Layer Check
        run: |
          mypy apps/*/adapters/ --strict --ignore-missing-imports

  # Guardian-Check (bestehender Job, erweitert)
  architecture-guardian:
    runs-on: [self-hosted, hetzner, dev]
    needs: [lint]
    steps:
      - uses: actions/checkout@v4
      - name: Check no **kwargs forwarding in adapters
        run: |
          if grep -rn "\*\*kwargs" apps/*/adapters/ 2>/dev/null | grep "return self\._"; then
            echo "FEHLER: **kwargs-Forwarding in Adapter gefunden (ADR-155 §4.3)"
            exit 1
          fi
          echo "✓ Kein **kwargs-Forwarding in Adaptern"
```

### 4.5 Checkliste für neue iil-Package Integrationen

Bei **jeder** neuen Integration eines iil-Packages in einen Hub:

```
□ 1. Contract-Test-Datei anlegen: tests/contracts/test_<package>_contract.py
□ 2. @pytest.mark.contract gesetzt
□ 3. Parameternamen aller genutzten Klassen/Methoden geprüft
□ 4. Enum/Registry-Werte aller genutzten Keys geprüft
□ 5. Historische Fehler-Namen mit assert_no_param() dokumentiert
□ 6. Adapter-Klasse von ApiAdapter erben
□ 7. Kein **kwargs-Forwarding — explizites Mapping in Kommentar dokumentiert
□ 8. mypy --strict läuft ohne Fehler für apps/*/adapters/
□ 9. py.typed im Provider-Package vorhanden (Provider-Team informieren falls fehlend)
```

---

## 5. Migration Tracking

| Repo / Component                  | Phase | Status        | Datum      | Notizen                                          |
|-----------------------------------|-------|---------------|------------|--------------------------------------------------|
| `iil-testkit` — ContractVerifier  | 1     | 🔲 offen      | –          | Neue Datei `iil_testkit/contract/verifier.py`    |
| `iil-testkit` — `__init__` Export | 1     | 🔲 offen      | –          | `from iil_testkit.contract import ContractVerifier` |
| `platform_context` — ApiAdapter   | 1     | 🔲 offen      | –          | Neue Datei `platform_context/adapters/base.py`   |
| `bfagent` — outlinefw Contract    | 2     | 🔲 offen      | –          | `tests/contracts/test_outlinefw_contract.py`     |
| `bfagent` — aifw Contract         | 2     | 🔲 offen      | –          | `tests/contracts/test_aifw_contract.py`          |
| `bfagent` — OutlineAdapter        | 2     | 🔲 offen      | –          | `apps/writing_hub/adapters/outline_adapter.py`   |
| `_ci-python.yml` — contract Job   | 1     | 🔲 offen      | –          | exit-code-5-Behandlung wie ADR-076               |
| `_ci-python.yml` — mypy adapters  | 1     | 🔲 offen      | –          | `mypy apps/*/adapters/ --strict`                 |
| Guardian-Regel no_kwargs          | 3     | 🔲 offen      | –          | Nach Phase 1+2 Stabilisierung                    |
| alle weiteren Hub-Repos           | 3     | 🔲 offen      | –          | Nach bfagent als Referenz-Implementation         |
| iil-Packages — `py.typed`         | 2     | 🔲 offen      | –          | outlinefw, aifw, promptfw als erste Kandidaten   |

---

## 6. Consequences

### 6.1 Good

- **Alle vier historischen Fehler wären verhindert worden**: Parameternamen via Layer 1+2, Enum-Werte via Layer 2, Adapter via Layer 3.
- **Breaking Changes in Packages werden sofort sichtbar**: Contract-Tests schlagen bei `pip install --upgrade outlinefw` fehl bevor Code-Änderungen nötig sind.
- **Tests dokumentieren Consumer-API-Erwartungen**: `assert_no_param(..., "llm_router")` ist lebendige Dokumentation des historischen Fehlers.
- **Adapter sind selbstdokumentierend**: Kommentar-Tabelle `Consumer-Parameter → Provider-Parameter` macht Mappings explizit sichtbar.
- **Schrittweise einführbar**: Layer 2 (iil-testkit) kann ohne Layer 1 (py.typed) starten.

### 6.2 Bad

- **Pflege-Aufwand bei Package-Updates**: Contract-Tests müssen bei API-Änderungen der Provider aktualisiert werden — aber das ist das **gewollte Signal**.
- **Initialer Aufwand**: Alle bestehenden Hub-Integrationen benötigen nachträgliche Contract-Tests.
- **py.typed in Provider-Packages**: Erfordert Koordination (beide Repos unter eigener Kontrolle — niedrige Hürde).

### 6.3 Nicht in Scope

- Semantische Contract-Tests (Rückgabewert-Shapes, Seiteneffekte) — Phase 2 / ADR-060
- Pact Broker (ADR-057: evaluate when Team > 5 Personen)
- Celery Task Payload Contracts (ADR-058 §A10 deferred — separates ADR)

---

## 7. Risks

| Risiko | W'keit | Impact | Mitigation |
|--------|--------|--------|-----------|
| Contract-Tests werden nicht geschrieben (nur als Checkliste wahrgenommen) | Mittel | Hoch | CI-Gate: leere `tests/contracts/` → Build-Fehler |
| iil-Package hat kein `py.typed` → mypy ignoriert es | Hoch | Mittel | `ignore_missing_imports = false` + explizite Fehler-Message; Provider-Update priorisieren |
| Contract-Tests werden bei Provider-Update nicht mitgepflegt | Mittel | Mittel | Das ist das gewollte Verhalten — Tests schlagen fehl → zwingt Review |
| Adapter-Basisklasse wird nicht genutzt (direkte Provider-Aufrufe) | Mittel | Hoch | Guardian-Regel prüft `apps/*/adapters/*.py` auf direktes Forwarding |
| False Sense of Security: Contract-Tests grün, semantisch falsch | Niedrig | Mittel | Akzeptiert — Scope ist Signatur, nicht Semantik (Phase 2) |

---

## 8. Confirmation

1. **CI-Gate Contract-Tests**: `pytest -m contract` im `test-contract`-Job — exit code 5 → Build-Fehler mit ADR-Hinweis
2. **mypy-Gate Adapters**: `mypy apps/*/adapters/ --strict` in `_ci-python.yml` — kein Merge bei Typ-Fehler
3. **Guardian no-kwargs-Regel**: `grep -rn "\*\*kwargs" apps/*/adapters/` — findet blindes Forwarding
4. **Drift-Detector**: Dieses ADR wird von ADR-059 auf Aktualität geprüft — Staleness-Schwelle: 12 Monate

---

## 9. More Information

- ADR-057: Platform Test Strategy — §Option 4: Pact deferred, §2.9 CI-Integration
- ADR-058: Platform Test Taxonomy — §A10 Celery Payload Contracts (deferred → dieses ADR schließt allgemeinere Lücke)
- ADR-076: bfagent CI — exit-code-5-Behandlung für leere Contract-Test-Suites
- ADR-054: Architecture Guardian — Guardian-Regel no_kwargs_forwarding
- ADR-059: Drift-Detector — Staleness-Monitoring für dieses ADR
- PEP 561: https://peps.python.org/pep-0561/ — `py.typed` Spezifikation
- Konzeptpapier (Input): Inline-Konzept aus writing-hub Session 2026-04-02

---

## 10. Changelog

| Datum      | Autor          | Änderung                                      |
|------------|----------------|-----------------------------------------------|
| 2026-04-02 | Achim Dehnert  | Initial: Status Proposed — generisches Konzept aus writing-hub Session |

---

<!--
  Drift-Detector-Felder (ADR-059):
  - staleness_months: 12
  - drift_check_paths:
      - iil-testkit/iil_testkit/contract/verifier.py
      - platform_context/platform_context/adapters/base.py
      - bfagent/tests/contracts/
  - supersedes_check: true
-->
