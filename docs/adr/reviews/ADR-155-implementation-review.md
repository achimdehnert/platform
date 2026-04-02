# ADR-155 — Vollständiges Architektur-Review & Implementierungsplan

**Reviewer:** Principal IT-Architekt (Cascade)
**Datum:** 2026-04-02
**ADR-Version:** v2 → v3 (erweitert auf 5 Aufruftypen + alle Fixes)
**Input-Dokumente:**
- `docs/adr/inputs/ADR-155-api-contract-testing.md` (Konzeptpapier v1)
- `docs/adr/ADR-155-contract-testing-strategy.md` (ADR v2)
- `docs/adr/reviews/ADR-155-review.md` (Reviewer-Befunde: 4 BLOCKER, 3 KRITISCH, 4 HOCH, 4 MEDIUM)
- `docs/adr/inputs/ADR 115 input/*.py` (korrigierte Implementierungen)

**Gesamtbewertung:** ⚠️ ACCEPT WITH MANDATORY CHANGES → ✅ APPROVED nach Einarbeitung aller Fixes

---

## 1. Review-Tabelle — Konsolidierte Befunde + Korrekturen

| # | Befund | Severity | Status | Korrektur (Datei) |
|---|--------|----------|--------|-------------------|
| B1 | `assert_return_annotation`: `hasattr(__origin__)` Short-Circuit → Generics-Test immer True | **BLOCKER** | ✅ FIXED | `verifier.py:255-259` — Direkter `==`-Vergleich + neues `assert_return_origin()` für Generics |
| B2 | `assert_raises`: `warnings.warn` statt `assert` → kein CI-Gate | **BLOCKER** | ✅ FIXED | `verifier.py:213-219` — `assert` mit Sphinx+Google-Style Docstring-Match |
| B3 | `assert_return_keys`: `warnings.warn` statt `assert` → kein CI-Gate | **BLOCKER** | ✅ FIXED | `verifier.py:305-311` — `assert` mit TypedDict-Empfehlung in Message |
| B4 | `TaskContractVerifier`: `getattr(task, "run", task)` Fallback auf nicht-callable | **BLOCKER** | ✅ FIXED | `verifier.py:461-498` — `_resolve_task_function()` mit `inspect.unwrap()` + `type(task).run` + callable-Fallback |
| K1 | `_assert_params` nur unidirektional — neue Required-Params nicht erkannt | **KRITISCH** | ✅ FIXED | `verifier.py:322-369` — `exhaustive=True` prüft beide Richtungen |
| K2 | Guardian-Regex erkennt indirektes `**kwargs`-Forwarding nicht | **KRITISCH** | ✅ FIXED | `no_kwargs_forwarding.py:28-52` — 3 Patterns (direkt, Zuweisung, pur) + Allowlist-Kommentar |
| K3 | `for_response_schema` im Docstring versprochen, nie implementiert | **KRITISCH** | ✅ FIXED | `verifier.py:535-575` — `ResponseShapeVerifier` mit `assert_response()`, `assert_response_types()`, `assert_status_code()` |
| H1 | `mypy --strict` + `ignore_missing_imports=false` bricht Pipeline für Django/Celery | **HOCH** | ✅ FIXED | `pyproject_mypy_snippet.toml` — Default `ignore_missing_imports=true`, explicit `false` nur für `py.typed`-Packages |
| H2 | `assert_raises` prüft Doku statt Verhalten — irreführender Name | **HOCH** | ✅ FIXED | Docstring klargestellt: "DEKLARATION, nicht Verhalten. Für Verhaltenstest: `pytest.raises()`" |
| H3 | `conftest.py` erwähnt aber Inhalt fehlt — `PytestUnknownMarkWarning` | **HOCH** | ✅ FIXED | `contracts_conftest.py` — `pytest_configure()` mit Marker-Registration |
| H4 | `iil_testkit/contract/__init__.py` fehlt — `ImportError` | **HOCH** | ✅ FIXED | `contract_init.py` — Exports + `__all__` |
| M1 | Confirmation §2 nennt `services.py`, CI-YAML nur `adapters/` | **MEDIUM** | ✅ FIXED | `ci_contract_jobs.yml` — Separater mypy-Step für Service-Layer (non-strict, progressiv) |
| M2 | Return-Shape via Docstring statt TypedDict/Pydantic | **MEDIUM** | ✅ ADDRESSED | TypedDict als empfohlene Alternative dokumentiert in `assert_return_keys()` Docstring |
| M3 | Factory-Methoden geben verschiedene Typen zurück — kein Protocol | **MEDIUM** | ✅ FIXED | `BaseContractVerifier(ABC)` als gemeinsame Basis mit `assert_params()` + `assert_no_param()` |
| M4 | `assert_init_params` prüft nicht ob required ohne Default vorhanden | **MEDIUM** | ✅ FIXED | Über `exhaustive=True` Parameter in `assert_init_params()` / `assert_method_params()` |

