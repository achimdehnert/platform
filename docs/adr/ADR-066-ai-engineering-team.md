---
status: "accepted"
date: 2026-02-22
decision-makers: [Achim Dehnert]
consulted: []
informed: []
supersedes: ["ADR-014-ai-native-development-teams.md"]
amends: []
related: ["ADR-057-platform-test-strategy.md", "ADR-058-platform-test-taxonomy.md", "ADR-067-work-management-strategy.md", "ADR-068-adaptive-model-routing.md"]
---

# Adopt a structured AI Engineering Squad with role-based agents and gate-controlled workflows

> **Konzeptbasis**: `mcp-hub` Branch `claude/ai-engineering-team-concept-06LJF`
> (2026-02-22). Dieses ADR supersedes ADR-014, das ein konzeptuelles Team Alpha/Bravo
> Modell definiert hat. ADR-066 ersetzt es durch eine konkrete, implementierbare
> Rollenarchitektur.

---

## Context and Problem Statement

ADR-014 definierte das AI-Native Development Model auf konzeptueller Ebene
(Hybrid Human-AI, Gate-System, Team Alpha/Bravo). In der Praxis fehlte eine
**konkrete Implementierungsarchitektur**:

- Welche Agenten-Rollen existieren mit welchen Verantwortungen?
- Wie werden ADRs systematisch in ausführbaren Code übersetzt?
- Wie wird Qualität ohne menschliches Eingreifen bei Routine-Tasks sichergestellt?
- Welche Modell-Tiers werden für welche Rollen eingesetzt?

**Problem**: Jede Entwicklungsaufgabe wird ad-hoc an Cascade delegiert — ohne
definierte Rollen, ohne reproduzierbare Workflows, ohne Quality Gates. Das führt
zu inkonsistenter Qualität und fehlendem Audit-Trail.

ADR-014 (Team Alpha/Bravo) wird durch dieses ADR vollständig ersetzt, da das
Alpha/Bravo-Modell nie implementiert wurde und das neue Rollenmodell präziser
und direkt umsetzbar ist.

---

## Decision Drivers

- **Konsistenz**: Jeder Code-Change folgt demselben definierten Qualitätsprozess
- **Audit-Trail**: Alle AI-Aktionen sind nachvollziehbar (bestehender AuditStore)
- **ADR-Compliance**: Code wird systematisch gegen ADRs validiert
- **Kosteneffizienz**: Modell-Tier wird nach Aufgabenkomplexität gewählt
- **Menschliche Kontrolle**: Gate-Level skaliert mit dem Risiko der Aktion
- **Wiederverwendung**: Bestehende `orchestrator_mcp`-Infrastruktur wird erweitert

---

## Considered Options

### Option 1 — AI Engineering Squad: 4 AI-Rollen + 1 Quality Gate (gewählt)

Strukturiertes Team aus Tech Lead, Developer, Tester, Re-Engineer (AI-Agenten)
und Guardian (regelbasiertes Quality Gate), koordiniert durch Gate-System.

**Pro:**
- Klare Verantwortlichkeiten, kein "alles macht Cascade"
- Guardian als statisches Quality Gate läuft immer — kein LLM-Overhead
- ADR-basierte Entwicklung ist nachvollziehbar und reproduzierbar
- Bestehende `orchestrator_mcp`-Infrastruktur wird erweitert, nicht ersetzt
- Modell-Tiers ermöglichen Kostenoptimierung

**Contra:**
- Höhere Komplexität als Single-Agent-Ansatz
- High-Reasoning-Modelle für Tech Lead und Re-Engineer erhöhen API-Kosten
- Sequentielle Workflows erhöhen Durchlaufzeit gegenüber Single-Agent

---

### Option 2 — Single-Agent ohne Rollenstruktur (Status Quo)

Cascade/Windsurf übernimmt alle Aufgaben ohne definierte Rollen.

**Pro:** Einfach, kein Setup-Aufwand

**Contra:**
- Inkonsistente Qualität — kein definierter Prozess
- Kein Audit-Trail auf Rollen-Ebene
- Kein systematisches Quality Gate

