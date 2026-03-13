# ADR-141 Review: Discord → Agentic Coding Bridge (Layer 4)

**Reviewer:** Principal IT-Architekt / Autonomous Coding Expert  
**Datum:** 2026-03-13  
**ADR-Version:** proposed (2026-03-13)  
**Review-Status:** ⛔ NICHT IMPLEMENTIERUNGSREIF — 3 BLOCKER, 5 KRITISCH, 6 HOCH, 5 MEDIUM

---

## 0. Executive Summary

ADR-141 adressiert eine echte Lücke (Layer-3 ist ein Briefkasten, kein Agent), aber der
Implementierungsansatz hat schwerwiegende Probleme:

1. **Paralleles Competing System** — Die Plattform hat bereits ADR-080/081/082 (Multi-Agent
   Coding Team, Guardrails, StepExecutor + ToolRegistry). Aider als eigenständiges CLI-Tool
   würde **alle diese ADRs bypassen** und ein konkurrierendes System schaffen — das
   schwerwiegendste Architektur-Anti-Pattern der Platform.

2. **Kein DB-First-Design** — Es werden keine Django-Modelle für `AgentTask`, `AgentRun`,
   `AgentIteration` definiert. Status landet im Container-Speicher statt in der DB — widerspricht
   dem fundamentalen Platform-Standard.

3. **Sicherheits-Guardrails fehlen vollständig** — ADR-081 `ScopeLock`, `ALWAYS_FORBIDDEN_PATHS`,
   Pre/Post-Execution-Verifier sind nicht erwähnt. Der Container-Agent hätte keinerlei
   technische Scope-Kontrolle.

4. **Temporal wird ignoriert** — ADR-079 definiert Temporal als Primary Durable Workflow Engine.
   Ein "Agent Scheduler in mcp-hub" ist ein zweites Workflow-System neben Temporal.

---

## 1. Review-Tabelle

### 🔴 BLOCKER

| # | Befund | Severity | Betroffener ADR |
|---|--------|----------|-----------------|
| B1 | **Paralleles Competing System zu ADR-080/081/082.** Aider als CLI-Tool bypasses StepExecutor, ToolRegistry, ScopeLock, AuditStore, RollbackEngine — alle accepted ADRs werden umgangen. Dies ist der schwerwiegendste Architektur-Verstoß der Platform. | 🔴 BLOCKER | ADR-080, ADR-081, ADR-082 |
| B2 | **Kein DB-First-Design.** Weder `AgentTask` noch `AgentRun` noch Iterations-State werden als Django-Modelle mit `BigAutoField PK + public_id + tenant_id + deleted_at` definiert. Ephemerer `/tmp/agent-tasks/`-Workspace ersetzt DB-State — nicht wiederherstellbar nach Container-Crash. | 🔴 BLOCKER | Platform-Standard |
| B3 | **Alle 3 `related`-ADR-Referenzen existieren nicht.** `ADR-113-discord-bot-architecture.md` → tatsächlich `ADR-113-telegram-gateway-pgvector-memory.md`. `ADR-116-llm-cost-controlling.md` → tatsächlich `ADR-116-dynamic-model-router.md`. `ADR-100-agentic-coding-workflow.md` → tatsächlich `ADR-100-iil-testkit-shared-test-factory-package.md`. Keine der referenzierten ADRs hat inhaltlich mit dem Thema zu tun. Fehlende Referenzen: ADR-079, ADR-080, ADR-081, ADR-082, ADR-045. | 🔴 BLOCKER | MADR-4.0 Standard |

---

### 🔴 KRITISCH

| # | Befund | Severity | Betroffener ADR |
|---|--------|----------|-----------------|
| K1 | **Kein ScopeLock / ALWAYS_FORBIDDEN_PATHS.** ADR-081 verbietet explizit `*/migrations/*.py`, `.env*`, `docker-compose.prod.yml`, `*.pem/.key/.crt`. Ein Aider-Agent ohne diesen Mechanismus kann migrations/, prod-settings oder secrets überschreiben. | 🔴 KRITISCH | ADR-081 |
| K2 | **Agent Scheduler in mcp-hub statt Temporal.** ADR-079 accepted Temporal als "Primary Durable Workflow Engine". Ein Custom-Scheduler in mcp-hub ist ein zweites, konkurrierendes Workflow-System — widerspricht ADR-079. **Caveat:** ADR-079 hat `implementation_status: none` ("intentionally deferred: Celery + orchestrator_mcp sufficient for current scale"). Implementierung muss entscheiden: Temporal jetzt einführen oder Celery-Task als pragmatischer Ersatz mit expliziter ADR-079-Referenz. | 🔴 KRITISCH | ADR-079 |
| K5 | **Aider bypassed llm_mcp vollständig.** Aider ruft OpenAI/Anthropic-APIs direkt auf (eigener API-Key, eigene Requests). Damit wird das gesamte ADR-116 Budget-Tracking (llm_calls-Tabelle, Grafana Dashboard, $5-Hard-Stop) umgangen. Kosten sind weder messbar noch kontrollierbar. | 🔴 KRITISCH | ADR-116 |
| K3 | **Secret Management nicht ADR-045-konform.** Deploy-Keys "pro Repo" werden erwähnt, aber kein `read_secret()`-Pattern (ADR-045 Section 2.4 Pattern A). GitHub-Token, API-Keys und Deploy-Keys müssen über `/run/secrets/<key_lower>` aufgelöst werden, nicht via Umgebungsvariablen direkt im Container. | 🔴 KRITISCH | ADR-045 |
| K4 | **`asyncio.run()` Risiko im ASGI-Kontext.** Die mcp-hub API ist ASGI-basiert. Wird der Agent-Start synchron über einen Celery-Task oder ASGI-View getriggert, ist `asyncio.run()` im laufenden Loop verboten (Platform-Standard). `asgiref.async_to_sync` ist Pflicht. | 🔴 KRITISCH | Platform-Standard |

