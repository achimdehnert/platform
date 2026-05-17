---
description: Fully Agentic Coding — Task definieren, planen, routen, ausführen, bewerten (v6)
mode: write
---

# Agentic Coding Workflow v6

Operationalisiert ADR-066 + ADR-068 + ADR-080 + ADR-107 + ADR-108 + ADR-154 + ADR-173 + ADR-174.
**v6**: Auto-Dispatch Router + Cost-Aware Auto-Downgrade Ladder.
**v5**: Task-Type-granulares LLM-Routing + Auto-Issue-Creation + `get_full_context` + `run_workflow` Alternative. Repo-aware Guardian.

> ⚠️ MCP-Prefixes sind environment-spezifisch — Prefix aus `project-facts.md` oder
> `.windsurf/rules/mcp-tools.md` lesen. `<orc>` = Orchestrator-Prefix, `<ctx>` = Platform-Context-Prefix,
> `<gh>` = GitHub-MCP-Prefix.
>
> **task_id** = GitHub Issue-Nummer des aktuellen Tasks (aus dem Issue-Link). Dieser Wert wird
> in Steps 2, 5, 6, 8 als Audit-Referenz verwendet.

---

## Auto-Dispatch Router (Entry Point)

**Immer zuerst aufrufen** — wählt automatisch den richtigen Pfad:

```
MCP: <orc>_analyze_task(description)
→ liefert: {task_type, complexity, gate_level, recommended_model}
```

**Routing-Entscheidung:**

| Bedingung | Pfad | Begründung |
|-----------|------|------------|
| `gate_level <= 1` AND `complexity in {trivial, simple}` | **Pfad A** (Fully-Autonomous) | Agent-Team reicht |
| `gate_level == 2` OR `complexity == moderate` | **Pfad B** (Semi-Agentic) | Cascade als Tech Lead nötig |
| `gate_level >= 3` | **Pfad C** (Human-First) | `<orc>_request_approval(gate=gate_level)` — warten |
| `complexity == architectural` | **Pfad B** + `model=opus` erzwingen | ADRs brauchen Design-Review |

Bei Unsicherheit → **Pfad B** (konservativer). Nie Pfad A für `infra`/`deployment`/`breaking_change`.

---

## Übersicht: Zwei Pfade

### Pfad A — Fully-Autonomous (Gate 0-1 Tasks, einfach/simpel)

Für `trivial`/`simple` Tasks — der Orchestrator führt selbstständig aus:

```
<orc>_run_workflow(
    task_description, task_type, complexity,
    affected_paths, acceptance_criteria
)
→ Developer+Guardian+Tester Team läuft autonom mit bis zu 3 Retry-Iterationen
→ Keine Cascade-Beteiligung nötig, Audit im AuditStore
```

Alternativ für einzelne Sub-Tasks: `<orc>_delegate_subtask(...)`.

### Pfad B — Semi-Agentic (moderate+, Cascade als Tech Lead)

Für `moderate`+ Tasks — Cascade koordiniert, Agent-Team unterstützt:

```
Phase 0: Contract Verification    → PCV-Checkliste          (moderate+ | trivial: nur D)
Step 0:  Context + Governance     → <orc>_get_full_context + <ctx>_get_banned_patterns
Step 1:  Task analysieren + plan  → <orc>_analyze_task + agent_plan_task
Step 2:  Model-Routing + Budget   → <orc>_get_cost_estimate  (complex+)
Step 3:  Implementieren           → Developer (Gate 1)
Step 3.5 Proactive Tasks          → CHANGELOG, ADR-Impact, Auto-Issues
Step 4:  Guardian-Check           → repo-aware Lint + Security + Tests (Gate 0)
Step 5:  Self-Review              → Kriterien-Checkliste + log_action
Step 6:  QA Gate                  → check_gate / request_approval (Gate 0-4)
Step 7:  Commit + PR
Step 8:  AuditStore + Issue-Update
```

Bei Fail in Step 5/6 → Rollback-Pfad beachten (Ende dieses Dokuments).

---

## Phase 0: Contract Verification — PCV

> **Wann:** Immer bei `moderate`+. Bei `trivial` (docu, README, CHANGELOG): nur Schritt D (Dependency-Scan).
> **Zweck:** Verhindert Review-Iterationen durch proaktive Verifikation aller Annahmen.
> ~10 Tool-Calls, spart 2–3 Review-Zyklen à 8k Token. ROI: 10:1.

### A) Pattern-Scan — Repo-spezifische Typen verifizieren

```bash
# Wie definiert DIESES Repo tenant_id, public_id, FK-Typen?
grep -r "tenant_id" src/ --include="models.py" | head -5
grep -r "public_id" src/ --include="models.py" | head -5
```

