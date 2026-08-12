#!/usr/bin/env python3
"""Ruleset-Waechter — bestaetigt, dass die Vier-Augen-Pflicht noch scharf ist.

Das eigentliche Enforcement gegen das Retro-Muster `autonomous-no-human-review`
lebt NICHT in diesem Repo, sondern in der GitHub-Plattform: das Ruleset
`main-required-checks` verlangt Code-Owner-Review, und `.github/CODEOWNERS`
verengt diese Pflicht auf den Entscheidungs-Perimeter (KONZ-032 B1/B1-2,
Owner-Go 2026-08-10). Genau deshalb fand der Gate-Audit in platform#1650 fuer
den Slug nur Kommentare: die Wirkung ist real, aber ausserhalb des Repos —
und eine stille Lockerung (Ruleset deaktiviert, Pfad aus CODEOWNERS entfernt)
wuerde niemand bemerken. Dieselbe Klasse wie ein unregistriertes Gate.

Dieser Waechter prueft beides gegen ein EINGEFRORENES Soll:

1. Es existiert ein aktives Branch-Ruleset mit einer pull_request-Regel und
   `require_code_owner_review: true`.
2. `.github/CODEOWNERS` fuehrt jeden Soll-Perimeter-Pfad.

Bewusst gegen ein gepinntes Soll statt gegen den Ist-Zustand: ein Waechter,
der das Ist als Soll nimmt, segnet jede Verengung automatisch ab. Aenderungen
am Perimeter sind legitim — sie laufen dann als PR an dieser Datei vorbei,
und die liegt zusammen mit CODEOWNERS hinter genau der Review-Pflicht, die
hier bewacht wird (.github/ ist Perimeter; tools/ nicht — der Trade-off ist
im Registry-note dokumentiert).

Exit: 0 = Perimeter intakt · 1 = Verletzung · 2 = nicht bewertbar (kein gh /
keine Auth / API-Fehler — NIE als gruen werten, ein Fetch-Fehler ist kein
gruener Zustand). Der CI-Aufrufer (.github/workflows/ruleset-waechter.yml)
behandelt beide Nicht-Null-Exits als rot (fail-closed).
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

# Maschinenlesbarer Kopf (KONZ-038 D8) — von tools/gate_drill_check.py gegen
# docs/governance/gate-registry.json abgeglichen.
GATE_HEADER = {
    "slug": "autonomous-no-human-review",
    "mode": "process",
    "owner": "achim",
    "last_drill_pass": "2026-08-12",
    "evidence": "tools/tests/test_ruleset_perimeter_check.py",
}

REPO_ROOT = Path(__file__).resolve().parent.parent

# Soll-Perimeter, eingefroren am 2026-08-12 (Ist-Stand aus KONZ-032 B1/B1-2).
# Nur Verzeichnis-Pfade — die Datei-Eintraege (.sops.yaml etc.) sind Zusatz,
# ihr Fehlen waere ein eigener Befund, aber nicht der Kern der Vier-Augen-Pflicht.
PERIMETER_PATHS = (
    "/.github/",
    "/registry/",
    "/packages/",
    "/docs/adr/",
    "/policies/",
    "/governance/",
    "/deployment/",
    "/infra/",
    "/scripts/",
    "/.windsurf/",
)


def repo_slug() -> str | None:
    """owner/repo aus CI-Env oder git-Remote — nie hardcoden (Org-Migrationen)."""
    env = os.environ.get("GITHUB_REPOSITORY", "").strip()
    if env:
        return env
    try:
        out = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    url = out.stdout.strip().removesuffix(".git")
    parts = url.replace(":", "/").rstrip("/").split("/")
    if len(parts) < 2:
        return None
    return f"{parts[-2]}/{parts[-1]}"


def gh_api(pfad: str) -> object | None:
    """GET ueber gh api; None = nicht bewertbar (kein gh, keine Auth, API-Fehler)."""
    try:
        out = subprocess.run(
            ["gh", "api", pfad],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    try:
        return json.loads(out.stdout)
    except json.JSONDecodeError:
        return None


def codeowners_befunde(text: str) -> list[str]:
    """Fehlende Soll-Perimeter-Pfade in einem CODEOWNERS-Text."""
    eintraege = set()
    for zeile in text.splitlines():
        zeile = zeile.strip()
        if not zeile or zeile.startswith("#"):
            continue
        eintraege.add(zeile.split()[0])
    return [p for p in PERIMETER_PATHS if p not in eintraege]


def ruleset_befunde(slug: str) -> tuple[list[str], bool]:
    """(Befunde, bewertbar). Sucht ein aktives Branch-Ruleset mit
    require_code_owner_review=true — namensunabhaengig, damit ein Rename das
    Urteil nicht verfaelscht."""
    listing = gh_api(f"repos/{slug}/rulesets")
    if not isinstance(listing, list):
        return ([], False)
    kandidaten = [
        r
        for r in listing
        if r.get("enforcement") == "active" and r.get("target") == "branch"
    ]
    for r in kandidaten:
        detail = gh_api(f"repos/{slug}/rulesets/{r['id']}")
        if not isinstance(detail, dict):
            return ([], False)
        for rule in detail.get("rules", []):
            if rule.get("type") != "pull_request":
                continue
            if rule.get("parameters", {}).get("require_code_owner_review") is True:
                return ([], True)
    return (
        [
            "kein aktives Branch-Ruleset mit require_code_owner_review=true — "
            "die Vier-Augen-Pflicht auf dem Perimeter ist NICHT mehr erzwungen"
        ],
        True,
    )


def main() -> int:
    befunde: list[str] = []

    co_pfad = REPO_ROOT / ".github" / "CODEOWNERS"
    try:
        co_text = co_pfad.read_text(encoding="utf-8")
    except OSError:
        # Fehlende CODEOWNERS ist keine Messluecke, sondern die Verletzung selbst:
        # ohne Datei gibt es keinen Perimeter mehr.
        befunde.append(f"CODEOWNERS fehlt/unlesbar: {co_pfad}")
        co_text = ""
    if co_text:
        befunde.extend(
            f"Perimeter-Pfad fehlt in CODEOWNERS: {p}"
            for p in codeowners_befunde(co_text)
        )

    slug = repo_slug()
    if slug is None:
        print("⚠ Repo-Slug nicht bestimmbar — NICHT bewertbar (nie als ok werten).")
        return 2
    rs_befunde, bewertbar = ruleset_befunde(slug)
    if not bewertbar:
        print(
            "⚠ Ruleset-Zustand nicht abfragbar (gh fehlt / keine Auth / API-Fehler)"
            " — NICHT bewertbar (ein Fetch-Fehler ist kein gruener Zustand)."
        )
        return 2
    befunde.extend(rs_befunde)

    if befunde:
        print("⛔ Ruleset-Waechter (autonomous-no-human-review):")
        for b in befunde:
            print(f"   - {b}")
        print(
            "   → Soll-Perimeter: KONZ-032 B1/B1-2. Eine gewollte Aenderung gehoert"
            " als PR an tools/ruleset_perimeter_check.py (Soll nachziehen), nicht"
            " als stille Lockerung."
        )
        return 1

    print(
        f"✅ Ruleset-Waechter: Vier-Augen-Pflicht scharf ({slug}: aktives Ruleset"
        f" mit Code-Owner-Review, {len(PERIMETER_PATHS)} Perimeter-Pfade in CODEOWNERS)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