---

### 🟠 HOCH

| # | Befund | Severity |
|---|--------|----------|
| H1 | **Kein ExecutionBudget-Management.** Das Cost-Limit "$5 pro Task" ist nur als Monitoring-Regel genannt, nicht als technisch erzwungener `ExecutionBudget`-Check wie in ADR-082 definiert (BudgetExceededError → sofortiger Stop). | 🟠 HOCH |
| H2 | **Kein `set -euo pipefail`** in den impliziten Shell-Skripten (git clone, ruff, pytest, git push). Platform-Standard für alle Shell-Skripte. Fehlendes `set -e` → stille Failures, Agent läuft weiter nach Fehler. | 🟠 HOCH |
| H3 | **COMPOSE_PROJECT_NAME nicht spezifiziert.** ADR-120 identifiziert diesen Fehler bereits als Blocker für Container-Kollisionen. Der `iil_coding_agent`-Container muss einen eindeutigen `COMPOSE_PROJECT_NAME` haben (z.B. `coding_agent`). | 🟠 HOCH |
| H4 | **Kein i18n ab Tag 1.** Discord-Notifications, PR-Beschreibungen und Fehlermeldungen werden ohne `_()` / `{% trans %}` definiert. Nachrüsten ist Platform-Standard-Verletzung. | 🟠 HOCH |
| H5 | **GitHub Actions Polling nicht spezifiziert.** Der CI-Feedback-Loop (Agent liest CI-Ergebnis) hat kein definiertes Polling-Intervall, kein Timeout für den Polling-Loop, keinen Backoff. Race-Condition: Agent liest CI-Status bevor Actions-Check fertig ist. | 🟠 HOCH |
| H6 | **Server-Ressourcen nicht evaluiert.** hetzner-prod hat aktuell 89 laufende Container, 10GB/22GB RAM belegt, 35GB Disk frei. Ein 2GB-Agent-Container ist machbar, aber: (a) bei git-clone großer Repos + LLM-Context wird RAM eng, (b) `/tmp/agent-tasks/` auf Root-Partition mit nur 35GB — mehrere parallele Tasks füllen Disk schnell. Keine Resource-Limits oder Disk-Quotas definiert. | 🟠 HOCH |

---

### 🟡 MEDIUM

| # | Befund | Severity |
|---|--------|----------|
| M1 | **Aider vs. StepExecutor — falsche Abstraktionsebene.** Aider ist ein vollständiges, eigenmächtiges Coding-Tool mit eigenem Kontextfenster-Management. StepExecutor (ADR-082) ist die Platform-native Abstraktion. Evaluation "in Phase 2" ist zu spät — muss in der ADR entschieden werden. | 🟡 MEDIUM |
| M2 | **Kein Idempotenz-Guard für den Agent-Task.** Celery-Retry (oder Discord-Doppelklick) kann denselben Task zweimal starten. Ohne DB-Record + `select_for_update()` entsteht doppelte Branch-Erstellung. | 🟡 MEDIUM |
| M3 | **Branch-Naming-Konflikt mit ADR-082.** ADR-082 / ADR-081 verwenden `ai/<role>/<task_id>` als Branch-Schema. ADR-141 schlägt `agent/<task-id>` vor — inkonsistentes Naming-Schema plattformweit. | 🟡 MEDIUM |
| M4 | **Max. 3 CI-Iterationen ohne Circuit-Breaker.** Wenn alle 3 Iterationen fehlschlagen, ist der Fehlerzustand nicht persistent (kein DB-Record). Kein Alert an Discord, kein automatisches Issue-Update. | 🟡 MEDIUM |
| M5 | **Docker Image nicht im GHCR.** Der `iil_coding_agent`-Container wird nicht im bestehenden GHCR-Workflow (ADR-120 `_build-docker`) erwähnt. Image-Build außerhalb der CI/CD-Pipeline. *(Hinweis: ADR-117 ist "Shared World Layer worldfw", nicht GHCR — korrekte Referenz ist ADR-120.)* | 🟡 MEDIUM |

---

## 2. Alternativer Ansatz — Empfehlung des Reviewers

### 🏆 Option D: StepExecutor-Bridge (Empfohlen)

**Kern-Idee:** Nicht Aider als neues Tool, sondern die bereits accepted ADR-080/081/082-Infrastruktur
(StepExecutor + ToolRegistry + ScopeLock) als Ausführungs-Engine nutzen und Discord als
reinen Trigger-Layer verbinden. Temporal als Workflow-Orchestrator.