**Verworfen**: Löst das Konsistenz- und Audit-Problem nicht.

---

### Option 3 — Vollautonomes System ohne Human-in-the-Loop

**Pro:** Maximale Geschwindigkeit

**Contra:**
- Kein menschliches Korrektiv bei Architekturentscheidungen
- Nicht vereinbar mit Platform-Governance-Anforderungen
- Kritische Entscheidungen (Prod-Deploy, Breaking Changes) erfordern menschliche Freigabe

**Verworfen**: Verletzt Governance-Anforderungen; Gate 3–4 sind nicht delegierbar.

---

### Option 4 — Externes CI/CD-only (GitHub Actions, kein lokaler Agent)

**Pro:** Kein lokaler Agent-Overhead, Standard-Tooling

**Contra:**
- Kein ADR-Parsing, keine intelligente Task-Zerlegung
- Kein Re-Engineering oder Code-Review durch AI
- Nur statische Checks, keine adaptive Qualitätssicherung

**Verworfen**: Deckt nur Quality-Gate-Aspekte ab, nicht ADR-basierte Entwicklung.

---

## Pros and Cons of the Options

### Option 1 — AI Engineering Squad (gewählt)

- **Pro**: Klare Verantwortlichkeiten — kein "alles macht Cascade"
- **Pro**: Guardian als statisches Quality Gate ohne LLM-Overhead
- **Pro**: ADR-basierte Entwicklung ist nachvollziehbar und reproduzierbar
- **Pro**: Bestehende `orchestrator_mcp`-Infrastruktur wird erweitert, nicht ersetzt
- **Pro**: Modell-Tiers ermöglichen Kostenoptimierung pro Aufgabentyp
- **Con**: Höhere Komplexität als Single-Agent-Ansatz
- **Con**: High-Reasoning-Modelle für Tech Lead und Re-Engineer erhöhen API-Kosten
- **Con**: Sequentielle Workflows erhöhen Durchlaufzeit gegenüber Single-Agent

### Option 2 — Single-Agent ohne Rollenstruktur (Status Quo)

- **Pro**: Einfach, kein Setup-Aufwand
- **Con**: Inkonsistente Qualität — kein definierter Prozess
- **Con**: Kein Audit-Trail auf Rollen-Ebene
- **Con**: Kein systematisches Quality Gate

### Option 3 — Vollautonomes System ohne Human-in-the-Loop

- **Pro**: Maximale Geschwindigkeit
- **Con**: Kein menschliches Korrektiv bei Architekturentscheidungen
- **Con**: Nicht vereinbar mit Platform-Governance-Anforderungen
- **Con**: Gate 3–4 sind nicht an AI delegierbar

### Option 4 — Externes CI/CD-only (GitHub Actions)

- **Pro**: Kein lokaler Agent-Overhead, Standard-Tooling
- **Con**: Kein ADR-Parsing, keine intelligente Task-Zerlegung
- **Con**: Kein Re-Engineering oder Code-Review durch AI
- **Con**: Nur statische Checks, keine adaptive Qualitätssicherung

---

## Decision Outcome

**Gewählt: Option 1** — Strukturiertes 4-Rollen-Team + Guardian Quality Gate,
implementiert als Erweiterung von `orchestrator_mcp/agent_team/`.

### Positive Consequences

- Klare Verantwortlichkeiten und reproduzierbare Workflows
- Guardian als statisches Quality Gate ohne LLM-Kosten
- ADR-basierte Entwicklung mit vollständigem Audit-Trail
- Modell-Tiers ermöglichen Kostenoptimierung pro Aufgabentyp

### Negative Consequences

- Höhere Komplexität als Single-Agent-Ansatz
- High-Reasoning-Modelle für Tech Lead und Re-Engineer erhöhen API-Kosten
- Sequentielle Workflows erhöhen Durchlaufzeit

---

## Implementation Details

### Team-Architektur

