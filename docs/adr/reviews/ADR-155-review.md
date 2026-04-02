# ADR-155 Review: Three-Layer Contract Testing Strategy

**Reviewer:** Claude (Principal IT-Architekt-Rolle)
**Datum:** 2026-04-02
**ADR-Version:** v2 (erweitert auf 5 Aufruftypen)
**Gesamtbewertung:** ⚠️ ACCEPT WITH MANDATORY CHANGES — 4 BLOCKER müssen vor Merge behoben sein

---

## 1. Review-Tabelle

| # | Befund | Severity | Bereich | Begründung |
|---|--------|----------|---------|-----------|
| B1 | `assert_return_annotation`: `hasattr(annotation, "__origin__")` macht Assertion für ALLE generischen Typen wirkungslos | **BLOCKER** | `verifier.py:351-364` | `dict[str, Any].__origin__` existiert immer → `assert X == list or True` → Test PASSED auch wenn Typ völlig falsch |
| B2 | `assert_raises` nutzt `warnings.warn` statt `assert` — CI-Gate nicht durchsetzbar | **BLOCKER** | `verifier.py:316-323` | Test PASSED immer, auch wenn Exception-Contract verletzt — `warnings.warn` ist kein Assertion-Fail |
| B3 | `assert_return_keys` nutzt `warnings.warn` statt `assert` — Return-Shape-Contract nicht durchsetzbar | **BLOCKER** | `verifier.py:342-349` | Gleiche Ursache wie B2: Test PASSED immer |
| B4 | `TaskContractVerifier.__init__`: `getattr(task, "run", task)` → Fallback auf nicht-callable Objekt → `inspect.signature()` wirft `TypeError` | **BLOCKER** | `verifier.py:430` | Für `@shared_task`-dekorierte Funktionen ohne `.run`-Attribut fällt der Verifier auf die Task-Instanz zurück, die `inspect.signature()` nicht verarbeiten kann |
| K1 | `_assert_params` prüft nur `missing` (Consumer-Erwartungen) — nicht ob Provider neue Required-Params hinzugefügt hat | **KRITISCH** | `verifier.py:369-379` | Breaking Change: Provider fügt `tenant_id` als Pflichtparam hinzu → Consumer crasht in Produktion — Contract-Test bleibt grün |
| K2 | Guardian-Regex `r"return\s+self\._\w+\.\w+\([^)]*\*\*kwargs[^)]*\)"` erkennt indirektes `**kwargs`-Forwarding nicht | **KRITISCH** | `no_kwargs_forwarding.py` | Pattern `result = self._x.m(**kwargs); return result` wird nicht gefunden — häufiges Refactoring-Ergebnis |
| K3 | `for_response_schema` in Klassen-Docstring versprochen aber nie implementiert | **KRITISCH** | `verifier.py:217` | Nutzer implementiert Contract-Test gegen nicht-existierende API → ImportError zur Laufzeit |
| H1 | `mypy --strict` + `ignore_missing_imports = false` bricht Pipeline für alle ungetypten Third-Party-Packages (Django, Celery etc.) | **HOCH** | CI yaml + mypy config | `ignore_missing_imports = false` wirft Fehler für ALLE Imports ohne `py.typed`, inkl. Django selbst — Pipeline-Breaking von Tag 1 |
| H2 | `assert_raises` prüft Docstring-Format `:raises ExcType:` — semantisch falsch: Contract ist Verhalten, nicht Dokumentation | **HOCH** | `verifier.py:296-323` | Methode heißt `assert_raises` (impliziert Verhaltenstest wie `pytest.raises`) — liefert aber nur Doku-Lint; irreführend und schwächer als nötig |
| H3 | `conftest.py` im ADR erwähnt aber Inhalt fehlt komplett — `@pytest.mark.contract` erzeugt `PytestUnknownMarkWarning` | **HOCH** | `tests/contracts/conftest.py` | Ohne Marker-Registration in `conftest.py` oder `pyproject.toml` gibt es Warnings die CI-Output verschmutzen und bei `--strict-markers` zu Fehlern führen |
| H4 | `iil_testkit/contract/__init__.py` fehlt — keine definierten Exports | **HOCH** | `iil_testkit/contract/` | `from iil_testkit.contract import ContractVerifier` wirft `ImportError` — Package-Struktur unvollständig |
| M1 | Confirmation §2 nennt `apps/*/services.py` für mypy — CI-YAML zeigt nur `apps/*/adapters/` | **MEDIUM** | §8 vs §4.4 | Inkonsistenz: Entweder CI-Job anpassen oder Confirmation korrigieren |
| M2 | Return-Shape via Docstring-Analyse ist falscher Ansatz — `TypedDict`/Pydantic wäre static + runtime | **MEDIUM** | §4.2 | Docstring-Prüfung ist Dokumentations-Linter, kein echter Contract. TypedDict gibt mypy-Prüfung + Runtime-Sicherheit gratis |
| M3 | Factory-Methoden (`for_callable`, `for_task`) geben andere Typen zurück als `ContractVerifier` — kein gemeinsames Protocol | **MEDIUM** | `verifier.py:234-242` | Keine gemeinsame Basis → keine einheitliche Typisierung → Nutzer kann nicht `verifier: BaseContractVerifier` als Parameter-Typ angeben |
| M4 | `assert_init_params` prüft NUR ob expected-Params existieren — nicht ob required ohne Default vorhanden sind | **MEDIUM** | `verifier.py:246-248` | `OutlineGenerator(router=r, extra="x")` würde Provider-seitig `TypeError` geben — Consumer-Test bleibt grün |