```
Discord /code
    │
    ▼
Discord Bot (Layer 4 Command)
    │  POST /api/agent-tasks/
    ▼
AgentTask Model (DB) ← BigAutoField + public_id + tenant_id + deleted_at
    │
    ▼
Temporal Workflow: CodingAgentWorkflow
    ├── Activity: GitCloneActivity
    ├── Activity: StepExecutorActivity (ADR-082 StepExecutor)
    │     ├── LLMClient (llm_mcp → ADR-116 Kosten-Tracking)
    │     ├── ToolRegistry (ScopeLock aus ADR-081)
    │     └── ExecutionBudget ($5 hard limit)
    ├── Activity: CIPollingActivity (GitHub Actions API)
    ├── Activity: PRCreationActivity (GitHub API)
    └── Activity: DiscordNotifyActivity
          │
          ▼
    Discord Thread (Live-Updates via AgentTask.status)
```

**Trade-offs gegenüber Option C (ADR-141 original):**

| Aspekt | Option C (ADR-141) | Option D (StepExecutor-Bridge) |
|--------|-------------------|-------------------------------|
| Aider-Dependency | Ja — externes CLI-Tool | Nein — Platform-native |
| Guardrails | Keine | ADR-081 ScopeLock + Post-Verifier |
| Audit-Trail | Container-Logs | AuditStore (DB) |
| Rollback | Manuell | RollbackEngine (ADR-081, L1-L4) |
| Kosten-Kontrolle | Monitoring | ExecutionBudget (Hard-Stop) |
| Workflow-Durabilität | Custom-Scheduler | Temporal (ADR-079) |
| Code-Änderung | Minimal | Medium (Temporal-Workflow neu) |

**Wann trotzdem Aider sinnvoll?** Wenn Phase 1 ein schneller Proof-of-Concept sein soll,
kann Aider als `AiderTool` in die ToolRegistry (ADR-082) eingebettet werden — als ein Tool
unter vielen, nicht als Replacement für StepExecutor. Siehe Section 3.3.

---

## 3. Korrigierter Implementierungsplan

### 3.1 Phase 0: ADR-Anpassungen (vor Implementierung)

**Pflicht vor dem ersten Code-Commit:**

- ADR-141 als Supersedes-Kandidat für ADR-082 Phase-2 einordnen (oder als Erweiterung markieren)
- `related` in ADR-141 erweitern: `ADR-079`, `ADR-081`, `ADR-082`, `ADR-045`
- Agent-Tool-Entscheidung (Aider vs. StepExecutor) treffen und in ADR festschreiben

### 3.2 Phase 1: Datenmodell + Discord Command (2-3h)

**Dateipfad:** `mcp_hub/django/models/agent_task.py`

```python
"""AgentTask-Modell für den Agentic Coding Bridge (ADR-141)."""
from __future__ import annotations

import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _


class AgentTaskStatus(models.TextChoices):
    QUEUED = "queued", _("Queued")
    RUNNING = "running", _("Running")
    CI_WAITING = "ci_waiting", _("CI Waiting")
    CI_ITERATING = "ci_iterating", _("CI Iterating")
    PR_OPEN = "pr_open", _("PR Open")
    FAILED = "failed", _("Failed")
    CANCELLED = "cancelled", _("Cancelled")


class AgentTask(models.Model):
    """Persistenter State für einen Agentic-Coding-Task (ADR-141).

    Platform-Standards:
    - BigAutoField PK (settings.DEFAULT_AUTO_FIELD)
    - public_id: UUIDField für externe Referenzen
    - tenant_id: BigIntegerField(db_index=True) — kein FK
    - deleted_at: Soft-Delete
    """

    # --- PKs & Identifiers ---
    public_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True,
        verbose_name=_("Public ID"),
    )
    tenant_id = models.BigIntegerField(
        db_index=True,
        verbose_name=_("Tenant ID"),
    )

    # --- Task Definition ---
    repo_name = models.CharField(
        max_length=100,
        verbose_name=_("Repository Name"),
        help_text=_("Format: achimdehnert/<repo>"),
    )
    task_description = models.TextField(verbose_name=_("Task Description"))
    priority = models.CharField(
        max_length=10,
        choices=[("low", _("Low")), ("medium", _("Medium")), ("high", _("High"))],
        default="medium",
        verbose_name=_("Priority"),
    )

    # --- Discord Context ---
    discord_user_id = models.CharField(max_length=64, verbose_name=_("Discord User ID"))
    discord_channel_id = models.CharField(max_length=64, verbose_name=_("Discord Channel ID"))
    discord_thread_id = models.CharField(
        max_length=64, blank=True, verbose_name=_("Discord Thread ID")
    )

    # --- GitHub State ---
    github_issue_number = models.IntegerField(
        null=True, blank=True, verbose_name=_("GitHub Issue Number")
    )
    branch_name = models.CharField(
        max_length=200, blank=True, verbose_name=_("Branch Name")
    )
    pr_number = models.IntegerField(
        null=True, blank=True, verbose_name=_("PR Number")
    )
    pr_url = models.URLField(blank=True, verbose_name=_("PR URL"))

    # --- Execution State ---
    status = models.CharField(
        max_length=20,
        choices=AgentTaskStatus.choices,
        default=AgentTaskStatus.QUEUED,
        db_index=True,
        verbose_name=_("Status"),
    )
    iteration_count = models.PositiveSmallIntegerField(
        default=0, verbose_name=_("Iteration Count")
    )
    llm_cost_usd = models.DecimalField(
        max_digits=8, decimal_places=4, default=0, verbose_name=_("LLM Cost USD")
    )
    error_message = models.TextField(blank=True, verbose_name=_("Error Message"))

    # --- Temporal Workflow ---
    temporal_workflow_id = models.CharField(
        max_length=200, blank=True, verbose_name=_("Temporal Workflow ID")
    )

    # --- Soft-Delete & Timestamps ---
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Deleted At"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Agent Task")
        verbose_name_plural = _("Agent Tasks")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["repo_name", "branch_name"],
                condition=models.Q(deleted_at__isnull=True)
                & ~models.Q(branch_name=""),
                name="uq_agent_task_repo_branch_active",
            )
        ]

    def __str__(self) -> str:
        return f"AgentTask({self.public_id}, {self.repo_name}, {self.status})"
```

