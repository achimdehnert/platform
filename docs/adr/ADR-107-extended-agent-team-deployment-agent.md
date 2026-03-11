---
status: accepted
date: 2026-03-08
decision-makers: Achim Dehnert
consulted: Cascade (Tech Lead)
informed: –
supersedes: –
amends: ADR-066-ai-engineering-team.md, ADR-080-multi-agent-coding-team-pattern.md
related: ADR-066, ADR-068, ADR-075, ADR-080, ADR-081, ADR-086
implementation_status: implemented
implementation_evidence:
  - "mcp-hub/orchestrator_mcp/: deployment agent active"
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

**Deployment-Schritte (vollständig):**
```
Step 0: Aktuellen Image-Tag sichern (für deterministischen Rollback)
Step 1: Neues Image pullen (GHCR)
Step 2: Pending Migrations prüfen (migrate --check)
Step 2a: Breaking-Change-Analyse via breaking_change_detector (PFLICHT)
         → sqlmigrate SQL parsen → Gate-2-Approval wenn breaking
Step 3: Migration ausführen (timeout 300s, --noinput)
Step 4: Container recreaten (--no-deps --force-recreate)
Step 5: Health-Check (HTTP 200 auf /health/, 3 Versuche)
Step 6: Bei Fehler: Tier-Rollback (siehe unten)
Step 7: AuditStore: DeploymentLog schreiben
```

**Breaking-Change-Erkennung (breaking_change_detector.py):**
`migrate --check` erkennt NUR ob Migrations pending sind — nicht ob sie
destructive sind. Die Breaking-Change-Analyse via `sqlmigrate` SQL-Parsing
ist Pflichtschritt vor jedem Deployment mit Migrations.

```python
analyses = analyse_all_pending_migrations()
gate_level, auto_eligible, reason = get_deployment_gate_level(analyses)
if not auto_eligible:
    # Gate-2-Approval erforderlich (Breaking Change oder unklassifiziertes SQL)
    trigger_gate2_approval(reason)
```

**Drei-Tier-Rollback-Strategie:**

| Tier | Bedingung | Aktion |
|------|-----------|--------|
| **Tier 1** | Migration noch nicht angewendet | Image-Tag revert + Container recreate |
| **Tier 2** | Migration angewendet, kein destructive Change | Image-Tag revert (Schema bleibt, neues Image kompatibel) |
| **Tier 3** | Destructive Migration bereits angewendet | **Cascade (Tech Lead) alarmieren — KEIN Auto-Rollback** |

Tier-3-Eskalation: `RollbackPolicy.requires_tech_lead(migration_is_destructive=True, migration_was_applied=True)` → `True`

**Tools (orchestrator_mcp):**
- `deploy` — docker compose Steuerung
- `shell_exec` — SSH-Kommandos (Allowlist: docker, python, cat, tail, timeout, curl, grep)
- `github_pr` — Deployment-Status auf PR kommentieren

**Gate-Level**: Gate 2
- `auto_eligible=True`: wenn CI grün + kein Breaking Change → automatisch
- `auto_eligible=False`: Breaking Changes / unklassifiziertes SQL → Gate-2-Approval

**Rollback-Trigger:**
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

**Override-Mechanismus**: Label `agent-review-override` oder Kommentar
`/override-review <reason>` — Override-Event wird in `ReviewLog` persistiert.

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
    |   +- auto_eligible=True (kein Schema-Change) --> Deployment Agent (Gate 2, autonom)
    |   +- auto_eligible=False (Breaking Change)   --> Gate 2: Cascade Approval
    |
    +- Typ: PR Review
    |   --> Review Agent (Gate 1)
    |
    +- Typ: Refactor / Tech Debt
        --> Re-Engineer --> Tech Lead Approval (Gate 2)
```

---

## 5. Implementierung

### Phase 1 — Deployment Agent (abgeschlossen)

- [x] `agent_team_config.yaml` um `deployment_agent` Rolle erweitert
- [x] `orchestrator_mcp/agent_team/roles.py` — `DeploymentAgentConfig`, `AgentRoleProtocol`
- [x] `orchestrator_mcp/agent_team/breaking_change_detector.py` — SQL-Analyse
- [x] `orchestrator_mcp/models/deployment_log.py` — AuditStore Model
- [x] `orchestrator_mcp/migrations/0001_deployment_log_review_log.py` — Idempotente Migration
- [x] `.github/workflows/cd.yml` — Deployment Agent Workflow (alle Fixes aus REVIEW-ADR-107)
- [x] `/deploy` Windsurf-Workflow auf Agent-Routing umgestellt

### Phase 2 — Review Agent (abgeschlossen)

- [x] `agent_team_config.yaml` um `review_agent` Rolle erweitert
- [x] `orchestrator_mcp/agent_team/roles.py` — `ReviewAgentConfig`
- [x] `orchestrator_mcp/models/review_log.py` — AuditStore + Override-Trail
- [x] Neuen Windsurf-Workflow `/agent-review` erstellt

### Phase 3 — Workflow-Dokumentation (abgeschlossen)

- [x] `/agentic-coding` Workflow: Cascade-als-Tech-Lead dokumentiert
- [x] `/deploy` Workflow: Deployment Agent als primäre Ausführungsrolle
- [x] `/agent-review` Workflow: Review Agent als erste Prüfstufe

### Phase 4 — orchestrator_mcp Integration (ausstehend)

- [ ] `agent_team_status` Tool: neue Rollen anzeigen
- [ ] `agent_plan_task` Tool: Deployment-Tasks korrekt routen
- [ ] PR #20 mergen → `orchestrator_mcp` deployen

---

## 6. Konsequenzen

### Positiv
- Cascade fokussiert auf Architektur und Konzepte — höhere Qualität der Entscheidungen
- Deployments laufen vollständig automatisiert ohne manuelle SSH-Intervention
- PR-Reviews sind konsistent und ADR-compliant
- Breaking-Change-Erkennung via SQL-Analyse verhindert ungewollte Datenverluste
- Drei-Tier-Rollback schützt vor unkontrolliertem Rollback bei destructiven Migrations

### Negativ / Risiken
- Deployment Agent benötigt SSH-Key als GitHub Secret (umgesetzt: `DEPLOY_SSH_PRIVATE_KEY`)
- Review Agent kann False Positives produzieren — Override-Mechanismus vorhanden
- Initiale Setup-Kosten für `orchestrator_mcp`-Erweiterung (Phase 4)

### Neutrale Änderungen
- `agent_team_config.yaml` Schema-Version 2.0 — Breaking Change gegenüber 1.x
- `get_deployment_gate_level()` gibt jetzt `(int, bool, str)` zurück — API-Change

---

## 7. Compliance

| ADR | Bezug |
|-----|-------|
| ADR-014 | "AI führt aus, Mensch entscheidet" — jetzt rollenspezifisch umgesetzt |
| ADR-066 | Squad-Erweiterung: +2 neue Rollen (Deployment, Review) |
| ADR-075 | Deployment-Execution: jetzt als dedizierter Agent |
| ADR-080 | Handoff-Protokoll: Deployment Agent als letzter Handoff-Empfänger |
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
- Review: `docs/adr/reviews/REVIEW-ADR-107-extended-agent-team.md`
- Implementation: PR #20 `feat/adr-107-blocker-fixes`

---

## 9. Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-03-08 | Achim Dehnert | Initial — korrigiert von fehlerhafter Nummer ADR-100 |
| 2026-03-08 | Cascade | §4.3 Tier-Rollback + breaking_change_detector als Pflichtschritt; §5 Phase-Status auf Stand gebracht (PR #20) |