→ Ergebnis als **Constraint Manifest** notieren: `tenant_id = UUIDField` o.ä.

### B) Call-Scan — Externe Funktionssignaturen verifizieren

Für jede externe Funktion die aufgerufen wird:

```bash
# Signatur lesen — nie aus dem Gedächtnis annehmen
grep -n "^def " <package>/services.py
# Oder: read_file(<package_path>)
```

Besonders: `aifw.sync_completion` (public API), `audit.services.*`, alle iil-* Packages.

### C) Infra-Scan — Constraints prüfen

```bash
# Nginx Upload-Limit
grep "client_max_body" docker/nginx/*.conf

# Storage-Backend (S3 oder lokal?)
grep -E "STORAGES|DEFAULT_FILE_STORAGE|S3_ENDPOINT" src/config/settings.py

# Migrations-Stand für betroffene Apps
python -m django showmigrations <app>
```

### D) Dependency-Scan

```bash
# Alle benötigten Packages vorhanden?
grep -E "<package1>|<package2>" requirements.txt
```

### E) Assumption Register aufstellen

Jede nicht-verifiable Annahme inline markieren:

```python
# ASSUMPTION[verified]: tenant_id = UUIDField (grep: 3/3 models)
# ASSUMPTION[unverified]: audit.services.log(actor_id, ...) — vor Merge prüfen
```

**Output: Constraint Manifest** → steuert Step 3.

---

## Step 0: Context + Governance Check (complexity >= moderate)

**1 Call ersetzt 4 greps aus Phase 0 A-D** (R-04, ADR-154):

```
MCP: <orc>_get_full_context(task_description, repo, top_k=5)
→ kombiniert: pgvector-Memories + Repo-Facts + Session-Deltas + Architektur-Regeln + ADR-Referenzen
```

Zusätzlich für repo-spezifische Regeln:

```
MCP: <ctx>_get_banned_patterns(context=<file_type>)
→ verbotene Patterns für diesen Datei-Typ

MCP: <ctx>_check_violations(code_snippet="<vorhandener ähnlicher Code>")
→ Optional: bestehenden verwandten Code auf Violations scannen (BEVOR du ihn erweiterst)
→ Neuen Code prüfen: → Step 5 (Self-Review)
```

Optional bei Session-Übernahme:

```
MCP: <orc>_get_session_delta()
→ Was hat sich seit letzter Session geändert? (offene Tasks, neue Entscheidungen)
```

**Blockiert bei ADR-Verletzung.** Kein Weiter ohne grünen Check.

---

## Step 1: Task analysieren + planen

```
MCP: <orc>_analyze_task(description)
→ liefert: task_type, complexity, recommended_role, gate_level, model_recommendation

MCP: <orc>_agent_plan_task(description, task_type, complexity)
→ liefert: branches[], estimated_steps, assigned_role, gate_level
```

Rollen-Zuweisung nach Gate (kompatibel mit `agent_plan_task` Enum):

| Task-Typ | Rolle | Gate |
|----------|-------|------|
| `test` | Tester | Gate 0 (autonom) |
| `docs` | Developer | Gate 1 (notify) |
| `feature` | Developer | Gate 1-2 |
| `bugfix` | Developer | Gate 1-2 |
| `refactor` | Re-Engineer | Gate 2 (approve) |
| `infra` / `deployment` | Deployment Agent | Gate 3 (synchronous) |
| `architecture` (intern — per ADR-066 → Tech Lead) | Tech Lead | Gate 2 |
| `breaking_change` / `production_data` / `delete` | Human Only | Gate 4 |

> **Hinweis:** `agent_plan_task` akzeptiert nur `feature|bugfix|refactor|test|docs|infra`.
> Architektur-Tasks → als `refactor` planen mit `complexity=architectural` (triggert opus-Modell).

Gate 2+ → User um Approval bitten (Chat), bevor weitergemacht wird.
Gate 3+ → `<orc>_request_approval(gate=3)` mit Begründung.

---

## Step 2: Model-Routing + Budget (empfohlen bei complex+)

**Task-Type-granulares Routing** (SSoT: `orchestrator_mcp/config.py:MODEL_SELECTION`):

| Task-Typ | Default-Modell | Kosten/1k | Beispiele |
|----------|---------------|-----------|-----------|
| `typo` / `lint` / `docs` / `test` | `gpt_low` | ~$0.001 | Typo-Fix, docu-update, Tests schreiben |
| `feature` / `bug` / `refactor` | `swe` | ~$0.003 | Features, Bugfixes, Refactoring |
| `architecture` / `security` / `breaking_change` | `opus` | ~$0.015 | ADRs, Security-Review, API-Breaking |

