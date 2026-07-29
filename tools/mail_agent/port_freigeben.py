#!/usr/bin/env python3
"""Einen verwaisten eigenen Dienst vom Port lösen — und NUR den eigenen.

Warum es das gibt: Am 2026-07-29 hielt ein von Hand gestarteter
`mail_link_server.py` den Port 8787 weiter, nachdem die systemd-Unit übernehmen
sollte. Die Unit scheiterte fünfmal an `OSError: [Errno 98] Address already in
use`, blieb auf `activating` stehen — und der Waisenprozess beantwortete die
Anfragen weiter mit **altem Code**. Aufgefallen ist das nur, weil die Routen
nach dem Neustart nachgemessen wurden. `Restart=on-failure` hilft dagegen nicht:
der Port wird ja nie frei.

Gedacht als `ExecStartPre=` der Unit.

Die harte Grenze: Beendet wird **ausschließlich** ein Prozess, der

  1. dem aufrufenden Benutzer gehört (gleiche UID) **und**
  2. in seiner Kommandozeile den erwarteten Marker trägt (`mail_link_server.py`).

Trifft eines davon nicht zu, wird **nichts** beendet und der Aufruf schlägt mit
einer Erklärung fehl. Ein fremder Dienst auf dem Port ist ein Befund, den ein
Mensch ansehen muss — kein Hindernis, das ein Start-Skript wegräumt.

Ohne root: die Zuordnung Port → Prozess läuft über `/proc/net/tcp` und die
Datei-Deskriptoren unter `/proc/<pid>/fd`. Beides ist für **eigene** Prozesse
lesbar — genau die Menge, die hier überhaupt in Frage kommt.
"""

from __future__ import annotations

import argparse
import errno
import os
import signal
import sys
import time
from pathlib import Path

#: Nur ein Prozess mit diesem Marker in der Kommandozeile gilt als „eigene Instanz".
MARKER = "mail_link_server.py"

#: `st`-Spalte in /proc/net/tcp für LISTEN.
_LISTEN = "0A"


def hex_zu_port(local_address: str) -> int:
    """'0100007F:2CAA' → 11434. Die Adresse selbst interessiert hier nicht."""
    return int(local_address.rsplit(":", 1)[1], 16)


def lauschende_inodes(port: int, proc_root: Path = Path("/proc")) -> set[str]:
    """Socket-Inodes, die auf `port` lauschen (IPv4 und IPv6)."""
    inodes: set[str] = set()
    for name in ("net/tcp", "net/tcp6"):
        datei = proc_root / name
        try:
            zeilen = datei.read_text().splitlines()[1:]
        except OSError:
            continue
        for zeile in zeilen:
            felder = zeile.split()
            if len(felder) < 10 or felder[3] != _LISTEN:
                continue
            try:
                if hex_zu_port(felder[1]) == port:
                    inodes.add(felder[9])
            except (ValueError, IndexError):
                continue
    return inodes


def pids_zu_inodes(inodes: set[str], proc_root: Path = Path("/proc")) -> set[int]:
    """Prozesse, die einen dieser Sockets offen haben. Fremde Prozesse fehlen
    hier mangels Leserecht — das ist gewollt, sie sollen ohnehin unangetastet
    bleiben."""
    gesucht = {f"socket:[{inode}]" for inode in inodes}
    treffer: set[int] = set()
    for eintrag in proc_root.iterdir():
        if not eintrag.name.isdigit():
            continue
        fd_dir = eintrag / "fd"
        try:
            deskriptoren = list(fd_dir.iterdir())
        except OSError:
            continue  # fremder Prozess oder gerade beendet
        for fd in deskriptoren:
            try:
                if os.readlink(fd) in gesucht:
                    treffer.add(int(eintrag.name))
                    break
            except OSError:
                continue
    return treffer


def ist_eigene_instanz(
    pid: int, marker: str = MARKER, proc_root: Path = Path("/proc")
) -> bool:
    """Gehört der Prozess uns UND ist es unser Dienst? Beides muss stimmen."""
    verzeichnis = proc_root / str(pid)
    try:
        if verzeichnis.stat().st_uid != os.getuid():
            return False
        kommandozeile = (
            (verzeichnis / "cmdline").read_bytes().decode("utf-8", "replace")
        )
    except OSError:
        return False
    return marker in kommandozeile


def beschreibe(pid: int, proc_root: Path = Path("/proc")) -> str:
    try:
        roh = (proc_root / str(pid) / "cmdline").read_bytes()
        return " ".join(roh.decode("utf-8", "replace").split("\x00")).strip() or "?"
    except OSError:
        return "?"


def freigeben(
    port: int,
    marker: str = MARKER,
    proc_root: Path = Path("/proc"),
    gnadenfrist: float = 3.0,
    toeten=os.kill,
) -> tuple[int, str]:
    """(Exit-Code, Meldung). 0 = Port frei oder freigeräumt, 1 = fremde Belegung."""
    inodes = lauschende_inodes(port, proc_root)
    if not inodes:
        return 0, f"Port {port} ist frei."

    pids = pids_zu_inodes(inodes, proc_root)
    if not pids:
        return 1, (
            f"Port {port} ist belegt, der Prozess gehört aber nicht diesem Benutzer "
            "(nicht lesbar). Nichts beendet — bitte von Hand ansehen."
        )

    fremde = [p for p in pids if not ist_eigene_instanz(p, marker, proc_root)]
    if fremde:
        liste = ", ".join(f"PID {p} ({beschreibe(p, proc_root)[:60]})" for p in fremde)
        return 1, (
            f"Port {port} ist von einem fremden Prozess belegt: {liste}. "
            "Nichts beendet — das ist ein Befund, kein Hindernis."
        )

    beendet = []
    for pid in sorted(pids):
        try:
            toeten(pid, signal.SIGTERM)
            beendet.append(pid)
        except OSError as fehler:
            if fehler.errno != errno.ESRCH:
                return 1, f"PID {pid} ließ sich nicht beenden: {fehler}"

    ende = time.monotonic() + gnadenfrist
    while time.monotonic() < ende:
        if not lauschende_inodes(port, proc_root):
            break
        time.sleep(0.2)
    else:
        for pid in beendet:
            try:
                toeten(pid, signal.SIGKILL)
            except OSError:
                pass

    return 0, (
        f"Verwaiste eigene Instanz vom Port {port} gelöst: "
        f"{', '.join(f'PID {p}' for p in beendet)}."
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument(
        "--marker",
        default=MARKER,
        help="Erkennungsmerkmal der eigenen Instanz in der Kommandozeile",
    )
    ap.add_argument(
        "--nur-pruefen",
        action="store_true",
        help="nur melden, wer lauscht — nichts beenden",
    )
    args = ap.parse_args()

    if args.nur_pruefen:
        inodes = lauschende_inodes(args.port)
        pids = pids_zu_inodes(inodes) if inodes else set()
        if not inodes:
            print(f"Port {args.port} ist frei.")
        elif not pids:
            print(f"Port {args.port} belegt, Prozess nicht lesbar (fremder Benutzer).")
        else:
            for pid in sorted(pids):
                eigen = (
                    "eigene Instanz"
                    if ist_eigene_instanz(pid, args.marker)
                    else "FREMD"
                )
                print(f"PID {pid} [{eigen}] {beschreibe(pid)[:70]}")
        return

    code, meldung = freigeben(args.port, args.marker)
    print(meldung, file=sys.stderr if code else sys.stdout)
    sys.exit(code)


if __name__ == "__main__":
    main()
