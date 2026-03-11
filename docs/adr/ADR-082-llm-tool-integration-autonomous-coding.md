---
status: accepted
date: 2026-02-25
decision-makers: Achim Dehnert
consulted: –
informed: –
supersedes: –
amends: ADR-066-ai-engineering-team.md, ADR-080-multi-agent-coding-team-pattern.md
related: ADR-066, ADR-068, ADR-070, ADR-080, ADR-081
implementation_status: implemented
implementation_evidence:
  - "mcp-hub/orchestrator_mcp/: LLM tool integration"
---

# ADR-082: Wir ersetzen Stub-Steps durch echte LLM-Tool-Calls um das Agent Team autonom Coding-Tasks ausführen zu lassen

| Feld | Wert |
|------|------|
| **Status** | Accepted |
| **Datum** | 2026-02-25 |
| **Autor** | Achim Dehnert |
| **Amends** | ADR-066 (AI Engineering Squad), ADR-080 (Multi-Agent Handoff) |
| **Related** | ADR-068 (Adaptive Model Routing), ADR-070 (Progressive Autonomy), ADR-081 (Guardrails) |

---

## 1. Kontext und Problem

ADR-066 bis ADR-081 definieren ein vollständiges Multi-Agent Coding Team mit strukturiertem
Handoff, Guardrails, Rollback-Strategie und Workflow-Orchestrierung.

**Der kritische Gap:** Alle Agent-Steps (`developer_implement`, `re_engineer_root_cause`,
`tech_lead_design` etc.) sind **Stubs mit `WAITING_APPROVAL`-Status** — sie beschreiben
was ein Mensch tun soll, führen aber nichts aus. Das System ist ein gut strukturiertes
Human-in-the-Loop-Gerüst, kein autonomes Agent Team.

### Aktuelle Situation: Vollständige Stub-Architektur

```
run_workflow()
  ├── guardian_step()         ✅ REAL  — Ruff/Bandit/MyPy läuft
  ├── initial_handoff         ✅ REAL  — AgentHandoff wird erzeugt
  ├── planner_decompose       ✅ REAL  — TaskGraph wird erzeugt (rule-based)
  ├── developer_implement     ❌ STUB  — "Gate 1: human executes"
  ├── tester_step()           ✅ REAL  — pytest läuft (run_suite)
  ├── re_engineer_root_cause  ❌ STUB  — "Gate 2: human refactors"
  ├── tech_lead_design        ❌ STUB  — "Gate 2: Tech Lead Design Review"
  ├── tech_lead_review        ❌ STUB  — "Gate 3: human reviews"
  └── merger_merge            ✅ REAL  — Merger.merge() läuft
```

### Drei strukturelle Lücken

**Lücke 1: Kein LLM-Execution-Layer**
Die Stub-Steps haben keinen Mechanismus um Code zu lesen, zu analysieren und zu schreiben.
Es gibt keine Verbindung zwischen `AgentHandoff.to_cascade_instruction()` und einem echten
LLM-Call der diese Instruktion ausführt.

**Lücke 2: Kein Tool-Set für Code-Operationen**
Agenten brauchen strukturierten Zugriff auf: Filesystem (read/write), Git (status/diff/commit),
Shell (test runner, linter), und optional externe APIs. Ohne ein definiertes Tool-Set
können LLM-Calls keinen Code produzieren der in das bestehende Guardrail-System integriert ist.

**Lücke 3: Kein Execution-Budget-Management**
Autonome LLM-Calls erzeugen Token-Kosten pro Step. Ohne Budget-Limits und Cost-Tracking
pro Workflow-Run ist autonome Ausführung unkontrollierbar. ADR-068 definiert Model-Tiers,
aber kein per-Run-Budget.

---

## 2. Decision Drivers

- **Autonomie**: Developer- und Re-Engineer-Steps werden ohne menschliches Eingreifen ausgeführt
- **Sicherheit**: Guardrails (ADR-081) bleiben vollständig erhalten — LLM schreibt nie direkt, immer durch ScopeLock-verifizierten Layer
- **Nachvollziehbarkeit**: Jeder LLM-Call ist im AuditStore geloggt (Prompt, Response, Token-Count, Cost)
- **Kosteneffizienz**: Budget-Tier (ADR-068) pro Step-Typ — kein High-Reasoning für triviale Code-Tasks
- **Inkrementalität**: Stubs werden schrittweise durch echte Calls ersetzt — kein Big-Bang-Refactor
- **Vendor-Agnostizität**: LLM-Provider austauschbar (OpenAI, Anthropic, lokale Modelle) — kein SDK-Lock-in
- **Reversibilität**: Jeder autonome Step kann via Feature-Flag deaktiviert werden → zurück zu WAITING_APPROVAL

