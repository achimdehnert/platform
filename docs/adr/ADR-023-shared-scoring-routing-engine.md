---
status: proposed
date: 2026-02-21
decision-makers: Achim Dehnert
---

# ADR-023: Shared Scoring and Routing Engine

| Metadata    | Value                                                      |
|-------------|-------------------------------------------------------------|
| **Status**  | Proposed                                                    |
| **Date**    | 2026-02-10                                                  |
| **Author**  | Achim Dehnert                                               |
| **Scope**   | cross-repo (bfagent, mcp-hub, platform)                     |
| **Related** | ADR-015 (Governance), ADR-012 (MCP Quality), ADR-022 (Consistency) |

---

## 1. Executive Summary

Im Ökosystem existieren **vier unabhängige Implementierungen** von Task-Complexity-Scoring und LLM-Routing. Dieses ADR dokumentiert die Ist-Analyse, bewertet Konsolidierungsoptionen und schlägt eine **Shared Scoring Engine** als leichtgewichtiges Python-Package vor.

**Kernentscheidung:** Scoring-Logik (Keyword-basierte Komplexitätseinschätzung, Confidence-Kalibrierung) wird in ein gemeinsames, dependency-freies Package extrahiert. Die darauf aufbauende Routing-/Execution-Logik verbleibt in den jeweiligen Systemen.

---

## 2. Context

### 2.1 Problem Statement

| Problem | Fundstelle | Impact |
|---------|-----------|--------|
| 4× nahezu identische Keyword-Scoring-Logik | Siehe §3 | DRY-Verstoß, divergierende Ergebnisse |
| Keyword-Listen driften auseinander | bfagent vs. orchestrator | Gleicher Task wird unterschiedlich eingestuft |
| Confidence-Kalibrierung nur in 1 von 4 Systemen | orchestrator (neu) | Keine Unsicherheits-Erkennung in bfagent |
| Keine Tests für Scoring in bfagent | LLMRouter, TestRequirement | Regressionen unerkannt |
| Kein Feedback-Loop | Alle Systeme | Scoring wird nie anhand realer Ergebnisse verbessert |

### 2.2 Auslöser

1. **ClawRouter-Analyse** (2026-02-10): Externer TypeScript-Router mit 14-dimensionalem gewichtetem Scoring und Sigmoid-Confidence zeigte, dass die eigene Keyword-Matching-Logik deutlich primitiver ist.
2. **Orchestrator-Verbesserung** (2026-02-10): Weighted Scoring und Confidence nach ClawRouter-Vorbild im `orchestrator_mcp` implementiert — dabei aufgefallen, dass BFAgent die gleiche Logik separat pflegt.
3. **BFAgent Initiativen-System**: Im Control Center werden Use Cases in Tasks zerlegt und jeweils einem LLM zugeordnet — per Heuristik, die der Orchestrator-Heuristik sehr ähnelt.

---

## 3. Ist-Analyse: Vier Scoring-Implementierungen

### 3.1 TestRequirement.estimate_complexity()

**Pfad:** `bfagent/apps/bfagent/models_testing.py:737-782`

- **Methode:** Additive Scoring (16 Keywords, 5 Dimensionen: category, keywords, criteria count, domain, description length)
- **Output:** `'low'` / `'medium'` / `'high'`
- **Kritik:** Keine Gewichtung (alle Keywords zählen gleich), keine Confidence, hardcoded im Django-Model (nicht ohne DB testbar), Mixed Concerns (Scoring + Model-Instance-Logik)

### 3.2 LLMRouter.estimate_complexity()

**Pfad:** `bfagent/apps/bfagent/services/llm_router.py:151-224`

- **Methode:** Binary keyword match (`any()`) + 4 Dimensionen (keywords, files_affected, criteria_count, category)
- **Output:** `ComplexityLevel.LOW/MEDIUM/HIGH`
- **Kritik:** Binary match — 1 Treffer gibt gleichen Score wie 10 Treffer. Andere Keywords als §3.1 (z.B. `'architektur'` vs. `'architecture'`). Andere Thresholds (`>=5` = HIGH vs. `>4`). Redundant zu §3.1, aber eigenständig.

### 3.3 AutoroutingOrchestrator._estimate_complexity()

**Pfad:** `bfagent/apps/bfagent/services/autorouting_orchestrator.py:262-271`

