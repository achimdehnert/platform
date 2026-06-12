---
status: proposed
date: 2026-05-07
version: 1.3
decision-makers: [Achim Dehnert]
consulted: [Cascade]
informed: []
supersedes: []
amends: [ADR-141]
related: [ADR-045, ADR-059, ADR-066, ADR-068, ADR-075, ADR-077, ADR-081, ADR-116, ADR-138, ADR-177]
implementation_status: partial
implementation_evidence:
  - "mcp-hub orchestrator_mcp/headless/ — Phase 1 (CLI adapters, bridge, services, 44 tests)"
last_reviewed: 2026-06-10
staleness_months: 6
drift_check_paths:
  - orchestrator_mcp/headless/
tags: [agent-coding, headless, aifw, agent-loop, orchestrator, quality-assurance, testing, polyrepo]
---

# ADR-186: Use Unified Agent Loop on aifw for Headless Coding Pipeline

> **Provenienz-Hinweis (2026-06-10):** Diese Datei ist der Playback der in mcp-hub
> weiterentwickelten v1.3 (`mcp-hub/docs/adr/ADR-186-headless-agent-coding-pipeline.md`,
> Commit `1e6ce04`). Die hier zuvor liegende v1.2 entschied „Devin CLI + Orchestrator-Bridge"
> und widersprach damit der tatsächlich implementierten Architektur. Kanonische Heimat
> dieser Entscheidung ist ab jetzt wieder platform; die mcp-hub-Kopie ist als
> non-canonical gebannert.

## Versionshistorie

| Version | Datum | Änderungen |
|---------|-------|------------|
| 1.0 | 2026-05-07 | Erstentwurf — Architektur, Use Cases, Gate-Modell, Implementierungsplan |
| 1.1 | 2026-05-07 | Review-Fixes: Titel als Decision Statement, Consequences-Sektion, Glossar, Secret-Management, catalog-info.yaml, ADR-075-Klassifikation |
| 1.2 | 2026-05-08 | Status draft→proposed, CLI-Backend-Entscheidung: Aider Primary, Devin optional |
| 1.3 | 2026-05-07 (mcp-hub) / 2026-06-10 (platform-Playback) | **Architektur-Reversal:** Unified Agent Loop auf aifw als Primary, CLI-Adapter (Claude Code/Devin/Aider) nur Fallback. Löst die v1.2-Blocker: Live-Budget-Abort, Inline-ScopeLock, ein Routing für alle Konsumenten. Der Re-Eval-Trigger aus dem ADR-Full-Scan 2026-06-06 (Devin-Vendor-Bindung) ist damit aufgelöst. |

---

## Context and Problem Statement

The platform requires autonomous code quality enforcement across 19+ repos.
Manual Cascade sessions don't scale for recurring tasks (sweeps, test gen,
refactoring). We need a headless pipeline that invokes AI coding agents
without human interaction, with proper budget control, scope locking, and
security isolation.

**Critical architectural insight (v1.3)**: CLI-based agents (Claude Code,
Devin, Aider) are opaque subprocesses. We lose cost control mid-run,
ScopeLock is only post-hoc, and model routing is fragmented across three
parallel systems. The unified Agent Loop built on aifw solves all three.

## Decision Drivers

- Autonomous nightly quality sweeps across all platform repos
- Budget control to prevent runaway costs — **live, not post-hoc**
- Security: no secret leakage to AI subprocesses
- Scope isolation: agents can only modify allowed files — **inline, not after**
- Vendor independence: **any model via aifw** (any known/sensible LLM provider)
- Central LLM routing: **one config for all consumers** (Django, headless, CI)
- Full observability: **every token, every tool call logged**

## Considered Options

1. **Devin CLI as primary** — Cognition's managed agent, opaque subprocess
2. **Aider CLI as primary** — Open-source, but CLI = black box
3. **Claude Code CLI as primary** — Anthropic-official, best CLI but still opaque
4. **Unified Agent Loop on aifw** — Full control, transparent, vendor-independent

## Decision Outcome

**Chosen: Option 4 — Unified Agent Loop on aifw, with CLI adapters as fallback.**

### Why not CLI-primary (v1.2 approach)?

