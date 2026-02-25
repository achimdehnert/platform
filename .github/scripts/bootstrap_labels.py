#!/usr/bin/env python3
"""
Bootstrap GitHub Labels — ADR-085 Issue Triage (platform).

Usage:
    GITHUB_TOKEN=ghp_xxx python bootstrap_labels.py
    GITHUB_TOKEN=ghp_xxx python bootstrap_labels.py --dry-run
"""

import argparse
import json
import os
import sys
from urllib import error, request

REPO = os.environ.get("GITHUB_REPOSITORY", "achimdehnert/platform")
TOKEN = os.environ.get("GITHUB_TOKEN", "")

LABELS: list[tuple[str, str, str]] = [
    # Type
    ("type:feature",   "0075ca", "New feature or enhancement"),
    ("type:bug",       "d73a4a", "Something is broken"),
    ("type:refactor",  "0075ca", "Code improvement without behavior change"),
    ("type:test",      "0075ca", "Test coverage improvement"),
    ("type:docs",      "0075ca", "Documentation update"),
    ("type:adr",       "0075ca", "Architecture Decision Record"),
    ("type:chore",     "0075ca", "Maintenance / tooling"),
    # Complexity
    ("complexity:trivial",       "e4e669", "< 1h, single line change"),
    ("complexity:simple",        "e4e669", "< 1 day, one component"),
    ("complexity:moderate",      "e4e669", "1–3 days, multiple components"),
    ("complexity:complex",       "e4e669", "3–5 days, cross-app changes"),
    ("complexity:architectural", "e4e669", "> 5 days, system-wide impact"),
    # Risk
    ("risk:high",     "d93f0b", "High risk — careful review needed"),
    ("risk:critical", "b60205", "Critical risk — security/data impact"),
    # App (platform-spezifisch)
    ("app:adr",             "0e8a16", "Architecture Decision Records"),
    ("app:docs",            "0e8a16", "Documentation"),
    ("app:governance",      "0e8a16", "Governance rules"),
    ("app:task-scorer",     "0e8a16", "Task Scorer package"),
    ("app:django-tenancy",  "0e8a16", "Django Tenancy package"),
    ("app:docs-agent",      "0e8a16", "Docs Agent package"),
    ("app:contracts",       "0e8a16", "Shared Contracts"),
    ("app:shared",          "0e8a16", "Shared utilities"),
    # Scope
    ("scope:packages",        "c5def5", "Package affected"),
    ("scope:tools",           "c5def5", "Tooling affected"),
    ("scope:ci",              "c5def5", "CI/CD pipeline affected"),
    ("scope:infrastructure",  "c5def5", "Infrastructure / provisioning"),
]


def create_label(headers, repo, name, color, description, dry_run):
    if dry_run:
        return "dry-run"
    url = f"https://api.github.com/repos/{repo}/labels"
    payload = json.dumps({"name": name, "color": color, "description": description}).encode()
    req = request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with request.urlopen(req, timeout=15) as resp:
            return "created" if resp.status in (200, 201) else f"unexpected:{resp.status}"
    except error.HTTPError as e:
        return "exists" if e.code == 422 else f"error:{e.code}"
    except Exception as e:
        return f"error:{e}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--repo", default=REPO)
    parser.add_argument("--token", default=TOKEN)
    args = parser.parse_args()

    print(f"\n=== Bootstrap GitHub Labels — {args.repo} ===")
    print(f"  Labels  : {len(LABELS)}")
    print(f"  Dry-run : {args.dry_run}\n")

    if not args.dry_run and not args.token:
        print("ERROR: GITHUB_TOKEN nicht gesetzt.")
        return 1

    headers = {
        "Authorization": f"Bearer {args.token}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    created, exists, errors = [], [], []
    for name, color, description in LABELS:
        status = create_label(headers, args.repo, name, color, description, args.dry_run)
        if status == "created":
            created.append(name); print(f"  + {name}")
        elif status in ("exists", "dry-run"):
            exists.append(name); print(f"  {'~' if args.dry_run else '='} {name}")
        else:
            errors.append((name, status)); print(f"  ! {name}  [{status}]", file=sys.stderr)

    print()
    if args.dry_run:
        print(f"[dry-run] Würde {len(LABELS)} Labels in '{args.repo}' anlegen.")
    else:
        print(f"Fertig: erstellt={len(created)}, vorhanden={len(exists)}, fehler={len(errors)}")

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
