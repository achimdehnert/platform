"""Referenzpostfach mit bekannter Grundgesamtheit (KONZ-platform-035, REC-10).

Das Kill-Gate KG-RECALL verlangt eine Menge, bei der **vorher feststeht**, was drinsteht.
Nur dagegen lässt sich messen, ob eine Suche etwas übersieht — im echten Postfach ist
genau das unmöglich, weil man das Übersehene nicht kennt.

**Warum nicht anonymisierte Echt-Mails.** Anonymisieren hieße, jede Nachricht vollständig
zu lesen und auszuwerten — Betreff, Text, Signatur, zitierte Vorgänger. Genau das schließt
die Freigabe der Datenschutz-Folgenabschätzung aus, und für in Mails genannte Dritte trägt
die Ausnahme von der Informationspflicht ausdrücklich nicht, wenn deren Daten systematisch
ausgewertet werden. Der Bau des Testkorpus würde also die Bedingung verletzen, unter der
das Vorhaben freigegeben ist.

**Stattdessen: Struktur messen, Inhalt erfinden.** Was eine Suche scheitern lässt, ist
fast nie der Inhalt, sondern die Form — in welchem Ordner eine Nachricht liegt, wie der
Absender kodiert ist, ob Umlaute als MIME-Kodierung dastehen, ob der Begriff nur im Text
vorkommt. Vom echten Postfach werden deshalb nur **Zählwerte** erhoben (wie viele Ordner,
wie tief, wie viele Nachrichten, wie oft welche Kopfzeilen-Form); die Nachrichten selbst
sind frei erfunden. Es überlebt kein Wort eines Originals, also gibt es auch nichts zu
re-identifizieren.

**Restlücke, ehrlich benannt:** Die Form muss gemessen werden, statt sie zu raten — aber
ein Merkmal, das ich nicht als Merkmal erkenne, taucht auch im Profil nicht auf. Das ist
kleiner als beim frei erfundenen Postfach, aber nicht null.
"""

from __future__ import annotations

import email.header
import email.utils
import sys
from pathlib import Path
from typing import NamedTuple

sys.path.insert(0, str(Path(__file__).resolve().parent))

import read_mail as rm  # noqa: E402

#: Alles unterhalb dieser Wurzel gehört dem Referenzpostfach und wird beim Aufbau
#: gelöscht. Der Namespace-Trenner des Servers wird zur Laufzeit ermittelt.
WURZEL = "INBOX.REF"

#: Absender in X.500-Form — genau die Kodierung, an der am 2026-07-27 ein
#: Absender-Filter scheiterte, weil sie kein "@" enthält.
X500 = "/O=EXCHANGELABS/OU=EXCHANGE ADMINISTRATIVE GROUP/CN=RECIPIENTS/CN=abc123-Muster"


class Fall(NamedTuple):
    """Eine geplante Nachricht samt der Wahrheit, die über sie feststeht.

    ``begriffe`` ist die Grundgesamtheit für KG-RECALL: Eine Suche nach einem dieser
    Begriffe **muss** diese Nachricht liefern. Wer sie nicht liefert, hat einen False
    Negative — unabhängig davon, wie plausibel die Erklärung dafür klingt.
    """

    nr: int
    ordner: str
    absender: str
    betreff: str | None
    text: str
    begriffe: tuple[str, ...]
    warum: str


