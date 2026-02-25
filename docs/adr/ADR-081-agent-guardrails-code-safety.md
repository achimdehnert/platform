---
status: accepted
date: 2026-02-24
decision-makers: Achim Dehnert
consulted: –
informed: –
supersedes: –
amends: ADR-066-ai-engineering-team.md, ADR-080-multi-agent-coding-team-pattern.md
related: ADR-066, ADR-068, ADR-070, ADR-080
---

# ADR-081: Agent Guardrails & Code Safety — Scope-Lock, Pre/Post-Gates, Rollback

| Feld | Wert |
|------|------|
| **Status** | Accepted |
| **Datum** | 2026-02-24 |
| **Autor** | Achim Dehnert |
| **Amends** | ADR-066 (AI Engineering Squad), ADR-080 (Multi-Agent Handoff) |
| **Related** | ADR-068 (Model Routing), ADR-070 (Progressive Autonomy) |

---

## 1. Kontext und Problem

ADR-066 definiert Rollen und Gates. ADR-080 definiert Handoff und Rollback-Leiter.
**Beide ADRs setzen voraus, dass ein Agent nur das ändert was er soll** — aber keines
definiert den Mechanismus der das erzwingt.

Ohne Guardrails kann ein Agent:
1. **Scope-Drift**: Dateien außerhalb von `affected_paths` ändern (z.B. Migrations, Settings)
2. **Regressing Tests**: Tests überschreiben oder löschen die vorher grün waren
3. **ADR-Violations**: Code schreiben der gegen bekannte ADR-Entscheidungen verstößt
4. **Irreversible State**: Änderungen machen die nicht automatisch rückgängig gemacht werden können

**Problem:** Kein Mechanismus der Agents in einem definierten, sicheren Perimeter hält.

---

## 2. Decision Drivers

- **Scope-Integrität**: Agent kann nur ändern was er darf — nicht mehr
- **Test-Regression-Schutz**: Kein Agent-Commit der Tests rot macht (außer explizit erlaubt)
- **ADR-Compliance**: Agent-Aktionen werden gegen relevante ADRs geprüft
- **Reversibilität**: Jede Agent-Aktion ist rückgängig machbar (Git-Snapshot)
- **Minimale Friction**: Guardrails dürfen schnelle Tasks nicht signifikant verlangsamen

---

## 3. Considered Options

### Option A — Vertrauensbasiert (Status Quo)

Agent bekommt Task-Beschreibung und handelt nach bestem Wissen.

**Con:** Kein technischer Schutz — Scope-Drift, Test-Regressionen unentdeckt.
**Verworfen.**

### Option B — Filesystem-Level Sandboxing (z.B. Docker-Volume-Mount, chroot)

Agent läuft in isoliertem Container mit eingeschränktem Filesystem-Zugriff.

**Pro:** Starke Isolation
**Con:** Hoher Infrastruktur-Overhead, inkompatibel mit lokalem Windsurf/Cascade-Workflow.
**Verworfen** für v1.

### Option C — Soft-Enforcement durch Scope-Lock + Git-Hooks + Test-Gate (gewählt)

Drei Ebenen in Software:
1. **Scope-Lock** im `AgentHandoff` — deklarierter Perimeter
2. **Pre-Execution-Snapshot** — Git-Branch/Stash vor jeder Ausführung
3. **Post-Execution-Verifier** — prüft ob Agent im Scope geblieben ist

**Pro:** Sofort implementierbar, kein Infrastruktur-Overhead, reversibel.
**Con:** Kein hartes Filesystem-Blocking — Agent kann theoretisch den Lock ignorieren.
**Annahme:** In Windsurf/Cascade-Kontext ist der Agent Cascade selbst — der Lock ist
eine explizite Instruktion, keine technische Schranke. Cascade hält sich daran.

---

## 4. Entscheidung

**Option C** — Soft-Enforcement durch drei aufeinander aufbauende Schichten.

