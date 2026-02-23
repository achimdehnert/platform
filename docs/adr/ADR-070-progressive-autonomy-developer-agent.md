# ADR-070: Progressive Autonomy Pattern für den Developer-Agenten

| Feld | Wert |
|------|------|
| **Status** | Accepted |
| **Datum** | 2026-02-23 |
| **Autor** | Achim Dehnert |
| **Supersedes** | — |
| **Related** | ADR-066, ADR-067, ADR-068, CONCEPT-001 |

---

## Kontext

ADR-066 definiert den `Developer`-Agenten als eine der vier Kernrollen des
AI Engineering Squad. Zwei architektonische Fragen wurden in dieser Version
beantwortet:

1. **Hybrid-Architektur**: `developer.py` ist weder rein autonom noch rein
   Cascade-gesteuert, sondern ein **Progressive Autonomy Hybrid** (→ Entscheidung
   unten).

2. **`cascade_execute()` Implementierung**: Direkter Funktionsaufruf oder
   MCP-Tool-Call? (→ Entscheidung unten, tiefe Analyse in §3)

---

## Entscheidung 1: Progressive Autonomy Hybrid

Der Developer-Agent startet als Cascade-gesteuerter Koordinations-Wrapper
(Gate 1–2). Für jeden Task-Typ wird separat gemessen, ob autonome LLM-Execution
zuverlässig funktioniert. Bei nachgewiesener Qualität (≥ 3 Erfolge, Score ≥ 0.85)
wird der Task-Typ auf Gate 0 (Autonomous) herabgestuft. Bei Qualitätsverlust
wird automatisch zurückgestuft.

---

## Entscheidung 2: `cascade_execute()` als direkter Funktionsaufruf

**`cascade_execute()` wird als direkter Python-Funktionsaufruf implementiert —
kein MCP-Tool-Call.**

### Analyse: MCP-Tool-Call vs. direkter Funktionsaufruf

#### Das MCP-Problem (aus ADR-067, empirisch belegt)

ADR-067 dokumentiert die konkreten Symptome des MCP-SSH-Problems:

```
git_manage stash         → hängt, kein Response nach 60s
docker_manage compose_up → blockiert Windsurf-Event-Loop
ssh_manage exec          → Timeout bei langen Operationen (30–120s)
```

**Ursache**: Das MCP-Protokoll ist **synchron**. Jeder Tool-Call öffnet eine neue
Verbindung, wartet auf Antwort, blockiert den Event-Loop. Das ist kein
Konfigurationsfehler — es ist ein strukturelles Protokoll-Problem.

Ein `cascade_execute()` als MCP-Tool-Call würde **dasselbe strukturelle Problem**
in `developer.py` einführen:

```
developer.py ruft MCP-Tool auf
  → MCP öffnet Verbindung zu Cascade/Windsurf
  → Wartet auf Antwort (synchron)
  → Bei langen Code-Generierungs-Tasks (30–120s): Timeout
  → Event-Loop blockiert
  → Identisches Problem wie deployment-mcp Write-Tools
```

#### Warum "Cascade ruft sich selbst via MCP auf" nicht funktioniert

Das Konzept "Cascade ruft sich selbst via MCP auf" hat einen fundamentalen
Architektur-Fehler: **Cascade ist der MCP-Client, nicht der MCP-Server**.

```
FALSCH (konzeptuell):
  developer.py (läuft in Cascade)
    → mcp_tool_call("cascade_execute", ...)
    → Cascade empfängt Tool-Call von sich selbst
    → Führt aus
    → Antwortet an sich selbst
  Problem: Cascade ist kein MCP-Server. Es gibt keinen Endpoint.

RICHTIG:
  developer.py (läuft in Cascade)
    → cascade_execute(plan)  # direkter Funktionsaufruf
    → Cascade führt den Plan als nächste Aktion aus
    → Kein Netzwerk-Overhead, kein Timeout-Risiko
```

#### Best Practices: Wann MCP, wann direkter Aufruf?

| Kriterium | MCP-Tool-Call | Direkter Funktionsaufruf |
|-----------|--------------|--------------------------|
| **Externe Ressource** (SSH, GitHub, DB) | ✅ richtig | — |
| **Interner Aufruf** (gleicher Prozess) | ❌ Overhead | ✅ richtig |
| **Lange Operation** (> 10s) | ❌ Timeout-Risiko | ✅ kein Timeout |
| **Audit-Trail nötig** | ✅ MCP-Log | ✅ AuditStore direkt |
| **Fehlerbehandlung** | ❌ MCP-Error-Wrapping | ✅ native Python-Exceptions |
| **Testbarkeit** | ❌ Mock-Aufwand | ✅ direkt mockbar |
| **Autonomie-Ziel** | ❌ Flaschenhals | ✅ skaliert |

**Fazit**: MCP ist das richtige Protokoll für **externe Ressourcen** (ADR-067:
GitHub Actions, SSH-Read-Ops). Für **interne Koordination** innerhalb von
`developer.py` ist es der falsche Layer.

#### Die drei Ausführungsmodi ohne MCP

```python
async def cascade_execute(plan: TaskPlan, mode: DeveloperMode) -> ExecutionResult:
    """
    Direkter Funktionsaufruf — kein MCP-Tool-Call.

    CASCADE_CONTROLLED: LLM erstellt Plan, Cascade führt aus.
      → plan enthält strukturierte Anweisungen (Pydantic v2)
      → Cascade liest plan.steps und führt sie sequentiell aus
      → Kein Netzwerk-Hop, kein Timeout

    SUPERVISED: LLM führt aus, Ergebnis wird geprüft.
      → litellm.acompletion() mit code_generation-Prompt
      → Ergebnis wird durch evaluator.py bewertet
      → Bei Score < threshold: Cascade übernimmt

    AUTONOMOUS: LLM führt vollständig aus.
      → litellm.acompletion() ohne Cascade-Eingriff
      → Nur QualityEvaluator prüft
    """
    match mode:
        case DeveloperMode.CASCADE_CONTROLLED:
            return await _cascade_controlled_execute(plan)
        case DeveloperMode.SUPERVISED:
            return await _supervised_execute(plan)
        case DeveloperMode.AUTONOMOUS:
            return await _autonomous_execute(plan)
```