| Problem | CLI Adapter | Unified Loop |
|---------|-------------|--------------|
| Model routing | 3 parallel worlds (aifw, litellm, CLI-internal) | ONE aifw router |
| Cost tracking | estimated post-hoc | exact, token-for-token, live abort |
| ScopeLock | post-execution validation | **inline at every tool call** |
| Observability | stdout parsing (fragile) | every step in audit log |
| Vendor lock-in | Claude CLI = Anthropic only | any model via aifw |
| Free tier (Groq) | needs separate adapter | just a routing config |
| Testability | subprocess mocking | pure Python unit tests |

### Pros and Cons of the Options

#### Option 1: Devin CLI as primary

- Good: Managed cloud sandbox (no local infra)
- Good: Multi-file refactoring across complex codebases
- Bad: Opaque subprocess — no live cost control
- Bad: Vendor lock-in (Cognition)
- Bad: `DEVIN_API_TOKEN` required (additional secret management)
- Bad: No native `.windsurf/rules` reading (BLOCKER-1)

#### Option 2: Aider CLI as primary

- Good: Open-source, GDPR-compliant (own API keys)
- Good: Local execution (no cloud dependency)
- Bad: Opaque subprocess — stdout parsing for results
- Bad: No tool-use loop (commit-oriented, not analysis-oriented)
- Bad: Limited to Anthropic/OpenAI models

#### Option 3: Claude Code CLI as primary

- Good: Officially supported by Anthropic
- Good: `--allowedTools` for defense-in-depth
- Good: `--output-format json` documented and stable
- Bad: Still opaque subprocess — no live budget abort
- Bad: Vendor lock-in (Anthropic only)
- Bad: ScopeLock only post-execution (worktree discard on violation)

#### Option 4: Unified Agent Loop on aifw (chosen)

- Good: Full cost control — live abort mid-generation
- Good: Inline ScopeLock — tool rejects forbidden writes before they happen
- Good: Vendor-independent — any model via aifw routing config
- Good: Full observability — every token and tool call logged
- Good: Pure Python — testable without subprocess mocking
- Good: Free-tier capable (Groq, Ollama) for read-only tasks
- Bad: aifw requires refactoring to extract DB-independent core (prerequisite)
- Bad: Own tool implementations need maintenance
- Bad: May be less capable than Claude Code for very complex multi-file tasks

### Architecture v1.3

```
┌──────────────────────────────────────────────────────────────┐
│                    aifw (erweitert — CLI + HTTP + Python)      │
│                                                              │
│  ┌───────────────────────────────────────────────────────┐   │
│  │  Routing Engine (DB-driven OR yaml fallback)           │   │
│  │  action_code → provider + model + budget + fallback    │   │
│  └─────────┬─────────────┬──────────────┬────────────────┘   │
│            │             │              │                     │
│  ┌─────────┴──┐  ┌──────┴────┐  ┌──────┴─────┐  ┌───────┐  │
│  │ Anthropic  │  │   OpenAI  │  │  Groq FREE │  │Ollama │  │
│  └────────────┘  └───────────┘  └────────────┘  └───────┘  │
└──────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│              Agent Loop (orchestrator_mcp/headless)            │
│                                                              │
│   while budget.remaining > 0:                                │
│     response = aifw.complete(                                │
│       action_code = task.action_code,                        │
│       messages = conversation,                               │
│       tools = SCOPED_TOOLS,         ← ScopeLock built-in    │
│     )                                                        │
│     budget.spend(response.usage)    ← live cost tracking    │
│     if budget.exceeded: ABORT       ← immediate, not later  │
│                                                              │
│     for tool_call in response.tool_calls:                    │
│       result = sandbox.execute(tool_call)  ← scope-checked  │
│       audit.log(tool_call, result)         ← full trace     │
│                                                              │
│   Tools (scope-aware, sandbox-aware):                        │
│   ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌─────────┐  │
│   │  Read  │ │  Edit  │ │  Grep  │ │  Bash  │ │RunTests │  │
│   │  File  │ │  File  │ │ Search │ │(allow) │ │ (pytest)│  │
│   └────┬───┘ └────┬───┘ └────┬───┘ └────┬───┘ └────┬────┘  │
│        └───────────┴──────────┴──────────┴──────────┘        │
│                           │                                  │
│   ┌───────────────────────┴──────────────────────────────┐   │
│   │  Sandbox (git worktree) + ScopeLock (inline reject)   │   │
│   └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘

                    FALLBACK (complex tasks only)
                           │
              ┌────────────┼────────────┐
         ┌────┴────┐  ┌───┴────┐  ┌────┴────┐
         │  Claude  │  │ Devin  │  │  Aider  │
         │Code CLI │  │  CLI   │  │   CLI   │
         └─────────┘  └────────┘  └─────────┘
```

