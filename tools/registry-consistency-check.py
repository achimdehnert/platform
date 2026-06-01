#!/usr/bin/env python3
"""registry-consistency-check — macht die Registry-Doppelquelle sichtbar (ADR-234 P0).

Es existieren zwei Registries mit UNTERSCHIEDLICHEM Scope (kein Superset):
  - scripts/repo-registry.yaml  — flaches Flotten-Inventar (alle Repos, operativ:
                                  type/prod_url/port/health/pypi/staging_url)
  - registry/repos.yaml         — kuratiertes deployed-Subset (domains[].systems[]),
                                  Deploy-/Governance-Detail (lifecycle/tenancy/coverage/deploy)

Solange beide „Single Source of Truth" beanspruchen, kann jede Adoptions-/Live-Repo-
Messung je nach Quelle eine andere Zahl liefern. Dieser Check ELIMINIERT die Dual-Quelle
noch NICHT (das ist die Union-Canonical-Migration, ADR-234 P0) — er macht die Divergenz
deterministisch SICHTBAR, damit sie nicht still driftet:

  1. Repos, die in genau EINER Registry stehen.
  2. Überlappende Repos, deren gemeinsame Felder (z.B. `type`) DIVERGIEREN.

INFORMATIONAL by default (exit 0) — nach Repo-Health-Regel-Disziplin (neue Regeln starten
als SUGGEST, gegen echte Repos validiert, 0 FP, kein Hard-Fail der die Flotte einfriert).
`--strict` macht Divergenz zum Exit-1 (für spätere, gewollte Gates).

Deterministisch, kein LLM. ADR-234 P0 / KONZ-platform-001.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
FLAT = REPO_ROOT / "scripts" / "repo-registry.yaml"
RICH = REPO_ROOT / "registry" / "repos.yaml"


def load_flat(path: Path) -> dict[str, dict]:
    d = yaml.safe_load(path.read_text())
    repos = d.get("repos", d) if isinstance(d, dict) else {}
    return {k: (v or {}) for k, v in repos.items() if isinstance(v, dict)}


def load_rich(path: Path) -> dict[str, dict]:
    d = yaml.safe_load(path.read_text())
    out: dict[str, dict] = {}
    for dom in d.get("domains", []) if isinstance(d, dict) else []:
        for s in dom.get("systems", []):
            key = s.get("repo") or s.get("name")
            if key:
                out[key] = s
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Registry-Konsistenz-Check (ADR-234 P0).")
    ap.add_argument("--strict", action="store_true", help="Exit 1 bei Divergenz (Default: informational).")
    args = ap.parse_args()

    if not FLAT.exists() or not RICH.exists():
        print(f"FEHLER: Registry fehlt ({FLAT} / {RICH}).", file=sys.stderr)
        return 2

    flat, rich = load_flat(FLAT), load_rich(RICH)
    fset, rset = set(flat), set(rich)
    only_flat = sorted(fset - rset)
    only_rich = sorted(rset - fset)

    # Feld-Divergenz auf der Schnittmenge (gemeinsam vorhandenes Feld 'type').
    type_mismatch = []
    for r in sorted(fset & rset):
        ft, rt = flat[r].get("type"), rich[r].get("type")
        if ft is not None and rt is not None and ft != rt:
            type_mismatch.append((r, ft, rt))

    lines = [
        "# Registry-Konsistenz (ADR-234 P0)",
        "",
        f"- `scripts/repo-registry.yaml` (flach): **{len(flat)}** Repos",
        f"- `registry/repos.yaml` (reich): **{len(rich)}** Systeme",
        f"- Schnittmenge: **{len(fset & rset)}**",
        "",
        f"## Nur in flach — fehlt in reich ({len(only_flat)})",
        *([f"- `{r}`" for r in only_flat] or ["- (keine)"]),
        "",
        f"## Nur in reich — fehlt in flach ({len(only_rich)})",
        *([f"- `{r}`" for r in only_rich] or ["- (keine)"]),
        "",
        f"## `type`-Divergenz auf der Schnittmenge ({len(type_mismatch)})",
        *([f"- `{r}`: flach=`{ft}` ≠ reich=`{rt}`" for r, ft, rt in type_mismatch] or ["- (keine)"]),
        "",
        "_Dual-SSoT noch aktiv — Auflösung = Union-Canonical (ADR-234 P0). Dieser Check macht Drift sichtbar._",
    ]
    report = "\n".join(lines)
    print(report)

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write(report + "\n")

    diverged = bool(only_flat or only_rich or type_mismatch)
    if args.strict and diverged:
        print("\n[strict] Divergenz vorhanden → exit 1.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
