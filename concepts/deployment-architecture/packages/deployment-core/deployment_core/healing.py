"""
AI-powered error analysis and auto-healing for deployments.

This module provides:
- ErrorAnalyzer: Claude-powered error analysis
- HetznerPatterns: Known error patterns for Hetzner Cloud
- AutoFixer: Execute safe fixes automatically

Example:
    analyzer = ErrorAnalyzer(api_key=os.environ["ANTHROPIC_API_KEY"])
    
    analysis = await analyzer.analyze(
        error_log="Error: OOMKilled...",
        context={"app": "travel-beat", "deploy_path": "/opt/travel-beat"}
    )
    
    if analysis.can_auto_fix:
        result = await analyzer.execute_fix(analysis)
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class ErrorCategory(Enum):
    """Deployment error categories."""

    INFRASTRUCTURE = "INFRASTRUCTURE"  # Hetzner API, Provisioning, Network
    BUILD = "BUILD"  # Docker build, Dependencies, Compilation
    DEPLOY = "DEPLOY"  # Container start, Health, Migrations
    RUNTIME = "RUNTIME"  # Crashes, Memory, CPU
    NETWORK = "NETWORK"  # DNS, SSL, Firewall
    PERMISSION = "PERMISSION"  # SSH, Tokens, File permissions
    UNKNOWN = "UNKNOWN"


class Severity(Enum):
    """Error severity levels."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class FixAction(Enum):
    """Recommended fix actions."""

    AUTO_FIX = "AUTO-FIX"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    RETRY = "RETRY"
    ROLLBACK = "ROLLBACK"
    ESCALATE = "ESCALATE"


