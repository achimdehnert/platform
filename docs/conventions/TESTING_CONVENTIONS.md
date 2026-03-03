# Testing Conventions — Platform Python Packages

> **Verbindlich für alle Repos:** `aifw`, `authoringfw`, `promptfw`, `weltenfw`, `riskfw`, `nl2cad`, `iil-nl2cadfw`  
> Abgeleitet aus 5 CI-Failures vom 2026-03-03 (authoringfw v0.6.0 tag).

---

## T-01 — Optionale Dependencies: `pytest.importorskip()`

### Problem
Wenn ein Package eine optionale Dependency hat (z.B. `[project.optional-dependencies] aifw = [...]`),
installiert CI nur `.[dev]` — die optionale Dep fehlt. Ein direkter Import führt zu `ModuleNotFoundError`
und einem **FAIL** statt einem **SKIP**.

### Regel
```python
# FALSCH — crashed wenn aifw nicht installiert
from aifw.schema import LLMResult

def test_should_verify_llm_result_fields():
    result = LLMResult(...)
    ...

# RICHTIG — skip wenn aifw nicht installiert
def test_should_verify_llm_result_fields():
    aifw_schema = pytest.importorskip("aifw.schema", reason="aifw not installed")
    LLMResult = aifw_schema.LLMResult
    result = LLMResult(...)
    ...
```

### Anwendung
- Jede Test-Funktion die ein optionales Modul importiert **muss** `pytest.importorskip()` am Anfang der Funktion verwenden
- `pytest.importorskip()` **nicht** auf Modul-Ebene (würde alle Tests in der Datei skippen)
- Gilt auch für cross-package Tests (z.B. `authoringfw` testet gegen `aifw`)

### Betroffene Repos
| Repo | Optionale Dep | Tests die importorskip brauchen |
|------|-------------|--------------------------------|
| `authoringfw` | `iil-aifw` | `test_contracts.py` |
| `promptfw` | `iil-aifw` (future) | bei Bedarf |

---

## T-02 — Async Mocks: `side_effect` statt `wraps`

### Problem
`AsyncMock(wraps=sync_lambda)` ruft das Lambda auf, das eine Coroutine zurückgibt.
`AsyncMock` awaitet den `wraps`-Return **nicht** — gibt die Coroutine-Referenz roh weiter.
Das führt zu `AttributeError: 'coroutine' object has no attribute 'content'`.

### Regel
```python
# FALSCH — wraps mit sync lambda liefert coroutine-Objekt
with patch.object(orch, "_call_llm_async",
    new=AsyncMock(wraps=lambda msgs, cfg, ql, t: _fake_async(**kwargs))):
    ...

# RICHTIG — side_effect mit echter async-Funktion
async def _fake_llm_async(msgs, cfg, quality_level, task):
    captured["quality_level"] = quality_level
    return _make_llm_result()

with patch.object(orch, "_call_llm_async", side_effect=_fake_llm_async):
    ...

# AUCH RICHTIG — AsyncMock(return_value=...) für einfache Fälle
with patch.object(orch, "_call_llm_async", new=AsyncMock(return_value=llm_result)):
    ...
```

### Entscheidungsbaum
```
Async Mock nötig?
    ├─ Einfaches return_value → AsyncMock(return_value=...)
    ├─ Seiteneffekte prüfen / capture kwargs → side_effect=async_fn
    └─ NIEMALS wraps=sync_callable für async behaviour
```

---

## T-03 — Exception-Tests: Fehler-Contracts explizit testen

### Problem
Wenn sich das Verhalten einer Funktion von "stillem Fallback" zu "explizitem Fehler" ändert,
muss der Test mitgeändert werden. Ein Test der `get_format("unknown")` aufruft und ein Objekt
erwartet, schlägt nach dem Fix fehl — weil jetzt `KeyError` geworfen wird.

### Regel
```python
# FALSCH — testet altes Fallback-Verhalten das behoben wurde
def test_unknown_format_fallback():
    fmt = get_format("unknown_xyz")
    fields = fmt.planning_fields          # AttributeError wenn KeyError kommt
    assert isinstance(fields, PlanningFieldConfig)

# RICHTIG — testet explizit dass KeyError geworfen wird
def test_unknown_format_raises_key_error():
    """get_format() raises KeyError for unknown format keys (no silent fallback)."""
    with pytest.raises(KeyError):
        get_format("unknown_xyz")
```

### Konsequenz
- Wenn eine Funktion von "return default" auf "raise Exception" umgestellt wird:
  **immer** auch den Test anpassen
- Fehler-Contracts sind **features**, nicht Bugs — sie müssen explizit getestet werden
- Test-Name sollte das Verhalten beschreiben: `test_should_raise_...` statt `test_..._fallback`

---

## Checkliste vor Commit (Python Packages)

```
[ ] T-01: Importiere ich ein optionales Package direkt auf Modul-Ebene?
          → pytest.importorskip() innerhalb der Test-Funktion verwenden

[ ] T-02: Nutze ich AsyncMock(wraps=...)?
          → In AsyncMock(side_effect=async_fn) oder AsyncMock(return_value=...) umwandeln

[ ] T-03: Testet ein Test altes "Fallback"-Verhalten das inzwischen eine Exception wirft?
          → pytest.raises(ExcType) verwenden, Test-Name anpassen

[ ] Alle Tests lokal grün: `make test` oder `pytest tests/ -v`
[ ] CI test-gate ist in publish.yml vorhanden (`needs: test`)
```

---

## Scan-Befehl (Quick Check)

```bash
# T-01: Direkte optionale Imports auf Modul-Ebene suchen
grep -rn "^from aifw" tests/ 2>/dev/null && echo "T-01 VIOLATION" || echo "T-01 OK"
grep -rn "^import aifw" tests/ 2>/dev/null && echo "T-01 VIOLATION" || echo "T-01 OK"

# T-02: AsyncMock(wraps= suchen
grep -rn "AsyncMock(wraps=" tests/ 2>/dev/null && echo "T-02 VIOLATION" || echo "T-02 OK"

# T-03: Pattern 'fallback' in Testnamen (Hinweis, kein Block)
grep -rn "def test_.*fallback" tests/ 2>/dev/null && echo "T-03 REVIEW" || echo "T-03 OK"
```

---

## Audit-Log

| Datum | Repo | Fehler | Fix | Regel |
|-------|------|--------|-----|-------|
| 2026-03-03 | authoringfw | `ModuleNotFoundError: No module named 'aifw'` in `test_contracts.py` | `pytest.importorskip()` | T-01 |
| 2026-03-03 | authoringfw | `'coroutine' object has no attribute 'content'` in `test_async_execute.py` | `side_effect=async_fn` | T-02 |
| 2026-03-03 | authoringfw | `KeyError: 'unknown_xyz'` in `test_planning.py` | `pytest.raises(KeyError)` | T-03 |

---

*Platform Testing Conventions v1.0 — 2026-03-03*
