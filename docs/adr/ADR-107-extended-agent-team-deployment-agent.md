---
status: accepted
date: 2026-03-08
decision-makers: Achim Dehnert
consulted: Cascade (Tech Lead)
informed: –
supersedes: –
amends: ADR-066-ai-engineering-team.md, ADR-080-multi-agent-coding-team-pattern.md
related: ADR-066, ADR-068, ADR-075, ADR-080, ADR-081, ADR-086
---

# ADR-107: Erweitertes Agent-Team — Cascade als Tech Lead, Deployment Agent, Review Agent und explizite Rollenentlastung

| Feld | Wert |
|------|------|
| **Status** | Accepted |
| **Datum** | 2026-03-08 |
| **Autor** | Achim Dehnert |
| **Amends** | ADR-066 (AI Engineering Squad), ADR-080 (Multi-Agent Pattern) |
| **Related** | ADR-068 (Adaptive Model Routing), ADR-075 (Deployment Execution), ADR-081 (Agent Guardrails), ADR-086 (Agent Team Workflow) |

---

## 1. Kontext und Problem

ADR-066 und ADR-080 definieren ein funktionierendes AI Engineering Squad. In der
täglichen Praxis zeigt sich jedoch eine strukturelle Schwäche:

**Cascade wird für alles eingesetzt** — von trivialen Template-Fixes bis zu
Architektur-Entscheidungen. Das ist ineffizient und verschwendet Kapazität für
hochwertige Aufgaben.

### Konkrete Lücken (Stand 2026-03-08)

**Lücke 1: Kein dedizierter Deployment Agent**
ADR-075 beschreibt Deployment-Execution, aber kein Agent ist explizit für
SSH, Docker, Migrationen und Health-Checks zuständig. Cascade führt Deployments
manuell durch, obwohl diese vollständig automatisierbar sind.

**Lücke 2: Cascade ist nicht klar als Tech Lead positioniert**
In der Praxis übernimmt Cascade alle Rollen gleichzeitig: Feature-Developer,
Tester, Deployer, Reviewer. Das Prinzip "AI führt aus, Mensch entscheidet"
(ADR-014) wird nicht ausgeschöpft — der Mensch entscheidet bei zu vielen
trivialen Aktionen.

**Lücke 3: Kein Review Agent**
PR-Reviews gegen Platform-Konventionen (ADRs, Ruff, Bandit) werden ad-hoc
durchgeführt. Ein dedizierter Review Agent könnte das systematisch übernehmen.

**Lücke 4: Fehlende Rollenentlastung**
Das Ziel ist: Cascade konzentriert sich auf **Konzepte, Reviews, Architektur**.
Das Agent-Team führt aus. Dieser Grundsatz ist in keinem ADR operationalisiert.

---

## 2. Decision Drivers

- **Kapazitätseffizienz**: Cascade für hochwertige Aufgaben reservieren
- **Vollständige Automatisierung**: Deployment-Pipeline ohne manuelle SSH-Schritte
- **Klarheit**: Jede Aufgabe hat genau eine verantwortliche Rolle
- **Skalierbarkeit**: Neue Hubs können ohne Cascade-Involvement deployed werden
- **Gate-Konsistenz**: Alle Deployments durchlaufen denselben Gate-2-Prozess

---

## 3. Considered Options

### Option A — Status quo beibehalten (abgelehnt)
Cascade bleibt Generalist. Kein dedizierter Deployment Agent.
**Contra**: Verschwendet Cascade-Kapazität, keine Skalierung.

### Option B — Nur Deployment Agent hinzufügen (abgelehnt)
Deployment Agent ohne explizite Cascade-Rolle als Tech Lead.
**Contra**: Löst Lücke 1, aber nicht die anderen drei.

### Option C — Vollständige Rollenerweiterung (gewählt)
Cascade als expliziter Tech Lead, neuer Deployment Agent, neuer Review Agent,
klare Aufgabentrennung per Workflow.
**Pro**: Löst alle vier Lücken, nutzt bestehende orchestrator_mcp-Infrastruktur.

---

## 4. Decision

### 4.1 Rollen-Matrix (erweitert)

