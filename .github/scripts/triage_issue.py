#!/usr/bin/env python3
"""
Issue Triage Script — ADR-085 (platform).

Usage:
    python .github/scripts/triage_issue.py \
        --issue-number 42 \
        --title "Add ADR-086" \
        --body "We need..."
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from issue_triage_service import IssueTriageService


def main() -> int:
    parser = argparse.ArgumentParser(description="Triage a GitHub issue")
    parser.add_argument("--issue-number", type=int, required=True)
    parser.add_argument("--title", type=str, required=True)
    parser.add_argument("--body", type=str, default="")
    parser.add_argument("--dry-run", action="store_true", default=False)
    parser.add_argument("--tier", type=str, default="budget")
    args = parser.parse_args()

    service = IssueTriageService(
        github_token=os.environ.get("GITHUB_TOKEN", ""),
        github_repo=os.environ.get("GITHUB_REPOSITORY", "achimdehnert/platform"),
        tier=args.tier,
        dry_run=args.dry_run,
    )

    print(f"Triage Issue #{args.issue_number}: {args.title[:60]}")
    result = service.triage(
        issue_number=args.issue_number,
        title=args.title,
        body=args.body or "",
    )

    print(f"  Tasks erkannt : {result.tasks_found}")
    print(f"  Labels        : {result.labels}")
    print(f"  GitHub updated: {result.github_updated}")
    print(f"  Modell        : {result.model_used} / {result.tier_used}")

    if result.warnings:
        for w in result.warnings:
            print(f"  [warn] {w}")

    print(result.summary)
    return 0  # Exit 0 always — MCP unavailable in CI is expected, not a failure


if __name__ == "__main__":
    sys.exit(main())
