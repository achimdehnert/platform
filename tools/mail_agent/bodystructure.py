"""IMAP-`BODYSTRUCTURE` lesen — welche Teile hat eine Nachricht, ohne sie zu holen.

**Warum das überhaupt gebraucht wird.** Der Bulk-Abruf des Index holt
`BODY.PEEK[HEADER.FIELDS (...)]`, also Kopfzeilen. Wer auf einer solchen
Nachricht `msg.walk()` laufen lässt, findet nie einen Anhang — nicht weil keiner
da ist, sondern weil der Körper nie übertragen wurde. Bis 2026-08-02 stand
deshalb `has_attachments=False` an **allen** 3.649 IMAP-Kopien des Bestands
(platform#1663). Das ist ein Vorgabewert, der wie ein Messwert aussieht.

`BODYSTRUCTURE` ist die Antwort darauf: der Server beschreibt den Aufbau der
Nachricht, ohne einen Anhang zu übertragen. Im Bulk-FETCH kostet das keinen
zweiten Umlauf — dieselbe Antwort trägt Kopfzeilen und Struktur.

**Die Rückgabe ist bewusst dreiwertig.** `None` heißt „nicht erhoben" und ist
etwas anderes als eine leere Liste („erhoben, keine Anhänge"). Diese
Unterscheidung ist der ganze Punkt: die Fehlerklasse, die hier repariert wird,
entstand daraus, dass ein Nicht-Wissen als Nein durchging.
"""

from __future__ import annotations

import re
import urllib.parse
from dataclasses import dataclass
from email.header import decode_header, make_header

#: Werte, die als Content-Disposition gelten. Alles andere ist ein Atom aus
#: einem anderen Feld und darf nicht als Disposition durchgehen.
_DISPOSITIONEN = {"attachment", "inline"}

_ATOM = re.compile(rb"[^\s()\"]+")


class NichtLesbar(Exception):
    """Struktur nicht parsebar — führt zu `None`, nie zu „keine Anhänge"."""


@dataclass(frozen=True)
class Teil:
    """Ein benannter Teil einer Nachricht — das, was ein Mensch „Anhang" nennt."""

    dateiname: str = ""
    media_type: str = ""
    groesse: int = 0
    disposition: str = ""
    #: Content-ID, falls gesetzt. Ein Teil MIT Content-ID und `inline` wird aus
    #: dem HTML-Körper heraus referenziert (`cid:`) — er ist Bestandteil der
    #: Darstellung, kein beigelegtes Dokument.
    content_id: str = ""
    #: Pfad im Baum, z. B. "2.1" — die IMAP-Teilnummer, mit der er einzeln
    #: abrufbar wäre. Nützlich, wenn ein Anhang später gezielt geholt wird,
    #: statt die ganze Nachricht zu ziehen.
    teilnummer: str = ""

    @property
    def ist_layout(self) -> bool:
        """Eingebettetes Beiwerk statt Dokument — Signaturlogo, Trennlinie, Icon.

        **Am echten Bestand gemessen** (HNU, 551 Nachrichten, 2026-08-02): 173
        `image/jpeg` und 137 `image/png` — die weit überwiegende Mehrheit
        `image001.jpg` aus Outlook-Signaturen, jeweils `inline` **mit**
        Content-ID. Zählte man die als Anhang, bestünde die Anhangsstatistik
        zur Hälfte aus Firmenlogos, und ein Volltextlauf lüde sie mit herunter.

        Das Unterscheidungsmerkmal ist die Content-ID, nicht der Medientyp: sie
        bedeutet „wird aus dem Körper referenziert". Ein Foto, das jemand
        wirklich mitschickt, kommt als `attachment` ohne Content-ID.
        """
        return self.disposition == "inline" and bool(self.content_id)

    @property
    def ist_anhang(self) -> bool:
        """`attachment` zählt immer; `inline` nur, wenn es kein Layout ist."""
        if self.ist_layout:
            return False
        if self.disposition == "attachment":
            return True
        return bool(self.dateiname)