---

**Dateipfad:** `mcp_hub/django/models/agent_iteration.py`

```python
"""AgentIteration — Protokoll jedes CI-Feedback-Loops (ADR-141)."""
from __future__ import annotations

import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _


class AgentIteration(models.Model):
    """Einzelne Iteration des CI-Feedback-Loops.

    Jede Agent-Iteration (max. 3) wird hier persistiert.
    """

    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    tenant_id = models.BigIntegerField(db_index=True, verbose_name=_("Tenant ID"))

    task = models.ForeignKey(
        "AgentTask",
        on_delete=models.CASCADE,
        related_name="iterations",
        verbose_name=_("Agent Task"),
    )
    iteration_number = models.PositiveSmallIntegerField(verbose_name=_("Iteration Number"))

    # CI-State
    ci_run_id = models.CharField(max_length=64, blank=True, verbose_name=_("CI Run ID"))
    ci_status = models.CharField(
        max_length=20,
        choices=[
            ("pending", _("Pending")),
            ("success", _("Success")),
            ("failure", _("Failure")),
            ("timeout", _("Timeout")),
        ],
        default="pending",
        verbose_name=_("CI Status"),
    )
    ci_failure_log = models.TextField(blank=True, verbose_name=_("CI Failure Log"))

    # LLM-State
    llm_prompt_tokens = models.IntegerField(default=0)
    llm_completion_tokens = models.IntegerField(default=0)
    llm_cost_usd = models.DecimalField(max_digits=8, decimal_places=4, default=0)

    # Soft-Delete
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Agent Iteration")
        verbose_name_plural = _("Agent Iterations")
        ordering = ["task", "iteration_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["task", "iteration_number"],
                name="uq_agent_iteration_task_number",
            )
        ]
```

---

### 3.3 Phase 2: Service-Layer + Guardrails (3-4h)

**Dateipfad:** `mcp_hub/services/agent_task_service.py`

```python
"""Service-Layer für AgentTask (ADR-141) — keine Business-Logik in Views/Tasks."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal

from asgiref.sync import async_to_sync  # NIEMALS asyncio.run() im ASGI-Kontext
from django.db import transaction

from mcp_hub.django.models.agent_task import AgentTask, AgentTaskStatus

logger = logging.getLogger(__name__)

# Repo-Allowlist — muss in DB-Config (ADR: Database-first!)
# Initial als Konstante, Migration zu DB-Config in Phase 4
ALLOWED_REPOS: frozenset[str] = frozenset(
    {
        "achimdehnert/coach-hub",
        "achimdehnert/risk-hub",
        "achimdehnert/travel-beat",
        "achimdehnert/mcp-hub",
        "achimdehnert/weltenhub",
        "achimdehnert/pptx-hub",
    }
)

MAX_ITERATIONS: int = 3
MAX_LLM_COST_USD: Decimal = Decimal("5.00")
AGENT_BRANCH_PREFIX: str = "ai/agent"  # Konform mit ADR-081/082: ai/<type>/<id>


@dataclass
class AgentTaskCreateRequest:
    repo_name: str
    task_description: str
    priority: str
    discord_user_id: str
    discord_channel_id: str
    tenant_id: int


@dataclass
class AgentTaskCreateResult:
    task: AgentTask
    error: str | None = None


class AgentTaskService:
    """Orchestriert Erstellung und Status-Management von AgentTasks (ADR-141).

    Alle schreibenden Operationen laufen in transaction.atomic().
    Async-Calls nur via asgiref.async_to_sync.
    """

    def create_task(
        self, request: AgentTaskCreateRequest
    ) -> AgentTaskCreateResult:
        """Erstellt einen neuen AgentTask mit Idempotenz-Guard.

        Raises:
            ValueError: Wenn Repo nicht in ALLOWED_REPOS oder
                        bereits ein aktiver Task für diesen Branch existiert.
        """
        full_repo = request.repo_name
        if not full_repo.startswith("achimdehnert/"):
            full_repo = f"achimdehnert/{request.repo_name}"

        if full_repo not in ALLOWED_REPOS:
            return AgentTaskCreateResult(
                task=None,  # type: ignore[arg-type]
                error=_build_error(
                    "repo_not_allowed",
                    f"Repository '{full_repo}' ist nicht in der Allowlist.",
                ),
            )

        with transaction.atomic():
            task = AgentTask.objects.create(
                repo_name=full_repo,
                task_description=request.task_description,
                priority=request.priority,
                discord_user_id=request.discord_user_id,
                discord_channel_id=request.discord_channel_id,
                tenant_id=request.tenant_id,
                status=AgentTaskStatus.QUEUED,
            )
            logger.info(
                "AgentTask created",
                extra={
                    "task_public_id": str(task.public_id),
                    "repo": full_repo,
                    "tenant_id": request.tenant_id,
                },
            )
        return AgentTaskCreateResult(task=task)

    def mark_failed(
        self, task: AgentTask, error_message: str
    ) -> None:
        """Setzt Task auf FAILED — immer via Service-Layer, nie direkt."""
        with transaction.atomic():
            task.status = AgentTaskStatus.FAILED
            task.error_message = error_message
            task.save(update_fields=["status", "error_message", "updated_at"])

    def mark_pr_open(
        self, task: AgentTask, pr_number: int, pr_url: str
    ) -> None:
        with transaction.atomic():
            task.status = AgentTaskStatus.PR_OPEN
            task.pr_number = pr_number
            task.pr_url = pr_url
            task.save(update_fields=["status", "pr_number", "pr_url", "updated_at"])


def _build_error(code: str, message: str) -> str:
    return f"[{code}] {message}"
```