---

## 2. Zusätzliche Architektur-Entscheidungen (über Review hinaus)

### 2.1 TypedDict als empfohlener Return-Contract (Alternative A aus Review)

**Entscheidung:** TypedDict ist der bevorzugte Mechanismus für Return-Shape-Contracts ab Phase 2.

```python
# EMPFOHLEN ab Phase 2:
from typing import TypedDict

class AnalysisResult(TypedDict):
    fit_score: float
    skills: list[str]
    summary: str
    experience_years: int | None
    fit_reasoning: str

def analyze_cv_with_llm(text: str, ...) -> AnalysisResult: ...
```

**Trade-off:** Mehr initialer Aufwand → aber mypy prüft statisch + Runtime-Prüfung möglich + self-documenting.

### 2.2 `@documents_raises`-Dekorator (Alternative B aus Review)

**Entscheidung:** Deferred auf Phase 3. `assert_raises` mit Docstring-Gate ist ausreichend für Phase 1-2. Dekorator-basiertes Exception-Contract erst wenn Docstring-Ansatz sich als zu fragil erweist.

**Begründung:** YAGNI für 1-Entwickler-Team — Docstring-Disziplin ist mit CI-Gate durchsetzbar.

### 2.3 `assert_is_acks_late` für Celery Tasks

**Entscheidung:** Platform-Standard `acks_late=True` wird als Contract-Assertion in `TaskContractVerifier` aufgenommen. Kein neuer ADR nötig — ist bestehender Standard.

---

## 3. Vollständiger Implementierungsplan

### Phase 1 — Core Infrastructure (Sprint 1, ~3 Tage)

| # | Datei | Aktion | Repo | Abhängigkeit |
|---|-------|--------|------|-------------|
| 1.1 | `iil_testkit/contract/__init__.py` | NEU | iil-testkit | — |
| 1.2 | `iil_testkit/contract/verifier.py` | NEU | iil-testkit | — |
| 1.3 | `platform_context/adapters/__init__.py` | NEU (leer) | platform_context | — |
| 1.4 | `platform_context/adapters/base.py` | NEU | platform_context | — |
| 1.5 | `iil-testkit` → PyPI Release | `bump2version minor` + publish | iil-testkit | 1.1, 1.2 |
| 1.6 | `platform_context` → PyPI Release | `bump2version minor` + publish | platform_context | 1.3, 1.4 |

### Phase 2 — Referenz-Implementation (Sprint 2, ~3 Tage)

| # | Datei | Aktion | Repo | Abhängigkeit |
|---|-------|--------|------|-------------|
| 2.1 | `tests/contracts/conftest.py` | NEU | bfagent / recruiting-hub | 1.5 |
| 2.2 | `tests/contracts/test_outlinefw_contract.py` | NEU | bfagent | 1.5 |
| 2.3 | `tests/contracts/test_aifw_contract.py` | NEU | bfagent | 1.5 |
| 2.4 | `tests/contracts/test_document_service_contract.py` | NEU | recruiting-hub | 1.5 |
| 2.5 | `tests/contracts/test_llm_service_contract.py` | NEU | recruiting-hub | 1.5 |
| 2.6 | `tests/contracts/test_celery_tasks_contract.py` | NEU | bfagent / recruiting-hub | 1.5 |
| 2.7 | `pyproject.toml` — mypy + markers | EDIT | bfagent / recruiting-hub | — |
| 2.8 | iil-Packages — `py.typed` Marker | NEU | outlinefw, aifw, promptfw | — |

### Phase 3 — CI + Guardian (Sprint 3, ~2 Tage)

| # | Datei | Aktion | Repo | Abhängigkeit |
|---|-------|--------|------|-------------|
| 3.1 | `.github/workflows/_ci-python.yml` | EDIT: `test-contract` + `architecture-guardian` Jobs | platform | 2.x |
| 3.2 | `no_kwargs_forwarding.py` | NEU | dev-hub | — |
| 3.3 | CI testen: bfagent + recruiting-hub | VERIFY | bfagent, recruiting-hub | 3.1 |

### Phase 4 — Rollout alle Hubs (Sprint 4+, fortlaufend)

| # | Aktion | Repos |
|---|--------|-------|
| 4.1 | `tests/contracts/conftest.py` + mindestens 1 Contract-Test | Alle Hubs mit iil-Package-Integration |
| 4.2 | `pyproject.toml` mypy-Config | Alle Hubs |
| 4.3 | TypedDict für Return-Shapes einführen (Progressive) | Service-Layer in allen Hubs |

