#!/usr/bin/env python3
"""Board-Einträge an die Message-ID binden, damit Verschieben nichts zerreißt.

Warum es das gibt: Ein Board-Eintrag zeigte bisher auf Ordner + UID. UIDs gelten
pro Ordner — verschiebt der Owner eine Mail (oder räumt `/organize-mail` auf),
zeigt der Link ins Leere und der Eintrag meldet nur „gibt es nicht", ohne sagen
zu können, ob verschoben oder gelöscht. Genau das passierte am 2026-07-29 mit
einer Termineinladung: aufgefallen ist es an einem 404, erklärbar erst nach einer
Suche über alle Ordner.

Die Message-ID ist der stabile Anker — dieselbe Begründung, die
`referenzpostfach.py` für die Grundgesamtheit schon zieht: „UIDs → Message-IDs.
Der Anker der Grundgesamtheit, weil UIDs nicht stabil sind."

Damit lässt sich pro Eintrag sauber unterscheiden:

    UNVERAENDERT  UID trifft noch, Message-ID stimmt      → schneller Weg, kein Suchen
    VERSCHOBEN    Message-ID in einem anderen Ordner      → Anker wird nachgezogen
    GELOESCHT     Message-ID nirgends mehr                → wird gemeldet, nicht verschluckt

Kosten: im Regelfall ein Kopfzeilen-Abruf je Eintrag. Die Suche über alle Ordner
läuft nur, wenn der schnelle Weg reißt.

Strikt read-only gegenüber dem Postfach (`select(readonly=True)` + `BODY.PEEK`).
Der Ankerspeicher liegt unter ~/.claude, nie in einem Repo — er trägt Betreffs
und Ordnernamen (Charta Art. 2).
"""

from __future__ import annotations

import argparse
import email
import email.utils
import imaplib
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from read_mail import (
    _mailbox_arg,
    _resolve_config,
    alle_ordner,
    connect,
    decode_hdr,
)
from send_mail import parse_env

#: Ankerspeicher. Schwester von ~/.claude/mail-action-board.md.
ANKER_DATEI = Path.home() / ".claude" / "mail-anker.json"

UNVERAENDERT = "unveraendert"
VERSCHOBEN = "verschoben"
GELOESCHT = "geloescht"
UNPRUEFBAR = "unpruefbar"

_MSGID = re.compile(rb"Message-ID:\s*(<[^>]+>)", re.IGNORECASE)


@dataclass
class Anker:
    """Ein Board-Eintrag und die Mail, an der er hängt."""

    item: str
    konto: str
    ordner: str
    uid: str
    message_id: str
    betreff: str = ""
    #: Datum der Mail (ISO, ``YYYY-MM-DD``) — leer bei Ankern aus der Zeit vor
    #: 2026-09-03. Es unterscheidet zwei Mails, die denselben Betreff tragen:
    #: ein weitergeleiteter Strang heisst in jeder Weiterleitung gleich, und im
    #: Verlauf standen dann zwei Links, die niemand auseinanderhalten konnte,
    #: ohne beide zu oeffnen (Owner-Befund 2026-09-03 an Vorgang 160).
    datum: str = ""

    @classmethod
    def aus_dict(cls, daten: dict) -> Anker:
        erlaubt = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in daten.items() if k in erlaubt})


@dataclass
class Befund:
    """Was die Prüfung eines Ankers ergeben hat."""

    anker: Anker
    zustand: str
    neuer_ordner: str = ""
    neue_uid: str = ""
    hinweis: str = ""

    @property
    def handlungsbedarf(self) -> bool:
        return self.zustand in (VERSCHOBEN, GELOESCHT)


