# ADR-121: iil-outlinefw — Zentrales Story-Outline-Framework

> **Umnummeriert von ADR-100** (Nummernkonflikt mit ADR-100-iil-testkit)

```yaml
status: accepted
date: 2026-03-08
decision-makers: [achim.dehnert]
tags: [writing-hub, travel-beat, bfagent, coach-hub, outline, pypi, iil-packages, creative-writing]
drift-detector: paths=[outlinefw/src/outlinefw/], adr=ADR-121
related: [ADR-083-writing-hub, iil-authoringfw, iil-aifw, iil-promptfw]
```

---

## Kontext und Problemstellung

Drei Applikationen (writing-hub, travel-beat, bfagent) implementieren Story-Outline-Logik
unabhängig voneinander:

| Repo | Duplication |
|------|-------------|
| `bfagent` | `OutlineGenerationHandler`, `EnhancedSaveTheCatOutlineHandler`, `OutlineGeneratorService` |
| `travel-beat` | `StoryOutline` Model, `OutlineEngine`, `OutlineValidator`, `SAVE_THE_CAT_BEATS` |
| `writing-hub` | `OutlineGeneratorService`, `FRAMEWORKS` dict, `_parse_nodes()` |

Konkrete Duplikationen:
- **FRAMEWORKS dict**: 3× (Three-Act, Save the Cat, Hero's Journey, Five-Act)
- **Beat-Definitionen**: 3× (unterschiedliche Vollständigkeit und Korrektheit)
- **JSON-Parser für LLM-Antworten**: 3× (mit jeweils anderen Edge-Case-Behandlungen)
- **Prompt-Templates für Outline-Generierung**: 2–3×

Jede neue App (coach-hub, 137-hub etc.) würde diesen Code erneut kopieren.

---

## Decision Drivers

- **DRY**: Jeder Outline-relevante Code einmalig, zentral getestet
- **Konsistenz**: Alle Apps nutzen dieselben Framework-Definitionen und Beat-Positionen
- **Erweiterbarkeit**: Neues Framework (z.B. IMRAD, Kishōtenketsu) einmal hinzufügen → alle Apps profitieren
- **Testbarkeit**: Pure-Python-Paket ohne Django ist einfach isoliert testbar
- **MVP-first**: Erst in writing-hub stabilisieren, dann als PyPI-Package extrahieren (ADR-Prinzip: Code vor ADR)

---

## Considered Options

### Option 1 — `iil-outlinefw` als eigenständiges PyPI-Package (gewählt)

Pure-Python-Paket analog zu `iil-authoringfw`, `iil-promptfw`.
Kein Django in den Core-Modulen. Optionaler Django-Adapter als separates Modul.

**Pro:**
- Einmalige Implementierung, alle Apps `pip install iil-outlinefw`
- Pure Python → einfach testbar ohne Django-Setup
- Klare Schichttrennung: Core (Schemas, Frameworks, Generator) vs. Adapter (Django-Bridge)
- Konsistenter Pattern mit bestehenden iil-Packages

**Contra:**
- Zusätzliches Repo und Release-Prozess
- Migration der bestehenden Apps erforderlich

### Option 2 — Shared Django App in jedem Repo kopiert

**Contra:** Gleiche Duplikation wie heute, nur expliziter. Verworfen.

### Option 3 — Zentrale Django-App in einem Shared-Repo (ähnlich ADR-027)

**Contra:** Erzwingt Django-Abhängigkeit im gesamten Package.
Outline-Logik ist fundamentally nicht Django-spezifisch. Verworfen.

---

## Decision Outcome

**Gewählt: Option 1** — `iil-outlinefw` als eigenständiges PyPI-Package.

### Paket-Struktur

```
outlinefw/                          # github.com/achimdehnert/outlinefw
  src/outlinefw/
    __init__.py                     # Public API
    schemas.py                      # Pydantic: OutlineNode, OutlineResult, ProjectContext
    frameworks.py                   # FRAMEWORKS dict + BeatDefinition TypedDicts
    generator.py                    # OutlineGenerator (LLMRouter Protocol)
    parser.py                       # parse_nodes() — robust LLM JSON parser
    django_adapter.py               # Optional Bridge — Host-App überschreibt Stubs
  tests/
    test_frameworks.py
    test_parser.py
  pyproject.toml                    # name = "iil-outlinefw"
```

### Schichten-Trennung

```
┌─────────────────────────────────────┐
│  Host-App (writing-hub, travel-beat) │
│  django_adapter.py (Host-spezifisch) │
├─────────────────────────────────────┤
│  outlinefw Core (Pure Python)        │
│  schemas · frameworks · generator   │
│  parser · LLMRouter Protocol        │
├─────────────────────────────────────┤
│  iil-aifw (LLM Routing)             │
│  iil-promptfw (Prompt Templates)    │
└─────────────────────────────────────┘
```

### Eingebettete Frameworks (v0.1.0)

| Key | Name | Beats |
|-----|------|-------|
| `three_act` | Drei-Akt-Struktur | 7 |
| `save_the_cat` | Save the Cat (Blake Snyder) | 15 |
| `heros_journey` | Heldenreise (Campbell) | 12 |
| `five_act` | Fünf-Akt-Struktur (Shakespeare) | 5 |
| `dan_harmon` | Dan Harmon Story Circle | 8 |

Jeder Beat hat: `name`, `position` (0.0–1.0), `act` (act_1/2a/2b/3), `description`, `tension` (low/medium/high/peak).

### LLMRouter Protocol

`OutlineGenerator` nimmt ein Objekt entgegen, das das `LLMRouter`-Protocol erfüllt:

```python
@runtime_checkable
class LLMRouter(Protocol):
    def completion(
        self,
        action_code: str,
        messages: list[dict[str, str]],
        quality: LLMQuality = LLMQuality.STANDARD,
        priority: str = "balanced",
    ) -> str: ...
```

- `@runtime_checkable` — `isinstance(router, LLMRouter)` wird im Konstruktor erzwungen
- Fehler-Hierarchie: `LLMRouterError` → `LLMRouterTimeout`
- Kompatibel mit `iil-aifw` und jedem Custom-Router

### Enums (v0.1.0)

| Enum | Werte | Zweck |
|------|-------|-------|
| `LLMQuality` | DRAFT=1, STANDARD=2, PREMIUM=3 | Ersetzt `quality_level: int \| None` |
| `GenerationStatus` | SUCCESS, PARTIAL, PARSE_ERROR, LLM_ERROR, VALIDATION_ERROR | Feingranularer Ergebnis-Status |
| `ParseStatus` | SUCCESS, EMPTY, MALFORMED_JSON, PARTIAL, SCHEMA_MISMATCH | Parser-Outcome |
| `ActPhase` | ACT_1, ACT_2A, ACT_2B, ACT_3, ACT_OPEN, ACT_CLOSE | Struktureller Akt |
| `TensionLevel` | LOW, MEDIUM, HIGH, PEAK | Narrative Spannung |

### ABC-basierter Django-Adapter

Statt Stubs verwendet der Adapter eine abstrakte Basisklasse:

```python
class OutlineServiceBase(ABC):
    @abstractmethod
    def get_tenant_id(self, request: Any) -> int: ...
    @abstractmethod
    def persist_outline(self, result, context, tenant_id) -> Any: ...
    @abstractmethod
    def get_llm_router(self, tenant_id: int) -> Any: ...

    def generate_and_persist(self, framework_key, context, request, quality) -> OutlineResult:
        """Template method — subclasses implement nur die 3 abstrakten Methoden."""
```

`InMemoryOutlineService` ist eine fertige Test-Implementierung ohne Django.

### FrameworkDefinition Validierung (K-2)

`FrameworkDefinition` ist ein frozen Pydantic-Model das beim Import validiert:
- Keine doppelten Beat-Positionen
- Beats sind nach Position sortiert
- Erster Beat ≤ 0.1, letzter Beat ≥ 0.9
- Kein Gap zwischen adjacent Beats > 0.30

---

## Implementation

### Phase 1 — MVP in writing-hub (abgeschlossen 2026-03-08)

- `src/outlinefw/` direkt im writing-hub-Repo unter `src/`
- `sys.path.insert(0, BASE_DIR / "src")` in `settings/base.py`
- `apps/authoring/services/outline_service.py` als dünne Facade
- `apps/outlines/` — eigenständige Django-App mit Liste, Detail, Inline-Edit

### Phase 2 — Eigenständiges Repo + Production Quality (abgeschlossen 2026-03-08)

- Repo: `https://github.com/achimdehnert/outlinefw`
- PyPI-Name: `iil-outlinefw`
- `pyproject.toml`: hatchling build, `py.typed` (PEP 561), `django` optional dep, mypy strict
- Test-Suite: `tests/test_outlinefw.py` mit 30+ Tests (Schemas, Frameworks, Parser, Generator, Adapter)
- writing-hub: `src/outlinefw/` aktualisiert auf v0.1.0, commit `055cea8`

**Applied fixes from review:**

| Fix-ID | Beschreibung |
|--------|-------------|
| K-1 | `py.typed` für PEP 561 Compliance |
| K-2 | `FrameworkDefinition` validiert Beat-Positionen (keine Dups, keine Gaps >0.30) |
| K-3 | `OutlineResult` mit `GenerationStatus` Enum + `completion_ratio` + `raise_if_failed()` |
| K-4 | `ParseResult` unterscheidet EMPTY/MALFORMED_JSON/PARTIAL/SCHEMA_MISMATCH/SUCCESS |
| H-1 | Explizites `__all__` in `__init__.py` |
| H-2 | `LLMQuality` Enum ersetzt `quality_level: int \| None` |
| H-3 | `pyproject.toml` komplett (py.typed, django optional, mypy strict, ruff erweitert) |
| H-4 | Jedes Framework hat expliziten `version` String |
| B-2 | `LLMRouter` Protocol mit `LLMRouterError` + `LLMRouterTimeout` |
| B-3 | `django_adapter` nutzt ABC (`OutlineServiceBase`) statt Stubs |

### Phase 3 — Migration (pending)

| Repo | Aufgabe | Priorität |
|------|---------|-----------|
| `writing-hub` | `pip install iil-outlinefw`, `src/outlinefw/` + `sys.path` Hack entfernen | HIGH |
| `travel-beat` | `SAVE_THE_CAT_BEATS` ersetzen durch `outlinefw.frameworks` | LOW |
| `bfagent` | `OutlineGenerationHandler` auf `OutlineGenerator` umstellen | LOW |
| `coach-hub` | Direkt `iil-outlinefw` nutzen, kein Copy-Paste | FUTURE |

---

## Consequences

### Positive

- Frameworks und Beat-Definitionen einmalig definiert, konsistent über alle Apps
- Neues Framework: 1 PR in `outlinefw` statt 3 separate Änderungen
- `parse_nodes()` mit vollständiger Edge-Case-Behandlung zentral verfügbar
- Pure-Python-Tests ohne Django-Setup möglich

### Negative

- Zusätzlicher Release-Prozess wenn sich API ändert
- Phase-3-Migration muss geplant und durchgeführt werden
- `django_adapter.py` bleibt Host-spezifisch — kein universelles Django-Adapter möglich

### Risks

| Risiko | Schwere | Mitigation |
|--------|---------|-----------|
| PyPI-Publish vergessen | LOW | GitHub Actions CI (geplant) |
| writing-hub nutzt `src/` statt PyPI-Package | LOW | Phase 3 Migration; funktioniert beides |
| API-Break beim PyPI-Upgrade | MEDIUM | Semantic Versioning; `<1` Pinning in requirements |

---

## Abgrenzung zu verwandten Packages

| Package | Zweck | Verhältnis |
|---------|-------|------------|
| `iil-authoringfw` | Authoring-Schemas (Chapter-Inhalt, Style, Character) | Peer — `outlinefw` = Struktur, `authoringfw` = Inhalt |
| `iil-promptfw` | Jinja2 Prompt-Templates | `outlinefw` kann optional `promptfw` nutzen |
| `iil-aifw` | LLM-Routing | `outlinefw` nutzt es via LLMRouter Protocol |
| `iil-weltenfw` | WeltenHub REST-Client | Unabhängig |

---

## Links

- Repo: https://github.com/achimdehnert/outlinefw
- writing-hub MVP: `writing-hub/src/outlinefw/` (commit `2c79c27`)
- Outlines-App: `writing-hub/apps/outlines/` (commit `a6db87f`)
- writing-hub v0.1.0: `writing-hub/src/outlinefw/` (commit `055cea8`)
- outlinefw Repo v0.1.0: commit `7b9bc63`
