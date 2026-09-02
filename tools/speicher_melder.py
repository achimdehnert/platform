#!/usr/bin/env python3
"""speicher_melder.py — #2284 K3: Platten melden ihr Volllaufen VORHER, nicht bei 90 %.

Anlass: die Reparatur des dev-hub-Backups schreibt seit dem 2026-08-24 rund 6,3 GB
pro Tag auf die Root-Platte von `prod` ([infra-deploy#5]). Bei 43 GB frei sind das
sieben Tage — und kein Melder haette es gesagt, weil keiner die Platten misst.
Eine Schwelle („warnen bei 90 %") haette beim dritten Tag noch geschwiegen und
beim sechsten gerufen; ein Wochenende dazwischen, und die Platte ist voll.

Was gemessen wird
-----------------
`df -B1` auf jedem Host mit ssh-Zugang aus `infra/hosts.yaml` — Prod, Staging und
der Offsite-Host. Letzterer gehoert dazu, weil eine volle Offsite-Platte das
Backup lautlos beendet: `restic backup` scheitert, der Cron laeuft weiter, und
erst der 26-h-Melder ruft, wenn es zu spaet ist.

Wie die Vorlaufzeit entsteht
----------------------------
Jeder Lauf schreibt je (Host, Mount) einen Tagespunkt in ein Journal — mehrere
Laeufe am selben Tag ersetzen sich, der letzte gilt. Aus den Tagespunkten der
letzten acht Tage entstehen Tagesdifferenzen; ihr **Median** ist die Rate.
Median, nicht Steigung aus zwei Punkten: ein einzelner Tagesdump oder ein
`docker system prune` waere sonst die ganze Prognose.

    Tage bis voll = frei / (-Median der Tagesdifferenz)     falls Median < 0

Drei Zustaende, alle laut:
  SAMMELPHASE  weniger als zwei Tagespunkte — es gibt noch keine Rate. Das ist
               ausdruecklich KEINE Entwarnung; die 10-%-Untergrenze gilt trotzdem.
  vorlaeufig   genau zwei Tagespunkte — eine Rate aus einer Differenz. Sie wird
               genannt, aber als vorlaeufig markiert.
  belastbar    drei oder mehr Tagespunkte — Median.

Warum ein Journal und nicht `sar`
---------------------------------
`prod` hat sysstat, aber `SADC_OPTIONS="-S DISK"` — Geraete-I/O, kein Fuellstand
(`sar -F` antwortet „Requested activities not available", gemessen 2026-08-25).
Das Journal liegt neben `befund-journal.json` unter `~/.claude/`; ein Host-Eingriff
(XDISK aktivieren) waere IaC-pflichtig und liefert nichts, was das Journal nicht
auch liefert.

Exit-Codes
----------
0 = OK oder SAMMELPHASE · 1 = ≥1 Platte < 7 Tage oder < 10 % frei
2 = kein einziger Host erreichbar — blind ist nicht gruen.
3 = sauber gemessen, aber `--nur HOST` liess Hosts aus (Scope-Luecke) — gleicher
    Vertrag wie backup_deckung.py, damit der Workflow beide gleich liest.
Ein einzelner unerreichbarer Host ist ein WARN-Befund, kein Werkzeugfehler.

Usage
-----
    python3 tools/speicher_melder.py --kurz          # eine Zeile fuer den Sitzungsstart
    python3 tools/speicher_melder.py                 # Vollbericht
    python3 tools/speicher_melder.py --journal PFAD  # Tests / Zweitjournal
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from statistics import median

import yaml

WARN_TAGE = 7
WARN_PROZENT_FREI = 10.0
FENSTER_TAGE = 8
SSH = ["ssh", "-o", "ConnectTimeout=10", "-o", "BatchMode=yes"]
SSH_TIMEOUT_S = 30
REPO_ROOT = Path(__file__).resolve().parent.parent
HOSTS_YAML = REPO_ROOT / "infra" / "hosts.yaml"
JOURNAL_STANDARD = (
    Path(os.environ.get("HOME", "/tmp")) / ".claude" / "speicher-journal.jsonl"
)
# Pseudo-Dateisysteme, die df sonst als „Platte" fuehrt.
# `fuse.snapfuse` und `rootfs` kamen 2026-09-02 dazu: unter WSL bindet snapd seine
# Images NICHT als `squashfs` ein, sondern ueber snapfuse — acht davon standen auf
# der gpu-box als „0 GB frei (0 %)" im Bericht, obwohl ein nur lesbares Image nie
# volllaufen kann. `rootfs` ist das WSL-Init (`/init`), ebenfalls keine Platte.
DF_AUSSCHLUSS = (
    "tmpfs",
    "devtmpfs",
    "overlay",
    "squashfs",
    "fuse.snapfuse",
    "rootfs",
    "efivarfs",
    "fuse.lxcfs",
)

# Mount-Praefixe, die keine eigene Platte sind, obwohl ihr Dateisystem echt ist.
# `/boot*`: 1 GB, aendert sich nur beim Kernel-Update — „0 GB frei (100 %)" liest
# sich wie ein Befund, ist aber keiner (Erstlauf 2026-08-25).
# `/usr/lib/wsl/`: WSL-Innenleben. `/usr/lib/wsl/drivers` ist ein zweiter Blick auf
# dieselbe Windows-Platte, die unter `/mnt/c` schon steht — byte-gleich in Groesse
# und frei (gemessen gpu-box 2026-09-02). Zweimal dieselbe Platte sind zwei Zeilen
# im Bericht und ein doppelt gezaehlter Befund; `/mnt/c` ist die ehrliche davon.
MOUNT_AUSSCHLUSS = ("/boot", "/usr/lib/wsl/")


# --- Eingaben -----------------------------------------------------------------


def lade_hosts(pfad: Path) -> dict[str, str]:
    """Alle Hosts mit ssh-Zugang — hier bewusst nicht nur Prod (siehe Kopf)."""
    daten = yaml.safe_load(pfad.read_text(encoding="utf-8")) or {}
    roh = daten.get("hosts", daten) or {}
    raus = {}
    for name, cfg in roh.items():
        if isinstance(cfg, dict):
            ziel = cfg.get("ssh")
            if ziel and ziel != "-":
                raus[name] = str(ziel).split()[0]
    return raus


def lade_shells(pfad: Path) -> dict[str, str]:
    """Knoten mit eigener Fern-Shell: Name -> `ssh_shell` aus `infra/hosts.yaml`.

    Windows-Knoten (gpu-box) landen ueber OpenSSH in `cmd`. Der Fernbefehl enthaelt
    eine Pipe — die fuehrt `cmd` selbst aus, statt sie an die Ziel-Shell
    durchzureichen. `flottenbild.py` loest das laengst ueber stdin an `bash -s`;
    hier fehlte es, und die gpu-box fiel still aus der Zeitreihe (platform#2541).
    """
    daten = yaml.safe_load(pfad.read_text(encoding="utf-8")) or {}
    roh = daten.get("hosts", daten) or {}
    return {
        name: str(cfg["ssh_shell"])
        for name, cfg in roh.items()
        if isinstance(cfg, dict) and cfg.get("ssh_shell")
    }


def lade_hops(pfad: Path) -> dict[str, str]:
    """Knoten hinter einem Sprung: Name -> `ssh_via` aus `infra/hosts.yaml`.

    Warum das noetig ist: `gpu-box` und `gx10` haengen an wg0 und sind nur von prod
    aus erreichbar — der Schluessel liegt dort. Ohne den Sprung meldete dieses
    Werkzeug fuer beide "kein Host erreichbar" und liess sie still aus der
    Zeitreihe fallen (gemessen 2026-08-31 fuer beide Knoten). `flottenbild.py`
    kennt `ssh_via` laengst; hier fehlte es.
    """
    daten = yaml.safe_load(pfad.read_text(encoding="utf-8")) or {}
    roh = daten.get("hosts", daten) or {}
    return {
        name: str(cfg["ssh_via"]).split()[0]
        for name, cfg in roh.items()
        if isinstance(cfg, dict) and cfg.get("ssh_via")
    }


def fernbefehl() -> str:
    ausschluss = " ".join(f"-x {t}" for t in DF_AUSSCHLUSS)
    return f"df -B1 --output=target,size,avail {ausschluss} 2>/dev/null | tail -n +2"


def _sh(cmd: list[str], timeout: int, stdin: str | None = None) -> tuple[int, str]:
    try:
        p = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, input=stdin
        )
        return p.returncode, p.stdout
    except subprocess.TimeoutExpired:
        return 124, ""
    except OSError:
        return 127, ""


def parse_df(text: str) -> list[dict]:
    """df-Zeilen → Platten; Mounts unter `MOUNT_AUSSCHLUSS` fallen heraus.

    Der Dateisystem-Filter sitzt im Fernbefehl (`df -x`), dieser hier im Ergebnis:
    manche Mounts tragen ein echtes Dateisystem und sind trotzdem keine eigene
    Platte (Kernel-Boot-Partition, zweiter Blick auf eine schon gezaehlte Platte).
    """
    raus = []
    for zeile in text.splitlines():
        teile = zeile.split()
        if len(teile) != 3 or teile[0].startswith(MOUNT_AUSSCHLUSS):
            continue
        try:
            raus.append(
                {"mount": teile[0], "size": int(teile[1]), "avail": int(teile[2])}
            )
        except ValueError:
            continue
    return raus


def messe(
    hosts: dict[str, str],
    laeufer=None,
    lokal: set[str] | None = None,
    hops: dict[str, str] | None = None,
    shells: dict[str, str] | None = None,
) -> dict[str, list[dict] | None]:
    """`lokal` = Hosts, auf denen dieser Prozess selbst laeuft (bash -c statt ssh).
    Der prod-server-Runner hat keinen ssh-Zugang zu sich selbst.
    `hops` = Knoten hinter einem Sprung (`ssh_via`): das df laeuft dann vom Hop aus.
    `shells` = Knoten mit eigener Fern-Shell (`ssh_shell`, Windows/WSL): der Befehl
    geht dann ueber **stdin**, weil die Zwischenstation `cmd` sonst die Pipe im df
    selbst ausfuehrt."""
    laeufer = laeufer or (lambda cmd, stdin=None: _sh(cmd, SSH_TIMEOUT_S, stdin))
    lokal = lokal or set()
    hops = hops or {}
    shells = shells or {}
    raus: dict = {}
    for name, ziel in hosts.items():
        shell, stdin = shells.get(name), None
        if name in lokal:
            cmd = ["bash", "-c", fernbefehl()]
        elif shell:
            stdin = fernbefehl()
            if hops.get(name):
                innen = f'ssh -o BatchMode=yes -o ConnectTimeout=10 {ziel} "{shell}"'
                cmd = SSH + [hops[name], innen]
            else:
                cmd = SSH + [ziel, shell]
        elif hops.get(name):
            innen = f'ssh -o BatchMode=yes -o ConnectTimeout=10 {ziel} "{fernbefehl()}"'
            cmd = SSH + [hops[name], innen]
        else:
            cmd = SSH + [ziel, fernbefehl()]
        # Ein-Argument-Aufruf bleibt der Normalfall: die vorhandenen Test-Doubles
        # (und jeder andere Aufrufer) nehmen nur `cmd`. Nur der Windows-Weg braucht
        # das zweite Argument.
        _, out = laeufer(cmd) if stdin is None else laeufer(cmd, stdin)
        platten = parse_df(out)
        raus[name] = platten if platten else None
    return raus


# --- Journal ------------------------------------------------------------------


def lies_journal(pfad: Path) -> list[dict]:
    if not pfad.exists():
        return []
    raus = []
    for zeile in pfad.read_text(encoding="utf-8").splitlines():
        try:
            e = json.loads(zeile)
            if {"datum", "host", "mount", "size", "avail"} <= set(e):
                raus.append(e)
        except json.JSONDecodeError:
            continue
    return raus


def schreibe_journal(
    pfad: Path, eintraege: list[dict], heute: date, messung: dict
) -> list[dict]:
    """Heutige Punkte ersetzen, aeltere behalten; komplette Datei neu schreiben."""
    heute_s = heute.isoformat()
    behalten = [e for e in eintraege if e["datum"] != heute_s]
    for host, platten in messung.items():
        for p in platten or []:
            behalten.append({"datum": heute_s, "host": host, **p})
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text("".join(json.dumps(e) + "\n" for e in behalten), encoding="utf-8")
    return behalten


# --- Prognose -----------------------------------------------------------------


def prognose(punkte: list[dict], heute: date) -> dict:
    """Aus Tagespunkten (datum, avail) einer Platte: Rate und Tage bis voll.

    Differenzen werden je Kalendertag normiert — zwei Punkte drei Tage
    auseinander ergeben eine Tagesrate, keine Dreitagesrate.
    """
    grenze = heute - timedelta(days=FENSTER_TAGE)
    reihe = sorted(
        (
            (date.fromisoformat(p["datum"]), p["avail"])
            for p in punkte
            if date.fromisoformat(p["datum"]) >= grenze
        ),
    )
    if len(reihe) < 2:
        return {
            "stand": "SAMMELPHASE",
            "punkte": len(reihe),
            "rate": None,
            "tage": None,
        }
    raten = []
    for (d0, a0), (d1, a1) in zip(reihe, reihe[1:]):
        tage = (d1 - d0).days
        if tage > 0:
            raten.append((a1 - a0) / tage)
    if not raten:
        return {
            "stand": "SAMMELPHASE",
            "punkte": len(reihe),
            "rate": None,
            "tage": None,
        }
    rate = median(raten)
    stand = "vorlaeufig" if len(reihe) == 2 else "belastbar"
    _, frei = reihe[-1]
    tage = None if rate >= 0 else frei / -rate
    return {"stand": stand, "punkte": len(reihe), "rate": rate, "tage": tage}


def bewerte(messung: dict, journal: list[dict], heute: date) -> dict:
    platten = []
    for host, liste in messung.items():
        if liste is None:
            continue
        for p in liste:
            punkte = [
                e for e in journal if e["host"] == host and e["mount"] == p["mount"]
            ]
            pr = prognose(punkte, heute)
            prozent = 100.0 * p["avail"] / p["size"] if p["size"] else 0.0
            warn = prozent < WARN_PROZENT_FREI or (
                pr["tage"] is not None and pr["tage"] < WARN_TAGE
            )
            platten.append(
                {
                    "host": host,
                    "mount": p["mount"],
                    "frei_gb": p["avail"] / 1e9,
                    "prozent_frei": prozent,
                    "warn": warn,
                    **pr,
                }
            )
    return {
        "heute": heute.isoformat(),
        "unerreichbar": sorted(h for h, v in messung.items() if v is None),
        "blind": bool(messung) and all(v is None for v in messung.values()),
        "platten": platten,
    }


# --- Ausgabe ------------------------------------------------------------------


def _platte_kurz(p: dict) -> str:
    kopf = f"{p['host']} {p['mount']} — {p['frei_gb']:.0f} GB frei ({p['prozent_frei']:.0f} %)"
    if p["tage"] is not None:
        zusatz = f", ~{p['tage']:.0f} d bis voll"
        if p["stand"] == "vorlaeufig":
            zusatz += " (vorlaeufig)"
        return kopf + zusatz
    if p["stand"] == "SAMMELPHASE":
        return kopf
    return kopf + ", stabil"


def kurzzeile(e: dict) -> str:
    a = e.get("ausserhalb") or []
    return _kurzzeile(e) + (f" · nicht im Scope: {', '.join(a)}" if a else "")


def _kurzzeile(e: dict) -> str:
    if e["blind"]:
        return "Speicher NICHT messbar — kein Host erreichbar (kein Urteil, keine Entwarnung)"
    warn = [p for p in e["platten"] if p["warn"]]
    praefix = ""
    if e["unerreichbar"]:
        praefix = f"nicht erreichbar: {', '.join(e['unerreichbar'])} · "
    if warn:
        return f"WARN: {praefix}{len(warn)} Platte(n) unter Vorlauf — " + " · ".join(
            _platte_kurz(p)
            for p in sorted(warn, key=lambda p: (p["tage"] or 1e9, p["prozent_frei"]))
        )
    sammel = [p for p in e["platten"] if p["stand"] == "SAMMELPHASE"]
    knappste = (
        min(e["platten"], key=lambda p: p["prozent_frei"]) if e["platten"] else None
    )
    if sammel:
        punkte = min(p["punkte"] for p in sammel)
        return (
            f"SAMMELPHASE {punkte}/2 Tagespunkte — noch keine Vorlaufzeit; {praefix}"
            f"knappste: {_platte_kurz(knappste)}"
        )
    if praefix:
        return f"WARN: {praefix}{len(e['platten'])} Platte(n) gemessen, knappste {_platte_kurz(knappste)}"
    return f"OK: {len(e['platten'])} Platte(n), keine unter {WARN_TAGE} d — knappste {_platte_kurz(knappste)}"


def bericht(e: dict) -> str:
    z = [f"# Speicher-Vorlauf — {e['heute']}", ""]
    if e["blind"]:
        z.append("⛔ kein Host erreichbar — nichts gemessen.")
        return "\n".join(z)
    if e["unerreichbar"]:
        z.append(f"⚠️  nicht erreichbar: {', '.join(e['unerreichbar'])}")
        z.append("")
    z.append(
        f"{'host':<18}{'mount':<30}{'frei GB':>9}{'frei %':>8}{'Rate GB/d':>11}{'Tage':>7}  Stand"
    )
    for p in sorted(e["platten"], key=lambda p: (p["tage"] or 1e9, p["prozent_frei"])):
        rate = "" if p["rate"] is None else f"{p['rate'] / 1e9:+.1f}"
        tage = "" if p["tage"] is None else f"{p['tage']:.0f}"
        marker = "🚨 " if p["warn"] else ""
        z.append(
            f"{p['host']:<18}{p['mount']:<30}{p['frei_gb']:>9.0f}{p['prozent_frei']:>8.0f}{rate:>11}{tage:>7}  {marker}{p['stand']}"
        )
    return "\n".join(z)


# --- CLI ----------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--kurz", action="store_true")
    p.add_argument("--json", action="store_true", dest="als_json")
    p.add_argument("--journal", type=Path, default=JOURNAL_STANDARD)
    p.add_argument("--hosts", type=Path, default=HOSTS_YAML)
    p.add_argument("--heute", default=None, help="YYYY-MM-DD (Tests)")
    p.add_argument(
        "--df-fixtures", type=Path, help="Verzeichnis mit <host>.txt statt ssh"
    )
    p.add_argument("--nur", action="append", default=None, help="nur diese(n) Host(s)")
    p.add_argument(
        "--lokal", action="append", default=None, help="Host = dieser Prozess"
    )
    a = p.parse_args(argv)

    heute = (
        date.fromisoformat(a.heute) if a.heute else datetime.now(timezone.utc).date()
    )
    alle = lade_hosts(a.hosts)
    hosts = {h: z for h, z in alle.items() if not a.nur or h in a.nur}
    ausserhalb = sorted(set(alle) - set(hosts))
    if a.df_fixtures:
        messung = {
            h: (
                parse_df((a.df_fixtures / f"{h}.txt").read_text(encoding="utf-8"))
                or None
            )
            if (a.df_fixtures / f"{h}.txt").exists()
            else None
            for h in hosts
        }
    else:
        messung = messe(
            hosts,
            lokal=set(a.lokal or []),
            hops=lade_hops(a.hosts),
            shells=lade_shells(a.hosts),
        )
    journal = schreibe_journal(a.journal, lies_journal(a.journal), heute, messung)
    e = bewerte(messung, journal, heute)
    e["ausserhalb"] = ausserhalb

    if a.als_json:
        print(json.dumps(e, ensure_ascii=False, indent=2))
    elif a.kurz:
        print(kurzzeile(e))
    else:
        print(bericht(e))
    if e["blind"]:
        return 2
    if any(p["warn"] for p in e["platten"]):
        return 1
    return 3 if ausserhalb else 0


if __name__ == "__main__":
    sys.exit(main())
