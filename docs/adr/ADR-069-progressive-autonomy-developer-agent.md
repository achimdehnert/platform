# ADR-069: Progressive Autonomy Pattern für den Developer-Agenten

| Feld | Wert |
|------|------|
| **Status** | Proposed |
| **Datum** | 2026-02-23 |
| **Autor** | Achim Dehnert |
| **Supersedes** | — |
| **Related** | ADR-066, ADR-068, CONCEPT-001 |

---

## Kontext

ADR-066 definiert den `Developer`-Agenten als eine der vier Kernrollen des
AI Engineering Squad. Die offene architektonische Frage lautet:

> Ist `developer.py` ein **autonomer LLM-Caller** (schreibt selbstständig Code
> via LLM-API) oder ein **Koordinations-Wrapper** (delegiert an Cascade/Windsurf)?

Beide Extreme haben Nachteile:
- **Rein autonom**: Unkontrolliertes Risiko bei komplexen Tasks; kein Lernen aus
  Fehlern; Gate-System wird umgangen wenn Qualität schlecht ist
- **Rein Cascade-gesteuert**: Kein Skalierungspotential; Cascade ist Flaschenhals;
  keine Messung was tatsächlich autonom funktioniert

Gleichzeitig zeigt `config.py` bereits ein `hybrid`-Szenario mit `fallback`-Feldern
pro Agent — die Infrastruktur für differenzierte Steuerung ist vorhanden.

Der `AuditStore` (`audit_store.py`) loggt bereits `cost_usd`, `model`, `gate` und
`status` pro Aktion — die Datenbasis für Qualitätsmessung existiert.

---

## Entscheidung

Wir implementieren `developer.py` als **Progressive Autonomy Hybrid**:

> Der Developer-Agent startet als Cascade-gesteuerter Koordinations-Wrapper
> (Gate 1–2). Für jeden Task-Typ wird separat gemessen, ob autonome LLM-Execution
> zuverlässig funktioniert. Bei nachgewiesener Qualität (≥ 3 Erfolge, Score ≥ 0.85)
> wird der Task-Typ auf Gate 0 (Autonomous) herabgestuft. Bei Qualitätsverlust
> wird automatisch zurückgestuft.

Das Pattern heißt **Progressive Autonomy**: Kontrolle wird sukzessive an den
automomen LLM-Caller zurückgegeben — messbar, reversibel, task-typ-spezifisch.

---

## Architektur

### Drei Ausführungsmodi

```
DeveloperMode.CASCADE_CONTROLLED   # Gate 2 — Cascade führt aus, LLM plant
DeveloperMode.SUPERVISED           # Gate 1 — LLM führt aus, Cascade überwacht
DeveloperMode.AUTONOMOUS           # Gate 0 — LLM führt vollständig autonom aus
```

### Autonomie-Profil pro Task-Typ

```
AutonomyProfile (pro TaskType):
  mode: DeveloperMode          # aktueller Modus
  success_count: int           # konsekutive Erfolge im aktuellen Modus
  failure_count: int           # konsekutive Fehler
  avg_quality_score: float     # Ø TaskQualityScore der letzten N Executions
  promoted_at: datetime | None # wann zuletzt hochgestuft
  demoted_at: datetime | None  # wann zuletzt zurückgestuft
```

### Promotion / Demotion Schwellwerte

```
PROMOTION_THRESHOLD:
  min_consecutive_successes: 3
  min_avg_quality_score: 0.85
  min_gate_level_for_promotion: 1  # CASCADE_CONTROLLED → SUPERVISED

DEMOTION_THRESHOLD:
  max_consecutive_failures: 1      # sofort bei erstem Fehler
  min_quality_score_trigger: 0.70  # unter diesem Score → Demotion
```

### Ablauf pro Task-Execution

