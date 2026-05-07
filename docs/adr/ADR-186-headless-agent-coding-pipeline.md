---
status: draft
date: 2026-05-07
version: 1.0
decision-makers: [Achim Dehnert]
consulted: []
informed: []
supersedes: []
amends: [ADR-141]
related: [ADR-066, ADR-068, ADR-077, ADR-080, ADR-081, ADR-082, ADR-116, ADR-141, ADR-156, ADR-177, ADR-185]
implementation_status: none
staleness_months: 6
drift_check_paths:
  - orchestrator_mcp/agents/
  - scripts/headless_agent/
  - .github/workflows/_headless-agent.yml
tags: [agent-coding, headless, devin, orchestrator, refactoring, quality-assurance, testing, polyrepo]
---

# ADR-186: Headless Agent-Coding Pipeline — Orchestrator-gesteuerte Polyrepo-Automatisierung

**Devin CLI als Headless-Frontend, Orchestrator als Steuerungsschicht, Platform-Guardrails als Safety-Net.**

## Versionshistorie

| Version | Datum | Änderungen |
|---------|-------|------------|
| 1.0 | 2026-05-07 | Erstentwurf — Architektur, Use Cases, Gate-Modell, Implementierungsplan |

---

## 1. Kontext & Problemstellung

### Das Cascade-Dilemma

Cascade/Windsurf ist die primäre IDE für agentic coding auf der IIL-Plattform. Die Agent-Infrastruktur ist ausgereift:

- **Orchestrator MCP** (ADR-066): Developer, Guardian, Tester, Planner, Merger — 6 aktive Agent-Rollen
- **Agent Role Specialization** (ADR-177): DocBot, TestBot, FeatureBot, ReEngineerBot, ArchitectBot — 5 spezialisierte Agents mit deterministischem Routing
- **Guardrails** (ADR-081): ScopeLock, PreExecution, PostVerify, Rollback L1-L4
- **LLM-Routing** (ADR-116): DB-driven Model-Selection mit Budget-Tracking
- **REFLEX** v0.5.0: Deterministische ADR-Compliance über 19 Repos
- **pgvector Memory**: Persistente Sessions, Error-Patterns, Repo-Context

**Problem**: Diese gesamte Infrastruktur ist **IDE-gebunden**. Es gibt keinen Weg, sie programmtisch von außen zu triggern — kein CLI, kein API, kein Headless-Modus. Konsequenzen:

| Szenario | Heute | Gewünscht |
|----------|-------|-----------|
| Nightly Quality-Sweep über 19 Repos | ❌ Unmöglich | ✅ Cron-Job, 03:00 UTC |
| PR-spezifischer semantischer Code-Review | ❌ Manuell in IDE | ✅ GitHub Actions Gate |
| Batch-Refactoring (z.B. Service-Layer-Migration) | ❌ Repo-für-Repo in IDE | ✅ Ein Script, N Repos |
| Automatisierte Test-Generierung für uncovered Code | ❌ Manuell pro Modul | ✅ Coverage-Diff → Testcases |
| Cross-Repo-Konsistenz-Check (über Pattern-Matching hinaus) | ❌ Nur REFLEX (Regex/AST) | ✅ LLM-semantisch + REFLEX |

### ADR-141 Gap

ADR-141 (Discord → Agentic Coding Bridge) definiert einen StepExecutor-basierten Agent, der Code via Celery-Tasks schreibt und PRs öffnet. **Problem**: ADR-141 baut die gesamte Execution-Engine selbst (StepExecutor + ToolRegistry + LLMClient). Das ist ein enormer Implementierungsaufwand (~19h) und dupliziert Fähigkeiten, die Devin Terminal bereits als fertiges Produkt mitbringt.

### Devin Terminal als Beschleuniger

Devin CLI (`devin -p`) bietet:

