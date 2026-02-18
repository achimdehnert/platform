# Review: ADR-023 — Shared Scoring and Routing Engine

| Metadata     | Value                                   |
|--------------|-----------------------------------------|
| **Reviewer** | AI Code Review (produktionskritisch)    |
| **Datum**    | 2026-02-10                              |
| **Artefakt** | `platform/docs/adr/ADR-023-shared-scoring-routing-engine.md` |
| **Ergebnis** | **Bedingt akzeptabel — 3 Blocker, 6 Warnings, 4 Hinweise** |

---

## 1. Faktenprüfung (Invarianten-Verletzungen)

### F-1: Keyword-Zählung §3.1 ist falsch

- **Befund:** ADR behauptet "16 Keywords" für `TestRequirement.estimate_complexity()`. Tatsächlich:
  `complex_keywords` = 8 (`migration`, `refactor`, `database`, `architecture`, `api`, `authentication`, `permission`, `model`) +
  `simple_keywords` = 9 (`typo`, `text`, `label`, `css`, `color`, `button`, `style`, `spacing`, `icon`) = **17**.
- **Risiko:** Niedrig (Dokumentationsfehler), aber untergräbt Glaubwürdigkeit der Analyse.
- **Empfehlung:** Korrigieren auf 17 (8 complex + 9 simple).
- **Quelle:** `bfagent/apps/bfagent/models_testing.py:751-754`

### F-2: Keyword-Zählung §3.2 ist falsch

- **Befund:** ADR behauptet "25 Keywords" für `LLMRouter.estimate_complexity()`. Tatsächlich:
  `high_keywords` = 13, `medium_keywords` = 11, `low_keywords` = 12 = **36**.
- **Risiko:** Niedrig (Dokumentationsfehler), aber 36 vs. 25 ist erhebliche Abweichung.
- **Empfehlung:** Korrigieren auf 36 (13 high + 11 medium + 12 low).
- **Quelle:** `bfagent/apps/bfagent/services/llm_router.py:172-188`

### F-3: Threshold-Behauptung §3.2 ist irreführend

- **Befund:** ADR §3.2 behauptet "Andere Thresholds (`>=5` = HIGH vs. `>4`)". Für ganzzahlige Scores sind `score >= 5` und `score > 4` **identisch**. Ebenso: `score <= 1` (§3.1) und `score < 2` (§3.2) sind identisch.
  - §3.1: `score <= 1` → low, `score <= 4` → medium, else high
  - §3.2: `score >= 5` → HIGH, `score >= 2` → MEDIUM, else LOW
  - Für Ganzzahlen: **exakt gleiche Grenzen**.
- **Risiko:** Mittel. Verfälscht die Argumentation für Divergenz. Die tatsächliche Divergenz liegt in **Scoring-Mechanik** (additive vs. binary), nicht in Thresholds.
- **Empfehlung:** Threshold-Behauptung entfernen. Stattdessen den echten Unterschied betonen: additive count (`sum(2 for kw ...)`) vs. binary match (`any(kw in text ...)`).

### F-4: Appendix A — `authentication` falsch markiert

- **Befund:** Appendix A zeigt `authentication` als ❌ für §3.1 Model. Tatsächlich **ist** `authentication` in `complex_keywords` (Zeile 752).
- **Risiko:** Mittel. Untergräbt die Divergenz-Analyse, die ein Kernargument des ADR ist.
- **Empfehlung:** Korrigieren auf ✅ für §3.1.
- **Quelle:** `bfagent/apps/bfagent/models_testing.py:752`

---

## 2. Architekturkonformität

### A-1: BLOCKER — Widerspruch zu ADR-015 (Database-Driven Choices)

