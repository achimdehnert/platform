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

- **R1 kein_tag** — kein Tag in einer der Tag-Formen des Pakets im Quell-Repo.
- **R3 fremde_herkunft** — Attestation vorhanden, aber Repo, Org oder Workflow
  passt nicht zum Publisher aus `registry/pypi-fleet.yaml`.
- **R4 ohne_herkunft** — keine Attestation (404 oder 0 Bundles).
- **ohne_erwartung** — Attestation vorhanden, das Inventar kennt aber keinen
  Publisher. Befund am Inventar, nicht an der Version.
- R2 (Upload nach Tag-Erstellung) ist bewusst nicht gebaut, Anker #4018.

Erwartet wird je Paket nur die eigene Org (Retro 5c34f2 Befund 11): Heimat-Org
aus `registry/canonical.yaml`, während einer Migration zusätzlich
`publisher_current` aus `registry/iil-migration.yaml`. Tag-Formen und die
Remote-Publisher-Art stehen in `registry/pypi-release-melder.yaml`.

🌀 Null aus dem eigenen Fehlerfall ist keine Abwesenheit: Tag-Liste,
Integrity-API, PyPI-Antwort oder eine Datendatei nicht lesbar oder ohne den
erwarteten Schlüssel → `unbekannt`, nie R1/R4 und nie „0 Versionen“. Ein 404 von
PyPI ist dagegen die Aussage des Servers: Paket nicht veröffentlicht, gezählt als
„nicht auf PyPI“, kein Befund.

## Aufruf

    python3 tools/pypi_release_melder.py                 # Report, Fenster 30 Tage
    python3 tools/pypi_release_melder.py --seit-tagen 7
    python3 tools/pypi_release_melder.py --json
    python3 tools/pypi_release_melder.py --kurz          # eine Zeile
    # Runner-Phase 0.7.35: höchstens alle 6 Stunden ins Netz, sonst Ergebnis-Datei
    python3 tools/pypi_release_melder.py --kurz --ergebnis-datei X --frisch-stunden 6

Nur lesend, ohne Alarmkanal nach außen; Leser ist die Runner-Phase 0.7.35.
Exit 0 = kein Befund · 1 = Befund (R1/R3/R4/ohne Erwartung) · 2 = nicht prüfbar
(`unbekannt` ohne weiteren Befund, oder Datendatei unlesbar).
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
import melder_ergebnis  # noqa: E402
import registry_api  # noqa: E402
from pypi_fleet_inventory import FLEET_FILE, fetch_provenance  # noqa: E402

DATEN_DATEI = TOOLS_DIR.parent / "registry" / "pypi-release-melder.yaml"
MIGRATION_DATEI = TOOLS_DIR.parent / "registry" / "iil-migration.yaml"
MELDER = "pypi-release-melder"
STANDARD_FENSTER_TAGE = 30
# Im --kurz-Modus genannte Funde; der Rest steht im Langbericht.
KURZ_FUNDE = 3

R1 = "kein_tag"
R3 = "fremde_herkunft"
R4 = "ohne_herkunft"
OK = "ok"
UNBEKANNT = "unbekannt"
# Attestation da, aber pypi-fleet.yaml kennt keinen Publisher: Lücke im Inventar, kein R3.
OHNE_ERWARTUNG = "ohne_erwartung"
BEFUND_REGELN = (R1, R3, R4, OHNE_ERWARTUNG)

EXIT_OK = 0
EXIT_BEFUND = 1
EXIT_NICHT_PRUEFBAR = 2


class DatenFehler(ValueError):
    """Eine Datendatei fehlt, ist kaputt oder ihr fehlt ein Pflicht-Schlüssel."""


# --------------------------------------------------------------------------
# Daten laden (Fehler = DatenFehler, nie stiller Default)
# --------------------------------------------------------------------------


