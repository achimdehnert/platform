#!/usr/bin/env python3
"""pr-merge-sa — merged einen PR NUR, wenn er belegbar unter eine ratifizierte
Standing-Authorization-Klasse faellt (policies/autonomy-gates.md).

GATE_HEADER (KONZ-038 D8):
  "slug": "merge-without-class-proof"
  "mode": "tool"
  "owner": "achim"
  "last_drill_pass": "2026-08-26"
  "evidence": "tools/tests/test_pr_merge_sa.py"

Warum dieses Werkzeug statt `Bash(gh pr merge:*)` in `autoMode.allow`:
Das Praefix-Muster erlaubt das KOMMANDO, nicht die KLASSE. Es kann nicht
unterscheiden, ob `main` in diesem Repo einen Prod-Deploy ausloest — genau die
Unterscheidung, an der Gate 2 haengt. Gemessen 2026-08-26: 26 von 69 lokal
geklonten Repos mit Workflows deployen auf `main`. Der Radius gehoert deshalb
ins Werkzeug, nicht in die Selbstdisziplin des Agenten: was dieses Skript nicht
kann, kann der Agent nicht.

Grundregel (uebernommen von pr-gruen-ziehen.sh): Ein API-Fehler, eine leere
Antwort oder ein unlesbarer Workflow ist ABWESENHEIT VON BEWEIS — nie Beweis.
Jeder unklare Zustand fuehrt zu Exit != 0 und KEINEM Merge.

Aufruf:
  pr_merge_sa.py <pr-nr> [owner/repo] [--dry-run] [--json]

Exit-Codes:
  0  gedeckt (bei --dry-run: waere gedeckt) — Merge ausgefuehrt
  2  NICHT gedeckt (Klasse verneint, mit Grund)
  3  unklar — Daten fehlen oder API-Fehler (fail-closed, nie Merge)
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field, asdict

# --- Klassifikations-Konstanten ------------------------------------------------

# Reine Doku (SA-5). Bewusst eng: was hier nicht steht, ist kein Doku-PR.
DOKU_PATTERNS = (
    re.compile(r"\.md$"),
    re.compile(r"\.rst$"),
    re.compile(r"^docs/"),
    re.compile(r"(^|/)README[^/]*$"),
    re.compile(r"(^|/)CHANGELOG[^/]*$"),
)

# Governance — dort ist `.md` Inhalt der Steuerung, nicht Doku. Nie autonom.
GOVERNANCE_PREFIXES = (
    ".github/",
    "docs/adr/",
    "policies/",
    "registry/",
    "packages/",
)
GOVERNANCE_NAMES = ("CODEOWNERS",)

# Ein Workflow gilt als Deploy, wenn er auf push nach main triggert UND einer
# dieser Marker vorkommt. Bewusst breit: lieber ein Repo zu viel als Gate 2 zu
# wenig — die Fehlerrichtung ist "Merge abgelehnt", nicht "Prod deployed".
DEPLOY_MARKERS = re.compile(
    r"\b(deploy|ship|release|publish|docker\s+push|ghcr\.io|ssh)\b", re.IGNORECASE
)


class Unklar(Exception):
    """Fail-closed: Datenlage erlaubt kein Urteil."""


@dataclass
class Facts:
    """Alles, was zur Klassifikation noetig ist — bewusst reine Daten, damit
    classify() ohne Netz testbar ist."""

    repo: str
    number: int
    state: str
    is_draft: bool
    mergeable: str
    merge_state: str
    review_decision: str
    review_required: bool
    auto_deploy: bool
    files: list = field(default_factory=list)
    checks_total: int = 0
    checks_failing: int = 0
    checks_pending: int = 0


@dataclass
class Verdict:
    klasse: str  # "SA-1" | "SA-5" | "-"
    erlaubt: bool
    grund: str


# --- Klassifikation (rein, ohne Netz) -----------------------------------------


def ist_doku(pfad: str) -> bool:
    return any(p.search(pfad) for p in DOKU_PATTERNS)


def ist_governance(pfad: str) -> bool:
    if any(pfad.startswith(p) for p in GOVERNANCE_PREFIXES):
        return True
    return pfad.rsplit("/", 1)[-1] in GOVERNANCE_NAMES


def classify(f: Facts) -> Verdict:
    """Entscheidet die Klasse. Jede Ablehnung nennt ihren Grund — ein Verdict
    ohne Grund waere so nutzlos wie ein Skip ohne Grund."""
    if f.state != "OPEN":
        return Verdict("-", False, f"PR ist {f.state}, nicht OPEN")
    if f.is_draft:
        return Verdict("-", False, "PR ist ein Draft")
    if not f.files:
        raise Unklar("keine Dateiliste erhalten — ohne Diff keine Klasse")

    governance = [p for p in f.files if ist_governance(p)]
    if governance:
        return Verdict("-", False, f"Governance-Pfad beruehrt: {governance[0]}")

    if f.auto_deploy:
        # Gate 2: in diesen Repos IST der Merge der Prod-Schritt. SA-5 wuerde
        # reine Doku auch hier decken, sobald platform#2334 ratifiziert ist —
        # bis dahin ist der konservative Schnitt der richtige (Issue #2338, K4).
        return Verdict(
            "-", False, "Repo deployt auf main — Gate 2, Merge ist Prod-Schritt"
        )

    if f.review_required:
        return Verdict("-", False, "Ruleset/CODEOWNERS verlangt Review")

    if f.mergeable != "MERGEABLE":
        raise Unklar(f"mergeable={f.mergeable} — GitHub hat den Merge nicht bestaetigt")
    if f.merge_state in ("DIRTY", "BLOCKED", "BEHIND"):
        return Verdict("-", False, f"mergeStateStatus={f.merge_state}")

    if f.checks_failing:
        return Verdict("-", False, f"{f.checks_failing} Check(s) rot")
    if f.checks_pending:
        raise Unklar(
            f"{f.checks_pending} Check(s) laufen noch — Abwesenheit von Beweis"
        )

    nicht_doku = [p for p in f.files if not ist_doku(p)]
    if not nicht_doku:
        return Verdict("SA-5", True, f"reiner Doku-PR ({len(f.files)} Datei(en))")

    if f.checks_total == 0:
        return Verdict(
            "-",
            False,
            "Code-PR ohne einen einzigen Check — SA-1 verlangt gruenes CI",
        )
    return Verdict(
        "SA-1",
        True,
        f"CI gruen ({f.checks_total} Checks), kein Review-Gate, kein Auto-Deploy",
    )


# --- Datenbeschaffung ----------------------------------------------------------


def _gh(args: list, roh: bool = False):
    p = subprocess.run(["gh", *args], capture_output=True, text=True)
    if p.returncode != 0:
        raise Unklar(f"gh {' '.join(args[:3])} …: {p.stderr.strip()[:200]}")
    if roh:
        return p.stdout
    try:
        return json.loads(p.stdout)
    except json.JSONDecodeError as exc:
        raise Unklar(f"gh-Antwort nicht lesbar: {exc}")


def repo_deployt_auf_main(repo: str) -> bool:
    """Trigger lesen, nicht Dateinamen raten. Unlesbar => Unklar (fail-closed)."""
    try:
        eintraege = _gh(["api", f"repos/{repo}/contents/.github/workflows"])
    except Unklar as exc:
        if "404" in str(exc) or "Not Found" in str(exc):
            return False  # keine Workflows => kein Auto-Deploy
        raise
    if not isinstance(eintraege, list):
        raise Unklar("Workflow-Verzeichnis nicht als Liste erhalten")

    for e in eintraege:
        name = e.get("name", "")
        if not name.endswith((".yml", ".yaml")):
            continue
        datei = _gh(["api", e["url"]])
        inhalt = datei.get("content")
        if not inhalt:
            raise Unklar(f"Workflow {name} ohne Inhalt")
        text = base64.b64decode(inhalt).decode("utf-8", errors="replace")
        kopf = text.split("jobs:", 1)[0]
        push_auf_main = "push:" in kopf and re.search(r"\bmain\b", kopf)
        if push_auf_main and DEPLOY_MARKERS.search(text):
            return True
    return False


def review_ist_pflicht(repo: str, branch: str) -> bool:
    try:
        rules = _gh(["api", f"repos/{repo}/rules/branches/{branch}"])
    except Unklar as exc:
        if "404" in str(exc) or "Not Found" in str(exc):
            return False
        raise
    if not isinstance(rules, list):
        raise Unklar("Ruleset-Antwort nicht als Liste erhalten")
    return any(r.get("type") == "pull_request" for r in rules)


def gather(repo: str, nummer: int) -> Facts:
    felder = "state,isDraft,mergeable,mergeStateStatus,reviewDecision,files,baseRefName,statusCheckRollup"
    pr = _gh(["pr", "view", str(nummer), "-R", repo, "--json", felder])

    if pr.get("mergeable") == "UNKNOWN":
        # mergeable wird lazy berechnet — einmal neu fragen, dann fail-closed.
        pr = _gh(["pr", "view", str(nummer), "-R", repo, "--json", felder])

    roll = pr.get("statusCheckRollup") or []
    failing = pending = 0
    for c in roll:
        zustand = (c.get("conclusion") or c.get("state") or "").upper()
        if zustand in ("FAILURE", "TIMED_OUT", "CANCELLED", "ACTION_REQUIRED", "ERROR"):
            failing += 1
        elif zustand in ("", "PENDING", "IN_PROGRESS", "QUEUED", "EXPECTED"):
            pending += 1

    return Facts(
        repo=repo,
        number=nummer,
        state=pr.get("state", ""),
        is_draft=bool(pr.get("isDraft")),
        mergeable=pr.get("mergeable", "UNKNOWN"),
        merge_state=pr.get("mergeStateStatus", ""),
        review_decision=pr.get("reviewDecision") or "",
        review_required=review_ist_pflicht(repo, pr.get("baseRefName", "main")),
        auto_deploy=repo_deployt_auf_main(repo),
        files=[f["path"] for f in pr.get("files", [])],
        checks_total=len(roll),
        checks_failing=failing,
        checks_pending=pending,
    )


def repo_aus_cwd() -> str:
    p = subprocess.run(
        ["git", "remote", "get-url", "origin"], capture_output=True, text=True
    )
    if p.returncode != 0:
        raise Unklar("kein Repo bestimmbar — als zweites Argument angeben")
    url = p.stdout.strip()
    return re.sub(r"^(git@[^:]+:|https://[^/]+/)", "", url).removesuffix(".git")


# --- CLI -----------------------------------------------------------------------


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("nummer", type=int)
    ap.add_argument("repo", nargs="?", default=None, help="owner/repo (sonst aus cwd)")
    ap.add_argument("--dry-run", action="store_true", help="nur klassifizieren")
    ap.add_argument("--json", action="store_true", dest="als_json")
    args = ap.parse_args(argv)

    try:
        repo = args.repo or repo_aus_cwd()
        fakten = gather(repo, args.nummer)
        urteil = classify(fakten)
    except Unklar as exc:
        print(f"UNKLAR: {exc}", file=sys.stderr)
        print("→ kein Merge (fail-closed).", file=sys.stderr)
        return 3

    if args.als_json:
        print(
            json.dumps({"facts": asdict(fakten), "verdict": asdict(urteil)}, indent=2)
        )
    else:
        marke = "✓" if urteil.erlaubt else "✗"
        print(f"{marke} {repo}#{args.nummer}: {urteil.klasse} — {urteil.grund}")

    if not urteil.erlaubt:
        return 2
    if args.dry_run:
        print("(dry-run — nicht gemergt)")
        return 0

    p = subprocess.run(
        [
            "gh",
            "pr",
            "merge",
            str(args.nummer),
            "-R",
            repo,
            "--squash",
            "--delete-branch",
        ],
        capture_output=True,
        text=True,
    )
    if p.returncode != 0:
        print(f"Merge fehlgeschlagen: {p.stderr.strip()[:300]}", file=sys.stderr)
        return 3
    print(f"gemergt: {repo}#{args.nummer} ({urteil.klasse})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