- **Befund:** ADR-015 §R2 verlangt: *"Database-driven Lookup Tables statt Enums"*. ADR-023 schlägt Keywords und Weights als **Python-Dataclass** vor (`ScoringConfig`). Das ist hardcoded Configuration in Code, nicht database-driven.
- **Risiko:** Hoch. Verstößt gegen etablierte Governance. Jede Keyword-Änderung erfordert Package-Release + Deploy statt DB-Update.
- **Empfehlung:** Hybrid-Ansatz: `task_scorer` liefert **Default-Config** als Fallback. Konsumenten (bfagent, orchestrator) können DB-basierte Config injizieren:

```python
# bfagent: Config aus DB laden
from task_scorer import score_task, ScoringConfig

def get_scoring_config() -> ScoringConfig:
    """Lade Keywords/Weights aus lkp_scoring_keywords."""
    from apps.bfagent.models import ScoringKeyword  # Lookup Table
    keywords = {}
    weights = {}
    for entry in ScoringKeyword.objects.all():
        keywords.setdefault(entry.task_type, []).append(entry.keyword)
        weights[entry.task_type] = entry.weight
    return ScoringConfig(keywords=keywords, weights=weights)

result = score_task(description, config=get_scoring_config())
```

Dies wahrt Zero-Dependency für das Package UND erlaubt DB-Driven Config.

### A-2: BLOCKER — Fehlende Dependency-Strategie für Docker

- **Befund:** ADR §5.1 sagt "installierbar via pip", §8 sagt "Im Docker-Build, oder als git submodule" — ohne konkrete Lösung. Für den Hetzner-Produktionsserver ist dies **deployment-kritisch**.
- **Risiko:** Hoch. Ohne klare Lösung kann Phase 2/3 nicht umgesetzt werden.
- **Empfehlung:** Explizit festlegen (eine der folgenden):

```bash
# Option A: pip install von Git (bevorzugt, kein PyPI nötig)
# In bfagent/requirements.txt:
task-scorer @ git+ssh://git@github.com/achimdehnert/platform.git@v0.1.0#subdirectory=packages/task_scorer

# Option B: COPY im Dockerfile (kein Netzwerk nötig)
# In bfagent/docker/app/Dockerfile:
COPY --from=platform-packages /packages/task_scorer /tmp/task_scorer
RUN pip install /tmp/task_scorer && rm -rf /tmp/task_scorer
```

Option A empfohlen — versioniert, kein Monorepo-COPY nötig, SSH-Auth auf Server bereits konfiguriert.

### A-3: BLOCKER — Tier-Mapping ungelöst (Offene Frage #4)

- **Befund:** `task_scorer` soll 3 Tiers liefern (low/medium/high). Der Orchestrator braucht 10 TaskTypes + 3 ModelTiers. Die Public API in §5.3 zeigt `result.task_type` ("security") UND `result.tier` (Tier.HIGH) — das sind **zwei verschiedene Taxonomien**, die beide vom Scorer kommen sollen. Das ist aber als "Offene Frage" markiert statt als Design-Entscheidung.
- **Risiko:** Hoch. Ohne Klärung ist die API nicht implementierbar. Wenn der Scorer nur 3 Tiers kennt, kann der Orchestrator seine 10 TaskTypes nicht ableiten. Wenn der Scorer 10 TaskTypes kennt, ist er nicht mehr "generisch".
- **Empfehlung:** Zwei separate Outputs:

```python
@dataclass(frozen=True)
class ScoringResult:
    """Ergebnis des Scoring — generisch, keine App-spezifische Logik."""
    scores: dict[str, float]     # Alle Typ-Scores: {"security": 1.5, "bug": 0.3, ...}
    top_type: str                # Höchster Score: "security"
    tier: Tier                   # Mapping zu LOW/MEDIUM/HIGH
    confidence: float            # Sigmoid-Confidence
    signals: list[str]           # Debug-Signale
```

BFAgent nutzt `result.tier`, Orchestrator nutzt `result.top_type` + `result.scores` für sein eigenes TaskType-Mapping. Das Package liefert beides.

---

## 3. Seiteneffekte und Migrationsrisiken

### S-1: WARNING — Scoring-Ergebnisse ändern sich bei Migration

