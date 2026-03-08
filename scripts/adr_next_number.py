#!/usr/bin/env python3
"""ADR Number Guard — single source of truth for ADR numbering.

Usage:
    python3 scripts/adr_next_number.py         # next free number
    python3 scripts/adr_next_number.py --audit # all conflicts + gaps
    python3 scripts/adr_next_number.py --check # exit 1 if conflicts
    python3 scripts/adr_next_number.py --next  # next free (explicit)
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

ADR_DIR = Path(__file__).parent.parent / "docs" / "adr"
ADR_PATTERN = re.compile(r"^ADR-(\d{3,4})-(.+)\.md$", re.IGNORECASE)

# Range concept ABANDONED after ADR-059 (confirmed by ADR-107).
# Kept for gap-detection only. get_next_free() uses GLOBAL maximum.
REPO_RANGES: dict[str, tuple[int, int]] = {
    "platform":    (1,    99),
    "bfagent":     (100, 149),
    "travel-beat": (150, 199),
    "mcp-hub":     (200, 249),
    "risk-hub":    (250, 299),
    "cad-hub":     (300, 349),
    "pptx-hub":    (350, 399),
    "trading-hub": (400, 449),
    "shared":      (450, 499),
}

# Safety ceiling — prevents infinite loops on malformed filenames
_GLOBAL_MAX = 9999


def scan_adr_dir(adr_dir: Path = ADR_DIR) -> dict[int, list[Path]]:
    """Scan ADR directory; return mapping of number to file list."""
    mapping: dict[int, list[Path]] = defaultdict(list)
    for f in sorted(adr_dir.glob("ADR-*.md")):
        m = ADR_PATTERN.match(f.name)
        if m:
            num = int(m.group(1))
            mapping[num].append(f)
    return dict(mapping)


def get_conflicts(
    mapping: dict[int, list[Path]],
) -> dict[int, list[Path]]:
    """Return numbers with more than one file (duplicates)."""
    return {
        num: files
        for num, files in mapping.items()
        if len(files) > 1
    }


def get_next_free(
    mapping: dict[int, list[Path]],
    repo: str = "platform",  # noqa: ARG001
) -> int:
    """Next free ADR number — global max strategy.

    The repo-range concept was abandoned after ADR-059 and confirmed
    by ADR-107. All new ADRs receive the next free GLOBAL number.

    The repo parameter is kept only for API compatibility — it no
    longer restricts which numbers are considered.

    Strategy: global max(used) + 1, then skip any already-used
    numbers. Gaps are intentional and must never be reused.
    """
    all_used = set(mapping.keys())
    if not all_used:
        return 1
    candidate = max(all_used) + 1
    while candidate in all_used and candidate <= _GLOBAL_MAX:
        candidate += 1
    if candidate > _GLOBAL_MAX:
        raise ValueError("No free ADR numbers left below global max")
    return candidate


def get_gaps(
    mapping: dict[int, list[Path]],
    repo: str = "platform",
) -> list[int]:
    """Return gap numbers in the repo range (for audit only)."""
    lo, hi = REPO_RANGES.get(repo, (1, 99))
    used = {n for n in mapping if lo <= n <= hi}
    if not used:
        return []
    return [n for n in range(lo, max(used) + 1) if n not in used]


def format_audit(
    mapping: dict[int, list[Path]],
    repo: str = "platform",
) -> str:
    """Return a human-readable audit report."""
    lines: list[str] = []
    conflicts = get_conflicts(mapping)
    gaps = get_gaps(mapping, repo)
    next_num = get_next_free(mapping, repo)

    lines.append("=" * 60)
    lines.append("ADR Number Guard — Audit Report")
    lines.append("=" * 60)
    lines.append(f"ADR directory : {ADR_DIR}")
    lines.append(
        f"Total ADRs    : {sum(len(v) for v in mapping.values())}"
    )
    lines.append(f"Unique numbers: {len(mapping)}")
    lines.append(f"Next free (global): ADR-{next_num:03d}")
    lines.append("")

    if conflicts:
        lines.append(
            f"CONFLICTS ({len(conflicts)} duplicate numbers):"
        )
        for num, files in sorted(conflicts.items()):
            lines.append(f"  ADR-{num:03d}:")
            for f in files:
                lines.append(f"    -> {f.name}")
        lines.append("")
    else:
        lines.append("No duplicate numbers found.")
        lines.append("")

    if gaps:
        gap_str = ", ".join(f"ADR-{n:03d}" for n in gaps)
        lines.append(
            f"GAPS in {repo} range ({len(gaps)} missing): {gap_str}"
        )
        lines.append("")
    else:
        lines.append(f"No gaps in {repo} range.")
        lines.append("")

    lines.append("=" * 60)
    return "\n".join(lines)


def main() -> int:
    args = sys.argv[1:]
    repo = "platform"

    for i, arg in enumerate(args):
        if arg == "--repo" and i + 1 < len(args):
            repo = args[i + 1]

    mapping = scan_adr_dir()
    conflicts = get_conflicts(mapping)

    if "--audit" in args:
        print(format_audit(mapping, repo))
        return 1 if conflicts else 0

    if "--check" in args:
        if conflicts:
            print("ADR number conflicts detected:")
            for num, files in sorted(conflicts.items()):
                names = ", ".join(f.name for f in files)
                print(f"  ADR-{num:03d}: {names}")
            print(
                "\nRun: python3 scripts/adr_next_number.py --audit"
                " for full report."
            )
            return 1
        print("No ADR number conflicts.")
        return 0

    # Default / --next: print next free number
    try:
        next_num = get_next_free(mapping, repo)
        print(f"ADR-{next_num:03d}")
        return 0
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
