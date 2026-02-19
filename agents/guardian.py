"""
agents/guardian.py — Architecture Guardian (Agent A2)

Prüft Pull Requests gegen 4 Architektur-Regeln:
  G-001: Model-Änderung ohne Migration?
  G-002: Public API Signatur geändert?
  G-003: Neues Model ohne tenant_id?
  G-004: PR > 400 Zeilen?

Nutzung:
  python -m agents.guardian --pr 42 --repo achimdehnert/bfagent
  python -m agents.guardian --diff /path/to/diff.patch

Gate-Integration:
  G-001, G-004 → Gate 1 (Auto-Warn, PR-Kommentar)
  G-002, G-003 → Gate 2 (Human Approval Required)
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("guardian")


class Gate(IntEnum):
    AUTO_WARN = 1
    HUMAN_APPROVAL = 2


@dataclass
class Violation:
    """Eine Regel-Verletzung."""

    rule: str
    gate: Gate
    file: str
    line: int | None
    message: str
    suggestion: str | None = None


@dataclass
class GuardianResult:
    """Ergebnis der Guardian-Analyse."""

    violations: list[Violation] = field(default_factory=list)
    files_checked: int = 0
    lines_added: int = 0
    lines_removed: int = 0

    @property
    def passed(self) -> bool:
        return len(self.violations) == 0

    @property
    def max_gate(self) -> int:
        if not self.violations:
            return 0
        return max(v.gate for v in self.violations)

    @property
    def blocking(self) -> bool:
        return any(v.gate >= Gate.HUMAN_APPROVAL for v in self.violations)

    def to_markdown(self) -> str:
        if self.passed:
            return (
                "## \u2705 Architecture Guardian \u2014 Passed\n\n"
                f"Checked {self.files_checked} files, "
                f"+{self.lines_added}/-{self.lines_removed} lines. "
                "No violations found."
            )

        lines = [
            "## \u26a0\ufe0f Architecture Guardian \u2014 Violations Found\n",
            f"Checked {self.files_checked} files, "
            f"+{self.lines_added}/-{self.lines_removed} lines.\n",
        ]

        gate1 = [v for v in self.violations if v.gate == Gate.AUTO_WARN]
        gate2 = [v for v in self.violations if v.gate == Gate.HUMAN_APPROVAL]

        if gate2:
            lines.append("### \ud83d\udd34 Requires Human Approval (Gate 2)\n")
            for v in gate2:
                loc = f"`{v.file}:{v.line}`" if v.line else f"`{v.file}`"
                lines.append(f"- **{v.rule}**: {v.message} ({loc})")
                if v.suggestion:
                    lines.append(f"  - \ud83d\udca1 {v.suggestion}")

        if gate1:
            lines.append("\n### \ud83d\udfe1 Auto-Warning (Gate 1)\n")
            for v in gate1:
                loc = f"`{v.file}:{v.line}`" if v.line else f"`{v.file}`"
                lines.append(f"- **{v.rule}**: {v.message} ({loc})")
                if v.suggestion:
                    lines.append(f"  - \ud83d\udca1 {v.suggestion}")

        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "max_gate": self.max_gate,
            "blocking": self.blocking,
            "files_checked": self.files_checked,
            "lines_added": self.lines_added,
            "lines_removed": self.lines_removed,
            "violations": [
                {
                    "rule": v.rule,
                    "gate": v.gate,
                    "file": v.file,
                    "line": v.line,
                    "message": v.message,
                    "suggestion": v.suggestion,
                }
                for v in self.violations
            ],
        }


def parse_diff(diff_text: str) -> list[dict[str, Any]]:
    """Parst unified diff in Datei-Abschnitte."""
    files: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    for line in diff_text.splitlines():
        if line.startswith("diff --git"):
            if current:
                files.append(current)
            match = re.search(r"b/(.+)$", line)
            path = match.group(1) if match else "unknown"
            current = {
                "path": path,
                "added_lines": [],
                "removed_lines": [],
                "hunks": [],
            }
        elif current is not None:
            if line.startswith("@@"):
                match = re.search(r"\+(\d+)", line)
                if match:
                    current["hunks"].append(int(match.group(1)))
            elif line.startswith("+") and not line.startswith("+++"):
                current["added_lines"].append(line[1:])
            elif line.startswith("-") and not line.startswith("---"):
                current["removed_lines"].append(line[1:])

    if current:
        files.append(current)

    return files


def check_g001_model_without_migration(
    files: list[dict[str, Any]],
) -> list[Violation]:
    """G-001: Model-\u00c4nderung ohne Migration?"""
    violations: list[Violation] = []
    model_files = [
        f for f in files
        if f["path"].endswith("models.py")
        or f["path"].endswith("models_testing.py")
    ]
    migration_files = [
        f for f in files
        if "/migrations/" in f["path"]
    ]

    model_patterns = [
        r"class\s+\w+\(.*Model\)",
        r"models\.\w+Field",
        r"CharField|IntegerField|ForeignKey|TextField",
        r"BooleanField|DateTimeField|UUIDField|JSONField",
    ]

    for mf in model_files:
        added = "\n".join(mf["added_lines"])
        has_model_change = any(
            re.search(p, added) for p in model_patterns
        )
        if has_model_change and not migration_files:
            violations.append(Violation(
                rule="G-001",
                gate=Gate.AUTO_WARN,
                file=mf["path"],
                line=mf["hunks"][0] if mf["hunks"] else None,
                message=(
                    "Model-\u00c4nderung erkannt aber keine "
                    "Migration in diesem PR"
                ),
                suggestion=(
                    "F\u00fchre `python manage.py makemigrations` "
                    "aus und f\u00fcge die Migration dem PR hinzu"
                ),
            ))

    return violations


def check_g002_api_signature_changed(
    files: list[dict[str, Any]],
) -> list[Violation]:
    """G-002: Public API Signatur ge\u00e4ndert?"""
    violations: list[Violation] = []

    api_patterns = [
        (r"class\s+\w+Serializer", "Serializer"),
        (r"class\s+\w+ViewSet", "ViewSet"),
        (r"class\s+\w+APIView", "APIView"),
        (r"path\s*\(\s*['\"]api/", "URL-Pattern"),
    ]

    for f in files:
        if not (
            f["path"].endswith(".py")
            and any(
                x in f["path"]
                for x in ["serializers", "views", "urls", "api"]
            )
        ):
            continue

        removed = "\n".join(f["removed_lines"])
        for pattern, label in api_patterns:
            if re.search(pattern, removed):
                violations.append(Violation(
                    rule="G-002",
                    gate=Gate.HUMAN_APPROVAL,
                    file=f["path"],
                    line=f["hunks"][0] if f["hunks"] else None,
                    message=(
                        f"Public API {label} wurde ge\u00e4ndert/entfernt"
                    ),
                    suggestion=(
                        "Pr\u00fcfe ob bestehende Clients betroffen "
                        "sind. Nutze Expand/Contract Pattern "
                        "(ADR-042) f\u00fcr Breaking Changes"
                    ),
                ))

    return violations


def check_g003_model_without_tenant_id(
    files: list[dict[str, Any]],
) -> list[Violation]:
    """G-003: Neues Model ohne tenant_id?"""
    violations: list[Violation] = []

    for f in files:
        if not f["path"].endswith("models.py"):
            continue

        added = "\n".join(f["added_lines"])
        new_models = re.findall(
            r"class\s+(\w+)\(.*Model\)", added,
        )

        for model_name in new_models:
            if model_name.startswith("_"):
                continue
            if "Abstract" in model_name:
                continue

            if "tenant_id" not in added:
                violations.append(Violation(
                    rule="G-003",
                    gate=Gate.HUMAN_APPROVAL,
                    file=f["path"],
                    line=f["hunks"][0] if f["hunks"] else None,
                    message=(
                        f"Neues Model `{model_name}` ohne "
                        "`tenant_id` Feld"
                    ),
                    suggestion=(
                        "Jedes User-Data-Model MUSS "
                        "`tenant_id = UUIDField(db_index=True)` "
                        "haben (Platform-Regel \u00a73.3)"
                    ),
                ))

    return violations


def check_g004_pr_too_large(
    files: list[dict[str, Any]],
    threshold: int = 400,
) -> list[Violation]:
    """G-004: PR > 400 Zeilen?"""
    total_added = sum(len(f["added_lines"]) for f in files)
    total_removed = sum(len(f["removed_lines"]) for f in files)
    total_changed = total_added + total_removed

    if total_changed > threshold:
        return [Violation(
            rule="G-004",
            gate=Gate.AUTO_WARN,
            file="(gesamt)",
            line=None,
            message=(
                f"PR hat {total_changed} ge\u00e4nderte Zeilen "
                f"(Limit: {threshold})"
            ),
            suggestion=(
                "Gro\u00dfe PRs sind schwerer zu reviewen. "
                "Erw\u00e4ge Aufteilen in kleinere PRs"
            ),
        )]

    return []


def analyze_diff(diff_text: str) -> GuardianResult:
    """Hauptfunktion: Analysiert einen Diff gegen alle Regeln."""
    files = parse_diff(diff_text)
    result = GuardianResult(
        files_checked=len(files),
        lines_added=sum(len(f["added_lines"]) for f in files),
        lines_removed=sum(len(f["removed_lines"]) for f in files),
    )

    result.violations.extend(check_g001_model_without_migration(files))
    result.violations.extend(check_g002_api_signature_changed(files))
    result.violations.extend(check_g003_model_without_tenant_id(files))
    result.violations.extend(check_g004_pr_too_large(files))

    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Architecture Guardian \u2014 PR Analyse",
    )
    parser.add_argument(
        "--diff", type=str,
        help="Pfad zu Diff-Datei (oder stdin)",
    )
    parser.add_argument(
        "--format", choices=["markdown", "json"],
        default="markdown",
    )
    parser.add_argument(
        "--threshold", type=int, default=400,
        help="Max ge\u00e4nderte Zeilen (G-004)",
    )
    args = parser.parse_args()

    if args.diff:
        diff_text = Path(args.diff).read_text(encoding="utf-8")
    else:
        diff_text = sys.stdin.read()

    result = analyze_diff(diff_text)

    if args.format == "json":
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(result.to_markdown())

    sys.exit(1 if result.blocking else 0)


if __name__ == "__main__":
    main()