- **Headless Single-Turn-Modus**: Prompt → Antwort → Exit (wie `grep` oder `ruff`)
- **Nativer Zugriff auf `.windsurf/rules/*.md`**: Alle bestehenden Cascade-Rules gelten automatisch
- **MCP-Server-Integration**: Kann MCP-Server als Tools nutzen
- **Permission-Modes**: `bypass` (Headless), `autonomous` (Sandbox), `normal` (interaktiv)
- **Strukturierte Outputs**: JSON-Output per Prompt-Engineering erzwingbar

**Die Kernidee**: Devin CLI als **Execution-Frontend** nutzen, aber die **Steuerungslogik** (Routing, Guardrails, Memory, Audit) im Orchestrator belassen.

---

## 2. Entscheidungskriterien (Decision Drivers)

- **Orchestrator-Hoheit**: LLM-Routing, Budget-Tracking und Gate-System bleiben im Orchestrator (ADR-066, ADR-116, ADR-177) — kein Parallel-System
- **Guardrails-Konsistenz**: ScopeLock (ADR-081) muss auch im Headless-Modus greifen
- **Kosteneffizienz**: LLM-Kosten müssen trackbar und budgetierbar sein
- **Polyrepo-Skalierung**: Muss über 19+ Repos in Batch-Läufen funktionieren
- **DSGVO-Compliance**: Mandanten-Code darf nicht unkontrolliert an externe Cloud-Inferenz
- **Inkrementelle Adoption**: Kein Big-Bang — stufenweise aktivierbar pro Use Case
- **Reversibilität**: Jeder Schritt muss rückgängig machbar sein ohne Datenverlust

---

## 3. Betrachtete Optionen

### Option A: ADR-141 StepExecutor (Custom-Build)

Alles selbst bauen: Git-Clone → StepExecutor → LLMClient → PR.

- **Pro**: Volle Kontrolle, kein externer Vendor
- **Contra**: ~19h Aufwand, dupliziert Devin-Fähigkeiten, kein Codebase-Verständnis ohne Indexierung

### Option B: Devin CLI standalone (wie im devin.zip Bundle)

Devin CLI direkt mit eigenen Prompts und eigenem JSON-Parsing aufrufen.

- **Pro**: Schnell aufgesetzt, sofort nutzbar
- **Contra**: Umgeht Orchestrator komplett — kein LLM-Routing, kein Budget, kein Memory, keine Guardrails

### Option C: Devin CLI + Orchestrator-Bridge ✅

Devin CLI als Execution-Frontend, Orchestrator als Steuerungsschicht:

```
Orchestrator (Routing + Guards + Memory + Audit)
    ↓ wählt Agent-Typ, Modell, Budget, Scope
    ↓ baut Prompt mit Platform-Context
Devin CLI (Execution)
    ↓ devin -p --model {routed_model} -- {enriched_prompt}
    ↓ führt Code-Analyse/Refactoring/Test-Generierung aus
Orchestrator (Verification + Storage)
    ↓ parsed Output, prüft ScopeLock, speichert in pgvector
    ↓ öffnet PR / erstellt Issue / sendet Discord-Notification
```

- **Pro**: Nutzt bestehende Orchestrator-Infrastruktur UND Devins Code-Verständnis, schnellste Time-to-Value
- **Contra**: Abhängigkeit von Devin-Vendor (mitigierbar: Devin ist austauschbar durch jedes CLI-Tool)

### Option D: GitHub Actions + LLM direkt (ohne Devin)

Eigener GH-Actions-Workflow, der litellm/aifw direkt aufruft.

- **Pro**: Kein Vendor-Lock-in
- **Contra**: Kein Codebase-Indexing, kein File-System-Zugriff im Runner, limitierte Kontextfenster

### Option E: Aider CLI als Alternative zu Devin

Open-Source-CLI-Agent (aider) statt Devin.

- **Pro**: Open Source, kein Vendor-Lock-in, günstig
- **Contra**: Kein nativer Zugriff auf `.windsurf/rules/`, kein MCP-Support, weniger Codebase-Verständnis

---

## 4. Entscheidung

**Option C: Devin CLI + Orchestrator-Bridge** — mit Fallback auf Option E (Aider) als Exit-Strategie.