- **Befund:** Wenn `task_scorer` die vereinigten Keywords aller Systeme nutzt, werden bestehende Tasks **anders bewertet** als zuvor. Z.B. ein Task mit "authentication" wird in §3.2 aktuell binary +3 (high) gewertet, im neuen System per hit-ratio möglicherweise anders.
- **Risiko:** Mittel. `get_effective_complexity()` (Zeile 784-788) cached Complexity nur wenn explizit gesetzt (`!= 'auto'`). Auto-Tasks werden bei jedem Aufruf neu berechnet — Ergebnis ändert sich.
- **Empfehlung:** Phase 3 muss eine **Vergleichsvalidierung** enthalten:

```python
# Einmalig: Alle auto-complexity Tasks vergleichen
for req in TestRequirement.objects.filter(complexity='auto'):
    old = req.estimate_complexity()  # Alte Logik
    new = score_task(f"{req.name} {req.description}").tier.value
    if old != new:
        logger.warning(f"Scoring change: {req.pk} {old} -> {new}")
```

### S-2: WARNING — get_llm() Silent None Return

- **Befund:** `TestRequirement.get_llm()` (Zeile 818-819) hat einen stillen Fallback: `return Llms.objects.filter(is_active=True).first()`. Wenn kein aktives LLM existiert, wird **None** zurückgegeben — ohne Exception, ohne Logging.
- **Risiko:** Mittel. Downstream-Code (AutoroutingOrchestrator Zeile 315: `llm.name`) crasht mit `AttributeError: 'NoneType' has no attribute 'name'`.
- **Empfehlung:** Im Rahmen des Refactoring beheben:

```python
# Fallback mit explizitem Error
llm = Llms.objects.filter(is_active=True).first()
if llm is None:
    raise LLMNotAvailableError("No active LLM configured")
return llm
```

### S-3: WARNING — AutoroutingOrchestrator Tier-Nomenklatur-Bruch

- **Befund:** `AutoroutingOrchestrator._estimate_complexity()` liefert `AutocodingRun.Complexity.SMALL/MEDIUM/LARGE`. Der neue `score_task()` liefert `Tier.LOW/MEDIUM/HIGH`. Das Feld `AutocodingRun.complexity` muss die alten DB-Werte verstehen.
- **Risiko:** Mittel. Django-Migration nötig oder Mapping-Layer.
- **Empfehlung:** In Phase 3 explizit adressieren:

```python
# Mapping: task_scorer Tier -> AutocodingRun.Complexity
TIER_TO_COMPLEXITY = {
    "low": AutocodingRun.Complexity.SMALL,
    "medium": AutocodingRun.Complexity.MEDIUM,
    "high": AutocodingRun.Complexity.LARGE,
}
```

### S-4: WARNING — Substring-Match-Semantik undokumentiert

- **Befund:** Orchestrator nutzt Substring-Match (`"auth" in desc_lower`). Das matched auch "authentication", "authorization", "author". BFAgent nutzt ebenfalls Substring. Die Appendix-A-Tabelle berücksichtigt das nicht — `auth` in Orchestrator ≈ `authentication` in BFAgent via Substring.
- **Risiko:** Niedrig. Aber die Divergenz-Analyse ist dadurch übertrieben.
- **Empfehlung:** Appendix A um eine Spalte "Substring-Match via" erweitern oder als Fußnote dokumentieren.

### S-5: WARNING — Idempotenz bei mehrfachem score_task() Aufruf

- **Befund:** Der ADR-Entwurf (§5.4) ruft `score_task()` in `estimate_complexity()` auf. `get_llm()` ruft `get_effective_complexity()` auf, das wiederum `estimate_complexity()` aufruft. Bei jedem `get_llm()`-Aufruf wird also neu gescored. Das ist idempotent (gut), aber **performance-relevant** bei Listen-Views.
- **Risiko:** Niedrig (Scoring ist CPU-only, kein I/O).
- **Empfehlung:** `@cached_property` oder einmaliges Scoring beim Save erwägen.

### S-6: WARNING — Kein Rollback-Plan

