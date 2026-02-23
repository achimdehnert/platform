---
title: "Agent Task Catalog — Autonomie-Grade, Priorisierung und Tracking"
id: "CONCEPT-002"
status: "accepted"
date: 2026-02-23
author: [Achim Dehnert]
related_adrs:
  - ADR-066-ai-engineering-team.md
  - ADR-068-adaptive-model-routing.md
  - ADR-069-progressive-autonomy-developer-agent.md
tags: [agent-team, autonomy, task-catalog, tracking, progressive-autonomy]
---

# Agent Task Catalog — Autonomie-Grade, Priorisierung und Tracking

> **Zweck**: Priorisierte Liste aller Task-Typen des AI Engineering Squad mit
> initialem Autonomie-Grad, Ceiling, Tracking-Schema und Plot-Konzept.
> Basis für das Progressive Autonomy Pattern (ADR-069).

---

## 1. Autonomie-Stufen (Referenz)

| Stufe | DeveloperMode | Gate | Beschreibung |
|-------|--------------|------|-------------|
| **A0** | `CASCADE_CONTROLLED` | 2 | LLM plant, Cascade führt aus |
| **A1** | `SUPERVISED` | 1 | LLM führt aus, Cascade prüft |
| **A2** | `AUTONOMOUS` | 0 | LLM vollständig autonom, nur QualityEval |

**Ceiling**: Maximale Stufe, die ein Task-Typ je erreichen kann (unabhängig von Score).

---

## 2. Task-Katalog (priorisiert nach Automatisierungspotential)

> **Legende**:
> - **Prio**: Reihenfolge der Implementierung (1 = zuerst automatisieren)
> - **Start**: Initialer Autonomie-Grad beim ersten Deployment
> - **Ceiling**: Maximale erreichbare Stufe
> - **Frequenz**: Geschätzte Ausführungen pro Monat
> - **Risiko**: Schadensmöglichkeit bei Fehler (LOW/MEDIUM/HIGH/CRITICAL)

### Kategorie 1: Code-Qualität und Analyse (sofort automatisierbar)

| Prio | Task-Typ | Agent | Start | Ceiling | Frequenz | Risiko | Begründung |
|------|----------|-------|-------|---------|----------|--------|------------|
| 1 | `lint_fix` | Developer | A1 | A2 | 50+ | LOW | Deterministisch, Ruff-Output eindeutig |
| 2 | `typo_fix` | Developer | A1 | A2 | 20+ | LOW | Minimale Änderung, leicht verifizierbar |
| 3 | `docstring_add` | Developer | A1 | A2 | 30+ | LOW | Kein Logik-Änderung, nur Dokumentation |
| 4 | `type_hint_add` | Developer | A1 | A2 | 20+ | LOW | Statisch prüfbar via mypy |
| 5 | `import_sort` | Developer | A2 | A2 | 50+ | LOW | Vollständig deterministisch (isort) |
| 6 | `dead_code_remove` | Re-Engineer | A0 | A1 | 10 | MEDIUM | Vulture-Output eindeutig, aber Risiko |
| 7 | `coverage_gap_analyze` | Tester | A2 | A2 | 30+ | LOW | Nur Analyse, keine Änderung |

### Kategorie 2: Test-Generierung (hohe Frequenz, gutes Automatisierungspotential)

| Prio | Task-Typ | Agent | Start | Ceiling | Frequenz | Risiko | Begründung |
|------|----------|-------|-------|---------|----------|--------|------------|
| 8 | `unit_test_write` | Developer | A0 | A1 | 40+ | LOW | Neue Tests können nichts kaputt machen |
| 9 | `test_suite_run` | Tester | A2 | A2 | 100+ | LOW | Nur Ausführung, keine Änderung |
| 10 | `coverage_report` | Tester | A2 | A2 | 30+ | LOW | Read-only |
| 11 | `regression_test` | Tester | A1 | A2 | 20+ | MEDIUM | Kritisch bei Breaking Changes |
| 12 | `integration_test_write` | Developer | A0 | A1 | 10 | MEDIUM | Komplexer als Unit-Tests |

### Kategorie 3: Standard-Features (mittleres Automatisierungspotential)

| Prio | Task-Typ | Agent | Start | Ceiling | Frequenz | Risiko | Begründung |
|------|----------|-------|-------|---------|----------|--------|------------|
| 13 | `bug_fix_simple` | Developer | A0 | A1 | 15 | MEDIUM | Klar definierter Fehler, isoliert |
| 14 | `feature_crud` | Developer | A0 | A1 | 10 | MEDIUM | CRUD-Pattern bekannt, Django-Standard |
| 15 | `model_field_add` | Developer | A0 | A1 | 10 | MEDIUM | Migration nötig — Ceiling A1 |
| 16 | `api_endpoint_add` | Developer | A0 | A1 | 8 | MEDIUM | DRF-Pattern bekannt |
| 17 | `template_update` | Developer | A0 | A1 | 15 | LOW | UI-only, kein Backend-Risiko |
| 18 | `refactor_extract` | Re-Engineer | A0 | A1 | 8 | MEDIUM | Isolierte Extraktion, Tests prüfen |
| 19 | `dependency_update_patch` | Developer | A0 | A1 | 5 | MEDIUM | Patch-Version: gering, Minor: höher |
| 20 | `config_update` | Developer | A0 | A1 | 10 | MEDIUM | Settings-Änderungen, kein Code |