### Routing Decision

```
IF task.complexity <= moderate AND task.type in (sweep, review, test_gen, docs):
    → Agent Loop (aifw + Tools)
    → Full control, full transparency
    → Model: Groq FREE (read-only) or Claude Sonnet (write)

ELIF task.complexity == complex AND needs multi-file deep reasoning:
    → Claude Code CLI (subprocess fallback)
    → For 50+ file refactoring where Claude's toolchain excels

ELIF task.requires_cloud_sandbox:
    → Devin CLI (cloud VM for dependency installation)
```

### aifw Extension Required

```
aifw/ (erweitert)
├── core/
│   ├── engine.py          # CompletionEngine (DB-unabhängig)
│   ├── routing.py         # Route: DB-driven OR yaml OR env
│   ├── cost.py            # Token counting + budget enforcement
│   └── tool_use.py        # Tool-call dispatch + schema
├── django/                # Bestehende Django-Integration
│   └── integration.py     # sync_completion() wrapper
├── cli/                   # NEU: python -m aifw complete
│   └── __main__.py
├── http/                  # NEU: aifw serve --port 8099
│   └── server.py
└── providers/
    ├── anthropic.py
    ├── openai.py
    ├── groq.py            # NEU (free tier)
    └── ollama.py          # NEU (local/private)
```

### Key Blocker Fixes (from external review, still valid)

| # | Issue | Fix |
|---|-------|-----|
| B1 | CLI doesn't read `.windsurf/rules` | System prompt contains platform rules |
| B2 | Devin CLI flag syntax wrong | Corrected (fallback adapter only) |
| B3 | ScopeLock after execution too late | **Tool rejects write inline** |
| B4 | Full os.environ passed to subprocess | env_isolation (fallback only) |
| B5 | Repo allowlist not enforced | DB-backed check before loop starts |
| B6 | `text=True` without error handling | Not applicable (no subprocess in primary) |
| B7 | Finding duplication across runs | content_hash + UniqueConstraint dedup |

## Implementation

Location: `mcp-hub/orchestrator_mcp/headless/`

```
headless/
├── __init__.py
├── models.py                  # SQLAlchemy models (4 tables)
├── agent_loop/                # PRIMARY — eigener Tool-Use Loop
│   ├── __init__.py
│   ├── loop.py                # AgentLoop: while budget > 0
│   ├── tools/                 # Scope-aware tool implementations
│   │   ├── read_file.py
│   │   ├── edit_file.py       # ScopeLock inline
│   │   ├── grep_search.py
│   │   ├── bash_exec.py       # Command allowlist
│   │   └── run_tests.py
│   └── routing.py             # Task → action_code → aifw
├── adapters/                  # FALLBACK — CLI für komplexe Tasks
│   ├── __init__.py            # CLIAdapter ABC + DTOs
│   ├── claude.py              # Claude Code CLI
│   ├── devin.py               # Devin CLI
│   └── aider.py               # Aider CLI
├── services/
│   ├── bridge.py              # HeadlessBridge orchestrator (dispatches)
│   ├── sandbox.py             # Git worktree + subprocess management
│   ├── env_isolation.py       # Subprocess env allowlist (fallback only)
│   ├── scope_lock.py          # ADR-081 ScopeLock (inline + post-hoc)
│   ├── cost_tracker.py        # Atomic budget reservation (row locks)
│   ├── prompt_builder.py      # Anti-injection prompt assembly
│   └── result_parser.py       # JSON output validation
└── tests/
    ├── test_agent_loop.py
    ├── test_tools.py
    ├── test_adapters.py
    ├── test_env_isolation.py
    ├── test_prompt_builder.py
    ├── test_result_parser.py
    └── test_scope_lock.py
```

