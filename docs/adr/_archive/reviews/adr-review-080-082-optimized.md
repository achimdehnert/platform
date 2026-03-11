# ADR-Review: ADR-080 & ADR-082 (Optimierte Fassung)

## Kritischer Architektur-Review für produktionskritischen Code

**Reviewer:** Cascade (basierend auf Claude Opus 4.6 Review + Verifikation gegen Codebase)  
**Datum:** 2026-02-25  
**Scope:** ADR-080 (Multi-Agent Coding Team Pattern) + ADR-082 (LLM-Tool-Integration)  
**Stack-Kontext:** Django + HTMX + Postgres 16 auf Hetzner VMs via Docker, WSL + MCP  
**Verifikation:** Alle Befunde gegen `/home/deploy/projects/` Codebase verifiziert

---

## Änderungen gegenüber Original-Review

| Befund | Original | Optimiert | Begründung |
|--------|----------|-----------|------------|
| A1 `context_summary` | ERHEBLICH | **NIEDRIG** | `to_cascade_instruction()` rendert Vollkontext — 500 Zeichen betreffen nur ein Logging-Feld |
| B3 DynamicLLMClient | ERHEBLICH | **KRITISCH** | Verifiziert: `complete(messages, tools, tool_choice)` bereits implementiert — Duplikation ist Blocker |
| B5 Feature-Flag-Parsing | MITTEL | **ERHEBLICH** | Silent-Failure bei `AUTONOMOUS_DEVELOPER=1` in Production ist schwerwiegender als bewertet |
| C1 Temporal | MITTEL (deferred) | **INFO** | Phase 1 ist explizit synchron by design — kein Risiko, nur Dokumentations-Hinweis |

---

## Executive Summary

Beide ADRs sind architektonisch solide. Nach Verifikation gegen die Codebase ergibt sich:

**Gesamturteil: 9 Befunde — 3 kritisch, 3 erheblich, 2 mittel, 1 informell.**

Die drei kritischen Punkte:
1. **B1** — Kein Context-Window-Management im `StepExecutor` (unverändert kritisch)
2. **B2** — Kein Error-Recovery im Tool-Call-Loop (unverändert kritisch)
3. **B3** — `LLMClient` in ADR-082 dupliziert `DynamicLLMClient` aus `creative-services`, der bereits `tools`-Support hat (hochgestuft auf KRITISCH)

ADR-082 darf erst auf "Accepted" wechseln wenn B1, B2 und B3 adressiert sind.

---

## TEIL A: ADR-080 — Multi-Agent Coding Team Pattern

### Befund A1: `context_summary` — korrigierte Einstufung NIEDRIG (war: ERHEBLICH)

**Original-Befund:** 500 Zeichen limitieren den Context künstlich.

**Korrektur nach Code-Verifikation:** `to_cascade_instruction()` in `handoff.py` rendert
`artifacts_produced`, `decisions_made`, `acceptance_criteria` und `affected_paths` vollständig
in den Prompt — unabhängig vom `context_summary`-Feld. Das 500-Zeichen-Limit betrifft nur
ein optionales Logging/PR-Body-Feld, nicht den tatsächlichen Agent-Kontext.

**Verbleibende Empfehlung (optional):**
```python
# In AgentHandoff — explizit dokumentieren dass context_summary nur Logging ist:
context_summary: str = Field(
    "",
    max_length=500,
    description="Kurzzusammenfassung für Logging/PR-Body. Vollkontext via to_cascade_instruction().",
)
```

**Risiko:** NIEDRIG — Kein Blocker, nur Klarstellungs-Kandidat.

---

### Befund A2: Planner-Bypass — Complexity-Upgrade zur Laufzeit undokumentiert

**Befund:** Die Bypass-Bedingung `if task.complexity < TaskComplexity.COMPLEX` ist korrekt.
Fehlend ist die explizite Dokumentation des Falls, wenn ein Agent die Complexity im laufenden
Workflow höherstuft.

**Risiko:** MITTEL