**Complexity überschreibt Default:**
- `complexity=architectural` → immer `opus` (egal welcher task_type)
- `complexity=trivial` + `task_type=feature` → kann auf `gpt_low` heruntergestuft werden

```
MCP: <orc>_get_cost_estimate(task_id, model=<empfohlen aus analyze_task>, estimated_tokens)
→ liefert: cost_usd, budget_status (ok/over), token_budget
```

### Cost-Aware Auto-Downgrade Ladder

Statt bei `budget_status == over` abzubrechen — **automatische Fallback-Leiter**:

```python
ladder = ["opus", "swe", "gpt_low"]
start_idx = ladder.index(recommended_model)

for model in ladder[start_idx:]:
    estimate = <orc>_get_cost_estimate(task_id, model=model, estimated_tokens=N)
    if estimate.budget_status == "ok":
        selected_model = model
        break
else:
    # Alle Modelle über Budget → Task splitten
    sub_plan = <orc>_agent_plan_task(description, complexity="simple")
    # Jede Sub-Task einzeln durch den Router schicken
```

**Downgrade-Guards (nie automatisch herunterstufen):**
- `complexity == architectural` → immer `opus`, nie downgraden
- `task_type == security` → immer `opus`, nie downgraden
- `complexity == architectural` + Budget over → User fragen, nicht automatisch splitten

**Log nach Downgrade:**
```
<orc>_log_action(task_id, action="model_downgrade",
    details="opus→swe (budget=$0.47/$0.50)")
```

---

## Step 3: Implementieren (Developer / Gate 1)

Cascade implementiert den Task — geleitet durch das **Constraint Manifest** aus Phase 0.

**Pflicht-Konventionen:**
- Kein direktes `print()` in Produktion — Logger verwenden
- Imports immer am Dateianfang
- Keine Hard-coded Credentials
- Tests für jede neue Funktion
- `ASSUMPTION[unverified]`-Einträge aus Phase 0 auflösen

---

## Step 3.5: Proactive Tasks (nach Implementierung, vor Guardian)

> Bounded Scope: nur berührte Files + direkte Abhängigkeiten.
> Flaggen, nicht auto-anwenden bei riskanten Änderungen.

### A) CHANGELOG aktualisieren

```bash
# Eintrag unter [Unreleased] in CHANGELOG.md ergänzen
```

### B) ADR-Impact-Detection

```bash
# Berühre ich ein bestehendes ADR?
grep -r "<schlüsselbegriff>" docs/adr/ | head -5
```
→ Falls Treffer: User informieren — ADR-Update nötig?

### C) Konsistenz-Scan (nur touched files)

```bash
# Pattern-Drift in editierten Models/Services?
grep -n "tenant_id\|public_id" <editierte_files>
# Fehlende data-testid in editierten Templates?
grep -n "hx-post\|hx-put\|button" <editierte_templates> | grep -v "data-testid"
```

### D) Refactoring-Flags → Auto-Issues (ADR-068)

Refactoring-Opportunities werden als GitHub Issues erstellt (nicht auto-angewendet — Out-of-Scope Schutz):

```
MCP: <gh>_create_issue(
    owner="achimdehnert", repo=<repo>,
    title="[refactor] <Datei>:<Zeile> — <Kurzbeschreibung>",
    body="Auto-erkannt in Task #<task_id>.\n\n"
         "**Problem:** <Funktion >50 Zeilen | JSONField | etc>\n"
         "**ADR:** <ADR-071 | ADR-022>\n"
         "**Aufwand:** <S|M|L>\n"
         "**Begründung Out-of-Scope:** bounded scope (ADR-081 ScopeLock)",
    labels=["refactor", "auto", "agentic-coding"]
)
```

**Trigger-Regeln** (nur bei Hit, kein Lärm):
- Funktion >50 Zeilen in **editierten** Files (ADR-071)
- `JSONField()` für strukturierte Daten in **editierten** Models (ADR-022)
- Fehlende `data-testid` in **editierten** Templates mit `hx-*` (ADR-048)
- Funktion mit Typ-Annotation `Any` in **editierten** Services

**Duplikat-Schutz:** vorher `<gh>_list_issues(labels=["refactor","auto"], state="open")` —
Issue nur erstellen wenn gleicher `<Datei>:<Zeile>` noch nicht offen.

---

## Step 4: Guardian-Check (Gate 0 — immer nach Implementierung)

**Befehle sind repo-spezifisch** — aus `project-facts.md` (`REPO_TYPE`, `TEST_CMD`, `LINT_CMD`) ableiten.

### Python / Django (risk-hub, bfagent, weltenhub, tax-hub, ...)