---

## 4. Produktionsreife Dateien — Übersicht

Alle korrigierten Dateien liegen produktionsreif vor:

| Datei | Pfad im Ziel-Repo | Quelle (Input) | LOC |
|-------|-------------------|-----------------|-----|
| `verifier.py` | `iil-testkit/iil_testkit/contract/verifier.py` | `ADR 115 input/verifier.py` | 575 |
| `__init__.py` | `iil-testkit/iil_testkit/contract/__init__.py` | `ADR 115 input/contract_init.py` | 30 |
| `base.py` | `platform_context/platform_context/adapters/base.py` | `ADR 115 input/api_adapter_base.py` | 106 |
| `conftest.py` | `<hub>/tests/contracts/conftest.py` | `ADR 115 input/contracts_conftest.py` | 24 |
| `no_kwargs_forwarding.py` | `dev-hub/apps/architecture_guardian/rules/no_kwargs_forwarding.py` | `ADR 115 input/no_kwargs_forwarding.py` | 126 |
| `_ci-python.yml` (Snippet) | `platform/.github/workflows/_ci-python.yml` | `ADR 115 input/ci_contract_jobs.yml` | 106 |
| `pyproject.toml` (Snippet) | `<hub>/pyproject.toml` | `ADR 115 input/pyproject_mypy_snippet.toml` | 47 |

---

## 5. Architektur-Diagramm — Contract-Test-Schichten

```
┌────────────────────────────────────────────────────────────────────┐
│                        CI Pipeline (_ci-python.yml)                │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌─── Schicht 1: Statisch ──────────────────────────────────────┐ │
│  │  mypy --strict apps/*/adapters/                              │ │
│  │  mypy apps/*/services.py (progressiv)                        │ │
│  │  → Fängt: Parameternamen-Fehler, Typ-Mismatch               │ │
│  │  → Voraussetzung: py.typed in Provider-Packages              │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                    │
│  ┌─── Schicht 2: Strukturell (pytest -m contract) ──────────────┐ │
│  │  ContractVerifier(Class)        → Package-API, Service-Layer │ │
│  │  ContractVerifier.for_callable  → Freie Funktionen           │ │
│  │  ContractVerifier.for_task      → Celery Tasks               │ │
│  │  ResponseShapeVerifier          → REST API Responses         │ │
│  │  → Fängt: Param-Drift, Enum-Drift, Exception-Contract,      │ │
│  │           Return-Shape, neue Required-Params (exhaustive)    │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                    │
│  ┌─── Schicht 3: Architecture Guardian ─────────────────────────┐ │
│  │  no_kwargs_forwarding.py        → **kwargs-Forwarding        │ │
│  │  Contract-Test-Existenz         → tests/contracts/ nicht leer│ │
│  │  py.typed-Check                 → Provider hat py.typed      │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                    │
├────────────────────────────────────────────────────────────────────┤
│                     Runtime (Production)                           │
│  ┌─── Schicht 3b: ApiAdapter ───────────────────────────────────┐ │
│  │  Explizites Parameter-Mapping                                │ │
│  │  Debug-Logging + Error-Logging                               │ │
│  │  Kein **kwargs-Forwarding                                    │ │
│  └──────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────┘
```

---

## 6. Risiko-Matrix nach Fixes

| Risiko | Vor Fixes | Nach Fixes | Mitigation |
|--------|-----------|------------|-----------|
| Contract-Tests grün obwohl Contract verletzt | 🔴 4 BLOCKER | ✅ Alle fixed | B1-B4 behoben, exhaustive-Mode |
| Neue Required-Params unentdeckt | 🔴 KRITISCH | ✅ Fixed | `exhaustive=True` (K1) |
| Indirektes **kwargs-Forwarding | 🔴 KRITISCH | ✅ Fixed | 3 Pattern-Regeln (K2) |
| Pipeline bricht wegen ungetypter Packages | 🟡 HOCH | ✅ Fixed | `ignore_missing_imports=true` als Default (H1) |
| False Sense of Security bei Docstring-Contracts | 🟡 HOCH | 🟡 Akzeptiert | TypedDict als Phase-2-Upgrade (M2) |

---

## 7. Nächste Schritte

1. **ADR-155 v3 erstellen** — alle Fixes aus diesem Review einarbeiten
2. **Phase 1 starten** — `verifier.py` + `__init__.py` in iil-testkit
3. **Phase 2** — recruiting-hub als Referenz-Implementation (bereits teilweise vorhanden)
4. **ADR-058 §A10 schließen** — Verweis auf ADR-155 TaskContractVerifier

---

*Generiert: 2026-04-02 | Basis: ADR-155-review.md + ADR 115 input/*