def _lies_yaml(pfad: Path) -> dict:
    try:
        daten = yaml.safe_load(Path(pfad).read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as e:
        raise DatenFehler(f"{pfad} nicht lesbar: {e.__class__.__name__}") from e
    if not isinstance(daten, dict):
        raise DatenFehler(f"{pfad} ist kein Mapping")
    return daten


def lade_daten(pfad: Path = DATEN_DATEI) -> dict:
    """Melder-Daten prüfen: fehlt ein Pflicht-Schlüssel, ist das kein leerer Default."""
    daten = _lies_yaml(pfad)
    remote = daten.get("publisher_remote")
    if not isinstance(remote, dict) or not remote.get("kind") or not remote.get("repo"):
        raise DatenFehler(f"{pfad}: publisher_remote.kind/.repo fehlt")
    formen = daten.get("tag_formen")
    if not isinstance(formen, list) or not formen:
        raise DatenFehler(f"{pfad}: tag_formen fehlt oder leer")
    pakete = daten.get("pakete", {})
    if not isinstance(pakete, dict):
        raise DatenFehler(f"{pfad}: pakete ist kein Mapping")
    for name, eintrag in pakete.items():
        eigene = (eintrag or {}).get("tag_formen")
        if not isinstance(eigene, list) or not eigene:
            raise DatenFehler(f"{pfad}: pakete.{name}.tag_formen fehlt oder leer")
    return daten


def lade_migration(pfad: Path = MIGRATION_DATEI) -> dict:
    pakete = _lies_yaml(pfad).get("packages")
    if not isinstance(pakete, dict):
        raise DatenFehler(f"{pfad}: packages fehlt")
    return pakete


def lade_flotte(pfad: Path) -> dict:
    pakete = _lies_yaml(pfad).get("packages")
    if not isinstance(pakete, dict):
        raise DatenFehler(f"{pfad}: packages fehlt")
    return pakete


# --------------------------------------------------------------------------
# Pure Funktionen (getestet in tools/tests/test_pypi_release_melder.py)
# --------------------------------------------------------------------------


def erwartete_orgs(repo: str, migration: dict, owner=registry_api.owner) -> set[str]:
    """Heimat-Org aus canonical.yaml, dazu `publisher_current` einer laufenden Migration."""
    orgs = {owner(repo), (migration.get(repo) or {}).get("publisher_current")}
    return {o for o in orgs if o}


def erwartung(pkg: dict, daten: dict, orgs_fuer) -> dict:
    """Erwartete Herkunft eines Pakets; `orgs_fuer(repo)` liefert die erlaubten Orgs."""
    remote = daten["publisher_remote"]
    repos: set[str] = set()
    workflows: set[str] = set()
    for pub in pkg.get("publishers") or []:
        quelle = remote["repo"] if pub.get("kind") == remote["kind"] else pkg.get("repo")
        repos.update(f"{org}/{quelle}" for org in orgs_fuer(quelle))
        workflows.update(w.get("file", "") for w in pub.get("workflows") or [])
    return {"repos": repos, "workflows": workflows}


def tag_formen(name: str, daten: dict) -> list[str]:
    eigene = (daten.get("pakete") or {}).get(name)
    return eigene["tag_formen"] if eigene else daten["tag_formen"]


def versionen_im_fenster(releases: dict, seit: datetime) -> dict[str, list[dict]] | None:
    """Versionen mit mindestens einer Datei, die seit `seit` hochgeladen wurde.

    `None` = unlesbar: eine Datei ohne `upload_time_iso_8601` ist keine alte Datei.
    """
    treffer = {}
    for version, dateien in releases.items():
        if not isinstance(dateien, list):
            return None
        zeiten = []
        for d in dateien:
            roh = d.get("upload_time_iso_8601") if isinstance(d, dict) else None
            if not isinstance(roh, str):
                return None
            zeiten.append(datetime.fromisoformat(roh.replace("Z", "+00:00")))
        if zeiten and max(zeiten) >= seit:
            treffer[version] = dateien
    return treffer


def pruefe_tag(dist: str, version: str, tags: set[str] | None, formen: list[str]) -> str:
    """OK, wenn eine der Tag-Formen des Pakets (`registry/pypi-release-melder.yaml`) existiert."""
    if tags is None:
        return UNBEKANNT
    erwartet = {f.format(version=version, dist=dist) for f in formen}
    return OK if erwartet & tags else R1


def pruefe_herkunft(status: int | None, body: bytes, erwartet: dict) -> tuple[str, list[dict]]:
    """Bewertet die Antwort der Integrity-API gegen die erwartete Herkunft."""
    if status == 404:
        return R4, []
    if status != 200 or not body:
        return UNBEKANNT, []
    try:
        antwort = json.loads(body)
    except json.JSONDecodeError:
        return UNBEKANNT, []
    bundles = antwort.get("attestation_bundles") if isinstance(antwort, dict) else None
    if not isinstance(bundles, list):
        return UNBEKANNT, []
    if not bundles:
        return R4, []
    publisher = [b.get("publisher") if isinstance(b, dict) else None for b in bundles]
    if not all(isinstance(p, dict) for p in publisher):
        return UNBEKANNT, [p for p in publisher if isinstance(p, dict)]
    if not erwartet["repos"]:
        return OHNE_ERWARTUNG, publisher
    passt = all(
        p.get("repository") in erwartet["repos"] and p.get("workflow") in erwartet["workflows"]
        for p in publisher
    )
    return (OK if passt else R3), publisher


def bewerte_version(
    dist: str, version: str, dateien: list[dict], tags: set[str] | None,
    erwartet: dict, formen: list[str], fetch=fetch_provenance,
) -> dict:
    befunde = []
    tag = pruefe_tag(dist, version, tags, formen)
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


def zaehle(bericht: dict) -> dict[str, int]:
    zahl = dict.fromkeys(BEFUND_REGELN, 0)
    zahl[UNBEKANNT] = len(bericht["pypi_unlesbar"])
    for v in bericht["versionen"]:
        for b in v["befunde"]:
            zahl[b] += 1
    return zahl


def exit_code(zahl: dict[str, int]) -> int:
    if any(zahl[r] for r in BEFUND_REGELN):
        return EXIT_BEFUND
    if zahl[UNBEKANNT]:
        return EXIT_NICHT_PRUEFBAR
    return EXIT_OK


def kopfzeile(bericht: dict, stand: str = "") -> str:
    zahl = zaehle(bericht)
    return (
        f"pypi-release-melder: {len(bericht['versionen'])} Versionen seit {bericht['seit']} · "
        f"R1 {zahl[R1]} · R3 {zahl[R3]} · R4 {zahl[R4]} · "
        f"ohne Erwartung {zahl[OHNE_ERWARTUNG]} · unbekannt {zahl[UNBEKANNT]} · "
        f"nicht auf PyPI {len(bericht.get('pypi_fehlt', []))}"
    ) + (f" [Stand {stand}]" if stand else "")


def kurzzeile(bericht: dict, stand: str = "") -> str:
    """Kopfzeile plus die ersten Funde — die eine Zeile, die die Runner-Phase zeigt."""
    zeile = kopfzeile(bericht, stand)
    funde = [
        f"{v['paket']} {v['version']} ({', '.join(v['befunde'])})"
        for v in bericht["versionen"] if v["befunde"]
    ] + [f"{d} (PyPI unlesbar)" for d in bericht["pypi_unlesbar"]]
    if funde:
        rest = len(funde) - KURZ_FUNDE
        zeile += " — " + "; ".join(funde[:KURZ_FUNDE]) + (f"; +{rest}" if rest > 0 else "")
    return zeile


# --------------------------------------------------------------------------
# Netz-I/O (fail-soft)
# --------------------------------------------------------------------------

PYPI_FEHLT = "fehlt"


def pypi_releases(dist: str, timeout: int = 10) -> dict | str | None:
    """`releases` von PyPI; `PYPI_FEHLT` bei 404, `None` = unlesbar.

    Fehlendes oder fremdartiges `releases` ist keine Abwesenheit von Versionen.
    """
    try:
        with urllib.request.urlopen(f"https://pypi.org/pypi/{dist}/json", timeout=timeout) as resp:  # noqa: S310
            daten = json.load(resp)
    except urllib.error.HTTPError as e:
        return PYPI_FEHLT if e.code == 404 else None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None
    releases = daten.get("releases") if isinstance(daten, dict) else None
    return releases if isinstance(releases, dict) else None


def repo_tags(repo: str, org: str | None, run=subprocess.run) -> set[str] | None:
    """Tag-Namen des Quell-Repos in seiner Heimat-Org; `None` = unlesbar, nie leere Menge."""
    if not org:
        return None
    try:
        proc = run(
            ["gh", "api", "--paginate", f"repos/{org}/{repo}/tags", "-q", ".[].name"],
            capture_output=True, text=True, timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return set(proc.stdout.split()) if proc.returncode == 0 else None


# --------------------------------------------------------------------------


def lauf(
    fleet_file: Path, seit: datetime, daten: dict, migration: dict,
    owner=registry_api.owner, tags_fuer=repo_tags, fetch=fetch_provenance,
) -> dict:
    pakete = lade_flotte(fleet_file)
    ergebnisse, unlesbar, fehlt = [], [], []

    def orgs_fuer(repo: str) -> set[str]:
        return erwartete_orgs(repo, migration, owner)

    for name, pkg in sorted(pakete.items()):
        pkg = pkg or {}
        dist = pkg.get("dist_name") or name
        releases = pypi_releases(dist)
        if releases == PYPI_FEHLT:
            fehlt.append(dist)
            continue
        fenster = versionen_im_fenster(releases, seit) if isinstance(releases, dict) else None
        if fenster is None:
            unlesbar.append(dist)
            continue
        if not fenster:
            continue
        quelle = pkg.get("repo") or name
        tags = tags_fuer(quelle, owner(quelle))
        erwartet = erwartung(pkg, daten, orgs_fuer)
        formen = tag_formen(name, daten)
        for version, dateien in sorted(fenster.items()):
            ergebnisse.append(bewerte_version(dist, version, dateien, tags, erwartet, formen, fetch))
    return {
        "seit": seit.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pakete": len(pakete),
        "versionen": ergebnisse,
        "pypi_unlesbar": unlesbar,
        "pypi_fehlt": fehlt,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seit-tagen", type=int, default=STANDARD_FENSTER_TAGE)
    ap.add_argument("--fleet-file", type=Path, default=FLEET_FILE)
    ap.add_argument("--daten-datei", type=Path, default=DATEN_DATEI)
    ap.add_argument("--migration-datei", type=Path, default=MIGRATION_DATEI)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--kurz", action="store_true")
    ap.add_argument("--ergebnis-datei", type=Path, help="Ergebnis ablegen (melder_ergebnis)")
    ap.add_argument(
        "--frisch-stunden", type=float, default=0,
        help="mit --ergebnis-datei: jüngeres Ergebnis lesen statt neu messen (0 = immer messen)",
    )
    args = ap.parse_args(argv)

    stand = ""
    vorher = None
    if args.ergebnis_datei and args.frisch_stunden > 0:
        vorher = melder_ergebnis.lies(args.ergebnis_datei, max_alter_tage=args.frisch_stunden / 24)
    if vorher is not None:
        bericht, stand = vorher["ergebnis"], vorher["gemessen_am"]
    else:
        seit = datetime.now(timezone.utc) - timedelta(days=args.seit_tagen)
        try:
            bericht = lauf(
                args.fleet_file, seit, lade_daten(args.daten_datei), lade_migration(args.migration_datei)
            )
        except DatenFehler as e:
            print(f"pypi-release-melder: nicht prüfbar — {e}")
            return EXIT_NICHT_PRUEFBAR
        if args.ergebnis_datei:
            melder_ergebnis.schreibe(args.ergebnis_datei, MELDER, bericht)
    rc = exit_code(zaehle(bericht))

    if args.json:
        print(json.dumps(bericht, indent=2, ensure_ascii=False, default=list))
        return rc
    if args.kurz:
        print(kurzzeile(bericht, stand))
        return rc
    print(kopfzeile(bericht, stand))
    for v in bericht["versionen"]:
        if v["befunde"]:
            print(f"  {v['paket']} {v['version']}: {', '.join(v['befunde'])}")
    for dist in bericht["pypi_unlesbar"]:
        print(f"  {dist}: PyPI nicht lesbar (unbekannt)")
    for dist in bericht.get("pypi_fehlt", []):
        print(f"  {dist}: nicht auf PyPI (404)")
    return rc


if __name__ == "__main__":
    sys.exit(main())