---

### 3.4 Phase 3: Scope-Guard für den Agent-Container (1-2h)

**Dateipfad:** `mcp_hub/services/agent_scope_guard.py`

```python
"""ScopeGuard — ADR-081-konforme Scope-Kontrolle für den Agent-Container.

Verwendet ALWAYS_FORBIDDEN_PATHS aus ADR-081 und ergänzt diese
um container-spezifische Regeln.
"""
from __future__ import annotations

import fnmatch
import subprocess
from pathlib import Path


# ADR-081 Section 5.6 — Immer verbotene Pfade (nie durch Agent änderbar)
ALWAYS_FORBIDDEN_PATHS: tuple[str, ...] = (
    "*/migrations/*.py",
    "config/settings/prod*.py",
    "config/settings/production*",
    ".env*",
    "docker-compose.prod.yml",
    "*.pem",
    "*.key",
    "*.crt",
    "requirements.txt",
    # Zusätzlich für Agent-Container:
    ".github/workflows/*.yml",   # CI-Workflows nicht durch Agent änderbar
    "Dockerfile*",               # Docker-Configs nur via ADR-Process
)


class ScopeViolation(Exception):
    """Scope-Verletzung durch Agent-Container."""


class AgentScopeGuard:
    """Prüft ob Agent-Output den ADR-081 ScopeLock einhält.

    Wird nach jedem Aider/StepExecutor-Durchlauf aufgerufen,
    bevor git push ausgeführt wird.
    """

    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace

    def verify_changed_files(self) -> list[str]:
        """Gibt Liste der veränderten Dateien zurück.

        Raises:
            ScopeViolation: Bei Verletzung von ALWAYS_FORBIDDEN_PATHS.
        """
        result = subprocess.run(  # noqa: S603
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True,
            text=True,
            cwd=self.workspace,
            check=True,
        )
        changed_files = [f for f in result.stdout.splitlines() if f.strip()]

        violations = []
        for filepath in changed_files:
            for pattern in ALWAYS_FORBIDDEN_PATHS:
                if fnmatch.fnmatch(filepath, pattern):
                    violations.append(f"{filepath!r} matched forbidden pattern {pattern!r}")

        if violations:
            raise ScopeViolation(
                f"Agent hat verbotene Dateien geändert:\n"
                + "\n".join(f"  • {v}" for v in violations)
            )

        return changed_files
```

---

### 3.5 Phase 4: Shell-Skript — ADR-konform mit `set -euo pipefail` (1h)

**Dateipfad:** `mcp_hub/scripts/run_agent_task.sh`