| Rolle | Agent | Gate | Aufgaben |
|-------|-------|------|----------|
| **Tech Lead / Architect** | Cascade | 2–3 | ADRs, Konzepte, Reviews, Architektur-Entscheidungen, komplexe Feature-Planung |
| **Developer** | AI Agent | 1 | Feature-Code, Bugfixes, Refactoring (nach Plan von Tech Lead) |
| **Tester** | AI Agent | 0 | Tests schreiben, Coverage, CI-Fehler analysieren |
| **Deployment Agent** | AI Agent | 2 | SSH, Docker, Migrationen, Health-Checks, Rollback |
| **Review Agent** | AI Agent | 1 | PR-Reviews gegen ADRs, Ruff, Bandit, Platform-Patterns |
| **Re-Engineer** | AI Agent | 2 | Refactoring nach Guardian-Fail, Tech Debt |
| **Guardian** | Regelbasiert | 0 | Ruff, Bandit, MyPy, ADR-Compliance (automatisch) |

### 4.2 Cascade als Tech Lead — Operative Definition

Cascade übernimmt **ausschließlich** folgende Aufgaben direkt:

1. **ADR schreiben und reviewen** — alle Architektur-Entscheidungen
2. **Konzepte entwickeln** — Feature-Konzepte, Migrations-Strategien, API-Designs
3. **Task-Planung** — `agent_plan_task` für `complexity >= complex`
4. **Agent-Koordination** — Handoff-Dokumente, Acceptance Criteria definieren
5. **Blocking-Issues** — wenn Agent-Team-Rollback Level 3 erreicht
6. **Finale PR-Freigabe** — Gate-2-Approval für Features und Deployments

Cascade übernimmt **nicht** direkt:
- Routine-Feature-Code (→ Developer Agent)
- Test-Schreiben (→ Tester Agent)
- SSH/Docker-Kommandos (→ Deployment Agent)
- PR-Reviews gegen Lint-Regeln (→ Review Agent)

### 4.3 Deployment Agent — Spezifikation

**Trigger**: Jeder `git push` auf `main` nach erfolgreichem CI.

**Verantwortlichkeiten:**
```
1. Image pullen (GHCR)
2. Migration dry-run prüfen (--check)
3. Migration ausführen (--noinput)
4. Container recreaten (--no-deps --force-recreate)
5. Health-Check (HTTP 200 auf /health/)
6. Bei Fehler: Rollback auf previous image tag
7. AuditStore: deployment_log schreiben
```

**Tools (orchestrator_mcp):**
- `deploy` — docker compose Steuerung
- `shell_exec` — SSH-Kommandos (Allowlist: docker, python, cat, tail)
- `github_pr` — Deployment-Status auf PR kommentieren

**Gate-Level**: Gate 2
- Automatisch: wenn CI grün + kein DB-Schema-Breaking-Change
- Gate-2-Approval: bei neuen Migrations, Breaking Changes, Prod-Only-Fixes

**Rollback-Kriterien:**
- Health-Check schlägt nach 3 Versuchen fehl
- Migration-Fehler (exit code != 0)
- Container startet nicht innerhalb von 60s

### 4.4 Review Agent — Spezifikation

**Trigger**: Neuer PR gegen `main`.

**Prüfkriterien (in Reihenfolge):**
1. Ruff + Bandit clean (Gate 0 — blockiert)
2. ADR-Compliance via `mcp12_check_violations` (Gate 1 — blockiert)
3. Platform-Patterns: keine Inline-CSS in Python, kein hardcoded SQL (Gate 1)
4. Test-Coverage-Delta >= 0 (Warnung, kein Block)
5. Migrations ohne `RunPython` ohne Reverse (Warnung)

**Output**: Automatischer PR-Kommentar mit strukturiertem Review-Report.

### 4.5 Aufgaben-Routing-Entscheidungsbaum