### Kategorie 4: ADR-basierte Entwicklung (Kernworkflow)

| Prio | Task-Typ | Agent | Start | Ceiling | Frequenz | Risiko | Begründung |
|------|----------|-------|-------|---------|----------|--------|------------|
| 21 | `adr_parse` | Tech Lead | A0 | A2 | 5 | LOW | Nur Lesen + Strukturieren |
| 22 | `task_plan_create` | Tech Lead | A0 | A1 | 5 | MEDIUM | Plan-Fehler propagieren |
| 23 | `feature_complex` | Developer | A0 | A1 | 5 | HIGH | Multi-File, Cross-App |
| 24 | `code_review` | Tech Lead | A0 | A1 | 20 | MEDIUM | Review ist Advisory, kein Merge |
| 25 | `impact_report` | Re-Engineer | A0 | A1 | 5 | LOW | Nur Analyse, keine Änderung |
| 26 | `refactor_complex` | Re-Engineer | A0 | A0 | 3 | HIGH | Immer Cascade-Kontrolle |

### Kategorie 5: Infrastruktur und Deployment (strenge Kontrolle)

| Prio | Task-Typ | Agent | Start | Ceiling | Frequenz | Risiko | Begründung |
|------|----------|-------|-------|---------|----------|--------|------------|
| 27 | `deploy_trigger` | Developer | A0 | A1 | 10 | HIGH | Via GitHub Actions (ADR-067), nie direkt |
| 28 | `health_check` | Tester | A1 | A2 | 50+ | LOW | Read-only, kein Risiko |
| 29 | `log_analysis` | Re-Engineer | A1 | A2 | 20 | LOW | Read-only |
| 30 | `db_migration_create` | Developer | A0 | A0 | 5 | CRITICAL | Immer Cascade-Kontrolle, kein Ceiling |
| 31 | `db_migration_run` | Developer | A0 | A0 | 5 | CRITICAL | Gate 4 — Human-Only |
| 32 | `breaking_change` | Developer | A0 | A0 | 2 | CRITICAL | Gate 3–4, immer Mensch |
| 33 | `security_fix` | Developer | A0 | A0 | 3 | CRITICAL | Gate 3, immer Mensch |
| 34 | `prod_rollback` | Developer | A0 | A0 | 1 | CRITICAL | Gate 4 — Human-Only |

---

## 3. Zusammenfassung nach Autonomie-Ceiling

| Ceiling | Anzahl Task-Typen | Beispiele |
|---------|------------------|----------|
| **A2 (AUTONOMOUS)** | 8 | `lint_fix`, `import_sort`, `test_suite_run`, `coverage_report`, `adr_parse` |
| **A1 (SUPERVISED)** | 18 | `unit_test_write`, `bug_fix_simple`, `feature_crud`, `api_endpoint_add` |
| **A0 (CASCADE_CONTROLLED)** | 8 | `db_migration_*`, `breaking_change`, `security_fix`, `prod_rollback` |

**Automatisierungspotential**: 76% der Task-Typen können über A0 hinaus skalieren.
**Dauerhaft manuell**: 24% (kritische Infrastruktur, Sicherheit, Prod-Ops).

---

## 4. Tracking-Schema

### 4.1 Datenbank-Tabellen

```sql
-- Autonomie-Profile (aus ADR-069)
CREATE TABLE developer_autonomy_profiles (
    task_type         VARCHAR(50) PRIMARY KEY,
    mode              VARCHAR(30) NOT NULL DEFAULT 'cascade_controlled',
    success_count     INTEGER DEFAULT 0,
    failure_count     INTEGER DEFAULT 0,
    avg_quality_score NUMERIC(4,3) DEFAULT 0.0,
    total_executions  INTEGER DEFAULT 0,
    promoted_at       TIMESTAMPTZ,
    demoted_at        TIMESTAMPTZ,
    updated_at        TIMESTAMPTZ DEFAULT NOW()
);

-- Execution-History für Plotting
CREATE TABLE agent_execution_history (
    id              SERIAL PRIMARY KEY,
    executed_at     TIMESTAMPTZ DEFAULT NOW(),
    task_type       VARCHAR(50) NOT NULL,
    agent_role      VARCHAR(30) NOT NULL,
    mode_used       VARCHAR(30) NOT NULL,
    quality_score   NUMERIC(4,3),
    cost_usd        NUMERIC(10,6) DEFAULT 0,
    duration_seconds NUMERIC(8,2),
    promoted        BOOLEAN DEFAULT FALSE,
    demoted         BOOLEAN DEFAULT FALSE,
    workflow_id     VARCHAR(50),
    model_used      VARCHAR(100)
);

-- Index für Zeitreihen-Queries
CREATE INDEX idx_exec_history_task_time
    ON agent_execution_history (task_type, executed_at DESC);
CREATE INDEX idx_exec_history_mode
    ON agent_execution_history (mode_used, executed_at DESC);
```

