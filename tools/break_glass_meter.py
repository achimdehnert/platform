#!/usr/bin/env python3
"""KONZ-platform-004 Kill-Gate: break-glass-meter — zählt umgangene Rulesets.

Das Kill-Gate von KONZ-004 lautet: "Nach 2 Wochen Pilot (Prod-Subset) mehr
legitime grün-werdende Merges blockiert als rote Merges verhindert, ODER
>=1 Break-Glass/Woche nötig -> zurück auf Konvention + nur Audit-Meter".

Für die Break-Glass-Hälfte dieses Kriteriums gab es bis 2026-07-20 kein
Messinstrument: `branch_protection_meter.py` prüft, ob das Ruleset *existiert
und aktiv ist* (Break-Glass in der Form "Schutz abgeschaltet"), aber nicht,
wie oft ein bestehendes Ruleset für einen einzelnen Merge *umgangen* wurde.
Genau diese zweite Form ist der Regelfall (Admin-Merge via `--admin` bzw.
bypass_actor) und blieb ungezählt — das Gate konnte also gar nicht feuern.

Instrument: GET /repos/{owner}/{repo}/rulesets/rule-suites liefert je
Push/Merge eine Rule-Suite mit `result` in {pass, fail, bypass} und
`actor_name`. `bypass` = Break-Glass.

Exit-Codes: 0 = unter Schwelle · 1 = Schwelle gerissen (das ist ein FUND,
            kein Tool-Fehler) · 2 = Konfigurations-/Aufruffehler

Usage:
    TOKEN=<pat> python3 tools/break_glass_meter.py \
        --expected governance/rulesets/wave1-repos.json \
                   governance/rulesets/wave2-repos.json \
        --weeks 2 --threshold-per-week 1 \
        --report /tmp/break-glass-report.md
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.github.com"


def _api_get(path: str, token: str):
    req = urllib.request.Request(
        f"{API}{path}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def fetch_bypasses(owner: str, repo: str, token: str, per_page: int = 100) -> list:
    """Liefert die Rule-Suites mit result=bypass für ein Repo.

    Gotcha: `rule_suite_result=bypass` filtert server-seitig; ohne den Filter
    kämen bis zu `per_page` Suites zurück, von denen die meisten `pass` sind —
    und der Zähler wäre still unvollständig, sobald ein Repo viel Traffic hat.
    """
    query = urllib.parse.urlencode(
        {"per_page": per_page, "rule_suite_result": "bypass"}
    )
    return _api_get(f"/repos/{owner}/{repo}/rulesets/rule-suites?{query}", token)


def iso_week(timestamp: str) -> str:
    """'2026-07-20T06:57:10Z' -> '2026-W30'. Leerer/kaputter Wert -> 'unknown'."""
    if not timestamp:
        return "unknown"
    try:
        parsed = dt.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return "unknown"
    year, week, _ = parsed.isocalendar()
    return f"{year}-W{week:02d}"


def within_window(timestamp: str, cutoff: dt.datetime) -> bool:
    """True, wenn der Zeitstempel im Betrachtungsfenster liegt.

    Unparsbare Zeitstempel werden EINGESCHLOSSEN, nicht verworfen: ein
    Break-Glass, dessen Datum wir nicht lesen können, darf nicht still aus
    der Zählung fallen (er wäre sonst genau der Fall, den das Gate sucht).
    """
    if not timestamp:
        return True
    try:
        parsed = dt.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return True
    return parsed >= cutoff


def evaluate(suites: list, weeks: int, threshold_per_week: float, now: dt.datetime) -> dict:
    """Bewertet die Bypass-Suites eines Repos gegen die Schwelle (pure, testbar)."""
    cutoff = now - dt.timedelta(weeks=weeks)
    recent = [s for s in suites if within_window(s.get("pushed_at", ""), cutoff)]
    per_week = collections.Counter(iso_week(s.get("pushed_at", "")) for s in recent)
    per_actor = collections.Counter(s.get("actor_name") or "unknown" for s in recent)
    rate = len(recent) / weeks if weeks else 0.0
    return {
        "count": len(recent),
        "rate_per_week": round(rate, 2),
        "breached": rate >= threshold_per_week,
        "per_week": dict(per_week),
        "per_actor": dict(per_actor),
    }


def render_report(results: list, weeks: int, threshold_per_week: float) -> str:
    breached = [r for r in results if r.get("breached")]
    clean = [r for r in results if not r.get("breached") and not r.get("error")]
    errored = [r for r in results if r.get("error")]
    total = sum(r.get("count", 0) for r in results)

    lines = ["# break-glass-meter (KONZ-platform-004 Kill-Gate)", ""]
    lines.append(
        f"Fenster: **{weeks} Wochen** · Schwelle: **{threshold_per_week}/Woche** · "
        f"Break-Glass gesamt: **{total}**"
    )
    lines.append("")
    lines.append(
        f"**{len(breached)} über Schwelle · {len(clean)} unauffällig · {len(errored)} nicht lesbar**"
    )

    if breached:
        lines += ["", "## Schwelle gerissen — Kill-Gate-Signal", ""]
        lines.append("| Repo | Break-Glass | pro Woche | Actor(en) |")
        lines.append("|---|---|---|---|")
        for r in breached:
            actors = ", ".join(f"{a} ({n})" for a, n in sorted(r["per_actor"].items()))
            lines.append(
                f"| {r['repo']} | {r['count']} | {r['rate_per_week']} | {actors} |"
            )
    if errored:
        lines += ["", "## Nicht lesbar (kein Freispruch)", ""]
        for r in errored:
            lines.append(f"- {r['repo']}: {r['error']}")
    if clean:
        lines += ["", "## Unauffällig", ""]
        for r in clean:
            lines.append(f"- {r['repo']}: {r['count']} Break-Glass")
    return "\n".join(lines) + "\n"


def load_expected(paths: list) -> list:
    merged: list = []
    for path in paths:
        with open(path) as fh:
            merged.extend(json.load(fh))
    return merged


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected", nargs="+", required=True)
    parser.add_argument("--weeks", type=int, default=2)
    parser.add_argument("--threshold-per-week", type=float, default=1.0)
    parser.add_argument("--report")
    args = parser.parse_args()

    token = os.environ.get("TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        print("FEHLER: TOKEN/GITHUB_TOKEN nicht gesetzt", file=sys.stderr)
        return 2

    try:
        expected = load_expected(args.expected)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FEHLER: Soll-Liste nicht lesbar: {exc}", file=sys.stderr)
        return 2

    now = dt.datetime.now(dt.timezone.utc)
    results = []
    for entry in expected:
        owner, repo = entry["owner"], entry["repo"]
        try:
            suites = fetch_bypasses(owner, repo, token)
        except urllib.error.HTTPError as exc:
            results.append(
                {"repo": repo, "error": f"rule-suites-API nicht lesbar (HTTP {exc.code})"}
            )
            continue
        except urllib.error.URLError as exc:
            results.append({"repo": repo, "error": f"rule-suites-API nicht lesbar ({exc})"})
            continue
        verdict = evaluate(suites, args.weeks, args.threshold_per_week, now)
        results.append({"repo": repo, **verdict})

    report = render_report(results, args.weeks, args.threshold_per_week)
    print(report)
    if args.report:
        with open(args.report, "w") as fh:
            fh.write(report)

    breached = sum(1 for r in results if r.get("breached"))
    total = sum(r.get("count", 0) for r in results)
    gh_output = os.environ.get("GITHUB_OUTPUT")
    if gh_output:
        with open(gh_output, "a") as fh:
            fh.write(f"breached={breached}\n")
            fh.write(f"break_glass_total={total}\n")

    return 1 if breached else 0


if __name__ == "__main__":
    sys.exit(main())
