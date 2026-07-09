#!/usr/bin/env python3
"""retro-kpis.py — Längsschnitt-Hebel für /session-retro (ADR-light, kein Dep).

Liest die YAML-Frontmatter aller `session-retro-*.md` (außer den
`-extern-`-Briefings) aus `<repo>/docs/retros/` (git-durable, KONZ-platform-010)
UND `~/shared/` (Skill-Schreibpfad) — dedupliziert nach Dateiname —, zählt
`recurring_findings`-Slugs ÜBER Retros hinweg und
eskaliert jeden Slug mit **Zähler ≥2 → GATE-PFLICHT**. Trendet zusätzlich
`refuted_rate` gegen das Skill-KPI-Band (>0.8 Finder zu lasch · <0.2 Falsifikation
Theater) und die 6 Score-Dimensionen.

Bewusst stdlib-only (Frontmatter-Mini-Parser statt PyYAML) — das Tool muss in
jeder session-retro-Phase-4 ohne Setup laufen.

Aufruf:
    python3 tools/retro_kpis.py                 # Default: docs/retros/ + ~/shared/
    python3 tools/retro_kpis.py --dir <pfad>    # nur dies(e) Verzeichnis(se), mehrfach angebbar
    python3 tools/retro_kpis.py --min-band 3    # refuted_rate-Band erst ab N Retros werten

Exit-Code 0 immer (Report-Tool, kein Gate-Enforcer — das Gate ist der gemeldete
GATE-PFLICHT-Block, den der Mensch in einen PR überführt).
"""
from __future__ import annotations

import argparse
import glob
import os
import re
from collections import Counter, defaultdict

LIST_KEYS = {"recurring_findings", "gate_candidates", "repo_scope"}
SCALAR_KEYS = {"date", "session_id", "footprint", "refuted_rate",
               "findings_total", "findings_survived",
               "phase3_refuted", "pre_refuted"}
SCORE_KEYS = ["zielerreichung", "architektur_design", "code_konventionstreue",
              "risiko_debt", "prozess_effizienz", "entscheidungsqualitaet"]


def parse_frontmatter(text: str) -> dict | None:
    """Minimaler Frontmatter-Parser: erstes ---...----Block, flache keys + scores-Block."""
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return None
    body = m.group(1)
    out: dict = {"scores": {}}
    in_scores = False
    for raw in body.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indented = raw[0] in " \t"
        line = raw.strip()
        if line.rstrip(":") == "scores" and line.endswith(":"):
            in_scores = True
            continue
        if in_scores and indented and ":" in line:
            k, v = line.split(":", 1)
            k, v = k.strip(), v.strip()
            if k in SCORE_KEYS:
                try:
                    out["scores"][k] = int(v)
                except ValueError:
                    pass
            continue
        in_scores = False
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        k, v = k.strip(), v.strip()
        if k in LIST_KEYS:
            v = v.strip("[]")
            out[k] = [s.strip().strip("'\"") for s in v.split(",") if s.strip()]
        elif k in SCALAR_KEYS:
            out[k] = v.strip("'\"")
    return out


def load_reports(directories) -> list[dict]:
    """Load retro frontmatter from one or more directories.

    Accepts a single dir (str) or a list of dirs. Reports are deduplicated by
    filename across dirs (first dir wins) so the git-durable ``docs/retros/``
    home (KONZ-platform-010) and the skill's ``~/shared/`` write path can both
    be scanned without double-counting a report that lives in both.
    """
    if isinstance(directories, str):
        directories = [directories]
    reports = []
    seen: set[str] = set()
    for directory in directories:
        pattern = os.path.join(directory, "session-retro-*.md")
        for path in sorted(glob.glob(pattern)):
            base = os.path.basename(path)
            if "-extern-" in base:
                continue  # Phase-6-Briefings sind keine Retros
            if base in seen:
                continue  # gleicher Report in beiden Dirs → nur einmal zählen
            try:
                fm = parse_frontmatter(open(path, encoding="utf-8").read())
            except OSError:
                continue
            if fm is None:
                continue
            fm["_path"] = base
            seen.add(base)
            reports.append(fm)
    return reports


