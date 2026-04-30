---
status: proposed
date: 2026-04-30
deciders: [achimdehnert, cascade]
related: [ADR-066, ADR-068, ADR-173, ADR-174]
tags: [agent-team, llm-routing, cost-optimization, autonomy]
---

# ADR-177 — Agent Role Specialization

**Split monolithic Developer into DocBot, TestBot, FeatureBot, ArchitectBot.**

## Context

Der aktuelle `DeveloperAgent` im `orchestrator_mcp` bearbeitet **alle** Task-Types von Typo-Fixes bis Feature-Implementation mit dem gleichen Modell (`swe`).

### Probleme

1. **Überqualifikation** — Typo-Fix braucht kein SWE-Modell (`gpt_low` reicht, 3× billiger)
2. **Unterqualifikation** — Architecture-Tasks scheitern am SWE-Modell (bräuchten `opus`)
3. **Keine Skill-Trennung** — Kein spezialisiertes Prompt-Engineering für Docs vs Tests vs Code
4. **Tech Lead ist Stub** — Gate 2+ Tasks müssen komplett an Menschen (keine Agent-Option für architekturelle Arbeit)
5. **Re-Engineer ist Stub** — Refactoring wird vom generischen Developer gemacht

**Messung:** Laut `orchestrator_mcp/config.py:MODEL_SELECTION` werden bereits Model-Mappings gepflegt, aber alle führen zum gleichen `developer`-Agent.

## Decision

**4 spezialisierte Agents** statt einem Monolith:

| Agent | Task-Types | Modell | Gate | Prompt-Style |
|-------|-----------|--------|------|--------------|
| **DocBot** | `docs`, `typo`, `lint`, CHANGELOG, README, ADR-Text | `gpt_low` | 0-1 | Editing-focused, minimal invasive |
| **TestBot** | `test`, Fixtures, Factories, Coverage-Fixes | `gpt_low` | 0-1 | `test_should_*` Naming, iil-testkit-aware |
| **FeatureBot** | `feature`, `bugfix`, `refactor` (Gate ≤ 2) | `swe` | 1-2 | Service-Layer-enforcing, Ruff-clean |
| **ArchitectBot** | `architecture`, `breaking_change`, `security`, ADR-Drafts | `opus` | 2-3 | ADR-aware, Design-oriented |

### Keeper aus ADR-066

- **Guardian** (Lint/Security/Tests) — bleibt cross-cutting, prüft Output aller 4 Agents
- **Tester** (pytest-Runner) — bleibt als Verifikations-Stufe
- **Planner** (agent_plan_task) — entscheidet **welcher Agent** zugeteilt wird
- **Merger** — fasst parallele Agent-Branches zusammen (Vorbereitung für Wave 4)
- **Tech Lead** — bleibt als Human-Escalation für Gate 3+

### Routing-Logik (im `Planner`)

```python
def select_agent(task_type, complexity, gate):
    if task_type in {"docs", "typo", "lint"}:
        return DocBot(model="gpt_low")
    if task_type == "test":
        return TestBot(model="gpt_low")
    if task_type in {"architecture", "breaking_change", "security"}:
        return ArchitectBot(model="opus")
    if complexity == "architectural":
        return ArchitectBot(model="opus")
    # Default
    return FeatureBot(model="swe")
```

## Considered Alternatives

### A) Status quo (ein Developer für alles)

- ❌ **Kosten:** typo_fix = $0.003 statt $0.001 (3× zu teuer)
- ❌ **Qualität:** Architecture-Tasks scheitern — `swe`-Model kann keine ADRs
- ✅ **Einfachheit:** eine Code-Basis

### B) Per-Task-Type Model-Dispatch ohne Agent-Split (nur Model-Routing)

- ✅ Löst Kostenproblem sofort
- ❌ Kein spezialisiertes Prompt-Engineering
- ❌ Kein domänenspezifischer Kontext (DocBot weiß nichts von ADR-Struktur)
- ❌ Tech Lead bleibt Stub

### C) Volle Spezialisierung (gewählt)

- ✅ Kostenoptimal
- ✅ Prompt-Engineering pro Rolle optimierbar
- ✅ Tech Lead evolviert zu ArchitectBot (kein Stub mehr)
- ⚠️ Größter Implementation-Aufwand (~1-2 Tage)

