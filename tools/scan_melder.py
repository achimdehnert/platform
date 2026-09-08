#!/usr/bin/env python3
"""scan_melder.py — ein Scan, der nicht ankommt, sieht aus wie ein Scan, den es nie gab.

## Anlass (2026-09-08, doc-hub#3)

Der ScanSnap iX1600 schreibt per SFTP direkt in den Paperless-Consume-Baum
(`Match User scansnap`, home = `/opt/paperless-consume`, `ForceCommand internal-sftp`).
Am 2026-09-07 um 10:19 landete dort `achim/07092026101932.pdf` — eine abgeschnittene
PDF ohne Trailer. Paperless brach die Aufnahme ab (`InputFileError`), **liess die Datei
liegen** und meldete nach aussen nichts. Der Scan davor (10:10) ging durch. Gemerkt hat
es 23 Stunden lang niemand.

Das ist die gefaehrliche Sorte Fehler: sporadisch, still, und fuer den Menschen am
Geraet nicht von "hab ich wohl doch nicht gescannt" zu unterscheiden.

## Was gemessen wird — und warum ohne Datenbank

Paperless entfernt eine Datei aus dem Consume-Baum, sobald sie aufgenommen ist.
**Eine Datei, die noch da liegt, ist nicht aufgenommen** — das ist das ganze Signal,
und es braucht weder Container noch Datenbank. Der Melder misst deshalb nur das
Dateisystem und bleibt auch dann aussagefaehig, wenn der Stack gerade steht.

Die Umkehrung gilt NICHT: eine verschwundene Datei ist nicht automatisch ein
Dokument (jemand kann sie von Hand geloescht haben). Der Melder behauptet darum
nur die eine Richtung, die er wirklich belegt.

## Warum eine Altersschwelle und keine blosse Anwesenheit

Waehrend der SFTP-Uebertragung liegt die Datei ebenfalls im Ordner. Ein Melder ohne
Schwelle wuerde jeden laufenden Scan als Befund melden — und damit binnen einer Woche
ignoriert. Paperless nimmt normal in 10-30 s auf (`PAPERLESS_CONSUMER_POLLING_INTERVAL=10`);
30 Minuten Schwelle ist reichlich Luft und trotzdem am selben Tag ein Befund.

## Warum die Ignoranz-Liste aus dem Container kommt

`PAPERLESS_CONSUMER_IGNORE_DIRS` steht auf `["schleuse", ".thumbs"]`, und in
`schleuse/` liegen absichtlich Dateien, die nie aufgenommen werden sollen (Uebergabe
zur/von der Box). Waeren sie hier hartkodiert, ginge die Liste beim naechsten
Compose-Edit auseinander und der Melder meldete auf Dauer denselben Fehlalarm —
die haeufigste Todesursache von Meldern. Er liest sie deshalb aus dem laufenden
Container. Geht das nicht, faellt er auf `IGNORE_DIRS_FALLBACK` zurueck und **sagt
das im Bericht**, statt so zu tun, als haette er gemessen.

## Warum jede haengende Datei genau einmal alarmiert

Der Workflow laeuft stuendlich. Ein taeglicher Alarm ueber dieselbe Datei waere
Rauschen (dieselbe Lehre wie bei `backup-deckung.yml` Exit 3). Statt einen Zustand
mitzuschleppen — der auf einem Runner ohnehin nicht verlaesslich ueberlebt — meldet
`--neu-seit MINUTEN` nur Dateien, deren Alter im **letzten Laufabstand** die Schwelle
ueberschritten hat. Jede Datei faellt so durch genau ein Fenster. Der Lauf selbst
bleibt rot, solange irgendetwas haengt: kein Dauerlaerm, aber auch kein Gruen ueber
einem liegengebliebenen Dokument.

## Datenschutz: die Kurzzeile nennt keine Namen

`--kurz` gibt nur Zahlen aus. Ordner- und Dateinamen stehen ausschliesslich im
Vollbericht, denn dieses Repo ist oeffentlich — und damit sind es auch die
Actions-Logs. Der Workflow ruft nur `--kurz` auf; Details holt sich der Owner lokal.

Exit-Codes
----------
0 = nichts haengt · 1 = mindestens eine Datei haengt · 2 = blind (Wurzel nicht lesbar)

Usage
-----
    python3 tools/scan_melder.py                      # Vollbericht (auf prod)
    python3 tools/scan_melder.py --kurz               # eine Zeile, ohne Namen
    python3 tools/scan_melder.py --ssh hetzner-prod   # von der Dev-Maschine
    python3 tools/scan_melder.py --neu-seit 60        # nur frisch haengende melden
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

WURZEL = "/opt/paperless-consume"
CONTAINER = "iil_dochub_web"
SCHWELLE_MIN = 30

# Nur Rueckfallposition, wenn der Container nicht antwortet — die Wahrheit steht
# in der Container-Env (siehe Modul-Docstring).
IGNORE_DIRS_FALLBACK = ["schleuse", ".thumbs"]


def _lauf(argv: list[str], ssh: str | None) -> tuple[int, str]:
    """Kommando lokal oder ueber ssh ausfuehren. Gibt (rc, stdout) zurueck."""
    if ssh:
        argv = [
            "ssh",
            "-o",
            "ConnectTimeout=8",
            ssh,
            " ".join(shlex.quote(a) for a in argv),
        ]
    p = subprocess.run(argv, capture_output=True, text=True, timeout=120)
    return p.returncode, p.stdout


# --- reine Auswertung (testbar ohne Host) ----------------------------------


def ignorierte_ordner(env_text: str) -> tuple[list[str], bool]:
    """`PAPERLESS_CONSUMER_IGNORE_DIRS` aus einer `docker exec env`-Ausgabe lesen.

    Zweiter Rueckgabewert sagt, ob die Liste wirklich gemessen wurde. Ein
    Fehlschlag darf nicht wie ein Messergebnis aussehen.
    """
    m = re.search(r"^PAPERLESS_CONSUMER_IGNORE_DIRS=(.*)$", env_text, re.MULTILINE)
    if not m:
        return list(IGNORE_DIRS_FALLBACK), False
    try:
        werte = json.loads(m.group(1).strip())
    except json.JSONDecodeError:
        return list(IGNORE_DIRS_FALLBACK), False
    if not isinstance(werte, list):
        return list(IGNORE_DIRS_FALLBACK), False
    return [str(w) for w in werte], True


def _ignoriert(relpfad: str, ignore_dirs: list[str]) -> bool:
    teile = Path(relpfad).parts
    ordner = set(teile[:-1])
    if ordner & set(ignore_dirs):
        return True
    # Punktdateien legt kein Scanner ab; sie stammen von Editoren und Sync-Werkzeugen.
    return any(t.startswith(".") for t in teile)


def haengende(
    dateien: list[dict],
    *,
    jetzt: float,
    schwelle_min: int = SCHWELLE_MIN,
    ignore_dirs: list[str] | None = None,
    neu_seit_min: int | None = None,
) -> list[dict]:
    """Dateien, die laenger als die Schwelle im Consume-Baum liegen.

    `neu_seit_min` schneidet oben ab: nur was die Schwelle im letzten Laufabstand
    ueberschritten hat. Ohne den Parameter kommt alles Haengende zurueck.
    """
    ignore_dirs = IGNORE_DIRS_FALLBACK if ignore_dirs is None else ignore_dirs
    unten = schwelle_min * 60
    oben = (schwelle_min + neu_seit_min) * 60 if neu_seit_min is not None else None
    treffer = []
    for d in dateien:
        if _ignoriert(d["pfad"], ignore_dirs):
            continue
        alter = jetzt - d["mtime"]
        if alter < unten:
            continue
        if oben is not None and alter >= oben:
            continue
        treffer.append({**d, "alter_s": alter})
    return sorted(treffer, key=lambda t: -t["alter_s"])


def _stunden(sekunden: float) -> str:
    return f"{sekunden / 3600:.1f} h"


def kurzzeile(treffer: list[dict], *, geprueft: int, gemessene_ignoranz: bool) -> str:
    """Eine Zeile ohne Ordner- und Dateinamen (Repo und Actions-Log sind oeffentlich)."""
    nachsatz = "" if gemessene_ignoranz else " [Ignoranz-Liste nicht gemessen]"
    if not treffer:
        return f"scan-melder: 0 haengende Dateien ({geprueft} geprueft){nachsatz}"
    return (
        f"scan-melder: {len(treffer)} haengende Datei(en), aeltester Eingang vor "
        f"{_stunden(treffer[0]['alter_s'])} ({geprueft} geprueft) — "
        f"Details lokal: python3 tools/scan_melder.py --ssh hetzner-prod{nachsatz}"
    )


def bericht(treffer: list[dict], *, geprueft: int, gemessene_ignoranz: bool) -> str:
    zeilen = [
        kurzzeile(treffer, geprueft=geprueft, gemessene_ignoranz=gemessene_ignoranz)
    ]
    for t in treffer:
        zeilen.append(
            f"  {_stunden(t['alter_s']):>8}  {t['groesse']:>10} B  {t['pfad']}"
        )
    if treffer:
        zeilen.append("")
        zeilen.append(
            f'  Ursache je Datei: ssh hetzner-prod "docker logs {CONTAINER} --since 48h'
            ' 2>&1 | grep -i <dateiname>"'
        )
    return "\n".join(zeilen)


# --- Messung ---------------------------------------------------------------


def sammle(wurzel: str, ssh: str | None) -> tuple[list[dict], bool]:
    """Alle Dateien unter der Wurzel mit mtime und Groesse. Zweiter Wert: lesbar?"""
    rc, out = _lauf(["find", wurzel, "-type", "f", "-printf", "%T@\\t%s\\t%P\\n"], ssh)
    if rc != 0:
        return [], False
    dateien = []
    for zeile in out.splitlines():
        felder = zeile.split("\t", 2)
        if len(felder) != 3:
            continue
        dateien.append(
            {"mtime": float(felder[0]), "groesse": int(felder[1]), "pfad": felder[2]}
        )
    return dateien, True


def lies_ignoranz(ssh: str | None) -> tuple[list[str], bool]:
    rc, out = _lauf(["docker", "exec", CONTAINER, "env"], ssh)
    if rc != 0:
        return list(IGNORE_DIRS_FALLBACK), False
    return ignorierte_ordner(out)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--wurzel", default=WURZEL)
    p.add_argument(
        "--ssh", default=None, help="Host-Alias, wenn nicht auf prod gelaufen wird"
    )
    p.add_argument(
        "--schwelle", type=int, default=SCHWELLE_MIN, help="Minuten (Default 30)"
    )
    p.add_argument(
        "--neu-seit",
        type=int,
        default=None,
        metavar="MINUTEN",
        help="nur Dateien melden, die die Schwelle im letzten Laufabstand ueberschritten haben",
    )
    p.add_argument("--kurz", action="store_true")
    a = p.parse_args(argv)

    dateien, lesbar = sammle(a.wurzel, a.ssh)
    if not lesbar:
        print(
            f"scan-melder: {a.wurzel} nicht lesbar — blind, nicht gruen",
            file=sys.stderr,
        )
        return 2

    ignore_dirs, gemessen = lies_ignoranz(a.ssh)
    treffer = haengende(
        dateien,
        jetzt=time.time(),
        schwelle_min=a.schwelle,
        ignore_dirs=ignore_dirs,
        neu_seit_min=a.neu_seit,
    )
    geprueft = sum(1 for d in dateien if not _ignoriert(d["pfad"], ignore_dirs))
    if a.kurz:
        print(kurzzeile(treffer, geprueft=geprueft, gemessene_ignoranz=gemessen))
    else:
        print(bericht(treffer, geprueft=geprueft, gemessene_ignoranz=gemessen))
    return 1 if treffer else 0


if __name__ == "__main__":
    raise SystemExit(main())