#: Die Fälle sind keine erfundenen Randfälle: Nr. 3, 5 und 9 bilden die drei belegten
#: Fehlschläge vom 2026-07-27 nach, der Rest deckt Formen ab, die im echten Bestand
#: gemessen wurden (X.500-Absender, MIME-kodierte Betreffs, betrefflose Nachrichten).
FAELLE: tuple[Fall, ...] = (
    Fall(
        1,
        "",
        "anna.muster@example.org",
        "Postsortierung im Amt",
        "Wir sollten die Postsortierung neu ordnen.",
        ("Postsortierung",),
        "Grundfall: Begriff in Betreff und Text, im Posteingang",
    ),
    Fall(
        2,
        "",
        "bernd.beispiel@example.org",
        "Rueckfrage",
        "Zur Postsortierung habe ich noch eine Anmerkung.",
        ("Postsortierung",),
        "Begriff NUR im Text — ein Betreff-Filter übersieht das",
    ),
    Fall(
        3,
        "Gesendet",
        "search@dehnert.team",
        "AW: Postsortierung im Amt",
        "Meine Antwort zur Postsortierung.",
        ("Postsortierung",),
        "eigene gesendete Nachricht — am 27.07. lagen 8 von 11 ausserhalb des Posteingangs",
    ),
    Fall(
        4,
        "Papierkorb",
        "carla.probe@example.org",
        "Postsortierung erledigt",
        "Der Vorgang Postsortierung ist abgeschlossen.",
        ("Postsortierung",),
        "geloescht heisst meistens erledigt — also gerade die Information ueber den Stand",
    ),
    Fall(
        5,
        "",
        X500,
        "Postsortierung intern",
        "Interner Hinweis zur Postsortierung.",
        ("Postsortierung",),
        "Absender ohne @ — der Platzhalter-Filter verwarf am 27.07. 21 von 34 Nachrichten",
    ),
    Fall(
        6,
        "Projekte.Ablage.Alt",
        "dora.demo@example.org",
        "Postsortierung Archiv",
        "Alte Unterlagen zur Postsortierung.",
        ("Postsortierung",),
        "tief verschachtelter Ordner — ein flacher Lauf erreicht ihn nicht",
    ),
    Fall(
        7,
        "Mit Leerzeichen",
        "emil.entwurf@example.org",
        "Postsortierung Notiz",
        "Notiz zur Postsortierung.",
        ("Postsortierung",),
        "Ordnername mit Leerzeichen — bricht SELECT ohne Quoting",
    ),
    Fall(
        8,
        "",
        "frida.frage@example.org",
        "Löschung nach Betroffenenanfrage",
        "Bitte um Löschung meiner Daten.",
        ("Löschung",),
        "Umlaut im Betreff — MIME-kodiert auf dem Draht, nicht als Klartext",
    ),
    Fall(
        9,
        "",
        "gustav.grund@example.org",
        None,
        "Auch diese Nachricht betrifft die Postsortierung.",
        ("Postsortierung",),
        "gar kein Betreff — jeder Betreff-basierte Zugriff laeuft ins Leere",
    ),
    Fall(
        10,
        "Projekte",
        "hanna.hinweis@example.org",
        "Fwd: voellig anderes Thema",
        "Im Verlauf: die Postsortierung wurde bereits geklaert.",
        ("Postsortierung",),
        "Betreff gewechselt — Thread-Zuordnung ueber den Betreff versagt hier",
    ),
    Fall(
        11,
        "",
        "ivo.irrelevant@example.org",
        "Kantinenplan",
        "Diese Woche gibt es Suppe.",
        (),
        "Gegenprobe: darf bei KEINEM Begriff auftauchen (False Positive)",
    ),
    Fall(
        12,
        "Papierkorb",
        "jana.jenseits@example.org",
        "Werbung",
        "Unschlagbares Angebot.",
        (),
        "zweite Gegenprobe, im Papierkorb",
    ),
)


def trenner(imap) -> str:
    """Namespace-Trenner des Servers — nicht raten, der Server sagt es in LIST."""
    typ, data = imap.list()
    if typ == "OK":
        for zeile in data or []:
            teile = zeile.decode(errors="replace").split('"')
            if len(teile) >= 2 and len(teile[1]) == 1:
                return teile[1]
    return "."


def gehoert_zur_wurzel(name: str, sep: str) -> bool:
    """Liegt dieser Ordner im Referenzpostfach — oder trägt er nur einen ähnlichen Namen?

    Der Aufbau **löscht** alles unterhalb der Wurzel. Ein bloßes ``startswith(WURZEL)``
    trifft dabei auch ``INBOX.REFERAT.Wichtig`` oder ``INBOX.REFERENZ``: der Präfix passt,
    obwohl es fremde Ordner sind. Bei einer löschenden Operation ist das kein Schönheits-
    fehler. Die Grenze muss der Namensraum-Trenner sein, nicht die Zeichenkette.
    """
    return name == WURZEL or name.startswith(WURZEL + sep)


def ordnerpfad(sep: str, ordner: str) -> str:
    """Relativer Fall-Ordner → absoluter Mailbox-Name unterhalb der Wurzel."""
    if not ordner:
        return WURZEL
    return WURZEL + sep + ordner.replace(".", sep)


def alle_ordner(sep: str) -> list[str]:
    """Jeder benötigte Ordner, Eltern vor Kindern — sonst schlägt CREATE fehl."""
    namen = {WURZEL}
    for f in FAELLE:
        if not f.ordner:
            continue
        teile = f.ordner.split(".")
        for i in range(1, len(teile) + 1):
            namen.add(ordnerpfad(sep, ".".join(teile[:i])))
    return sorted(namen, key=lambda n: (n.count(sep), n))