### Begründung

1. **Kein Parallel-System**: Orchestrator (ADR-066) bleibt die Single Source of Truth für Routing, Budget und Guardrails
2. **Time-to-Value**: Devin CLI ist sofort nutzbar — kein StepExecutor-Build nötig
3. **Rule-Kompatibilität**: Devin liest `.windsurf/rules/*.md` nativ — keine Doppelpflege
4. **Austauschbarkeit**: Die Bridge-Schicht abstrahiert das CLI-Tool — Devin kann durch Aider, Claude Code CLI oder jedes andere Tool ersetzt werden
5. **Amends ADR-141**: Die Headless-Pipeline ersetzt den Custom-StepExecutor aus ADR-141 durch ein Vendor-CLI + Orchestrator-Bridge-Pattern

---

## 5. Architektur

### 5.1 Komponentenübersicht

```
┌─────────────────────────────────────────────────────────────────┐
│                    TRIGGER LAYER                                 │
│  Cron │ GitHub Actions │ Discord /code │ CLI manual              │
└──────────────┬──────────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────────┐
│                 ORCHESTRATOR LAYER (mcp-hub)                     │
│                                                                  │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────────────┐  │
│  │ TaskRouter    │  │ BudgetGuard   │  │ ContextBuilder       │  │
│  │ (ADR-177)     │  │ (ADR-116)     │  │ (platform-context +  │  │
│  │ select_agent()│  │ $-Limit/Task  │  │  pgvector Memory)    │  │
│  └──────┬───────┘  └───────┬───────┘  └──────────┬───────────┘  │
│         │                  │                      │              │
│         ▼                  ▼                      ▼              │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │              HeadlessBridge                                  │ │
│  │  - Baut enriched Prompt (Context + Rules + Task)            │ │
│  │  - Mappt ModelTier → Devin --model Flag                     │ │
│  │  - Ruft CLI auf (subprocess, timeout, cwd=repo)             │ │
│  │  - Parsed JSON-Output                                       │ │
│  │  - Prüft ScopeLock (ADR-081) auf changed files              │ │
│  └──────────────────────────┬──────────────────────────────────┘ │
│                             │                                    │
│  ┌──────────────┐  ┌───────┴───────┐  ┌──────────────────────┐  │
│  │ AuditStore   │  │ ResultHandler │  │ MemoryStore          │  │
│  │ (ADR-068)    │  │ PR / Issue /  │  │ (pgvector)           │  │
│  │              │  │ Discord / Log │  │                      │  │
│  └──────────────┘  └───────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────────┐
│                  EXECUTION LAYER (austauschbar)                   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │  Devin CLI (Primary)                                      │    │
│  │  devin -p --model {model} --permission-mode bypass -- ... │    │
│  └──────────────────────────────────────────────────────────┘    │
│                          ODER                                    │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │  Aider CLI (Fallback)                                     │    │
│  │  aider --model {model} --message "..." --yes              │    │
│  └──────────────────────────────────────────────────────────┘    │
│                          ODER                                    │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │  Claude Code CLI (Future)                                 │    │
│  │  claude -p "..." --model {model} --allowedTools ...       │    │
│  └──────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 HeadlessBridge — Kern-Abstraktion

```python
from __future__ import annotations

import subprocess
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

log = logging.getLogger("headless-bridge")


class CLIBackend(str, Enum):
    """Austauschbare CLI-Backends."""
    DEVIN = "devin"
    AIDER = "aider"
    CLAUDE = "claude"


@dataclass(frozen=True)
class HeadlessTask:
    """Input für einen Headless-Agent-Run."""
    repo_path: Path
    task_type: str          # TaskType aus ADR-177
    description: str
    scope_paths: list[str]  # Erlaubte Pfade (ScopeLock Allowlist)
    budget_usd: float = 5.0
    timeout_seconds: int = 900  # 15 Min Default