---

## 5. Architektur: Agent Guardrails

### 5.1 Drei-Schichten-Modell

```
┌─────────────────────────────────────────────────────────┐
│  Schicht 1: Pre-Execution                               │
│  ├── Scope-Lock deklarieren (AgentHandoff)              │
│  ├── Git-Snapshot erstellen (Branch ai/{role}/{id})     │
│  └── ADR-Compliance-Check (affected_adrs prüfen)        │
├─────────────────────────────────────────────────────────┤
│  Schicht 2: Post-Execution                              │
│  ├── Scope-Verifier: Nur erlaubte Pfade geändert?       │
│  ├── Guardian: Ruff + Bandit + MyPy grün?               │
│  └── Test-Gate: pytest grün, Coverage-Delta ≥ 0?        │
├─────────────────────────────────────────────────────────┤
│  Schicht 3: Rollback                                    │
│  ├── L1: Re-Engineer (Auto-Retry)                       │
│  ├── L2: Tech Lead Review                               │
│  ├── L3: Human-in-the-Loop                              │
│  └── L4: git checkout → Pre-Execution-Snapshot          │
└─────────────────────────────────────────────────────────┘
```

### 5.2 ScopeLock — das Kernkonzept

```python
class ScopeLock(BaseModel):
    """Deklarierter Perimeter für eine Agent-Ausführung (ADR-081)."""

    allowed_paths: list[str]
    """Erlaubte Pfade — Agent darf NUR diese ändern (glob-kompatibel)."""

    forbidden_paths: list[str] = Field(default_factory=list)
    """Explizit verbotene Pfade (Override über allowed_paths)."""

    allow_new_files: bool = True
    """Darf Agent neue Dateien erstellen (nur in allowed_paths)?"""

    allow_delete: bool = False
    """Darf Agent Dateien löschen? Default: Nein."""

    max_files_changed: int = 50
    """Maximale Anzahl Dateien die geändert werden dürfen."""

    max_lines_changed: int = 2000
    """Maximale Anzahl Zeilen (diff) die geändert werden dürfen."""
```

**Standardwerte nach Task-Typ:**

| Task-Typ | `allow_delete` | `max_files` | `allow_new_files` |
|----------|---------------|-------------|------------------|
| `bugfix` | `False` | 10 | `False` |
| `feature` | `False` | 30 | `True` |
| `refactor` | `False` | 50 | `False` |
| `test` | `False` | 20 | `True` |
| `adr` | `False` | 5 | `True` |
| `infra` | `True` | 20 | `True` |

### 5.3 Pre-Execution Guardrail

```python
class PreExecutionGuardrail:
    """Bereitet sichere Ausführungsumgebung vor (ADR-081 Schicht 1)."""

    def prepare(self, task: Task, cwd: str) -> PreExecutionContext:
        """
        1. Git-Branch erstellen: ai/{role}/{task_id}
        2. Snapshot-Commit-Hash merken (Rollback-Anker)
        3. ScopeLock aus task.affected_paths + task_type defaults ableiten
        4. ADR-Compliance-Check für task.affected_adrs
        """
        branch = f"ai/{task.type.value}/{task.task_id}"
        snapshot_hash = self._get_head_hash(cwd)
        scope_lock = ScopeLock.from_task(task)
        adr_issues = self._check_adr_compliance(task.affected_adrs, task.affected_paths)

        return PreExecutionContext(
            branch=branch,
            snapshot_hash=snapshot_hash,
            scope_lock=scope_lock,
            adr_compliance_issues=adr_issues,
        )
```

### 5.4 Post-Execution Verifier

