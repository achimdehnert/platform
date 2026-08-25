#!/usr/bin/env python3
"""Jeden Lotsen-Link vor dem Absenden gegen den echten Dienst pruefen.

Warum es das gibt: Am 2026-08-25 stand in einer Antwort an den Owner der Link
``https://todo.iil.pet/m/hnu/23630`` auf einen frisch abgelegten Entwurf. Er war
getippt, nicht erzeugt, und er war gleich dreifach falsch:

1. **Falscher Hostname.** ``/m/`` rendert Mail-Koerper und liegt auf
   ``mail.iil.pet`` (Port 8787). ``todo.iil.pet`` ist die Arbeitsliste auf Port
   8789 — sie liest nur das Ledger und spricht kein IMAP. Der Host stammte aus
   den *Vorgangs*-Links derselben Antwort, wo er richtig ist.
2. **Fehlende Ordnerangabe.** ``/m/<konto>/<uid>`` traf einen Dienstprozess, der
   am 20.08. gestartet war; die Ordnersuche kam am 21.08. dazu (61f4480d). Der
   laufende Code loeste UIDs weiter nur gegen INBOX auf — eine Entwurfs-UID gab
   dort 404.
3. **Nie geprueft.** Der Check von aussen (``https://…``) beantwortet die Frage
   nicht: davor steht Cloudflare Access und liefert 302, egal ob die Route
   existiert. Auf dem Loopback gibt es kein Access — und genau dort war die
   Antwort in einer Sekunde zu haben.

Daraus die Regel, die dieses Werkzeug durchsetzt: **ein Lotsen-Link wird nie
getippt, sondern erzeugt — und vor dem Absenden auf dem Loopback geprueft.**
Der Hostname wird dabei nicht geraten, sondern aus der cloudflared-Ingress-Liste
in den Port uebersetzt, der ihn wirklich bedient.

Aufrufe::

    python3 tools/mail_agent/link_pruefen.py https://mail.iil.pet/m/hnu/entwuerfe/23630
    board.py --render | python3 tools/mail_agent/link_pruefen.py --stdin
    python3 tools/mail_agent/link_pruefen.py --datei antwort.md

Exit 0 nur, wenn JEDER geprueffaehige Link 200 liefert.
"""

from __future__ import annotations

import argparse
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

INGRESS_GLOB = "*.yml"
INGRESS_DIRS = (Path.home() / ".cloudflared", Path("/etc/cloudflared"))
TIMEOUT = 25

_MD_LINK = re.compile(r"\]\((https?://[^\s)]+)\)")
_CODE = re.compile(r"`[^`]*`")
_URL = re.compile(r"https?://[^\s<>\"')\]]+")
_HOST = re.compile(r"^\s*-\s*hostname:\s*(\S+)\s*$")
_SVC = re.compile(r"^\s*service:\s*(http://127\.0\.0\.1:(\d+))\s*$")


def ingress_karte(dirs=INGRESS_DIRS) -> dict[str, str]:
    """hostname -> Loopback-Basis, gelesen aus den cloudflared-Configs.

    Bewusst zeilenweise statt per YAML-Parser: die Dateien sind flach, und das
    Werkzeug soll ohne Abhaengigkeit laufen. Ein ``hostname`` gilt, bis der
    naechste kommt; nur Loopback-Services werden uebernommen, denn nur die sind
    von hier aus ohne Access erreichbar.
    """
    karte: dict[str, str] = {}
    for d in dirs:
        if not d.is_dir():
            continue
        for pfad in sorted(d.glob(INGRESS_GLOB)):
            offen: str | None = None
            try:
                zeilen = pfad.read_text(encoding="utf-8").splitlines()
            except OSError:
                continue
            for zeile in zeilen:
                if (m := _HOST.match(zeile)) is not None:
                    offen = m.group(1)
                elif (m := _SVC.match(zeile)) is not None and offen:
                    karte.setdefault(offen, m.group(1))
                    offen = None
    return karte