@dataclass
class HeadlessResult:
    """Strukturiertes Ergebnis eines Headless-Runs."""
    repo: str
    task_type: str
    success: bool
    findings: list[dict[str, Any]] = field(default_factory=list)
    changes: list[dict[str, Any]] = field(default_factory=list)
    tests_generated: list[str] = field(default_factory=list)
    error: str | None = None
    cost_usd: float = 0.0
    model_used: str = ""
    session_id: str | None = None


class CLIAdapter(ABC):
    """Abstraktion über CLI-Backends — Devin, Aider, Claude Code."""

    @abstractmethod
    def execute(
        self,
        prompt: str,
        repo_path: Path,
        model: str,
        timeout: int,
    ) -> tuple[str, str | None]:
        """Execute prompt, return (stdout, error)."""
        ...


class DevinAdapter(CLIAdapter):
    """Devin CLI via subprocess."""

    def execute(self, prompt, repo_path, model, timeout):
        cmd = [
            "devin", "-p",
            "--model", model,
            "--permission-mode", "bypass",
            "--", prompt,
        ]
        try:
            result = subprocess.run(
                cmd, cwd=repo_path,
                capture_output=True, text=True,
                timeout=timeout, check=False,
            )
            if result.returncode != 0:
                return "", f"Exit {result.returncode}: {result.stderr[:500]}"
            return result.stdout, None
        except subprocess.TimeoutExpired:
            return "", f"Timeout after {timeout}s"
        except FileNotFoundError:
            return "", "devin binary not found in PATH"


class AiderAdapter(CLIAdapter):
    """Aider CLI als Fallback-Backend."""

    def execute(self, prompt, repo_path, model, timeout):
        cmd = [
            "aider",
            "--model", model,
            "--message", prompt,
            "--yes",          # Non-interactive
            "--no-git",       # Wir managen Git selbst
        ]
        try:
            result = subprocess.run(
                cmd, cwd=repo_path,
                capture_output=True, text=True,
                timeout=timeout, check=False,
            )
            return result.stdout, None if result.returncode == 0 else result.stderr[:500]
        except subprocess.TimeoutExpired:
            return "", f"Timeout after {timeout}s"
```

### 5.3 ModelTier → CLI-Model Mapping

Der Orchestrator routet nach ADR-177. Die Bridge übersetzt:

```python
# Orchestrator ModelTier → Devin --model Flag
TIER_TO_DEVIN_MODEL: dict[str, str] = {
    "gpt_low":  "haiku-4.5",       # Docs, Typos, Lint
    "swe":      "swe-1.6",         # Features, Bugfixes, Refactor
    "opus":     "opus-4.7",        # Architecture, Security, ADR
}

# Fallback: Orchestrator ModelTier → Aider --model Flag
TIER_TO_AIDER_MODEL: dict[str, str] = {
    "gpt_low":  "anthropic/claude-haiku-4-5-20251001",
    "swe":      "anthropic/claude-sonnet-4-6-20260217",
    "opus":     "anthropic/claude-opus-4-6-20260205",
}
```

### 5.4 Gate-Modell (konsistent mit ADR-066)

| Use Case | Gate | Automatisierung | Approval |
|----------|------|----------------|----------|
| Read-only Quality-Sweep (Findings only) | Gate 0 | Vollautomatisch | Keine |
| Test-Generierung (neuer Code) | Gate 1 | Automatisch + Notification | User wird informiert |
| Refactoring (bestehender Code ändern) | Gate 2 | Vorbereitet, Branch + PR | Human-Review vor Merge |
| Cross-Repo-Batch-Refactoring | Gate 3 | Vorbereitet, je 1 PR/Repo | Explizite Freigabe pro Repo |
| Security-Patches | Gate 2 | Branch + PR | Human-Review vor Merge |

**Invariante**: Headless-Pipeline darf **niemals** direkt auf `main` pushen — immer Branch + PR.

---

## 6. Use Cases im Detail

### 6.1 Nightly Quality-Sweep (Gate 0 — Read-only)

```
Cron 03:00 UTC → headless_sweep.py
    for repo in PLATFORM_REPOS:
        1. Orchestrator: select_agent(task_type="quality_sweep") → DocBot + gpt_low
        2. ContextBuilder: platform-context + REFLEX-Baseline + letzte Error-Patterns
        3. HeadlessBridge: devin -p "Semantic quality check, return JSON findings"
        4. ResultHandler: Findings → pgvector Memory + Markdown-Report
        5. Vergleich mit REFLEX-Baseline: nur semantische Delta-Findings reporten
    Aggregat-Summary → Discord #quality-reports