---

## 3. Considered Options

### Option A — Direkter OpenAI/Anthropic SDK-Call pro Step

Jeder Stub-Step wird durch einen direkten LLM-SDK-Call ersetzt. Kein Abstraktions-Layer.

**Pro:**
- Schnellste Time-to-First-Autonomous-Step
- Minimaler Overhead

**Con:**
- Vendor-Lock-in — Modell-Wechsel erfordert Code-Änderungen
- Kein einheitliches Tool-Interface — jeder Step implementiert Tool-Calling anders
- Keine Budget-Kontrolle über Steps hinweg
- **Verworfen**

### Option B — LangChain/LlamaIndex als Abstraktions-Layer

Etabliertes Framework für LLM-Orchestrierung mit Tool-Calling, Memory und Agent-Loops.

**Pro:**
- Breites Ökosystem, viele fertige Tools
- Gut dokumentiert

**Con:**
- Externes Framework-Dependency widerspricht ADR-073 (kein Vendor-Lock auf Framework-Ebene)
- Overhead und Abhängigkeiten passen nicht zur schlanken mcp-hub Architektur
- Tool-Calling-Abstraktion überschreibt bestehendes Guardrail-System
- **Verworfen**

### Option C — Eigener LLM-Execution-Layer mit Tool-Registry (gewählt)

Minimaler, eigener `ExecutionEngine`-Layer mit:
- **`LLMClient`**: Dünner, Provider-agnostischer Wrapper (OpenAI-kompatibles API-Format)
- **`ToolRegistry`**: Registrierte Tools (read_file, write_file, run_command, git_*) mit ScopeLock-Validierung
- **`StepExecutor`**: Verbindet `AgentHandoff.to_cascade_instruction()` → LLM-Call → Tool-Calls → neuer `AgentHandoff`
- **`ExecutionBudget`**: Per-Run-Token- und Cost-Tracking mit Hard-Limits

**Pro:**
- Vollständige Kontrolle über Tool-Execution (Guardrails bleiben erhalten)
- Provider-agnostisch durch OpenAI-kompatibles Format (OpenAI, Anthropic via compatibility layer, Ollama)
- Nahtlose Integration in bestehende `workflows.py` — Stubs werden durch `StepExecutor.run()` ersetzt
- Feature-Flags pro Step-Typ — schrittweise Migration
- **Gewählt**

### Option D — MCP-Tool-Server als Execution-Layer

Agent-Steps werden als MCP-Tools exponiert und durch einen externen MCP-Client (Windsurf/Claude)
ausgeführt. Das Agent Team wird zum MCP-Server statt zum MCP-Client.

**Pro:**
- Native Integration mit Windsurf-IDE
- Kein eigener LLM-Client nötig

**Con:**
- Architekturumkehr: mcp-hub wird Server, verliert Kontrolle über Execution-Flow
- Latenz und Verfügbarkeit abhängig von IDE-Verbindung
- **Deferred: Phase 2 — als ergänzender Execution-Mode möglich**

---

## 4. Entscheidung

**Option C: Eigener LLM-Execution-Layer mit Tool-Registry.**

Der `StepExecutor` ersetzt Stub-Steps schrittweise in drei Phasen:
- **Phase 1** (v1): `developer_implement` + `re_engineer_root_cause` — höchster Autonomie-Gewinn
- **Phase 2** (v2): `tech_lead_design` + `tech_lead_review` — Architektur-Entscheidungen
- **Phase 3** (v3): Planner `_llm_decompose()` (bereits in ADR-080 §5.5 geplant)

Feature-Flags steuern ob ein Step autonom ausgeführt oder als WAITING_APPROVAL zurückgegeben wird.

### Confirmation

Die Implementierung gilt als korrekt, wenn:

