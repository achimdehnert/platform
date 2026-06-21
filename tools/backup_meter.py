#!/usr/bin/env python3
"""ADR-241 §4: backup-meter — die maschinelle Confirmation der Backup-Baseline.

Prüft täglich zwei Dinge:

1. **Snapshot-Frische (Offsite):** für jede Soll-App aus
   governance/backup/expected-apps.json existiert ein restic-Snapshot mit Tag
   = App-Name, jünger als `max_age_hours` (Default 26 h, ADR-241 §4).
   Die Snapshot-Daten kommen aus `restic snapshots --json` (auf dem
   self-hosted Runner mit restic-Env erhoben) und werden via `--snapshots`
   übergeben. **Ohne `--snapshots` (= Offsite noch nicht provisioniert) gilt
   jede App als `deferred`, nicht als Verletzung** — der Meter ist dann grün,
   aber sichtbar „noch nicht scharf".

2. **Restore-Feuerübung (Repo-Artefakt):** ein Protokoll < 100 Tage alt in
   docs/runbooks/restore-drills/ (ADR-241 §Confirmation 4). Fehlt/veraltet es,
   sobald der Offsite-Modus scharf ist (`--snapshots` gesetzt), ist das eine
   Verletzung; im Scaffold-Modus nur ein Hinweis.

Exit-Codes: 0 = konform (oder deferred) · 1 = ≥1 Verletzung · 2 = Aufruffehler

Usage:
    # scharf (auf self-hosted Runner mit restic-Env):
    restic snapshots --json > /tmp/snap.json
    python3 tools/backup_meter.py \
        --expected governance/backup/expected-apps.json \
        --snapshots /tmp/snap.json \
        --drills-dir docs/runbooks/restore-drills \
        --report /tmp/backup-meter-report.md

    # scaffold (ohne Offsite — alles deferred, CI grün):
    python3 tools/backup_meter.py --expected governance/backup/expected-apps.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_MAX_AGE_HOURS = 26
DRILL_MAX_AGE_DAYS = 100


def _parse_restic_time(value: str) -> datetime:
    """restic-Zeitstempel (ISO 8601, ggf. mit Nanosekunden/Offset) → aware UTC."""
    raw = value.strip()
    # restic liefert z. B. '2026-06-21T04:00:11.123456789+02:00' — Python parst
    # max. Mikrosekunden, also Nanosekunden-Rest vor dem Offset kappen.
    if "." in raw:
        head, _, tail = raw.partition(".")
        frac = ""
        for ch in tail:
            if ch.isdigit():
                frac += ch
            else:
                tail = tail[len(frac):]
                break
        raw = f"{head}.{frac[:6]}{tail}"
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    return datetime.fromisoformat(raw).astimezone(timezone.utc)


def newest_snapshot_age_hours(snapshots: list, tag: str, now: datetime):
    """Alter (h) des jüngsten Snapshots mit `tag`, oder None wenn keiner."""
    times = []
    for snap in snapshots:
        if tag in (snap.get("tags") or []):
            try:
                times.append(_parse_restic_time(snap["time"]))
            except (KeyError, ValueError):
                continue
    if not times:
        return None
    newest = max(times)
    return (now - newest).total_seconds() / 3600.0


def evaluate_app(entry: dict, snapshots, now: datetime) -> dict:
    """Bewertet eine Soll-App (pure, testbar).

    snapshots=None → Scaffold-Modus (Offsite nicht provisioniert) → deferred.
    status: 'ok' | 'violation' | 'deferred'.
    """
    app = entry["app"]
    if entry.get("deferred"):
        return {"app": app, "status": "deferred",
                "reasons": [entry.get("reason", "explizit deferred")]}
    if snapshots is None:
        return {"app": app, "status": "deferred",
                "reasons": ["Offsite (restic) noch nicht provisioniert — Scaffold"]}

    tag = entry.get("tag", app)
    max_age = entry.get("max_age_hours", DEFAULT_MAX_AGE_HOURS)
    age = newest_snapshot_age_hours(snapshots, tag, now)
    if age is None:
        return {"app": app, "status": "violation",
                "reasons": [f"kein restic-Snapshot mit Tag '{tag}'"]}
    if age > max_age:
        return {"app": app, "status": "violation",
                "reasons": [f"jüngster Snapshot {age:.1f} h alt (> {max_age} h Soll)"]}
    return {"app": app, "status": "ok", "reasons": []}


def evaluate_drill(drills_dir: Path, now: datetime, scaffold: bool) -> dict:
    """Restore-Feuerübungs-Protokoll < DRILL_MAX_AGE_DAYS Tage alt?

    Im Scaffold-Modus (scaffold=True) ist ein fehlendes Protokoll nur deferred.
    """
    protocols = sorted(drills_dir.glob("*.md")) if drills_dir.is_dir() else []
    protocols = [p for p in protocols if p.name.lower() != "readme.md"]
    if not protocols:
        status = "deferred" if scaffold else "violation"
        return {"app": "restore-drill", "status": status,
                "reasons": ["kein Feuerübungs-Protokoll in docs/runbooks/restore-drills/"]}
    newest = max(p.stat().st_mtime for p in protocols)
    age_days = (now.timestamp() - newest) / 86400.0
    if age_days > DRILL_MAX_AGE_DAYS:
        status = "deferred" if scaffold else "violation"
        return {"app": "restore-drill", "status": status,
                "reasons": [f"jüngstes Protokoll {age_days:.0f} Tage alt (> {DRILL_MAX_AGE_DAYS})"]}
    return {"app": "restore-drill", "status": "ok", "reasons": []}


def render_report(results: list) -> str:
    """Markdown-Report für Issue/Discord (Stil wie branch-protection-meter)."""
    ok = [r for r in results if r["status"] == "ok"]
    deferred = [r for r in results if r["status"] == "deferred"]
    violations = [r for r in results if r["status"] == "violation"]

    lines = ["# backup-meter (ADR-241)", ""]
    lines.append(
        f"**{len(ok)} konform · {len(violations)} Verletzungen · {len(deferred)} deferred**"
    )
    if violations:
        lines += ["", "## ❌ Verletzungen", ""]
        for r in violations:
            for reason in r["reasons"]:
                lines.append(f"- **{r['app']}**: {reason}")
    if deferred:
        lines += ["", "## ⏸ Deferred (kein Alarm)", ""]
        for r in deferred:
            lines.append(f"- {r['app']}: {r['reasons'][0]}")
    if ok:
        lines += ["", "## ✅ Konform", ""]
        for r in ok:
            lines.append(f"- {r['app']}")
    return "\n".join(lines) + "\n"


def load_expected(paths: list) -> list:
    merged: list = []
    for path in paths:
        with open(path) as fh:
            merged.extend(json.load(fh))
    return merged


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected", required=True, nargs="+",
                        help="Pfad(e) zur Soll-App-Liste (JSON)")
    parser.add_argument("--snapshots",
                        help="restic-snapshots-JSON; fehlt → Scaffold (alles deferred)")
    parser.add_argument("--drills-dir", default="docs/runbooks/restore-drills",
                        help="Verzeichnis der Feuerübungs-Protokolle")
    parser.add_argument("--report", help="Markdown-Report in Datei schreiben")
    args = parser.parse_args()

    try:
        expected = load_expected(args.expected)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"❌ Soll-Liste nicht lesbar: {exc}", file=sys.stderr)
        return 2

    snapshots = None
    if args.snapshots:
        try:
            with open(args.snapshots) as fh:
                snapshots = json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"❌ Snapshots-JSON nicht lesbar: {exc}", file=sys.stderr)
            return 2

    now = datetime.now(timezone.utc)
    results = [evaluate_app(entry, snapshots, now) for entry in expected]
    results.append(evaluate_drill(Path(args.drills_dir), now, scaffold=snapshots is None))

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
    raise SystemExit(main())