- **Befund:** Der Implementierungsplan hat keine Rollback-Strategie. Wenn Phase 3 (BFAgent-Refactoring) die Scoring-Ergebnisse verschlechtert, gibt es keinen dokumentierten Weg zurück.
- **Empfehlung:** Feature-Flag oder `SCORING_ENGINE` Setting:

```python
# settings.py
SCORING_ENGINE = "task_scorer"  # oder "legacy" zum Rollback

# models_testing.py
def estimate_complexity(self) -> str:
    if settings.SCORING_ENGINE == "legacy":
        return self._legacy_estimate_complexity()
    from task_scorer import score_task
    ...
```

---

## 4. Separation of Concerns

### C-1: Hinweis — Scoring vs. Routing korrekt getrennt

- **Befund:** Die Abgrenzung in §5.5 ist sauber. Scoring (was) im Package, Routing (wohin) in den Konsumenten. Das respektiert SoC.
- **Empfehlung:** Keine Aktion nötig. Gut.

### C-2: Hinweis — Multi-Tenancy nicht erwähnt

- **Befund:** Scoring ist tenant-agnostic (pure function auf Text). Das ist korrekt, sollte aber explizit dokumentiert werden, da alle Django-Apps multi-tenant sind.
- **Empfehlung:** In §5.1 ergänzen: "Tenant-agnostic: Scoring ist eine reine Funktion ohne Datenbankzugriff. Tenant-spezifische Anpassungen erfolgen über die Config-Injection der Konsumenten."

### C-3: Hinweis — `models.py` im Package ist irreführend

- **Befund:** §5.2 zeigt `src/task_scorer/models.py` für Dataclasses. Im Django-Kontext suggeriert `models.py` ORM-Models.
- **Empfehlung:** Umbenennen zu `types.py` oder `schemas.py`.

### C-4: Hinweis — Naming Convention `task_scorer` vs. `task-scorer`

- **Befund:** Python-Packages nutzen Underscores (`task_scorer`), pip nutzt Hyphens (`task-scorer`). In `pyproject.toml` heißt das:

```toml
[project]
name = "task-scorer"       # pip install task-scorer
[tool.setuptools.packages.find]
where = ["src"]            # import task_scorer
```

- **Empfehlung:** Explizit in §5.2 dokumentieren.

---

## 5. Zusammenfassung

### Blocker (müssen vor Acceptance gelöst werden)

| ID | Befund | Aufwand |
|----|--------|---------|
| A-1 | Widerspruch ADR-015: Hardcoded Config statt DB-driven | Design-Entscheidung (Hybrid) |
| A-2 | Keine konkrete Dependency-Strategie für Docker | 1 Zeile in ADR |
| A-3 | Tier-Mapping zwischen 3 Tiers und 10 TaskTypes ungelöst | API-Design-Entscheidung |

### Faktenfehler (müssen korrigiert werden)

| ID | Befund | Fix |
|----|--------|-----|
| F-1 | §3.1 "16 Keywords" → tatsächlich 17 | s/16/17/ |
| F-2 | §3.2 "25 Keywords" → tatsächlich 36 | s/25/36/ |
| F-3 | "Andere Thresholds" → für Ganzzahlen identisch | Behauptung entfernen |
| F-4 | Appendix `authentication` §3.1 ❌ → tatsächlich ✅ | Tabelle korrigieren |

### Warnings (sollten adressiert werden)

| ID | Befund | Priorität |
|----|--------|-----------|
| S-1 | Scoring-Ergebnisse ändern sich bei Migration | Hoch |
| S-2 | `get_llm()` Silent None Return | Mittel |
| S-3 | SMALL/MEDIUM/LARGE → LOW/MEDIUM/HIGH Mapping | Mittel |
| S-4 | Substring-Match-Semantik in Appendix A fehlt | Niedrig |
| S-5 | Performance bei wiederholtem Scoring | Niedrig |
| S-6 | Kein Rollback-Plan | Mittel |