- **Methode:** Rein textlängenbasiert (`len(description) < 200` → SMALL)
- **Output:** `Complexity.SMALL/MEDIUM/LARGE`
- **Kritik:** Ignoriert Inhalt komplett. Dritte Tier-Nomenklatur (S/M/L). Wird nie von den anderen Scorern aufgerufen.

### 3.4 orchestrator_mcp/analyzer.py (neu, 2026-02-10)

**Pfad:** `mcp-hub/orchestrator_mcp/analyzer.py:33-95`

- **Methode:** Weighted hit-ratio scoring (50+ Keywords, 10 Task-Typen), Sigmoid-Confidence, Gate-Elevation bei niedriger Confidence
- **Output:** `TaskType` + `confidence: float` + `signals: list[str]`
- **Stärken:** Hit-Ratio statt binary match, per-type Gewichtung, Confidence mit Sigmoid, 38 Tests
- **Schwächen:** Andere Keywords/Typen als bfagent, kein `files_affected`/`criteria_count`, nicht von bfagent nutzbar (lebt in mcp-hub)

### 3.5 Vergleichsmatrix

| Dimension              | §3.1 Model | §3.2 Router | §3.3 Autorouting | §3.4 Orchestrator |
|------------------------|:----------:|:-----------:|:-----------------:|:-----------------:|
| Keywords               | 16         | 25          | 0                 | 50+               |
| Gewichtung             | ❌         | ❌          | ❌                | ✅ per-type       |
| Hit-Ratio              | Count      | Binary      | N/A               | ✅ Ratio          |
| Confidence             | ❌         | ❌          | ❌                | ✅ Sigmoid        |
| Structural Inputs      | ✅         | ✅          | ❌                | ❌                |
| Output-Tiers           | 3          | 3           | 3                 | 10 Types + 3 Tiers|
| Tests                  | 0          | 0           | 0                 | 38                |
| Django-Abhängigkeit    | ✅ Model   | ✅ Queryset | ✅ Model          | ❌ Pure Python    |

---

## 4. Externe Referenz: ClawRouter

**Repo:** `dehnert-clawrouter` (TypeScript, analysiert 2026-02-10)

**Übernommene Konzepte** (bereits im Orchestrator §3.4):
- Weighted multi-dimension scoring
- Sigmoid confidence calibration
- Confidence-basierte Eskalation

**Bewusst nicht übernommen:**
- TypeScript / npm-Ökosystem — falscher Stack
- x402 USDC Micropayments — irrelevant
- 30+ Provider-Proxy — nicht unser Problem
- Agentic-Detection — zukünftige Erweiterung

---

## 5. Entscheidung

### 5.1 Shared Scoring Package: `task_scorer`

Ein leichtgewichtiges Python-Package in `platform/packages/task_scorer/`.

**Eigenschaften:**
- **Zero Dependencies** — nur Python stdlib (`math`, `dataclasses`)
- **Django-unabhängig** — reine Funktionen, keine ORM-Nutzung
- **Konfigurierbar** — Keywords, Weights, Thresholds als Parameter
- **Testbar** — pytest, 100% Coverage Ziel
- **Versioniert** — Semantic Versioning, installierbar via pip

### 5.2 Package-Struktur

```
platform/packages/task_scorer/
├── pyproject.toml
├── README.md
├── src/task_scorer/
│   ├── __init__.py       # Public API: score_task, ScoringResult
│   ├── scorer.py         # Core scoring engine
│   ├── confidence.py     # Sigmoid confidence calibration
│   ├── config.py         # Default keywords, weights, boundaries
│   └── models.py         # Dataclasses (ScoringResult, Tier, Signal)
└── tests/
    ├── test_scorer.py
    ├── test_confidence.py
    └── test_integration.py
```

### 5.3 Public API (Entwurf)

```python
from task_scorer import score_task, ScoringResult, Tier, ScoringConfig

# Minimal — nur Text
result: ScoringResult = score_task("fix auth permission vulnerability")
result.tier          # Tier.HIGH
result.confidence    # 0.92
result.signals       # ["security(auth, permission, vulnerability)"]
result.task_type     # "security"

# Mit strukturellem Kontext
result = score_task(
    description="fix auth permission vulnerability",
    category="security",
    files_affected=3,
    acceptance_criteria_count=5,
)

# Custom Config
config = ScoringConfig(
    keywords={"my_type": ["kw1", "kw2"]},
    weights={"my_type": 1.5},
    confidence_steepness=8.0,
)
result = score_task("...", config=config)
```

