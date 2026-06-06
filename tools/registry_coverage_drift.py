#!/usr/bin/env python3
"""registry_coverage_drift.py — KONZ-001 R5 „Liar-Liste" (read-only, Pilot Sprint 1, Issue #488).

Vergleicht die **Org-Ground-Truth** (`gh repo list`) gegen die **SSoT** `registry/canonical.yaml`
und meldet die Widerspruchsmenge — NICHT die Grün-Liste, sondern die *Lügen*-Liste:
- ENROLLMENT-GAP: Repos, die auf GitHub existieren, aber NICHT in canonical eingeschrieben sind
  (der „unsichtbare" Repo — die tödlichste Lücke, KONZ-001 §5b R8/§6).
- PHANTOM: canonical-Einträge ohne Org-Repo (stale/falsch).

Read-only, **advisory** (exit 0). `--strict` → exit 1 bei Drift>0 — für den späteren gegateten
Einsatz (KONZ-001 R2b, hinter org-weitem ADR); im Pilot Sprint 1 bewusst NICHT gated.

KONZ-platform-001 §5 R5 / §5b. Reiner Kern (`compute_drift`) ist netz-frei → R7-Fault-Injection (s. test).
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

import yaml

CANONICAL = Path(__file__).resolve().parents[1] / "registry" / "canonical.yaml"


def canonical_fullnames(canonical_path: str, org: str) -> set:
    d = yaml.safe_load(open(canonical_path))
    out = set()
    for name, entry in (d.get("repos") or {}).items():
        entry = entry or {}
        gh = (entry.get("rich") or {}).get("github")
        out.add(gh if gh else f"{org}/{name}")
    return out


def gh_repo_fullnames(org: str) -> set:
    r = subprocess.run(
        ["gh", "repo", "list", org, "--limit", "300", "--json", "nameWithOwner",
         "-q", ".[].nameWithOwner"],
        capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"gh repo list {org} fehlgeschlagen: {r.stderr[:200]}")
    return {ln.strip() for ln in r.stdout.splitlines() if ln.strip()}


def compute_drift(org_repos: set, canonical_repos: set) -> dict:
    """Reine Widerspruchsmenge — testbar OHNE Netz (R7 Fault-Injection)."""
    return {
        "enrollment_gap": sorted(org_repos - canonical_repos),
        "phantom": sorted(canonical_repos - org_repos),
        "covered": sorted(org_repos & canonical_repos),
        "drift_score": len(org_repos - canonical_repos) + len(canonical_repos - org_repos),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--org", default=None, help="Default: meta.server.github_org aus canonical")
    ap.add_argument("--canonical", default=str(CANONICAL))
    ap.add_argument("--format", choices=["text", "json"], default="text")
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 bei Drift>0 (gated — Default ist read-only/advisory)")
    a = ap.parse_args()

    d = yaml.safe_load(open(a.canonical))
    org = a.org or (d.get("meta") or {}).get("server", {}).get("github_org", "achimdehnert")
    canon = canonical_fullnames(a.canonical, org)
    orgs = gh_repo_fullnames(org)
    res = compute_drift(orgs, canon)

    if a.format == "json":
        print(json.dumps({"org": org, **res}, indent=2, ensure_ascii=False))
    else:
        print(f"=== registry_coverage_drift (KONZ-001 R5) — org={org} ===")
        print(f"  Org-Repos (gh): {len(orgs)} · canonical: {len(canon)} · covered: {len(res['covered'])}")
        print(f"  ENROLLMENT-GAP (auf Org, NICHT in SSoT): {len(res['enrollment_gap'])}")
        for r in res["enrollment_gap"]:
            print(f"    + {r}")
        print(f"  PHANTOM (in SSoT, kein Org-Repo): {len(res['phantom'])}")
        for r in res["phantom"]:
            print(f"    - {r}")
        print(f"=== DRIFT-SCORE: {res['drift_score']} (0 = sauber) ===")
    sys.exit(1 if (a.strict and res["drift_score"]) else 0)


if __name__ == "__main__":
    main()