```
                    ┌─────────────────────┐
                    │    TECH LEAD (TL)    │
                    │  Tier: High-Reasoning│
                    │  Gate 2–4 | ADR-in   │
                    └──────────┬──────────┘
                               │
            ┌──────────────────┼──────────────────┐
            │                  │                  │
   ┌────────▼────────┐ ┌──────▼──────┐ ┌────────▼────────┐
   │  DEVELOPER (D)  │ │  TESTER (T)  │ │ RE-ENGINEER (R) │
   │  Tier: Standard │ │  Tier: Lean  │ │  Tier: High-Rea.│
   │  Gate 1–2       │ │  Gate 0–1    │ │  Gate 2–3       │
   └────────┬────────┘ └──────┬───────┘ └────────┬────────┘
            │                  │                  │
            └──────────────────┼──────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │    GUARDIAN (G)      │
                    │  Regelbasiert (kein  │
                    │  LLM): Ruff/Bandit/  │
                    │  MyPy | Gate 0–1     │
                    └─────────────────────┘
```

> **Hinweis**: Guardian ist kein AI-Agent, sondern ein regelbasiertes Quality Gate
> (Pre-Commit + CI). Es wird als Rolle geführt, weil es in den Workflow integriert
> ist und Merge-Entscheidungen blockieren kann.

### Agenten-Rollen

| Rolle | Tier | Gate | Verantwortung |
|-------|------|------|---------------|
| **Tech Lead** | High-Reasoning | 2–4 | ADR-Parsing, Task-Zerlegung, Code-Review, Eskalation |
| **Developer** | Standard-Coding | 1–2 | Implementierung, Unit-Tests, lokale Commits |
| **Tester** | Lean / Lokal | 0–1 | pytest, Coverage-Analyse, Regressionstests |
| **Re-Engineer** | High-Reasoning | 2–3 | Code-Analyse, Impact-Report, Refactoring |
| **Guardian** | Regelbasiert | 0–1 | Ruff, Bandit, MyPy — blockiert bei Violations |

### Modell-Tiers (konfigurierbar, nicht hardcodiert)

Modellnamen ändern sich häufig. Das ADR definiert **Tiers**, die konkrete Modelle
werden in `agent_team_config.yaml` konfiguriert und können ohne ADR-Änderung
aktualisiert werden.

| Tier | Charakteristik | Typische Vertreter (Stand Feb 2026) |
|------|---------------|--------------------------------------|
| **High-Reasoning** | Extended Thinking, Architektur, Analyse | Claude Opus, o3 |
| **Standard-Coding** | Code-Generierung, Tests, Commits | Claude Sonnet, GPT-4o |
| **Budget-Cloud** | Agentic, SWE-Bench ≥75%, günstig | MiniMax M2.5, GLM-5, Haiku |
| **Lean / Lokal** | Test-Ausführung, Coverage, kein API-Cost | Qwen 2.5 lokal, Phi-4 |
| **Regelbasiert** | Statische Analyse, kein LLM | Ruff, Bandit, MyPy |

> **Hinweis**: Tier-Zuweisung erfolgt dynamisch durch den TaskRouter (ADR-068).
> Die Rollentabelle unten zeigt Default-Tiers — der Router kann abweichen.

> Konkrete Modellnamen und Kosten werden in `agent_team_config.yaml` gepflegt.
> Kostenschätzung (Feb 2026, Hybrid-Szenario): ~$80–110/Monat bei 50 Workflows.

### Gate-System (Erweiterung ADR-014 §3)

| Gate | Name | Beschreibung | Beispiel |
|------|------|-------------|---------|
| 0 | Autonomous | Kein Eingriff nötig | Guardian-Check, Unit-Tests |
| 1 | Notify | Mensch wird informiert, kann eingreifen | Developer-Commit |
| 2 | Approve | Mensch muss explizit freigeben | TL Code-Review |
| 3 | Synchronous | Mensch wartet aktiv auf Ergebnis | Breaking Changes |
| 4 | Human-Only | Nur Mensch darf handeln | Prod-Deploy |

### Kernworkflows

**Workflow A — ADR-basierte Neuentwicklung**

