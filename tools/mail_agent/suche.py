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
    echo '[{"begriff": "Vertrag"}, {"strang": "abc123"}]' | python3 suche.py --batch -

**--batch (platform#3067):** ``ablage_erledigt.py --pruefe`` rief dieses Skript
bis zu 75x je Lauf auf, jeder Aufruf bootete Django neu (2-6,6s gemessen,
2026-09-10). ``--batch DATEI|-`` reicht stattdessen EINE Liste von
Abfrage-Objekten ueber EINE SSH-Verbindung an ``mail_suche --batch`` durch, der
sie in einem einzigen Prozess abarbeitet. Kennt der entfernte dev-hub den Modus
noch nicht (vor Merge/Deploy von dev-hub#351), fallen wir laut auf
Einzelabfragen zurueck — damit ein noch nicht ausgerollter dev-hub nichts
bricht.
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

#: Multiplex-Verbindung (#3069) — ein Verzeichnis mit kurzen Socket-Pfaden
#: (`%C` ist der OpenSSH-Hash aus lokalem User, Ziel und Port, damit der Pfad
#: unter dem Limit von ~104 Zeichen bleibt) und wie lange die Verbindung nach
#: dem letzten Aufruf offen bleibt, bevor ssh sie von selbst schliesst.
CONTROL_DIR = Path.home() / ".ssh" / "control-mail-index"
CONTROL_PERSIST = int(os.environ.get("MAIL_INDEX_CONTROL_PERSIST", "120"))
#: Ein --batch-Aufruf traegt viele Abfragen in einem Prozess — grosszuegiger
#: als die 120s der Einzelabfrage, aber immer noch ein hartes Limit.
BATCH_TIMEOUT = int(os.environ.get("MAIL_INDEX_BATCH_TIMEOUT", "300"))

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

    **ControlMaster (#3069):** `ablage_erledigt.py --pruefe` ruft dieses Skript
    bis zu 75x in einem Lauf auf — gemessen 2026-09-10 kostete jeder einzelne
    Aufruf 2-6,6s, fast ausschliesslich SSH-Verbindungsaufbau plus
    Docker/Django-Start. Mit einer gemultiplexten Verbindung (`ControlMaster`)
    baut nur der erste Aufruf die Verbindung neu auf; jeder folgende Aufruf
    innerhalb von `CONTROL_PERSIST` Sekunden haengt sich an dieselbe an. Das
    Ergebnis der entfernten Abfrage aendert das nicht — nur, wie oft die
    Leitung neu aufgebaut wird.
    """
    fern = ["docker", "exec", CONTAINER, "python", "manage.py", "mail_suche", *argv]
    gequotet = " ".join(shlex.quote(teil) for teil in fern)
    return ["ssh", *_ssh_optionen(), ziel, gequotet]


def _ssh_optionen() -> list[str]:
    """SSH-Optionen fuer Einzel- UND Batch-Aufruf — ControlMaster, siehe oben (#3069)."""
    CONTROL_DIR.mkdir(parents=True, exist_ok=True)
    return [
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=15",
        "-o",
        "ControlMaster=auto",
        "-o",
        f"ControlPersist={CONTROL_PERSIST}",
        "-o",
        f"ControlPath={CONTROL_DIR}/%C",
    ]


def batch_befehl_bauen(ziel: str) -> list[str]:
    """SSH-Aufruf fuer ``--batch``: die Anfragen kommen ueber stdin, nicht als Argumente.

    ``docker exec -i`` haelt stdin des entfernten Prozesses offen — ohne ``-i``
    kommt die JSON-Liste nie beim Management-Befehl an.
    """
    fern = [
        "docker",
        "exec",
        "-i",
        CONTAINER,
        "python",
        "manage.py",
        "mail_suche",
        "--batch",
    ]
    gequotet = " ".join(shlex.quote(teil) for teil in fern)
    return ["ssh", *_ssh_optionen(), ziel, gequotet]


#: Kriterien-Feldnamen -> CLI-Flag, fuer den Einzelabfrage-Fallback von --batch
#: (dev-hub kennt den Batch-Modus noch nicht) und um Namen an einer Stelle zu halten.
_FELD_ZU_FLAG = {
    "begriff": "--begriff",
    "von": "--von",
    "an": "--an",
    "seit": "--seit",
    "bis": "--bis",
    "ordner": "--ordner",
    "strang": "--strang",
    "limit": "--limit",
    "tenant": "--tenant",
}


def _kriterien_zu_argv(anfrage: dict) -> list[str]:
    aus: list[str] = []
    for feld, flag in _FELD_ZU_FLAG.items():
        wert = anfrage.get(feld)
        if wert not in (None, "", 0):
            aus += [flag, str(wert)]
    return aus


def _unbekanntes_argument(stderr: str) -> bool:
    """Erkennt, dass der entfernte ``mail_suche`` ``--batch`` noch nicht kennt.

    Vor dem Merge/Deploy von dev-hub#351 (platform#3067) antwortet argparse auf
    der Gegenseite mit ``error: unrecognized arguments: --batch`` — genau der
    Fall, in dem wir laut auf Einzelabfragen zurueckfallen, statt zu brechen.
    """
    return "unrecognized arguments" in (stderr or "") and "--batch" in (stderr or "")


def _batch_ausfuehren(quelle: str) -> int:
    """``--batch DATEI|-``: eine JSON-Liste von Abfragen in EINER SSH-Verbindung.

    Faellt auf Einzelabfragen zurueck, wenn der entfernte dev-hub ``--batch``
    (noch) nicht kennt (platform#3067 Punkt 3) — mit einer Hinweiszeile auf
    stderr, damit der Rueckfall nicht unbemerkt bleibt.
    """
    text = (
        sys.stdin.read() if quelle == "-" else Path(quelle).read_text(encoding="utf-8")
    )
    try:
        anfragen = json.loads(text)
    except json.JSONDecodeError as e:
        sys.stderr.write(f"--batch erwartet eine JSON-Liste: {e}\n")
        return 2
    if not isinstance(anfragen, list):
        sys.stderr.write("--batch erwartet eine JSON-LISTE von Abfrage-Objekten\n")
        return 2

    ziel = ssh_ziel()
    lauf = subprocess.run(
        batch_befehl_bauen(ziel),
        input=json.dumps(anfragen, ensure_ascii=False),
        capture_output=True,
        text=True,
        timeout=BATCH_TIMEOUT,
    )
    if lauf.returncode != 0 and _unbekanntes_argument(lauf.stderr):
        sys.stderr.write(
            "Hinweis: dev-hub kennt --batch noch nicht (dev-hub#351 nicht "
            "deployed) — falle auf Einzelabfragen zurueck.\n"
        )
        return _einzeln_ausfuehren(anfragen, ziel)
    if lauf.returncode != 0:
        sys.stderr.write(lauf.stderr or "SSH-Aufruf (--batch) fehlgeschlagen\n")
        return lauf.returncode

    aus = lauf.stdout
    if (start := aus.find("[")) >= 0:
        aus = aus[start:]
    try:
        json.loads(aus)
    except ValueError:
        sys.stderr.write("Antwort ist kein gueltiges JSON:\n" + lauf.stdout)
        return 2
    sys.stdout.write(aus)
    return 0


def _einzeln_ausfuehren(anfragen: list[dict], ziel: str) -> int:
    """Fallback fuer ``--batch``: jede Abfrage einzeln, ueber dieselbe (gemultiplexten) Verbindung."""
    ergebnisse = []
    for i, anfrage in enumerate(anfragen):
        argv = [*_kriterien_zu_argv(anfrage), "--json"]
        einzel = subprocess.run(
            befehl_bauen(argv, ziel), capture_output=True, text=True, timeout=120
        )
        if einzel.returncode != 0:
            sys.stderr.write(einzel.stderr or "SSH-Aufruf fehlgeschlagen\n")
            return einzel.returncode
        roh = einzel.stdout
        if (start := roh.find("{")) >= 0:
            roh = roh[start:]
        try:
            ergebnis = json.loads(roh)
        except ValueError:
            sys.stderr.write("Antwort ist kein gueltiges JSON:\n" + einzel.stdout)
            return 2
        ergebnisse.append({"index": i, **ergebnis})
    sys.stdout.write(json.dumps(ergebnisse, ensure_ascii=False, indent=2))
    return 0


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
    p.add_argument(
        "--batch",
        metavar="DATEI",
        default=None,
        help=(
            "JSON-Liste von Abfrage-Objekten aus DATEI oder '-' (stdin) in EINER "
            "SSH-Verbindung ausfuehren, statt je Abfrage neu zu verbinden "
            "(platform#3067); schliesst die uebrigen Filter-Optionen aus"
        ),
    )
    args = p.parse_args()

    if args.batch is not None:
        return _batch_ausfuehren(args.batch)

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