```python
class PostExecutionVerifier:
    """Prüft ob Agent im Scope geblieben ist (ADR-081 Schicht 2)."""

    def verify(
        self,
        context: PreExecutionContext,
        cwd: str,
    ) -> VerificationResult:
        """
        1. git diff --name-only HEAD~1 → Liste geänderter Dateien
        2. Jede Datei gegen scope_lock.allowed_paths prüfen
        3. Verbotene Pfade prüfen (migrations/, settings/prod*)
        4. Anzahl geänderte Dateien / Zeilen prüfen
        """
        changed_files = self._get_changed_files(cwd)
        violations = []

        for f in changed_files:
            if not self._is_allowed(f, context.scope_lock):
                violations.append(ScopeViolation(
                    file=f,
                    reason="outside allowed_paths",
                    severity="blocking",
                ))
            if self._is_forbidden(f, context.scope_lock):
                violations.append(ScopeViolation(
                    file=f,
                    reason="explicitly forbidden path",
                    severity="blocking",
                ))

        blocking = [v for v in violations if v.severity == "blocking"]
        return VerificationResult(
            passed=len(blocking) == 0,
            violations=violations,
            changed_files=changed_files,
        )
```

### 5.5 Rollback-Mechanismus

```python
class RollbackEngine:
    """Führt Rollback auf Pre-Execution-Snapshot durch (ADR-081 Schicht 3)."""

    def rollback_to_snapshot(
        self,
        context: PreExecutionContext,
        cwd: str,
        reason: str,
    ) -> RollbackResult:
        """
        Harter Rollback: git reset --hard {snapshot_hash}
        Nur bei Level 3/4 — Level 1/2 arbeiten auf dem Branch weiter.
        """
        rc, _, stderr = _run_git(
            ["reset", "--hard", context.snapshot_hash],
            cwd,
        )
        return RollbackResult(
            success=rc == 0,
            snapshot_hash=context.snapshot_hash,
            reason=reason,
            error=stderr if rc != 0 else None,
        )

    def rollback_level(
        self,
        level: int,
        context: PreExecutionContext,
        handoff: "AgentHandoff",
        cwd: str,
    ) -> RollbackAction:
        match level:
            case 1:
                return RollbackAction.RE_ENGINEER_RETRY   # Bleibt auf Branch
            case 2:
                return RollbackAction.TECH_LEAD_REVIEW    # Bleibt auf Branch
            case 3:
                return RollbackAction.HUMAN_NOTIFY        # Bleibt auf Branch, wartet
            case 4:
                self.rollback_to_snapshot(context, cwd, handoff.blocking_issues[0])
                return RollbackAction.ABORTED
```

### 5.6 Verbotene Pfade (Plattform-Standard)

Immer verboten, unabhängig von `allowed_paths`:

```python
ALWAYS_FORBIDDEN_PATHS = [
    "*/migrations/*.py",          # DB-Migrations — nie automatisch
    "config/settings/prod*.py",   # Prod-Settings
    "config/settings/production*",
    ".env*",                      # Env-Dateien
    "docker-compose.prod.yml",    # Prod-Compose
    "*.pem", "*.key", "*.crt",   # Zertifikate / Schlüssel
    "requirements.txt",           # Basis-Dependencies (nur explizit)
]
```

---

## 6. Integration in AgentHandoff (amends ADR-080)

`AgentHandoff` aus ADR-080 wird um `scope_lock` und `pre_execution_context` erweitert:

```python
class AgentHandoff(BaseModel):
    # ... (ADR-080 Felder unverändert) ...

    # NEU (ADR-081):
    scope_lock: ScopeLock
    """Deklarierter Perimeter für den empfangenden Agenten."""

    pre_execution_context: PreExecutionContext | None = None
    """Gesetzt nach prepare() — enthält Snapshot-Hash und Branch."""

    verification_result: VerificationResult | None = None
    """Gesetzt nach verify() — Scope-Violations falls vorhanden."""
```

---

## 7. Implementierungsstruktur

