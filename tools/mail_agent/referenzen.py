#!/usr/bin/env python3
"""Mail-Referenzen in Verlaufseintraegen finden — EINE Lesart fuer alle Leser.

Warum es das gibt: Bis 2026-09-01 lasen drei Werkzeuge dieselben Saetze mit
drei verschiedenen Regexen (`todo_board.verweise`, `eintrag_mails.url_aus_text`,
und gar keiner fuer die PFLICHT-Regel „Nummer MIT Ordner" aus mailcheck.md —
platform#2199). Was der eine als Mail-Nummer erkannte, hielt der andere fuer
einen PR, und die Regel selbst hatte keinen Pruefer. Hier steht die Lesart
einmal, und jeder Leser holt sie sich.

Zwei Fragen beantwortet dieses Modul:

1. **Welche Mail meint der Satz?** `finde(text)` liefert jede Nummer, die als
   Nachrichten-Referenz auftritt (`INBOX #164024`, `UID 23589`, `#23611`), und
   sagt dazu, ob ein Ordner **daneben** steht. GitHub-Referenzen
   (`platform#2183`) werden vorher ausgeblendet — `#2183` ist keine UID.
2. **Unter welchem Schluessel ist sie verankert?** `schluessel(konto, slug, uid)`
   ist der Name, unter dem `eintrag_anker.py` die Message-ID ablegt und unter
   dem der Mail-Dienst sie als `/a/<schluessel>` ausliefert. Renderer und
   Verankerung rechnen denselben Schluessel aus demselben Text — nur so zeigt
   ein Link auf das, was verankert wurde.

Dazu der Pruefer fuer platform#2199 (`--pruefe-ordner`): jede Referenz ohne
Ordner in einem Eintrag ab dem Stichtag ist ein Verstoss. Eintraege VOR dem
Stichtag (der Tag, an dem die Regel in mailcheck.md kam) werden gezaehlt, aber
nicht angekreidet — ein Melder mit hundert Altlasten ist Rauschen, kein Gate.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mail_view import slugify  # noqa: E402

LEDGER = Path.home() / ".claude" / "mail-vorgaenge.json"
VERLAUF_ARCHIV = Path.home() / ".claude" / "mail-vorgaenge-archiv.json"
#: Ab diesem Tag ist eine Referenz ohne Ordner ein Verstoss. Die Regel steht
#: seit 2026-08-21 in mailcheck.md (#2191), der Pruefer kam am 2026-09-01
#: (#2592 K3). Bestandsaufnahme am Tag des Pruefers: 23 Referenzen ohne Ordner
#: seit der Regel, 14 nach Anerkennung von Aufzaehlungen — alle in Eintraegen,
#: die vor dem Pruefer geschrieben wurden. Ein Gate, das am ersten Tag rot
#: startet, wird umgangen statt befolgt; darum beginnt es mit dem Pruefer.
STICHTAG = date(2026, 9, 1)

#: Ordnernamen, die der Mail-Dienst als Slug kennt. Bewusst eine geschlossene
#: Liste echter Ordner — Prosa-Woerter wie "Papierkorb" oder "Entwurfsordner"
#: stehen NICHT drin: der HNU-Papierkorb heisst `Gelöschte Objekte`, ein Link auf
#: `/m/hnu/papierkorb/<uid>` waere ein 404 mit Selbstbewusstsein.
ORDNER = (
    "INBOX",
    "Entwürfe",
    "Entwuerfe",
    "Gesendete Objekte",
    "Gesendete Elemente",
    "Gelöschte Objekte",
    "Geloeschte Objekte",
    "Gelöschte Elemente",
    "Geloeschte Elemente",
    "Junk-E-Mail",
    "Posteingang",
)
ORDNER_RE = re.compile("|".join(re.escape(o) for o in ORDNER))
#: Was zwischen Ordnername und Nummer stehen darf, ohne den Bezug zu loesen.
#: `&#x27;`/`&quot;` sind die escapten Anfuehrungszeichen — der Renderer ruft
#: mit HTML-escaptem Text, der Pruefer mit rohem. Beide Formen sind erlaubt,
#: damit dieselbe Regel fuer beide gilt. Weitere Nummern samt Listen-Trennern
#: (`INBOX #164084, #164091`, `Entwuerfe #23761 bis #23780`, `(#29644/#29645`)
#: loesen den Bezug ebenfalls nicht: der Ordner gilt fuer die ganze Aufzaehlung
#: — so liest es ein Mensch, und so sollen es Pruefer und Renderer lesen.
NUR_TRENNER = re.compile(r"(?:\s|[('\"’„,/–-]|&#x27;|&quot;|UID|bis|und|#\d{3,7})*")
#: Jede Nummer, die als Nachrichten-Referenz auftritt — mit oder ohne Ordner.
REF_NUMMER = re.compile(r"(?:\bUID\s+|#)(?P<uid>\d{3,7})\b")
#: GitHub-Referenzen im Verlauf: `meiki-lra/meiki-hub#146` oder `platform#2183`.
#: Muessen VOR den Mail-Nummern greifen — sonst haelt die Nummernregel `#146`
#: fuer eine Mail-UID.
REF_GITHUB = re.compile(
    r"\b(?:(?P<owner>[A-Za-z][\w.-]*)/)?(?P<repo>[a-z][\w.-]*(?:-hub|-beat|-lab|platform|[\w.-]*))#(?P<nr>\d{1,6})\b"
)
#: Wo eine UID gesucht wird, wenn der Text keinen Ordner nennt. Bewusst eine
#: kurze, geordnete Liste statt aller ~120 Ordner: jeder Kandidat kostet ein
#: SELECT, und die Jahresarchive enthalten keine Nachricht, auf die ein laufender
#: Vorgang verweist. INBOX zuerst, weil dort der Regelfall liegt. Der Mail-Dienst
#: (`mail_link_server`) und die Verankerung (`eintrag_anker`) suchen in DERSELBEN
#: Reihenfolge — sonst verankert der eine, was der andere nicht findet.
SUCHORDNER = (
    "inbox",
    "posteingang",
    "entwuerfe",
    "drafts",
    "gesendete-objekte",
    "gesendete-elemente",
    "sent",
    "sent-items",
    "geloeschte-objekte",
    "geloeschte-elemente",
    "papierkorb",
    "trash",
    "junk-e-mail",
    "junk",
)
#: Kopf eines Verlaufseintrags: das Datum, mit dem er beginnt.
_DATUM = re.compile(r"^\s*(?:NEU\s+)?(\d{4}-\d{2}-\d{2})")
#: Wie weit vor der Nummer nach dem Ordner gesucht wird.
_FENSTER = 40


@dataclass(frozen=True)
class Referenz:
    """Eine Mail-Nummer im Text — und der Ordner, der daneben steht (oder nicht)."""

    uid: str
    ordner: str | None
    start: int
    end: int

    @property
    def slug(self) -> str | None:
        return slugify(self.ordner) if self.ordner else None


def ordner_daneben(text: str, start: int) -> str | None:
    """Der Ordnername unmittelbar vor Position `start` — oder None.

    Zwischen Ordnername und Nummer duerfen nur Anfuehrungszeichen, Klammern,
    Leerraum und das Wort UID stehen. Alles andere heisst: der Ordner gehoert zu
    einem anderen Satzteil. Genau daran scheiterte die erste Fassung im Renderer
    — sie nahm den naechstbesten Ordnernamen im Umkreis und verlinkte eine
    Gesendet-UID nach INBOX.
    """
    fenster = text[max(0, start - _FENSTER) : start]
    letzter = None
    for treffer in ORDNER_RE.finditer(fenster):
        letzter = treffer
    if letzter is None:
        return None
    zwischen = fenster[letzter.end() :]
    return letzter.group(0) if NUR_TRENNER.fullmatch(zwischen) else None


def ohne_github(text: str) -> str:
    """GitHub-Referenzen durch Leerraum gleicher Laenge ersetzen.

    Gleiche Laenge, damit die Positionen der uebrigen Treffer im Originaltext
    gueltig bleiben — der Renderer setzt seine Links ueber `start`/`end`.
    """
    return REF_GITHUB.sub(lambda m: " " * len(m.group(0)), text)


def finde(text: str) -> list[Referenz]:
    """Alle Mail-Referenzen im Text, in Lesereihenfolge."""
    bereinigt = ohne_github(text)
    return [
        Referenz(
            uid=m.group("uid"),
            ordner=ordner_daneben(bereinigt, m.start()),
            start=m.start(),
            end=m.end(),
        )
        for m in REF_NUMMER.finditer(bereinigt)
    ]


def schluessel(konto: str, slug: str | None, uid: str) -> str:
    """Der Anker-Schluessel einer Referenz, wie er im Ledger-Text steht.

    Mit Ordner `hnu-entwuerfe-23611`, ohne `hnu-23611`. Das Konto ist das des
    VORGANGS, nicht das, in dem die Mail spaeter gefunden wurde — der Renderer
    kennt nur den Vorgang, und er muss denselben Schluessel bilden.
    """
    return f"{konto}-{slug}-{uid}" if slug else f"{konto}-{uid}"


def schluessel_kandidaten(konto: str, ref: Referenz) -> tuple[str, ...]:
    """Unter welchen Schluesseln eine Referenz verankert sein kann — beste zuerst.

    Eine Nummer MIT Ordner ist auch unter dem ordnerlosen Schluessel gueltig,
    wenn dieselbe Mail frueher ohne Ordner genannt wurde. Umgekehrt nicht: ohne
    Ordner im Text laesst sich kein Ordner-Schluessel bilden.
    """
    if ref.slug:
        return (schluessel(konto, ref.slug, ref.uid), schluessel(konto, None, ref.uid))
    return (schluessel(konto, None, ref.uid),)


def eintrag_datum(text: str) -> date | None:
    m = _DATUM.match(text)
    if not m:
        return None
    try:
        return date.fromisoformat(m.group(1))
    except ValueError:
        return None


def verlauf_eintraege(v: dict, archiv: dict) -> list[str]:
    """Alle Eintraege eines Vorgangs, gekappte (Archiv) zuerst, dann aktive."""
    aktiv = [t.strip() for t in str(v.get("notiz") or "").split(" | ") if t.strip()]
    return [str(e) for e in archiv.get(str(v.get("nr")), [])] + aktiv


def _lade(pfad: Path) -> dict:
    try:
        daten = json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return daten if isinstance(daten, dict) else {}


@dataclass(frozen=True)
class Verstoss:
    nr: int | None
    eintrag: int
    datum: date | None
    uid: str
    auszug: str


def ohne_ordner(ledger: dict, archiv: dict) -> list[Verstoss]:
    """Jede Referenz ohne Ordner daneben — ueber alle Vorgaenge und Eintraege."""
    verstoesse: list[Verstoss] = []
    for v in ledger.get("vorgaenge", []):
        for i, text in enumerate(verlauf_eintraege(v, archiv), start=1):
            datum = eintrag_datum(text)
            for ref in finde(text):
                if ref.ordner:
                    continue
                auszug = text[max(0, ref.start - 30) : ref.end + 20].replace("\n", " ")
                verstoesse.append(Verstoss(v.get("nr"), i, datum, ref.uid, auszug))
    return verstoesse


def pruefe_ordner(
    ledger: dict, archiv: dict, stichtag: date = STICHTAG
) -> tuple[list[Verstoss], list[Verstoss]]:
    """(ab Stichtag, davor) — nur der erste Teil ist ein Gate-Verstoss."""
    alle = ohne_ordner(ledger, archiv)
    ab = [x for x in alle if x.datum is not None and x.datum >= stichtag]
    davor = [x for x in alle if x not in ab]
    return ab, davor


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--ledger", default=str(LEDGER))
    ap.add_argument("--verlauf-archiv", default=str(VERLAUF_ARCHIV))
    ap.add_argument(
        "--pruefe-ordner",
        action="store_true",
        help="Referenzen ohne Ordner melden (Exit 1 bei Verstoss ab Stichtag)",
    )
    ap.add_argument(
        "--stichtag",
        default=STICHTAG.isoformat(),
        help="ab wann eine Referenz ohne Ordner ein Verstoss ist",
    )
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    if not args.pruefe_ordner:
        ap.error("Aufruf braucht --pruefe-ordner.")

    ledger = _lade(Path(args.ledger))
    archiv = _lade(Path(args.verlauf_archiv))
    stichtag = date.fromisoformat(args.stichtag)
    ab, davor = pruefe_ordner(ledger, archiv, stichtag)

    if args.json:
        print(
            json.dumps(
                {
                    "stichtag": stichtag.isoformat(),
                    "ab_stichtag": [x.__dict__ | {"datum": str(x.datum)} for x in ab],
                    "davor": len(davor),
                },
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )
    else:
        print(
            f"Referenzen ohne Ordner: {len(ab)} ab {stichtag} (Verstoss), "
            f"{len(davor)} davor (Altbestand, nicht angekreidet)"
        )
        for x in ab:
            print(f"  #{x.nr}-{x.eintrag} {x.datum} UID {x.uid}: …{x.auszug}…")
    return 1 if ab else 0


if __name__ == "__main__":
    raise SystemExit(main())