### 5.4 Konsumenten-Integration

#### BFAgent: TestRequirement.estimate_complexity()

**Vorher:** 45 Zeilen Keyword-Logik in `models_testing.py:737-782`
**Nachher:**

```python
def estimate_complexity(self) -> str:
    from task_scorer import score_task
    result = score_task(
        description=f"{self.name} {self.description or ''}",
        category=self.category,
        acceptance_criteria_count=len(self.acceptance_criteria or []),
    )
    return result.tier.value  # "low" / "medium" / "high"
```

#### BFAgent: LLMRouter.estimate_complexity()

**Vorher:** 73 Zeilen Keyword-Logik in `llm_router.py:151-224`
**Nachher:**

```python
def estimate_complexity(self, description, files_affected=0,
                        acceptance_criteria_count=0, category=None):
    from task_scorer import score_task
    result = score_task(
        description=description,
        category=category,
        files_affected=files_affected,
        acceptance_criteria_count=acceptance_criteria_count,
    )
    return ComplexityLevel(result.tier.value)
```

#### BFAgent: AutoroutingOrchestrator._estimate_complexity()

**Vorher:** Reine Textlänge (5 Zeilen, inhaltlich wertlos)
**Nachher:** Delegiert an `score_task()` — erstmals inhaltliche Analyse.

#### Orchestrator MCP: analyzer.py

**Vorher:** Eigene `_score_task_types()` + `_sigmoid_confidence()`
**Nachher:** Importiert von `task_scorer`, ergänzt um Gate/Team/Model-Logik.

### 5.5 Abgrenzung: Was bleibt wo

| Verantwortung | Verbleibt in | Nicht in task_scorer |
|--------------|-------------|---------------------|
| Keyword Scoring + Confidence | `task_scorer` | — |
| LLM-Auswahl (Ollama/Cloud/Cascade) | bfagent `LLMRouter` | ✅ |
| LLM Execution (API-Call) | bfagent `llm_client` | ✅ |
| Gate/Team/Cost Assignment | orchestrator `analyzer` | ✅ |
| Django Model Integration | bfagent `models_testing` | ✅ |
| MCP Tool Registration | mcp-hub `server.py` | ✅ |

---

## 6. Alternativen (bewertet)

### 6.1 Status Quo beibehalten ❌

- **Pro:** Kein Aufwand
- **Contra:** Keywords driften weiter auseinander, keine Confidence in bfagent, AutoroutingOrchestrator bleibt textlängenbasiert, 0 Tests für 3 von 4 Implementierungen
- **Bewertung:** Nicht tragbar bei wachsendem Ökosystem

### 6.2 ClawRouter vollständig übernehmen ❌

- **Pro:** Ausgereift, 14 Dimensionen, gut getestet
- **Contra:** TypeScript (falscher Stack), Client-Side Router (nicht unser Problem), x402 Payment (irrelevant), würde Neuschreiben aller Konsumenten erfordern
- **Bewertung:** Overkill, falsches Ökosystem

### 6.3 Scoring direkt im Orchestrator MCP belassen ❌

- **Pro:** Bereits implementiert und getestet
- **Contra:** bfagent kann `orchestrator_mcp` nicht importieren (anderes Repo, FastMCP vs. Django), Duplikation bleibt bestehen
- **Bewertung:** Löst das Kernproblem nicht

### 6.4 Scoring in bfagent konsolidieren ❌

- **Pro:** Dort sind die meisten Konsumenten
- **Contra:** Django-Abhängigkeit, orchestrator_mcp kann bfagent nicht importieren, bfagent ist kein Library-Repo
- **Bewertung:** Würde die Abhängigkeitsrichtung umkehren

### 6.5 Shared Package in platform ✅ (gewählt)

- **Pro:** Neutral, dependency-frei, von allen Repos importierbar, zentral getestet, versioniert
- **Contra:** Neues Package pflegen, pip install nötig
- **Bewertung:** Minimaler Aufwand, maximaler Nutzen

---

## 7. Implementierungsplan

### Phase 1: Package erstellen (Aufwand: ~4h)