```
orchestrator_mcp/agent_team/
  guardrails/
    __init__.py
    scope_lock.py          # ScopeLock Pydantic-Model + from_task() Factory (NEU)
    pre_execution.py       # PreExecutionGuardrail + PreExecutionContext (NEU)
    post_execution.py      # PostExecutionVerifier + VerificationResult (NEU)
    rollback.py            # RollbackEngine + RollbackAction (NEU)
    forbidden_paths.py     # ALWAYS_FORBIDDEN_PATHS + Matcher (NEU)
  handoff.py               # AgentHandoff + scope_lock Felder (UPDATE)
```

**Implementierungsreihenfolge:**
1. `guardrails/forbidden_paths.py` — keine Abhängigkeiten
2. `guardrails/scope_lock.py` — abhängig von `forbidden_paths`
3. `guardrails/pre_execution.py` — abhängig von `scope_lock`
4. `guardrails/post_execution.py` — abhängig von `scope_lock`
5. `guardrails/rollback.py` — abhängig von `pre_execution`
6. `handoff.py` — integriert `ScopeLock` und `PreExecutionContext`

---

## 8. Workflow-Integration (amends agentic-coding.md Step 4)

```
Step 4: Ausführung + Handoff (mit Guardrails)

  4.0  PreExecutionGuardrail.prepare(task, cwd)
       → Branch erstellen, Snapshot merken, ScopeLock ableiten
       → Bei ADR-Compliance-Issues → Gate 2 (kein Auto-Start)

  4.1  Agent führt aus (Developer / Tester / Re-Engineer)
       → Cascade bekommt scope_lock.allowed_paths als explizite Instruktion
       → "Ändere NUR Dateien in: {allowed_paths}"

  4.2  PostExecutionVerifier.verify(context, cwd)
       → Scope-Violations? → L1 Rollback (Re-Engineer)
       → Guardian-Fail? → L1 Rollback
       → Test-Fail? → L1 Rollback
       → Alles grün → AgentHandoff produzieren

  4.3  Handoff an nächsten Agenten
       → handoff.verification_result mitgeben
       → handoff.scope_lock für nächsten Agenten ableiten
```

---

## 9. Konsequenzen

### Positiv
- **Scope-Drift verhindert**: Agent kann Migrations, Prod-Settings etc. nie versehentlich ändern
- **Reversibilität garantiert**: Snapshot-Hash ist immer vorhanden — L4 Rollback in 1 Command
- **Audit-Trail**: Scope-Violations werden im AuditStore geloggt
- **Kontext für Cascade**: `scope_lock.allowed_paths` ist eine explizite, maschinenlesbare Instruktion

### Negativ / Risiken

| Risiko | Mitigation |
|--------|------------|
| Soft-Enforcement — kein hartes Blocking | Scope-Lock ist explizite Cascade-Instruktion; Violation wird erkannt und geloggt |
| False Positives bei Refactoring (viele Dateien) | `max_files_changed` per Task-Typ konfigurierbar |
| `ALWAYS_FORBIDDEN_PATHS` zu restriktiv | Override via `task.routing_hints.scope_override` (Gate 3 required) |

---

## 10. Entschiedene Fragen

| Frage | Entscheidung |
|-------|-----------|
| Soll Scope-Verifier im CI laufen (nicht nur lokal)? | **Ja** — pytest-Check in `tests/guardrails/`; umgesetzt v1 |
| Wie werden `ALWAYS_FORBIDDEN_PATHS` aktualisiert? | `forbidden_paths.py` versioniert, Änderung via ADR-Amendment — umgesetzt |
| Scope-Lock für parallele Branches bei TaskGraph? | Pro Branch eigener Lock — kein Shared State — umgesetzt in `merger.py` |

---

## 11. Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-02-25 | Achim Dehnert | v1: Implementierung abgeschlossen, Status → Accepted; §10 Fragen entschieden |
| 2026-02-24 | Achim Dehnert | v1 — Initial Proposed; Scope-Lock, Pre/Post-Gates, Rollback-Engine |
