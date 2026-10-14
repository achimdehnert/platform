#!/usr/bin/env python3
"""Ablage-Lauf: aktive Regeln anwenden, unbeantwortete Mails bleiben liegen (platform#3970).

`regeln.py plan` sagt, wohin eine Mail gehört — aber nicht, ob sie schon erledigt
ist. Eine Regel kennt nur Absender und Betreff. Der Trockenlauf vom 2026-10-14
gegen 451 Mails im HNU-Posteingang zeigt die Folge: Die 51 vorgeschlagenen Regeln
träfen 375 Mails, darunter 43 der 47 noch offenen Vorgänge. Ein Lauf ohne Schutz
räumte also genau die Mails weg, die noch eine Antwort brauchen.

Deshalb verschiebt dieser Lauf eine getroffene Mail nur, wenn sie

* beantwortet ist — Flag `\\Answered` oder eine Mail im Gesendet-Ordner, deren
  `In-Reply-To`/`References` auf sie zeigt, oder
* keine Antwort braucht — maschinell versandt (`Auto-Submitted`, `List-Id`,
  `List-Unsubscribe`, `Precedence: bulk|list|junk`).

Alles andere bleibt im Posteingang und wird als „geschützt" gezählt. Ein Entwurf
zählt nicht als Antwort: solange er nicht gesendet ist, ist der Vorgang offen.

Weitere Grenzen:

* Nur Regeln im Zustand `aktiv` wirken (`regeln.wirksam`).
* Nur die Aktion `verschieben`. Papierkorb und Markieren bleiben außen vor.
* Jeder Lauf trägt eine `lauf_id` im Protokoll; `--ruecknahme <lauf_id>` holt
  ihn zurück. Die UID ändert sich beim Umzug, deshalb wird die Message-ID mit
  protokolliert und am Zielort neu aufgelöst.
* Ohne `--apply` ist es ein Trockenlauf. Kennzahl ist die Restmenge.

Regeln und Protokoll liegen unter `~/.claude/` und nie im Repo — sie tragen
Absenderadressen und Betreffs (ADR-284 §7a).

    python3 tools/mail_agent/ablage_lauf.py --account hnu              # Trockenlauf
    python3 tools/mail_agent/ablage_lauf.py --account hnu --apply      # verschieben
    python3 tools/mail_agent/ablage_lauf.py --account hnu --ruecknahme <lauf_id> --apply
"""

from __future__ import annotations

import argparse
import email
import imaplib
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from email.utils import parseaddr
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import regeln  # noqa: E402

QUELLORDNER = "INBOX"
#: Gesendet-Ordner der IMAP-Konten, gleiche Quelle wie sendeabgleich.py.
SENDEORDNER = "Gesendete Objekte"
#: Wie weit zurück der Gesendet-Ordner nach Antworten durchsucht wird.
SENDE_TAGE = 365

_KOEPFE = (
    "FROM SUBJECT DATE MESSAGE-ID AUTO-SUBMITTED LIST-ID LIST-UNSUBSCRIBE PRECEDENCE"
)
_MSGID = re.compile(r"<[^<>\s]+>")
_UID = re.compile(rb"UID (\d+)")
_FLAGS = re.compile(rb"FLAGS \(([^)]*)\)")


# --- Schutz: darf die Mail weg? ---------------------------------------------


def braucht_keine_antwort(kopf: dict) -> bool:
    """Maschinell versandt — Newsletter, Benachrichtigung, Verteiler.

    Nur Kopfzeilen, die der Versender selbst setzt; der Absendername allein
    („noreply") ist kein Beleg, weil Menschen auch über Systemadressen schreiben.
    """
    auto = (kopf.get("auto_submitted") or "").strip().lower()
    if auto and auto != "no":
        return True
    if kopf.get("list_id") or kopf.get("list_unsubscribe"):
        return True
    return (kopf.get("precedence") or "").strip().lower() in ("bulk", "list", "junk")


def schutz_grund(nachricht: dict, beantwortet_ids: set[str]) -> str | None:
    """None = darf weg; sonst der Grund, warum die Mail im Posteingang bleibt."""
    if nachricht.get("beantwortet"):
        return None
    if nachricht.get("message_id") and nachricht["message_id"] in beantwortet_ids:
        return None
    if braucht_keine_antwort(nachricht):
        return None
    return "unbeantwortet"