1. **StepExecutor**: `StepExecutor.run(handoff, tool_registry)` führt einen LLM-gestützten Step aus und gibt einen neuen `AgentHandoff` zurück — verifizierbar via `test_executor.py`
2. **ToolRegistry**: Alle registrierten Tools werden vor Ausführung gegen den `ScopeLock` des `AgentHandoff` validiert — verifizierbar via `test_tool_registry.py`
3. **developer_implement autonom**: Ein SIMPLE/MODERATE BUGFIX-Task läuft ohne `WAITING_APPROVAL`-Step durch — verifizierbar via `test_workflows_autonomous.py`
4. **Budget-Guard**: Ein Run mit `max_cost_usd=0.10` überschreitet das Limit nicht und bricht sauber ab — verifizierbar via `test_execution_budget.py`
5. **AuditStore**: Jeder LLM-Call ist mit Prompt-Hash, Token-Count, Cost und Step-ID geloggt — verifizierbar via AuditStore-Query
6. **Feature-Flag OFF → WAITING_APPROVAL**: Bei `AUTONOMOUS_DEVELOPER=false` verhält sich der Workflow identisch zu ADR-080 v1 — Regressions-Test grün
7. **173+ bestehende Tests grün**: Keine Regressionen in `orchestrator_mcp/agent_team/tests/`

---

## 5. Architektur: LLM-Execution-Layer

### 5.1 Komponenten-Übersicht

```
workflows.py (ADR-080)
    │
    ▼
StepExecutor                          ← NEU (ADR-082)
    │
    ├── LLMClient                     ← NEU — Provider-agnostischer Wrapper
    │     ├── OpenAIProvider
    │     ├── AnthropicProvider (via compat)
    │     └── OllamaProvider (lokal)
    │
    ├── ToolRegistry                  ← NEU — ScopeLock-validierte Tools
    │     ├── FileReadTool
    │     ├── FileWriteTool            (ScopeLock-verifiziert!)
    │     ├── ShellTool                (Allowlist + Timeout)
    │     ├── GitTool                  (read-only + staged-only writes)
    │     └── SearchTool
    │
    ├── ExecutionBudget               ← NEU — Token/Cost-Tracking
    │
    └── AgentHandoff (ADR-080)        ← to_cascade_instruction() → System-Prompt
```

### 5.2 StepExecutor — Kernkomponente

```python
@dataclass
class StepExecutor:
    """Führt einen Agenten-Step autonom via LLM + Tools aus (ADR-082).

    Input:  AgentHandoff (from_agent definiert verfügbare Tools)
    Output: AgentHandoff (to_agent = nächste Rolle, artifacts_produced befüllt)
    """

    llm_client: LLMClient
    tool_registry: ToolRegistry
    budget: ExecutionBudget
    audit_logger: AuditLogger

    def run(
        self,
        handoff: AgentHandoff,
        step_id: str,
        max_tool_calls: int = 20,
    ) -> StepResult:
        """
        Ablauf:
        1. System-Prompt aus handoff.to_cascade_instruction()
        2. LLM-Call mit verfügbaren Tools (gefiltert nach AgentRole + ScopeLock)
        3. Tool-Call-Loop: LLM ruft Tools, ExecutionBudget prüft Limit
        4. Finales LLM-Call: strukturierter Output als AgentHandoff
        5. AuditStore: kompletter Call-Trace geloggt
        """
        ...
```

### 5.3 ToolRegistry — ScopeLock-Integration

Alle File-Write-Operationen durchlaufen obligatorisch den `ScopeLock`-Check (ADR-081):

```python
class ToolRegistry:
    """Registrierung und ScopeLock-Validierung aller Agent-Tools (ADR-082)."""

    def execute(
        self,
        tool_name: str,
        args: dict,
        scope_lock: ScopeLock,
        role: AgentRole,
    ) -> ToolResult:
        tool = self._tools[tool_name]

        # ScopeLock-Check für alle schreibenden Operationen
        if tool.is_write_operation:
            affected_path = args.get("path", "")
            if not scope_lock.allows_path(affected_path):
                raise ScopeViolationError(
                    f"Tool '{tool_name}' attempted write to '{affected_path}' "
                    f"outside ScopeLock: {scope_lock.allowed_paths}"
                )

        # Role-Permission-Check
        if tool_name not in ROLE_TOOL_PERMISSIONS[role]:
            raise PermissionError(f"Role {role.value} not allowed to use {tool_name}")

        return tool.execute(args)
```

**Role-Tool-Permissions Matrix:**