class RiskLevel(Enum):
    """Risk level for fixes."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass
class Fix:
    """Proposed fix for an error."""

    action: FixAction
    risk: RiskLevel
    commands: list[str] = field(default_factory=list)
    rollback_commands: list[str] = field(default_factory=list)
    validation_commands: list[str] = field(default_factory=list)
    description: str = ""
    prevention: str = ""


@dataclass
class ErrorAnalysis:
    """Result of error analysis."""

    category: ErrorCategory
    severity: Severity
    confidence: int  # 0-100
    root_cause: str
    fix: Fix
    matched_pattern: str | None = None
    raw_response: dict[str, Any] | None = None

    @property
    def can_auto_fix(self) -> bool:
        """Check if auto-fix is safe to execute."""
        return (
            self.fix.action == FixAction.AUTO_FIX
            and self.confidence >= 85
            and self.fix.risk == RiskLevel.LOW
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "category": self.category.value,
            "severity": self.severity.value,
            "confidence": self.confidence,
            "root_cause": self.root_cause,
            "can_auto_fix": self.can_auto_fix,
            "fix": {
                "action": self.fix.action.value,
                "risk": self.fix.risk.value,
                "commands": self.fix.commands,
                "rollback_commands": self.fix.rollback_commands,
                "validation_commands": self.fix.validation_commands,
                "description": self.fix.description,
                "prevention": self.fix.prevention,
            },
            "matched_pattern": self.matched_pattern,
        }


class HetznerPatterns:
    """Known error patterns for Hetzner Cloud deployments."""

    PATTERNS: dict[str, dict[str, Any]] = {
        # Rate Limiting
        r"429|Too Many Requests|rate.?limit": {
            "category": ErrorCategory.INFRASTRUCTURE,
            "severity": Severity.MEDIUM,
            "confidence": 95,
            "root_cause": "Hetzner API rate limit exceeded",
            "fix": {
                "action": FixAction.RETRY,
                "risk": RiskLevel.LOW,
                "commands": ["sleep $((2**$RETRY_COUNT))", "# Retry with exponential backoff"],
                "prevention": "Implement rate limiting in deployment scripts",
            },
        },
        # Docker Image Not Found
        r"manifest unknown|image not found|pull access denied": {
            "category": ErrorCategory.BUILD,
            "severity": Severity.HIGH,
            "confidence": 90,
            "root_cause": "Docker image tag does not exist in registry",
            "fix": {
                "action": FixAction.AUTO_FIX,
                "risk": RiskLevel.LOW,
                "commands": [
                    "# Fallback to previous tag",
                    "docker pull ${REGISTRY}/${IMAGE}:latest || true",
                ],
                "rollback_commands": [],
                "prevention": "Add pre-deployment image existence check",
            },
        },
        # Out of Memory
        r"OOMKilled|Out of memory|Cannot allocate memory": {
            "category": ErrorCategory.RUNTIME,
            "severity": Severity.CRITICAL,
            "confidence": 92,
            "root_cause": "Container exceeded memory limits",
            "fix": {
                "action": FixAction.HUMAN_REVIEW,
                "risk": RiskLevel.MEDIUM,
                "commands": [
                    "# Increase memory limit (requires manual review)",
                    "# docker-compose.yml: mem_limit: 1g -> 2g",
                ],
                "prevention": "Monitor memory usage, optimize application",
            },
        },
        # Disk Space
        r"no space left on device|disk.?full|ENOSPC": {
            "category": ErrorCategory.INFRASTRUCTURE,
            "severity": Severity.CRITICAL,
            "confidence": 95,
            "root_cause": "Disk space exhausted",
            "fix": {
                "action": FixAction.AUTO_FIX,
                "risk": RiskLevel.LOW,
                "commands": [
                    "docker system prune -af --volumes",
                    "journalctl --vacuum-time=3d",
                ],
                "validation_commands": ["df -h /"],
                "prevention": "Set up disk space monitoring and alerts",
            },
        },
        # Permission Denied (SSH)
        r"Permission denied \(publickey\)|Could not read from remote": {
            "category": ErrorCategory.PERMISSION,
            "severity": Severity.HIGH,
            "confidence": 88,
            "root_cause": "SSH key permissions or authentication failed",
            "fix": {
                "action": FixAction.AUTO_FIX,
                "risk": RiskLevel.LOW,
                "commands": [
                    "chmod 600 ~/.ssh/id_*",
                    "chmod 700 ~/.ssh",
                ],
                "validation_commands": ["ssh -T git@github.com || true"],
                "prevention": "Verify SSH key setup in CI/CD",
            },
        },
        # Terraform State Lock
        r"state lock|Error locking state|Lock Info": {
            "category": ErrorCategory.INFRASTRUCTURE,
            "severity": Severity.MEDIUM,
            "confidence": 90,
            "root_cause": "Terraform state is locked by another process",
            "fix": {
                "action": FixAction.HUMAN_REVIEW,
                "risk": RiskLevel.MEDIUM,
                "commands": [
                    "# After 10 minutes, force unlock (dangerous!):",
                    "# terraform force-unlock <LOCK_ID>",
                ],
                "prevention": "Use remote state with proper locking",
            },
        },
        # Connection Refused
        r"connection refused|ECONNREFUSED|Connection reset": {
            "category": ErrorCategory.NETWORK,
            "severity": Severity.HIGH,
            "confidence": 75,
            "root_cause": "Service not running or firewall blocking",
            "fix": {
                "action": FixAction.HUMAN_REVIEW,
                "risk": RiskLevel.MEDIUM,
                "commands": [
                    "docker-compose ps",
                    "systemctl status <service>",
                    "ufw status",
                ],
                "prevention": "Implement health checks and retry logic",
            },
        },
        # Database Connection
        r"could not connect to server|Connection refused.*5432|pg_": {
            "category": ErrorCategory.RUNTIME,
            "severity": Severity.CRITICAL,
            "confidence": 85,
            "root_cause": "Database connection failed",
            "fix": {
                "action": FixAction.HUMAN_REVIEW,
                "risk": RiskLevel.HIGH,
                "commands": [
                    "docker-compose logs postgres",
                    "pg_isready -h localhost -p 5432",
                ],
                "prevention": "Add database health check to deployment",
            },
        },
        # SSL/TLS Errors
        r"SSL|certificate|CERT_|handshake": {
            "category": ErrorCategory.NETWORK,
            "severity": Severity.HIGH,
            "confidence": 70,
            "root_cause": "SSL/TLS certificate issue",
            "fix": {
                "action": FixAction.HUMAN_REVIEW,
                "risk": RiskLevel.MEDIUM,
                "commands": [
                    "certbot certificates",
                    "openssl s_client -connect domain:443",
                ],
                "prevention": "Set up certificate expiry monitoring",
            },
        },
    }

    @classmethod
    def match(cls, error_log: str) -> ErrorAnalysis | None:
        """
        Match error log against known patterns.

        Returns ErrorAnalysis if a pattern matches, None otherwise.
        """
        for pattern, config in cls.PATTERNS.items():
            if re.search(pattern, error_log, re.IGNORECASE | re.MULTILINE):
                logger.info("pattern_matched", pattern=pattern)

                fix_config = config.get("fix", {})
                fix = Fix(
                    action=fix_config.get("action", FixAction.HUMAN_REVIEW),
                    risk=fix_config.get("risk", RiskLevel.MEDIUM),
                    commands=fix_config.get("commands", []),
                    rollback_commands=fix_config.get("rollback_commands", []),
                    validation_commands=fix_config.get("validation_commands", []),
                    prevention=fix_config.get("prevention", ""),
                )

                return ErrorAnalysis(
                    category=config["category"],
                    severity=config["severity"],
                    confidence=config["confidence"],
                    root_cause=config["root_cause"],
                    fix=fix,
                    matched_pattern=pattern,
                )

        return None


CLAUDE_SYSTEM_PROMPT = """Du bist ein autonomer DevOps-Agent für Hetzner Cloud Deployments.
Analysiere den Deployment-Fehler und antworte NUR mit validem JSON.