def lauf_planen(
    alle_regeln: list[regeln.Regel],
    bestand: list[dict],
    beantwortet_ids: set[str],
) -> dict:
    """Bewegungen, geschützte Treffer und Restmenge — ohne Postfachzugriff, prüfbar."""
    roh, rest = regeln.plan(alle_regeln, bestand)
    nach_id = {m.get("id"): m for m in bestand}
    bewegungen, geschuetzt, ausgelassen = [], [], []
    for b in roh:
        m = nach_id[b["id"]]
        if b["aktion"] != "verschieben":
            ausgelassen.append(b)
            continue
        if grund := schutz_grund(m, beantwortet_ids):
            geschuetzt.append({**b, "grund": grund})
            continue
        bewegungen.append(
            {
                **b,
                "message_id": m.get("message_id", ""),
                "datum": m.get("datum", ""),
            }
        )
    return {
        "bestand": len(bestand),
        "bewegungen": bewegungen,
        "geschuetzt": geschuetzt,
        "ausgelassen": ausgelassen,
        "restmenge": len(rest),
    }


# --- Postfach ---------------------------------------------------------------


def _kopf(roh: bytes) -> dict:
    from organize_mail import _decode

    msg = email.message_from_bytes(roh)
    mid = _MSGID.search(msg.get("Message-ID", "") or "")
    return {
        "absender": parseaddr(_decode(msg.get("From")))[1].lower(),
        "betreff": _decode(msg.get("Subject")),
        "datum": _decode(msg.get("Date")),
        "message_id": mid.group(0) if mid else "",
        "auto_submitted": msg.get("Auto-Submitted", ""),
        "list_id": msg.get("List-Id", ""),
        "list_unsubscribe": msg.get("List-Unsubscribe", ""),
        "precedence": msg.get("Precedence", ""),
    }


def _abrufen(imap: imaplib.IMAP4_SSL, uid_set: bytes, felder: str) -> list[tuple]:
    typ, data = imap.uid("FETCH", uid_set, f"(UID FLAGS BODY.PEEK[HEADER.FIELDS ({felder})])")
    if typ != "OK":
        raise RuntimeError(f"FETCH fehlgeschlagen: {data}")
    aus = []
    for teil in data:
        if not isinstance(teil, tuple):
            continue
        uid = _UID.search(teil[0])
        flags = _FLAGS.search(teil[0])
        if uid:
            aus.append((uid.group(1).decode(), flags.group(1) if flags else b"", teil[1]))
    return aus


def posteingang_lesen(imap: imaplib.IMAP4_SSL) -> list[dict]:
    from organize_mail import _mailbox_arg

    imap.select(_mailbox_arg(QUELLORDNER), readonly=True)
    typ, data = imap.uid("SEARCH", None, "ALL")
    uids = data[0].split() if typ == "OK" and data and data[0] else []
    if not uids:
        return []
    bestand = []
    for uid, flags, roh in _abrufen(imap, b",".join(uids), _KOEPFE):
        bestand.append(
            {
                "id": uid,
                "ordner": QUELLORDNER,
                "beantwortet": b"\\Answered" in flags,
                **_kopf(roh),
            }
        )
    return bestand


def beantwortete_ids(imap: imaplib.IMAP4_SSL, tage: int = SENDE_TAGE) -> set[str]:
    """Message-IDs, auf die eine gesendete Mail antwortet."""
    from organize_mail import _mailbox_arg

    typ, _ = imap.select(_mailbox_arg(SENDEORDNER), readonly=True)
    if typ != "OK":
        raise RuntimeError(f"Gesendet-Ordner '{SENDEORDNER}' nicht lesbar")
    seit = (datetime.now(timezone.utc) - timedelta(days=tage)).strftime("%d-%b-%Y")
    typ, data = imap.uid("SEARCH", None, "SINCE", seit)
    uids = data[0].split() if typ == "OK" and data and data[0] else []
    ids: set[str] = set()
    for i in range(0, len(uids), 500):
        for _, _, roh in _abrufen(imap, b",".join(uids[i : i + 500]), "IN-REPLY-TO REFERENCES"):
            msg = email.message_from_bytes(roh)
            for feld in ("In-Reply-To", "References"):
                ids.update(_MSGID.findall(msg.get(feld, "") or ""))
    return ids


def _ausfuehren(imap, konto: str, bewegungen: list[dict], lauf_id: str, protokoll: Path) -> int:
    from organize_mail import _move, list_folders

    vorhanden = set(list_folders(imap))
    je_ziel: dict[str, list[dict]] = defaultdict(list)
    for b in bewegungen:
        je_ziel[b["zielordner"]].append(b)
    bewegt = 0
    for ziel, gruppe in sorted(je_ziel.items()):
        if ziel not in vorhanden:
            print(f"  ! Zielordner '{ziel}' fehlt — {len(gruppe)} Mail(s) bleiben liegen.")
            continue
        _move(imap, gruppe[0]["quellordner"], ziel, [b["id"].encode() for b in gruppe])
        # Nach jedem Ordner protokollieren: bricht der Lauf ab, ist das bereits
        # Bewegte trotzdem rücknehmbar.
        regeln.protokollieren([{**b, "konto": konto} for b in gruppe], protokoll, lauf_id)
        bewegt += len(gruppe)
        print(f"  {len(gruppe):4d} → {ziel}")
    return bewegt


