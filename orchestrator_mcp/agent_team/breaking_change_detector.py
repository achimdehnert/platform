"""
orchestrator_mcp/agent_team/breaking_change_detector.py

Fixes applied (see REVIEW-ADR-107):
  L-3: shell=False + shlex.split() in all subprocess calls — no injection risk
  B-1: sqlmigrate-based breaking change detection (unchanged, already correct)
  M-4: get_deployment_gate_level returns auto_eligible flag for clarity

Breaking changes (trigger Gate-2-Approval):
  - DROP TABLE / DROP COLUMN
  - ALTER COLUMN ... NOT NULL (without default)
  - RENAME TABLE / RENAME COLUMN

Safe changes (Gate-2-Automatic):
  - ADD COLUMN (with default or nullable)
  - CREATE TABLE / CREATE INDEX
  - ALTER COLUMN ADD DEFAULT
"""

from __future__ import annotations

import logging
import re
import shlex
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class ChangeType(str, Enum):
    SAFE = "safe"
    BREAKING = "breaking"
    UNKNOWN = "unknown"


@dataclass
class MigrationChange:
    sql_statement: str
    change_type: ChangeType
    reason: str

    @property
    def is_breaking(self) -> bool:
        return self.change_type == ChangeType.BREAKING


@dataclass
class MigrationAnalysis:
    app_label: str
    migration_name: str
    changes: list[MigrationChange] = field(default_factory=list)
    sql_output: str = ""
    error: str | None = None

    @property
    def has_breaking_changes(self) -> bool:
        return any(c.is_breaking for c in self.changes)

    @property
    def breaking_changes(self) -> list[MigrationChange]:
        return [c for c in self.changes if c.is_breaking]

    def summary(self) -> str:
        if self.error:
            return (
                f"ERROR analysing {self.app_label}.{self.migration_name}: "
                f"{self.error}"
            )
        if not self.changes:
            return (
                f"{self.app_label}.{self.migration_name}: "
                "no schema changes detected"
            )
        status = "BREAKING" if self.has_breaking_changes else "SAFE"
        details = "; ".join(c.reason for c in self.breaking_changes)
        return (
            f"{self.app_label}.{self.migration_name}: {status} "
            f"— {details or 'additive changes only'}"
        )


# ---------------------------------------------------------------------------
# SQL Pattern Matching
# ---------------------------------------------------------------------------

_BREAKING_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^\s*DROP\s+TABLE\b", re.IGNORECASE), "DROP TABLE detected"),
    (re.compile(r"^\s*DROP\s+COLUMN\b", re.IGNORECASE), "DROP COLUMN detected"),
    (
        re.compile(r"^\s*ALTER\s+TABLE.*DROP\s+COLUMN", re.IGNORECASE),
        "ALTER TABLE DROP COLUMN",
    ),
    (
        re.compile(r"^\s*ALTER\s+TABLE.*RENAME\b", re.IGNORECASE),
        "RENAME operation detected",
    ),
    (re.compile(r"^\s*RENAME\s+TABLE\b", re.IGNORECASE), "RENAME TABLE detected"),
    (
        re.compile(
            r"ALTER\s+TABLE.*ALTER\s+COLUMN.*SET\s+NOT\s+NULL",
            re.IGNORECASE,
        ),
        "SET NOT NULL without DEFAULT (existing NULLs would fail)",
    ),
    (
        re.compile(r"ALTER\s+TABLE.*ALTER\s+COLUMN.*TYPE\b", re.IGNORECASE),
        "Column type change (may truncate data)",
    ),
]

_SAFE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^\s*CREATE\s+TABLE\b", re.IGNORECASE), "CREATE TABLE (additive)"),
    (
        re.compile(r"^\s*ALTER\s+TABLE.*ADD\s+COLUMN", re.IGNORECASE),
        "ADD COLUMN (additive)",
    ),
    (re.compile(r"^\s*CREATE\s+INDEX\b", re.IGNORECASE), "CREATE INDEX (additive)"),
    (
        re.compile(r"^\s*ALTER\s+TABLE.*ADD\s+CONSTRAINT", re.IGNORECASE),
        "ADD CONSTRAINT",
    ),
    (
        re.compile(
            r"^\s*ALTER\s+TABLE.*ALTER\s+COLUMN.*SET\s+DEFAULT", re.IGNORECASE
        ),
        "SET DEFAULT",
    ),
]


