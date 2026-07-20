#!/usr/bin/env python3
"""sync_drift_meter.py — ADR-265 REC-3 / Option 1: read-only Sync-Drift-Melder.

Schließt die Sichtbarkeitslücke „nie geöffnete Repos behalten veraltete
Workflows unbemerkt" (AD-4, Issue #949) — OHNE Cross-Repo-Write. Läuft
`scripts/sync-workflows.sh --dry-run --strict` gegen die Fleet-Checkouts
unter `${GITHUB_DIR:-$HOME/github}` (auf dem self-hosted Runner vorhanden,
wie `megatest.yml` sie klont) und klassifiziert das Ergebnis:

- **SKIP-REPO**    — Repo hat keinen wirksamen `.windsurf/`-Ignore
                     (Zeile fehlt in `.gitignore`, ADR-265).
- **SKIP-TRACKED**  — Repo hat mind. einen im Index getrackten
                     `.windsurf/workflows/*.md`-Pfad, der einen Symlink
                     verhindert (erst `git rm --cached` nötig).
- **STALE**         — Repo hat mind. einen Symlink, der (laut Dry-Run
                     `FIX-LINK`) nicht mehr auf die aktuelle SSoT zeigt.

**Read-only Pflicht (Issue #949):** dieses Skript ruft `sync-workflows.sh`
AUSSCHLIESSLICH mit `--dry-run --strict` auf, schreibt nichts in fremde
Repos, pusht/committet nichts. Es öffnet selbst gar kein GitHub-Issue —
das übernimmt der aufrufende Workflow (`sync-drift-meter.yml`) im EIGENEN
(platform-)Repo, analog `backup-meter.yml`/`branch-protection-meter.yml`.

Exit-Codes: 0 = kein Drift · 1 = Drift (SKIP und/oder STALE) · 2 = Aufruffehler

Usage:
    python3 tools/sync_drift_meter.py --report /tmp/sync-drift-report.md
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SYNC_SCRIPT = _ROOT / "scripts" / "sync-workflows.sh"

# Schluss-Summary-Zeile von sync-workflows.sh (ADR-265 REC-1, seit #950/#946):
#   "SKIP-SUMMARY: 3 Repo(s) übersprungen (SKIP-REPO: a,b; SKIP-TRACKED: c)"
#   "SKIP-SUMMARY: 0 Repos übersprungen"
_SKIP_SUMMARY_RE = re.compile(
    r"^SKIP-SUMMARY:\s*(\d+)\s+Repo(?:\(s\)|s)\s+übersprungen"
    r"(?:\s*\(SKIP-REPO:\s*([^;]*);\s*SKIP-TRACKED:\s*([^)]*)\))?"
)
# Per-Repo-Blockkopf: "📦 risk-hub (django-hub)" oder "📦 some-repo" (SKIP-REPO-Fall)
_REPO_BLOCK_RE = re.compile(r"^📦\s+(\S+)")


def _split_names(raw: str | None) -> list[str]:
    """'a,b,' / '' / None -> saubere Namensliste (keine Leerstrings)."""
    if not raw:
        return []
    return [name.strip() for name in raw.split(",") if name.strip()]


def parse_sync_output(output: str) -> dict:
    """Parst stdout+stderr von `sync-workflows.sh --dry-run --strict` (pure, testbar).

    Liefert ein dict mit:
        skip_repo:    list[str]  — Repos mit SKIP-REPO (Ignore-Guard)
        skip_tracked: list[str]  — Repos mit SKIP-TRACKED (Tracked-Guard)
        stale:        list[str]  — Repos mit >=1 FIX-LINK (Symlink veraltet)
        total_skips:  int        — Zahl aus der SKIP-SUMMARY-Zeile
        summary_line: str | None — die rohe SKIP-SUMMARY-Zeile (None = nicht
                                    gefunden -> Aufruf ist vermutlich vor der
                                    Summary abgebrochen, siehe main())
    """
    skip_repo: list[str] = []
    skip_tracked: list[str] = []
    stale: list[str] = []
    total_skips = 0
    summary_line: str | None = None

    current_repo: str | None = None
    for raw_line in output.splitlines():
        line = raw_line.strip()

        block_match = _REPO_BLOCK_RE.match(line)
        if block_match:
            current_repo = block_match.group(1)

        if "FIX-LINK" in line and current_repo and current_repo not in stale:
            stale.append(current_repo)

        summary_match = _SKIP_SUMMARY_RE.match(line)
        if summary_match:
            summary_line = line
            total_skips = int(summary_match.group(1))
            skip_repo = _split_names(summary_match.group(2))
            skip_tracked = _split_names(summary_match.group(3))

    return {
        "skip_repo": skip_repo,
        "skip_tracked": skip_tracked,
        "stale": stale,
        "total_skips": total_skips,
        "summary_line": summary_line,
    }


def has_drift(parsed: dict) -> bool:
    """True, wenn irgendeine der drei Kategorien nicht leer ist."""
    return bool(parsed["skip_repo"] or parsed["skip_tracked"] or parsed["stale"])


def render_report(parsed: dict, exit_code: int) -> str:
    """Markdown-Report für Issue/Job-Summary (Stil wie backup-/branch-protection-meter)."""
    skip_repo = parsed["skip_repo"]
    skip_tracked = parsed["skip_tracked"]
    stale = parsed["stale"]

    lines = ["# sync-drift-meter (ADR-265 REC-3)", ""]

    if not has_drift(parsed):
        lines.append(
            "**0 Drift** — Fleet ist synchron laut "
            "`sync-workflows.sh --dry-run --strict`."
        )
        return "\n".join(lines) + "\n"

    lines.append(
        f"**Drift erkannt** — {len(skip_repo)} SKIP-REPO · "
        f"{len(skip_tracked)} SKIP-TRACKED · {len(stale)} STALE."
    )

    if skip_repo:
        lines += ["", "## SKIP-REPO (kein wirksamer `.windsurf/`-Ignore)", ""]
        for name in skip_repo:
            lines.append(
                f"- **{name}**: `.windsurf/` fehlt in `.gitignore` — "
                "Zeile committen, dann sync (ADR-265)"
            )

    if skip_tracked:
        lines += ["", "## SKIP-TRACKED (getrackte Pfade blockieren Symlink)", ""]
        for name in skip_tracked:
            lines.append(
                f"- **{name}**: mind. ein `.windsurf/workflows/*.md` ist im "
                "Index getrackt — erst `git rm --cached`, dann sync (ADR-265)"
            )

    if stale:
        lines += ["", "## STALE (Symlink zeigt auf veraltete SSoT)", ""]
        for name in stale:
            lines.append(
                f"- **{name}**: mind. ein Symlink zeigt laut Dry-Run (`FIX-LINK`) "
                "nicht mehr auf die aktuelle SSoT"
            )

    lines += ["", f"Quelle: `sync-workflows.sh --dry-run --strict` (Exit {exit_code})."]
    return "\n".join(lines) + "\n"


def run_sync_dry_run(
    sync_script: Path, github_dir: Path, repo: str | None = None
) -> subprocess.CompletedProcess:
    """Ruft sync-workflows.sh **ausschließlich** mit --dry-run --strict auf.

    Read-only per Konstruktion: kein anderer Aufruf-Pfad in diesem Modul ruft
    sync-workflows.sh ohne --dry-run. Kein Push/Commit, kein `gh ... --repo
    <fremd>`-Write.
    """
    cmd = ["bash", str(sync_script), "--dry-run", "--strict"]
    if repo:
        cmd.append(repo)
    env = dict(os.environ)
    env["GITHUB_DIR"] = str(github_dir)
    return subprocess.run(
        cmd, capture_output=True, text=True, env=env, check=False
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--github-dir",
        default=os.environ.get("GITHUB_DIR", str(Path.home() / "github")),
        help="Fleet-Checkout-Wurzel (default $GITHUB_DIR oder ~/github)",
    )
    parser.add_argument(
        "--sync-script",
        default=str(DEFAULT_SYNC_SCRIPT),
        help="Pfad zu scripts/sync-workflows.sh",
    )
    parser.add_argument(
        "--repo", help="Nur ein Repo prüfen statt der ganzen Fleet"
    )
    parser.add_argument("--report", help="Markdown-Report in Datei schreiben")
    args = parser.parse_args()

    sync_script = Path(args.sync_script)
    if not sync_script.is_file():
        print(f"❌ sync-workflows.sh nicht gefunden: {sync_script}", file=sys.stderr)
        return 2

    proc = run_sync_dry_run(sync_script, Path(args.github_dir), args.repo)
    output = f"{proc.stdout}\n{proc.stderr}"
    parsed = parse_sync_output(output)

    if parsed["summary_line"] is None:
        # SKIP-SUMMARY fehlt komplett -> Lauf ist vor der Summary abgebrochen
        # (z. B. Registry nicht lesbar) -> Aufruffehler, nicht "kein Drift".
        print("❌ sync-workflows.sh lieferte keine SKIP-SUMMARY-Zeile:", file=sys.stderr)
        print(output, file=sys.stderr)
        return 2

    report = render_report(parsed, proc.returncode)
    print(report)
    if args.report:
        with open(args.report, "w") as fh:
            fh.write(report)

    drift = has_drift(parsed)
    gh_output = os.environ.get("GITHUB_OUTPUT")
    if gh_output:
        with open(gh_output, "a") as fh:
            fh.write(f"drift={1 if drift else 0}\n")

    return 1 if drift else 0


if __name__ == "__main__":
    raise SystemExit(main())