@dataclass
class _Leser:
    """Zeichenweiser Leser über die S-Ausdruck-Notation von IMAP."""

    daten: bytes
    pos: int = 0

    def ueberspringen(self) -> None:
        while (
            self.pos < len(self.daten) and self.daten[self.pos : self.pos + 1].isspace()
        ):
            self.pos += 1

    def lesen(self):
        """Ein Element: Liste, Zeichenkette, NIL oder Atom."""
        self.ueberspringen()
        if self.pos >= len(self.daten):
            raise NichtLesbar("Ende mitten im Ausdruck")
        z = self.daten[self.pos : self.pos + 1]
        if z == b"(":
            self.pos += 1
            raus: list = []
            while True:
                self.ueberspringen()
                if self.pos >= len(self.daten):
                    raise NichtLesbar("Klammer nie geschlossen")
                if self.daten[self.pos : self.pos + 1] == b")":
                    self.pos += 1
                    return raus
                raus.append(self.lesen())
        if z == b")":
            raise NichtLesbar("Klammer zu ohne auf")
        if z == b'"':
            return self._zeichenkette()
        if z == b"{":
            # Literal — der Inhalt steht in einem eigenen Antwortteil, den wir
            # hier nicht haben. Lieber ehrlich abbrechen als raten.
            raise NichtLesbar(
                "Literal in BODYSTRUCTURE — nicht aus einem Stueck lesbar"
            )
        m = _ATOM.match(self.daten, self.pos)
        if not m:
            raise NichtLesbar(f"unlesbares Zeichen an Position {self.pos}")
        self.pos = m.end()
        roh = m.group(0)
        if roh.upper() == b"NIL":
            return None
        text = roh.decode("utf-8", "replace")
        return int(text) if text.isdigit() else text

    def _zeichenkette(self) -> str:
        self.pos += 1  # das oeffnende Anfuehrungszeichen
        raus = bytearray()
        while self.pos < len(self.daten):
            z = self.daten[self.pos : self.pos + 1]
            if z == b"\\":
                # Maskiertes Zeichen — genau eines, wie RFC 3501 es vorsieht.
                self.pos += 1
                if self.pos >= len(self.daten):
                    raise NichtLesbar("Maskierung am Ende")
                raus += self.daten[self.pos : self.pos + 1]
                self.pos += 1
                continue
            if z == b'"':
                self.pos += 1
                return raus.decode("utf-8", "replace")
            raus += z
            self.pos += 1
        raise NichtLesbar("Zeichenkette nie geschlossen")


def _paare(werte) -> dict:
    """IMAP-Parameterliste `("name" "x.pdf" "size" "12")` → Wörterbuch."""
    if not isinstance(werte, list):
        return {}
    raus = {}
    for i in range(0, len(werte) - 1, 2):
        schluessel, wert = werte[i], werte[i + 1]
        if isinstance(schluessel, str) and isinstance(wert, str):
            raus[schluessel.lower()] = wert
    return raus


def _entkodieren(wert: str) -> str:
    """RFC-2047-Wörter (`=?iso-8859-1?q?...?=`) in Klartext auflösen.

    **Am echten Bestand gefunden** (HNU, 2026-08-02): unter 109 PDF-Anhängen
    trugen 10 einen Namen wie `Antrag.pdf?=` oder gar
    `Antrag.pd?= =?iso-8859-1?q?f?=` — der Name war über zwei kodierte Wörter
    getrennt, mitten in der Dateiendung. Ungelöst kostet das nicht nur einen
    hässlichen Namen: die Endung ist der Rückfall der Typerkennung, wenn der
    Server `application/octet-stream` meldet. Ein `.pdf?=` findet keinen Parser.
    """
    if "=?" not in wert:
        return wert
    try:
        return str(make_header(decode_header(wert)))
    except (UnicodeDecodeError, LookupError, ValueError):
        return wert


_FORTSETZUNG = re.compile(r"^(?P<name>[^*]+)\*(?P<nr>\d+)(?P<kodiert>\*?)$")


def _rfc2231(wert: str) -> str:
    """`utf-8''Ver%C3%A4nderung.pdf` → `Veränderung.pdf`."""
    teile = wert.split("'", 2)
    if len(teile) == 3:
        zeichensatz, _sprache, rest = teile
        return urllib.parse.unquote(
            rest, encoding=zeichensatz or "utf-8", errors="replace"
        )
    return urllib.parse.unquote(wert, errors="replace")


