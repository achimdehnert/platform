---
status: accepted
date: 2026-02-26
implemented: 2026-02-26
decision-makers: Achim Dehnert
consulted: –
informed: –
supersedes: –
amends: –
related: ADR-014, ADR-066, ADR-080, ADR-081, ADR-085
---

# ADR-086: Agent Team Workflow — Cross-Repo Sprint Execution Pattern

| Feld | Wert |
|------|------|
| **Status** | Accepted |
| **Datum** | 2026-02-26 |
| **Autor** | Achim Dehnert |
| **Related** | ADR-014 (AI-Native Teams), ADR-066 (AI Squad), ADR-080 (Multi-Agent), ADR-081 (Guardrails), ADR-085 (Use Case Pipeline) |

---

## 1. Kontext und Problem

ADR-080 definiert das Multi-Agent Coding Team Pattern mit 7 Rollen, Handoff-Protokoll
und TaskGraph. ADR-081 definiert Guardrails und Scope-Lock. ADR-085 definiert die
Use-Case-Pipeline für Task-Zerlegung.

**Problem:** Diese ADRs beschreiben die Architektur, aber nicht den **praktischen
Sprint-Workflow** für den täglichen Einsatz über mehrere Repos hinweg. Es fehlt:

1. **Kein einheitlicher Einstiegspunkt** — jedes Repo hat eigene Konventionen
2. **Kein Performance-Tracking** — keine Sichtbarkeit ob Agents effektiv arbeiten
3. **Kein Verbesserungsmechanismus** — kein Feedback-Loop für Workflow-Optimierung
4. **Keine Drift-Detection** — Workflow kann veralten ohne dass es auffällt

---

## 2. Entscheidung

Wir implementieren ein **dreistufiges Cross-Repo Agent Team Workflow System**:

- **Stufe 1: Conventions** — Issue-Templates, Windsurf Workflows, PR-Templates
- **Stufe 2: Automation** — CI-Gates (Guardian), Branch Protection
- **Stufe 3: Reflexion** — Performance-Log, Sprint-Retro, Drift-Detection

### 2.1 Repos im Scope

| Repo | Domäne |
|------|--------|
| 137-hub | Community/Book Platform |
| bfagent | Agent Management |
| travel-beat | Travel Stories |
| weltenhub | Story Universes |
| pptx-hub | Presentations |
| risk-hub | Occupational Safety |
| mcp-hub | MCP Server Collection |

---

## 3. Architektur

### 3.1 Dateien pro Repo

```
<repo>/
  .windsurf/workflows/
    agent-task.md           # Agent-Anleitung: wie Task ausführen
  .github/
    ISSUE_TEMPLATE/
      agent-task.yml        # Standardisiertes Task-Format
    PULL_REQUEST_TEMPLATE/
      agent-pr.md           # PR-Checkliste für Agent-PRs
  docs/
    AGENT_HANDOVER.md       # Repo-Kontext für neue Agents
```

### 3.2 Zentrale Dateien (platform Repo)

```
platform/
  docs/adr/
    ADR-086-agent-team-workflow.md    # Dieses ADR (Source of Truth)
  docs/agent-team/
    performance-log.md                # Zentrales Performance-Tracking
    retro/
      sprint-NNN.md                   # Sprint-Retrospektiven
```

### 3.3 Sprint-Workflow

```
┌─────────────────────────────────────────────────────────┐
│  SPRINT PLANNING                                        │
│  1. Parent-Issues in Sub-Tasks zerlegen                 │
│  2. Sub-Tasks als GitHub Issues mit agent-task Template  │
│  3. Sprint-Retro Issue anlegen (Pflicht)                │
├─────────────────────────────────────────────────────────┤
│  TASK EXECUTION (pro Sub-Task)                           │
│  1. Builder Agent: liest Issue + agent-task.md Workflow  │
│  2. Builder Agent: implementiert auf Feature-Branch      │
│  3. Builder Agent: erstellt PR mit agent-pr.md Template  │
│  4. Guardian (CI): Ruff + Tests automatisch              │
│  5. Review Agent: semantischer Code-Review               │
│  6. QA Agent: zusätzliche Tests wenn nötig               │
│  7. Merge nach Approval                                  │
│  8. Performance-Log Eintrag schreiben                    │
├─────────────────────────────────────────────────────────┤
│  SPRINT RETRO (Pflicht-Task am Sprint-Ende)              │
│  1. Tech Lead Agent: liest Performance-Log               │
│  2. Vergleicht IST vs SOLL (ADR-086 Ziele)              │
│  3. Schreibt Sprint-Retro (platform/docs/retro/)        │
│  4. Schlägt Workflow-Änderungen vor                      │
│  5. Aktualisiert last_reviewed in allen Repos            │
└─────────────────────────────────────────────────────────┘
```

---

## 4. Agent-Rollen im Sprint

| Rolle | ADR-Ref | Aufgabe im Sprint | Wann |
|-------|---------|-------------------|------|
| **Planner** | ADR-080 | Parent-Issue → Sub-Tasks zerlegen | Sprint-Start |
| **Builder (Developer)** | ADR-066 | Code implementieren | Pro Task |
| **Tester** | ADR-066 | Tests schreiben + ausführen | Parallel zum Builder |
| **Guardian** | ADR-081 | Ruff + Bandit + Tests (CI) | Automatisch bei PR |
| **Tech Lead** | ADR-066 | Semantischer Code-Review | Nach Guardian |
| **Merger** | ADR-080 | PR mergen nach Approval | Nach Review |
| **Tech Lead** | ADR-066 | Sprint-Retro + Workflow-Review | Sprint-Ende |

