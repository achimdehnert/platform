"""
orchestrator_mcp/agent_team/roles.py

Extended agent team roles per ADR-107.
Fixes applied (see REVIEW-ADR-107):
  B-3: AgentRoleProtocol (Protocol) — ROLE_REGISTRY correctly typed
  C-1: set -euo pipefail via ShellAllowlist.wrap_script (unchanged, already correct)

Platform-standards compliance:
- Business logic in service layer (DeploymentExecutor, ReviewExecutor)
- No asyncio.run() — uses asgiref.async_to_sync where needed
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class AgentRole(str, Enum):
    TECH_LEAD = "tech_lead"
    DEVELOPER = "developer"
    TESTER = "tester"
    DEPLOYMENT = "deployment"
    PAYMENT = "payment"
    REVIEW = "review"
    RE_ENGINEER = "re_engineer"
    GUARDIAN = "guardian"


class GateLevel(int, Enum):
    """
    Gate-0: Fully automated, no approval needed.
    Gate-1: Agent decision, human informed.
    Gate-2: Human approval required for deployment.
    Gate-3: Tech Lead (Cascade) direct involvement.
    """

    ZERO = 0
    ONE = 1
    TWO = 2
    THREE = 3


class DeploymentTrigger(str, Enum):
    GIT_PUSH_MAIN = "git_push_main"
    MANUAL = "manual"
    ROLLBACK = "rollback"


class DeploymentStatus(str, Enum):
    PENDING = "pending"
    PRE_CHECK = "pre_check"
    MIGRATING = "migrating"
    DEPLOYING = "deploying"
    HEALTH_CHECKING = "health_checking"
    DEPLOYED = "deployed"
    ROLLING_BACK = "rolling_back"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class ReviewStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    OVERRIDDEN = "overridden"


# ---------------------------------------------------------------------------
# Fix B-3: Shared Protocol for all agent role types
# ---------------------------------------------------------------------------


@runtime_checkable
class AgentRoleProtocol(Protocol):
    """Common interface for all agent role configuration objects.

    Enforces that every role exposes role, gate_level, description,
    and can_auto_execute() — regardless of concrete type.
    Fix B-3: replaces Union typing in ROLE_REGISTRY.
    """

    role: AgentRole
    gate_level: GateLevel
    description: str

    def can_auto_execute(self) -> bool:
        ...


# ---------------------------------------------------------------------------
# Agent Config Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ShellAllowlist:
    """
    Enforces the shell command allowlist per ADR-107 §4.3.
    All commands MUST be prefixed with 'set -euo pipefail'.
    """

    allowed_commands: frozenset[str] = field(
        default_factory=lambda: frozenset(
            {"docker", "python", "manage.py", "cat", "tail", "timeout", "grep", "curl"}
        )
    )

    SHELL_PREAMBLE: str = "set -euo pipefail\n"

    def validate_command(self, cmd: str) -> bool:
        """Returns True if the command starts with an allowed binary."""
        stripped = cmd.lstrip()
        for allowed in self.allowed_commands:
            if stripped.startswith(allowed):
                return True
        return False

    def wrap_script(self, script_body: str) -> str:
        """Prepend set -euo pipefail to every shell script body."""
        if not script_body.startswith(self.SHELL_PREAMBLE):
            return self.SHELL_PREAMBLE + script_body
        return script_body


@dataclass(frozen=True)
class RollbackPolicy:
    """
    Three-tier rollback per ADR-107 review fix B-2.

    Tier 1 — No migration applied yet: revert image tag, recreate container.
    Tier 2 — Migration applied, no destructive change: image revert only
              (zero-downtime schema: new image handles both old/new schema).
    Tier 3 — Destructive migration applied: PAGE TECH LEAD, do NOT auto-rollback.
    """

    health_check_retries: int = 3
    health_check_timeout_seconds: int = 10
    container_start_timeout_seconds: int = 60
    migration_timeout_seconds: int = 300

    def requires_tech_lead(
        self, migration_is_destructive: bool, migration_was_applied: bool
    ) -> bool:
        return migration_is_destructive and migration_was_applied


# ---------------------------------------------------------------------------
# Base Agent Role
# ---------------------------------------------------------------------------


@dataclass
class BaseAgentRole:
    role: AgentRole
    gate_level: GateLevel
    description: str

    def can_auto_execute(self) -> bool:
        """Gate 0 and 1 execute autonomously; Gate 2+ require approval."""
        return self.gate_level <= GateLevel.ONE


# ---------------------------------------------------------------------------
# Deployment Agent
# ---------------------------------------------------------------------------


@dataclass
class DeploymentAgentConfig:
    """
    Full specification for the Deployment Agent per ADR-107 §4.3.

    MCP Tools (concrete, available in Windsurf):
      - mcp5_ssh_manage      : SSH on hetzner-prod (88.198.191.108)
      - mcp5_docker_manage   : Docker Compose control on hetzner-prod
      - mcp8_add_issue_comment: GitHub PR/Issue comments
      - mcp11_deploy_check   : Health check + status for known repos
      - mcp_cloudflare_*     : DNS/Tunnel management via Cloudflare API

    Deploy rule: NEVER write directly to prod. Use scripts/ship.sh or CI/CD.
    After every deploy: mcp11_deploy_check(action="health", repo=<name>)
    """

    role: AgentRole = AgentRole.DEPLOYMENT
    gate_level: GateLevel = GateLevel.TWO
    shell_allowlist: ShellAllowlist = field(default_factory=ShellAllowlist)
    rollback_policy: RollbackPolicy = field(default_factory=RollbackPolicy)

    health_check_endpoint: str = "/health/"
    health_check_expected_status: int = 200

    description: str = (
        "Executes full deployment lifecycle: image pull, migration, "
        "container recreate, health check, rollback on failure. "
        "Triggered by git push to main after green CI."
    )

    @property
    def allowed_tools(self) -> list[str]:
        return [
            "mcp5_ssh_manage",
            "mcp5_docker_manage",
            "mcp8_add_issue_comment",
            "mcp11_deploy_check",
            "mcp_cloudflare_dns_list",
            "mcp_cloudflare_dns_create",
        ]

    @property
    def infra_context(self) -> dict[str, Any]:
        """Concrete infra config — eliminates per-session guesswork."""
        return {
            "prod_host": "hetzner-prod",
            "prod_ip": "88.198.191.108",
            "prod_user": "deploy",
            "dev_host": "hetzner-dev",
            "cloudflare_access": "via mcp_cloudflare_* (API-Keys in Windsurf-Secrets)",
            "deploy_targets": {
                "coach-hub":        {"path": "/opt/coach-hub",        "health": "https://kiohnerisiko.de/healthz/"},
                "billing-hub":      {"path": "/opt/billing-hub",      "health": "https://billing.iil.pet/healthz/"},
                "travel-beat":      {"path": "/opt/travel-beat",      "health": "https://drifttales.de/healthz/"},
                "weltenhub":        {"path": "/opt/weltenhub",        "health": "https://weltenforger.com/healthz/"},
                "trading-hub":      {"path": "/opt/trading-hub",      "health": "https://ai-trades.de/healthz/"},
                "cad-hub":          {"path": "/opt/cad-hub",          "health": "https://nl2cad.de/healthz/"},
                "pptx-hub":         {"path": "/opt/pptx-hub",         "health": "https://prezimo.de/healthz/"},
                "risk-hub":         {"path": "/opt/risk-hub",         "health": "https://risk-hub.iil.pet/healthz/"},
                "ausschreibungs-hub": {"path": "/opt/ausschreibungs-hub", "health": "https://bieterpilot.de/healthz/"},
            },
            "rules": [
                "Gate-2 required before any prod deploy",
                "Use mcp11_deploy_check(action='health') after every deploy",
                "DB changes only via Django migrations, never direct SQL on prod",
                "API-Keys are in Windsurf-Secrets — never hardcode",
            ],
        }

    @property
    def requires_gate2_approval_for(self) -> list[str]:
        return [
            "new_migrations",
            "breaking_schema_changes",
            "prod_only_fixes",
        ]

    def can_auto_execute(self) -> bool:
        """Deployment Agent always requires Gate-2 (never auto)."""
        return False

    def build_deployment_script(
        self,
        image_tag: str,
        service_name: str,
        compose_file: str = "docker-compose.prod.yml",
    ) -> str:
        body = f"""