def main() -> int:
    ap = argparse.ArgumentParser(description="Längsschnitt-KPIs über session-retro-Reports")
    # KONZ-platform-010: durable Heimat = git docs/retros/ (nicht ~/shared, ungebackupt).
    # Default liest BEIDE — docs/retros/ (git-durable, KONZ-010) UND ~/shared/ (der Pfad,
    # nach dem die /session-retro-Skill schreibt) — dedupliziert nach Dateiname, damit ein
    # frisch nach ~/shared geschriebener Report nicht durch die Pfad-Drift unsichtbar bleibt.
    _repo_retros = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "retros")
    _shared = os.path.expanduser("~/shared")
    ap.add_argument("--dir", action="append", default=None,
                    help="Verzeichnis(se) mit session-retro-*.md; mehrfach angebbar. "
                         "Default: <repo>/docs/retros (KONZ-010) + ~/shared (Skill-Schreibpfad).")
    ap.add_argument("--min-band", type=int, default=3,
                    help="refuted_rate-Band erst ab N Retros bewerten (default 3)")
    args = ap.parse_args()

    dirs = args.dir if args.dir else [_repo_retros, _shared]
    reports = load_reports(dirs)
    if not reports:
        print(f"Keine session-retro-Reports in {', '.join(dirs)} gefunden.")
        return 0

    print(f"# Längsschnitt über {len(reports)} Retro-Reports ({', '.join(dirs)})\n")

    # --- Recurring-Findings-Zähler über Retros → Gate-Eskalation ---
    slug_reports: dict[str, list[str]] = defaultdict(list)
    for r in reports:
        for slug in r.get("recurring_findings", []):
            slug_reports[slug].append(r.get("session_id", r["_path"]))
    gated = {s: v for s, v in slug_reports.items() if len(v) >= 2}

    print("## recurring_findings (Zähler über Retros)")
    if not slug_reports:
        print("(keine recurring_findings deklariert)")
    for slug, where in sorted(slug_reports.items(), key=lambda kv: -len(kv[1])):
        mark = "🚨 GATE-PFLICHT" if len(where) >= 2 else "·"
        print(f"  {mark}  {slug}  ×{len(where)}  [{', '.join(where)}]")
    if gated:
        print(f"\n→ {len(gated)} Slug(s) ≥2 ⇒ Gate-PR-Pflicht: "
              f"{', '.join(sorted(gated))}. Als Gate (Hook/CI/Skill) verankern, "
              f"nicht als N-tes Memo.")

    # --- refuted_rate-Band ---
    rates = []
    for r in reports:
        try:
            rates.append((r.get("session_id", r["_path"]), float(r["refuted_rate"])))
        except (KeyError, ValueError):
            pass
    print("\n## refuted_rate-Trend (Skill-KPI)")
    if rates:
        print("  " + " · ".join(f"{sid}:{val:.2f}" for sid, val in rates[-8:]))
        n = len(rates)
        if n >= args.min_band:
            recent = [v for _, v in rates[-args.min_band:]]
            if all(v > 0.8 for v in recent):
                print(f"  ⚠️  letzte {args.min_band} >0.8 → Finder zu lasch (widerlegbares Stroh).")
            elif all(v < 0.2 for v in recent):
                print(f"  ⚠️  letzte {args.min_band} <0.2 → Falsifikation ist Theater (widerlegt nie).")
            else:
                print(f"  ✅ Band gesund (weder {args.min_band}× >0.8 noch <0.2).")
        else:
            print(f"  (erst ab {args.min_band} Retros als Band gewertet — bisher {n})")
    else:
        print("  (keine refuted_rate-Werte parsebar)")

    # --- Score-Mittel je Dimension ---
    print("\n## Score-Mittel je Dimension (1–5)")
    sums: Counter = Counter()
    cnts: Counter = Counter()
    for r in reports:
        for k, v in r.get("scores", {}).items():
            sums[k] += v
            cnts[k] += 1
    for k in SCORE_KEYS:
        if cnts[k]:
            print(f"  {k:24} {sums[k]/cnts[k]:.2f}  (n={cnts[k]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
