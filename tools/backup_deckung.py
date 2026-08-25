#!/usr/bin/env python3
"""backup_deckung.py — #2284 K1: jedes Prod-Volume ist gedeckt, verzichtet oder rot.

Die Grundgesamtheit ist `docker volume ls` auf dem Host — **nicht** eine gepflegte
Soll-Liste. `backup_meter.py` (ADR-241 §4) prueft, ob die Apps aus
`expected-apps.json` frische Snapshots haben; das ist die richtige Frage fuer
„laeuft das Backup?" und die falsche fuer „fehlt etwas?". Ein Volume, das in
keiner Liste steht, ist fuer den Meter unsichtbar — so blieben acht Volumes mit
2,1 GB ohne jeden Snapshot ([#2086](https://github.com/achimdehnert/platform/issues/2086)),
waehrend der Meter jeden Morgen gruen war. Dieses Werkzeug dreht die Richtung um:
es geht vom Host aus und verlangt fuer JEDES Volume eine von vier Antworten.

Klassen je Volume
-----------------
pgdump     gemountet von einem laufenden Postgres-Container, dessen pg_dumpall
           (restic-Tag = Containername) < 26 h alt ist. pgdata-Volumes werden
           bewusst nicht als Dateien gesichert (inkonsistent) — der Dump deckt sie.
volumes    der Volume-Pfad liegt in einem `volumes`-Snapshot < 26 h desselben Hosts.
verzicht   `governance/backup/volume-verzicht.yaml` nennt es MIT Grund.
anonym     Docker-Label `com.docker.volume.anonymous` — Scratch eines Containers
           ohne Namen und ohne Nutzdaten-Anspruch. Gezaehlt, nicht bewertet.
UNGEDECKT  alles andere. Das ist der Befund — ob verwaist oder in Nutzung.

Warum die Postgres-Erkennung dem Backup-Skript folgt und nicht dem Image
------------------------------------------------------------------------
`infra/host-maintenance/prod-offsite-daily.sh` sichert einen Container, wenn
`pg_isready` antwortet UND ein compose-Projekt-Label existiert (CI-Wegwerf-
container werden uebersprungen). Ein Volume zaehlt hier als `pgdump`-gedeckt nur,
wenn fuer genau diesen Containernamen ein frischer Dump liegt — nicht, weil das
Image nach Postgres aussieht. Sonst wuerde das Werkzeug die Absicht des Skripts
bestaetigen statt sein Ergebnis.

Exit-Codes
----------
0 = jedes Volume gedeckt oder verzichtet · 1 = ≥1 UNGEDECKT (ROT IST BEFUND)
2 = ein Host oder das restic-Repo war nicht erreichbar — der Lauf hat NICHT
    gemessen. Ein blindes Werkzeug darf nicht wie ein sauberer Befund aussehen
    ([#2278](https://github.com/achimdehnert/platform/issues/2278)).

Usage
-----
    python3 tools/backup_deckung.py              # Vollbericht (ssh je Prod-Host)
    python3 tools/backup_deckung.py --kurz       # eine Zeile fuer den Sitzungsstart
    python3 tools/backup_deckung.py --json
    python3 tools/backup_deckung.py --fixtures tools/tests/fixtures/backup_deckung
                                                 # ohne ssh: aus abgelegten Rohdaten
    python3 tools/backup_deckung.py --dump-fixtures DIR
                                                 # Rohdaten eines Echtlaufs ablegen
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

MAX_AGE_HOURS = 26  # ADR-241 §4 — dieselbe Frische wie backup_meter.py
PROD_HOSTS = ("prod", "prod-b")
SSH = ["ssh", "-o", "ConnectTimeout=10", "-o", "BatchMode=yes"]
SSH_TIMEOUT_S = 90
# Quelle: infra/host-maintenance/prod-offsite-daily.sh, Zeile `ENV_FILE=`.
# Beide Prod-Hosts pushen mit diesem Env in dasselbe append-only-Repo (ADR-289).
OFFSITE_ENV = "/etc/offsite-backup.env"
ANONYM_LABEL = "com.docker.volume.anonymous"
CONTAINER_TRENNER = "### CONTAINERS"

REPO_ROOT = Path(__file__).resolve().parent.parent
VERZICHT_YAML = REPO_ROOT / "governance" / "backup" / "volume-verzicht.yaml"
HOSTS_YAML = REPO_ROOT / "infra" / "hosts.yaml"


# --- Eingaben -----------------------------------------------------------------


def lade_hosts(pfad: Path) -> dict[str, str]:
    """{'prod': 'root@1.2.3.4', ...} — nur Prod-Hosts mit ssh-Zugang."""
    daten = yaml.safe_load(pfad.read_text(encoding="utf-8")) or {}
    roh = daten.get("hosts", daten) or {}
    raus = {}
    for name, cfg in roh.items():
        if name in PROD_HOSTS and isinstance(cfg, dict):
            ziel = cfg.get("ssh")
            if ziel and ziel != "-":
                raus[name] = str(ziel)
    return raus


def lade_verzicht(pfad: Path) -> dict[tuple[str, str], dict]:
    """{(host, volume): eintrag} — nur Eintraege MIT Grund zaehlen.

    Ein Verzicht ohne Grund ist keine Entscheidung, sondern ein Loch in der
    Liste; er wird wie „nicht vorhanden" behandelt und im Bericht genannt.
    """
    if not pfad.exists():
        return {}
    daten = yaml.safe_load(pfad.read_text(encoding="utf-8")) or {}
    raus = {}
    for e in daten.get("verzicht") or []:
        if not isinstance(e, dict):
            continue
        host, volume = str(e.get("host", "")), str(e.get("volume", ""))
        if host and volume:
            raus[(host, volume)] = e
    return raus


def fernbefehl_volumes() -> str:
    """Ein ssh-Aufruf je Host: Volumes (mit Groesse, Links, Labels) + Container.

    `docker system df -v --format '{{json .Volumes}}'` liefert Name, Links (= wie
    viele Container es mounten), Size, Mountpoint und Labels in einem Zug. Die
    `Mounts`-Spalte von `docker ps` waere die naheliegende Quelle fuer „in
    Nutzung" — sie kuerzt Volume-Namen aber ab und liefert dann 174 von 175
    Volumes als verwaist (gemessen 2026-08-25). Deshalb `inspect`.
    """
    return (
        "docker system df -v --format '{{json .Volumes}}'; "
        f"echo; echo '{CONTAINER_TRENNER}'; "
        "docker ps -q | xargs -r docker inspect --format "
        '\'{{.Name}}|{{.Config.Image}}|{{index .Config.Labels "com.docker.compose.project"}}|'
        '{{range .Mounts}}{{if eq .Type "volume"}}{{.Name}},{{end}}{{end}}\''
    )


def fernbefehl_snapshots() -> str:
    return f"set -a; . {OFFSITE_ENV}; set +a; restic snapshots --json"


def _sh(cmd: list[str], timeout: int) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout
    except subprocess.TimeoutExpired:
        return 124, ""
    except OSError:
        return 127, ""


def parse_host_rohdaten(text: str) -> dict:
    """Rohausgabe von `fernbefehl_volumes()` → {'volumes': [...], 'container': [...]}.

    Leere oder unparsbare Eingabe liefert None-Felder, nicht leere Listen —
    „keine Volumes" und „nichts gelesen" sind zwei verschiedene Aussagen.
    """
    if CONTAINER_TRENNER not in text:
        return {"volumes": None, "container": None}
    vol_teil, _, cont_teil = text.partition(CONTAINER_TRENNER)
    try:
        volumes = json.loads(vol_teil.strip() or "[]")
    except json.JSONDecodeError:
        return {"volumes": None, "container": None}
    container = []
    for zeile in cont_teil.strip().splitlines():
        teile = zeile.split("|")
        if len(teile) < 4:
            continue
        container.append(
            {
                "name": teile[0].lstrip("/"),
                "image": teile[1],
                "projekt": teile[2],
                "volumes": [v for v in teile[3].split(",") if v],
            }
        )
    return {"volumes": volumes, "container": container}


def _parse_restic_time(value: str) -> datetime:
    raw = value.strip()
    if "." in raw:
        head, _, tail = raw.partition(".")
        ziffern = ""
        for ch in tail:
            if ch.isdigit():
                ziffern += ch
            else:
                break
        raw = f"{head}.{ziffern[:6]}{tail[len(ziffern) :]}"
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    return datetime.fromisoformat(raw).astimezone(timezone.utc)


def frische_snapshots(snapshots: list, now: datetime) -> dict:
    """{host: {'pgdump': {tag,…}, 'volumes': {volumename,…}}} aus Snapshots < 26 h.

    Volume-Namen kommen aus den Snapshot-Pfaden (`…/volumes/<name>/_data`) —
    derselbe stabile Teil, den `backup_meter._snapshot_deckt_pfade` vergleicht.
    """
    raus: dict = {}
    grenze = now - timedelta(hours=MAX_AGE_HOURS)
    for s in snapshots:
        try:
            if _parse_restic_time(s["time"]) < grenze:
                continue
        except (KeyError, ValueError):
            continue
        host = s.get("hostname") or "?"
        eintrag = raus.setdefault(host, {"pgdump": set(), "volumes": set()})
        tags = set(s.get("tags") or [])
        if "pgdump" in tags:
            eintrag["pgdump"] |= tags - {"pgdump"}
        if "volumes" in tags:
            for p in s.get("paths") or []:
                if "/volumes/" in p:
                    eintrag["volumes"].add(p.split("/volumes/", 1)[1].split("/", 1)[0])
    return raus


# --- Bewertung ----------------------------------------------------------------


def _mb(size: str) -> float:
    m = re.match(r"([\d.]+)\s*([kMGT]?)B", size or "")
    if not m:
        return 0.0
    return (
        float(m.group(1))
        * {"": 1e-6, "k": 1e-3, "M": 1.0, "G": 1e3, "T": 1e6}[m.group(2)]
    )


def bewerte_host(host: str, daten: dict, frisch: dict, verzicht: dict) -> list[dict]:
    """Je Volume genau eine Klasse. Reihenfolge: pgdump → volumes → verzicht → anonym."""
    volumes = daten.get("volumes") or []
    container = daten.get("container") or []
    frisch_host = frisch.get(host) or {"pgdump": set(), "volumes": set()}
    # Volume → Container, der es mountet und dessen Dump frisch ist
    dump_deckt: dict[str, str] = {}
    laeuft: set[str] = set()
    for c in container:
        laeuft.update(c["volumes"])
        if c["name"] in frisch_host["pgdump"]:
            for v in c["volumes"]:
                dump_deckt.setdefault(v, c["name"])
    raus = []
    for v in volumes:
        name = v.get("Name", "")
        labels = v.get("Labels") or ""
        # `Links` zaehlt auch GESTOPPTE Container. coach-hub_coach_hub_pgdata auf
        # prod-b stand am 2026-08-25 mit Links=1 da, waehrend kein laufender
        # Container es mountete — der Dienst war seit dem 20.08. down. „in
        # Nutzung" haette das verdeckt; „Container steht" ist die Aussage.
        eintrag = {
            "host": host,
            "volume": name,
            "mb": round(_mb(v.get("Size", "0B")), 1),
            "links": int(v.get("Links") or 0),
            "laeuft": name in laeuft,
        }
        if name in dump_deckt:
            eintrag.update(klasse="pgdump", durch=dump_deckt[name])
        elif name in frisch_host["volumes"]:
            eintrag.update(klasse="volumes", durch="Sammel-Snapshot")
        elif (host, name) in verzicht:
            grund = verzicht[(host, name)].get("grund")
            if grund:
                eintrag.update(klasse="verzicht", durch=str(grund))
            else:
                eintrag.update(klasse="UNGEDECKT", durch="Verzicht OHNE Grund")
        elif ANONYM_LABEL in labels:
            eintrag.update(klasse="anonym", durch="")
        else:
            eintrag.update(klasse="UNGEDECKT", durch="")
        raus.append(eintrag)
    return raus


def bewerte(
    rohdaten: dict[str, str | None],
    snapshots: list | None,
    verzicht: dict,
    now: datetime,
) -> dict:
    """rohdaten: {host: Text|None}; snapshots: Liste|None (None = nicht erreichbar)."""
    blind = [h for h, t in rohdaten.items() if not t]
    geparst = {h: parse_host_rohdaten(t) for h, t in rohdaten.items() if t}
    blind += [h for h, d in geparst.items() if d["volumes"] is None]
    if snapshots is None:
        blind.append("restic")
    frisch = frische_snapshots(snapshots or [], now)
    eintraege = []
    for host, daten in geparst.items():
        if daten["volumes"] is not None:
            eintraege += bewerte_host(host, daten, frisch, verzicht)
    return {
        "stichtag": now.isoformat(timespec="minutes"),
        "blind": sorted(set(blind)),
        "volumes": eintraege,
        "klassen": dict(Counter(e["klasse"] for e in eintraege)),
    }


# --- Ausgabe ------------------------------------------------------------------


def _lage(v: dict) -> str:
    if v["laeuft"]:
        return "in Nutzung"
    if v["links"] > 0:
        return "Container steht"
    return "verwaist"


def _scope(e: dict) -> str:
    """Hosts, die dieser Lauf bewusst NICHT gemessen hat — kein Gruen fuer sie."""
    a = e.get("ausserhalb") or []
    return f" · nicht im Scope: {', '.join(a)}" if a else ""


def kurzzeile(e: dict) -> str:
    return _kurzzeile(e) + _scope(e)


def _kurzzeile(e: dict) -> str:
    if e["blind"]:
        return (
            f"Deckung NICHT messbar — nicht erreichbar: {', '.join(e['blind'])} "
            "(kein Urteil, keine Entwarnung)"
        )
    rot = [v for v in e["volumes"] if v["klasse"] == "UNGEDECKT"]
    k = e["klassen"]
    if not rot:
        return (
            f"OK: {len(e['volumes']) - k.get('anonym', 0)} Volume(s) gedeckt "
            f"({k.get('pgdump', 0)} pgdump, {k.get('volumes', 0)} volumes, "
            f"{k.get('verzicht', 0)} verzicht), {k.get('anonym', 0)} anonym"
        )
    mb = sum(v["mb"] for v in rot)
    verwaist = sum(1 for v in rot if v["links"] == 0)
    je_host = []
    for host in sorted({v["host"] for v in rot}):
        namen = sorted((v for v in rot if v["host"] == host), key=lambda v: -v["mb"])
        kopf = ", ".join(v["volume"] for v in namen[:3])
        rest = f" (+{len(namen) - 3} weitere)" if len(namen) > 3 else ""
        je_host.append(f"{host}: {kopf}{rest}")
    return (
        f"{len(rot)} Volume(s) ungedeckt ({mb:.0f} MB, davon {verwaist} verwaist) — "
        + " · ".join(je_host)
    )


def bericht(e: dict) -> str:
    z = [f"# Backup-Deckung vom Host aus — Stand {e['stichtag']}", ""]
    if e.get("ausserhalb"):
        z.append(
            f"◌ Nicht im Scope dieses Laufs: {', '.join(e['ausserhalb'])} — "
            "keine Aussage, keine Entwarnung (der Sitzungsstart misst beide Hosts)."
        )
        z.append("")
    if e["blind"]:
        z.append(
            f"⛔ NICHT messbar: {', '.join(e['blind'])} — dieser Lauf hat nicht gemessen."
        )
        z.append("")
    for host in sorted({v["host"] for v in e["volumes"]}):
        vols = [v for v in e["volumes"] if v["host"] == host]
        k = Counter(v["klasse"] for v in vols)
        z.append(
            f"## {host} — {len(vols)} Volumes: "
            + ", ".join(f"{n} {kl}" for kl, n in sorted(k.items()))
        )
        rot = sorted(
            (v for v in vols if v["klasse"] == "UNGEDECKT"), key=lambda v: -v["mb"]
        )
        if rot:
            z.append("")
            z.append(f"{'volume':<52}{'MB':>9}  {'links':>5}  hinweis")
            for v in rot:
                hinweis = v["durch"] or _lage(v)
                z.append(
                    f"{v['volume']:<52}{v['mb']:>9.1f}  {v['links']:>5}  {hinweis}"
                )
        z.append("")
    rot_gesamt = e["klassen"].get("UNGEDECKT", 0)
    if rot_gesamt:
        z.append(
            f"→ {rot_gesamt} Volume(s) ohne Antwort. Zulaessige Abschluesse je Zeile: ins Backup\n"
            f"  aufnehmen (Muster in prod-offsite-daily.sh), ODER Eintrag in\n"
            f"  governance/backup/volume-verzicht.yaml MIT Grund, ODER loeschen (Owner, #2258).\n"
            f"  Liegenlassen ist der vierte Weg und der einzige, den dieses Werkzeug rot haelt."
        )
    return "\n".join(z)


# --- CLI ----------------------------------------------------------------------


def _aufruf(name: str, ziel: str, befehl: str, lokal: set[str]) -> list[str]:
    """ssh — oder `bash -c`, wenn wir auf diesem Host SIND.

    Der prod-server-Runner laeuft als root auf prod und hat keinen ssh-Zugang
    zu sich selbst (gemessen 2026-08-25: Permission denied). Ein Workflow dort
    misst prod lokal; was er nicht erreicht, steht als Scope-Luecke im Bericht,
    nicht als Gruen.
    """
    if name in lokal:
        return ["bash", "-c", befehl]
    return SSH + [ziel, befehl]


def erhebe_live(
    hosts: dict[str, str], laeufer=None, lokal: set[str] | None = None
) -> tuple[dict, list | None]:
    laeufer = laeufer or (lambda cmd: _sh(cmd, SSH_TIMEOUT_S))
    lokal = lokal or set()
    roh: dict[str, str | None] = {}
    for name, ziel in hosts.items():
        code, out = laeufer(_aufruf(name, ziel, fernbefehl_volumes(), lokal))
        roh[name] = out if out.strip() else None
    snapshots = None
    # Lokaler Host zuerst: dort liegt das Env garantiert lesbar (backup-meter
    # nutzt es an derselben Stelle), und es spart einen ssh.
    reihenfolge = sorted(hosts.items(), key=lambda kv: kv[0] not in lokal)
    for name, ziel in reihenfolge:
        code, out = laeufer(_aufruf(name, ziel, fernbefehl_snapshots(), lokal))
        if out.strip():
            try:
                snapshots = json.loads(out)
                break
            except json.JSONDecodeError:
                continue
    return roh, snapshots


def lade_fixtures(verzeichnis: Path) -> tuple[dict, list | None]:
    roh = {}
    for p in sorted(verzeichnis.glob("host_*.txt")):
        roh[p.stem[len("host_") :]] = p.read_text(encoding="utf-8")
    snap = verzeichnis / "snapshots.json"
    snapshots = json.loads(snap.read_text(encoding="utf-8")) if snap.exists() else None
    return roh, snapshots


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument(
        "--kurz", action="store_true", help="eine Zeile fuer den Sitzungsstart"
    )
    p.add_argument("--json", action="store_true", dest="als_json")
    p.add_argument("--fixtures", type=Path, help="Rohdaten statt ssh (Tests/offline)")
    p.add_argument("--dump-fixtures", type=Path, help="Rohdaten dieses Laufs ablegen")
    p.add_argument("--hosts", type=Path, default=HOSTS_YAML)
    p.add_argument(
        "--nur",
        action="append",
        default=None,
        help="nur diese(n) Host(s) messen — die Luecke wird im Bericht genannt",
    )
    p.add_argument(
        "--lokal",
        action="append",
        default=None,
        help="Host, auf dem dieser Prozess laeuft (bash -c statt ssh)",
    )
    p.add_argument("--verzicht", type=Path, default=VERZICHT_YAML)
    p.add_argument("--now", default=None, help="ISO-Zeitpunkt (Tests)")
    a = p.parse_args(argv)

    now = datetime.fromisoformat(a.now) if a.now else datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    alle = lade_hosts(a.hosts)
    hosts = {h: z for h, z in alle.items() if not a.nur or h in a.nur}
    ausserhalb = sorted(set(alle) - set(hosts))
    if a.fixtures:
        roh, snapshots = lade_fixtures(a.fixtures)
    else:
        roh, snapshots = erhebe_live(hosts, lokal=set(a.lokal or []))
    if a.dump_fixtures:
        a.dump_fixtures.mkdir(parents=True, exist_ok=True)
        for host, text in roh.items():
            (a.dump_fixtures / f"host_{host}.txt").write_text(
                text or "", encoding="utf-8"
            )
        if snapshots is not None:
            (a.dump_fixtures / "snapshots.json").write_text(
                json.dumps(snapshots, indent=1), encoding="utf-8"
            )
    e = bewerte(roh, snapshots, lade_verzicht(a.verzicht), now)
    e["ausserhalb"] = ausserhalb

    if a.als_json:
        print(json.dumps(e, ensure_ascii=False, indent=2))
    elif a.kurz:
        print(kurzzeile(e))
    else:
        print(bericht(e))
    if e["blind"]:
        return 2
    return 1 if e["klassen"].get("UNGEDECKT") else 0


if __name__ == "__main__":
    sys.exit(main())