## Implementation

### Phase 1 — Code-Struktur

```
orchestrator_mcp/agents/
├── __init__.py
├── base.py           # BaseAgent — gemeinsame Interfaces
├── planner.py        # Routing: select_agent()
├── developer.py      # [DEPRECATED, wird zu feature_bot.py]
├── doc_bot.py        # NEU
├── test_bot.py       # NEU
├── feature_bot.py    # = bisheriger developer.py (umbenannt)
├── architect_bot.py  # NEU (ersetzt Tech Lead Stub)
├── guardian.py       # unverändert
├── tester.py         # unverändert
└── merger.py         # unverändert (Vorbereitung Wave 4)
```

### Phase 2 — Migration

1. `developer.py` → `feature_bot.py` (umbenennen, Scope einschränken)
2. `DocBot`, `TestBot`, `ArchitectBot` implementieren (je ~100 Zeilen)
3. `Planner.select_agent()` Routing-Funktion
4. `run_workflow` in `server.py` anpassen: Agent-Auswahl basiert auf `analyze_task`-Output
5. `agent_team_status` Response erweitern

### Phase 3 — Tests

- Unit: `tests/orchestrator_mcp/agents/test_doc_bot.py`, `test_test_bot.py`, etc.
- Integration: `test_planner_routing.py` — prüft Agent-Auswahl für alle Task-Types
- E2E: `test_run_workflow_routes_correctly.py` — ganzer Flow

### Phase 4 — Dokumentation

- `platform/docs/governance/agent-team.md` aktualisieren
- `/agentic-coding` Workflow v6 → v7 (neue Agent-Rollen in Step 1-Tabelle)

## Implementation Done When

- [ ] 4 Agent-Klassen implementiert + getestet (>80% Coverage)
- [ ] `Planner.select_agent()` Routing-Funktion, 100% Coverage
- [ ] `agent_team_status` zeigt 4 Agents statt 1 Developer
- [ ] `analyze_task` Response enthält `recommended_agent` Feld
- [ ] Migration-Guide für bestehende `delegate_subtask`-Caller
- [ ] CHANGELOG in `mcp-hub`
- [ ] ADR-177 Status: `accepted`

## Consequences

### Positive

- **Cost Reduction:** Schätzung −40 % bei typischer Workload (viele Docs/Tests, wenige Architecture)
- **Quality Up:** Architecture-Tasks bekommen `opus` statt `swe` → weniger gescheiterte ADR-Drafts
- **Fully Autonomous:** Auch Gate 2 Tasks können durch ArchitectBot bearbeitet werden (bisher: Tech Lead Stub → Mensch)
- **Parallelisierung vorbereitet** (Wave 4): Verschiedene Agents für verschiedene Branches

### Negative

- **Code-Komplexität:** 4 statt 1 Agent-Klasse
- **Test-Aufwand:** initial ~8 h für 80 % Coverage
- **Migration-Risiko:** bestehende `delegate_subtask(...)`-Aufrufer müssen ggf. `task_type` explizit setzen

### Neutral

- `MODEL_SELECTION` bleibt als Mapping-Table, wird aber von Planner konsumiert statt von `server.py` direkt.

## Rollout-Plan

1. **Woche 1**: Phase 1 (Code-Struktur) + Phase 2 (Migration) — getrennter Branch `feat/agent-specialization`
2. **Woche 1**: Phase 3 (Tests) — parallel
3. **Woche 2**: Dry-Run mit wenigen Test-Tasks, dann Rollout
4. **Woche 2**: `/agentic-coding` v7 Update + Workflow-Sync
5. **Woche 3**: Beobachtung, Metriken (`session_stats`), ggf. Nachjustierung `MODEL_SELECTION`

## References

- ADR-066 — Agent Team Architecture (4 Rollen: Developer, Guardian, Tester, Tech Lead)
- ADR-068 — AuditStore (Agent-Aktionen werden geloggt)
- ADR-173 — Orchestrator MCP Server
- ADR-174 — QM Gate (ASSUMPTION[unverified] = 0)
- `/agentic-coding` Workflow v6 — Auto-Dispatch Router
- `/process-agent-queue` Workflow — Queue-Prozessor (nutzt Agent-Auswahl aus Planner)