def zuruecknehmen(imap, eintraege: list[dict], apply: bool) -> tuple[int, int]:
    """Am Zielort über die Message-ID neu auflösen und zurückverschieben."""
    from organize_mail import _mailbox_arg, _move

    zurueck, fehlt = 0, 0
    je_ordner: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for e in eintraege:
        je_ordner[(e["quellordner"], e["zielordner"])].append(e)
    for (ort, heim), gruppe in sorted(je_ordner.items()):
        imap.select(_mailbox_arg(ort), readonly=not apply)
        uids = []
        for e in gruppe:
            mid = e.get("message_id")
            typ, data = imap.uid("SEARCH", None, "HEADER", "Message-ID", mid) if mid else ("NO", None)
            treffer = data[0].split() if typ == "OK" and data and data[0] else []
            if len(treffer) == 1:
                uids.append(treffer[0])
            else:
                fehlt += 1
                print(f"  ! nicht eindeutig in '{ort}': {e.get('betreff', '')[:60]}")
        if uids and apply:
            _move(imap, ort, heim, uids)
        zurueck += len(uids)
        print(f"  {len(uids):4d} {ort} → {heim}")
    return zurueck, fehlt


# --- CLI --------------------------------------------------------------------


def _bericht(ergebnis: dict, nur_vorschlaege: bool) -> None:
    b, g = ergebnis["bewegungen"], ergebnis["geschuetzt"]
    print(f"Posteingang: {ergebnis['bestand']} Mails")
    print(f"  verschieben: {len(b)}")
    for ziel, n in sorted(Counter(x["zielordner"] for x in b).items(), key=lambda kv: -kv[1]):
        print(f"    {n:4d}  {ziel}")
    print(f"  geschützt (Regel trifft, aber unbeantwortet): {len(g)}")
    if ergebnis["ausgelassen"]:
        print(f"  ausgelassen (Aktion ≠ verschieben): {len(ergebnis['ausgelassen'])}")
    print(f"  Restmenge (keine Regel trifft): {ergebnis['restmenge']}")
    if nur_vorschlaege:
        print("  Hinweis: gerechnet mit Vorschlägen als aktiv — nur Trockenlauf.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--account", required=True, help="Postfach-Kürzel → ~/.claude/mail-<NAME>.env")
    ap.add_argument("--apply", action="store_true", help="wirklich verschieben (sonst Trockenlauf)")
    ap.add_argument("--regeln", default=None, help="Regel-Datei (Default: ~/.claude/mail-regeln.json)")
    ap.add_argument("--protokoll", default=None, help="Default: ~/.claude/mail-regeln-protokoll.jsonl")
    ap.add_argument(
        "--mit-vorschlaegen",
        action="store_true",
        help="Vorschläge wie aktive Regeln rechnen — nur im Trockenlauf, zum Messen des Schutzes",
    )
    ap.add_argument("--ruecknahme", metavar="LAUF_ID", default=None)
    args = ap.parse_args()
    if args.mit_vorschlaegen and args.apply:
        ap.error("--mit-vorschlaegen wirkt nur im Trockenlauf; aktiviert wird per regeln.py aktivieren")

    from organize_mail import connect

    protokoll = Path(args.protokoll).expanduser() if args.protokoll else regeln.PROTOKOLL_DATEI
    imap, _ = connect(Path.home() / ".claude" / f"mail-{args.account}.env")
    try:
        if args.ruecknahme:
            eintraege = regeln.ruecknahme(protokoll, args.ruecknahme)
            zurueck, fehlt = zuruecknehmen(imap, eintraege, args.apply)
            modus = "zurückgeholt" if args.apply else "würden zurückgeholt (Trockenlauf)"
            print(f"{zurueck} {modus}, {fehlt} nicht auflösbar")
            return 1 if fehlt else 0

        alle = regeln.laden(args.regeln)
        if args.mit_vorschlaegen:
            for r in alle:
                if r.zustand == "vorschlag":
                    r.zustand = "aktiv"
        bestand = posteingang_lesen(imap)
        ergebnis = lauf_planen(alle, bestand, beantwortete_ids(imap))
        _bericht(ergebnis, args.mit_vorschlaegen)
        if not args.apply or not ergebnis["bewegungen"]:
            return 0
        lauf_id = f"ablage-{args.account}-{datetime.now().strftime('%Y%m%dT%H%M%S')}"
        bewegt = _ausfuehren(imap, args.account, ergebnis["bewegungen"], lauf_id, protokoll)
        print(f"OK: {bewegt} verschoben, lauf_id {lauf_id} (Rücknahme: --ruecknahme {lauf_id})")
        return 0
    finally:
        try:
            imap.logout()
        except (imaplib.IMAP4.error, OSError):
            pass


if __name__ == "__main__":
    sys.exit(main())
