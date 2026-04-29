---
description: Fully Agentic Coding — Task definieren, planen, routen, ausführen, bewerten (v4)
---

# Agentic Coding Workflow v4

Operationalisiert ADR-066 + ADR-068 + ADR-080 + ADR-107 + ADR-108 + ADR-173.
**v4**: Phase 0 Contract Verification (PCV) + Step 3.5 Proactive Tasks. Fiktive MCP-Calls entfernt.

> ⚠️ MCP-Prefixes sind environment-spezifisch — Prefix aus `project-facts.md` oder
> `.windsurf/rules/mcp-tools.md` lesen. `<orc>` = Orchestrator-Prefix, `<ctx>` = Platform-Context-Prefix,
> `<gh>` = GitHub-MCP-Prefix.
>
> **task_id** = GitHub Issue-Nummer des aktuellen Tasks (aus dem Issue-Link). Dieser Wert wird
> in Steps 2, 5, 6, 8 als Audit-Referenz verwendet.

---

## Übersicht: Der vollständige Loop

```
Phase 0: Contract Verification    → PCV-Checkliste          (moderate+ | trivial: nur D)
Step 0:  Governance Check         → <ctx>_get_context_for_task
Step 1:  Task analysieren + plan  → <orc>_analyze_task + agent_plan_task
Step 2:  Kostenschätzung          → <orc>_get_cost_estimate  (complex+)
Step 3:  Implementieren           → Developer (Gate 1)
Step 3.5 Proactive Tasks          → CHANGELOG, ADR-Impact, Konsistenz-Scan
Step 4:  Guardian-Check           → ruff + bandit + pytest   (Gate 0)
Step 5:  Self-Review              → Kriterien-Checkliste + log_action
Step 6:  QA Gate                  → check_gate / request_approval
Step 7:  Commit + PR
Step 8:  AuditStore + Issue
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

## Step 0: Governance Check (immer bei complexity >= moderate)

```
MCP: <ctx>_get_context_for_task(repo, file_type)
→ liefert Architektur-Regeln + ADR-Referenzen + Repo-Facts

MCP: <ctx>_get_banned_patterns(context)
→ liefert verbotene Patterns für diesen Datei-Typ

MCP: <ctx>_check_violations(code_snippet="<vorhandener ähnlicher Code — nicht neuer Code>")
→ Optional: bestehenden verwandten Code auf Violations scannen (BEVOR du ihn erweiterst)
→ Neuen Code prüfen: → Step 5 (Self-Review)
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

Rollen-Zuweisung nach Gate:

| Task-Typ | Rolle | Gate |
|----------|-------|------|
| `feature` | Developer | Gate 1 |
| `bugfix` | Developer | Gate 1 |
| `test` | Tester | Gate 0 |
| `refactor` | Re-Engineer | Gate 2 |
| `adr` / `architecture` | Tech Lead | Gate 2 |
| `deployment` | Deployment Agent | Gate 2 |
| `pr_review` | Review Agent | Gate 1 |

Gate 2+ → User um Approval bitten (Chat), bevor weitergemacht wird.

---

## Step 2: Kostenschätzung (optional, empfohlen bei complex+)

```
MCP: <orc>_get_cost_estimate(task_id, model, estimated_tokens)
→ liefert: cost_usd, budget_status (ok/over), token_budget
```

Modell-Wahl:

| Complexity | Modell | Kosten/1k | Anwendung |
|------------|--------|-----------|-----------|
| `trivial` | `gpt_low` | $0.001 | docu-update, CHANGELOG, README-Sync |
| `simple` | `gpt_low` | $0.001 | Tests schreiben, kleine Bugfixes |
| `moderate` | `swe` | $0.003 | Features, Refactoring |
| `complex/architectural` | `opus` | $0.015 | ADRs, Architektur, komplexe Bugs |

Bei `budget_status = over` → complexity herunterstufen oder Task splitten.

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

### D) Refactoring-Flags (nur Listen, nie auto-anwenden)

```
Refactoring-Opportunities (nicht auto-angewendet):
- services.py:42 → Funktion >50 Zeilen (ADR-071)
- models.py:88 → JSONField für strukturierte Daten (BANNED)
```

---

## Step 4: Guardian-Check (Gate 0 — immer nach Implementierung)

```bash
# Ruff (Linter + Formatter)
ruff check . --fix
ruff format .
ruff check .   # nochmals prüfen — --fix hebt nicht alle Fehler

# Bandit (Security)
bandit -r . -ll

# Tests — Befehl ist repo-spezifisch (project-facts.md):
python -m pytest tests/ -q --tb=short
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