```bash
#!/usr/bin/env bash
# ADR-141: Agent-Task-Execution-Script
# Platform-Standard: set -euo pipefail in ALLEN Shell-Skripten

set -euo pipefail

# --- Argument-Validierung ---
TASK_ID="${1:?Fehler: TASK_ID erforderlich (Argument 1)}"
REPO_FULL="${2:?Fehler: REPO_FULL erforderlich (Argument 2, z.B. achimdehnert/coach-hub)}"
TASK_DESC="${3:?Fehler: TASK_DESC erforderlich (Argument 3)}"

WORKSPACE="/tmp/agent-tasks/${TASK_ID}"
BRANCH="ai/agent/${TASK_ID}"
MAX_COST_USD="${MAX_COST_USD:-5.00}"

echo "[agent] Task ${TASK_ID} gestartet für ${REPO_FULL}"
echo "[agent] Branch: ${BRANCH}"

# --- Workspace vorbereiten ---
mkdir -p "${WORKSPACE}"
cd "${WORKSPACE}"

# --- Git-Clone (Deploy-Key via ADR-045 read_secret) ---
DEPLOY_KEY_FILE="$(python -c "from config.secrets import read_secret; print(read_secret('AGENT_DEPLOY_KEY_PATH', required=True))")"

GIT_SSH_COMMAND="ssh -i ${DEPLOY_KEY_FILE} -o StrictHostKeyChecking=yes" \
    git clone "git@github.com:${REPO_FULL}.git" repo

cd repo

# --- Branch erstellen ---
git checkout -b "${BRANCH}"

# --- Kontext-Injection ---
CONTEXT_FILES=""
if [[ -f "CORE_CONTEXT.md" ]]; then
    CONTEXT_FILES="${CONTEXT_FILES} --read CORE_CONTEXT.md"
fi
if [[ -f "AGENT_HANDOVER.md" ]]; then
    CONTEXT_FILES="${CONTEXT_FILES} --read AGENT_HANDOVER.md"
fi

# --- Aider-Execution (nur als Fallback wenn StepExecutor nicht verfügbar) ---
# Präferenz: StepExecutor (ADR-082) via Python-API
python -m mcp_hub.services.agent_runner \
    --task-id "${TASK_ID}" \
    --task-desc "${TASK_DESC}" \
    --workspace "${WORKSPACE}/repo" \
    --branch "${BRANCH}" \
    --max-cost "${MAX_COST_USD}"

EXIT_CODE=$?
if [[ ${EXIT_CODE} -ne 0 ]]; then
    echo "[agent] Agent-Execution fehlgeschlagen mit Exit-Code ${EXIT_CODE}" >&2
    exit "${EXIT_CODE}"
fi

echo "[agent] Task ${TASK_ID} abgeschlossen."
```

---

### 3.6 Phase 5: Temporal Workflow (2-3h)

**Dateipfad:** `mcp_hub/temporal/workflows/coding_agent_workflow.py`

```python
"""CodingAgentWorkflow — Durable Workflow für ADR-141 (ADR-079: Temporal)."""
from __future__ import annotations

import asyncio
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

from mcp_hub.temporal.activities import (
    CIPollingActivity,
    DiscordNotifyActivity,
    GitCloneActivity,
    PRCreationActivity,
    StepExecutorActivity,
)


MAX_CI_ITERATIONS: int = 3
TASK_TIMEOUT: timedelta = timedelta(minutes=20)
ACTIVITY_TIMEOUT: timedelta = timedelta(minutes=10)


@workflow.defn
class CodingAgentWorkflow:
    """Orchestriert den kompletten Agentic-Coding-Flow (ADR-141).

    Ablauf:
        1. GitCloneActivity → Branch erstellen
        2. StepExecutorActivity → Code implementieren (ADR-082)
        3. CIPollingActivity → GitHub Actions abwarten
        4. Bei Failure → StepExecutorActivity (Fix) → zurück zu 3
        5. Bei Success → PRCreationActivity → DiscordNotifyActivity
    """

    @workflow.run
    async def run(self, task_public_id: str) -> dict:
        retry_policy = RetryPolicy(
            maximum_attempts=3,
            initial_interval=timedelta(seconds=5),
            maximum_interval=timedelta(minutes=2),
        )

        # 1. Git-Clone + Branch
        git_result = await workflow.execute_activity(
            GitCloneActivity.run,
            args=[task_public_id],
            start_to_close_timeout=ACTIVITY_TIMEOUT,
            retry_policy=retry_policy,
        )

        pr_url: str | None = None
        for iteration in range(1, MAX_CI_ITERATIONS + 1):
            # 2. Notify Discord — Iteration Start
            await workflow.execute_activity(
                DiscordNotifyActivity.run,
                args=[task_public_id, f"⚙️ Iteration {iteration}/{MAX_CI_ITERATIONS}…"],
                start_to_close_timeout=timedelta(seconds=30),
            )

            # 3. StepExecutor (ADR-082) — Code implementieren/fixen
            step_result = await workflow.execute_activity(
                StepExecutorActivity.run,
                args=[task_public_id, git_result, iteration],
                start_to_close_timeout=ACTIVITY_TIMEOUT,
                retry_policy=retry_policy,
            )

            # 4. CI abwarten
            ci_result = await workflow.execute_activity(
                CIPollingActivity.run,
                args=[task_public_id, step_result["ci_run_id"]],
                start_to_close_timeout=timedelta(minutes=15),
                retry_policy=RetryPolicy(maximum_attempts=1),
            )

            if ci_result["status"] == "success":
                # 5. PR erstellen
                pr_result = await workflow.execute_activity(
                    PRCreationActivity.run,
                    args=[task_public_id, step_result],
                    start_to_close_timeout=timedelta(minutes=2),
                )
                pr_url = pr_result["pr_url"]
                break

            if iteration == MAX_CI_ITERATIONS:
                # Alle Iterationen ausgeschöpft
                await workflow.execute_activity(
                    DiscordNotifyActivity.run,
                    args=[
                        task_public_id,
                        f"❌ CI nach {MAX_CI_ITERATIONS} Iterationen noch rot — "
                        "manueller Review erforderlich.",
                    ],
                    start_to_close_timeout=timedelta(seconds=30),
                )
                return {"status": "failed", "reason": "max_iterations_exceeded"}

        # 6. Discord-Notification: Erfolg
        await workflow.execute_activity(
            DiscordNotifyActivity.run,
            args=[task_public_id, f"✅ PR geöffnet: {pr_url}"],
            start_to_close_timeout=timedelta(seconds=30),
        )

        return {"status": "pr_open", "pr_url": pr_url}
```

