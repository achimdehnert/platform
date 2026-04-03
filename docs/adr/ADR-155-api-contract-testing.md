# ADR-155: API Contract Testing für iil-Package Integrationen

**Status:** Accepted  
**Datum:** 2026-04-02  
**Kontext:** Platform (alle iil-Packages)  

## Kontext

In den letzten Sessions traten mehrere Fehler auf, die alle dieselbe Ursache hatten:
**API-Mismatch zwischen Consumers (z.B. writing-hub) und Providers (iil-Packages)**.

### Aufgetretene Fehler (writing-hub ↔ outlinefw/aifw)

| Fehler | Ursache | Hätte Test gefunden? |
|--------|---------|---------------------|
| `OutlineGenerator.__init__() got an unexpected keyword argument 'llm_router'` | Parameter heißt `router`, nicht `llm_router` | ✅ JA |
| `OutlineGenerator.generate() got an unexpected keyword argument 'framework'` | Parameter heißt `framework_key`, nicht `framework` | ✅ JA |
| `Unknown framework key: 'scientific_essay'` | Framework existiert nicht in outlinefw | ✅ JA |
| `Unrecognized request argument supplied: quality` | LLMRouter erwartet `quality_level`, nicht `quality` | ✅ JA |

**Alle diese Fehler wären durch Contract-Tests vermeidbar gewesen.**

## Entscheidung

### 1. Contract-Tests für alle iil-Package Integrationen

Jede Integration mit einem iil-Package erhält einen Contract-Test, der:
- Die erwartete API-Signatur prüft
- Parameter-Namen validiert
- Enum-Werte und Typen verifiziert

```python
# tests/contracts/test_outlinefw_contract.py
def test_outline_generator_init_signature():
    """Verify OutlineGenerator.__init__ accepts 'router' parameter."""
    from outlinefw import OutlineGenerator
    import inspect
    
    sig = inspect.signature(OutlineGenerator.__init__)
    params = list(sig.parameters.keys())
    
    assert "router" in params, "Expected 'router' parameter"
    assert "llm_router" not in params, "Wrong param name: use 'router'"

def test_outline_generator_generate_signature():
    """Verify OutlineGenerator.generate() parameter names."""
    from outlinefw import OutlineGenerator
    import inspect
    
    sig = inspect.signature(OutlineGenerator.generate)
    params = list(sig.parameters.keys())
    
    assert "framework_key" in params
    assert "context" in params
    assert "framework" not in params  # Common mistake
    assert "chapter_count" not in params  # Doesn't exist
```

### 2. Adapter-Pattern mit explizitem Parameter-Mapping

Adapter zwischen Packages müssen Parameter explizit mappen, nicht blind durchreichen:

```python
# FALSCH: Blind durchreichen
def completion(self, messages, **kwargs):
    return self._router.completion(messages=messages, **kwargs)  # ❌

# RICHTIG: Explizites Mapping
def completion(self, messages, **kwargs):
    router_kwargs = {}
    if "quality" in kwargs:
        quality = kwargs.pop("quality")
        router_kwargs["quality_level"] = quality.value  # ✅ Mapping
    return self._router.completion(messages=messages, **router_kwargs)
```

### 3. CI-Pipeline Integration

```yaml
# .github/workflows/ci.yml
jobs:
  contract-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run contract tests
        run: pytest tests/contracts/ -v --tb=short
```

### 4. Test-Struktur (pro Consumer-Repo)

```
tests/
├── contracts/                    # API Contract Tests
│   ├── test_outlinefw_contract.py
│   ├── test_aifw_contract.py
│   ├── test_promptfw_contract.py
│   ├── test_weltenfw_contract.py
│   └── test_authoringfw_contract.py
└── ...
```

### 5. Contract-Test Checkliste für neue Integrationen

Bei jeder neuen iil-Package Integration:

- [ ] API-Signatur-Test für Hauptklassen
- [ ] Parameter-Namen-Validierung
- [ ] Enum/Type-Mapping dokumentiert
- [ ] Adapter mit explizitem Mapping (kein `**kwargs` durchreichen)
- [ ] Fallback für unbekannte Parameter

## Konsequenzen

### Positiv
- API-Mismatches werden vor Deployment erkannt
- Breaking Changes in Packages werden sofort sichtbar
- Dokumentation der erwarteten API im Test-Code
- Schnellere Fehlerdiagnose

### Negativ
- Zusätzlicher Test-Aufwand bei Package-Updates
- Tests müssen bei API-Änderungen aktualisiert werden

## Referenzen

- [Consumer-Driven Contract Testing](https://martinfowler.com/articles/consumerDrivenContracts.html)
- ADR-058: Platform Test Taxonomy
- ADR-097: aifw Implementation Contract