def nachricht_bauen(fall: Fall) -> bytes:
    """RFC-822-Nachricht mit stabiler Message-ID als Anker der Grundgesamtheit.

    Die Message-ID ist der Schlüssel, an dem KG-RECALL misst: UIDs stehen vor dem
    Hochladen nicht fest und wechseln bei jedem Neuaufbau, die ID nicht.
    """
    kopf = [
        f"From: {fall.absender}",
        "To: search@dehnert.team",
        f"Message-ID: <{nachricht_id(fall)}>",
        f"Date: {email.utils.formatdate(1784000000 + fall.nr * 3600)}",
        "MIME-Version: 1.0",
        'Content-Type: text/plain; charset="utf-8"',
        "Content-Transfer-Encoding: 8bit",
    ]
    if fall.betreff is not None:
        # Umlaute bewusst MIME-kodiert wie ein echter Client — genau die Form, an der
        # ein naiver Vergleich auf dem Rohkopf scheitert.
        kopf.insert(
            2, f"Subject: {email.header.Header(fall.betreff, 'utf-8').encode()}"
        )
    return ("\r\n".join(kopf) + "\r\n\r\n" + fall.text + "\r\n").encode("utf-8")


def nachricht_id(fall: Fall) -> str:
    return f"ref-{fall.nr:04d}@referenz.invalid"


def erwartung() -> dict[str, set[str]]:
    """Die Grundgesamtheit: Begriff → Message-IDs, die eine Suche liefern MUSS.

    Abgeleitet aus der Plan-Tabelle, nicht aus einem Suchlauf — sonst prüfte die
    Messung sich selbst. Der Plan weiß nicht, wie gesucht wird; die Suche weiß nicht,
    was geplant war.
    """
    raus: dict[str, set[str]] = {}
    for f in FAELLE:
        for b in f.begriffe:
            raus.setdefault(b, set()).add(nachricht_id(f))
    return raus


def gegenprobe() -> set[str]:
    """Nachrichten, die bei KEINEM Begriff auftauchen dürfen (False Positives)."""
    return {nachricht_id(f) for f in FAELLE if not f.begriffe}


def strukturprofil(imap) -> dict[str, int]:
    """Zählwerte eines echten Postfachs — ausschließlich Metadaten, keine Inhalte.

    Erhoben wird, wie viele Ordner es gibt, wie tief sie geschachtelt sind und wie
    viele Nachrichten je Ordner liegen. Kein Betreff, kein Absender, kein Text wird
    gespeichert oder zurückgegeben; die Zahlen sagen nichts über eine einzelne Person.
    """
    sep = trenner(imap)
    typ, data = imap.list()
    namen = []
    for zeile in data or []:
        teil = zeile.decode(errors="replace")
        if '"' in teil:
            namen.append(
                teil.rsplit('"', 2)[-2]
                if teil.endswith('"')
                else teil.split('"')[-1].strip()
            )
    namen = [n for n in namen if n]
    gesamt = 0
    for n in namen:
        typ, res = imap.status(f'"{n}"', "(MESSAGES)")
        if typ == "OK" and res and res[0]:
            import re

            if m := re.search(rb"MESSAGES\s+(\d+)", res[0]):
                gesamt += int(m.group(1))
    return {
        "ordner": len(namen),
        "maximale_tiefe": max((n.count(sep) for n in namen), default=0),
        "nachrichten": gesamt,
    }


def aufbauen(imap, verbose: bool = True) -> int:
    """Referenzpostfach von Grund auf neu erzeugen — idempotent.

    Erst wird alles unterhalb der Wurzel entfernt, dann neu geschrieben. Ein
    inkrementeller Aufbau wäre bequemer und würde genau das kaputt machen, was den
    Wert ausmacht: dass der Inhalt **exakt** dem Plan entspricht.
    """
    sep = trenner(imap)
    typ, data = imap.list()
    vorhandene = []
    for zeile in data or []:
        teil = zeile.decode(errors="replace")
        if WURZEL in teil:
            vorhandene.append(
                teil.split('"')[-2] if teil.count('"') >= 2 else teil.split()[-1]
            )
    for name in sorted(set(vorhandene), key=lambda n: -n.count(sep)):
        if not gehoert_zur_wurzel(name, sep):
            continue
        typ, res = imap.delete(f'"{name}"')
        if typ != "OK" and verbose:
            print(f"⚠ DELETE {name}: {res}", file=sys.stderr)

    for name in alle_ordner(sep):
        typ, res = imap.create(f'"{name}"')
        if typ != "OK" and verbose:
            print(f"⚠ CREATE {name}: {res}", file=sys.stderr)

    geschrieben = 0
    for fall in FAELLE:
        ziel = ordnerpfad(sep, fall.ordner)
        typ, res = imap.append(f'"{ziel}"', "", None, nachricht_bauen(fall))
        if typ == "OK":
            geschrieben += 1
        elif verbose:
            print(f"⚠ APPEND #{fall.nr} → {ziel}: {res}", file=sys.stderr)
    return geschrieben