```
Eingehende Aufgabe
    |
    +- Typ: ADR / Konzept / Architektur
    |   --> Cascade (Tech Lead)
    |
    +- Typ: Feature / Bugfix
    |   +- complexity >= complex --> Cascade plant --> Developer fuehrt aus
    |   +- complexity < complex  --> Developer direkt (Gate 1)
    |
    +- Typ: Test
    |   --> Tester Agent (Gate 0, autonom)
    |
    +- Typ: Deployment
    |   +- Routine (kein Schema-Change) --> Deployment Agent (Gate 2, autonom)
    |   +- Breaking Change --> Gate 2: Cascade Approval
    |
    +- Typ: PR Review
    |   --> Review Agent (Gate 1)
    |
    +- Typ: Refactor / Tech Debt
        --> Re-Engineer --> Tech Lead Approval (Gate 2)
```

---

## 5. Implementierung

### Phase 1 — Deployment Agent (sofort)

- [x] `agent_team_config.yaml` um `deployment_agent` Rolle erweitert
- [ ] `orchestrator_mcp/agent_team/roles.py` — neue Rolle `DeploymentAgent`
- [x] CD-Workflow (`.github/workflows/cd.yml`) als Deployment Agent konfiguriert
- [x] `/deploy` Windsurf-Workflow auf Agent-Routing umgestellt

### Phase 2 — Review Agent (kurzfristig)

- [x] `agent_team_config.yaml` um `review_agent` Rolle erweitert
- [ ] `orchestrator_mcp/agent_team/roles.py` — neue Rolle `ReviewAgent`
- [x] Neuen Windsurf-Workflow `/agent-review` erstellt

### Phase 3 — Workflow-Dokumentation (erledigt)

- [x] `/agentic-coding` Workflow: Cascade-als-Tech-Lead dokumentiert
- [x] `/deploy` Workflow: Deployment Agent als primäre Ausführungsrolle
- [x] `/agent-review` Workflow: Review Agent als erste Prüfstufe

### Phase 4 — orchestrator_mcp Erweiterung (mittelfristig)

- [ ] `agent_team_status` Tool: neue Rollen anzeigen
- [ ] `agent_plan_task` Tool: Deployment-Tasks korrekt routen
- [ ] AuditStore: Deployment-Log-Einträge

---

## 6. Konsequenzen

### Positiv
- Cascade fokussiert auf Architektur und Konzepte
- Deployments laufen vollständig automatisiert
- PR-Reviews sind konsistent und ADR-compliant
- Klare Verantwortlichkeiten reduzieren Fehlerquellen

### Negativ / Risiken
- Deployment Agent benoetigt SSH-Key als GitHub Secret (umgesetzt: `SSH_PRIVATE_KEY`)
- Review Agent kann False Positives produzieren
- Initiale Setup-Kosten fuer `orchestrator_mcp`-Erweiterung

### Neutrale Aenderungen
- `agent_team_config.yaml` muss in allen Repos aktualisiert werden
- Bestehende Workflows erhalten Breaking Changes — Versionierung noetig

---

## 7. Compliance

| ADR | Bezug |
|-----|-------|
| ADR-014 | "AI fuehrt aus, Mensch entscheidet" — jetzt rollenspezifisch umgesetzt |
| ADR-066 | Squad-Erweiterung: +2 neue Rollen (Deployment, Review) |
| ADR-075 | Deployment-Execution: jetzt als dedizierter Agent |
| ADR-080 | Handoff-Protokoll: Deployment Agent als letzter Handoff-Empfaenger |
| ADR-081 | Guardrails: Deployment Agent hat engste Shell-Allowlist aller Agenten |

---

## 8. Referenzen

- ADR-014: AI-Native Development Teams
- ADR-066: AI Engineering Squad — Rollen, Gates, Workflows
- ADR-068: Adaptive Model Routing
- ADR-075: Deployment Execution Strategy
- ADR-080: Multi-Agent Coding Team Pattern
- ADR-081: Agent Guardrails & Code Safety
- ADR-086: Agent Team Workflow
- Windsurf Workflows: `/deploy`, `/agentic-coding`, `/agent-review`

---

## 9. Changelog

| Datum | Autor | Aenderung |
|-------|-------|-----------|
| 2026-03-08 | Achim Dehnert | Initial — korrigiert von faelschlicher Nummer ADR-100 |