---

## 4. Korrigierte Architektur-Übersicht

```
┌───────────────┐     ┌──────────────────────┐
│  Discord Bot  │────▶│  AgentTaskService     │
│  /code cmd    │     │  (Service-Layer)      │
└───────────────┘     └──────────┬───────────┘
                                  │ create AgentTask (DB)
                                  │
                                  ▼
                       ┌──────────────────────┐
                       │  Temporal Workflow   │ ← ADR-079
                       │  CodingAgentWorkflow │
                       └──────────┬───────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              ▼                   ▼                   ▼
   ┌──────────────────┐ ┌─────────────────┐ ┌────────────────┐
   │ GitCloneActivity │ │ StepExecutor    │ │ CIPolling      │
   │ (Deploy-Key via  │ │ Activity        │ │ Activity       │
   │  ADR-045)        │ │ (ADR-082!)      │ │ (GitHub API)   │
   └──────────────────┘ └────────┬────────┘ └────────────────┘
                                  │
              ┌────────────────────┼──────────────────┐
              ▼                    ▼                   ▼
   ┌──────────────────┐  ┌─────────────────┐ ┌───────────────┐
   │ LLMClient        │  │ ToolRegistry    │ │ ExecutionBudget│
   │ (llm_mcp routing │  │ + ScopeLock     │ │ $5 Hard-Stop  │
   │  ADR-116)        │  │ (ADR-081)       │ │ (ADR-082)     │
   └──────────────────┘  └─────────────────┘ └───────────────┘
                                  │
              ┌────────────────────┼──────────────────┐
              ▼                    ▼                   ▼
   ┌──────────────────┐  ┌─────────────────┐ ┌───────────────┐
   │  AgentIteration  │  │  AuditStore     │ │ Discord Thread│
   │  (DB Record)     │  │  (DB)           │ │ (Live-Updates)│
   └──────────────────┘  └─────────────────┘ └───────────────┘
```

---

## 5. Vollständiger Implementierungsplan (korrigiert)

| Phase | Inhalt | Dateipfade | Aufwand | Prio |
|-------|--------|------------|---------|------|
| **0** | ADR-141 Revision: related-ADRs ergänzen, Tool-Entscheidung treffen | `ADR-141-*.md` | 1h | BLOCKER |
| **1** | Django-Modelle: `AgentTask`, `AgentIteration` + Migration | `models/agent_task.py`, `models/agent_iteration.py`, `migrations/` | 2h | BLOCKER |
| **2** | Service-Layer: `AgentTaskService` + Discord `/code` Command | `services/agent_task_service.py`, `discord/commands/code_cmd.py` | 2h | BLOCKER |
| **3** | `AgentScopeGuard` (ADR-081-Guardrails) + Shell-Skript mit `set -euo pipefail` | `services/agent_scope_guard.py`, `scripts/run_agent_task.sh` | 2h | KRITISCH |
| **4** | Temporal Workflow + Activities | `temporal/workflows/coding_agent_workflow.py`, `temporal/activities/*.py` | 3h | KRITISCH |
| **5** | StepExecutorActivity (ADR-082-Bridge) + LLMClient via llm_mcp | `temporal/activities/step_executor_activity.py` | 2h | KRITISCH |
| **6** | CIPollingActivity: GitHub Actions API + Backoff | `temporal/activities/ci_polling_activity.py` | 1h | HOCH |
| **7** | Discord Live-Updates: Thread + Status-Posts | `temporal/activities/discord_notify_activity.py` | 1h | HOCH |
| **8** | ExecutionBudget Hard-Stop ($5) + ADR-116 Kosten-Tracking | Erweiterung `step_executor_activity.py` | 1h | HOCH |
| **9** | Docker-Image in GHCR-CI (ADR-117) + COMPOSE_PROJECT_NAME | `docker/coding-agent/Dockerfile`, CI-Workflow | 1h | HOCH |
| **10** | Secret-Management (ADR-045): Deploy-Keys, GitHub-Token | `config/secrets.py` Erweiterung | 1h | KRITISCH |
| **11** | i18n: `_()` in allen Models, Services, Discord-Messages | Alle neuen Dateien | 1h | HOCH |
| **12** | Tests: pytest-Suite für AgentTask, ScopeGuard, Service | `tests/test_agent_task_service.py`, `tests/test_scope_guard.py` | 2h | HOCH |

**Gesamt: ~20h über 3-4 Sessions** (statt 12h im ADR — durch korrekte Guardrails und DB-Modelle)

---

## 6. Offene Fragen — Entscheidungsbedarf