#### Audit-Trail ohne MCP

Der AuditStore (`audit_store.py`) loggt jeden Aufruf direkt — kein MCP-Log nötig:

```python
audit_store.log({
    "task_id": task.task_id,
    "action": f"cascade_execute:{mode.value}",
    "model": model_config["model"],
    "gate": gate_for_mode(mode),
    "status": "success" | "failure",
    "cost_usd": response.usage.total_tokens * COST_PER_TOKEN,
    "details": f"quality_score={quality.score:.3f} promoted={promoted}",
})
```

---

## Architektur: Progressive Autonomy

### Drei Ausführungsmodi

```
DeveloperMode.CASCADE_CONTROLLED   # Gate 2 — Cascade führt aus, LLM plant
DeveloperMode.SUPERVISED           # Gate 1 — LLM führt aus, Cascade überwacht
DeveloperMode.AUTONOMOUS           # Gate 0 — LLM führt vollständig autonom aus
```

### Promotion / Demotion

```
PROMOTION: 3 konsekutive Erfolge mit Score ≥ 0.85 → nächster Modus
DEMOTION:  Score < 0.70 → sofort zurück zum vorherigen Modus
HYSTERESE: min. 24h zwischen Promotions (verhindert Pendeln)
```

### Ablauf pro Task-Execution

```
execute_task(task) → ExecutionResult:

  1. Lade AutonomyProfile für task.task_type
  2. Wähle mode = profile.mode

  3. Führe aus (direkter Funktionsaufruf, kein MCP):
     CASCADE_CONTROLLED → _cascade_controlled_execute(plan)
     SUPERVISED         → _supervised_execute(plan)
     AUTONOMOUS         → _autonomous_execute(plan)

  4. evaluate(result) via evaluator.py (ADR-068)

  5. Update AutonomyProfile (promote/demote)

  6. Log in AuditStore (direkt, kein MCP)

  7. Return ExecutionResult
```

### Task-Typ-Deckel (max_mode_ceiling)

```python
"max_mode_ceiling": {
    "db_migration":    DeveloperMode.SUPERVISED,   # nie AUTONOMOUS
    "security":        DeveloperMode.SUPERVISED,   # nie AUTONOMOUS
    "breaking_change": DeveloperMode.SUPERVISED,   # nie AUTONOMOUS
    "lint":            DeveloperMode.AUTONOMOUS,   # kein Deckel
    "typo":            DeveloperMode.AUTONOMOUS,   # kein Deckel
    "docs":            DeveloperMode.AUTONOMOUS,   # kein Deckel
}
```

---

## Implementierungsstruktur

```
orchestrator_mcp/agent_team/
  utils.py              # llm_call_with_retry(), FALLBACK_CHAIN  (NEU — zuerst)
  evaluator.py          # QualityEvaluator — ADR-068             (NEU — Voraussetzung)
  autonomy_store.py     # AutonomyProfile Persistenz             (NEU)
  developer.py          # Progressive Autonomy Hybrid            (NEU)
  metrics.py            # TaskQualityScore + Feedback-Loop       (NEU — danach)
```

**Reihenfolge**: `utils.py` → `evaluator.py` → `autonomy_store.py` → `developer.py` → `metrics.py`

### Datenbank-Schema (autonomy_store)

```sql
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
```

---

## Konsequenzen

### Positiv

- **Kein MCP-Timeout-Risiko**: Direkter Funktionsaufruf — kein Event-Loop-Block
- **Vollständig autonom skalierbar**: AUTONOMOUS-Modus braucht keine Cascade-Interaktion
- **Testbar**: Alle drei Modi direkt mockbar ohne MCP-Infrastruktur
- **Audit-Trail**: AuditStore loggt jeden Aufruf direkt
- **Konsistent mit ADR-067**: MCP nur für externe Ressourcen (GitHub, SSH-Read)
- **Task-typ-spezifisch lernend**: `lint` wird autonom, `db_migration` nie

### Negativ / Risiken

| Risiko | Mitigation |
|--------|------------|
| `evaluator.py` Voraussetzung | Implementierungsreihenfolge erzwingen |
| Pendeln bei Grenzwert-Tasks | Hysterese: 24h zwischen Promotions |
| Kalt-Start neue Task-Typen | `task_type_overrides` für bekannte einfache Typen |

---

## Offene Fragen (gelöst)

| Frage | Entscheidung |
|-------|-------------|
| MCP-Tool-Call oder direkter Aufruf? | **Direkter Funktionsaufruf** — MCP strukturell ungeeignet |
| Hysterese: Zeit oder Executions? | **24h** — verhindert schnelles Pendeln bei Burst-Tasks |
| Manuelle Override-Funktion? | **Ja** — `force_mode(task_type, mode)` in `autonomy_store.py` |

---

## Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-02-23 | Achim Dehnert | v1 — Initial Proposed, offene Frage cascade_execute() |
| 2026-02-23 | Achim Dehnert | v2 — Accepted; cascade_execute() als direkter Funktionsaufruf entschieden; tiefe MCP-Analyse ergänzt |
| 2026-02-23 | Achim Dehnert | v3 — Umnummeriert von ADR-069 auf ADR-070 (069 bereits vergeben) |