**Empfehlung:** In ADR-080 §11 (Entscheidungen) ergänzen:

> "Complexity-Upgrade zur Laufzeit (z.B. Developer erkennt COMPLEX statt MODERATE) triggert
> Level-2-Rollback (Tech Lead Review). Nachträgliche Planner-Aktivierung ist bewusst ausgeschlossen
> — der Workflow bleibt sequentiell. Begründung: Parallelisierung mitten in einem laufenden
> Workflow erzeugt mehr Merge-Komplexität als sie löst."

---

### Befund A3: Rollback-Loop-Guard — globaler Counter fehlt

**Befund:** L1→L2-Loop ist durch "max 1 Re-Engineer-Retry" abgesichert. L2→L3→L2-Loop
(Tech Lead ↔ Human) ist nicht explizit kodifiziert.

**Risiko:** NIEDRIG

**Empfehlung:** In `WorkflowResult` ergänzen:
```python
escalation_count: int = Field(0, description="Anzahl Level-Wechsel im Rollback")
# In RollbackEngine: if escalation_count >= 3: force Level-4 (Abort)
```

---

### Befund A4: MAX_PARALLEL_BRANCHES = 3 — Herleitung fehlt

**Risiko:** INFO

**Empfehlung:** Einzeiler in ADR-080 §11:
> "MAX_PARALLEL_BRANCHES = 3: (a) Typische Feature-Tasks zerfallen in ≤ 3 unabhängige
> Sub-Tasks, (b) höhere Parallelität sprengt Token-Budget pro Run, (c) Merge-Komplexität
> wächst superlinear."

---

## TEIL B: ADR-082 — LLM-Tool-Integration Autonomous Coding

### Befund B1 (KRITISCH): StepExecutor — kein Context-Window-Management

**Befund:** `StepExecutor.run()` mit `max_tool_calls=20` ohne Context-Compaction.
Jeder Tool-Call akkumuliert Context (File-Inhalte, Git-Diffs, Shell-Output).
Bei 20 Tool-Calls sind 50k–100k Token-Context realistisch.

**Verifikation:** `DynamicLLMClient` in `creative-services` hat kein eingebautes
Context-Management — muss im `StepExecutor` selbst implementiert werden.

**Empfehlung:**
```python
@dataclass
class StepExecutor:
    max_tool_calls: int = 20
    max_context_tokens: int = 100_000     # Soft-Limit
    compaction_threshold: int = 15        # Nach N Tool-Calls komprimieren

    def _maybe_compact_context(
        self,
        messages: list[Message],
        tool_call_count: int,
    ) -> list[Message]:
        """Context Compaction nach Google ADK Pattern.

        Behält System-Prompt (messages[0]) stabil → Prompt-Cache-freundlich.
        Komprimiert messages[1:-3] zu Summary via Economy-LLM.
        Letzte 3 Messages bleiben vollständig (Recency-Bias).
        """
        if tool_call_count < self.compaction_threshold:
            return messages
        # messages[0] = System-Prompt (stabil, cache-freundlich)
        # messages[1:-3] → komprimieren via Budget-LLM (gpt-4o-mini / claude-haiku)
        # messages[-3:] → vollständig behalten
        ...
```

Zusätzlich: `max_tool_calls` an `task.complexity` koppeln:
```python
COMPLEXITY_TOOL_LIMITS = {
    TaskComplexity.SIMPLE: 5,
    TaskComplexity.MODERATE: 12,
    TaskComplexity.COMPLEX: 20,
    TaskComplexity.ARCHITECTURAL: 20,
}
```

---

### Befund B2 (KRITISCH): Tool-Call-Loop — keine Retry/Error-Recovery

**Befund:** ADR-082 §5.3 definiert den Tool-Call-Loop ohne Error-Recovery-Semantik.
Undefiniertes Verhalten bei: `ScopeViolationError`, `TimeoutError`, malformed LLM-Output.