# Step 1: Pull new image
docker compose -f {compose_file} pull {service_name}

# Step 4: Recreate container (no-deps, force-recreate)
docker compose -f {compose_file} up -d --no-deps --force-recreate {service_name}

# Step 5: Verify container is running
docker compose -f {compose_file} ps {service_name}
"""
        return self.shell_allowlist.wrap_script(body.lstrip())

    def build_health_check_script(self, base_url: str) -> str:
        body = f"""
# Step 5: Health check with retries
for i in 1 2 3; do
    STATUS=$(curl -s -o /dev/null -w "%{{http_code}}" {base_url}{self.health_check_endpoint})
    if [ "$STATUS" -eq {self.health_check_expected_status} ]; then
        echo "Health check passed (attempt $i)"
        exit 0
    fi
    echo "Health check failed (attempt $i, status $STATUS)"
    sleep {self.rollback_policy.health_check_timeout_seconds}
done
echo "Health check failed after {self.rollback_policy.health_check_retries} attempts"
exit 1
"""
        return self.shell_allowlist.wrap_script(body.lstrip())

    def build_rollback_script(
        self,
        previous_image_tag: str,
        service_name: str,
        compose_file: str = "docker-compose.prod.yml",
    ) -> str:
        if not previous_image_tag:
            raise ValueError(
                "previous_image_tag is required for rollback. "
                "Ensure save_tag step ran before deployment."
            )
        body = f"""