---

## 2. Detail-Analyse der BLOCKER

### B1 — `assert_return_annotation` immer True für Generics

```python
# Fehlerhafter Code (ADR §4.2.1, Zeile 361-364):
assert annotation == expected_type or (
    hasattr(annotation, "__origin__")
)

# Beweis:
annotation = dict[str, Any]   # Consumer schreibt dict[str, Any]
expected_type = list           # Falsche Erwartung
# → annotation == list → False
# → hasattr(dict[str,Any], "__origin__") → True (weil dict[str,Any] ist Generic)
# → False or True → True → Test PASSES obwohl Typ falsch!
```

### B2+B3 — `warnings.warn` ist kein CI-Gate

```python
# Fehlerhaft:
if f":raises {exc_name}:" not in docstring:
    warnings.warn(...)          # ← gibt nur Warning aus, Test läuft weiter!

# CI sieht:  PASSED (mit Warning-Output)
# Korrekt:
assert f":raises {exc_name}:" in docstring, f"..."  # ← Test schlägt fehl
```

### B4 — `TaskContractVerifier` mit nicht-callable Fallback

```python
# Fehlerhaft:
self._func = getattr(task, "run", task)  # ← Fallback: task selbst (nicht callable)

# @shared_task(name="analyze_document")
# def analyze_document_task(document_id: int): ...
# → task.run existiert nicht als eigene Funktion bei simplen shared_tasks
# → inspect.signature(task_instance) → TypeError: not a callable object

# Korrekt — Celery Task Signatur abrufen:
from celery import Task
if isinstance(task, Task):
    self._func = task.run  # Bound Task
else:
    self._func = task      # Direkte Funktion (schon callable)
```

---

## 3. Alternativen-Bewertung

### Alternative A: TypedDict statt Docstring für Return-Shape-Contracts (empfohlen für §4.2)

```python
# Statt Docstring-Inspection:
class AnalysisResult(TypedDict):
    fit_score: float
    skills: list[str]
    recommendation: str

def analyze_cv_with_llm(text: str, project_requirements: str) -> AnalysisResult:
    ...

# Contract-Test:
def test_return_type_annotation() -> None:
    import inspect
    from apps.candidates.llm_service import analyze_cv_with_llm, AnalysisResult
    sig = inspect.signature(analyze_cv_with_llm)
    assert sig.return_annotation is AnalysisResult
```

**Trade-off:** Mehr Aufwand bei der Erstellung (TypedDict-Klassen schreiben), aber:
- mypy prüft Rückgabewerte statisch → Fehler zur Compile-Zeit
- Runtime-Prüfung möglich (`isinstance(result, dict)` + `result.keys()`)
- Contract ist self-documenting in der Signatur, nicht im Docstring versteckt

### Alternative B: `@documents_raises`-Dekorator für Exception-Contracts

```python
# Dekorator in platform_context — macht Exceptions maschinenlesbar:
@documents_raises(DocumentUploadError, ValidationError)
def validate_file(self, file: File) -> None:
    ...

# Contract-Test:
def test_exception_contract() -> None:
    from apps.services import DocumentService, DocumentUploadError
    declared = get_documented_raises(DocumentService.validate_file)
    assert DocumentUploadError in declared
```

**Trade-off:** Requires platform_context-Erweiterung, aber Exception-Contracts sind strukturell verankert — nicht Docstring-abhängig.

---

## 4. Vollständiger Implementierungsplan

### Phase 1 — Core Infrastructure (iil-testkit + platform_context)

```
iil-testkit/
├── iil_testkit/
│   └── contract/
│       ├── __init__.py          ← NEW: Exports + __all__
│       ├── verifier.py          ← FIX: alle 4 BLOCKER behoben
│       └── decorators.py        ← NEW: @documents_raises
platform_context/
└── platform_context/
    └── adapters/
        └── base.py              ← NEW: ApiAdapter base class
```

### Phase 2 — Per-Hub Contract-Tests (bfagent als Referenz)

```
bfagent/
└── tests/
    └── contracts/
        ├── conftest.py          ← NEW: Marker-Registration
        ├── test_outlinefw_contract.py
        ├── test_aifw_contract.py
        ├── test_document_service_contract.py
        ├── test_celery_tasks_contract.py
        └── test_llm_service_contract.py
```

### Phase 3 — CI + Guardian

```
.github/workflows/
└── _ci-python.yml               ← FIX: mypy scope, exit-5, Guardian
dev-hub/
└── apps/architecture_guardian/
    └── rules/
        └── no_kwargs_forwarding.py  ← FIX: erweiterte Regex
```

### Phase 4 — Alle weiteren Hubs (nach bfagent als Muster)
