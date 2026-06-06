#!/usr/bin/env python3
"""registry_coverage_drift.py — KONZ-001 R5 „Liar-Liste" (read-only, Pilot Sprint 1, Issue #488).

Vergleicht die **Org-Ground-Truth über ALLE Owner** (`gh repo list` je Owner) gegen die **SSoT**
`registry/canonical.yaml` und meldet die Widerspruchsmenge — die *Lügen*-Liste, nicht die Grün-Liste:
- ENROLLMENT-GAP: existiert bei einem Owner, NICHT in canonical.
- PHANTOM: in canonical, bei keinem Owner.
- MIGRATED: gleicher Repo-Name unter *anderem* Owner als canonical sagt (Owner-Drift) — z. B.
  canonical `achimdehnert/iil-fieldprefill`, real `iilgmbh/iil-fieldprefill`. Eigene Klasse, weil es
  KEIN echtes Enrollment-Loch ist, sondern eine laufende Org-Migration (KONZ-002).

**Multi-Owner (v2):** `achimdehnert` ist ein User, `iilgmbh` die Enterprise-Org — Repos liegen während
der Migration auf beiden. Single-Owner-Ground-Truth lügt selbst (Befund 2026-06-06). Default-Owner-Set
deckt alle vier ab.

Read-only, **advisory** (exit 0); `--strict` → exit 1 (gated, KONZ-001 R2b, hinter org-weitem ADR).
Reiner Kern (`compute_drift`) ist netz-frei → R7-Fault-Injection (s. test).
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

import yaml

CANONICAL = Path(__file__).resolve().parents[1] / "registry" / "canonical.yaml"
DEFAULT_OWNERS = ["achimdehnert", "iilgmbh", "ttz-lif", "meiki-lra"]


def _basename(full: str) -> str:
    return full.split("/", 1)[-1]


def canonical_fullnames(canonical_path: str, org: str) -> set:
    d = yaml.safe_load(open(canonical_path))
    out = set()
    for name, entry in (d.get("repos") or {}).items():
        entry = entry or {}
        gh = (entry.get("rich") or {}).get("github")
        out.add(gh if gh else f"{org}/{name}")
    return out


def gh_repo_fullnames(owner: str) -> set:
    r = subprocess.run(
        ["gh", "repo", "list", owner, "--limit", "300", "--json", "nameWithOwner",
         "-q", ".[].nameWithOwner"],
        capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"gh repo list {owner} fehlgeschlagen: {r.stderr[:200]}")
    return {ln.strip() for ln in r.stdout.splitlines() if ln.strip()}


def compute_drift(ground: set, canonical: set) -> dict:
    """Reine Widerspruchsmenge inkl. Owner-Migration — testbar OHNE Netz (R7 Fault-Injection)."""
    raw_gap = ground - canonical
    raw_phantom = canonical - ground
    gap_by_base = {}
    for fn in raw_gap:
        gap_by_base.setdefault(_basename(fn), []).append(fn)
    migrated = []
    for pfn in raw_phantom:
        base = _basename(pfn)
        if base in gap_by_base:
            migrated.append({"repo": base, "canonical": pfn, "reality": sorted(gap_by_base[base])[0]})
    migrated_bases = {m["repo"] for m in migrated}
    enrollment_gap = sorted(fn for fn in raw_gap if _basename(fn) not in migrated_bases)
    phantom = sorted(fn for fn in raw_phantom if _basename(fn) not in migrated_bases)
    return {
        "enrollment_gap": enrollment_gap,
        "phantom": phantom,
        "migrated": sorted(migrated, key=lambda m: m["repo"]),
        "covered": sorted(ground & canonical),
        "drift_score": len(enrollment_gap) + len(phantom) + len(migrated),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--owners", default=",".join(DEFAULT_OWNERS),
                    help="Komma-Liste der GitHub-Owner (User+Orgs), die Ground-Truth bilden")
    ap.add_argument("--canonical", default=str(CANONICAL))
    ap.add_argument("--format", choices=["text", "json"], default="text")
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 bei Drift>0 (gated — Default ist read-only/advisory)")
    a = ap.parse_args()

    d = yaml.safe_load(open(a.canonical))
    canon_org = (d.get("meta") or {}).get("server", {}).get("github_org", "achimdehnert")
    canon = canonical_fullnames(a.canonical, canon_org)
    owners = [o.strip() for o in a.owners.split(",") if o.strip()]
    ground = set()
    for o in owners:
        ground |= gh_repo_fullnames(o)
    res = compute_drift(ground, canon)

    if a.format == "json":
        print(json.dumps({"owners": owners, "canonical_org": canon_org, **res}, indent=2, ensure_ascii=False))
    else:
        print(f"=== registry_coverage_drift (KONZ-001 R5) — owners={','.join(owners)} ===")
        print(f"  Ground-Truth (alle Owner): {len(ground)} · canonical: {len(canon)} · covered: {len(res['covered'])}")
        print(f"  ENROLLMENT-GAP (existiert, NICHT in SSoT): {len(res['enrollment_gap'])}")
        for r in res["enrollment_gap"]:
            print(f"    + {r}")
        print(f"  MIGRATED (Owner-Drift — canonical-Owner stale): {len(res['migrated'])}")
        for m in res["migrated"]:
            print(f"    ~ {m['repo']}: canonical={m['canonical']} → real={m['reality']}")
        print(f"  PHANTOM (in SSoT, bei keinem Owner): {len(res['phantom'])}")
        for r in res["phantom"]:
            print(f"    - {r}")
        print(f"=== DRIFT-SCORE: {res['drift_score']} (0 = sauber) ===")
    sys.exit(1 if (a.strict and res["drift_score"]) else 0)


if __name__ == "__main__":
    main()
