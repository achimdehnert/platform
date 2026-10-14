#!/usr/bin/env python3
"""Ressourcen-Lease: ein externes Schreibziel gehoert genau EINER Claude-Sitzung.

Bibliothek fuer den Hook `block_fremde_ressource.py` und Kommandozeile fuer
Sitzung und Owner. Realfall 2026-10-14 (platform#3549-Folge): zwei Sitzungen im
selben Repo arbeiteten parallel auf demselben Buchhaltungs-Mandanten und
schrieben ins selbe Board. Eine bereitete eine Zahlung per Ueberweisungsdatei
vor, die andere legte dieselbe Zahlung im Buchhaltungssystem an. Das kurze
Owner-Wort „erledigt" landete in der falschen Sitzung und wurde dort als die
andere Zahlung verbucht. Die Leases aus `repo-session.sh` decken nur Worktrees,
fuer Ziele ausserhalb von Git gab es nichts.

Modell:
  * Eine Lease-Datei je Ressource unter `~/.claude/leases/ressourcen/`.
  * Inhaber ist die `claude_session` (Hook-Eingabe `session_id`, in der Shell
    `$CLAUDE_CODE_SESSION_ID`).
  * Gueltig, solange der Prozess der Inhaber-Sitzung lebt (`~/.claude/sessions/
    <pid>.json` nennt `sessionId`, `os.kill(pid, 0)` prueft). Kein Ablaufdatum:
    eine lange Sitzung behaelt ihr Ziel, eine beendete gibt es von selbst frei.
  * Beanspruchen, Pruefen und Freigeben laufen unter `flock` auf einer
    Sperrdatei je Ressource. Zwei Sitzungen koennen dieselbe verwaiste Lease
    nicht beide uebernehmen.
  * Jedes Ereignis landet in `journal.jsonl` daneben (Messpunkt fuer das Gate).

Kommandozeile:
  ressourcen_lease.py status                       # alle Leases, Inhaber, lebt?
  ressourcen_lease.py nehmen <ressource> [--zweck T]
  ressourcen_lease.py freigeben <ressource>        # nur die eigene oder verwaiste
  ressourcen_lease.py freigeben <ressource> --erzwingen   # Owner-Recht, s. Hook
  ressourcen_lease.py aufraeumen                   # verwaiste Leases entfernen

Testbarkeits-Naht: `RESSOURCEN_LEASE_DIR`, `CLAUDE_SESSIONS_DIR` und
`RESSOURCEN_LEASE_TESTPAUSE` (Sekunden zwischen Lesen und Schreiben, nur Drill).
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

#: Ergebnis-Arten von `beanspruchen`.
FREI_GENOMMEN = "frei_genommen"
EIGEN = "eigen"
UEBERNOMMEN = "uebernommen"
FREMD = "fremd"

_UNSICHER = re.compile(r"[^A-Za-z0-9_.-]")


def lease_dir() -> Path:
    return Path(
        os.environ.get("RESSOURCEN_LEASE_DIR", "~/.claude/leases/ressourcen")
    ).expanduser()


def sessions_dir() -> Path:
    return Path(
        os.environ.get("CLAUDE_SESSIONS_DIR", "~/.claude/sessions")
    ).expanduser()


def _jetzt() -> str:
    # Ortszeit mit Versatz: die Zeile liest der Owner in der Sperrmeldung.
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _datei(ressource: str) -> Path:
    return lease_dir() / f"{_UNSICHER.sub('_', ressource)}.json"


def sitzung_info(session_id: str) -> dict | None:
    """Laufende Sitzung zu `session_id` oder None, wenn kein lebender Prozess sie traegt."""
    if not session_id:
        return None
    try:
        kandidaten = list(sessions_dir().glob("*.json"))
    except OSError:
        return None
    for datei in kandidaten:
        try:
            daten = json.loads(datei.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if daten.get("sessionId") != session_id:
            continue
        pid = daten.get("pid")
        if not isinstance(pid, int):
            continue
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            continue
        except PermissionError:
            pass  # Prozess existiert, gehoert nur einem anderen Nutzer
        return {
            "pid": pid,
            "name": daten.get("name") or "",
            "cwd": daten.get("cwd") or "",
        }
    return None


def lesen(ressource: str) -> dict | None:
    try:
        return json.loads(_datei(ressource).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, ValueError):
        # Unlesbar heisst NICHT frei: lieber sperren als zwei Schreiber zulassen.
        return {"claude_session": "<unlesbar>", "ressource": ressource}


def _journal(ereignis: str, ressource: str, session_id: str, **mehr: object) -> None:
    zeile = {
        "zeit": _jetzt(),
        "ereignis": ereignis,
        "ressource": ressource,
        "session": session_id[:64],
        **mehr,
    }
    try:
        with (lease_dir() / "journal.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(zeile, ensure_ascii=False) + "\n")
    except OSError:
        pass  # Messpunkt, nie Grund fuer einen Fehlschlag


class _Sperre:
    """Exklusive flock-Sperre je Ressource fuer Lesen-Entscheiden-Schreiben."""

    def __init__(self, ressource: str) -> None:
        self.pfad = _datei(ressource).with_suffix(".lock")

    def __enter__(self) -> "_Sperre":
        self.pfad.parent.mkdir(parents=True, exist_ok=True)
        self._fd = os.open(self.pfad, os.O_CREAT | os.O_RDWR, 0o600)
        fcntl.flock(self._fd, fcntl.LOCK_EX)
        return self

    def __exit__(self, *_: object) -> None:
        fcntl.flock(self._fd, fcntl.LOCK_UN)
        os.close(self._fd)


def _schreiben(ressource: str, lease: dict) -> None:
    ziel = _datei(ressource)
    tmp = ziel.with_suffix(f".tmp{os.getpid()}")
    tmp.write_text(
        json.dumps(lease, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    os.replace(tmp, ziel)


@dataclass
class Ergebnis:
    erlaubt: bool
    art: str
    lease: dict
    vorher: dict | None = None


def beanspruchen(ressource: str, session_id: str, zweck: str = "") -> Ergebnis:
    """Lease fuer `session_id` sichern, sofern frei, eigen oder verwaist."""
    with _Sperre(ressource):
        alt = lesen(ressource)
        if alt and alt.get("claude_session") == session_id:
            return Ergebnis(True, EIGEN, alt)
        if alt and sitzung_info(str(alt.get("claude_session") or "")) is not None:
            _journal(
                "verweigert", ressource, session_id, inhaber=alt.get("claude_session")
            )
            return Ergebnis(False, FREMD, alt)
        if alt and alt.get("claude_session") == "<unlesbar>":
            _journal("verweigert", ressource, session_id, inhaber="<unlesbar>")
            return Ergebnis(False, FREMD, alt)
        # Testbarkeits-Naht: weitet das Fenster zwischen Lesen und Schreiben, damit der
        # Wettlauf-Drill ohne flock ROT wird (Mutationsprobe, s. Gate-Eintrag).
        time.sleep(float(os.environ.get("RESSOURCEN_LEASE_TESTPAUSE") or 0))
        info = sitzung_info(session_id) or {}
        neu = {
            "ressource": ressource,
            "claude_session": session_id,
            "name": info.get("name", ""),
            "pid": info.get("pid"),
            "seit": _jetzt(),
            "zweck": zweck[:200],
        }
        _schreiben(ressource, neu)
        art = UEBERNOMMEN if alt else FREI_GENOMMEN
        _journal(
            art,
            ressource,
            session_id,
            vorher=(alt or {}).get("claude_session"),
            zweck=zweck[:200],
        )
        return Ergebnis(True, art, neu, alt)


def freigeben(
    ressource: str, session_id: str, erzwingen: bool = False
) -> tuple[bool, str]:
    with _Sperre(ressource):
        alt = lesen(ressource)
        if alt is None:
            return True, f"{ressource}: keine Lease"
        inhaber = str(alt.get("claude_session") or "")
        lebt = sitzung_info(inhaber) is not None
        if inhaber != session_id and lebt and not erzwingen:
            return False, (
                f"{ressource}: gehoert der laufenden Sitzung "
                f"{alt.get('name') or '?'} ({inhaber[:8]}), nicht freigegeben"
            )
        _datei(ressource).unlink(missing_ok=True)
        _journal(
            "erzwungen"
            if (erzwingen and inhaber != session_id and lebt)
            else "freigegeben",
            ressource,
            session_id,
            inhaber=inhaber,
        )
        return (
            True,
            f"{ressource}: freigegeben (Inhaber war {alt.get('name') or inhaber[:8]})",
        )


def alle() -> list[dict]:
    try:
        dateien = sorted(lease_dir().glob("*.json"))
    except OSError:
        return []
    ergebnis = []
    for datei in dateien:
        try:
            lease = json.loads(datei.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            lease = {"ressource": datei.stem, "claude_session": "<unlesbar>"}
        lease["lebt"] = sitzung_info(str(lease.get("claude_session") or "")) is not None
        ergebnis.append(lease)
    return ergebnis


def beschreibung(lease: dict) -> str:
    name = lease.get("name") or "?"
    sid = str(lease.get("claude_session") or "")[:8]
    return f"Sitzung {name} ({sid}…), seit {lease.get('seit', '?')}, Zweck: {lease.get('zweck') or '-'}"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    n = sub.add_parser("nehmen")
    n.add_argument("ressource")
    n.add_argument("--zweck", default="manuell")
    f = sub.add_parser("freigeben")
    f.add_argument("ressource")
    f.add_argument("--erzwingen", action="store_true")
    sub.add_parser("aufraeumen")
    args = p.parse_args(argv)
    session_id = os.environ.get("CLAUDE_CODE_SESSION_ID", "")

    if args.cmd == "status":
        leases = alle()
        if not leases:
            print("keine Ressourcen-Leases")
        for lease in leases:
            zustand = "lebt" if lease["lebt"] else "VERWAIST"
            eigen = (
                " (diese Sitzung)" if lease.get("claude_session") == session_id else ""
            )
            print(f"{lease.get('ressource')}: {zustand}{eigen} — {beschreibung(lease)}")
        return 0
    if args.cmd == "aufraeumen":
        for lease in alle():
            if not lease["lebt"]:
                _, text = freigeben(str(lease.get("ressource")), session_id)
                print(text)
        return 0
    if not session_id:
        print("CLAUDE_CODE_SESSION_ID fehlt — Sitzung unbekannt", file=sys.stderr)
        return 2
    if args.cmd == "nehmen":
        erg = beanspruchen(args.ressource, session_id, args.zweck)
        if not erg.erlaubt:
            print(
                f"{args.ressource}: belegt — {beschreibung(erg.lease)}", file=sys.stderr
            )
            return 1
        print(f"{args.ressource}: {erg.art}")
        return 0
    ok, text = freigeben(args.ressource, session_id, args.erzwingen)
    print(text, file=sys.stdout if ok else sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