```

**Output**: JSON + Markdown pro Repo, aggregierte Summary. **Kein Code-Change.**

**Mehrwert über REFLEX hinaus**:
- "Diese View delegiert an `_helper()` die ORM-Calls macht" (REFLEX: ✅, da kein direkter `Model.objects` in View)
- "Diese Migration ist nicht blue-green-safe wegen concurrent index lock" (REFLEX: kann Index-Locking nicht analysieren)
- "Dieser Service hat 3 Verantwortlichkeiten — SRP-Verstoß" (REFLEX: kein Semantic-Understanding)

### 6.2 Automatisierte Test-Generierung (Gate 1)

```
Trigger: Coverage-Report zeigt Module < 80%
    1. Orchestrator: select_agent(task_type="test") → TestBot + gpt_low
    2. ContextBuilder: Coverage-Diff + bestehende Test-Patterns + Factories
    3. HeadlessBridge: devin -p "Generate tests for uncovered paths in {module}"
    4. ScopeLock: Nur tests/**/*.py darf geschrieben werden
    5. Guardian: ruff + pytest auf generierte Tests
    6. ResultHandler: Branch test/auto-{date} → PR
    7. Discord: "🧪 Auto-Tests für {repo}: +12 Tests, Coverage 74% → 83%"
```

**ScopeLock-Config für Test-Generierung**:
```python
SCOPE_TEST_GEN = {
    "allow": ["tests/**/*.py", "apps/*/tests/**/*.py", "conftest.py"],
    "deny": ["apps/*/models.py", "apps/*/views.py", "apps/*/services.py",
             "migrations/**", ".env*", "docker-compose*", "Dockerfile*"],
}
```

### 6.3 Batch-Refactoring (Gate 2)

```
Trigger: Manuell oder Issue mit Label [headless-refactor]
    Beispiel: "Migriere alle repos von unique_together auf UniqueConstraint"
    1. Orchestrator: select_agent(task_type="refactor") → ReEngineerBot + swe
    2. Für jedes Repo:
        a. ContextBuilder: Repo-spezifische Models + ADR-Referenz
        b. HeadlessBridge: devin -p "Refactor unique_together → UniqueConstraint"
        c. ScopeLock: Nur models.py + migrations darf geändert werden
        d. Guardian: ruff + django check + migrate --check
        e. Tester: pytest
        f. Branch refactor/unique-constraint-{date} → PR
    3. Discord: "🔧 Batch-Refactoring: 14/19 Repos → PRs erstellt"
```

### 6.4 PR-spezifischer semantischer Code-Review (Gate 0)

```yaml
# .github/workflows/semantic-review.yml
on:
  pull_request:
    paths: ['apps/**/*.py']

jobs:
  semantic-review:
    runs-on: self-hosted
    steps:
      - uses: actions/checkout@v4
      - name: Run semantic review
        run: |
          python scripts/headless_agent/pr_review.py \
            --pr-diff "$(gh pr diff ${{ github.event.number }})" \
            --repo ${{ github.repository }} \
            --output-format github-comment
      - name: Post review comment
        # ... posts findings as PR comment
```

### 6.5 Cross-Repo-Konsistenz-Analyse (Gate 0)

```
Trigger: Wöchentlich oder nach ADR-Update
    "Prüfe ob alle 19 Repos ADR-177 Agent-Naming-Konventionen einhalten"
    1. Für jedes Repo:
        HeadlessBridge: "Check compliance with ADR-177 naming, return JSON"
    2. Aggregation: Matrix-Report {Repo × Standard → ✅/❌}
    3. Delta zu letzter Woche: nur neue Violations reporten
    4. pgvector: Trend-Daten für Governance-Dashboard