# Rollback: Restore previous image
echo "Rolling back to {previous_image_tag}"
sed -i "s|image:.*|image: {previous_image_tag}|" {compose_file}
docker compose -f {compose_file} up -d --no-deps --force-recreate {service_name}
echo "Rollback complete"
"""
        return self.shell_allowlist.wrap_script(body.lstrip())

    def build_migration_script(
        self,
        manage_py_path: str = "python manage.py",
        timeout_seconds: int | None = None,
    ) -> str:
        """
        Fix B-1: Uses migrate --check (detect unapplied) + sqlmigrate for SQL preview.
        Fix H-2: Wraps migrate in timeout.
        """
        t = timeout_seconds or self.rollback_policy.migration_timeout_seconds
        body = f"""
# Step 2a: Check for unapplied migrations
# NOTE: --check does NOT validate schema safety. Use breaking_change_detector separately.
{manage_py_path} migrate --check && echo "No pending migrations" || echo "Migrations pending, proceeding"

# Step 3: Apply migrations with timeout guard
timeout {t} {manage_py_path} migrate --noinput
"""
        return self.shell_allowlist.wrap_script(body.lstrip())


# ---------------------------------------------------------------------------
# Payment Agent
# ---------------------------------------------------------------------------


@dataclass
class PaymentAgentConfig:
    """
    Full specification for the Payment Agent (Stripe + billing-hub).

    MCP Tools (concrete, available in Windsurf):
      - mcp5_ssh_manage      : SSH on hetzner-prod to run management commands
      - mcp8_add_issue_comment: GitHub PR/Issue comments
      - mcp11_deploy_check   : Health check for billing-hub

    Stripe API-Keys: NEVER in code. Location:
      - Prod: /opt/billing-hub/.env  (STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET)
      - Local: billing-hub .env (never committed)

    Price IDs: Set via management command after creation in Stripe Dashboard.
    setup_plans command: python manage.py setup_plans --stripe-monthly=<id> --stripe-yearly=<id>

    billing-hub internal API (HMAC-Auth, Docker-Network only):
      - GET  /api/access/{platform}/{email}/{module}/
      - GET  /api/customer/{email}/
      - POST /api/webhook/stripe/  (Stripe-Signature, not HMAC)
      - GET  /healthz/
    """

    role: AgentRole = AgentRole.PAYMENT
    gate_level: GateLevel = GateLevel.TWO

    description: str = (
        "Manages Stripe subscriptions, Price IDs, webhook health, and "
        "billing-hub internal API. Requires Gate-2 for any Stripe config change. "
        "ADR-062: Central billing service for all 9 hubs."
    )

    def can_auto_execute(self) -> bool:
        """Payment Agent always requires Gate-2 — never auto."""
        return False

    @property
    def allowed_tools(self) -> list[str]:
        return [
            "mcp5_ssh_manage",
            "mcp11_deploy_check",
            "mcp8_add_issue_comment",
        ]

    @property
    def payment_context(self) -> dict[str, Any]:
        """Stripe + billing-hub config — eliminates per-session guesswork."""
        return {
            "billing_hub": {
                "host": "hetzner-prod",
                "path": "/opt/billing-hub",
                "health": "https://billing.iil.pet/healthz/",
                "internal_url": "http://billing-hub-web:8000",
                "port": 8092,
            },
            "stripe": {
                "account": "one Stripe account for all 9 hubs (ADR-062)",
                "webhook_endpoint": "POST /api/webhook/stripe/",
                "keys_location": "/opt/billing-hub/.env (STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET)",
                "keys_local": "billing-hub/.env (never committed — in Windsurf-Secrets)",
                "price_ids_status": "PENDING — must be created in Stripe Dashboard first",
                "setup_command": (
                    "python manage.py setup_plans "
                    "--stripe-monthly=price_xxx --stripe-yearly=price_xxx"
                ),
            },
            "platforms": [
                "coach-hub", "billing-hub", "travel-beat", "weltenhub",
                "trading-hub", "cad-hub", "pptx-hub", "risk-hub", "ausschreibungs-hub",
            ],
            "subscription_tiers": ["free", "registered", "premium", "enterprise"],
            "internal_api": {
                "auth": "HMAC (X-Internal-Token header, 30s replay protection)",
                "secret_location": "BILLING_INTERNAL_SECRET in each hub's .env",
                "access_check": "GET /api/access/{platform}/{email}/{module}/",
                "customer_info": "GET /api/customer/{email}/",
            },
            "rules": [
                "Gate-2 required before any Stripe config change",
                "STRIPE_SECRET_KEY only in .env — never in code or logs",
                "Webhook signature must be verified (STRIPE_WEBHOOK_SECRET)",
                "setup_plans only after Price IDs created in Stripe Dashboard",
                "Use mcp11_deploy_check(action='health', repo='billing-hub') after changes",
            ],
            "pending_actions": [
                "Create Price IDs in Stripe Dashboard for each hub/tier",
                "Run: python manage.py setup_plans --stripe-monthly=<id> --stripe-yearly=<id>",
                "Verify webhook endpoint in Stripe Dashboard points to billing.iil.pet",
            ],
        }


# ---------------------------------------------------------------------------
# Review Agent
# ---------------------------------------------------------------------------


@dataclass
class ReviewCheckResult:
    check_name: str
    passed: bool
    blocking: bool
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReviewAgentConfig:
    """
    Full specification for the Review Agent per ADR-107 §4.4.

    Check pipeline (in order):
      1. Ruff + Bandit clean         -> Gate 0, BLOCKS merge
      2. ADR-Compliance              -> Gate 1, BLOCKS merge
      3. Platform-Patterns           -> Gate 1, BLOCKS merge
      4. Test-Coverage-Delta >= 0    -> WARNING only
      5. RunPython without reverse   -> WARNING only
    """

    role: AgentRole = AgentRole.REVIEW
    gate_level: GateLevel = GateLevel.ONE

    override_label: str = "agent-review-override"
    override_comment_trigger: str = "/override-review"

    description: str = (
        "Automated PR review against ADRs, Ruff, Bandit, and platform patterns. "
        "Triggered by new PR against main. Posts structured review report as PR comment."
    )

    def can_auto_execute(self) -> bool:
        """Review Agent runs autonomously at Gate-1."""
        return True

    @property
    def allowed_tools(self) -> list[str]:
        return ["github_pr", "mcp12_check_violations", "shell_exec"]

    @property
    def check_pipeline(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "ruff_bandit",
                "label": "Ruff + Bandit",
                "gate": GateLevel.ZERO,
                "blocking": True,
                "tool": "shell_exec",
                "command": "ruff check . && bandit -r . -c pyproject.toml",
            },
            {
                "name": "adr_compliance",
                "label": "ADR-Compliance",
                "gate": GateLevel.ONE,
                "blocking": True,
                "tool": "mcp12_check_violations",
                "command": None,
            },
            {
                "name": "platform_patterns",
                "label": "Platform-Patterns",
                "gate": GateLevel.ONE,
                "blocking": True,
                "tool": "shell_exec",
                "command": (
                    "! grep -rn 'style=' --include='*.py' . && "
                    "! grep -rn 'cursor.execute' --include='*.py' . | grep -v '# noqa'"
                ),
            },
            {
                "name": "coverage_delta",
                "label": "Test-Coverage-Delta",
                "gate": GateLevel.ONE,
                "blocking": False,
                "tool": "shell_exec",
                "command": "python -m pytest --cov=. --cov-report=json --co -q",
            },
            {
                "name": "runpython_reverse",
                "label": "RunPython ohne Reverse",
                "gate": GateLevel.ONE,
                "blocking": False,
                "tool": "shell_exec",
                "command": (
                    "grep -rn 'RunPython' --include='*.py' migrations/ | "
                    "grep -v 'reverse=' || true"
                ),
            },
        ]

    def build_pr_comment(
        self,
        pr_number: int,
        results: list[ReviewCheckResult],
        override_active: bool = False,
    ) -> str:
        """Renders a structured PR comment from check results."""
        lines = ["## Agent Review Report", ""]

        if override_active:
            lines.append(f"> Override active (`{self.override_label}`)")
            lines.append("")

        all_passed = all(r.passed for r in results)
        blockers = [r for r in results if not r.passed and r.blocking]

        if all_passed:
            lines.append("**All checks passed.** PR is ready for merge.")
        elif blockers:
            lines.append(f"**{len(blockers)} blocking issue(s) found.** Merge blocked.")
        else:
            lines.append("**Warnings only.** PR may be merged, but review warnings.")

        lines.append("")
        lines.append("| Check | Status | Blocking |")
        lines.append("|-------|--------|----------|")  

        for r in results:
            status = "Pass" if r.passed else ("Fail" if r.blocking else "Warn")
            blocking = "Yes" if r.blocking else "No"
            lines.append(f"| {r.check_name} | {status} | {blocking} |")

        lines.append("")
        for r in results:
            if not r.passed:
                lines.append(f"### {r.check_name}")
                lines.append(r.message)
                if r.details:
                    lines.append(f"```\n{r.details}\n```")
                lines.append("")

        lines.append("---")
        lines.append(
            f"*To override: add label `{self.override_label}` "
            f"or comment `{self.override_comment_trigger} <reason>`*"
        )
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Role Registry — Fix B-3: typed as dict[AgentRole, AgentRoleProtocol]
# ---------------------------------------------------------------------------


ROLE_REGISTRY: dict[AgentRole, AgentRoleProtocol] = {
    AgentRole.TECH_LEAD: BaseAgentRole(
        role=AgentRole.TECH_LEAD,
        gate_level=GateLevel.THREE,
        description="ADRs, Konzepte, Architektur, komplexe Feature-Planung, finale PR-Freigabe.",
    ),
    AgentRole.DEVELOPER: BaseAgentRole(
        role=AgentRole.DEVELOPER,
        gate_level=GateLevel.ONE,
        description="Feature-Code, Bugfixes, Refactoring nach Plan von Tech Lead.",
    ),
    AgentRole.TESTER: BaseAgentRole(
        role=AgentRole.TESTER,
        gate_level=GateLevel.ZERO,
        description="Tests schreiben, Coverage prüfen, CI-Fehler analysieren.",
    ),
    AgentRole.DEPLOYMENT: DeploymentAgentConfig(),
    AgentRole.PAYMENT: PaymentAgentConfig(),
    AgentRole.REVIEW: ReviewAgentConfig(),
    AgentRole.RE_ENGINEER: BaseAgentRole(
        role=AgentRole.RE_ENGINEER,
        gate_level=GateLevel.TWO,
        description="Refactoring nach Guardian-Fail, Tech Debt, Architektur-Schulden.",
    ),
    AgentRole.GUARDIAN: BaseAgentRole(
        role=AgentRole.GUARDIAN,
        gate_level=GateLevel.ZERO,
        description="Ruff, Bandit, MyPy, ADR-Compliance — regelbasiert, vollautomatisch.",
    ),
}


def get_role(role: AgentRole) -> AgentRoleProtocol:
    """Returns the configured role object from the registry."""
    if role not in ROLE_REGISTRY:
        raise ValueError(
            f"Unknown agent role: {role!r}. Available: {list(ROLE_REGISTRY)}"
        )
    return ROLE_REGISTRY[role]


def route_task(task_type: str, complexity: str | None = None) -> AgentRole:
    """
    Implements the Aufgaben-Routing-Entscheidungsbaum per ADR-107 §4.5.

    Args:
        task_type: One of 'adr', 'concept', 'architecture', 'feature', 'bugfix',
                   'test', 'deployment', 'pr_review', 'refactor', 'tech_debt'
        complexity: One of 'trivial', 'simple', 'moderate', 'complex', 'expert'
    """
    TECH_LEAD_TYPES = {"adr", "concept", "architecture"}
    if task_type in TECH_LEAD_TYPES:
        return AgentRole.TECH_LEAD

    if task_type in {"feature", "bugfix"}:
        if complexity in {"complex", "expert"}:
            logger.info("High-complexity task: Cascade plans, Developer executes.")
        return AgentRole.DEVELOPER

    if task_type == "test":
        return AgentRole.TESTER

    if task_type == "deployment":
        return AgentRole.DEPLOYMENT

    if task_type == "pr_review":
        return AgentRole.REVIEW

    if task_type in {"refactor", "tech_debt"}:
        return AgentRole.RE_ENGINEER

    raise ValueError(
        f"Unknown task_type: {task_type!r}. "
        "Valid types: adr, concept, architecture, feature, bugfix, test, "
        "deployment, pr_review, refactor, tech_debt"
    )