| Tool | Tech Lead | Developer | Tester | Re-Engineer | Guardian |
|------|-----------|-----------|--------|-------------|----------|
| `read_file` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `write_file` | ✅ (ADR/docs) | ✅ (src only) | ✅ (tests only) | ✅ (src only) | ❌ |
| `run_shell` | ✅ (allowlist) | ✅ (allowlist) | ✅ (test-cmds) | ✅ (allowlist) | ✅ (linter) |
| `git_diff` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `git_commit` | ❌ | ✅ (staged only) | ❌ | ✅ (staged only) | ❌ |
| `search_code` | ✅ | ✅ | ✅ | ✅ | ✅ |

### 5.4 LLMClient — Provider-Agnostizität

OpenAI Chat-Completion-Format als gemeinsame Sprache. Alle Provider implementieren denselben
`BaseProvider`-Interface:

```python
@dataclass
class LLMRequest:
    system_prompt: str
    messages: list[Message]
    tools: list[ToolSchema]          # JSON-Schema der verfügbaren Tools
    model: str                        # Aus ModelTier (ADR-068)
    max_tokens: int = 4096
    temperature: float = 0.0          # Deterministisch für Coding-Tasks

@dataclass
class LLMResponse:
    content: str | None
    tool_calls: list[ToolCall]
    usage: TokenUsage                  # prompt_tokens, completion_tokens, total
    cost_usd: float
    model_used: str
    finish_reason: FinishReason        # stop | tool_calls | length | error
```

**Provider-Mapping** (ADR-068 ModelTier):

| ModelTier | Default Provider | Model | Einsatz |
|-----------|-----------------|-------|---------|
| `BUDGET` | OpenAI-compatible | `gpt-4o-mini` / Gemini Flash | Planner, einfache Fixes |
| `STANDARD` | OpenAI | `gpt-4o` | Developer, Re-Engineer |
| `HIGH_REASONING` | Anthropic | `claude-opus-4` / o3 | Tech Lead Review, ADR |
| `LOCAL` | Ollama | `qwen2.5-coder:7b` | Guardian, offline-fähig |

### 5.5 ExecutionBudget — Cost-Control

```python
@dataclass
class ExecutionBudget:
    """Token- und Cost-Budget pro Workflow-Run (ADR-082)."""

    max_cost_usd: float = 1.00       # Hard-Limit — überschreiten → L3-Rollback
    max_tokens_total: int = 200_000  # Sicherheitsnetz
    warn_threshold: float = 0.80     # 80% → Warning ins AuditStore

    _spent_usd: float = field(default=0.0, init=False)
    _spent_tokens: int = field(default=0, init=False)

    def charge(self, usage: TokenUsage, cost_usd: float) -> None:
        self._spent_usd += cost_usd
        self._spent_tokens += usage.total_tokens
        if self._spent_usd > self.max_cost_usd:
            raise BudgetExceededError(
                f"Execution budget exceeded: ${self._spent_usd:.3f} > ${self.max_cost_usd:.3f}"
            )
```

### 5.6 Feature-Flag-System

```python
# config/autonomous_features.py
@dataclass(frozen=True)
class AutonomousFeatures:
    """Feature-Flags für autonome Ausführung pro Step-Typ (ADR-082).

    Alle Flags default=False → Rückwärtskompatibilität mit ADR-080 v1.
    """
    developer_implement: bool = False      # Phase 1
    re_engineer_root_cause: bool = False   # Phase 1
    tech_lead_design: bool = False         # Phase 2
    tech_lead_review: bool = False         # Phase 2
    planner_llm_decompose: bool = False    # Phase 3 (ADR-080 §5.5)


AUTONOMOUS_FEATURES = AutonomousFeatures(
    developer_implement=os.getenv("AUTONOMOUS_DEVELOPER", "false").lower() == "true",
    re_engineer_root_cause=os.getenv("AUTONOMOUS_RE_ENGINEER", "false").lower() == "true",
    tech_lead_design=os.getenv("AUTONOMOUS_TECH_LEAD_DESIGN", "false").lower() == "true",
    tech_lead_review=os.getenv("AUTONOMOUS_TECH_LEAD_REVIEW", "false").lower() == "true",
    planner_llm_decompose=os.getenv("AUTONOMOUS_PLANNER", "false").lower() == "true",
)
```

### 5.7 Integration in workflows.py