### 4.2 Key Metrics pro Task-Typ

```python
class TaskTypeMetrics(BaseModel):
    task_type: str
    current_mode: DeveloperMode
    ceiling: DeveloperMode
    total_executions: int
    autonomous_rate: float        # % Executions in AUTONOMOUS-Modus
    avg_quality_score: float      # Ø Score letzte 30 Tage
    avg_cost_usd: float           # Ø Kosten pro Execution
    avg_duration_seconds: float   # Ø Dauer pro Execution
    promotion_count: int          # Wie oft hochgestuft
    demotion_count: int           # Wie oft zurückgestuft
    last_promotion: datetime | None
    last_demotion: datetime | None
    trend: str                    # "improving" | "stable" | "degrading"
```

### 4.3 Aggregierte Platform-Metriken

```python
class PlatformAutonomyMetrics(BaseModel):
    snapshot_at: datetime
    total_executions_30d: int
    autonomous_executions_30d: int     # Mode = AUTONOMOUS
    supervised_executions_30d: int     # Mode = SUPERVISED
    cascade_executions_30d: int        # Mode = CASCADE_CONTROLLED
    overall_autonomy_rate: float       # autonomous / total
    avg_quality_score: float
    total_cost_usd_30d: float
    cost_saved_vs_cascade: float       # Einsparung durch Autonomie
    task_types_at_autonomous: int      # Wie viele Task-Typen bei A2
    task_types_at_supervised: int
    task_types_at_cascade: int
```

---

## 5. Plot-Konzept

### Plot 1: Autonomie-Fortschritt über Zeit (Heatmap)

```
Y-Achse: Task-Typen (sortiert nach Prio)
X-Achse: Zeit (Wochen)
Farbe:   A0=Rot, A1=Gelb, A2=Grün

Beispiel nach 3 Monaten:

lint_fix         [R][R][Y][Y][G][G][G][G][G][G][G][G]
import_sort      [G][G][G][G][G][G][G][G][G][G][G][G]
unit_test_write  [R][R][R][Y][Y][Y][G][G][G][G][G][G]
bug_fix_simple   [R][R][R][R][Y][Y][Y][Y][Y][Y][Y][Y]
feature_crud     [R][R][R][R][R][Y][Y][Y][Y][Y][Y][Y]
db_migration     [R][R][R][R][R][R][R][R][R][R][R][R]  (Ceiling A0)

Legende: R=CASCADE_CONTROLLED, Y=SUPERVISED, G=AUTONOMOUS
```

### Plot 2: Autonomie-Rate über Zeit (Liniendiagramm)

```
Y-Achse: % Executions in AUTONOMOUS-Modus (0-100%)
X-Achse: Zeit (Monate)
Linien:  Gesamt, Kategorie-1, Kategorie-2, Kategorie-3

Erwarteter Verlauf:
Monat 1:  5%  (nur import_sort)
Monat 2: 25%  (lint, typo, test_suite_run)
Monat 3: 45%  (+ unit_test_write, coverage_report)
Monat 6: 65%  (+ bug_fix_simple, feature_crud)
```

### Plot 3: Qualitäts-Score vs. Autonomie-Grad (Scatter)

```
X-Achse: Autonomie-Grad (0=CASCADE, 1=SUPERVISED, 2=AUTONOMOUS)
Y-Achse: Quality Score (0.0-1.0)
Punkte:  Jede Execution (letzte 30 Tage)
Farbe:   Task-Typ-Kategorie

Erwartetes Muster:
- Kategorie 1 (Qualität): Cluster bei A2, Score 0.85-0.98
- Kategorie 3 (Features): Cluster bei A0-A1, Score 0.70-0.90
- Kategorie 5 (Infra): Nur A0, Score 0.90+ (Mensch prüft)
```

### Plot 4: Kosten-Einsparung durch Autonomie (Bar Chart)

```
Y-Achse: Kosten in USD/Monat
X-Achse: Monate
Bars:    Cascade-Kosten (hypothetisch) vs. Tatsächliche Kosten

Einsparung = (Cascade-Overhead-Zeit * Cascade-Stundensatz) - LLM-API-Kosten
```

