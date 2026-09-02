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

Exit-Codes: 0 = konform · 1 = ≥1 Verletzung · 2 = Aufruffehler ·
            3 = Scope-Luecke: keine Verletzung, aber ≥1 App deferred (KONZ-054 E3)

Warum Exit 3 (2026-08-30): der Meter stand 12 Tage auf gruen, weil sein Nenner
EINE App war — 8 von 10 Soll-Apps waren `deferred`, und deferred zaehlte als
konform. Ein Melder, der ungemessenes Gebiet als gruen verbucht, belohnt kleine
Nenner. Deshalb ist "nicht gemessen" jetzt ein eigener Zustand, der nie gruen
ist — und der Bericht sagt in der ersten Zeile, wie viel er ueberhaupt sieht.

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

#: App, fuer die ADR-241 §5 die quartalsweise Feuerübung verlangt — woertlich
#: "juengstes **risk-hub**-Backup in Wegwerf-Postgres restoren". Es ist genau EINE;
#: die uebrigen Klassen der RPO/RTO-Tabelle tragen keine Uebungspflicht.
#: Ueber `--drill-app` ueberschreibbar, falls das ADR die Pflicht spaeter ausweitet.
DRILL_APP = "risk-hub"


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


def _protokoll_datum(pfad: Path) -> datetime | None:
    """Datum aus dem Dateinamen `YYYY-MM-DD-<app>.md`, sonst None.

    **Nicht die mtime** (bis 2026-09-02, platform#2682): git speichert keine
    Aenderungszeiten, ein `actions/checkout` schreibt jede Datei frisch. In CI war
    damit JEDES Protokoll null Tage alt — die 100-Tage-Frist konnte dort nie
    greifen, auch nicht bei einem Protokoll von 2024. Lokal gemessen am
    2026-09-02: beide Protokolle trugen die Zeit des Auscheckens, ihre Namen
    dagegen den 25. und den 30. August.

    Die Benennung ist keine Kosmetik, sondern der einzige Traeger des Datums, der
    einen Checkout ueberlebt — das README verlangt sie ohnehin.
    """
    teile = pfad.stem.split("-")
    if len(teile) < 3:
        return None
    try:
        return datetime(
            int(teile[0]), int(teile[1]), int(teile[2]), tzinfo=timezone.utc
        )
    except ValueError:
        return None


def evaluate_drill(
    drills_dir: Path, now: datetime, enforce: bool, drill_app: str = DRILL_APP
) -> dict:
    """Feuerübungs-Protokoll DER PFLICHTIGEN APP < DRILL_MAX_AGE_DAYS Tage alt?

    `enforce=False` (Default, bis G3 erstmals durchgeführt ist): fehlendes/
    veraltetes Protokoll ist nur `deferred` — der Meter spammt nicht, bevor es
    überhaupt eine Feuerübungs-Kadenz gibt. Erst wenn der Workflow `--enforce-
    drill` setzt (nach G3), wird Staleness zur Verletzung. Ein frisches Protokoll
    ist immer `ok`.

    **Nur Protokolle der pflichtigen App zaehlen (seit 2026-09-02, platform#2682).**
    Vorher bewertete der Meter das juengste Protokoll im Ordner, egal zu welcher
    App — ein frisches Fremd-Protokoll setzte die 100-Tage-Uhr zurueck und konnte
    eine ausgefallene risk-hub-Übung bis zu 100 Tage verdecken. Der Fall war nicht
    theoretisch: am 2026-09-02 hielt `2026-08-30-config-prod.md` (Host-Konfiguration,
    nicht risk-hub) die Uhr.

    Fremd-Protokolle werden **nicht verworfen**, sondern im Grund benannt — sonst
    sieht die Meldung aus, als sei der Ordner leer, obwohl Arbeit darin liegt.
    Zuordnung ueber die Dateibenennung `YYYY-MM-DD-<app>.md` aus dem README.
    """
    alle = sorted(drills_dir.glob("*.md")) if drills_dir.is_dir() else []
    alle = [p for p in alle if p.name.lower() != "readme.md"]
    # `stem == app` faengt die fehlbenannte Datei `risk-hub.md` mit ein: sie
    # gehoert zur pflichtigen App und soll den klaren Grund "ohne Datum im Namen"
    # ausloesen statt still als fremdes Protokoll zu verschwinden.
    protocols = [
        p for p in alle if p.stem == drill_app or p.stem.endswith(f"-{drill_app}")
    ]
    if not protocols:
        status = "violation" if enforce else "deferred"
        fremd = f"; {len(alle)} Protokoll(e) anderer Apps liegen dort" if alle else ""
        return {
            "app": "restore-drill",
            "status": status,
            "reasons": [
                f"kein Feuerübungs-Protokoll fuer {drill_app} in "
                f"docs/runbooks/restore-drills/{fremd}"
            ],
        }
    datiert = [(_protokoll_datum(p), p) for p in protocols]
    datiert = [(d, p) for d, p in datiert if d is not None]
    if not datiert:
        status = "violation" if enforce else "deferred"
        return {
            "app": "restore-drill",
            "status": status,
            "reasons": [
                f"{len(protocols)} {drill_app}-Protokoll(e) ohne Datum im Namen — "
                "Frische nicht belegbar (Benennung YYYY-MM-DD-<app>.md, s. README)"
            ],
        }
    juengstes = max(d for d, _ in datiert)
    age_days = (now - juengstes).total_seconds() / 86400.0
    if age_days > DRILL_MAX_AGE_DAYS:
        status = "violation" if enforce else "deferred"
        return {
            "app": "restore-drill",
            "status": status,
            "reasons": [
                f"jüngstes {drill_app}-Protokoll {age_days:.0f} Tage alt "
                f"(> {DRILL_MAX_AGE_DAYS})"
            ],
        }
    return {"app": "restore-drill", "status": "ok", "reasons": []}