---

## 5. Issue-Format (agent-task Template)

Jedes Agent-Task-Issue MUSS enthalten:

```yaml
task_type: feature | bugfix | refactor | test | infra
complexity: trivial | simple | moderate | complex
parent_issue: "#NNN"
affected_paths:
  - src/apps/MODULE/...
forbidden_paths:
  - "*/migrations/*.py"
  - config/settings/prod*.py
acceptance_criteria:
  - "Criterion 1"
  - "Criterion 2"
test_requirements:
  - "Test 1"
  - "Test 2"
dependencies: []  # andere Sub-Task Issues die erst fertig sein müssen
```

---

## 6. Performance-Metriken

Pro Task werden folgende Metriken erfasst:

| Metrik | Beschreibung | Ziel |
|--------|-------------|------|
| **Durchlaufzeit** | Issue erstellt → PR merged | < 30 Min (simple), < 2h (complex) |
| **Review-Rounds** | Wie oft PR zurückgewiesen | ≤ 1 |
| **Test-Coverage-Delta** | Änderung der Coverage | ≥ 0% |
| **Regressions** | Bestehende Tests gebrochen | 0 |
| **Lines Changed** | Netto Diff-Zeilen | Tracking |
| **Guardian-Pass** | CI beim ersten Mal grün | > 80% |

### Aggregierte Sprint-Metriken

| Metrik | Beschreibung |
|--------|-------------|
| **Velocity** | Tasks completed / Sprint |
| **First-Pass-Rate** | % Tasks die beim ersten Review durchkommen |
| **Regression-Rate** | % Sprints mit Regressions |
| **Workflow-Compliance** | % Tasks die dem Template folgen |

---

## 7. Drift-Detection und Selbstverbesserung

### 7.1 Workflow-Versionierung

Jedes `.windsurf/workflows/agent-task.md` enthält:

```yaml
---
description: Agent Task Workflow
source_adr: ADR-086
last_reviewed: 2026-02-26
review_interval_days: 30
version: "1.0"
---
```

**Regel:** Wenn `last_reviewed + review_interval_days < today`, MUSS der Agent
vor Task-Ausführung ADR-086 auf Updates prüfen und `last_reviewed` aktualisieren.

### 7.2 Retro-Pflicht

Jeder Sprint enthält ein **Retro-Issue** als letzten Task. Dieses Issue:
- Wird beim Sprint-Planning automatisch mit angelegt
- Kann nicht geschlossen werden ohne Retro-Datei in `platform/docs/agent-team/retro/`
- Enthält konkrete Prozessänderungen die im nächsten Sprint umgesetzt werden

### 7.3 Verbesserungspfad

```
Sprint-Retro
    │
    ├─ Kleine Änderung → Workflow-File Update (agent-task.md)
    │
    ├─ Mittlere Änderung → ADR-086 Amendment
    │
    └─ Große Änderung → Neues ADR (z.B. ADR-087)
```

---

## 8. Enforcement

| Mechanismus | Typ | Umgehbar? |
|-------------|-----|----------|
| **CI-Gate** (Ruff + Tests) | Technisch | Nein (Branch Protection) |
| **PR-Template Checkliste** | Konvention | Ja (aber sichtbar) |
| **Issue-Template Pflichtfelder** | Konvention | Ja (aber standardisiert) |
| **Sprint-Retro Issue** | Prozess | Ja (aber wird beim Planning angelegt) |
| **Drift-Detection** | Konvention | Ja (aber Agent prüft bei Session-Start) |

**Kernprinzip:** Technische Gates wo möglich, Konventionen wo nötig,
Sichtbarkeit überall.

---

## 9. Migration bestehender Repos

Reihenfolge für Rollout:

| Phase | Repo | Status |
|-------|------|--------|
| 1 | 137-hub | Pilot (Sprint 4) |
| 2 | bfagent | Nach Sprint 4 Retro |
| 3 | travel-beat, weltenhub | Parallel |
| 4 | risk-hub, pptx-hub, mcp-hub | Bei Bedarf |

Pro Repo:
1. `.windsurf/workflows/agent-task.md` kopieren
2. `.github/ISSUE_TEMPLATE/agent-task.yml` kopieren
3. `.github/PULL_REQUEST_TEMPLATE/agent-pr.md` kopieren
4. `docs/AGENT_HANDOVER.md` erstellen/aktualisieren
5. Branch Protection auf `main` aktivieren

---

## 10. Konsequenzen

### Positiv
- **Einheitlich**: Jedes Repo hat denselben Workflow-Einstiegspunkt
- **Messbar**: Performance-Log macht Agent-Effektivität sichtbar
- **Selbstverbessernd**: Pflicht-Retro + Drift-Detection
- **Leichtgewichtig**: Kein Infrastructure-Overhead, nur Dateien + CI

### Negativ / Risiken

| Risiko | Mitigation |
|--------|------------|
| Workflow-Konventionen werden ignoriert | CI-Gate ist technisch, Rest ist sichtbar |
| Retro wird pro-forma ausgefüllt | Performance-Metriken machen Qualität objektiv messbar |
| Overhead bei kleinen Tasks | Trivial-Tasks bypassen Review (nur CI-Gate) |

---

## 11. Changelog

| Datum | Autor | Änderung |
|-------|-------|---------|
| 2026-02-26 | Achim Dehnert | v1 — Initial: Cross-Repo Sprint Pattern |