### Plot 5: Promotion/Demotion-Events (Timeline)

```
Y-Achse: Task-Typen
X-Achse: Zeit
Events:  ↑ Promotion (grüner Pfeil), ↓ Demotion (roter Pfeil)

Zeigt: Welche Task-Typen sind stabil, welche pendeln?
Aktion: Pendelnde Task-Typen → Hysterese erhöhen oder Ceiling senken
```

---

## 6. Implementierungs-Roadmap

### Phase 1: Tracking-Infrastruktur (Woche 1-2)

```
1. utils.py          — llm_call_with_retry(), FALLBACK_CHAIN
2. evaluator.py      — QualityEvaluator (Voraussetzung für alle Scores)
3. autonomy_store.py — DB-Schema + CRUD für AutonomyProfiles
4. metrics.py        — TaskTypeMetrics, PlatformAutonomyMetrics
```

### Phase 2: Erste autonome Task-Typen (Woche 3-4)

Start mit den 7 Kategorie-1-Tasks (Prio 1-7):
```
import_sort    → direkt A2 (deterministisch)
lint_fix       → Start A1, Ziel A2
typo_fix       → Start A1, Ziel A2
docstring_add  → Start A1, Ziel A2
type_hint_add  → Start A1, Ziel A2
```

### Phase 3: Test-Generierung (Woche 5-8)

```
test_suite_run    → direkt A2
coverage_report   → direkt A2
unit_test_write   → Start A0, Ziel A1
regression_test   → Start A1, Ziel A2
```

### Phase 4: Standard-Features (Monat 3-4)

```
bug_fix_simple    → Start A0, Ziel A1
feature_crud      → Start A0, Ziel A1
api_endpoint_add  → Start A0, Ziel A1
```

### Phase 5: Monitoring + Plots (parallel ab Phase 2)

```
SQL-Queries für alle 5 Plots
Cron-Job: tägliche Metriken-Aggregation
Optional: Django-Admin-View in orchestrator_mcp
```

---

## 7. SQL-Queries für Plots

### Autonomie-Rate letzte 30 Tage

```sql
SELECT
    DATE_TRUNC('week', executed_at) AS week,
    COUNT(*) AS total,
    COUNT(*) FILTER (WHERE mode_used = 'autonomous') AS autonomous,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE mode_used = 'autonomous') / COUNT(*),
        1
    ) AS autonomy_rate_pct
FROM agent_execution_history
WHERE executed_at >= NOW() - INTERVAL '30 days'
GROUP BY 1
ORDER BY 1;
```

### Aktueller Autonomie-Grad pro Task-Typ

```sql
SELECT
    p.task_type,
    p.mode AS current_mode,
    p.avg_quality_score,
    p.total_executions,
    p.success_count,
    p.failure_count,
    COALESCE(
        ROUND(100.0 * h.autonomous_count / NULLIF(h.total, 0), 1),
        0
    ) AS autonomous_rate_pct
FROM developer_autonomy_profiles p
LEFT JOIN (
    SELECT
        task_type,
        COUNT(*) AS total,
        COUNT(*) FILTER (WHERE mode_used = 'autonomous') AS autonomous_count
    FROM agent_execution_history
    WHERE executed_at >= NOW() - INTERVAL '30 days'
    GROUP BY task_type
) h ON p.task_type = h.task_type
ORDER BY
    CASE p.mode
        WHEN 'autonomous' THEN 0
        WHEN 'supervised' THEN 1
        ELSE 2
    END,
    p.avg_quality_score DESC;
```

### Kosten-Einsparung durch Autonomie

```sql
SELECT
    DATE_TRUNC('month', executed_at) AS month,
    SUM(cost_usd) AS actual_cost_usd,
    -- Hypothetische Cascade-Kosten: autonome Tasks * Ø CASCADE_CONTROLLED-Kosten
    SUM(cost_usd) FILTER (WHERE mode_used != 'autonomous') +
    COUNT(*) FILTER (WHERE mode_used = 'autonomous') *
        AVG(cost_usd) FILTER (WHERE mode_used = 'cascade_controlled')
        AS hypothetical_cascade_cost_usd
FROM agent_execution_history
GROUP BY 1
ORDER BY 1;
```

---

## 8. Referenzen

- [ADR-066: AI Engineering Squad](../adr/ADR-066-ai-engineering-team.md)
- [ADR-068: Adaptive Model Routing](../adr/ADR-068-adaptive-model-routing.md)
- [ADR-069: Progressive Autonomy Pattern](../adr/ADR-069-progressive-autonomy-developer-agent.md)
- [CONCEPT-001: OpenCLAW Integration](CONCEPT-001-openclaw-integration.md)

---

## Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-02-23 | Achim Dehnert | Initial — Task-Katalog, Tracking-Schema, Plot-Konzept |