def dateiname_aus(params: dict, *schluessel: str) -> str:
    """Dateiname aus einer Parameterliste — inklusive Fortsetzungen und Kodierung.

    Lange Namen werden nach RFC 2231 auf `filename*0*`, `filename*1*` … verteilt;
    wer nur `filename` liest, bekommt bei genau diesen Namen **nichts** zurück
    und hält den Anhang für unbenannt.
    """
    for name in schluessel:
        # Ungeteilt, aber ggf. RFC-2231-kodiert (`filename*`).
        if params.get(f"{name}*"):
            return _rfc2231(params[f"{name}*"])
        if params.get(name):
            return _entkodieren(params[name])
        # Geteilt: Stücke nach Nummer sortiert zusammensetzen.
        stuecke: list[tuple[int, str, bool]] = []
        for schluessel_roh, wert in params.items():
            m = _FORTSETZUNG.match(schluessel_roh)
            if m and m.group("name") == name:
                stuecke.append((int(m.group("nr")), wert, bool(m.group("kodiert"))))
        if stuecke:
            stuecke.sort()
            zusammen = "".join(w for _nr, w, _k in stuecke)
            return _rfc2231(zusammen) if stuecke[0][2] else _entkodieren(zusammen)
    return ""


def _erweiterung_ab(typ: str, subtyp: str) -> int:
    """Ab welchem Index die Erweiterungsfelder beginnen — typabhängig.

    RFC 3501 kennt drei Formen des einteiligen Körpers, und sie unterscheiden
    sich genau darin, wie viele Pflichtfelder vor den Erweiterungen stehen:

    | Form | Pflichtfelder | Erweiterungen ab |
    |---|---|---|
    | beliebig | … Größe (6) | 7 |
    | `text/*` | … Größe, Zeilen (7) | 8 |
    | `message/rfc822` | … Größe, Umschlag, **Körper**, Zeilen (9) | 10 |

    **Warum das nicht egal ist.** Bei `message/rfc822` steht an Index 8 die
    vollständige Struktur der eingebetteten Nachricht — mit deren eigenen
    Dispositionen. Eine Suche, die dort hineinsieht, schreibt die Disposition
    eines *inneren* Anhangs dem äußeren Teil zu. An einer echten Zeile aus dem
    HNU-Postfach nachvollzogen (Unzustellbarkeitsbericht mit eingebetteter
    Originalnachricht): die Suche fand `attachment` im Inneren und hätte den
    Bericht selbst so ausgezeichnet.
    """
    if typ == "text":
        return 8
    if typ == "message" and subtyp == "rfc822":
        return 10
    return 7


def _disposition_finden(rest: list) -> tuple[str, dict]:
    """Disposition in den Erweiterungsfeldern suchen.

    Innerhalb des richtigen Ausschnitts wird **gesucht** statt gezählt: Server
    lassen optionale Felder (`md5`, `language`) weg, und dann verschiebt sich
    alles Nachfolgende. Die Disposition ist dagegen unverwechselbar — eine
    Liste, deren erstes Element `attachment` oder `inline` ist.
    """
    for element in rest:
        if (
            isinstance(element, list)
            and element
            and isinstance(element[0], str)
            and element[0].lower() in _DISPOSITIONEN
        ):
            return element[0].lower(), _paare(element[1] if len(element) > 1 else None)
    return "", {}