**Empfehlung:**
```python
class ToolCallErrorStrategy(Enum):
    RETRY_WITH_FEEDBACK = "retry"   # Fehlermeldung → LLM → erneuter Versuch
    SKIP_AND_CONTINUE = "skip"      # Tool-Call überspringen
    ABORT_STEP = "abort"            # Step abbrechen → Rollback-Leiter

TOOL_ERROR_STRATEGIES: dict[type[Exception], ToolCallErrorStrategy] = {
    ScopeViolationError: ToolCallErrorStrategy.RETRY_WITH_FEEDBACK,
    TimeoutError: ToolCallErrorStrategy.RETRY_WITH_FEEDBACK,
    PermissionError: ToolCallErrorStrategy.ABORT_STEP,
    BudgetExceededError: ToolCallErrorStrategy.ABORT_STEP,
    json.JSONDecodeError: ToolCallErrorStrategy.RETRY_WITH_FEEDBACK,
}

# max_tool_call_retries: int = 3 pro einzelnem Tool-Call
# Bei 3 Fehlversuchen auf demselben Call → ABORT_STEP
```

---

### Befund B3 (KRITISCH — hochgestuft von ERHEBLICH): LLMClient dupliziert DynamicLLMClient

**Befund:** ADR-082 §5.4 plant einen neuen `LLMClient`. Nach Verifikation existiert in
`/home/deploy/projects/platform/packages/creative-services/creative_services/core/llm_client.py`
bereits ein `DynamicLLMClient` mit:
- Multi-Provider-Support (OpenAI, Anthropic, Ollama)
- `async def complete(messages, tools, tool_choice)` — **Tool-Calling bereits implementiert**
- `CompletionResponse` mit `tool_calls: list[ToolCall]`

Dies ist eine **direkte Duplikation** der geplanten ADR-082-Funktionalität.

**Risiko:** KRITISCH — Zwei parallele LLM-Client-Abstraktionen mit Tool-Support in derselben
Platform sind ein Maintenance-Blocker. Bei Provider-Updates (z.B. neues Anthropic SDK) müssen
beide Implementierungen synchron gehalten werden.

**Empfehlung:** ADR-082 §5.4 ersetzen durch:
```python
# orchestrator_mcp/llm_adapter.py
from creative_services.core.llm_client import DynamicLLMClient, LLMConfig

class OrchestratorLLMAdapter:
    """Thin Adapter: DynamicLLMClient + orchestrator-spezifisches Tool-Interface.

    Begründung: DynamicLLMClient hat bereits complete(messages, tools, tool_choice).
    Dieser Adapter fügt nur orchestrator-spezifische Budget-Tracking-Integration hinzu.
    """
    def __init__(self, config: LLMConfig, budget: ExecutionBudget) -> None:
        self._client = DynamicLLMClient(config)
        self._budget = budget

    async def complete_with_tools(
        self,
        messages: list[Message],
        tools: list[ToolSpec],
        budget: ExecutionBudget,
    ) -> CompletionResponse:
        # Budget-Check vor Call
        # Wrapped DynamicLLMClient.complete()
        # Budget-Update nach Call
        ...
```

Falls `creative-services` als Dependency nicht möglich (Circular Import):
- Explizit im ADR begründen
- Extraktion beider Clients in `platform_core` als mittelfristiges Ziel dokumentieren

---

### Befund B4 (ERHEBLICH): `git add` in Shell-Allowlist umgeht ScopeLock

**Befund:** `git add` ist eine schreibende Operation. Ein Agent kann beliebige Dateien
außerhalb des ScopeLocks via `git add` + `git commit` commiten, ohne dass `FileWriteTool`
involviert war. `FileWriteTool` triggert den ScopeLock-Check, `ShellTool` mit `git add` nicht.

