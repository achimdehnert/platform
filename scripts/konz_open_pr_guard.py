#!/usr/bin/env python3
"""KONZ open-PR collision guard — faengt IN-FLIGHT-Nummernkollisionen.

`konz_number_check.py --check` sieht nur den Baum, wie er nach dem Merge dieses
PRs aussaehe. Zwei GLEICHZEITIG OFFENE PRs, die je ein neues KONZ mit derselben
Nummer anlegen, bestehen den Check deshalb einzeln — und kollidieren erst, wenn
der zweite mergen will.

Realfall 2026-08-12: KONZ-platform-043 wurde von zwei parallelen Sessions
vergeben (`konz043-activity-intelligence` und `konz-formatsatz`, PR #1942).
Beide hatten korrekt `max+1` gegen `main` gerechnet — zum jeweiligen
Vergabezeitpunkt war das fuer beide die 043.

Fuer ADRs schliesst `scripts/adr_open_pr_guard.py` genau diese Luecke seit der
ADR-221..227-Umnummerierung (2026-05). Dieses Skript uebertraegt das Muster auf
KONZ; die beiden sind bewusst getrennt gehalten, solange der ADR-Guard nicht in
demselben PR nachweisbar mitlaufen kann (paths-Filter). Konsolidierung ist als
Folgearbeit an platform#1944 vermerkt.

Ein PR, der ein bestehendes KONZ nur bearbeitet (gleicher Dateiname), wird nicht
gemeldet — das ist paralleles Editieren, keine Doppelvergabe.

Usage (CI, PR-Kontext):
    GH_TOKEN=... PR_NUMBER=<n> GITHUB_REPOSITORY=owner/repo \\
        python3 scripts/konz_open_pr_guard.py
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from collections import defaultdict

KONZ_RE = re.compile(r"(?:^|/)(KONZ-platform-(\d{3})-[^/]+\.md)$", re.IGNORECASE)


def gh(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["gh", *args], capture_output=True, text=True)


def claims_from_files(paths: list[str]) -> dict[int, str]:
    """Dateipfade -> {nummer: dateiname} fuer alle KONZ-Dokumente darin."""
    claims: dict[int, str] = {}
    for path in paths:
        m = KONZ_RE.search(path)
        if m:
            claims[int(m.group(2))] = m.group(1)
    return claims


def main() -> int:
    repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    pr_number = os.environ.get("PR_NUMBER", "").strip()
    if not repo or not pr_number:
        print("ℹ️  no PR context (GITHUB_REPOSITORY/PR_NUMBER) — open-PR guard skipped")
        return 0

    listed = gh(
        "pr",
        "list",
        "--repo",
        repo,
        "--state",
        "open",
        "--json",
        "number",
        "--limit",
        "200",
    )
    if listed.returncode != 0:
        print(
            f"ℹ️  gh unavailable — open-PR guard skipped ({listed.stderr.strip()[:100]})"
        )
        return 0

    open_prs = [p["number"] for p in json.loads(listed.stdout or "[]")]
    # nummer -> { dateiname -> set(pr) }
    claims: dict[int, dict[str, set[int]]] = defaultdict(lambda: defaultdict(set))
    for n in open_prs:
        fr = gh("pr", "view", str(n), "--repo", repo, "--json", "files")
        if fr.returncode != 0:
            continue
        paths = [
            f.get("path", "") for f in json.loads(fr.stdout or "{}").get("files", [])
        ]
        for num, fname in claims_from_files(paths).items():
            claims[num][fname].add(n)

    fail = 0
    for num in sorted(claims):
        files = claims[num]
        if len(files) < 2:  # gleiche Nummer, aber nur eine Datei = paralleles Editieren
            continue
        involved = sorted({pr for prs in files.values() for pr in prs})
        if int(pr_number) not in involved:
            continue
        fail = 1
        detail = "; ".join(
            f"{fn} (PR {sorted(prs)})" for fn, prs in sorted(files.items())
        )
        print(
            f"::error::KONZ-platform-{num:03d} is claimed by multiple open PRs with "
            f"different files — in-flight collision: {detail}. "
            f"Renumber one to the next free number "
            f"(python3 scripts/konz_number_check.py zeigt sie an)."
        )

    if not fail:
        print(
            f"✅ no in-flight KONZ-number collisions across {len(open_prs)} open "
            f"PRs involving PR #{pr_number}"
        )
    return fail


if __name__ == "__main__":
    sys.exit(main())