```

### 6.6 Automatisierte Security-Analyse (Gate 2)

```
Trigger: Nightly oder nach dependency-Update
    1. Orchestrator: select_agent(task_type="security") → ArchitectBot + opus
    2. HeadlessBridge: "Analyze authentication flows, session handling,
       CSRF patterns — focus on semantic vulnerabilities that bandit misses"
    3. Findings → Issue mit Label [security-review]
    4. Bei critical: Discord @achim + E-Mail
```

---

## 7. DSGVO & Code-Souveränität

| Aspekt | Risiko | Mitigation |
|--------|--------|------------|
| **Code an Cognition Cloud** | HOCH bei Mandanten-Code | Repo-Allowlist: nur eigene Repos, keine Mandanten-Repos |
| **Prompt-Inhalte** | MITTEL | Keine personenbezogenen Daten in Prompts, nur Code-Patterns |
| **Output-Speicherung** | GERING | Findings in eigenem pgvector, nicht bei Cognition |
| **Exit-Strategie** | — | Aider-Fallback benötigt keine externe Cloud (eigener API-Key) |

### Repo-Klassifikation

```python
class RepoClassification(str, Enum):
    OWN_CODE = "own_code"           # Eigener Code → Headless erlaubt
    MANDANT_CODE = "mandant_code"   # Mandanten-Code → nur lokale Inferenz
    SENSITIVE = "sensitive"          # Trading, Billing → nur manuell

