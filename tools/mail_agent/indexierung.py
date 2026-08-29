#!/usr/bin/env python3
"""Ausschlusskonfiguration für die Mail-Indexierung (ADR-286 §4.10.7).

**Warum ausschließen und nicht löschen.** Der Kostenvorteil ist bei beiden gleich
null — ein ausgeschlossener Ordner wird nie gelesen. Der Unterschied liegt im
Nenner: Ausschluss verkleinert die Grundgesamtheit **sichtbar** („Ordner X, 1.203
Nachrichten, bewusst nicht indexiert"), Löschung verkleinert sie **unsichtbar**.
Danach kann kein Deckungsausweis mehr sagen, was fehlt. Genau das ist die
Fehlerklasse, gegen die KONZ-035 geschrieben wurde.

Deshalb ist die Regel dieses Moduls: Ein ausgeschlossener Ordner wird nicht
durchsucht, **erscheint aber im Ausweis** unter „nicht gedeckt" mit seinem Grund.
Der Ordner-Nenner bleibt die volle Ordnerzahl, nicht die reduzierte.

Freigegeben vom Owner am 2026-07-28 auf Basis des gemessenen Ordner-Rauschberichts.

**Zweite Ausschlussklasse (2026-07-31): Ordner, die gar keine Post enthalten.**
Kalender, Kontakte und Aufgaben liefert Exchange über IMAP nicht als RFC822 aus —
statt der Einträge kommt je Eintrag ein Platzhalter zurück. Im Konto ``hnu`` waren
das **2.488 von 6.035 Einträgen (41,2 %)**, alle ohne Absender und ohne Datum, und
ihr Betreff landete als Volltext im Index. Das ist kein Deckungs-, sondern ein
Datenqualitätsproblem: hier fehlt nichts, hier steht zu viel. Die Regel wurde gegen
die realen 83 Ordner des Kontos kalibriert und entfernt **genau** diese 2.488 —
die verbleibenden 3.547 sind exakt die Einträge, die ein Datum tragen.

Lokale Ergänzungen: ``~/.claude/mail-index-exclude.txt``, ein Muster je Zeile
(Teilstring, Groß-/Kleinschreibung egal), ``#`` als Kommentar.
"""

from __future__ import annotations

import re
from pathlib import Path

LOKALE_LISTE = Path.home() / ".claude" / "mail-index-exclude.txt"

#: Jahresarchive bis einschliesslich diesem Jahr werden nicht indexiert.
ARCHIV_BIS = 2024

# Gematcht wird gegen ganze **Pfadsegmente**, nicht als Teilstring: Ein Kunden-
# ordner "Junker" darf nicht unter "junk" fallen, "Werbungskosten" nicht unter
# "Werbung". Ein Treffer auf einem Elternsegment schliesst die Kinder mit ein
# (Synchronisierungsprobleme/Konflikte).
_PAPIERKORB = re.compile(
    # 'Gel&APY-schte Objekte' ist IMAP-UTF7 fuer 'Geloeschte Objekte' — der rohe
    # Ordnername kommt so vom Server und muss mitgetroffen werden.
    r"^(gel(ö|oe|&APY-)schte (objekte|elemente)|deleted items?|papierkorb|trash"
    r"|junk-?e-?mail|junk|spam)$",
    re.I,
)
# 2026-08-29 (Owner-Go, platform ADR-299): Vier dieser Ordner sind seit heute die
# QUELLE des Hot-Topics-Digests — genau das, was hier bisher als "werblich" wegfiel.
# Die Ausschlussregel ist laut ADR-293 §3.2 zugleich die Speichergrenze; wer die
# Ordner lesen will, muss sie also indexieren, nicht am Ausschluss vorbeilesen.
# Ein zweites Regelwerk daneben waere genau der Zustand, den ADR-299 vermeidet.
#
# `werbung` bleibt bewusst DRIN: der Ordner ist gemischt (Newsletter neben
# Werbepost), und der Digest filtert ihn ohnehin ueber eine Absender-Allowlist.
# Ihn zu indexieren hiesse, Werbepost dauerhaft zu speichern, um drei Absender
# lesen zu koennen. Wenn das AD-Konto dazukommt, ist das eine eigene Entscheidung.
_REDAKTIONELL = re.compile(
    r"^(zacks|werbung|rss-abonnements)$",
    re.I,
)
_TECHNISCH = re.compile(r"^(synchronisierungsprobleme|sync issues)$", re.I)
# Exchange legt Kalender, Kontakte, Aufgaben, Notizen und Journal als IMAP-Ordner
# aus, gibt ihren Inhalt ueber IMAP aber NICHT als RFC822 heraus. Der Abruf
# liefert je Eintrag einen Platzhalter, dessen Betreff woertlich lautet:
#   "Retrieval using the IMAP4 protocol failed for the following message: <n>"
# — ohne Absender, ohne Datum. Gemessen am Konto hnu (2026-07-31): 2.488 von
# 6.035 Eintraegen (41,2 %) waren solche Platzhalter, exakt deckungsgleich mit
# den 2.488 ohne `sent_at` und praktisch deckungsgleich mit den 2.490 ohne
# `from_addr`. Sie landeten als Volltext im Index — eine Suche nach "failed"
# oder "protocol" lieferte 500 von 500 Treffern Platzhalter.
# Es sind keine Nachrichten und gehoeren nicht in einen Mail-Index.
_NICHT_MAIL = re.compile(
    r"^(kalender|calendar|kontakte|contacts|aufgaben|tasks|notizen|notes|journal)$",
    re.I,
)
_JAHRESARCHIV = re.compile(r"^(sent-)?archiv/(?P<jahr>\d{4})(-und-(ae|ä)lter)?$", re.I)