def pruefe(url: str, karte: dict[str, str]) -> tuple[str, str]:
    """(status, hinweis) fuer EINEN Link. status: ok | fehler | uebersprungen."""
    teile = urlsplit(url)
    basis = karte.get(teile.netloc)
    if basis is None:
        return "uebersprungen", f"kein Loopback-Dienst fuer '{teile.netloc}' in der Ingress-Liste"
    pfad = teile.path or "/"
    if teile.query:
        pfad += "?" + teile.query
    try:
        with urllib.request.urlopen(basis + pfad, timeout=TIMEOUT) as antwort:
            code = antwort.status
    except urllib.error.HTTPError as exc:
        code = exc.code
    except OSError as exc:
        return "fehler", f"Dienst auf {basis} nicht erreichbar: {exc}"
    if code == 200:
        return "ok", f"{basis}{pfad} → 200"
    return "fehler", f"{basis}{pfad} → {code}"


def urls_aus(text: str) -> list[str]:
    """Links aus Fliesstext holen, ohne die zwei bekannten Fehlalarme.

    Beide sind am 2026-08-25 am gerenderten Board gemessen worden:

    * ``[Termin 28.08.](https://…/t/Termin%2028.08.)`` — der thread_key endet auf
      einen Punkt. Wer am Ende blind ``.`` abschneidet, prueft eine andere URL,
      als im Text steht, und meldet 404 fuer einen gesunden Link. Darum wird die
      Markdown-Form ``](…)`` zuerst gelesen: dort begrenzt die Klammer, nicht
      die Heuristik.
    * ``/m/<konto>/<uid>`` in der Erklaerprosa des Boards — eine Schablone in
      Backticks, kein Link. Code-Spans fliegen deshalb vor der Suche raus.

    Ein Melder, der bei gesundem Bestand anschlaegt, wird abgeschaltet statt
    gelesen; diese beiden Faelle sind der Preis dafuer, dass er ernst bleibt.
    """
    gesehen: list[str] = []

    def merke(url: str) -> None:
        # Eine URL mit spitzen Klammern ist eine Schablone, keine Adresse:
        # `/i/<kurz-id>` in der Board-Prosa ist kein toter Link, sondern ein
        # Platzhalter. Am 2026-08-25 der letzte verbliebene Fehlalarm.
        if url and "<" not in url and ">" not in url and url not in gesehen:
            gesehen.append(url)

    for treffer in _MD_LINK.findall(text):
        merke(treffer)
    rest = _MD_LINK.sub(" ", text)
    rest = _CODE.sub(" ", rest)
    for treffer in _URL.findall(rest):
        merke(treffer.rstrip(".,;:)"))
    return gesehen


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("urls", nargs="*", help="zu pruefende Links")
    p.add_argument("--stdin", action="store_true", help="Links aus stdin herauslesen")
    p.add_argument("--datei", type=Path, help="Links aus einer Datei herauslesen")
    p.add_argument(
        "--streng",
        action="store_true",
        help="uebersprungene Links (fremder Host) als Fehler werten",
    )
    args = p.parse_args()

    text = ""
    if args.stdin:
        text += sys.stdin.read()
    if args.datei:
        text += args.datei.read_text(encoding="utf-8")
    kandidaten = list(args.urls) + urls_aus(text)
    if not kandidaten:
        print("Keine Links gefunden — nichts zu pruefen.", file=sys.stderr)
        return 0

    karte = ingress_karte()
    if not karte:
        print("FEHLER: keine cloudflared-Ingress-Liste gefunden — Hostnamen sind nicht aufloesbar.", file=sys.stderr)
        return 1

    schlecht = 0
    for url in kandidaten:
        status, hinweis = pruefe(url, karte)
        marke = {"ok": "OK  ", "fehler": "TOT ", "uebersprungen": "?   "}[status]
        print(f"{marke} {url}\n     {hinweis}")
        if status == "fehler" or (status == "uebersprungen" and args.streng):
            schlecht += 1

    print(f"\n{len(kandidaten)} geprueft, {schlecht} nicht in Ordnung.")
    if schlecht:
        print(
            "Ein toter Link geht NICHT raus. Erzeugen statt tippen: board.py --render\n"
            "liefert die Vorgangs-Links, der Mail-Link ist /m/<konto>/<ordner-slug>/<uid>\n"
            "auf mail.iil.pet — der Ordner-Teil ist Pflicht, nicht Zierde.",
            file=sys.stderr,
        )
    return 1 if schlecht else 0


if __name__ == "__main__":
    raise SystemExit(main())