```
ADR → TL.parse_adr() → TaskPlan
    → Developer.implement() → Developer.write_tests()
    → Guardian.check()  [Gate 0: blockiert bei Violations]
    → Tester.validate() [Gate 0–1: meldet Coverage-Unterschreitungen]
    → TL.review()       [Gate 2: Approve | RequestChanges | Escalate]
    → Merge
```

**Workflow B — Test-Verbesserung bestehenden Codes**

```
Code → Tester.analyze_coverage()
     → Developer.write_tests()
     → Guardian.check()
     → Tester.validate()
     → TL.approve() [Gate 2]
```

**Workflow C — Re-Engineering / Refactoring**

```
Code → ReEngineer.analyze() → ImpactReport
     → TL.approve()          [Gate 2: Freigabe erforderlich]
     → ReEngineer.refactor_step() [max. 50 geänderte Zeilen/Schritt]
     → Guardian.check()
     → Tester.regression()
     → TL.review()           [Gate 2: Approve | Rollback]
```

### Fehlerbehandlung und Eskalation

| Situation | Verhalten |
|-----------|-----------|
| Developer erreicht Coverage-Ziel nach 3 Iterationen nicht | Tester eskaliert an TL (Gate 2); TL entscheidet: Ziel anpassen oder Mensch einbeziehen |
| TL kann ADR nicht in Tasks zerteilen (zu vage) | TL eskaliert an Mensch (Gate 3): ADR muss präzisiert werden |
| Guardian blockiert (Critical/Error) | Workflow stoppt; Developer muss Fix liefern vor Fortführung |
| Re-Engineer überschreitet `max_changes_per_step` | Schritt wird abgebrochen; TL zerlegt in kleinere Schritte |
| Workflow-Timeout | Task wird als `failed` markiert; Mensch wird notifiziert (Gate 1) |

### Implementierungsstruktur

```
orchestrator_mcp/
  agent_team/
    __init__.py      # Public API: run_workflow(), get_team_status()
    models.py        # Pydantic v2: AgentRole, Task, TaskPlan, ImpactReport, WorkflowResult
    guardian.py      # G: run_ruff(), run_bandit(), run_mypy(), quality_gate()
    tester.py        # T: run_suite(), analyze_coverage(), regression_test()
    workflows.py     # Workflow-Orchestrierung A, B, C + Fehlerbehandlung
    tech_lead.py     # TL: parse_adr(), assign_tasks(), review_results() [Phase 6]
    developer.py     # D: implement(), write_tests(), commit() [Phase 4]
    re_engineer.py   # R: analyze(), create_impact_report(), refactor_step() [Phase 5]
```

### Konfiguration (`agent_team_config.yaml`)

Siehe `mcp-hub/agent_team_config.yaml` — vollständige Konfiguration mit allen Tiers,
Agents, Workflows und Phasen-Status.

---

## Migration Tracking

| Phase | Inhalt | Definition of Done | Status |
|-------|--------|--------------------|--------|
| 1 | Datenmodell + Pydantic v2 models | `models.py` mit allen Klassen, Tests grün | ✅ done (2026-02-23) |
| 2 | Guardian Agent (Ruff/Bandit/MyPy) | `guardian.py` implementiert, quality_gate() läuft | ✅ done (2026-02-23) |
| 3 | Tester Agent (pytest + Coverage) | `tester.py` implementiert, run_suite() läuft | ✅ done (2026-02-23) |
| 4 | Developer Agent (Code-Generierung) | Workflow B (Test-Verbesserung) End-to-End lauffähig | ⬜ pending |
| 5 | Re-Engineer Agent (Analyse + Refactoring) | Impact-Report für ein bestehendes Modul generiert | ⬜ pending |
| 6 | Tech Lead Agent (ADR-Parsing + Orchestrierung) | Workflow A (ADR-basiert) End-to-End lauffähig | ⬜ pending |
| 7 | Workflow-Integration + End-to-End Tests | Alle 3 Workflows grün, Audit-Log vollständig | ⬜ pending |

