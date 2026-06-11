#!/usr/bin/env python3
"""Signal R measurement for the evidence-discipline policy (platform issue #256).

Signal R = (marker-claims with a cited check in the same logical turn,
            preceding the claim) / (all marker-claims)

A "logical turn" = all consecutive assistant JSONL entries between two user
entries in a session transcript. Tool-use blocks (Bash/Read/grep) appearing
before a text block that contains a marker-claim count as "cited checks".

Usage:
    python3 tools/measure-evidence-discipline.py [JSONL_PATH ...]
    python3 tools/measure-evidence-discipline.py          # scans ~/.claude/projects/
    python3 tools/measure-evidence-discipline.py --repo platform  # one project

Emits:
    R = <fraction>  (<checked>/<total> marker-claim turns, across N sessions)
    Baseline: ~6 documented incidents (assert-before-check or never checked).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Iterator

# ---------------------------------------------------------------------------
# Marker patterns — from policies/evidence-discipline.md "Fires when" section
# ---------------------------------------------------------------------------
MARKER_PATTERNS: list[re.Pattern[str]] = [
    # Named artifact
    re.compile(r'\bPR\s+#\d+\b', re.IGNORECASE),
    re.compile(r'\bcommit\s+[0-9a-f]{6,}\b', re.IGNORECASE),
    re.compile(r'\bADR-\d+\b', re.IGNORECASE),
    re.compile(r'\bfile\s+\S+\.(py|sh|yml|yaml|md|json|toml)\b', re.IGNORECASE),
    re.compile(r'\bmemory\s+\w+', re.IGNORECASE),
    # Status / outcome
    re.compile(r'\bdone\s*[✓✔]|\bfertig\s*[✓✔]', re.IGNORECASE),
    re.compile(r'\bfestgehalten\b', re.IGNORECASE),
    re.compile(r'\bdeployed\b', re.IGNORECASE),
    re.compile(r'\bCOMPLETE\b'),
    re.compile(r'\bgesichert\b', re.IGNORECASE),
    re.compile(r'\berfolgreich\b', re.IGNORECASE),
    re.compile(r'\bgreen\b|\bgrün\b', re.IGNORECASE),
    re.compile(r'\bfailed\b|\bfehler\b', re.IGNORECASE),
    # Number / date with specificity
    re.compile(r'\$\d+\.\d+'),                    # cost like $2.294
    re.compile(r'\d{1,3}[,./]\d{1,3}[,./]\d{2,4}'),  # date
    re.compile(r'\d+\s*(ms|s|min|Minuten)\b', re.IGNORECASE),
    # Root-cause labels
    re.compile(r'\bpre-existing\b|\bvorbestehend\b', re.IGNORECASE),
    re.compile(r'\bnot my code\b|\bnicht mein code\b', re.IGNORECASE),
    re.compile(r'\binfra smell\b', re.IGNORECASE),
    # Magnitude word
    re.compile(r'\bändert alles\b', re.IGNORECASE),
]

# Tools that count as a "cited check"
CHECK_TOOL_NAMES: frozenset[str] = frozenset({
    "Bash", "Read", "grep", "find",
    "mcp__github__get_file_contents",
    "mcp__github__list_issues",
    "mcp__github__get_pull_request",
    "mcp__github__search_code",
})


def _has_marker(text: str) -> bool:
    return any(p.search(text) for p in MARKER_PATTERNS)


def _extract_text_blocks(content: list) -> list[str]:
    return [
        c["text"]
        for c in content
        if isinstance(c, dict) and c.get("type") == "text" and c.get("text")
    ]


def _has_check_tool(content: list) -> bool:
    for c in content:
        if isinstance(c, dict) and c.get("type") == "tool_use":
            if c.get("name") in CHECK_TOOL_NAMES:
                return True
            # Also catch mcp__* Bash-style tools
            name = c.get("name", "")
            if name.startswith("mcp__") and any(
                k in name for k in ("run", "bash", "exec", "search", "get", "list")
            ):
                return True
    return False


def _is_real_user_message(obj: dict) -> bool:
    """True iff this is a genuine user prompt, not a tool_result callback.

    In CC transcripts, tool results are delivered as type=user entries whose
    content contains tool_result blocks.  Only real human prompts (empty
    content or plain text) should bound a logical turn.
    """
    content = obj.get("message", obj).get("content", [])
    if isinstance(content, str):
        return True
    if isinstance(content, list):
        # Has any tool_result block → it's a callback, not a real message
        return not any(
            isinstance(c, dict) and c.get("type") == "tool_result"
            for c in content
        )
    return True


def _iter_logical_turns(jsonl_path: Path) -> Iterator[list[dict]]:
    """Yield logical turns: all entries between two real user messages.

    A logical turn = everything between two genuine human prompts (type=user
    with no tool_result blocks).  Tool-call/result interleave (assistant →
    user[tool_result] → assistant) stays inside the same turn.
    """
    current: list[dict] = []
    with jsonl_path.open(encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                continue
            t = obj.get("type")
            if t == "user" and _is_real_user_message(obj):
                if current:
                    yield current
                current = []
            elif t == "assistant":
                current.append(obj)
            # tool_result user entries: include in current turn so ordering
            # is preserved, but they are not assistant entries and carry no
            # text claims of their own.
    if current:
        yield current


def measure_file(jsonl_path: Path) -> tuple[int, int]:
    """Return (checked_claims, total_claims) for one transcript file."""
    total = checked = 0
    for turn_entries in _iter_logical_turns(jsonl_path):
        # Collect tool-use blocks and text blocks in order
        saw_check = False
        turn_has_marker = False
        turn_checked = False
        for entry in turn_entries:
            msg = entry.get("message", entry)
            content = msg.get("content", [])
            if not isinstance(content, list):
                content = []
            if _has_check_tool(content):
                saw_check = True
            for text in _extract_text_blocks(content):
                if _has_marker(text):
                    turn_has_marker = True
                    if saw_check:
                        turn_checked = True
        if turn_has_marker:
            total += 1
            if turn_checked:
                checked += 1
    return checked, total


def scan_project_dir(project_dir: Path) -> tuple[int, int]:
    checked_total = total_total = 0
    files = list(project_dir.glob("*.jsonl"))
    for f in files:
        c, t = measure_file(f)
        checked_total += c
        total_total += t
    return checked_total, total_total


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("paths", nargs="*", help="JSONL files or project dirs to scan")
    ap.add_argument("--repo", help="Repo slug, e.g. 'platform' → scans ~/.claude/projects/*platform*/")
    ap.add_argument("--verbose", "-v", action="store_true")
    args = ap.parse_args()

    targets: list[Path] = []

    if args.repo:
        slug = args.repo.replace("/", "-").replace("_", "-")
        base = Path.home() / ".claude" / "projects"
        matches = [p for p in base.iterdir() if slug in p.name]
        if not matches:
            print(f"No project dir found matching repo '{args.repo}' under {base}", file=sys.stderr)
            return 2
        targets.extend(matches)
    elif args.paths:
        targets = [Path(p) for p in args.paths]
    else:
        base = Path.home() / ".claude" / "projects"
        targets = list(base.iterdir()) if base.exists() else []

    grand_checked = grand_total = 0
    session_count = 0

    for target in sorted(targets):
        if target.is_dir():
            files = list(target.glob("*.jsonl"))
            for f in files:
                c, t = measure_file(f)
                if args.verbose and t > 0:
                    r = c / t
                    print(f"  {f.parent.name}/{f.name}: R={r:.2f} ({c}/{t})")
                grand_checked += c
                grand_total += t
                session_count += 1
        elif target.is_file() and target.suffix == ".jsonl":
            c, t = measure_file(target)
            if args.verbose and t > 0:
                r = c / t
                print(f"  {target.name}: R={r:.2f} ({c}/{t})")
            grand_checked += c
            grand_total += t
            session_count += 1

    print(f"\nSignal R measurement — evidence-discipline policy")
    print(f"Sessions scanned : {session_count}")
    print(f"Marker-claim turns (total): {grand_total}")
    print(f"Checked before claim:       {grand_checked}")
    if grand_total > 0:
        r = grand_checked / grand_total
        print(f"R = {r:.3f}  ({grand_checked}/{grand_total})")
        print()
        if r < 0.5:
            print("⚠  R below 0.5 — policy effectiveness unproven; consider cut or patch.")
        elif r < 0.7:
            print("~  R between 0.5 and 0.7 — policy is improving, not yet strong.")
        else:
            print("✓  R ≥ 0.70 — policy is working.")
        print()
        print("Baseline: ~6 incidents (assert-before-check or never checked).")
        print("First measurement target: 2026-06-15 (~10 sessions post-merge).")
    else:
        print("R = n/a  (no marker-claim turns found in scanned transcripts)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
