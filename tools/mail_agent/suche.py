#!/usr/bin/env python3
"""Den Mail-Index aus einer Sitzung heraus abfragen (ADR-288 §4.7).

**Wozu.** Der Index liegt in der Datenbank des dev-hub auf Produktion, die
Werkzeuge dieses Verzeichnisses laufen auf dem Entwicklungsrechner. Ohne diesen
Aufruf bleibt der Index unerreichbar, und jede Frage geht wieder ueber IMAP —
also ueber Minuten statt Millisekunden. Dieses Skript ist der duenne Weg
dorthin: es baut den Aufruf, fuehrt ihn ueber SSH aus und reicht die Antwort
durch. Es entscheidet nichts; die Logik liegt im Management-Befehl `mail_suche`.

**Der Ziel-Host kommt aus `infra/hosts.yaml`**, nicht aus einer Konstante hier.
Ein zweiter Ort fuer dieselbe Adresse driftet — genau das war der Grund fuer
Issue #998. Ueberschreibbar per ``MAIL_INDEX_SSH`` (SSH-Alias oder user@host).

**Was dieses Skript NICHT kann:** ein Original abrufen. Es liest die Projektion.
Wer die Nachricht selbst braucht, nimmt ``read_mail.py`` — so steht es in
ADR-288 §3.1 Punkt 4: „Projektion sucht, Quelle verifiziert."

Beispiele::

    python3 suche.py --nur-deckung
    python3 suche.py --von offner@hnu.de --seit 2026-06-01
    python3 suche.py --begriff Rechnung --ordner Lieferanten --json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

#: Eintrag in infra/hosts.yaml, auf dem der dev-hub-Container laeuft.
HOST_SCHLUESSEL = "hetzner-prod"
CONTAINER = os.environ.get("MAIL_INDEX_CONTAINER", "devhub_web")

#: Argumente, die unveraendert an den Management-Befehl durchgereicht werden.
DURCHREICHEN = (
    "--begriff",
    "--von",
    "--an",
    "--seit",
    "--bis",
    "--ordner",
    "--strang",
    "--limit",
    "--tenant",
)


def ssh_ziel(hosts_datei: Path | None = None) -> str:
    """SSH-Ziel aus `infra/hosts.yaml` — oder aus ``MAIL_INDEX_SSH``.

    Bewusst eine Textprüfung statt eines YAML-Parsers: dieses Skript soll ohne
    PyYAML laufen (dieselbe Begruendung wie in `indexierung.py`), und der
    gesuchte Schluessel steht eindeutig in der Datei.
    """
    if wert := os.environ.get("MAIL_INDEX_SSH"):
        return wert
    pfad = hosts_datei or (Path(__file__).resolve().parents[2] / "infra" / "hosts.yaml")
    try:
        text = pfad.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        raise SystemExit(
            f"infra/hosts.yaml nicht lesbar ({e}) — MAIL_INDEX_SSH setzen"
        ) from e
    # Der Alias steht als `ssh_alias: <name>` im Block des Hosts.
    for zeile in text.splitlines():
        if m := re.match(r"\s*ssh_alias:\s*(\S+)", zeile):
            if m.group(1) == HOST_SCHLUESSEL:
                return m.group(1)
    raise SystemExit(
        f"kein ssh_alias '{HOST_SCHLUESSEL}' in {pfad} — MAIL_INDEX_SSH setzen"
    )


def befehl_bauen(argv: list[str], ziel: str) -> list[str]:
    """SSH-Aufruf als Argumentliste, der ferne Teil einzeln gequotet.

    Die Argumentliste schuetzt nur die **lokale** Seite. `ssh` haengt alles, was
    nach dem Ziel steht, zu EINEM String zusammen und uebergibt ihn der entfernten
    Shell — die zerlegt ihn erneut an den Leerzeichen. Ein Suchbegriff aus zwei
    Woertern kam deshalb als zwei Argumente an.

    Gemessen am 2026-08-18: `--begriff "Ihre Rueckfragen"` endete in
    `manage.py mail_suche: error: unrecognized arguments: Rueckfragen`. Einwortige
    Begriffe funktionierten, weshalb der Fehler lange unsichtbar blieb.

    Der frueher hier stehende Kommentar beschrieb genau diese Gefahr — und die
    Umsetzung schuetzte trotzdem nur lokal. Der zugehoerige Test pruefte
    ebenfalls die lokale Seite und war deshalb gruen.
    """
    fern = ["docker", "exec", CONTAINER, "python", "manage.py", "mail_suche", *argv]
    gequotet = " ".join(shlex.quote(teil) for teil in fern)
    return ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", ziel, gequotet]


def _durchgereichte(args: argparse.Namespace) -> list[str]:
    aus: list[str] = []
    for flag in DURCHREICHEN:
        wert = getattr(args, flag.lstrip("-").replace("-", "_"))
        if wert not in (None, "", 0):
            aus += [flag, str(wert)]
    if args.json:
        aus.append("--json")
    if args.nur_deckung:
        aus.append("--nur-deckung")
    return aus


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--begriff", default="")
    p.add_argument("--von", default="")
    p.add_argument("--an", default="")
    p.add_argument("--seit", default="")
    p.add_argument("--bis", default="")
    p.add_argument("--ordner", default="")
    p.add_argument("--strang", default="")
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--tenant", default="")
    p.add_argument("--json", action="store_true")
    p.add_argument("--nur-deckung", action="store_true", dest="nur_deckung")
    p.add_argument(
        "--zeige-befehl",
        action="store_true",
        help="nur den Aufruf ausgeben, nichts ausfuehren",
    )
    args = p.parse_args()

    befehl = befehl_bauen(_durchgereichte(args), ssh_ziel())
    if args.zeige_befehl:
        print(" ".join(befehl))
        return 0

    lauf = subprocess.run(befehl, capture_output=True, text=True, timeout=120)
    if lauf.returncode != 0:
        # Die Fehlermeldung des Befehls ist die Diagnose — nicht verschlucken.
        sys.stderr.write(lauf.stderr or "SSH-Aufruf fehlgeschlagen\n")
        return lauf.returncode

    aus = lauf.stdout
    if args.json:
        # Django gibt vor der eigentlichen Ausgabe ggf. Hinweiszeilen aus; die
        # JSON-Antwort beginnt am ersten '{'. Ohne das scheitert jeder Aufrufer,
        # der die Ausgabe parst — und zwar an einer Stelle, die nach unserem
        # Fehler aussieht, obwohl sie es nicht ist.
        if (start := aus.find("{")) >= 0:
            aus = aus[start:]
        try:
            json.loads(aus)
        except ValueError:
            sys.stderr.write("Antwort ist kein gueltiges JSON:\n" + lauf.stdout)
            return 2
    sys.stdout.write(aus)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