### Agent Loop — Tool Interface

```python
class Tool(ABC):
    name: str
    description: str
    parameters: dict  # JSON Schema

    @abstractmethod
    def execute(self, args: dict, sandbox: Sandbox) -> ToolResult:
        """Execute tool within sandbox. ScopeLock enforced HERE."""
        ...

class EditFileTool(Tool):
    name = "edit_file"

    def execute(self, args, sandbox):
        path = args["path"]
        if not sandbox.scope.allows_write(path):
            return ToolError(f"ScopeLock: write to '{path}' denied")
        sandbox.write(path, args["new_content"])
        return ToolSuccess(f"Written {len(args['new_content'])} bytes")
```

### Database Tables

- `headless_repo_allowlist` — repo whitelist with classification + kill-switch
- `headless_runs` — audit log for every pipeline execution
- `headless_findings` — deduplicated semantic findings (content_hash)
- `headless_budgets` — per-category budget with atomic reservation

### Security Model

1. **Inline ScopeLock**: Tool rejects forbidden writes before they happen
2. **Worktree Sandbox**: Disposable git worktree, discarded on violation
3. **Live Budget Abort**: Loop stops immediately when budget exceeded
4. **Prompt Hardening**: Delimiter-based user input isolation + injection detection
5. **Atomic Budget**: `SELECT FOR UPDATE` row locks prevent race conditions
6. **Repo Allowlist**: DB-backed, classification-aware (own_code only)
7. **Env Isolation**: Only for CLI fallback adapters (HARD_DENY frozenset)

### Confirmation

Compliance with this ADR is verified by:

1. **Unit tests**: `orchestrator_mcp/headless/tests/` — all pass in CI (44 tests)
2. **ScopeLock enforcement**: Integration test proves tool rejects forbidden writes
3. **Budget abort**: Test confirms loop exits when budget exceeded mid-run
4. **Audit log**: Every `headless_runs` entry has full trace (status, cost, duration)
5. **Nightly sweep metrics**: Discord weekly report shows finding count + cost per repo
6. **REFLEX rule**: `headless.no_direct_litellm` — blocks direct litellm usage in headless/

### Model Routing (via aifw)

| action_code | Default Model | Fallback | Budget |
|-------------|---------------|----------|--------|
| `quality_sweep` | `groq/llama-3.3-70b` | `claude-haiku` | $0 (free) |
| `pr_review` | `groq/llama-3.3-70b` | `claude-haiku` | $0 (free) |
| `docstring_gen` | `groq/llama-3.3-70b` | `claude-haiku` | $0 (free) |
| `test_generation` | `claude-sonnet-4-6` | `groq/llama-70b` | $0.50/run |
| `refactoring` | `claude-sonnet-4-6` | — | $1.00/run |
| `security_audit` | `claude-sonnet-4-6` | — | $0.50/run |
| `complex_refactor` | Claude Code CLI (fallback) | — | $5.00/run |

## Consequences

### Positive

- **One routing config for ALL consumers** — Django, headless, CI, MCP
- Autonomous nightly quality enforcement across all 19 repos at **$0 cost** (Groq)
- Live budget abort — never overspend
- Inline ScopeLock — impossible to write to forbidden paths
- Full observability — every token, every tool call in audit log
- Vendor-independent — swap model via config, not code
- Pure Python — testable without subprocess mocking

### Negative

- aifw requires refactoring to extract DB-independent core
- Own tool implementations need maintenance
- Tool-use loop may be less capable than Claude Code for very complex tasks

### Neutral

- CLI adapters remain as fallback (not wasted, just demoted)
- Git worktree sandbox shared between both paths
- Groq free tier has rate limits (30 req/min) — sufficient for nightly sweeps

## Open Questions

1. **aifw Core-Extraction scope**: Should aifw's DB-independent engine be a
   separate ADR (ADR-187)? Decision deferred until Phase 2 starts.
   → Preliminary answer: Yes, aifw CLI/HTTP extension warrants its own ADR.