```bash
ruff check . --fix && ruff format . && ruff check .
bandit -r . -ll
python -m pytest tests/ -q --tb=short
```

### Python Package (iil-platform, aifw, promptfw, iil-testkit, ...)

```bash
ruff check . --fix && ruff format .
python -m pytest tests/ -q --cov=<package>
```

### Node / Playwright (iil-reflex, pptx-hub Frontend-Teile)

```bash
npm run lint
npm test
```

### Infra / Bash-only (infra-deploy, platform Scripts)

```bash
shellcheck scripts/*.sh
bash -n scripts/*.sh   # Syntax-Check
```

**ADR-174 QM Gate simulieren (alle Repos):**
```bash
grep -rnF "ASSUMPTION[unverified]" --include="*.py" . && exit 1 || true
```

**Bei Fail**: sofort fixen — nicht weitermachen.

---

## Step 5: Self-Review (ersetzt fiktives verify_task)

Cascade prüft Kriterien manuell und loggt das Ergebnis:

```
Kriterien-Check:
□ Tests grün (Step 4)?            → [✅/❌]
□ Ruff clean (Step 4)?            → [✅/❌]
□ Acceptance Criteria erfüllt?    → [✅/❌]
□ ADR-Violations = 0?              → [✅/❌]  (check_violations auf NEUEN Code)
□ Alle ASSUMPTION[unverified] aufgelöst? → [✅/❌]
□ Constraint Manifest eingehalten → [✅/❌]
```

```
MCP: <ctx>_check_violations(code_snippet="<neuer Code aus Step 3>")
→ Hier den tatsächlich geschriebenen Code prüfen (nicht vorhandener Code wie in Step 0)
```

```
MCP: <orc>_log_action(
    task_id,
    action="self_review",
    status="passed" | "failed",
    details="<Kriterien-Zusammenfassung>"
)
```

**Ergebnis:**
- Alle ✅ → weiter zu Step 6
- Irgendein ❌ → sofort fixen → retry Step 4 (max. 3×)
- 3× Fail → User Approval (Gate 2 Escalation via `<orc>_request_approval`)

---

## Step 6: QA Gate (ersetzt fiktives evaluate_task)

```
MCP: <orc>_check_gate(action="commit", component="<app>")
```

| check_gate Ergebnis | Aktion |
|---------------------|--------|
| `allowed` | → Step 7 |
| `warn` | → User informieren, dann Step 7 |
| `blocked` | → `<orc>_request_approval(gate=2)` → warten |

```
MCP: <orc>_log_action(
    task_id,
    action="qa_gate",
    status="passed" | "escalated",
    details="iterations={n}, gate={level}"
)
```

---

## Step 7: Commit + PR

> Branch-Strategie ist **repo-spezifisch** — `project-facts.md` lesen.
> Viele Repos committen direkt auf `main`. Falls Feature-Branch: `ai/{role}/{task-id}`.

```bash
# Scope verifizieren — nur editierte Dateien aus Step 3 stagen
git diff --name-only        # zeigt was geändert wurde
git add <tatsächlich editierte Dateien aus Step 3 — nie git add .>
git commit -m "type(scope): description

Closes #{issue-number}
ADR: {betroffene ADRs — dynamisch aus Step 3.5 B}
Task: {task-id}"
```

PR-Body enthält:
- Acceptance Criteria (✅ / ⬜)
- Self-Review Ergebnis (Step 5)
- ADR-Impact (Step 3.5 B)

---

## Step 8: AuditStore + GitHub Issue Update (ADR-068)

```
MCP: <gh>_add_issue_comment(owner, repo, issue_number, body)
```

Issue-Kommentar enthält: Self-Review Ergebnis, Gate-Level, CHANGELOG-Eintrag, Refactoring-Flags.

Danach: **`/complete`** ausführen (Task Completion Gate).

---

## Rollback-Pfad

```
Step 5 Self-Review → ❌
    │
    ├─ Tests rot       → pytest failures beheben → retry Step 4
    ├─ Ruff-Fehler     → ruff check --fix → retry Step 4
    ├─ ADR-Violation   → platform-context violations beheben → retry Step 4
    └─ Kriterien offen → Acceptance Criteria prüfen → retry Step 3

Step 6 QA Gate → blocked
    │
    ├─ request_approval → User entscheidet
    ├─ approved         → weiter Step 7
    └─ rejected         → git revert → neu planen ab Step 1
```


## Übersicht & Referenzen

→ **[`docs/governance/agentic-coding-reference.md`](../../docs/governance/agentic-coding-reference.md)**

Inhalte:
- Workflow-Diagramm (alle Phasen+Steps auf einen Blick)
- ADR-Referenzen (ADR-066, 067, 068, 080, 107, 108, 173)