def _classify_sql_statement(statement: str) -> MigrationChange:
    """Classify a single SQL statement as safe or breaking."""
    stmt = statement.strip()
    if not stmt or stmt.startswith("--"):
        return MigrationChange(
            sql_statement=stmt, change_type=ChangeType.SAFE, reason="comment/empty"
        )

    for pattern, reason in _BREAKING_PATTERNS:
        if pattern.search(stmt):
            return MigrationChange(
                sql_statement=stmt,
                change_type=ChangeType.BREAKING,
                reason=reason,
            )

    for pattern, reason in _SAFE_PATTERNS:
        if pattern.search(stmt):
            return MigrationChange(
                sql_statement=stmt,
                change_type=ChangeType.SAFE,
                reason=reason,
            )

    return MigrationChange(
        sql_statement=stmt,
        change_type=ChangeType.UNKNOWN,
        reason="unclassified — manual review recommended",
    )


# ---------------------------------------------------------------------------
# Migration SQL Extractor — Fix L-3: shell=False + shlex.split()
# ---------------------------------------------------------------------------


def get_pending_migrations(
    manage_py: str = "python manage.py",
    cwd: Path | None = None,
) -> list[tuple[str, str]]:
    """
    Returns list of (app_label, migration_name) tuples for unapplied migrations.
    Fix L-3: uses shlex.split + shell=False — no command injection risk.
    """
    cmd = shlex.split(manage_py) + ["migrate", "--plan"]
    result = subprocess.run(
        cmd,
        shell=False,
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    migrations: list[tuple[str, str]] = []
    for line in result.stdout.splitlines():
        match = re.match(r"\s*\[\s*\]\s+([\w]+)\.([\w]+)", line)
        if match:
            migrations.append((match.group(1), match.group(2)))
    return migrations


def analyse_migration(
    app_label: str,
    migration_name: str,
    manage_py: str = "python manage.py",
    cwd: Path | None = None,
) -> MigrationAnalysis:
    """
    Runs sqlmigrate to get SQL, then classifies each statement.
    Fix L-3: shell=False + shlex.split().
    Fix B-1: This is the actual dry-run / breaking-change detection.
    """
    cmd = shlex.split(manage_py) + ["sqlmigrate", app_label, migration_name]
    result = subprocess.run(
        cmd,
        shell=False,
        capture_output=True,
        text=True,
        cwd=cwd,
    )

    analysis = MigrationAnalysis(
        app_label=app_label,
        migration_name=migration_name,
        sql_output=result.stdout,
    )

    if result.returncode != 0:
        analysis.error = result.stderr.strip()
        logger.error(
            "sqlmigrate failed for %s.%s: %s",
            app_label,
            migration_name,
            analysis.error,
        )
        return analysis

    statements = [s.strip() for s in result.stdout.split(";") if s.strip()]
    analysis.changes = [_classify_sql_statement(s) for s in statements]

    if analysis.has_breaking_changes:
        logger.warning(
            "Breaking changes detected in %s.%s: %s",
            app_label,
            migration_name,
            [c.reason for c in analysis.breaking_changes],
        )

    return analysis


def analyse_all_pending_migrations(
    manage_py: str = "python manage.py",
    cwd: Path | None = None,
) -> list[MigrationAnalysis]:
    """
    Analyses all pending migrations.

    Usage in CD workflow:
        analyses = analyse_all_pending_migrations()
        gate_level, auto_eligible, reason = get_deployment_gate_level(analyses)
        if not auto_eligible:
            trigger_gate2_approval()
        else:
            proceed_with_auto_deployment()
    """
    pending = get_pending_migrations(manage_py=manage_py, cwd=cwd)
    if not pending:
        logger.info("No pending migrations found.")
        return []

    return [
        analyse_migration(app_label, migration_name, manage_py=manage_py, cwd=cwd)
        for app_label, migration_name in pending
    ]


def get_deployment_gate_level(
    analyses: list[MigrationAnalysis],
) -> tuple[int, bool, str]:
    """
    Returns (gate_level, auto_eligible, reason).
    Fix M-4: auto_eligible flag added — semantically clear.

    gate_level is always 2 (all deployments are Gate-2).
    auto_eligible=True  => no human approval needed (additive changes only)
    auto_eligible=False => Gate-2 human approval required
    """
    if not analyses:
        return 2, True, "No pending migrations — auto-deployment eligible"

    breaking = [a for a in analyses if a.has_breaking_changes]
    unknown = [
        a for a in analyses
        if any(c.change_type == ChangeType.UNKNOWN for c in a.changes)
    ]
    errors = [a for a in analyses if a.error]

    if errors:
        names = ", ".join(
            f"{a.app_label}.{a.migration_name}" for a in errors
        )
        return 2, False, (
            f"sqlmigrate errors in {names} — manual review required"
        )

    if breaking:
        names = ", ".join(
            f"{a.app_label}.{a.migration_name}" for a in breaking
        )
        return 2, False, f"Breaking changes in: {names} — Gate-2-Approval required"

    if unknown:
        names = ", ".join(
            f"{a.app_label}.{a.migration_name}" for a in unknown
        )
        return 2, False, f"Unclassified SQL in: {names} — manual review recommended"

    return 2, True, "Additive migrations only — auto-deployment eligible"