def _message_ids(imap, uids: set[bytes]) -> set[str]:
    """UIDs → Message-IDs. Der Anker der Grundgesamtheit, weil UIDs nicht stabil sind."""
    if not uids:
        return set()
    _, resp = imap.uid(
        "FETCH",
        b",".join(sorted(uids)).decode(),
        "(BODY.PEEK[HEADER.FIELDS (MESSAGE-ID)])",
    )
    raus = set()
    for teil in resp or []:
        if isinstance(teil, tuple) and teil[1]:
            mid = email.message_from_bytes(teil[1]).get("Message-ID", "").strip("<>")
            if mid:
                raus.add(mid)
    return raus


def recall(imap, limit: int = 500) -> tuple[int, list[str]]:
    """KG-RECALL: findet die Suche jede geplante Nachricht wieder?

    **Ein einziger False Negative beendet den Pilot** (KONZ-035 §13). Deshalb wird hier
    nicht gerundet und nicht gemittelt — die Rückgabe ist die Zahl der Befunde und ihre
    Beschreibung.

    Gemessen wird über dieselben Pfade, die produktiv laufen, aber gegen eine Erwartung,
    die aus dem Plan stammt. Der Plan weiß nicht, wie gesucht wird; die Suche weiß nicht,
    was geplant war — ohne diese Trennung prüfte die Messung sich selbst.
    """
    import organize_mail as om
    import vorgang as vg

    befunde: list[str] = []
    for begriff, soll in sorted(erwartung().items()):
        je_pfad: dict[str, set[str]] = {"server-suche": set(), "client-filter": set()}
        for name in om.list_folders(imap):
            if imap.select(f'"{name}"', readonly=True)[0] != "OK":
                continue
            try:
                je_pfad["server-suche"] |= _message_ids(
                    imap, vg.pfad_server_suche(imap, begriff, "TEXT")
                )
            except Exception as exc:  # noqa: BLE001
                befunde.append(f"'{begriff}': server-suche brach ab in {name}: {exc!r}")
            uids, _ = vg.pfad_client_filter(imap, name, begriff, limit)
            imap.select(f'"{name}"', readonly=True)
            je_pfad["client-filter"] |= _message_ids(imap, uids)

        beide = je_pfad["server-suche"] | je_pfad["client-filter"]
        if fehlend := soll - beide:
            befunde.append(f"'{begriff}': False Negatives {sorted(fehlend)}")
        if falsch := beide & gegenprobe():
            befunde.append(f"'{begriff}': False Positives {sorted(falsch)}")
        print(f"'{begriff}': {len(beide & soll)}/{len(soll)} gefunden")
        for pfad, ids in sorted(je_pfad.items()):
            verpasst = soll - ids
            print(
                f"    {pfad}: {len(ids & soll)}/{len(soll)}"
                + (f"  verpasst {sorted(verpasst)}" if verpasst else "")
            )
    return len(befunde), befunde


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument(
        "--aufbauen", action="store_true", help="Referenzpostfach neu erzeugen"
    )
    g.add_argument("--erwartung", action="store_true", help="Grundgesamtheit ausgeben")
    g.add_argument(
        "--profil", action="store_true", help="Strukturprofil eines Postfachs"
    )
    g.add_argument(
        "--recall",
        action="store_true",
        help="KG-RECALL messen: Exit-Code 1 bei einem einzigen False Negative",
    )
    ap.add_argument("--account", help="Postfach-Kürzel (Aufbau NUR gegen 'search')")
    ap.add_argument("--config")
    args = ap.parse_args()

    if args.erwartung:
        for begriff, ids in sorted(erwartung().items()):
            print(f"{begriff}: {len(ids)} Nachricht(en)")
            for i in sorted(ids):
                print(f"  {i}")
        print(f"\nGegenprobe (darf nie treffen): {len(gegenprobe())}")
        return

    if args.aufbauen and args.account != "search":
        sys.exit(
            "FEHLER: --aufbauen schreibt Nachrichten und ist auf --account search "
            "beschränkt. Jedes andere Postfach enthält echte Post."
        )

    cfg = rm.parse_env(rm._resolve_config(args.config, args.account))
    imap = rm.connect(cfg)
    try:
        if args.profil:
            for k, v in strukturprofil(imap).items():
                print(f"{k}: {v}")
        elif args.recall:
            anzahl, befunde = recall(imap)
            print()
            for b in befunde:
                print(f"  ✗ {b}", file=sys.stderr)
            print(f"KG-RECALL: {'grün' if not anzahl else f'ROT — {anzahl} Befund(e)'}")
            if anzahl:
                sys.exit(1)
        else:
            n = aufbauen(imap)
            print(f"{n} von {len(FAELLE)} Nachricht(en) geschrieben.")
    finally:
        try:
            imap.logout()
        except Exception as exc:  # noqa: BLE001 — ein Logout-Fehler entwertet den Lauf nicht
            print(f"⚠ Logout: {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
