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
                tail = tail[len(frac) :]
                break
        raw = f"{head}.{frac[:6]}{tail}"
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    return datetime.fromisoformat(raw).astimezone(timezone.utc)


def _snapshot_deckt_pfade(snap: dict, fragmente: list) -> bool:
    """Enthalten die `paths` des Snapshots JEDES geforderte Fragment?

    Teilstring-Vergleich mit Absicht: die restic-Pfade tragen den Hetzner-
    Volume-Mountpoint (`/mnt/HC_Volume_105908261/docker/volumes/…`), der sich bei
    einem Volume-Wechsel aendert. Geprueft wird der stabile Teil — der
    Docker-Volume-Name.
    """
    pfade = snap.get("paths") or []
    return all(any(f in p for p in pfade) for f in fragmente)


def newest_snapshot_age_hours(
    snapshots: list, tag: str, now: datetime, paths_contain: list | None = None
):
    """Alter (h) des jüngsten passenden Snapshots, oder None wenn keiner passt.

    `paths_contain` verschaerft den Treffer: der Snapshot zaehlt nur, wenn seine
    `paths` alle geforderten Fragmente enthalten. Ohne das wuerde ein
    **Sammel-Snapshot** — Tag `volumes` deckt die Volumes ALLER Apps in einem
    einzigen Snapshot — den Melder gruen halten, auch wenn genau die Pfade der
    geprueften App daraus verschwinden: der Tag bliebe ja frisch. Der Melder
    wuerde dann die Frische des Jobs bestaetigen statt die Abdeckung der App.
    """
    times = []
    for snap in snapshots:
        if tag not in (snap.get("tags") or []):
            continue
        if paths_contain and not _snapshot_deckt_pfade(snap, paths_contain):
            continue
        try:
            times.append(_parse_restic_time(snap["time"]))
        except (KeyError, ValueError):
            continue
    if not times:
        return None
    newest = max(times)
    return (now - newest).total_seconds() / 3600.0


def _checks_aus(entry: dict) -> list:
    """Prueflinge einer Soll-App — `checks`-Liste oder der einzelne `tag`.

    Eine App kann ueber MEHRERE Snapshots gesichert sein (risk-hub: Datenbank
    unter Tag `risk_hub_db`, Medien/MinIO im Sammel-Snapshot `volumes`). Der
    Melder kannte vorher nur einen Tag pro App und war deshalb blind fuer die
    zweite Haelfte.
    """
    if entry.get("checks"):
        return entry["checks"]
    return [{"tag": entry.get("tag", entry["app"])}]


def evaluate_app(entry: dict, snapshots, now: datetime) -> dict:
    """Bewertet eine Soll-App (pure, testbar).

    snapshots=None → Scaffold-Modus (Offsite nicht provisioniert) → deferred.
    status: 'ok' | 'violation' | 'deferred'. ALLE Prueflinge muessen passen —
    eine App gilt erst als gesichert, wenn jeder ihrer Bestandteile frisch ist.
    """
    app = entry["app"]
    if entry.get("deferred"):
        return {
            "app": app,
            "status": "deferred",
            "reasons": [entry.get("reason", "explizit deferred")],
        }
    if snapshots is None:
        return {
            "app": app,
            "status": "deferred",
            "reasons": ["Offsite (restic) noch nicht provisioniert — Scaffold"],
        }

    max_age = entry.get("max_age_hours", DEFAULT_MAX_AGE_HOURS)
    gruende = []
    for check in _checks_aus(entry):
        tag = check["tag"]
        pfade = check.get("paths_contain")
        was = check.get("label") or tag
        age = newest_snapshot_age_hours(snapshots, tag, now, pfade)
        if age is None:
            if pfade:
                gruende.append(
                    f"{was}: kein Snapshot mit Tag '{tag}', der {', '.join(pfade)} enthaelt"
                )
            else:
                gruende.append(f"{was}: kein restic-Snapshot mit Tag '{tag}'")
        elif age > max_age:
            gruende.append(
                f"{was}: jüngster Snapshot {age:.1f} h alt (> {max_age} h Soll)"
            )

    if gruende:
        return {"app": app, "status": "violation", "reasons": gruende}
    return {"app": app, "status": "ok", "reasons": []}


def evaluate_drill(drills_dir: Path, now: datetime, enforce: bool) -> dict:
    """Restore-Feuerübungs-Protokoll < DRILL_MAX_AGE_DAYS Tage alt?

    `enforce=False` (Default, bis G3 erstmals durchgeführt ist): fehlendes/
    veraltetes Protokoll ist nur `deferred` — der Meter spammt nicht, bevor es
    überhaupt eine Feuerübungs-Kadenz gibt. Erst wenn der Workflow `--enforce-
    drill` setzt (nach G3), wird Staleness zur Verletzung. Ein frisches Protokoll
    ist immer `ok`.
    """
    protocols = sorted(drills_dir.glob("*.md")) if drills_dir.is_dir() else []
    protocols = [p for p in protocols if p.name.lower() != "readme.md"]
    if not protocols:
        status = "violation" if enforce else "deferred"
        return {
            "app": "restore-drill",
            "status": status,
            "reasons": ["kein Feuerübungs-Protokoll in docs/runbooks/restore-drills/"],
        }
    newest = max(p.stat().st_mtime for p in protocols)
    age_days = (now.timestamp() - newest) / 86400.0
    if age_days > DRILL_MAX_AGE_DAYS:
        status = "violation" if enforce else "deferred"
        return {
            "app": "restore-drill",
            "status": status,
            "reasons": [
                f"jüngstes Protokoll {age_days:.0f} Tage alt (> {DRILL_MAX_AGE_DAYS})"
            ],
        }
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
    parser.add_argument(
        "--expected", required=True, nargs="+", help="Pfad(e) zur Soll-App-Liste (JSON)"
    )
    parser.add_argument(
        "--snapshots", help="restic-snapshots-JSON; fehlt → Scaffold (alles deferred)"
    )
    parser.add_argument(
        "--drills-dir",
        default="docs/runbooks/restore-drills",
        help="Verzeichnis der Feuerübungs-Protokolle",
    )
    parser.add_argument(
        "--enforce-drill",
        action="store_true",
        help="Fehlendes/veraltetes Feuerübungs-Protokoll als Verletzung "
        "werten (erst nach erfolgter G3-Erstübung setzen)",
    )
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
    results.append(
        evaluate_drill(Path(args.drills_dir), now, enforce=args.enforce_drill)
    )

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
