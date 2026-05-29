#!/usr/bin/env python3
"""Static lint for MCP-call signatures in .windsurf/workflows/*.md skills.

Catches common signature-drift bugs discovered during /adr-curator + /adr-challenger
dogfood-testing (2026-05-15, PR #168):

- adr_query expects `question=`, not `query=`
- adr_explain expects `rule_id=`, not `adr_id=`
- adr_validate is directory-wide; `adr_id_or_path=` is wrong
- adr_diff is set/temporal mode; pair-wise `adr_a=/adr_b=` is wrong
- adr_impact direction is file -> ADRs (warn if comments imply reverse)

Exits non-zero on any violation. Designed for CI (paths: .windsurf/workflows/**).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

WORKFLOWS_DIR = Path(".windsurf/workflows")

# (regex, message) — match on the MCP call site inside skill markdown
RULES: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"adr_query\([^)]*\bquery\s*="),
        "adr_query expects `question=`, not `query=`",
    ),
    (
        re.compile(r"adr_explain\([^)]*\badr_id\s*="),
        "adr_explain expects `rule_id=`, not `adr_id=`",
    ),
    (
        re.compile(r"adr_validate\([^)]*\b(adr_id|adr_id_or_path|path)\s*="),
        "adr_validate accepts only `adr_dir=` (validates ALL ADRs in directory)",
    ),
    (
        re.compile(r"adr_diff\([^)]*\b(adr_a|adr_b)\s*="),
        "adr_diff is set/temporal mode — no pair-wise `adr_a=/adr_b=`",
    ),
    (
        re.compile(r"adr_impact\([^)]*\b(adr_id|scope)\s*="),
        "adr_impact accepts `file_path=` and optional `repo=` — direction is file -> ADRs, NOT reverse",
    ),
]


def lint_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    violations: list[str] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        # Skip comment lines explaining the rule (look for explicit "NOT" or "wrong" markers)
        lowered = line.lower()
        if any(marker in lowered for marker in ("not `", "wrong", "❌", "achtung", "warnung")):
            continue
        for pattern, msg in RULES:
            if pattern.search(line):
                violations.append(f"{path}:{line_no}: {msg}\n    → {line.strip()}")
    return violations


def main() -> int:
    if not WORKFLOWS_DIR.exists():
        print(f"::error::{WORKFLOWS_DIR} not found", file=sys.stderr)
        return 2

    skill_files = sorted(WORKFLOWS_DIR.glob("*.md"))
    if not skill_files:
        print(f"::warning::No skill files in {WORKFLOWS_DIR}", file=sys.stderr)
        return 0

    all_violations: list[str] = []
    for f in skill_files:
        all_violations.extend(lint_file(f))

    if all_violations:
        print("MCP signature violations found:\n", file=sys.stderr)
        for v in all_violations:
            print(v, file=sys.stderr)
            print("", file=sys.stderr)
        print(
            f"::error::Found {len(all_violations)} violation(s) across {len(skill_files)} skill file(s)",
            file=sys.stderr,
        )
        return 1

    print(f"OK: {len(skill_files)} skill files clean ({len(RULES)} rules checked)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