```
execute_task(task: EngineeringTask) -> ExecutionResult:

  1. Lade AutonomyProfile für task.task_type
  2. Wähle Ausführungsmodus:
     mode = profile.mode

  3. Führe aus:
     CASCADE_CONTROLLED:
       → plan = llm_call(model, task)          # LLM erstellt Plan
       → result = cascade_execute(plan)        # Cascade führt aus
       → quality = evaluate(result, task)

     SUPERVISED:
       → result = llm_execute(model, task)     # LLM führt aus
       → cascade_review(result)               # Cascade prüft
       → quality = evaluate(result, task)

     AUTONOMOUS:
       → result = llm_execute(model, task)     # LLM führt vollständig aus
       → quality = evaluate(result, task)      # nur QualityEvaluator

  4. Update AutonomyProfile:
     if quality.score >= PROMOTION_THRESHOLD.min_avg_quality_score:
       profile.success_count += 1
       profile.failure_count = 0
       if profile.success_count >= PROMOTION_THRESHOLD.min_consecutive_successes:
         promote(profile)  # mode += 1 (max: AUTONOMOUS)
     else:
       profile.failure_count += 1
       profile.success_count = 0
       if quality.score < DEMOTION_THRESHOLD.min_quality_score_trigger:
         demote(profile)   # mode -= 1 (min: CASCADE_CONTROLLED)

  5. Log in AuditStore:
     {task_id, mode, quality_score, promoted, demoted, cost_usd}

  6. Return ExecutionResult
```

### Visualisierung des Autonomie-Fortschritts

```
Task-Typ: "lint" (einfach, deterministisch)
  Start:    CASCADE_CONTROLLED
  Run 1–3:  Score 0.92, 0.89, 0.91  → promote → SUPERVISED
  Run 4–6:  Score 0.88, 0.90, 0.87  → promote → AUTONOMOUS
  Run 7:    Score 0.95               → bleibt AUTONOMOUS

Task-Typ: "db_migration" (komplex, riskant)
  Start:    CASCADE_CONTROLLED
  Run 1:    Score 0.72               → kein Promote (< 0.85)
  Run 2:    Score 0.65               → Demotion-Trigger → bleibt CASCADE_CONTROLLED
  → Bleibt dauerhaft CASCADE_CONTROLLED bis Qualität steigt

Task-Typ: "feature" (mittel)
  Start:    CASCADE_CONTROLLED
  Run 1–3:  Score 0.86, 0.88, 0.85  → promote → SUPERVISED
  Run 4:    Score 0.68               → demote → CASCADE_CONTROLLED
  Run 5–7:  Score 0.87, 0.90, 0.88  → promote → SUPERVISED
  → Pendelt je nach Komplexität der konkreten Feature-Tasks
```

---

## Implementierungsstruktur

```
orchestrator_mcp/agent_team/
  developer.py          # Haupt-Implementierung (NEU)
  autonomy_store.py     # Persistenz der AutonomyProfiles (NEU)
  evaluator.py          # QualityEvaluator — ADR-068 (NEU, parallel)
  utils.py              # llm_call_with_retry(), FALLBACK_CHAIN (NEU)
```

### developer.py — Kernstruktur

```python
class DeveloperMode(str, Enum):
    CASCADE_CONTROLLED = "cascade_controlled"  # Gate 2
    SUPERVISED = "supervised"                  # Gate 1
    AUTONOMOUS = "autonomous"                  # Gate 0


class AutonomyProfile(BaseModel):
    task_type: str
    mode: DeveloperMode = DeveloperMode.CASCADE_CONTROLLED
    success_count: int = 0
    failure_count: int = 0
    avg_quality_score: float = 0.0
    total_executions: int = 0
    promoted_at: datetime | None = None
    demoted_at: datetime | None = None


class ExecutionResult(BaseModel):
    task_id: str
    mode_used: DeveloperMode
    quality_score: float
    promoted: bool = False
    demoted: bool = False
    cost_usd: float = 0.0
    output: str
    duration_seconds: float
```

### autonomy_store.py — Persistenz

Profile werden in PostgreSQL (AuditStore-DB) gespeichert:

```sql
CREATE TABLE developer_autonomy_profiles (
    task_type VARCHAR(50) PRIMARY KEY,
    mode VARCHAR(30) NOT NULL DEFAULT 'cascade_controlled',
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    avg_quality_score NUMERIC(4,3) DEFAULT 0.0,
    total_executions INTEGER DEFAULT 0,
    promoted_at TIMESTAMPTZ,
    demoted_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

Fallback: In-Memory-Dict (analog zu `AuditStore`).

---

## Konfiguration

Erweiterung von `config.py`:

```python
AUTONOMY_CONFIG: Final[dict[str, object]] = {
    "promotion_threshold": {
        "min_consecutive_successes": 3,
        "min_avg_quality_score": 0.85,
    },
    "demotion_threshold": {
        "max_consecutive_failures": 1,
        "min_quality_score_trigger": 0.70,
    },
    "initial_mode": DeveloperMode.CASCADE_CONTROLLED,
    "task_type_overrides": {
        # Bestimmte Task-Typen starten höher oder bleiben gedeckelt
        "lint": DeveloperMode.SUPERVISED,       # Einfach — direkt SUPERVISED
        "typo": DeveloperMode.SUPERVISED,        # Einfach — direkt SUPERVISED
        "db_migration": DeveloperMode.CASCADE_CONTROLLED,  # Immer Kontrolle
        "security": DeveloperMode.CASCADE_CONTROLLED,      # Immer Kontrolle
        "breaking_change": DeveloperMode.CASCADE_CONTROLLED,
    },
    "max_mode_ceiling": {
        # Bestimmte Task-Typen können nie AUTONOMOUS werden
        "db_migration": DeveloperMode.SUPERVISED,
        "security": DeveloperMode.SUPERVISED,
        "breaking_change": DeveloperMode.SUPERVISED,
    },
}
```

---

## Konsequenzen

### Positiv

- **Messbar**: Jede Promotion/Demotion ist im AuditStore nachvollziehbar
- **Reversibel**: Qualitätsverlust führt sofort zur Rückstufung
- **Task-typ-spezifisch**: `lint` kann AUTONOMOUS sein, `db_migration` nie
- **Lernend**: Das System akkumuliert Erfahrung pro Task-Typ über Zeit
- **Skalierend**: Autonome Tasks kosten weniger (kein Cascade-Overhead)
- **Sicher**: Riskante Task-Typen haben `max_mode_ceiling` — kein Weg zu AUTONOMOUS
- **Transparent**: Dashboard-fähig — Autonomie-Grad pro Task-Typ sichtbar

### Negativ / Risiken

- **Komplexer als reine Variante**: Zwei zusätzliche Dateien (`developer.py`,
  `autonomy_store.py`)
- **Kalt-Start-Problem**: Neue Task-Typen beginnen immer bei CASCADE_CONTROLLED
  — erste Tasks sind langsamer
- **Score-Abhängigkeit**: Qualität der Promotion/Demotion hängt von
  `evaluator.py` (ADR-068) ab — muss zuerst implementiert sein
- **Pendeln möglich**: Bei grenzwertigen Task-Typen kann das System zwischen
  Modi pendeln — Hysterese-Mechanismus nötig (min. 24h zwischen Promotions)

### Mitigationen

| Risiko | Mitigation |
|--------|------------|
| Score-Abhängigkeit | `evaluator.py` vor `developer.py` implementieren |
| Pendeln | `min_hours_between_promotions: 24` in `AUTONOMY_CONFIG` |
| Kalt-Start | `task_type_overrides` für bekannt-einfache Task-Typen |
| Falsche Demotion | Demotion erst nach 2 Fehlern (konfigurierbar) |

---

## Implementierungsreihenfolge

```
1. utils.py          — llm_call_with_retry(), FALLBACK_CHAIN
2. evaluator.py      — QualityEvaluator (Voraussetzung für Scoring)
3. autonomy_store.py — AutonomyProfile Persistenz
4. developer.py      — Progressive Autonomy Hybrid
5. metrics.py        — TaskQualityScore + Feedback-Loop (ADR-068)
```

---

## Offene Fragen

| Frage | Priorität |
|-------|----------|
| Soll `cascade_execute()` in `developer.py` ein MCP-Tool-Call sein oder ein direkter Funktionsaufruf? | HIGH |
| Wie wird der Autonomie-Status im Windsurf-UI sichtbar gemacht (Dashboard)? | MEDIUM |
| Soll es eine manuelle Override-Funktion geben ("force AUTONOMOUS für Task-Typ X")? | MEDIUM |
| Hysterese: 24h zwischen Promotions — oder besser N Executions? | LOW |

---

## Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-02-23 | Achim Dehnert | Initial Proposed |
