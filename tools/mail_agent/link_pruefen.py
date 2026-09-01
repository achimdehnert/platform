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

    python3 tools/mail_agent/link_pruefen.py --vorgangsseiten   # alle Mail-Links aller Vorgangsseiten

Exit 0 nur, wenn JEDER Link 200 liefert — UND die Seite etwas zeigt. Ein 200 mit
leerem Rumpf belegt den Transport, nicht den Inhalt (Nebenbefund platform#2563):
unter ``LEER_AB`` sichtbaren Zeichen gilt die Antwort als Fehler. Ein Link auf einem Host, der nicht in
der Ingress-Liste steht, gilt als **ungeprueft** und damit als Fehler — das ist
der Standard. Der Grund steht in der Entstehungsgeschichte: der Ausgangsfehler
war ein Link auf `todo.iil.pet`, und ein Pruefer, der unbekannte Hosts
durchwinkt, haette genau den durchgelassen, waere der Host nicht zufaellig in
der Liste gewesen. Wer bewusst fremde Hosts erlauben will, sagt `--nachsichtig`.
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

#: Unter so vielen sichtbaren Zeichen ist eine 200-Antwort eine leere Seite.
LEER_AB = 40
#: Hostname der Arbeitsliste — ihre Vorgangsseiten sind die Quelle fuer
#: ``--vorgangsseiten``; der Loopback-Port kommt aus der Ingress-Liste.
TODO_HOST = "todo.iil.pet"
_TAGS = re.compile(r"<(script|style)\b.*?</\1>|<[^>]+>", re.S | re.I)
_VORGANGSSEITE = re.compile(r"""href=['"](?:https?://[^/'"]+)?(/t/[^'"]+)['"]""")

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
        return (
            "uebersprungen",
            f"kein Loopback-Dienst fuer '{teile.netloc}' in der Ingress-Liste",
        )
    pfad = teile.path or "/"
    if teile.query:
        pfad += "?" + teile.query
    try:
        with urllib.request.urlopen(basis + pfad, timeout=TIMEOUT) as antwort:
            code = antwort.status
            rumpf = _rumpf(antwort)
    except urllib.error.HTTPError as exc:
        code = exc.code
    except OSError as exc:
        return "fehler", f"Dienst auf {basis} nicht erreichbar: {exc}"
    if code != 200:
        return "fehler", f"{basis}{pfad} → {code}"
    if rumpf is not None and sichtbare_zeichen(rumpf) < LEER_AB:
        return (
            "fehler",
            f"{basis}{pfad} → 200, aber leer ({sichtbare_zeichen(rumpf)} Zeichen)",
        )
    return "ok", f"{basis}{pfad} → 200"


def _rumpf(antwort) -> str | None:
    """Der Antworttext — None, wenn die Antwort keinen lesbaren Rumpf hat."""
    lesen = getattr(antwort, "read", None)
    if lesen is None:
        return None
    try:
        return lesen().decode("utf-8", "replace")
    except Exception:
        return None


def sichtbare_zeichen(html_text: str) -> int:
    """Wie viele Zeichen ein Leser auf der Seite sieht — Tags und Leerraum zaehlen nicht."""
    return len("".join(_TAGS.sub(" ", html_text).split()))


def vorgangsseiten_links(
    karte: dict[str, str], todo_host: str = TODO_HOST
) -> list[str]:
    """Alle Links aller Vorgangsseiten der Arbeitsliste — auf Hosts, die die Karte kennt.

    Die Liste (``/``) nennt jede Vorgangsseite (``/t/<key>``); jede davon nennt
    ihre Mail-Links. GitHub-Links und andere fremde Hosts bleiben draussen: sie
    sind nicht Gegenstand von platform#2592 K2 und waeren als ``?`` nur Rauschen.
    """
    basis = karte.get(todo_host)
    if basis is None:
        raise LookupError(f"'{todo_host}' steht nicht in der Ingress-Liste")
    with urllib.request.urlopen(basis + "/", timeout=TIMEOUT) as antwort:
        liste = _rumpf(antwort) or ""
    seiten = sorted(set(_VORGANGSSEITE.findall(liste)))
    links: list[str] = []
    for pfad in seiten:
        with urllib.request.urlopen(basis + pfad, timeout=TIMEOUT) as antwort:
            seite = _rumpf(antwort) or ""
        for url in urls_aus(seite):
            if urlsplit(url).netloc in karte and url not in links:
                links.append(url)
    print(f"{len(seiten)} Vorgangsseiten, {len(links)} Links auf bekannten Hosts")
    return links


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
    # `finditer` statt `findall`, weil das Zeichen NACH dem Treffer entscheidet:
    # das URL-Muster bricht an `<` ab, aus `…/i/<kurz-id>` wird also `…/i/` —
    # eine abgeschnittene Schablone, die den Schablonen-Filter unterlaufen
    # wuerde, weil ihr die spitze Klammer fehlt. Am 2026-08-25 vom eigenen Test
    # gefangen, nicht vom Auge.
    for treffer in _URL.finditer(rest):
        if rest[treffer.end() : treffer.end() + 1] == "<":
            continue
        merke(treffer.group(0).rstrip(".,;:)"))
    return gesehen


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("urls", nargs="*", help="zu pruefende Links")
    p.add_argument("--stdin", action="store_true", help="Links aus stdin herauslesen")
    p.add_argument("--datei", type=Path, help="Links aus einer Datei herauslesen")
    p.add_argument(
        "--nachsichtig",
        action="store_true",
        help="Links auf fremden Hosts durchwinken, statt sie als ungeprueft zu werten "
        "(Ausnahme — der Standard ist streng)",
    )
    p.add_argument(
        "--vorgangsseiten",
        action="store_true",
        help="alle Mail-Links aller Vorgangsseiten der Arbeitsliste pruefen (#2592 K2)",
    )
    args = p.parse_args()

    text = ""
    if args.stdin:
        text += sys.stdin.read()
    if args.datei:
        text += args.datei.read_text(encoding="utf-8")
    kandidaten = list(args.urls) + urls_aus(text)

    karte = ingress_karte()
    if not karte:
        print(
            "FEHLER: keine cloudflared-Ingress-Liste gefunden — Hostnamen sind nicht aufloesbar.",
            file=sys.stderr,
        )
        return 1
    if args.vorgangsseiten:
        try:
            kandidaten += vorgangsseiten_links(karte)
        except (LookupError, OSError) as fehler:
            print(f"FEHLER: Vorgangsseiten nicht lesbar: {fehler}", file=sys.stderr)
            return 1
    if not kandidaten:
        print("Keine Links gefunden — nichts zu pruefen.", file=sys.stderr)
        return 0

    schlecht = 0
    for url in kandidaten:
        status, hinweis = pruefe(url, karte)
        marke = {"ok": "OK  ", "fehler": "TOT ", "uebersprungen": "?   "}[status]
        print(f"{marke} {url}\n     {hinweis}")
        if status == "fehler" or (status == "uebersprungen" and not args.nachsichtig):
            schlecht += 1

    print(f"\n{len(kandidaten)} geprueft, {schlecht} nicht in Ordnung.")
    if schlecht:
        print(
            "Ein toter Link geht NICHT raus. Erzeugen statt tippen: board.py --render\n"
            "liefert die Vorgangs-Links; ein Mail-Link ist /a/<schluessel> auf mail.iil.pet\n"
            "und entsteht durch eintrag_anker.py — nicht durch Abschreiben einer UID.\n"
            "Ein '?'-Link liegt auf einem Host ohne Loopback-Dienst und ist damit"
            " nicht geprueft, nicht in Ordnung — '--nachsichtig' winkt ihn durch.",
            file=sys.stderr,
        )
    return 1 if schlecht else 0


if __name__ == "__main__":
    raise SystemExit(main())
