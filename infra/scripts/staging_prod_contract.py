#!/usr/bin/env python3
"""Staging/Prod Infra Contract — enforceable lint over ports.yaml.

Enforces ADR-157/ADR-198 as red/green, no prose. Exit 1 on any violation
→ CI-gateable. Single source of truth = infra/ports.yaml `services:`.

Rules:
  R1 registry completeness — each app-hub has domain_prod, domain_staging,
     container_name.
  R2 ADR-198 SSL hard rule — a domain_staging under iil.pet MUST be a
     single-label subdomain (Cloudflare Universal SSL covers exactly 1
     label). I.e. the part before `.iil.pet` contains NO dot.
     `staging-writing.iil.pet` ok · `staging.iil.pet` ok ·
     `staging.writing.iil.pet` FORBIDDEN. Own domains (not iil.pet)
     exempt (LE wildcard).
  R3 naming convention (advisory, not a gate) — iil.pet staging label
     should be `staging` or `staging-<app>`.

Usage: python3 staging_prod_contract.py [path/to/ports.yaml]
"""
import sys
from pathlib import Path

import yaml


def main() -> int:
    p = Path(sys.argv[1] if len(sys.argv) > 1 else
             Path(__file__).resolve().parents[1] / "ports.yaml")
    services = (yaml.safe_load(p.read_text()) or {}).get("services") or {}
    violations: list[str] = []   # hard → exit 1
    advisories: list[str] = []   # R3 → reported, does not fail CI

    for name, s in services.items():
        if not isinstance(s, dict):
            continue
        for field in ("domain_prod", "domain_staging", "container_name"):
            if not s.get(field):
                violations.append(f"R1 {name}: missing `{field}`")
        ds = s.get("domain_staging") or ""
        if ds.endswith(".iil.pet"):
            label = ds[: -len(".iil.pet")]
            if "." in label:
                violations.append(
                    f"R2 {name}: domain_staging `{ds}` is a 2+-label "
                    f"subdomain under iil.pet — Cloudflare Universal SSL "
                    f"covers 1 label only (ADR-198)")
            elif label != "staging" and not label.startswith("staging-"):
                advisories.append(
                    f"R3 {name}: `{ds}` SSL-ok but off-convention "
                    f"(expected `staging` or `staging-<app>`)")

    for a in advisories:
        print(f"  ⚠️  {a}")
    if violations:
        print(f"❌ Staging/Prod contract: {len(violations)} violation(s)")
        for v in violations:
            print(f"  - {v}")
        return 1
    print(f"✅ Staging/Prod contract: {len(services)} services conform "
          f"({len(advisories)} advisory)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
