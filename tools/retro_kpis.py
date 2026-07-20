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
    python3 tools/retro_kpis.py --file-issues   # GATE-PFLICHT-Slugs (>=2) als GH-Issue anlegen/aktualisieren

--file-issues (Retro d80d23/2026-07-16 — "Verankerung entscheidet der Mensch" landete
bisher nur als Prosa im Report; niemand kam zuverlässig zurück, um sie in ein
durables Artefakt zu überführen — `handover-stale-vor-merge` blieb laut
`d2522c-incr` "ohne systemisches Gate", obwohl schon ×4 GATE-PFLICHT):
für jeden Slug mit Zähler ≥2 wird per `gh issue list --search` geprüft, ob bereits
ein Issue mit Titel "Gate: <slug>" existiert (offen ODER geschlossen — ein
geschlossenes Gate-Issue heißt "schon gebaut", nicht "bitte neu anlegen"). Fehlt
es, wird es per `gh issue create` angelegt (Body = Vorkommen-Liste + Retro-Links).
Fail-open wie der Rest des Tools: kein `gh`/kein Repo-Zugriff → Hinweis, Exit 0.

Exit-Code 0 immer (Report-Tool, kein Gate-Enforcer — das Gate ist der gemeldete
GATE-PFLICHT-Block, den der Mensch — oder mit --file-issues das Tool selbst als
durables Issue — in einen PR überführt).
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import subprocess
from collections import Counter, defaultdict

LIST_KEYS = {"recurring_findings", "gate_candidates", "repo_scope"}
SCALAR_KEYS = {
    "date",
    "session_id",
    "footprint",
    "refuted_rate",
    "findings_total",
    "findings_survived",
    "phase3_refuted",
    "pre_refuted",
}
SCORE_KEYS = [
    "zielerreichung",
    "architektur_design",
    "code_konventionstreue",
    "risiko_debt",
    "prozess_effizienz",
    "entscheidungsqualitaet",
]


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


def _gate_issue_title(slug: str) -> str:
    return f"Gate: {slug}"