**Empfehlung:** `git add` aus der Shell-Allowlist entfernen, stattdessen:
```python
class GitStageTool(BaseTool):
    """git add mit ScopeLock-Validierung (ADR-082 Fix B4)."""
    is_write_operation: bool = True  # Triggert ScopeLock-Check in ToolRegistry

    def execute(self, args: dict) -> ToolResult:
        path = Path(args["path"])
        # ScopeLock-Check wird von ToolRegistry.execute() erzwungen (is_write_operation=True)
        return run_shell(f"git add {shlex.quote(str(path))}")
```

`git log` bleibt in der Shell-Allowlist (read-only, kein ScopeLock nötig).

---

### Befund B5 (ERHEBLICH — hochgestuft von MITTEL): Feature-Flag-Parsing ohne Validierung

**Befund:** `os.getenv("AUTONOMOUS_DEVELOPER", "false").lower() == "true"` gibt `False`
für `"1"`, `"yes"`, `"True"`, `"TRUE"`. Silent Failure in Production.

**Korrigierte Einstufung:** ERHEBLICH — Ein Ops-Engineer, der `AUTONOMOUS_DEVELOPER=1`
in einer `.env`-Datei setzt und erwartet dass der Agent autonom arbeitet, bekommt stattdessen
einen Stub-Workflow. Dieser Fehler ist schwer zu debuggen (kein Error, nur falsches Verhalten).

**Empfehlung:**
```python
def _parse_bool_env(name: str, default: bool = False) -> bool:
    """Strikte Boolean-Parsing — wirft ValueError bei unbekannten Werten."""
    raw = os.getenv(name, str(default)).lower().strip()
    if raw in ("true", "1", "yes"):
        return True
    if raw in ("false", "0", "no", ""):
        return False
    raise ValueError(
        f"Invalid boolean for {name}={raw!r}. "
        f"Expected: true/false/1/0/yes/no"
    )

@dataclass(frozen=True)
class AutonomousFeatures:
    developer_implement: bool = False
    re_engineer_root_cause: bool = False
    tech_lead_design: bool = False
    tech_lead_review: bool = False
    planner_llm_decompose: bool = False

    def __post_init__(self) -> None:
        """Invarianten-Check: Phase N setzt Phase N-1 voraus."""
        if self.tech_lead_design and not self.developer_implement:
            raise ValueError(
                "AUTONOMOUS_TECH_LEAD_DESIGN requires AUTONOMOUS_DEVELOPER=true "
                "(Phase 2 requires Phase 1)"
            )
        if self.planner_llm_decompose and not self.tech_lead_design:
            raise ValueError(
                "AUTONOMOUS_PLANNER requires AUTONOMOUS_TECH_LEAD_DESIGN=true "
                "(Phase 3 requires Phase 2)"
            )

AUTONOMOUS_FEATURES = AutonomousFeatures(
    developer_implement=_parse_bool_env("AUTONOMOUS_DEVELOPER"),
    re_engineer_root_cause=_parse_bool_env("AUTONOMOUS_RE_ENGINEER"),
    tech_lead_design=_parse_bool_env("AUTONOMOUS_TECH_LEAD_DESIGN"),
    tech_lead_review=_parse_bool_env("AUTONOMOUS_TECH_LEAD_REVIEW"),
    planner_llm_decompose=_parse_bool_env("AUTONOMOUS_PLANNER"),
)
```

---

## TEIL C: Cross-ADR-Analyse

### Befund C1: Temporal-Integration — korrigierte Einstufung INFO (war: MITTEL deferred)

**Korrektur:** ADR-082 ist explizit in 3 Phasen strukturiert. Phase 1 ist synchron
by design — das ist eine bewusste Entscheidung, keine Lücke. Temporal-Migration ist
als "deferred" korrekt eingeordnet.

**Empfehlung:** Im ADR-082 §8 (Deferred) ergänzen:
> "Temporal-Integration (Phase 2+): `StepExecutor.run()` als Temporal Activity,
> `run_workflow()` als Temporal Workflow. Die synchrone Phase-1-Architektur verbaut
> diese Migration nicht — `StepExecutor` ist bereits als eigenständige Komponente
> isoliert."

---

### Befund C2: Keine Parity-Tests Stub vs. Autonomous

