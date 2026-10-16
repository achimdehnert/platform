#!/usr/bin/env python3
"""pypi_release_melder.py — passt jede neue PyPI-Version zu einem erwarteten Release?

## Warum es das gibt

KONZ-platform-072, Einsatzkonzept §2.2 (Owner „RW go“/„MB go“, 2026-10-16). Ein
gestohlenes Publish-Token oder eine zu weite Trusted-Publisher-Bindung fällt erst
auf, wenn jemand die fremde Version installiert (LiteLLM/Telnyx, April 2026). Der
Melder vergleicht deshalb, was auf PyPI **liegt**, mit dem, was die Flotte
**erwartet** — unabhängig davon, ob über GitHub, Forgejo oder per Hand publiziert
wird. Er erkennt Missbrauch, verhindert ihn nicht.

## Regeln (je Version im Zeitfenster)

- **R1 kein_tag** — kein Tag `v<version>` oder `<version>` im Quell-Repo.
- **R3 fremde_herkunft** — Attestation vorhanden, aber Repo oder Workflow passt
  nicht zum Publisher aus `registry/pypi-fleet.yaml`.
- **R4 ohne_herkunft** — keine Attestation (404 oder 0 Bundles).
- **ohne_erwartung** — Attestation vorhanden, das Inventar kennt aber keinen
  Publisher. Befund am Inventar, nicht an der Version.
- R2 (Upload nach Tag-Erstellung) ist bewusst nicht gebaut, Anker #4018.

🌀 Null aus dem eigenen Fehlerfall ist keine Abwesenheit: Tag-Liste oder
Integrity-API nicht lesbar → `unbekannt`, nie R1/R4.

## Aufruf

    python3 tools/pypi_release_melder.py                 # Report, Fenster 30 Tage
    python3 tools/pypi_release_melder.py --seit-tagen 7
    python3 tools/pypi_release_melder.py --json
    python3 tools/pypi_release_melder.py --kurz          # eine Zeile

Nur lesend, ohne Alarmkanal. Exit-Code 0 immer — Report-Werkzeug, kein Enforcer.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))
from pypi_fleet_inventory import FLEET_FILE, ORGS, fetch_provenance  # noqa: E402

PLATFORM_REPO = "platform"
PUBLISHER_REMOTE = "platform-remote"
STANDARD_FENSTER_TAGE = 30

R1 = "kein_tag"
R3 = "fremde_herkunft"
R4 = "ohne_herkunft"
OK = "ok"
UNBEKANNT = "unbekannt"
# Attestation da, aber pypi-fleet.yaml kennt keinen Publisher: Lücke im Inventar, kein R3.
OHNE_ERWARTUNG = "ohne_erwartung"


# --------------------------------------------------------------------------
# Pure Funktionen (getestet in tools/tests/test_pypi_release_melder.py)
# --------------------------------------------------------------------------


def erwartung(pkg: dict) -> dict:
    """Erwartete Herkunft eines Pakets aus seinem Eintrag in pypi-fleet.yaml."""
    repos: set[str] = set()
    workflows: set[str] = set()
    for pub in pkg.get("publishers") or []:
        quelle = PLATFORM_REPO if pub.get("kind") == PUBLISHER_REMOTE else pkg.get("repo")
        repos.update(f"{org}/{quelle}" for org in ORGS)
        workflows.update(w.get("file", "") for w in pub.get("workflows") or [])
    return {"repos": repos, "workflows": workflows}


def versionen_im_fenster(releases: dict, seit: datetime) -> dict[str, list[dict]]:
    """Versionen mit mindestens einer Datei, die seit `seit` hochgeladen wurde."""
    treffer = {}
    for version, dateien in releases.items():
        zeiten = [
            datetime.fromisoformat(d["upload_time_iso_8601"].replace("Z", "+00:00"))
            for d in dateien
            if d.get("upload_time_iso_8601")
        ]
        if zeiten and max(zeiten) >= seit:
            treffer[version] = dateien
    return treffer


def pruefe_tag(dist: str, version: str, tags: set[str] | None) -> str:
    """Akzeptiert die Tag-Formen der Flotte: `v1.2.0`, `1.2.0`, `<dist>@1.2.0`."""
    if tags is None:
        return UNBEKANNT
    return OK if {f"v{version}", version, f"{dist}@{version}"} & tags else R1


def pruefe_herkunft(status: int | None, body: bytes, erwartet: dict) -> tuple[str, list[dict]]:
    """Bewertet die Antwort der Integrity-API gegen die erwartete Herkunft."""
    if status == 404:
        return R4, []
    if status != 200 or not body:
        return UNBEKANNT, []
    try:
        bundles = json.loads(body).get("attestation_bundles", [])
    except json.JSONDecodeError:
        return UNBEKANNT, []
    if not bundles:
        return R4, []
    publisher = [b.get("publisher") or {} for b in bundles]
    if not erwartet["repos"]:
        return OHNE_ERWARTUNG, publisher
    passt = all(
        p.get("repository") in erwartet["repos"] and p.get("workflow") in erwartet["workflows"]
        for p in publisher
    )
    return (OK if passt else R3), publisher


def bewerte_version(
    dist: str, version: str, dateien: list[dict], tags: set[str] | None,
    erwartet: dict, fetch=fetch_provenance,
) -> dict:
    befunde = []
    tag = pruefe_tag(dist, version, tags)
    if tag != OK:
        befunde.append(tag)
    herkunft = []
    for datei in dateien:
        status, body = fetch(dist, version, datei.get("filename", ""))
        ergebnis, publisher = pruefe_herkunft(status, body, erwartet)
        herkunft.append({"datei": datei.get("filename"), "ergebnis": ergebnis, "publisher": publisher})
        if ergebnis != OK and ergebnis not in befunde:
            befunde.append(ergebnis)
    return {"paket": dist, "version": version, "befunde": befunde, "herkunft": herkunft}


# --------------------------------------------------------------------------
# Netz-I/O (fail-soft)
# --------------------------------------------------------------------------


def pypi_releases(dist: str, timeout: int = 10) -> dict | None:
    try:
        with urllib.request.urlopen(f"https://pypi.org/pypi/{dist}/json", timeout=timeout) as resp:  # noqa: S310
            return json.load(resp).get("releases", {})
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None


def repo_tags(repo: str) -> set[str] | None:
    """Tag-Namen des Quell-Repos über `gh api`, erste Org aus ORGS, die antwortet."""
    for org in ORGS:
        proc = subprocess.run(
            ["gh", "api", "--paginate", f"repos/{org}/{repo}/tags", "-q", ".[].name"],
            capture_output=True, text=True, timeout=60,
        )
        if proc.returncode == 0:
            return set(proc.stdout.split())
    return None


# --------------------------------------------------------------------------


def lauf(fleet_file: Path, seit: datetime) -> dict:
    pakete = (yaml.safe_load(fleet_file.read_text()) or {}).get("packages") or {}
    ergebnisse, unlesbar = [], []
    for name, pkg in sorted(pakete.items()):
        dist = pkg.get("dist_name") or name
        releases = pypi_releases(dist)
        if releases is None:
            unlesbar.append(dist)
            continue
        fenster = versionen_im_fenster(releases, seit)
        if not fenster:
            continue
        quelle = pkg.get("repo") or name
        tags = repo_tags(quelle)
        erwartet = erwartung(pkg)
        for version, dateien in sorted(fenster.items()):
            ergebnisse.append(bewerte_version(dist, version, dateien, tags, erwartet))
    return {
        "seit": seit.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pakete": len(pakete),
        "versionen": ergebnisse,
        "pypi_unlesbar": unlesbar,
    }


def zaehle(bericht: dict) -> dict[str, int]:
    zahl = {R1: 0, R3: 0, R4: 0, OHNE_ERWARTUNG: 0, UNBEKANNT: len(bericht["pypi_unlesbar"])}
    for v in bericht["versionen"]:
        for b in v["befunde"]:
            zahl[b] += 1
    return zahl


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seit-tagen", type=int, default=STANDARD_FENSTER_TAGE)
    ap.add_argument("--fleet-file", type=Path, default=FLEET_FILE)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--kurz", action="store_true")
    args = ap.parse_args()

    seit = datetime.now(timezone.utc) - timedelta(days=args.seit_tagen)
    bericht = lauf(args.fleet_file, seit)
    zahl = zaehle(bericht)

    if args.json:
        print(json.dumps(bericht, indent=2, ensure_ascii=False, default=list))
        return 0
    kopf = (
        f"pypi-release-melder: {len(bericht['versionen'])} Versionen seit {bericht['seit']} · "
        f"R1 {zahl[R1]} · R3 {zahl[R3]} · R4 {zahl[R4]} · "
        f"ohne Erwartung {zahl[OHNE_ERWARTUNG]} · unbekannt {zahl[UNBEKANNT]}"
    )
    print(kopf)
    if args.kurz:
        return 0
    for v in bericht["versionen"]:
        if v["befunde"]:
            print(f"  {v['paket']} {v['version']}: {', '.join(v['befunde'])}")
    for dist in bericht["pypi_unlesbar"]:
        print(f"  {dist}: PyPI nicht lesbar (unbekannt)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