```python
# Vor: Stub (ADR-080 v1)
step_results.append(_make_step(
    step_id="developer_implement",
    role=AgentRole.DEVELOPER,
    status=WorkflowStatus.WAITING_APPROVAL,   # ← Stub
    output={"message": "Gate 1: human executes."},
))

# Nach: Autonome Ausführung (ADR-082 Phase 1)
if AUTONOMOUS_FEATURES.developer_implement:
    _step_result = _executor.run(
        handoff=_initial_handoff,
        step_id="developer_implement",
    )
    step_results.append(_make_step(
        step_id="developer_implement",
        role=AgentRole.DEVELOPER,
        status=WorkflowStatus.SUCCESS if _step_result.success else WorkflowStatus.FAILED,
        output=_step_result.to_output_dict(),
    ))
else:
    step_results.append(_make_step(          # ← Fallback: unverändert
        step_id="developer_implement",
        role=AgentRole.DEVELOPER,
        status=WorkflowStatus.WAITING_APPROVAL,
        output={"message": "Gate 1: human executes."},
    ))
```

### 5.8 AuditStore-Schema (Erweiterung)

Jeder autonome Step schreibt einen `ExecutionTrace`:

```python
@dataclass
class ExecutionTrace:
    """Vollständiger Audit-Trail eines autonomen Agent-Steps (ADR-082)."""

    trace_id: str                    # UUID
    workflow_id: str                 # Referenz auf WorkflowResult
    step_id: str
    role: AgentRole
    handoff_in_id: str               # Referenz auf eingehenden AgentHandoff
    handoff_out_id: str | None       # Referenz auf ausgehenden AgentHandoff

    # LLM-Trace
    model_used: str
    prompt_hash: str                  # SHA-256(system_prompt + user_message)
    tool_calls: list[ToolCallTrace]   # Jeder Tool-Call mit Args + Result
    token_usage: TokenUsage
    cost_usd: float
    duration_ms: int

    # Ergebnis
    artifacts_written: list[str]      # Pfade aller geschriebenen Dateien
    scope_violations_caught: int      # Durch ScopeLock verhinderte Writes
    success: bool
    error: str | None
    timestamp: datetime
```

---

## 6. Implementierungsstruktur

```
orchestrator_mcp/agent_team/
├── execution/                        ← NEU (ADR-082)
│   ├── __init__.py
│   ├── executor.py                   # StepExecutor
│   ├── llm_client.py                 # LLMClient + Provider-Implementierungen
│   ├── tool_registry.py              # ToolRegistry + alle Tools
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── file_tools.py             # FileReadTool, FileWriteTool
│   │   ├── shell_tool.py             # ShellTool (Allowlist)
│   │   ├── git_tools.py              # GitDiffTool, GitCommitTool
│   │   └── search_tool.py            # SearchTool (ripgrep-basiert)
│   ├── budget.py                     # ExecutionBudget
│   ├── audit.py                      # AuditLogger, ExecutionTrace
│   └── config.py                     # AutonomousFeatures, Feature-Flags
│
├── tests/
│   ├── test_executor.py              ← NEU
│   ├── test_tool_registry.py         ← NEU
│   ├── test_execution_budget.py      ← NEU
│   └── test_workflows_autonomous.py  ← NEU
│
├── workflows.py                      ← amends (Feature-Flag-Integration)
├── handoff.py                        ← unverändert
├── models.py                         ← ExecutionTrace hinzufügen
└── ...
```

---

## 7. Migrationsstrategie (3 Phasen)

### Phase 1 — Developer + Re-Engineer autonom (v1)

**Ziel:** Die beiden Code-intensivsten Stub-Steps werden autonom.

| Step | Tool-Set | Model-Tier | Komplexität |
|------|----------|------------|-------------|
| `developer_implement` | read_file, write_file (src/), search_code, git_diff | STANDARD | SIMPLE/MODERATE Tasks |
| `re_engineer_root_cause` | read_file, write_file (src/), search_code, run_shell (linter) | STANDARD | nach Test-Failure |

**Guard:** Nur für `complexity in (SIMPLE, MODERATE)` und `risk_level in (LOW, MEDIUM)`.
COMPLEX/ARCHITECTURAL und HIGH/CRITICAL bleiben auf WAITING_APPROVAL.

### Phase 2 — Tech Lead autonom (v2)

**Ziel:** Design-Reviews und Code-Reviews werden autonom.

| Step | Tool-Set | Model-Tier |
|------|----------|------------|
| `tech_lead_design` | read_file, search_code, git_diff | HIGH_REASONING |
| `tech_lead_review` | read_file, search_code, git_diff | HIGH_REASONING |

**Guard:** Nur für Tasks ohne `requires_human_review=True` im eingehenden Handoff.

### Phase 3 — Planner LLM-Decompose (v3, amends ADR-080 §5.5)