HEADLESS_ALLOWED: dict[str, RepoClassification] = {
    "travel-beat": RepoClassification.OWN_CODE,
    "coach-hub": RepoClassification.OWN_CODE,
    "risk-hub": RepoClassification.OWN_CODE,
    "dev-hub": RepoClassification.OWN_CODE,
    "weltenhub": RepoClassification.OWN_CODE,
    "bfagent": RepoClassification.OWN_CODE,
    "pptx-hub": RepoClassification.OWN_CODE,
    "mcp-hub": RepoClassification.OWN_CODE,
    # ...
    "trading-hub": RepoClassification.SENSITIVE,  # IBKR-Code → kein Headless
}
```

---

## 8. Kosten-Modell

### Kosten pro Use Case

| Use Case | Modell | Tokens/Repo | $/Repo | $/Monat (19 Repos, 1×/Woche) |
|----------|--------|-------------|--------|-------------------------------|
| Quality-Sweep | gpt_low (Haiku) | ~8K | ~$0.01 | ~$0.76 |
| Test-Generierung | gpt_low (Haiku) | ~15K | ~$0.02 | ~$1.52 |
| Refactoring | swe (Sonnet) | ~25K | ~$0.20 | ~$15.20 |
| Security-Analyse | opus | ~20K | ~$0.80 | ~$60.80 |
| PR-Review | swe (Sonnet) | ~10K | ~$0.08 | ~$6.08 (angenommen 20 PRs/Woche) |

**Geschätzte Gesamtkosten**: ~$85/Monat bei vollem Betrieb.

### Budget-Guards (ADR-116)

```python
HEADLESS_BUDGET_LIMITS = {
    "quality_sweep": 0.50,      # $0.50 pro Sweep (alle Repos)
    "test_generation": 1.00,    # $1.00 pro Batch
    "refactoring": 5.00,        # $5.00 pro Refactoring-Run
    "security_analysis": 10.00, # $10.00 pro Security-Sweep
    "pr_review": 0.50,          # $0.50 pro PR
}
```

Hard-Stop bei Budget-Überschreitung → `BudgetExceededError` → Discord-Alert.

---

## 9. Implementierungsplan

| Phase | Inhalt | Aufwand | Abhängig von |
|-------|--------|---------|-------------|
| **0** | ADR-186 finalisieren | 1h | — |
| **1** | `CLIAdapter`-Abstraktion + `DevinAdapter` + `AiderAdapter` | 3h | Devin CLI installiert |
| **2** | `HeadlessBridge` mit Orchestrator-Integration (Routing, Budget, Context) | 4h | Phase 1 |
| **3** | Quality-Sweep-Script (`headless_sweep.py`) — Gate 0, read-only | 2h | Phase 2 |
| **4** | Cron-Setup + Discord-Notification für Sweep-Results | 1h | Phase 3 |
| **5** | Test-Generator (`headless_test_gen.py`) — Gate 1, ScopeLock tests-only | 3h | Phase 2 |
| **6** | PR-Review-Integration (`pr_review.py`) + GitHub Actions Workflow | 3h | Phase 2 |
| **7** | Batch-Refactoring-Engine (`headless_refactor.py`) — Gate 2 | 4h | Phase 2 |
| **8** | pgvector-Audit + Trend-Dashboard-Daten | 2h | Phase 3 |
| **9** | Validierung: 2 Wochen Pilotbetrieb auf 3 Repos | — | Phase 4-6 |

**Gesamt: ~23h über 4-5 Sessions.**

### Pilot-Repos

1. **dev-hub** — niedrigstes Risiko, 0 REFLEX-Findings, gute Test-Coverage
2. **coach-hub** — mittlere Komplexität, gute CI-Gates
3. **risk-hub** — höhere Komplexität, domänenspezifischer Code

### Rollout

| Woche | Aktivität |
|-------|-----------|
| 1 | Phase 1-3: Bridge + Quality-Sweep auf dev-hub |
| 2 | Phase 4-5: Cron + Test-Generator auf dev-hub + coach-hub |
| 3 | Phase 6-7: PR-Review + Refactoring auf Pilot-Repos |
| 4 | Phase 8-9: Audit + Validierung, Rollout auf alle OWN_CODE Repos |

---

## 10. Sicherheits-Gates

| Gate | Mechanismus | ADR-Referenz |
|------|------------|--------------|
| **Repo-Allowlist** | `HEADLESS_ALLOWED` Dict — nur klassifizierte Repos | ADR-186 §7 |
| **Branch-Protection** | Agent pusht nur `headless/{use-case}/{date}` — nie `main` | ADR-081 |
| **ScopeLock** | Per-Use-Case Scope-Config: Test-Gen darf nur tests/ schreiben | ADR-081 |
| **Budget-Guard** | Hard-Stop pro Use-Case-Kategorie | ADR-116 |
| **DSGVO-Klassifikation** | `SENSITIVE` und `MANDANT_CODE` Repos sind gesperrt | ADR-186 §7 |
| **Guardian-Verification** | ruff + bandit + pytest auf jeden Output | ADR-066 |
| **Human-Review** | Gate 2+ → PR mit manueller Review-Pflicht | ADR-066 |
| **Audit-Trail** | Jeder Run → pgvector Memory + AuditStore | ADR-068 |
| **Kill-Switch** | `HEADLESS_ENABLED=false` in Orchestrator-Config → sofort aus | — |

---

## 11. Abgrenzung

- **Kein Ersatz für Cascade** — interaktive IDE-Arbeit bleibt in Cascade
- **Kein Auto-Merge** — PRs werden immer manuell reviewed (Gate 2+)
- **Kein Prod-Zugriff** — Agent arbeitet nur mit Git, nie mit laufenden Containern
- **Kein Ersatz für REFLEX** — REFLEX bleibt für deterministische Pattern-Checks, Headless-Pipeline für semantische Analyse
- **Kein eigener LLM-Stack** — LLM-Routing über Orchestrator (ADR-116/177), nicht über Devin-eigenes Routing
- **Scope Phase 1**: Quality-Sweep + Test-Generierung — kein Multi-File-Refactoring
- **Devin CLI ist austauschbar** — CLIAdapter-Abstraktion erlaubt Backend-Wechsel

---

## 12. Vergleichsmatrix: Headless-Pipeline vs. Bestand

| Fähigkeit | REFLEX | Cascade | Headless-Pipeline (ADR-186) |
|-----------|--------|---------|----------------------------|
| Deterministisch | ✅ | — | ❌ (LLM-basiert) |
| Semantisches Verständnis | ❌ | ✅ | ✅ |
| Headless/Batch | ❌ | ❌ | ✅ |
| Polyrepo-Sweep | ✅ (schnell) | ❌ | ✅ (langsamer, tiefer) |
| Kosten | $0 | IDE-Lizenz | ~$85/Monat |
| Guardrails | Eigene Rules | Orchestrator | Orchestrator (identisch) |
| Memory/Context | ❌ | pgvector | pgvector (identisch) |
| Code-Änderungen | ❌ | ✅ | ✅ (Gate 1+) |
| Test-Generierung | ❌ | ✅ (manuell) | ✅ (automatisch) |

---

## 13. Confirmation

| Kriterium | Messung |
|-----------|---------|
| Quality-Sweep findet ≥ 3 semantische Findings die REFLEX nicht findet | Manueller Vergleich nach Phase 3 |
| Test-Generator erhöht Coverage um ≥ 5% auf Pilot-Repos | `coverage report` pre/post |
| Budget-Guard verhindert Überschreitung bei 100% der Runs | AuditStore-Query |
| ScopeLock blockiert Out-of-Scope-Änderungen bei 100% der Runs | Testcase |
| CLIAdapter-Wechsel (Devin → Aider) funktioniert ohne Orchestrator-Änderung | Integrations-Test |
| Headless-Pipeline ist per Kill-Switch deaktivierbar | Config-Test |

---

## 14. Open Questions

| # | Frage | Status | Kontext |
|---|-------|--------|---------|
| Q1 | Devin CLI Lizenzkosten bei Headless-Nutzung? | Offen | Pricing-Modell für `bypass`-Mode unklar |
| Q2 | Aider als gleichwertiger Fallback — oder nur Notfall? | Offen | Evaluierung in Phase 9 |
| Q3 | pgvector Disk-Space für Trend-Daten (Nightly × 19 Repos × 365 Tage)? | Offen | Retention-Policy definieren |
| Q4 | Soll PR-Review in CI blocking sein oder nur Comment? | Offen | Abhängig von False-Positive-Rate |
| Q5 | Temporal-Integration für Long-Running-Refactorings? | Deferred | Wie ADR-177 §Temporal |

---

## 15. Deferred Decisions

| Entscheidung | Begründung | Zieldatum |
|--------------|------------|-----------|
| RL-basiertes Routing für Headless-Tasks | Erst nach 3+ Monaten AuditStore-Daten | 2026-Q4 |
| Cloud-Delegation (Devin Cloud) | DSGVO-Klärung für Mandanten-Code pending | 2026-Q3 |
| Parallel-Execution über Repos | Requires Temporal (ADR-077) | 2026-Q4 |
| Custom Devin Skills für Platform-Standards | Evaluieren nach Phase 9 Erfahrung | 2026-Q3 |

---

## 16. References

- **ADR-066** — AI Engineering Squad (Gate-System, Agent-Rollen)
- **ADR-068** — AuditStore (Logging-Pflicht)
- **ADR-077** — Catalog & Temporal
- **ADR-080** — Multi-Agent Coding Team Pattern
- **ADR-081** — Agent Guardrails & Code Safety (ScopeLock)
- **ADR-082** — LLM Tool Integration & Autonomous Coding (StepExecutor)
- **ADR-116** — Dynamic Model Router (Budget-Tracking)
- **ADR-141** — Discord → Agentic Coding Bridge (amended: Execution via CLI statt Custom-StepExecutor)
- **ADR-156** — Job Duration Estimation
- **ADR-177** — Agent Role Specialization (5 Bots, deterministisches Routing)
- **ADR-185** — Deploy Agent Pattern (Gate-controlled Deployments)
- **REFLEX** v0.5.0 — Deterministische ADR-Compliance
- Devin Terminal CLI — cli.devin.ai
- Aider — aider.chat (Open-Source CLI Agent)