def _segmente(ordner: str) -> list[str]:
    return [t for t in re.split(r"[/.]", ordner) if t]


def _lokale_muster(pfad: Path | None = None) -> list[str]:
    quelle = pfad or LOKALE_LISTE
    try:
        zeilen = quelle.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    return [z.strip() for z in zeilen if z.strip() and not z.strip().startswith("#")]


def ist_ausgeschlossen(ordner: str, lokal: Path | None = None) -> str | None:
    """Grund für den Ausschluss — oder ``None``, wenn der Ordner indexiert wird.

    Der Rückgabewert ist bewusst der **Grund** und nicht ``True``: Er landet
    unverändert im Deckungsausweis, damit nachvollziehbar bleibt, warum ein Ordner
    fehlt. Ein blosses ``True`` erzeugte genau die stille Lücke, die vermieden
    werden soll.
    """
    segmente = _segmente(ordner)
    if any(_PAPIERKORB.match(s) for s in segmente):
        return "Papierkorb/Junk — bewusst nicht indexiert"
    if any(_TECHNISCH.match(s) for s in segmente):
        return "technischer Ordner — bewusst nicht indexiert"
    if any(_NICHT_MAIL.match(s) for s in segmente):
        # Elternsegment trifft die Kinder mit: 'Kalender/Feiertage in Deutschland'
        # und 'Kalender/Achim Dehnert' fallen ueber 'Kalender'.
        return "keine Mail (Kalender/Kontakte/Aufgaben) — ueber IMAP nicht abrufbar"
    if any(_REDAKTIONELL.match(s) for s in segmente):
        return "redaktionell/werblich — bewusst nicht indexiert"

    if m := _JAHRESARCHIV.match(ordner):
        jahr = int(m.group("jahr"))
        if jahr <= ARCHIV_BIS:
            return f"Jahresarchiv {jahr} (bis {ARCHIV_BIS}) — bewusst nicht indexiert"

    for muster in _lokale_muster(lokal):
        if muster.lower() in ordner.lower():
            return f"lokale Ausschlussliste ({muster})"

    return None


def aufteilen(
    ordner: list[str], lokal: Path | None = None
) -> tuple[list[str], list[tuple[str, str]]]:
    """(zu_indexieren, [(ordner, grund), ...]) — beide Mengen, nie nur die erste."""
    behalten: list[str] = []
    raus: list[tuple[str, str]] = []
    for o in ordner:
        if grund := ist_ausgeschlossen(o, lokal):
            raus.append((o, grund))
        else:
            behalten.append(o)
    return behalten, raus


def main() -> None:
    """Trockenlauf: zeigt für eine Ordnerliste auf stdin, was ausgeschlossen würde."""
    import sys

    ordner = [z.strip() for z in sys.stdin if z.strip()]
    behalten, raus = aufteilen(ordner)
    print(f"indexiert:      {len(behalten)}")
    print(f"ausgeschlossen: {len(raus)}")
    for o, grund in raus:
        print(f"  - {o}  →  {grund}")


if __name__ == "__main__":
    main()