**Ziel:** `Planner._llm_decompose()` ersetzt rule-based Zerlegung für dynamische Sub-Tasks.

**Guard:** Nur für `complexity == ARCHITECTURAL`. Rule-based bleibt Fallback.

---

## 8. Sicherheitsmodell

### Prinzip: Defense-in-Depth (4 Ebenen)

```
Ebene 1: Feature-Flag          — Step ist per Default WAITING_APPROVAL
Ebene 2: Complexity-Guard      — Nur SIMPLE/MODERATE für Developer autonom
Ebene 3: ScopeLock (ADR-081)   — Schreibende Tool-Calls gegen erlaubte Pfade validiert
Ebene 4: ExecutionBudget        — Hard-Limit auf Token + Cost pro Run
```

### Verbotene Operationen (immer, unabhängig von Feature-Flags)

- `git push` — niemals autonom
- `git reset --hard` ohne vorherigen `_get_snapshot_hash()` — bereits durch ADR-080 Fix 5 verhindert
- Schreiben in `ALWAYS_FORBIDDEN_PATHS` (ADR-081 §5.6) — durch ScopeLock verhindert
- Shell-Befehle außerhalb der Allowlist — durch ShellTool-Allowlist verhindert
- Secrets/Credentials lesen oder schreiben — durch ForbiddenPatterns in FileWriteTool

### Shell-Allowlist (Phase 1)

```python
SHELL_ALLOWLIST: frozenset[str] = frozenset({
    "pytest", "python -m pytest",
    "ruff check", "ruff format",
    "mypy",
    "git diff", "git status", "git add", "git log",
    "grep", "rg",
    "cat", "head", "tail",
})
```

---

## 9. Konsequenzen

### Positiv

- **Vollautonome Coding-Tasks** für SIMPLE/MODERATE Tasks ohne menschliches Eingreifen (Phase 1)
- **Strukturierter Audit-Trail** — jeder LLM-Call ist nachvollziehbar und reproduzierbar
- **Bestehende Guardrails bleiben erhalten** — keine Änderung an ADR-081
- **Schrittweise Migration** — Feature-Flags ermöglichen sichere Einführung
- **Provider-Flexibilität** — Modell-Wechsel ohne Code-Änderung

### Negativ / Risiken

| Risiko | Wahrscheinlichkeit | Mitigierung |
|--------|-------------------|-------------|
| LLM schreibt fehlerhaften Code | Mittel | Tester-Step bleibt real; Rollback-Engine greift |
| Budget-Überschreitung | Niedrig | Hard-Limit in ExecutionBudget; L3-Rollback |
| ScopeLock-Bypass durch Symlinks | Niedrig | `realpath()` in FileWriteTool vor Pfad-Check |
| Prompt-Injection via Codeinhalte | Niedrig | System-Prompt-Trennung; kein direktes Code-Echo im Prompt |
| Nicht-deterministische LLM-Outputs | Mittel | `temperature=0.0`; Tester-Verifikation |

### Neue Abhängigkeiten

- `openai>=1.0` (oder `httpx` für direkte API-Calls) — LLMClient
- `tiktoken` — Token-Counting vor LLM-Call
- Kein neues Framework — alle anderen Deps bereits vorhanden

---

## 10. Offene Fragen

| Frage | Entscheidung |
|-------|-------------|
| Welcher LLM-Provider wird zuerst integriert? | **OpenAI** via `OrchestratorLLMAdapter` wrapping `DynamicLLMClient` (creative-services) |
| Soll `git commit` autonom erlaubt sein? | **Ja** — nur staged files via `GitStageTool` (ScopeLock-validiert), nur auf `ai/<type>/<task_id>`-Branch |
| Wie werden LLM-API-Keys sicher verwaltet? | **`.env`** — `OPENAI_API_KEY` etc., niemals im Code |
| Soll Phase 1 einen Dry-Run-Modus haben? | **Ja** — `DRY_RUN=true` loggt Tool-Calls ohne Ausführung |
| Welche Mindest-Test-Coverage für autonomen Code? | **80%** auf neue Dateien — Guardian + Tester-Step verifizieren |

---

## 11. Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-02-25 | Achim Dehnert | v0: Initial Draft — LLM-Execution-Layer, Tool-Registry, Feature-Flags, 3-Phasen-Migration |
| 2026-02-25 | Cascade | v1: Accepted — Review-Blocker B1–B5 implementiert und verifiziert (216 Tests grün, commit 2eddd3d) |