def _existing_gate_issue(repo: str, slug: str) -> dict | None:
    """Search repo for an existing (open OR closed) 'Gate: <slug>' issue. None if gh/repo unavailable."""
    title = _gate_issue_title(slug)
    try:
        out = subprocess.run(
            [
                "gh",
                "issue",
                "list",
                "--repo",
                repo,
                "--state",
                "all",
                "--search",
                f'"{title}" in:title',
                "--json",
                "number,title,state,url",
                "--limit",
                "10",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    try:
        candidates = json.loads(out.stdout or "[]")
    except json.JSONDecodeError:
        return None
    for c in candidates:
        if c.get("title") == title:
            return c
    return None


def _create_gate_issue(
    repo: str, slug: str, sessions: list[str], reports_by_path: dict
) -> str | None:
    """Create a 'Gate: <slug>' issue. Returns the new issue URL, or None on failure."""
    title = _gate_issue_title(slug)
    lines = [
        f"`{slug}` ist über `tools/retro_kpis.py` mit Zähler **×{len(sessions)}** als "
        "GATE-PFLICHT eskaliert (Schwelle: ≥2 Vorkommen über Session-Retros).",
        "",
        "Bisheriges Muster: dieselbe Erkenntnis wird Retro für Retro neu entdeckt, "
        "bleibt aber Prosa im Report statt in ein durables Gate (Hook/CI/Skill-Edit) "
        "überführt zu werden. Dieses Issue ist genau dafür — es bleibt offen, bis ein "
        "echtes Gate existiert, nicht bis der nächste Report es erwähnt.",
        "",
        "**Vorkommen:**",
    ]
    for sid in sessions:
        path = reports_by_path.get(sid)
        if path:
            lines.append(
                f"- `{sid}` — [{path}](https://github.com/{repo}/blob/main/docs/retros/{path})"
            )
        else:
            lines.append(f"- `{sid}`")
    lines += ["", "_Automatisch angelegt von `tools/retro_kpis.py --file-issues`._"]
    body = "\n".join(lines)
    try:
        out = subprocess.run(
            ["gh", "issue", "create", "--repo", repo, "--title", title, "--body", body],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    return out.stdout.strip().splitlines()[-1] if out.stdout.strip() else None


def file_gate_issues(gated: dict, reports: list[dict], repo: str) -> None:
    """For each GATE-PFLICHT slug, ensure a durable tracking issue exists (create if missing)."""
    reports_by_session = {r.get("session_id", r["_path"]): r["_path"] for r in reports}
    print(f"\n## --file-issues (Repo: {repo})")
    try:
        who = subprocess.run(
            ["gh", "auth", "status"], capture_output=True, text=True, timeout=10
        )
    except (OSError, subprocess.TimeoutExpired):
        who = None
    if who is None or who.returncode != 0:
        print("  (gh nicht verfügbar/nicht eingeloggt — übersprungen, fail-open)")
        return
    for slug, sessions in sorted(gated.items()):
        existing = _existing_gate_issue(repo, slug)
        if existing is not None:
            print(
                f"  · {slug}: bereits vorhanden — {existing['state']} {existing['url']}"
            )
            continue
        url = _create_gate_issue(repo, slug, sessions, reports_by_session)
        if url:
            print(f"  ✓ {slug}: neu angelegt — {url}")
        else:
            print(
                f"  ✗ {slug}: Issue-Erstellung fehlgeschlagen (fail-open, kein Retry)"
            )


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Längsschnitt-KPIs über session-retro-Reports"
    )
    # KONZ-platform-010: durable Heimat = git docs/retros/ (nicht ~/shared, ungebackupt).
    # Default liest BEIDE — docs/retros/ (git-durable, KONZ-010) UND ~/shared/ (der Pfad,
    # nach dem die /session-retro-Skill schreibt) — dedupliziert nach Dateiname, damit ein
    # frisch nach ~/shared geschriebener Report nicht durch die Pfad-Drift unsichtbar bleibt.
    _repo_retros = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "retros"
    )
    _shared = os.path.expanduser("~/shared")
    ap.add_argument(
        "--dir",
        action="append",
        default=None,
        help="Verzeichnis(se) mit session-retro-*.md; mehrfach angebbar. "
        "Default: <repo>/docs/retros (KONZ-010) + ~/shared (Skill-Schreibpfad).",
    )
    ap.add_argument(
        "--min-band",
        type=int,
        default=3,
        help="refuted_rate-Band erst ab N Retros bewerten (default 3)",
    )
    ap.add_argument(
        "--file-issues",
        action="store_true",
        help="GATE-PFLICHT-Slugs (Zaehler >=2) als 'Gate: <slug>'-Issue in "
        "--issues-repo anlegen, falls noch keins existiert (offen oder "
        "geschlossen). Fail-open ohne gh/Login.",
    )
    ap.add_argument(
        "--issues-repo",
        default="achimdehnert/platform",
        help="Ziel-Repo fuer --file-issues (default: achimdehnert/platform)",
    )
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
        print(
            f"\n→ {len(gated)} Slug(s) ≥2 ⇒ Gate-PR-Pflicht: "
            f"{', '.join(sorted(gated))}. Als Gate (Hook/CI/Skill) verankern, "
            f"nicht als N-tes Memo."
        )

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
            recent = [v for _, v in rates[-args.min_band :]]
            if all(v > 0.8 for v in recent):
                print(
                    f"  ⚠️  letzte {args.min_band} >0.8 → Finder zu lasch (widerlegbares Stroh)."
                )
            elif all(v < 0.2 for v in recent):
                print(
                    f"  ⚠️  letzte {args.min_band} <0.2 → Falsifikation ist Theater (widerlegt nie)."
                )
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
            print(f"  {k:24} {sums[k] / cnts[k]:.2f}  (n={cnts[k]})")

    if args.file_issues:
        file_gate_issues(gated, reports, args.issues_repo)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
