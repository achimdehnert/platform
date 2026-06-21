#!/usr/bin/env python3
"""ADR-242 §Rollout 4: branch-protection-meter — Enforcement der Enforcement.

Prüft für jedes Soll-Repo aus governance/rulesets/*-repos.json, ob das
Branch-Protection-Ruleset 'main-required-checks' real existiert, aktiv ist
und den erwarteten required check trägt. Break-Glass (enforcement=disabled)
ist per ADR-242 ausdrücklich meldepflichtig.

Einträge mit "deferred"-Feld werden nicht als Verletzung gewertet, aber im
Report gelistet (Rollout-Gate: erst grüne main-CI, dann Ruleset).

Exit-Codes: 0 = alle Soll-Repos konform · 1 = mindestens eine Verletzung
            2 = Konfigurations-/Aufruffehler

Usage:
    TOKEN=<pat> python3 tools/branch_protection_meter.py \
        --expected governance/rulesets/wave1-repos.json \
                   governance/rulesets/wave2-repos.json \
        --report /tmp/meter-report.md
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

API = "https://api.github.com"
RULESET_NAME = "main-required-checks"


def evaluate_repo(entry: dict, rulesets: list) -> dict:
    """Bewertet ein Soll-Repo gegen seine live Rulesets (pure, testbar).

    Returns dict mit status: 'ok' | 'deferred' | 'violation' und reasons.
    """
    repo = entry["repo"]
    if entry.get("deferred"):
        return {"repo": repo, "status": "deferred", "reasons": [str(entry["deferred"])]}

    expected_check = entry["required_check"]
    matching = [r for r in rulesets if r.get("name") == RULESET_NAME]
    if not matching:
        return {
            "repo": repo,
            "status": "violation",
            "reasons": [f"Ruleset '{RULESET_NAME}' fehlt"],
        }

    reasons = []
    ruleset = matching[0]
    if ruleset.get("enforcement") != "active":
        reasons.append(
            f"enforcement='{ruleset.get('enforcement')}' (Break-Glass offen? ADR-242 verlangt Re-Aktivierung)"
        )

    contexts = [
        c.get("context")
        for rule in ruleset.get("rules", [])
        if rule.get("type") == "required_status_checks"
        for c in rule.get("parameters", {}).get("required_status_checks", [])
    ]
    if expected_check not in contexts:
        reasons.append(
            f"required check '{expected_check}' nicht konfiguriert (gefunden: {contexts or 'keine'})"
        )

    if reasons:
        return {"repo": repo, "status": "violation", "reasons": reasons}
    return {"repo": repo, "status": "ok", "reasons": []}


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


def fetch_rulesets(owner: str, repo: str, token: str) -> list:
    """Liefert Rulesets MIT rules-Array.

    Gotcha: der List-Endpoint (/rulesets) liefert nur Summaries ohne 'rules';
    die Regel-Details gibt es nur per GET /rulesets/{id} — daher zweistufig.
    """
    summaries = _api_get(f"/repos/{owner}/{repo}/rulesets", token)
    return [
        _api_get(f"/repos/{owner}/{repo}/rulesets/{s['id']}", token)
        for s in summaries
        if s.get("name") == RULESET_NAME
    ]


def render_report(results: list) -> str:
    """Markdown-Report für Issue/Discord."""
    ok = [r for r in results if r["status"] == "ok"]
    deferred = [r for r in results if r["status"] == "deferred"]
    violations = [r for r in results if r["status"] == "violation"]

    lines = ["# branch-protection-meter (ADR-242)", ""]
    lines.append(
        f"**{len(ok)} konform · {len(violations)} Verletzungen · {len(deferred)} deferred**"
    )
    if violations:
        lines += ["", "## ❌ Verletzungen", ""]
        for r in violations:
            for reason in r["reasons"]:
                lines.append(f"- **{r['repo']}**: {reason}")
    if deferred:
        lines += ["", "## ⏸ Deferred (kein Alarm)", ""]
        for r in deferred:
            lines.append(f"- {r['repo']}: {r['reasons'][0]}")
    if ok:
        lines += ["", "## ✅ Konform", ""]
        for r in ok:
            lines.append(f"- {r['repo']}")
    return "\n".join(lines) + "\n"


def load_expected(paths: list) -> list:
    """Lädt und konkateniert eine oder mehrere Soll-Listen (Wave-Dateien).

    Mehrere --expected (z. B. wave1 + wave2) ergeben eine gemeinsame
    Prüfmenge; Verletzungen aggregieren über alle Wellen.
    """
    merged: list = []
    for path in paths:
        with open(path) as fh:
            merged.extend(json.load(fh))
    return merged


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--expected",
        required=True,
        nargs="+",
        help="Pfad(e) zur Soll-Repo-Liste(n) (JSON) — mehrere Wellen erlaubt",
    )
    parser.add_argument("--report", help="Markdown-Report in Datei schreiben")
    args = parser.parse_args()

    token = os.environ.get("TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        print("❌ TOKEN (oder GH_TOKEN) nicht gesetzt", file=sys.stderr)
        return 2

    try:
        expected = load_expected(args.expected)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"❌ Soll-Liste nicht lesbar: {exc}", file=sys.stderr)
        return 2

    results = []
    for entry in expected:
        if entry.get("deferred"):
            results.append(evaluate_repo(entry, []))
            continue
        try:
            rulesets = fetch_rulesets(entry["owner"], entry["repo"], token)
        except urllib.error.HTTPError as exc:
            # Nicht-prüfbar = Verletzung (Schweigen wäre Schein-Grün)
            results.append(
                {
                    "repo": entry["repo"],
                    "status": "violation",
                    "reasons": [f"Rulesets-API nicht lesbar (HTTP {exc.code})"],
                }
            )
            continue
        results.append(evaluate_repo(entry, rulesets))

    report = render_report(results)
    print(report)
    if args.report:
        with open(args.report, "w") as fh:
            fh.write(report)

    violations = sum(1 for r in results if r["status"] == "violation")
    gh_output = os.environ.get("GITHUB_OUTPUT")
    if gh_output:
        with open(gh_output, "a") as fh:
            fh.write(f"violations={violations}\n")

    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