1. `platform/packages/task_scorer/` anlegen
2. Scoring-Engine aus orchestrator `_score_task_types()` extrahieren
3. Confidence aus orchestrator `_sigmoid_confidence()` extrahieren
4. Structural Inputs hinzufügen (`files_affected`, `criteria_count`, `category`)
5. Default-Config mit vereinigten Keywords aus allen 4 Systemen
6. Tests portieren und erweitern (Ziel: >90% Coverage)
7. `pyproject.toml` mit Version 0.1.0

### Phase 2: Orchestrator MCP refactoren (Aufwand: ~1h)

1. `orchestrator_mcp` importiert `task_scorer`
2. `_score_task_types()` und `_sigmoid_confidence()` entfernen
3. Tests anpassen, sicherstellen dass 38/38 weiter bestehen

### Phase 3: BFAgent refactoren (Aufwand: ~2h)

1. `task_scorer` als Dependency in `requirements.txt`
2. `TestRequirement.estimate_complexity()` refactoren
3. `LLMRouter.estimate_complexity()` refactoren
4. `AutoroutingOrchestrator._estimate_complexity()` refactoren
5. `get_llm()` um Confidence erweitern (unsichere Tasks → stärkeres LLM)
6. Tests für alle refactored Methods

### Phase 4: Monitoring (fortlaufend)

1. Scoring-Ergebnisse in `MCPUsageLog` / `InitiativeActivity` loggen
2. Confidence-Verteilung tracken (wie oft < Threshold?)
3. Langfristig: Feedback-Loop — wurde das Scoring-Ergebnis korrigiert?

---

## 8. Risiken

| Risiko | Wahrscheinlichkeit | Mitigation |
|--------|-------------------|------------|
| Regressions bei Refactoring | Mittel | Tests vorher, nachher, Staging |
| Scoring-Ergebnisse ändern sich | Hoch (gewollt!) | Validieren gegen bekannte Tasks |
| Overhead für neues Package | Niedrig | Zero-Dep, ~200 LOC |
| bfagent kann pip install nicht | Niedrig | Im Docker-Build, oder als git submodule |

---

## 9. Metriken für Erfolg

- **Scoring-Konsistenz:** Gleicher Task → gleiches Ergebnis in bfagent und orchestrator
- **Test-Coverage:** >90% für `task_scorer`, >0% (aktuell) für bfagent Scoring
- **LOC-Reduktion:** ~160 Zeilen Scoring-Code aus bfagent entfernt
- **Confidence-Nutzung:** bfagent loggt Confidence, UI zeigt bei <0.65 Warnung

---

## 10. Offene Fragen

1. **Agentic-Detection:** Soll ClawRouters Multi-Step/Tool-Use-Erkennung in Phase 1 oder später integriert werden?
2. **Zweisprachige Keywords:** bfagent nutzt teils deutsche Keywords (`architektur`). Unified List nur EN oder DE+EN?
3. **pip install vs. git submodule:** Wie wird `task_scorer` in bfagent und mcp-hub eingebunden?
4. **Tier-Mapping:** `task_scorer` gibt 3 Tiers. Orchestrator braucht 10 TaskTypes. Brauchen wir beides im Package?

---

## Appendix A: Keyword-Divergenz-Tabelle

Keywords die in mindestens einem System vorhanden, aber nicht in allen:

| Keyword | §3.1 Model | §3.2 Router | §3.4 Orchestrator | Empfehlung |
|---------|:----------:|:-----------:|:-----------------:|:----------:|
| `architecture` | ✅ | ❌ | ✅ | ✅ unified |
| `architektur` | ❌ | ✅ | ❌ | ✅ add (DE) |
| `authentication` | ❌ | ✅ | ❌ | ✅ add |
| `authorization` | ❌ | ✅ | ❌ | ✅ add |
| `caching` | ❌ | ✅ | ❌ | ✅ add |
| `optimization` | ❌ | ✅ | ✅ (`optimize`) | ✅ unified |
| `credential` | ❌ | ❌ | ✅ | ✅ keep |
| `vulnerability` | ❌ | ❌ | ✅ | ✅ keep |
| `cve` | ❌ | ❌ | ✅ | ✅ keep |
| `integration` | ❌ | ✅ | ✅ | ✅ unified |
| `validation` | ❌ | ✅ | ❌ | ✅ add |
| `readme` | ❌ | ❌ | ✅ | ✅ keep |
| `sphinx` | ❌ | ❌ | ✅ | ✅ keep |
| `performance` | ✅ | ✅ | ❌ | ✅ add |