## KATEGORIEN
- INFRASTRUCTURE: Hetzner API, Provisioning, Netzwerk
- BUILD: Docker, Dependencies, Compilation
- DEPLOY: Container-Start, Health, Migrations
- RUNTIME: Crashes, Memory, CPU
- NETWORK: DNS, SSL, Firewall
- PERMISSION: SSH, Tokens, Dateiberechtigungen

## ENTSCHEIDUNGSLOGIK

AUTO-FIX (confidence ≥85%, risk=LOW):
- Dependency Mismatches
- Docker Image Tag Fallback
- Rate Limits → Retry
- SSH Permissions → chmod 600
- Disk Space → docker system prune

HUMAN_REVIEW (confidence <85% oder risk≥MEDIUM):
- DB Migrations, Secrets, Firewall, DNS, Rollbacks

## OUTPUT FORMAT (JSON)

{
  "analysis": {
    "category": "CATEGORY",
    "severity": "CRITICAL|HIGH|MEDIUM|LOW",
    "confidence": 0-100,
    "root_cause": "Kurze Beschreibung"
  },
  "fix": {
    "action": "AUTO-FIX|HUMAN_REVIEW|RETRY|ROLLBACK",
    "risk": "LOW|MEDIUM|HIGH",
    "commands": ["cmd1", "cmd2"],
    "rollback_commands": ["rollback_cmd"],
    "validation_commands": ["validation_cmd"],
    "description": "Was wird geändert",
    "prevention": "Empfehlung"
  }
}

## REGELN
1. NIEMALS Secrets in Output
2. IMMER Rollback-Option wenn möglich
3. Bei Unsicherheit → HUMAN_REVIEW
4. Konkrete, ausführbare Befehle"""


class ErrorAnalyzer:
    """
    AI-powered error analyzer using Claude API.

    Falls back to pattern matching if API is unavailable.

    Example:
        analyzer = ErrorAnalyzer(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        analysis = await analyzer.analyze(error_log, context={"app": "myapp"})
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-20250514",
        use_patterns_first: bool = True,
    ):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model
        self.use_patterns_first = use_patterns_first
        self._client: Any = None

    async def _get_client(self) -> Any:
        """Lazy-load Anthropic client."""
        if self._client is None:
            try:
                import anthropic

                self._client = anthropic.AsyncAnthropic(api_key=self.api_key)
            except ImportError:
                logger.warning("anthropic package not installed, using pattern matching only")
                return None
        return self._client

    async def analyze(
        self,
        error_log: str,
        context: dict[str, Any] | None = None,
    ) -> ErrorAnalysis:
        """
        Analyze deployment error and return recommendations.

        Args:
            error_log: The error log or output from failed deployment
            context: Additional context (app name, deploy path, etc.)

        Returns:
            ErrorAnalysis with category, severity, and recommended fix
        """
        context = context or {}

        # Try pattern matching first (fast, no API call)
        if self.use_patterns_first:
            pattern_result = HetznerPatterns.match(error_log)
            if pattern_result and pattern_result.confidence >= 85:
                logger.info(
                    "using_pattern_match",
                    pattern=pattern_result.matched_pattern,
                    confidence=pattern_result.confidence,
                )
                return pattern_result

        # Use Claude for complex analysis
        client = await self._get_client()
        if client is None:
            # Fallback to pattern match or unknown
            if pattern_result:
                return pattern_result
            return self._unknown_error(error_log)

        try:
            # Build prompt
            prompt = self._build_prompt(error_log, context)

            # Call Claude API
            response = await client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=CLAUDE_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )

            # Parse response
            response_text = response.content[0].text
            return self._parse_response(response_text)

        except Exception as e:
            logger.error("claude_analysis_failed", error=str(e))
            # Fallback to pattern match
            if pattern_result:
                return pattern_result
            return self._unknown_error(error_log, error=str(e))

    def _build_prompt(self, error_log: str, context: dict[str, Any]) -> str:
        """Build the prompt for Claude."""
        context_str = json.dumps(context, indent=2) if context else "No additional context"

        return f"""KONTEXT:
{context_str}

ERROR LOG:
{error_log[:8000]}

Analysiere diesen Fehler und antworte NUR mit JSON."""

    def _parse_response(self, response_text: str) -> ErrorAnalysis:
        """Parse Claude's JSON response."""
        try:
            # Try to extract JSON from response
            json_match = re.search(r"\{[\s\S]*\}", response_text)
            if not json_match:
                raise ValueError("No JSON found in response")

            data = json.loads(json_match.group())

            analysis = data.get("analysis", {})
            fix_data = data.get("fix", {})

            fix = Fix(
                action=FixAction(fix_data.get("action", "HUMAN_REVIEW")),
                risk=RiskLevel(fix_data.get("risk", "MEDIUM")),
                commands=fix_data.get("commands", []),
                rollback_commands=fix_data.get("rollback_commands", []),
                validation_commands=fix_data.get("validation_commands", []),
                description=fix_data.get("description", ""),
                prevention=fix_data.get("prevention", ""),
            )

            return ErrorAnalysis(
                category=ErrorCategory(analysis.get("category", "UNKNOWN")),
                severity=Severity(analysis.get("severity", "MEDIUM")),
                confidence=analysis.get("confidence", 50),
                root_cause=analysis.get("root_cause", "Unknown"),
                fix=fix,
                raw_response=data,
            )

        except Exception as e:
            logger.error("response_parse_failed", error=str(e), response=response_text[:500])
            return self._unknown_error("", error=str(e))

    def _unknown_error(self, error_log: str, error: str | None = None) -> ErrorAnalysis:
        """Return unknown error analysis."""
        return ErrorAnalysis(
            category=ErrorCategory.UNKNOWN,
            severity=Severity.MEDIUM,
            confidence=0,
            root_cause=error or "Could not determine root cause",
            fix=Fix(
                action=FixAction.HUMAN_REVIEW,
                risk=RiskLevel.HIGH,
                commands=[],
                description="Manual investigation required",
            ),
        )