def _teil_lesen(knoten, nummer: str, raus: list[Teil]) -> None:
    """Einen Knoten des Baums auswerten und benannte Teile sammeln."""
    if not isinstance(knoten, list) or not knoten:
        return

    if isinstance(knoten[0], list):
        # Mehrteilig. Kinder sind **nur die führenden** Listen: was nach dem
        # Subtyp kommt, sind Parameter und Disposition des Mehrteilers selbst
        # und wäre als Kind ein erfundener Teil.
        kinder: list = []
        for k in knoten:
            if not isinstance(k, list):
                break
            kinder.append(k)
        for i, kind in enumerate(kinder, start=1):
            _teil_lesen(kind, f"{nummer}.{i}" if nummer else str(i), raus)
        return

    # Einteilig: [typ, subtyp, params, id, beschreibung, kodierung, groesse, ...]
    typ = knoten[0] if isinstance(knoten[0], str) else ""
    subtyp = knoten[1] if len(knoten) > 1 and isinstance(knoten[1], str) else ""
    params = _paare(knoten[2] if len(knoten) > 2 else None)
    content_id = knoten[3] if len(knoten) > 3 and isinstance(knoten[3], str) else ""
    groesse = 0
    for element in knoten[6:7]:
        if isinstance(element, int):
            groesse = element

    typ_klein, subtyp_klein = typ.lower(), subtyp.lower()
    disposition, dparams = _disposition_finden(
        knoten[_erweiterung_ab(typ_klein, subtyp_klein) :]
    )

    media_type = f"{typ_klein}/{subtyp_klein}" if typ and subtyp else ""
    dateiname = dateiname_aus(dparams, "filename") or dateiname_aus(params, "name")

    raus.append(
        Teil(
            dateiname=dateiname,
            media_type=media_type,
            groesse=groesse,
            disposition=disposition,
            content_id=content_id,
            teilnummer=nummer or "1",
        )
    )

    # Weitergeleitete Nachricht: an Index 8 steht ihre vollständige Struktur.
    # Ohne diesen Abstieg bleibt ein PDF, das jemand *in* einer weitergeleiteten
    # Mail mitschickt, unsichtbar — der äußere Teil meldet nur „message/rfc822".
    if typ_klein == "message" and subtyp_klein == "rfc822" and len(knoten) > 8:
        _teil_lesen(knoten[8], f"{nummer}.1" if nummer else "1", raus)


def teile_lesen(roh: bytes) -> list[Teil] | None:
    """Alle Teile einer `BODYSTRUCTURE`-Antwort — oder `None`, wenn nicht lesbar.

    `roh` ist der Abschnitt ab der öffnenden Klammer hinter dem Schlüsselwort
    `BODYSTRUCTURE`. `None` heißt ausdrücklich **nicht erhoben**.
    """
    try:
        baum = _Leser(roh).lesen()
    except NichtLesbar:
        return None
    if not isinstance(baum, list):
        return None
    raus: list[Teil] = []
    _teil_lesen(baum, "", raus)
    return raus


#: Findet den `BODYSTRUCTURE`-Abschnitt in einer FETCH-Antwortzeile.
_MARKE = re.compile(rb"BODYSTRUCTURE\s*\(", re.IGNORECASE)


def aus_fetch_antwort(zeile: bytes) -> list[Teil] | None:
    """`BODYSTRUCTURE` aus einer FETCH-Antwortzeile herausschneiden und lesen.

    Gibt `None` zurück, wenn die Antwort keine Struktur enthält (etwa weil sie
    nicht angefordert wurde) **oder** sie nicht lesbar ist. Beide Fälle sind
    „nicht erhoben" — der Aufrufer darf daraus nie „keine Anhänge" machen.
    """
    m = _MARKE.search(zeile)
    if not m:
        return None
    return teile_lesen(zeile[m.end() - 1 :])


def anhaenge(teile: list[Teil] | None) -> list[Teil] | None:
    """Aus allen Teilen die, die ein Mensch „Anhang" nennt. `None` bleibt `None`."""
    if teile is None:
        return None
    return [t for t in teile if t.ist_anhang]


def hat_anhaenge(teile: list[Teil] | None) -> bool:
    """Für das Feld `has_attachments` — **im Zweifel `True`**.

    Ist die Struktur nicht erhebbar, wäre `False` eine Behauptung über den
    Inhalt, die wir nicht geprüft haben; genau daran ist der Bestand einmal
    gescheitert. `True` kostet im schlimmsten Fall einen überflüssigen
    Volltext-Abruf — und der stellt es endgültig fest, weil er die ganze
    Nachricht holt. Ein falsches `False` dagegen verliert den Anhang dauerhaft,
    ohne eine Spur zu hinterlassen.
    """
    an = anhaenge(teile)
    if an is None:
        return True
    return bool(an)