---

## Consequences

### Risks

| Risiko | Schwere | Mitigation |
|--------|---------|-----------|
| Multi-Agent-Debugging schwierig | MEDIUM | Detailliertes Audit-Log für jeden Agent-Schritt (AuditStore) |
| API-Kosten (High-Reasoning-Tier) | MEDIUM | Standard-Coding-Tier für Routine; High-Reasoning nur für TL und RE |
| Sequentielle Latenz | LOW | Parallele Tasks wo Abhängigkeiten es erlauben |
| API-Abhängigkeit | MEDIUM | Lean/Lokal-Tier (Ollama) als Fallback für Gate 0–1 |
| Workflow-Deadlock (kein Fortschritt) | LOW | Timeout pro Workflow; Eskalation an Mensch (Gate 1) |

### Confirmation

- Guardian läuft bei jedem Commit (Gate 0) — messbar via CI-Log
- Coverage-Ziele: Tier-1 ≥ 80%, Tier-2 ≥ 60% — gemessen via `pytest-cov`
- Gate-Eskalationen an Mensch (Gate 3+): ≤ 20% aller Tasks — gemessen via Audit-Log
- ADR-Compliance-Rate: 100% — Guardian-Check blockiert bei Violations
- Alle Workflows haben definierten Timeout und Fehlerbehandlung

---

## Deferred Decisions

| Entscheidung | Begründung | Zieldatum | Referenz |
|--------------|------------|-----------|----------|
| API-Key-Management für AI-Agenten | Agenten benötigen eigene API-Keys (Anthropic, OpenAI, MiniMax) — Rotation, Secrets-Handling und Kostentracking noch nicht definiert | 2026-Q2 | ADR-045 (Secrets Management) |
| Ziel-Repo für `orchestrator_mcp/agent_team/` | Liegt `agent_team/` in `mcp-hub` oder `platform`? → mcp-hub gewählt (2026-02-23) | resolved | ADR-044 (MCP-Hub Architecture) |
| Kostenschwelle für High-Reasoning-Tier | Ab welchem monatlichen API-Kostenvolumen wird auf Standard-Tier downgestuft? SLA noch nicht definiert | 2026-Q3 | ADR-067 (Work Management) |
| GitHub Issues Integration für Task-Store | Sollen AI-Tasks als GitHub Issues getrackt werden (ADR-067) oder nur intern im AuditStore? | 2026-Q2 | ADR-067 (Work Management) |

---

## More Information

- ADR-014: AI-Native Development Teams — superseded by this ADR
- ADR-057: Platform Test Strategy — Coverage-Ziele (Tier-1 ≥ 80%, Tier-2 ≥ 60%)
- ADR-058: Platform Test Taxonomy — Test-Typen für Tester-Agent
- ADR-067: Work Management Strategy — GitHub Issues als Task-Store für AI-Agenten
- ADR-044: MCP-Hub Architecture — Ziel-Repo für `orchestrator_mcp/agent_team/`
- ADR-045: Secrets Management — API-Key-Handling für AI-Agenten
- Konzeptbasis: `mcp-hub` Branch `claude/ai-engineering-team-concept-06LJF` (2026-02-22)
- Implementierung: `mcp-hub/orchestrator_mcp/agent_team/` (Phase 1-3, 2026-02-23)

---

## Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-02-22 | Achim Dehnert | Initial — Status: Proposed |
| 2026-02-23 | Achim Dehnert | Review: Pros/Cons-Sektion, More Information, Deferred Decisions ergänzt |
| 2026-02-23 | Achim Dehnert | budget_cloud-Tier ergänzt; Routing-Hinweis auf ADR-068; Fallback-Chain in Config |
| 2026-02-23 | Achim Dehnert | Status: accepted — Phase 1-3 implementiert (models, guardian, tester, workflows) |

---

## Drift-Detector Governance Note

```yaml
paths:
  - orchestrator_mcp/agent_team/
  - orchestrator_mcp/agent_team/models.py
  - agent_team_config.yaml
gate: APPROVE
```