# Blocked dangerous commands that should never be auto-executed
BLOCKED_COMMANDS = [
    r"rm\s+-rf\s+/",
    r"rm\s+-rf\s+\*",
    r"DROP\s+DATABASE",
    r"DROP\s+TABLE",
    r"DELETE\s+FROM.*WHERE\s+1\s*=\s*1",
    r"curl.*\|.*sh",
    r"wget.*\|.*sh",
    r":\(\)\{.*:\|:.*\}",  # Fork bomb
    r"mkfs\.",
    r"dd\s+if=.*of=/dev/",
]


def is_command_safe(command: str) -> bool:
    """Check if a command is safe to auto-execute."""
    for pattern in BLOCKED_COMMANDS:
        if re.search(pattern, command, re.IGNORECASE):
            return False
    return True


async def execute_fix(
    analysis: ErrorAnalysis,
    dry_run: bool = True,
) -> dict[str, Any]:
    """
    Execute the recommended fix commands.

    Args:
        analysis: The error analysis with fix commands
        dry_run: If True, only log commands without executing

    Returns:
        dict with execution results
    """
    import asyncio

    results = {
        "success": True,
        "dry_run": dry_run,
        "commands_executed": [],
        "commands_blocked": [],
        "errors": [],
    }

    for cmd in analysis.fix.commands:
        # Skip comments
        if cmd.strip().startswith("#"):
            continue

        # Safety check
        if not is_command_safe(cmd):
            logger.warning("blocked_dangerous_command", command=cmd)
            results["commands_blocked"].append(cmd)
            continue

        if dry_run:
            logger.info("dry_run_command", command=cmd)
            results["commands_executed"].append({"command": cmd, "status": "dry_run"})
        else:
            try:
                proc = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)

                results["commands_executed"].append({
                    "command": cmd,
                    "status": "success" if proc.returncode == 0 else "failed",
                    "exit_code": proc.returncode,
                    "stdout": stdout.decode()[:500] if stdout else None,
                    "stderr": stderr.decode()[:500] if stderr else None,
                })

                if proc.returncode != 0:
                    results["success"] = False

            except Exception as e:
                logger.error("command_execution_failed", command=cmd, error=str(e))
                results["errors"].append({"command": cmd, "error": str(e)})
                results["success"] = False

    return results