2. **Complexity threshold for CLI fallback**: What defines "moderate" vs. "complex"?
   → Preliminary: >20 files changed OR >3 interdependent modules = complex → CLI fallback.
3. **Temporal integration**: Should the Agent Loop be wrapped in a Temporal workflow
   for durability and retry? → Phase 1: No. Runs synchronously. Re-evaluate in Phase 5.
4. **Nightly sweep scheduling**: GitHub Actions cron or Temporal schedule?
   → Decision: GitHub Actions scheduled workflow (ADR-075 compliance: write-ops via Actions).
5. **API key rotation**: How are `GROQ_API_KEY`, `ANTHROPIC_API_KEY` rotated?
   → Managed via SOPS (ADR-045), rotated quarterly, stored in org-level secrets.

## Implementation Plan

| Phase | Deliverable | Effort |
|-------|-------------|--------|
| 1 (done) | CLI adapters + bridge + services + tests | ✅ complete |
| 2 | aifw core extraction (DB-independent engine) | 4h |
| 3 | aifw CLI mode (`python -m aifw complete`) | 2h |
| 4 | Groq provider in aifw routing | 1h |
| 5 | Agent Loop + scope-aware tools | 6h |
| 6 | Integration: bridge dispatches to loop vs. CLI | 2h |
| 7 | Nightly sweep cron + Discord reporting | 3h |

## Glossary

- **action_code**: aifw routing key mapping task → model + provider + budget
- **Agent Loop**: Own tool-use loop built on aifw — full control, no external CLI
- **aifw**: Platform-internes LLM-Gateway (Python import, CLI, HTTP) — zentrale Schnittstelle für alle LLM-Aufrufe
- **CLI**: Command-Line Interface — Kommandozeilenprogramm
- **content_hash**: SHA256 aus Identitätsfeldern eines Findings zur Deduplizierung
- **HARD_DENY**: Frozenset von Umgebungsvariablen die niemals an Subprozesse weitergegeben werden dürfen
- **LLM**: Large Language Model — KI-Sprachmodell (z.B. Claude, GPT, Llama)
- **MCP**: Model Context Protocol — Orchestrator-Protokoll für Tool-Aufrufe und Kontext-Management
- **ORM**: Object-Relational Mapping — Abstraktion für Datenbankzugriffe (hier: SQLAlchemy)
- **ScopeLock**: ADR-081 Mechanismus zur Einschränkung erlaubter Dateimodifikationen (inline bei jedem Tool-Call)
- **SOPS**: Secrets OPerationS — Verschlüsselungstool für Secrets in Repositories (ADR-045)
- **Worktree**: Git-Feature für parallele Arbeitsverzeichnisse (isolierte Sandbox)

## More Information

- **catalog-info.yaml**: The `headless` component will be registered in mcp-hub's
  `catalog-info.yaml` once Phase 5 (Agent Loop) is complete (ADR-077 compliance).
- **aifw extension**: Phases 2–4 affect aifw package — a separate ADR-187 will be
  created when that work starts (scope separation).
- **Nightly sweep**: Triggered via GitHub Actions scheduled workflow (ADR-075: write-ops
  via Actions, not MCP). Agent Loop runs synchronously, no Temporal in Phase 1.

## References

- ADR-045: Secrets Management (SOPS)
- ADR-059: Drift-Detector
- ADR-066: AI Engineering Squad (Gate-System, Agent-Rollen)
- ADR-068: Audit Trail
- ADR-075: infra-deploy (write-ops via GitHub Actions)
- ADR-077: Service Catalog (catalog-info.yaml)
- ADR-081: ScopeLock
- ADR-116: Budget Tracking
- ADR-138: Implementation Tracking
- ADR-141: Discord → Agentic Coding Bridge (amended: Execution via Agent Loop statt Custom-StepExecutor)
- ADR-177: Agent Role Specialization / Model Tiers
- External Review: `mcp-hub/docs/ADR-186-PLAYBOOK.md` + Review-Historie (33 findings, 7 blockers fixed)
- aifw: `github.com/achimdehnert/aifw`