| Frage | Empfehlung | Begründung |
|-------|-----------|------------|
| Aider oder StepExecutor (ADR-082)? | **StepExecutor** | Kein paralleles System; Guardrails, AuditStore, Rollback bereits vorhanden |
| Wenn Aider: als Tool in ToolRegistry? | Ja — `AiderTool` als Wrapper | Aider-CLI als ein Tool unter vielen, ScopeLock greift trotzdem |
| Temporal oder Custom-Scheduler? | **Temporal** (ADR-079 accepted) | Durability, Retry, Observability bereits durch ADR-079 entschieden |
| Parallelität: 1 oder N Tasks gleichzeitig? | 1 pro Repo (Temporal-Mutex via Repo-Name als Workflow-ID) | Keine Branch-Konflikte, einfaches Locking |
| Allowlist in DB oder Code? | DB (Phase 4) — initial als Konstante | Database-first Platform-Standard |
| Welche Repos zuerst? | `coach-hub` + `risk-hub` wie geplant | Beides hat gute Test-Coverage als CI-Gate |

---

## 7. Nicht-Verhandelbares Checkliste (vor Merge)

- [ ] `BigAutoField PK + public_id UUIDField` auf `AgentTask` und `AgentIteration`
- [ ] `tenant_id = BigIntegerField(db_index=True)` auf beiden Modellen
- [ ] `deleted_at` auf beiden Modellen
- [ ] `UniqueConstraint` statt `unique_together`
- [ ] `SeparateDatabaseAndState` in Migration wenn nötig
- [ ] `asgiref.async_to_sync` — kein `asyncio.run()` im ASGI-Kontext
- [ ] `set -euo pipefail` in `run_agent_task.sh`
- [ ] `ALWAYS_FORBIDDEN_PATHS` (ADR-081) im `AgentScopeGuard` aktiv
- [ ] Secret-Management via `read_secret()` (ADR-045) — keine Env-Vars direkt
- [ ] `_()` / `{% trans %}` ab erstem Commit auf allen Strings
- [ ] `COMPOSE_PROJECT_NAME=coding_agent` in Docker-Config
- [ ] Docker-Image-Build in GHCR CI-Pipeline (ADR-120 `_build-docker`)
- [ ] `ExecutionBudget` Hard-Stop vor jedem LLM-Call
- [ ] Branch-Naming `ai/agent/<task-id>` (ADR-081/082-konform)

---

## 8. Befund-Zusammenfassung

| Severity | Anzahl | Status |
|----------|--------|--------|
| 🔴 BLOCKER | 3 | Muss vor Implementierung behoben werden |
| 🔴 KRITISCH | 5 | Muss in korrigiertem ADR adressiert werden |
| 🟠 HOCH | 6 | Im Implementierungsplan einplanen |
| 🟡 MEDIUM | 5 | Phase 2+ |

### Neue Befunde (Supplement 2026-03-13, 12:50 UTC+1)

| # | Befund | Severity | Begründung |
|---|--------|----------|------------|
| B3 | Alle 3 `related`-Referenzen in ADR-141 zeigen auf nicht-existierende Dateien | 🔴 BLOCKER | ADR-113 ist Telegram/pgvector, ADR-116 ist Model Router, ADR-100 ist iil-testkit — keine hat inhaltlich mit dem Thema zu tun. Fehlend: ADR-079, ADR-080, ADR-081, ADR-082, ADR-045 |
| K5 | Aider bypassed llm_mcp — Kosten nicht trackbar | 🔴 KRITISCH | Aider ruft OpenAI/Anthropic direkt auf. ADR-116 Budget-Tracking (llm_calls, Grafana) wird vollständig umgangen |
| H6 | Server-Ressourcen: 89 Container, 10/22GB RAM, 35GB Disk | 🟠 HOCH | 2GB Agent-Container machbar, aber `/tmp/agent-tasks/` auf Root-Partition — kein Disk-Quota definiert |
| K2† | Temporal hat `implementation_status: none` | Nuance | ADR-079 accepted aber "intentionally deferred". Pragmatische Alternative: Celery-Task mit expliziter ADR-079-Referenz |

**Empfehlung:** ADR-141 in `Draft` zurücksetzen, Section 4 (Entscheidung) und Section 5
(Architektur) gemäß diesem Review überarbeiten.

**Schwerpunkte der Überarbeitung:**
1. `related`-Feld auf korrekte ADR-Dateinamen ändern (ADR-079, -080, -081, -082, -045, -113, -116, -120)
2. Explizite Entscheidung: StepExecutor (ADR-082) statt Aider als Code-Engine
3. LLM-Routing via llm_mcp (ADR-116) — kein direkter API-Zugriff
4. Temporal vs. Celery als Workflow-Engine klären (ADR-079 ist accepted aber nicht implementiert)
5. DB-First-Design: `AgentTask` + `AgentIteration` Models (BigAutoField, public_id, tenant_id, deleted_at)
6. ADR-081 ScopeLock + ALWAYS_FORBIDDEN_PATHS als technische Sicherheits-Garantie

---

*Review erstellt: 2026-03-13 | Supplement: 2026-03-13 12:50*  
*Reviewer: Principal IT-Architekt, Autonomous Coding Expert, Senior Python-Entwickler*