**Befund:** Kein Test verifiziert dass `AUTONOMOUS_DEVELOPER=false` und `true` unter
identischen Inputs semantisch äquivalente `AgentHandoff`-Outputs produzieren.

**Risiko:** MITTEL

**Empfehlung:** `test_workflows_parity.py`:
```python
@pytest.mark.parametrize("autonomous", [False, True])
def test_workflow_parity(autonomous: bool, mock_llm_client):
    """AUTONOMOUS_DEVELOPER=false/true → identische AgentHandoff-Struktur."""
    with patch.dict(os.environ, {"AUTONOMOUS_DEVELOPER": str(autonomous).lower()}):
        result = run_workflow(_task(task_type=TaskType.FEATURE))

    assert result.status in (WorkflowStatus.SUCCESS, WorkflowStatus.WAITING_APPROVAL)
    assert result.next_agent_instruction is not None
    # Struktur des Handoffs ist identisch, nur status und artifacts_produced differ
```

---

## Zusammenfassung (optimiert)

| # | ADR | Schwere | Befund | Empfehlung (Kurzform) | Prio |
|---|-----|---------|--------|-----------------------|------|
| B1 | 082 | **KRITISCH** | Kein Context-Window-Management | Context Compaction + Complexity-abhängige Tool-Limits | Blocker |
| B2 | 082 | **KRITISCH** | Kein Error-Recovery im Tool-Call-Loop | `ToolCallErrorStrategy`-Enum + max 3 Retries | Blocker |
| B3 | 082 | **KRITISCH** ↑ | LLMClient dupliziert `DynamicLLMClient` (tool-support verifiziert) | `OrchestratorLLMAdapter` wraps `DynamicLLMClient` | Blocker |
| B4 | 082 | ERHEBLICH | `git add` umgeht ScopeLock | `GitStageTool` mit `is_write_operation=True` | Sprint 1 |
| B5 | 082 | ERHEBLICH ↑ | Feature-Flag Silent Failure bei `=1`/`=yes` | `_parse_bool_env()` + `__post_init__`-Invarianten | Sprint 1 |
| A2 | 080 | MITTEL | Complexity-Upgrade zur Laufzeit undokumentiert | Design-Decision in §11 explizieren | Sprint 1 |
| C2 | 080+082 | MITTEL | Keine Parity-Tests | `test_workflows_parity.py` | Sprint 2 |
| A3 | 080 | NIEDRIG | Rollback-Loop-Guard unvollständig | Globaler `escalation_count` | Backlog |
| A1 | 080 | NIEDRIG ↓ | `context_summary` 500 Zeichen | Docstring-Klarstellung (kein Code-Change nötig) | Backlog |
| A4 | 080 | INFO | MAX_PARALLEL_BRANCHES ohne Herleitung | Einzeiler in §11 | Backlog |
| C1 | 082 | INFO ↓ | Temporal nicht erwähnt | Deferred-Notiz in §8 | Backlog |

---

## Abschließende Bewertung (optimiert)

**ADR-080:** Reif für Production. Befunde A1–A4 sind Verbesserungen, keine Blocker.
Das Handoff-Modell und `to_cascade_instruction()` sind industrieweit Best Practice.

**ADR-082:** Status "Proposed" ist korrekt. **3 Blocker** müssen vor "Accepted" adressiert sein:
- **B1** (Context-Engineering) und **B2** (Error-Recovery) — wie im Original korrekt identifiziert
- **B3** (DynamicLLMClient-Duplikation) — nach Code-Verifikation hochgestuft auf KRITISCH,
  da `DynamicLLMClient.complete(messages, tools, tool_choice)` bereits vollständig implementiert ist

**Gesamtarchitektur ADR-066 → 068 → 070 → 080 → 081 → 082** ist kohärent und
architektonisch reif. Die Progression vom strukturierten Framework (ADR-080) zum
autonomen System (ADR-082) ist nachvollziehbar und korrekt phasiert.
