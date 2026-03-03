---
description: Testing Conventions prüfen und anwenden — T-01 importorskip, T-02 AsyncMock, T-03 Exception-Contracts
---

# Testing Conventions Check

> Trigger: Vor jedem Package-Release, nach Test-Failures, beim Schreiben neuer Tests.
> Referenz: `docs/conventions/TESTING_CONVENTIONS.md`

## Schritt 1: Scan auf T-01 Violations (optionale Imports)

Prüfe ob optionale Packages direkt auf Modul-Ebene importiert werden:

```bash
# Im jeweiligen Repo-Verzeichnis:
grep -rn "^from aifw" tests/
grep -rn "^import aifw" tests/
grep -rn "^from promptfw" tests/
grep -rn "^from weltenfw" tests/
```

**Fix wenn Violation gefunden:**
```python
# Ersetze:
from aifw.schema import LLMResult
def test_foo():
    ...

# Mit:
def test_foo():
    aifw_schema = pytest.importorskip("aifw.schema", reason="aifw not installed")
    LLMResult = aifw_schema.LLMResult
    ...
```

## Schritt 2: Scan auf T-02 Violations (AsyncMock wraps)

```bash
grep -rn "AsyncMock(wraps=" tests/
```

**Fix wenn Violation gefunden:**
```python
# Ersetze:
AsyncMock(wraps=lambda msgs, cfg, ql, t: some_coro_fn(...))

# Mit einer der beiden Alternativen:
# Option A — return_value (einfach)
AsyncMock(return_value=expected_result)

# Option B — side_effect (wenn kwargs capturen nötig)
async def _fake(msgs, cfg, quality_level, task):
    captured.update({"quality_level": quality_level})
    return expected_result

AsyncMock(side_effect=_fake)  # KEIN new= nötig bei side_effect
# ODER:
new=AsyncMock(side_effect=_fake)
```

## Schritt 3: Scan auf T-03 Violations (Fallback-Tests)

```bash
grep -rn "def test_.*fallback" tests/
```

Für jeden Treffer prüfen:
- Erwartet der Test einen Return-Wert wo jetzt eine Exception geworfen wird?
- Wenn ja: `pytest.raises(ExcType)` verwenden, Testname auf `test_should_raise_...` umbenennen

## Schritt 4: Full Test Run

```bash
make test
# oder:
pytest tests/ -v --tb=short
```

Erwartung: **0 failed**. Bei Failures:
1. Error-Message lesen
2. Zu T-01/T-02/T-03 Regel mappen
3. Fix aus `TESTING_CONVENTIONS.md` anwenden

## Schritt 5: CI Gate prüfen

Sicherstellen dass `publish.yml` ein `needs: test` Gate hat:

```yaml
jobs:
  test:
    name: Tests (publish gate)
    ...
  build:
    needs: test   # <-- muss vorhanden sein
    ...
  publish-pypi:
    needs: build  # <-- kaskadiert automatisch
    ...
```

## Wann ausführen?

- **Vor jedem `git tag vX.Y.Z`** (Package-Release)
- **Nach CI-Failures** die Tests betreffen
- **Beim Schreiben neuer Tests** die externe Packages importieren
- **Beim Upgrade** einer optionalen Dependency