def render_report(results: list) -> str:
    """Markdown-Report für Issue/Discord (Stil wie branch-protection-meter)."""
    ok = [r for r in results if r["status"] == "ok"]
    deferred = [r for r in results if r["status"] == "deferred"]
    violations = [r for r in results if r["status"] == "violation"]

    # Gezaehlt wird ueber denselben Nenner wie in deckungszeile(): die Soll-Apps.
    # Der restore-drill ist eine eigene Zusicherung, keine App. Stand er in
    # derselben Summe, widersprachen sich zwei aufeinanderfolgende Zeilen —
    # "Geprueft 8 von 9 Soll-Apps" ueber "9 konform" (gefunden 2026-08-31).
    # Zwei Nenner nebeneinander sind schlimmer als eine fehlende Zahl: sie
    # lassen den Leser raten, welcher der beiden das Soll ist.
    apps = [r for r in results if r["app"] != "restore-drill"]
    ok_apps = [r for r in apps if r["status"] == "ok"]
    def_apps = [r for r in apps if r["status"] == "deferred"]
    viol_apps = [r for r in apps if r["status"] == "violation"]
    drill = next((r for r in results if r["app"] == "restore-drill"), None)

    lines = ["# backup-meter (ADR-241)", ""]
    lines.append(deckungszeile(results))
    lines.append(
        f"**{len(ok_apps)} konform · {len(viol_apps)} Verletzungen · "
        f"{len(def_apps)} deferred**"
    )
    if drill is not None:
        zeichen = {"ok": "✅", "deferred": "⏸", "violation": "❌"}
        lines.append(
            f"**Restore-Feueruebung:** {zeichen.get(drill['status'], '?')} "
            f"{drill['status']} (zaehlt nicht als Soll-App)"
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


def deckungszeile(results: list) -> str:
    """Erste Zeile jedes Berichts: wie viel vom Soll dieser Lauf ueberhaupt gemessen hat.

    Der Nenner ist Teil der Meldung. "2 konform" ohne "von 10" liest sich wie
    Vollstaendigkeit — und genau so wurde es 12 Tage lang gelesen.
    """
    apps = [r for r in results if r["app"] != "restore-drill"]
    gemessen = [r for r in apps if r["status"] != "deferred"]
    if not apps:
        return "**Geprueft 0 von 0 Soll-Apps** — keine Soll-Liste, keine Aussage"
    quote = 100 * len(gemessen) / len(apps)
    marke = "" if len(gemessen) == len(apps) else " — Scope-Luecke, kein Gruen"
    return (
        f"**Geprueft {len(gemessen)} von {len(apps)} Soll-Apps ({quote:.0f} %)**{marke}"
    )


def exit_code(results: list) -> int:
    """0 nur, wenn alles gemessen und nichts verletzt ist. 3 fuer "nicht alles gemessen"."""
    if any(r["status"] == "violation" for r in results):
        return 1
    if any(r["status"] == "deferred" for r in results):
        return 3
    return 0


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
        "--drill-app",
        default=DRILL_APP,
        help=f"App mit Uebungspflicht nach ADR-241 §5 (Default: {DRILL_APP})",
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
        evaluate_drill(
            Path(args.drills_dir),
            now,
            enforce=args.enforce_drill,
            drill_app=args.drill_app,
        )
    )

    report = render_report(results)
    print(report)
    if args.report:
        with open(args.report, "w") as fh:
            fh.write(report)

    violations = sum(1 for r in results if r["status"] == "violation")
    deferred = sum(1 for r in results if r["status"] == "deferred")
    gh_output = os.environ.get("GITHUB_OUTPUT")
    if gh_output:
        with open(gh_output, "a") as fh:
            fh.write(f"violations={violations}\n")
            fh.write(f"deferred={deferred}\n")

    return exit_code(results)


if __name__ == "__main__":
    raise SystemExit(main())
