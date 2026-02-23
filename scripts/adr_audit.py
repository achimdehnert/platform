#!/usr/bin/env python3
"""ADR Audit — zeigt alle Konflikte, Doppelnummern und Lücken.

Usage:
    python3 scripts/adr_audit.py              # vollständiger Audit
    python3 scripts/adr_audit.py --fix-hints  # zeigt konkrete Rename-Befehle
    python3 scripts/adr_audit.py --json       # JSON-Output für CI
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Reuse core logic from adr_next_number
sys.path.insert(0, str(Path(__file__).parent))
from adr_next_number import (
    ADR_DIR,
    REPO_RANGES,
    get_conflicts,
    get_gaps,
    get_next_free,
    scan_adr_dir,
)


def build_report(fix_hints: bool = False) -> dict:
    mapping = scan_adr_dir()
    conflicts = get_conflicts(mapping)

    report: dict = {
        "total_files": sum(len(v) for v in mapping.values()),
        "unique_numbers": len(mapping),
        "conflicts": {},
        "gaps_by_repo": {},
        "next_free_by_repo": {},
        "fix_commands": [],
    }

    # Conflicts
    for num, files in sorted(conflicts.items()):
        report["conflicts"][f"ADR-{num:03d}"] = [f.name for f in files]

    # Gaps + next free per repo
    for repo, (lo, hi) in REPO_RANGES.items():
        gaps = get_gaps(mapping, repo)
        if gaps:
            report["gaps_by_repo"][repo] = [f"ADR-{n:03d}" for n in gaps]
        try:
            report["next_free_by_repo"][repo] = f"ADR-{get_next_free(mapping, repo):03d}"
        except ValueError:
            report["next_free_by_repo"][repo] = "FULL"

    # Fix hints: suggest rename commands for conflicts
    if fix_hints and conflicts:
        for num, files in sorted(conflicts.items()):
            # Keep the first file (alphabetically), rename others
            keeper = files[0]
            for duplicate in files[1:]:
                # Determine which repo the file belongs to based on content hint
                # Default: use platform next free
                new_num = get_next_free(mapping, "platform")
                new_name = duplicate.name.replace(
                    f"ADR-{num:03d}-", f"ADR-{new_num:03d}-"
                )
                report["fix_commands"].append(
                    f"git mv docs/adr/{duplicate.name} docs/adr/{new_name}"
                )
                # Mark new number as used so next conflict gets a different number
                mapping[new_num] = [ADR_DIR / new_name]

    return report


def print_human_report(report: dict, fix_hints: bool = False) -> None:
    print("=" * 65)
    print("ADR Audit Report")
    print("=" * 65)
    print(f"Total ADR files : {report['total_files']}")
    print(f"Unique numbers  : {report['unique_numbers']}")
    print()

    if report["conflicts"]:
        print(f"🚫 CONFLICTS — {len(report['conflicts'])} duplicate number(s):")
        for num, files in report["conflicts"].items():
            print(f"  {num}:")
            for f in files:
                print(f"    → {f}")
        print()
    else:
        print("✅ No duplicate numbers.\n")

    has_gaps = any(report["gaps_by_repo"].values())
    if has_gaps:
        print("⚠️  GAPS (skipped numbers):")
        for repo, gaps in report["gaps_by_repo"].items():
            if gaps:
                print(f"  {repo}: {', '.join(gaps)}")
        print()
    else:
        print("✅ No gaps detected.\n")

    print("Next free numbers per repo:")
    for repo, next_num in report["next_free_by_repo"].items():
        print(f"  {repo:12s} → {next_num}")
    print()

    if fix_hints and report["fix_commands"]:
        print("🔧 Suggested fix commands (review before running):")
        for cmd in report["fix_commands"]:
            print(f"  {cmd}")
        print()

    print("=" * 65)


def main() -> int:
    args = sys.argv[1:]
    fix_hints = "--fix-hints" in args
    as_json = "--json" in args

    report = build_report(fix_hints=fix_hints)

    if as_json:
        print(json.dumps(report, indent=2))
    else:
        print_human_report(report, fix_hints=fix_hints)

    return 1 if report["conflicts"] else 0


if __name__ == "__main__":
    sys.exit(main())