def lade(pfad: Path = ANKER_DATEI) -> dict[str, Anker]:
    if not pfad.exists():
        return {}
    try:
        roh = json.loads(pfad.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(roh, dict):
        return {}
    return {k: Anker.aus_dict(v) for k, v in roh.items() if isinstance(v, dict)}


def speichere(anker: dict[str, Anker], pfad: Path = ANKER_DATEI) -> None:
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(
        json.dumps(
            {k: asdict(v) for k, v in anker.items()}, indent=2, ensure_ascii=False
        ),
        encoding="utf-8",
    )


def message_id_von_uid(imap: imaplib.IMAP4_SSL, uid: str) -> str:
    """UID → Message-ID, ohne den ganzen Rumpf zu ziehen. '' wenn es sie nicht gibt."""
    typ, data = imap.uid(
        "FETCH", uid, "(BODY.PEEK[HEADER.FIELDS (MESSAGE-ID SUBJECT)])"
    )
    if typ != "OK" or not data or data[0] is None:
        return ""
    roh = b"".join(teil[1] for teil in data if isinstance(teil, tuple))
    treffer = _MSGID.search(roh)
    return treffer.group(1).decode("ascii", "replace") if treffer else ""


def betreff_von_uid(imap: imaplib.IMAP4_SSL, uid: str) -> str:
    typ, data = imap.uid("FETCH", uid, "(BODY.PEEK[HEADER.FIELDS (SUBJECT)])")
    if typ != "OK" or not data or data[0] is None:
        return ""
    roh = b"".join(teil[1] for teil in data if isinstance(teil, tuple))
    return decode_hdr(email.message_from_bytes(roh).get("Subject")) or ""


def datum_von_uid(imap: imaplib.IMAP4_SSL, uid: str) -> str:
    """UID → Datum der Mail als ISO-Tag. '' wenn der Kopf keins traegt.

    Nur der Tag, nicht die Uhrzeit: er soll zwei gleichbetreffte Mails im
    Verlauf unterscheidbar machen, nicht die Zustellung protokollieren.
    """
    typ, data = imap.uid("FETCH", uid, "(BODY.PEEK[HEADER.FIELDS (DATE)])")
    if typ != "OK" or not data or data[0] is None:
        return ""
    roh = b"".join(teil[1] for teil in data if isinstance(teil, tuple))
    kopf = email.message_from_bytes(roh).get("Date")
    if not kopf:
        return ""
    try:
        return email.utils.parsedate_to_datetime(kopf).date().isoformat()
    except (TypeError, ValueError):
        return ""


def suche_message_id(
    imap: imaplib.IMAP4_SSL, message_id: str, ausser: str = ""
) -> tuple[str, str]:
    """Message-ID über alle Ordner suchen → (ordner, uid). ('', '') wenn weg.

    Der Ordner, in dem sie zuletzt lag, wird übersprungen — dort wurde bereits
    über die UID nachgesehen.
    """
    ordner_liste, _ = alle_ordner(imap)
    for ordner in ordner_liste:
        if ordner == ausser:
            continue
        try:
            typ, _ = imap.select(_mailbox_arg(ordner), readonly=True)
            if typ != "OK":
                continue
            typ, data = imap.uid("SEARCH", None, "HEADER", "Message-ID", message_id)
        except (imaplib.IMAP4.error, OSError):
            continue
        if typ == "OK" and data and data[0]:
            uids = data[0].split()
            if uids:
                return ordner, uids[-1].decode()
    return "", ""


def pruefe_anker(imap: imaplib.IMAP4_SSL, anker: Anker) -> Befund:
    """Ein Anker gegen das Postfach. Schneller Weg zuerst, Suche nur im Fehlerfall."""
    if not anker.message_id:
        return Befund(anker, UNPRUEFBAR, hinweis="kein Message-ID-Anker hinterlegt")

    try:
        typ, _ = imap.select(_mailbox_arg(anker.ordner), readonly=True)
        gefunden = message_id_von_uid(imap, anker.uid) if typ == "OK" else ""
    except (imaplib.IMAP4.error, OSError) as fehler:
        return Befund(anker, UNPRUEFBAR, hinweis=f"Ordner nicht lesbar: {fehler}")

    if gefunden == anker.message_id:
        return Befund(anker, UNVERAENDERT)

    ordner, uid = suche_message_id(imap, anker.message_id, ausser=anker.ordner)
    if ordner:
        return Befund(anker, VERSCHOBEN, neuer_ordner=ordner, neue_uid=uid)
    return Befund(anker, GELOESCHT)


def uebernehme(befunde: list[Befund], anker: dict[str, Anker]) -> dict[str, Anker]:
    """Verschobene Anker nachziehen, gelöschte stehen lassen.

    Gelöschte werden NICHT stillschweigend entfernt — ein Eintrag verschwindet
    erst durch eine Entscheidung des Owners, nicht durch einen Befund
    (Pflege-Regel 1 des Boards: „Item verschwindet erst bei Beleg").
    """
    for befund in befunde:
        if befund.zustand == VERSCHOBEN:
            alt = anker[befund.anker.item]
            anker[befund.anker.item] = Anker(
                item=alt.item,
                konto=alt.konto,
                ordner=befund.neuer_ordner,
                uid=befund.neue_uid,
                message_id=alt.message_id,
                betreff=alt.betreff,
            )
    return anker


def rendern(befunde: list[Befund]) -> str:
    symbole = {
        UNVERAENDERT: "·",
        VERSCHOBEN: "→",
        GELOESCHT: "✗",
        UNPRUEFBAR: "?",
    }
    zeilen = []
    for befund in befunde:
        a = befund.anker
        zeile = f"{symbole[befund.zustand]} #{a.item} {a.betreff[:44]}"
        if befund.zustand == VERSCHOBEN:
            zeile += f"\n    {a.ordner} → {befund.neuer_ordner} (UID {befund.neue_uid})"
        elif befund.zustand == GELOESCHT:
            zeile += f"\n    war in {a.ordner}, in keinem Ordner mehr auffindbar"
        elif befund.zustand == UNPRUEFBAR:
            zeile += f"\n    {befund.hinweis}"
        zeilen.append(zeile)

    zaehler = {z: sum(1 for b in befunde if b.zustand == z) for z in symbole}
    bilanz = (
        f"{len(befunde)} Anker · {zaehler[UNVERAENDERT]} unverändert · "
        f"{zaehler[VERSCHOBEN]} verschoben · {zaehler[GELOESCHT]} gelöscht"
    )
    if zaehler[UNPRUEFBAR]:
        bilanz += f" · {zaehler[UNPRUEFBAR]} unprüfbar"
    return "\n".join([bilanz, ""] + zeilen) if befunde else "keine Anker hinterlegt"


def _verbinde(konto: str):
    return connect(
        parse_env(_resolve_config(None, None if konto == "default" else konto))
    )


def cmd_setze(args: argparse.Namespace) -> None:
    anker = lade()
    imap = _verbinde(args.account)
    try:
        imap.select(_mailbox_arg(args.folder), readonly=True)
        mid = message_id_von_uid(imap, args.uid)
        if not mid:
            sys.exit(f"FEHLER: UID {args.uid} in '{args.folder}' nicht gefunden.")
        betreff = args.betreff or betreff_von_uid(imap, args.uid)
    finally:
        imap.logout()
    anker[args.setze] = Anker(
        item=args.setze,
        konto=args.account,
        ordner=args.folder,
        uid=args.uid,
        message_id=mid,
        betreff=betreff,
    )
    speichere(anker)
    print(f"#{args.setze} verankert: {betreff[:50]} · {mid}")


def cmd_pruefe(args: argparse.Namespace) -> None:
    anker = lade()
    if not anker:
        print("keine Anker hinterlegt")
        return
    befunde: list[Befund] = []
    nach_konto: dict[str, list[Anker]] = {}
    for a in anker.values():
        nach_konto.setdefault(a.konto, []).append(a)

    for konto, liste in sorted(nach_konto.items()):
        try:
            imap = _verbinde(konto)
        # Benannt statt blind: das sind die Arten, die wirklich "Konto
        # unbenutzbar" heissen — Netz und TLS und Zeitueberschreitung als
        # OSError, Login-Ablehnung als IMAP4.error, fehlender SMTP_HOST oder
        # unbrauchbarer Port als KeyError/ValueError. Ein AttributeError ist
        # dagegen ein Fehler im Code und soll auffliegen, statt sich als
        # "nicht erreichbar" zu tarnen.
        #
        # SystemExit eigens: `load_credentials` beendet bei einem fehlenden
        # Credential-Paar den PROZESS (sys.exit) statt zu werfen. SystemExit
        # ist keine Exception — bis 2026-09-03 riss genau dieser gewoehnliche
        # Fall den ganzen Lauf mit, samt der Arbeit aller anderen Konten.
        # Wurzel (sys.exit in einer Bibliotheksfunktion) siehe platform#2752.
        except (
            OSError,
            imaplib.IMAP4.error,
            KeyError,
            ValueError,
            SystemExit,
        ) as fehler:
            befunde += [
                Befund(
                    a, UNPRUEFBAR, hinweis=f"Konto '{konto}' nicht erreichbar: {fehler}"
                )
                for a in liste
            ]
            continue
        try:
            befunde += [pruefe_anker(imap, a) for a in liste]
        finally:
            imap.logout()

    if args.json:
        print(
            json.dumps(
                [
                    {
                        "item": b.anker.item,
                        "zustand": b.zustand,
                        "ordner": b.neuer_ordner or b.anker.ordner,
                        "uid": b.neue_uid or b.anker.uid,
                        "betreff": b.anker.betreff,
                        "hinweis": b.hinweis,
                    }
                    for b in befunde
                ],
                indent=2,
                ensure_ascii=False,
            )
        )
    else:
        print(rendern(befunde))

    if args.uebernehmen:
        speichere(uebernehme(befunde, anker))
    # Exit 1, sobald etwas nachzuziehen ist — damit ein Aufrufer es nicht übersieht.
    sys.exit(1 if any(b.handlungsbedarf for b in befunde) else 0)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    modus = ap.add_mutually_exclusive_group(required=True)
    modus.add_argument("--setze", metavar="ITEM", help="Board-Eintrag verankern")
    modus.add_argument(
        "--pruefe", action="store_true", help="alle Anker gegen das Postfach"
    )
    modus.add_argument("--liste", action="store_true", help="hinterlegte Anker zeigen")
    ap.add_argument(
        "--account", default="hnu", help="Konto-Kürzel ('default' = mail.env)"
    )
    ap.add_argument("--folder", "--source", default="INBOX", dest="folder")
    ap.add_argument("--uid", help="zu --setze: IMAP-UID der Mail")
    ap.add_argument("--betreff", help="zu --setze: Betreff überschreiben")
    ap.add_argument("--json", action="store_true")
    ap.add_argument(
        "--uebernehmen",
        action="store_true",
        help="zu --pruefe: verschobene Anker nachziehen (gelöschte bleiben stehen)",
    )
    args = ap.parse_args()

    if args.liste:
        for item, a in sorted(lade().items()):
            print(f"#{item}\t{a.konto}\t{a.ordner}\tUID {a.uid}\t{a.betreff[:40]}")
        return
    if args.setze:
        if not args.uid:
            sys.exit("FEHLER: --setze braucht --uid.")
        return cmd_setze(args)
    return cmd_pruefe(args)


if __name__ == "__main__":
    main()
