#!/usr/bin/env python3
"""Deklarierte Dienste, die auf ihrem Zielhost nicht laufen (platform#2586, K1).

Warum es das gibt (gemessen 2026-09-01):
  `up --remove-orphans` loescht Container, deren compose-Datei nicht in der
  `-f`-Kette steht. `scripts/deploy.sh` nimmt genau EINEN weiteren Dateinamen
  auf (`docker-compose.override.yml`, platform#1063) — jede andere Overlay-Datei
  bleibt draussen. Am 2026-09-01 wurde so `mcp_hub_rag` 34 Minuten nach seiner
  Erzeugung entfernt, ausgeloest vom selben Merge, der ihn gebaut hatte.
  `llm_gateway` und `mcp_hub_grafana` fehlten da laengst; niemandem war es
  aufgefallen, weil kein Melder danach sah.

  Dieser Melder schliesst die Beobachtungsluecke, nicht die Ursache. Die Ursache
  ist K2/K3 in platform#2586.

Der Melder ENTDECKT statt zu deklarieren: er liest die compose-Dateien der Repos
und vergleicht mit dem, was auf dem Host laeuft. Eine gepflegte Dienstliste waere
ein zweiter Ort, der selbst driften kann (dieselbe Lehre wie host_datei_drift).

**Der Dateibestand kommt aus `origin/<default>`, nicht aus dem Arbeitsverzeichnis.**
Meine erste Messung von Hand lief gegen einen Klon, der einen Commit zurueck lag,
und zaehlte darum drei statt vier compose-Dateien — die Waise, um die es ging,
tauchte gar nicht auf.

Exit-Codes: 0 = alles Deklarierte laeuft · 1 = Waise(n) gefunden · 2 = Aufruffehler
· 3 = nicht alles pruefbar. Exit 3 ist eine eigene Klasse: ein Host oder ein Repo,
das wir nicht lesen konnten, ist NICHT gruen
(🌀 feedback_scope_gap_must_be_an_exit_state).

Usage:
    tools/waisen_melder.py              # Bericht
    tools/waisen_melder.py --quiet      # nur die RESULT-Zeile (fuer den Runner)
    tools/waisen_melder.py --repo mcp-hub
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

import yaml

SSH = ("ssh", "-o", "ConnectTimeout=10", "-o", "BatchMode=yes")

# Nur compose-Dateien, die den PROD-Stand beschreiben. staging/dev/test/ci
# beschreiben andere Umgebungen; `.bak` ist Muell, der auf Hosts liegenbleibt
# (gesehen 2026-09-01: docker-compose.llm-mcp.yml.bak in /opt/mcp-hub).
COMPOSE_MUSTER = re.compile(r"^docker-compose[^/]*\.ya?ml$")
NICHT_PROD = ("staging", "dev", "test", "ci", "local", "example")

# Vokabular kommt aus tools/betriebsstatus.py — dieselbe Quelle wie fuer den
# Erreichbarkeits- und den TLS-Melder (#2586 K5).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from betriebsstatus import ERKLAERT  # noqa: E402


class Unpruefbar(Exception):
    """Etwas liess sich nicht lesen — Exit 3, nicht stillschweigend gruen."""


def prod_compose_dateien(namen: list[str]) -> list[str]:
    """Aus allen Dateinamen die heraussuchen, die den Prod-Stack beschreiben.

    Die Regel spiegelt `scripts/deploy.sh`, statt eine eigene zu erfinden: dort
    ist die Basisdatei `docker-compose.prod.yml`, falls vorhanden — sonst
    `docker-compose.yml`. Wo es also eine prod-Datei gibt, ist die nackte
    `docker-compose.yml` die ENTWICKLUNGS-Datei und beschreibt nichts, was auf
    dem Prod-Host laufen soll.

    Der erste Entwurf nahm sie mit und meldete daraufhin 36 Waisen — darunter
    `writing_hub_db_dev` und `tradinghub-web`, die auf prod nie gedacht waren.
    Ein Melder, der Erwartetes als Befund ausgibt, wird nach dem dritten Mal
    nicht mehr gelesen.
    """
    kandidaten = [
        n
        for n in sorted(namen)
        if COMPOSE_MUSTER.match(n) and not any(w in n.lower() for w in NICHT_PROD)
    ]
    if "docker-compose.prod.yml" in kandidaten:
        kandidaten = [n for n in kandidaten if n != "docker-compose.yml"]
    return kandidaten


def container_namen(compose_text: str) -> dict[str, str]:
    """Dienstname -> Containername aus einer compose-Datei.

    Ohne `container_name` benennt compose den Container `<projekt>-<dienst>-1`;
    dieser Melder kann das Projektpraefix nicht kennen und meldet dann den
    Dienstnamen. Das ist absichtlich: lieber ein Name, der beim Vergleich
    auffaellt, als eine stillschweigend uebersprungene Zeile.
    """
    daten = yaml.safe_load(compose_text) or {}
    ergebnis: dict[str, str] = {}
    for dienst, spec in (daten.get("services") or {}).items():
        spec = spec or {}
        # Einmal-Container (`restart: "no"`, z.B. cad-hubs `migrate`) laufen
        # nach getaner Arbeit absichtlich nicht mehr. Ebenso Dienste hinter
        # einem `profiles:`-Schalter — die startet nur, wer sie anfordert.
        if str(spec.get("restart", "")).strip('"') == "no" or spec.get("profiles"):
            continue
        ergebnis[dienst] = spec.get("container_name") or dienst
    return ergebnis


def zuordnung_aus_ports(ports_yaml: dict) -> dict[str, str]:
    """repo -> prod_host, aus der SoT. Nicht hier hartkodieren."""
    dienste = ports_yaml.get("services", ports_yaml)
    zuordnung: dict[str, str] = {}
    for eintrag in dienste.values():
        eintrag = eintrag or {}
        repo, host = eintrag.get("repo"), eintrag.get("prod_host")
        if repo and host:
            zuordnung[str(repo).split("/")[-1]] = host
    return zuordnung


def erklaerte_container(ports_yaml: dict) -> dict[str, str]:
    """Containername -> Grundwort, fuer Dienste, die absichtlich nicht laufen."""
    dienste = ports_yaml.get("services", ports_yaml)
    erklaert: dict[str, str] = {}
    for eintrag in dienste.values():
        eintrag = eintrag or {}
        name = eintrag.get("container_name")
        status = eintrag.get("betriebsstatus", "aktiv")
        if name and status in ERKLAERT:
            erklaert[name] = status
    return erklaert


def erklaerte_repos(ports_yaml: dict) -> dict[str, str]:
    """Repo -> Grundwort. Das Urteil faellt je HUB, nicht je Container.

    `ports.yaml` fuehrt pro Hub in aller Regel EINEN Dienst — den Web-Container.
    Ein stillgelegter Hub hat aber vier bis sechs Container, und die tauchten
    darum weiter als Waisen auf, obwohl das Urteil laengst in der SoT stand:
    am 2026-09-01 waren coach-hub, wedding-hub und odoo bereits `stillgelegt`,
    ihre worker/beat/db/redis wurden trotzdem gemeldet.

    Bei mehreren Eintraegen desselben Repos gewinnt `aktiv`: wenn irgendein
    Dienst des Hubs laufen soll, ist der Hub nicht ruhend.
    """
    dienste = ports_yaml.get("services", ports_yaml)
    je_repo: dict[str, set[str]] = {}
    for eintrag in dienste.values():
        eintrag = eintrag or {}
        repo = eintrag.get("repo")
        if not repo:
            continue
        status = eintrag.get("betriebsstatus", "aktiv")
        je_repo.setdefault(str(repo).split("/")[-1], set()).add(status)

    erklaert: dict[str, str] = {}
    for repo, stati in je_repo.items():
        if "aktiv" in stati:
            continue
        nicht_aktiv = [s for s in sorted(stati) if s in ERKLAERT]
        if nicht_aktiv:
            erklaert[repo] = nicht_aktiv[0]
    return erklaert


def urteile(
    deklariert: list[tuple[str, str, str, str]],
    laufend: dict[str, set[str]],
    erklaert: dict[str, str],
    erklaerte_hubs: dict[str, str] | None = None,
) -> dict[str, list]:
    """Reine Funktion: aus Bestand + Laufzustand die drei Toepfe bilden.

    `deklariert` ist (repo, host, datei, container). Doppelte Container-Namen
    entstehen normal — `docker-compose.yml` und `docker-compose.prod.yml`
    beschreiben oft denselben Dienst. Gezaehlt wird je (host, container) einmal.
    """
    gesehen: set[tuple[str, str]] = set()
    waisen, laeuft, entschuldigt = [], [], []
    for repo, host, datei, container in deklariert:
        schluessel = (host, container)
        if schluessel in gesehen:
            continue
        gesehen.add(schluessel)
        zeile = {"repo": repo, "host": host, "datei": datei, "container": container}
        if host not in laufend:
            continue  # Host unlesbar — der Aufrufer fuehrt das als unpruefbar
        if container in laufend[host]:
            laeuft.append(zeile)
        elif container in erklaert:
            entschuldigt.append(dict(zeile, grund=erklaert[container]))
        elif (erklaerte_hubs or {}).get(repo):
            entschuldigt.append(
                dict(zeile, grund=f"{erklaerte_hubs[repo]} (ganzer Hub)")
            )
        else:
            waisen.append(zeile)
    return {"waisen": waisen, "laeuft": laeuft, "entschuldigt": entschuldigt}


def _git(repo: Path, *args: str, timeout: int = 60) -> str:
    aus = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, timeout=timeout
    )
    if aus.returncode != 0:
        raise Unpruefbar(
            f"git {' '.join(args)} in {repo.name}: {aus.stderr.strip()[:120]}"
        )
    return aus.stdout


def default_ref(repo: Path) -> str:
    """origin/<default-branch> — der Bestand, gegen den gemessen wird."""
    try:
        kopf = _git(repo, "symbolic-ref", "refs/remotes/origin/HEAD").strip()
        return kopf.removeprefix("refs/remotes/")
    except Unpruefbar:
        return "origin/main"


def bestand_aus_git(repo: Path) -> dict[str, str]:
    """Dateiname -> Inhalt der Prod-compose-Dateien aus origin/<default>.

    Erst `fetch`, dann lesen: ohne das misst der Melder den Stand des letzten
    `git pull` und nicht den von main.
    """
    _git(repo, "fetch", "--quiet", "origin", timeout=120)
    ref = default_ref(repo)
    namen = _git(repo, "ls-tree", "--name-only", ref).splitlines()
    return {n: _git(repo, "show", f"{ref}:{n}") for n in prod_compose_dateien(namen)}


def laufende_container(ssh_ziel: str) -> set[str]:
    """Ein ssh-Aufruf je Host. Leere Antwort ist verdaechtig, nicht 'nichts laeuft'."""
    aus = subprocess.run(
        [*SSH, ssh_ziel, "docker ps --format '{{.Names}}'"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if aus.returncode != 0:
        raise Unpruefbar(f"{ssh_ziel}: {aus.stderr.strip()[:120]}")
    namen = {z.strip() for z in aus.stdout.splitlines() if z.strip()}
    if not namen:
        raise Unpruefbar(f"{ssh_ziel}: docker ps lieferte keine Zeile")
    return namen


def hosts_aus_registry(platform_dir: Path) -> dict[str, str]:
    """Hostname -> ssh-Ziel aus der Infra-SoT."""
    daten = yaml.safe_load((platform_dir / "infra/hosts.yaml").read_text())
    return {
        name: h["ssh"]
        for name, h in (daten.get("hosts") or {}).items()
        if isinstance(h, dict) and h.get("ssh")
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--quiet", action="store_true", help="nur die RESULT-Zeile")
    p.add_argument("--repo", help="nur dieses Repo pruefen")
    p.add_argument(
        "--github-dir",
        default=os.environ.get("GITHUB_DIR", str(Path.home() / "github")),
    )
    args = p.parse_args()

    platform_dir = Path(__file__).resolve().parent.parent
    github_dir = Path(args.github_dir)
    ports = yaml.safe_load((platform_dir / "infra/ports.yaml").read_text())

    zuordnung = zuordnung_aus_ports(ports)
    if args.repo:
        zuordnung = {k: v for k, v in zuordnung.items() if k == args.repo}
        if not zuordnung:
            print(f"FEHLER: {args.repo} steht mit prod_host in keiner ports.yaml-Zeile")
            return 2
    erklaert = erklaerte_container(ports)
    ssh_ziele = hosts_aus_registry(platform_dir)

    unpruefbar: list[str] = []
    deklariert: list[tuple[str, str, str, str]] = []

    for repo, host in sorted(zuordnung.items()):
        pfad = github_dir / repo
        if not (pfad / ".git").exists():
            unpruefbar.append(f"{repo}: kein Klon unter {pfad}")
            continue
        try:
            for datei, text in bestand_aus_git(pfad).items():
                for _dienst, container in container_namen(text).items():
                    deklariert.append((repo, host, datei, container))
        except (Unpruefbar, subprocess.TimeoutExpired, yaml.YAMLError) as e:
            unpruefbar.append(f"{repo}: {e}")

    laufend: dict[str, set[str]] = {}
    for host in sorted({h for _r, h, _d, _c in deklariert}):
        ziel = ssh_ziele.get(host)
        if not ziel:
            unpruefbar.append(f"{host}: kein ssh-Ziel in hosts.yaml")
            continue
        try:
            laufend[host] = laufende_container(ziel)
        except (Unpruefbar, subprocess.TimeoutExpired) as e:
            unpruefbar.append(str(e))

    ergebnis = urteile(deklariert, laufend, erklaert, erklaerte_repos(ports))
    waisen, laeuft, entschuldigt = (
        ergebnis["waisen"],
        ergebnis["laeuft"],
        ergebnis["entschuldigt"],
    )

    if not args.quiet:
        # Die laufenden werden MIT ausgegeben: eine Null bei den Waisen belegt
        # erst dann eine Abwesenheit, wenn derselbe Vergleich nachweislich auch
        # etwas findet (🌀 feedback_null_from_own_filter_needs_positive_control).
        print(f"Positivkontrolle: {len(laeuft)} deklarierte Container laufen")
        for z in laeuft[:5]:
            print(f"  ✅ {z['host']:<10} {z['container']:<30} {z['repo']}/{z['datei']}")
        if len(laeuft) > 5:
            print(f"  … und {len(laeuft) - 5} weitere")
        print()
        if entschuldigt:
            print(f"Erklaert ({len(entschuldigt)}) — betriebsstatus sagt es:")
            for z in entschuldigt:
                print(f"  ⏸ {z['host']:<10} {z['container']:<30} {z['grund']}")
            print()
        if waisen:
            print(
                f"WAISEN ({len(waisen)}) — deklariert, laeuft nicht, nirgends erklaert:"
            )
            for z in waisen:
                print(
                    f"  ❌ {z['host']:<10} {z['container']:<30} {z['repo']}/{z['datei']}"
                )
            print()
        if unpruefbar:
            print(f"Nicht pruefbar ({len(unpruefbar)}):")
            for u in unpruefbar:
                print(f"  ⚠ {u}")
            print()

    print(
        f"RESULT waisen={len(waisen)} laeuft={len(laeuft)} "
        f"erklaert={len(entschuldigt)} unpruefbar={len(unpruefbar)}"
    )
    if unpruefbar:
        return 3
    return 1 if waisen else 0


if __name__ == "__main__":
    sys.exit(main())
