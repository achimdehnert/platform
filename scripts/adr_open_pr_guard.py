#!/usr/bin/env python3
"""ADR open-PR collision guard — catches IN-FLIGHT ADR-number collisions.

`adr_next_number.py --check` only sees the current tree (this PR merged against
main), so two OPEN PRs that each introduce a *different* ADR with the *same*
number pass individually and collide only when the second tries to merge. That
race caused the ADR-221..227 renumber churn (2026-05).

This guard closes the gap at PR time: it compares the ADR numbers claimed by
every open PR and fails if a number is claimed by >= 2 open PRs with *different*
files (distinct slugs = distinct ADRs = real collision). A PR that merely edits
an existing ADR (same filename) is not flagged.

Interim guard. The structural fix is merge-time number allocation (amends
ADR-065). Requires `gh` + GH_TOKEN; skips gracefully if unavailable.

Usage (CI, PR context):
    GH_TOKEN=... PR_NUMBER=<n> GITHUB_REPOSITORY=owner/repo \\
        python3 scripts/adr_open_pr_guard.py
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from collections import defaultdict

ADR_RE = re.compile(r"(?:^|/)ADR-(\d{3,4})-([^/]+)\.md$", re.IGNORECASE)


def gh(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["gh", *args], capture_output=True, text=True)


def main() -> int:
    repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    pr_number = os.environ.get("PR_NUMBER", "").strip()
    if not repo or not pr_number:
        print("ℹ️  no PR context (GITHUB_REPOSITORY/PR_NUMBER) — open-PR guard skipped")
        return 0

    listed = gh("pr", "list", "--repo", repo, "--state", "open",
                "--json", "number", "--limit", "200")
    if listed.returncode != 0:
        print(f"ℹ️  gh unavailable — open-PR guard skipped ({listed.stderr.strip()[:100]})")
        return 0

    open_prs = [p["number"] for p in json.loads(listed.stdout or "[]")]
    # number -> { filename -> set(pr) }
    claims: dict[int, dict[str, set[int]]] = defaultdict(lambda: defaultdict(set))
    for n in open_prs:
        fr = gh("pr", "view", str(n), "--repo", repo, "--json", "files")
        if fr.returncode != 0:
            continue
        for f in json.loads(fr.stdout or "{}").get("files", []):
            m = ADR_RE.search(f.get("path", ""))
            if m:
                num = int(m.group(1))
                fname = f"ADR-{m.group(1)}-{m.group(2)}.md"
                claims[num][fname].add(n)

    fail = 0
    for num in sorted(claims):
        files = claims[num]
        if len(files) >= 2:  # same number, >=2 distinct files across open PRs
            involved = sorted({pr for prs in files.values() for pr in prs})
            if int(pr_number) in involved:
                fail = 1
                detail = "; ".join(
                    f"{fn} (PR {sorted(prs)})" for fn, prs in sorted(files.items())
                )
                print(
                    f"::error::ADR-{num:03d} is claimed by multiple open PRs with "
                    f"different files — in-flight collision: {detail}. "
                    f"Renumber one to the next free number "
                    f"(python3 scripts/adr_next_number.py --next)."
                )

    if not fail:
        print(
            f"✅ no in-flight ADR-number collisions across {len(open_prs)} open "
            f"PRs involving PR #{pr_number}"
        )
    return fail


if __name__ == "__main__":
    sys.exit(main())
