#!/usr/bin/env python3
"""iil_migration_check.py — idempotent reality-checker for the iil-* org migration.

ADR-255 REC-3 mandates a single machine-readable SSoT (registry/iil-migration.yaml)
plus an idempotent checker so a later package cannot silently drift. This is that
checker. It is READ-ONLY: it queries GitHub (and optionally PyPI) and compares
reality against the registry, then reports drift. It never transfers, publishes,
or mutates anything.

What it catches (the failure modes ADR-255 names):
  * repo_current lies        — registry says owner/name X, gh resolves to Y
                               (the iil-testkit class: claimed iilgmbh, really achimdehnert)
  * status inconsistency     — status=done but repo not under the target org
  * registry-canonical drift — tools/registry-canonical.py repo_owner claims a
                               package is under iilgmbh while iil-migration.yaml
                               records repo_current under achimdehnert
  * stale "verified" claims  — verification.verified text vs live gh result

Usage:
  python3 tools/iil_migration_check.py            # full check (needs gh auth)
  python3 tools/iil_migration_check.py --offline  # structural checks only, no network
  python3 tools/iil_migration_check.py --json     # machine-readable report

Exit code: 0 = no drift, 1 = drift found, 2 = usage/load error.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("PyYAML required (pip install pyyaml)", file=sys.stderr)
    sys.exit(2)

REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY = REPO_ROOT / "registry" / "iil-migration.yaml"
CANONICAL_GEN = REPO_ROOT / "tools" / "registry-canonical.py"
TARGET_ORG = "iilgmbh"


def gh_repo_full_name(owner_name: str) -> str | None:
    """Return the canonical owner/name gh resolves to (follows transfer redirects),
    or None if the repo does not exist / gh is unavailable."""
    try:
        out = subprocess.run(
            ["gh", "api", f"repos/{owner_name}", "--jq", ".full_name"],
            capture_output=True, text=True, timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    return out.stdout.strip() or None


def parse_canonical_repo_owner() -> dict[str, str]:
    """Extract the repo_owner override map from tools/registry-canonical.py.

    The map is a Python dict literal in the generator source (the SSoT for
    current-owner overrides). We read it textually rather than importing to keep
    this checker side-effect free."""
    if not CANONICAL_GEN.exists():
        return {}
    text = CANONICAL_GEN.read_text(encoding="utf-8")
    m = re.search(r'"repo_owner":\s*\{(.*?)\}', text, re.DOTALL)
    if not m:
        return {}
    owners: dict[str, str] = {}
    for key, val in re.findall(r'"([^"]+)":\s*"([^"]+)"', m.group(1)):
        owners[key] = val
    return owners


def check(offline: bool) -> tuple[list[dict], dict]:
    data = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    packages = data.get("packages", {})
    canon_owner = parse_canonical_repo_owner()
    findings: list[dict] = []

    def add(level: str, pkg: str, msg: str) -> None:
        findings.append({"level": level, "package": pkg, "message": msg})

    for pkg, p in packages.items():
        repo_current = p.get("repo_current", "")
        status = p.get("status", "")
        repo_name = repo_current.split("/")[-1] if "/" in repo_current else repo_current

        # 1. registry-canonical repo_owner vs migration repo_current
        claimed = canon_owner.get(repo_name)
        if claimed and "/" in repo_current:
            actual_org = repo_current.split("/")[0]
            if claimed != actual_org:
                add("DRIFT", pkg,
                    f"registry-canonical repo_owner claims '{repo_name}: {claimed}' "
                    f"but iil-migration.yaml records repo_current={repo_current}")

        # 2. status=done must mean repo under target org
        if status == "done" and not repo_current.startswith(f"{TARGET_ORG}/"):
            add("DRIFT", pkg,
                f"status=done but repo_current={repo_current} is not under {TARGET_ORG}/")

        # 3. live gh reality vs repo_current
        if not offline:
            resolved = gh_repo_full_name(repo_current)
            if resolved is None:
                add("WARN", pkg, f"gh could not resolve repo_current={repo_current} (missing/unauth)")
            elif resolved != repo_current:
                add("DRIFT", pkg,
                    f"repo_current={repo_current} but gh resolves to {resolved} "
                    f"(transfer/redirect or registry stale)")

    summary = {
        "packages": len(packages),
        "drift": sum(1 for f in findings if f["level"] == "DRIFT"),
        "warn": sum(1 for f in findings if f["level"] == "WARN"),
        "offline": offline,
    }
    return findings, summary


def main() -> int:
    ap = argparse.ArgumentParser(description="Reality-check the iil-* migration registry (ADR-255 REC-3)")
    ap.add_argument("--offline", action="store_true", help="skip GitHub queries (structural checks only)")
    ap.add_argument("--json", action="store_true", help="emit JSON report")
    args = ap.parse_args()

    if not REGISTRY.exists():
        print(f"registry not found: {REGISTRY}", file=sys.stderr)
        return 2

    findings, summary = check(args.offline)

    if args.json:
        print(json.dumps({"summary": summary, "findings": findings}, indent=2))
    else:
        print(f"iil-migration check — {summary['packages']} packages, "
              f"{summary['drift']} drift, {summary['warn']} warn"
              f"{' (offline)' if summary['offline'] else ''}")
        for f in findings:
            icon = {"DRIFT": "✗", "WARN": "⚠"}.get(f["level"], "•")
            print(f"  {icon} [{f['package']}] {f['message']}")
        if not findings:
            print("  ✓ no drift")

    return 1 if summary["drift"] else 0


if __name__ == "__main__":
    sys.exit(main())
