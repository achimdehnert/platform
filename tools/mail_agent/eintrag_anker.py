#!/usr/bin/env python3
"""Jede Mail-Nummer aus dem Verlauf an ihre Message-ID binden — solange sie gilt.

Warum es das gibt: Gemessen am 2026-09-01 waren 89 von 203 Mail-Links auf den
Vorgangsseiten tot (platform#2563). Nicht, weil die Mails weg waren, sondern
weil der Link die IMAP-UID trug — und eine UID gilt nur in ihrem Ordner. Wer
ablegt, sendet oder einen Entwurf ersetzt, bekommt eine neue Nummer; die alte
zeigt ins Leere. Der Vorgangs-Anker (`anker.py`, `/a/<nr>`) loest das seit Juli
fuer die ERSTE Mail eines Strangs ueber die Message-ID. Dieses Werkzeug tut
dasselbe fuer jede Nummer, die ein Verlaufseintrag nennt.

Der Weg: `referenzen.finde` liest die Nummern aus dem Ledger (aktiv + gekappter
Verlauf), fuer jede noch nicht verankerte holt dieses Werkzeug die Message-ID aus
dem Postfach und legt sie unter `referenzen.schluessel` in derselben Ankerdatei
ab, die `anker.py` pflegt. Ab dann liefert der Mail-Dienst die Nummer als
`/a/<schluessel>` aus und zieht bei einem Ordnerwechsel selbst nach.

Was das Werkzeug bewusst NICHT tut:

* **Raten.** Eine Nummer ohne Ordner wird in `referenzen.SUCHORDNER` gesucht;
  liegt sie in ZWEI Ordnern, wird nichts verankert und der Fall gemeldet — eine
  UID bezeichnet in INBOX und Entwuerfen zwei verschiedene Nachrichten.
* **Nachtraeglich heilen.** Eine UID, die schon tot ist, hat keine Message-ID
  mehr, die sich lesen liesse. Sie bleibt unverankert und der Renderer zeigt sie
  als Text, nicht als Link. Der Wert dieses Werkzeugs liegt darin, dass es
  LAEUFT, bevor die Ablage die Nummer entwertet — darum steht es in der
  Abschluss-Checkliste von /mailcheck und im taeglichen Kettencheck.
* **Ins Postfach schreiben.** `select(readonly=True)` und `BODY.PEEK`, wie
  `anker.py`.

IIL-Vorgaenge laufen ueber Graph und haben keine IMAP-UIDs. Nennt ein solcher
Eintrag trotzdem eine Nummer, meint er ein HNU- oder AD-Postfach (so gemessen:
„INBOX #164222 (hnu)" in Vorgang 160). Darum werden diese Nummern in den
IMAP-Konten gesucht, und der Anker traegt das Konto, in dem die Mail liegt —
der SCHLUESSEL aber das Konto des Vorgangs, weil der Renderer nur das kennt.

Die Ankerdatei liegt unter ~/.claude, nie in einem Repo — sie traegt Betreffs
(Charta Art. 2).
"""

from __future__ import annotations

import argparse
import imaplib
import json
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from anker import (  # noqa: E402
    ANKER_DATEI,
    Anker,
    betreff_von_uid,
    lade,
    message_id_von_uid,
    speichere,
)
from mail_view import slugify  # noqa: E402
from read_mail import (  # noqa: E402
    _mailbox_arg,
    _resolve_config,
    alle_ordner,
    connect,
    ordner_klartext,
)
from referenzen import (  # noqa: E402
    LEDGER,
    SUCHORDNER,
    VERLAUF_ARCHIV,
    Referenz,
    finde,
    schluessel,
    schluessel_kandidaten,
    verlauf_eintraege,
)
from send_mail import parse_env  # noqa: E402

#: Vorgangs-Konto → IMAP-Konten, in denen seine Nummern liegen koennen. `default`
#: ist die namenlose mail.env (AD) — so heisst das Konto auch in den Ankern, die
#: `anker.py` bisher gesetzt hat. IIL hat kein IMAP; seine Nummern meinen HNU/AD.
IMAP_KONTEN: dict[str, tuple[str, ...]] = {
    "hnu": ("hnu",),
    "ad": ("default",),
    "default": ("default",),
    "iil": ("hnu", "default"),
}

NEU = "neu"
VORHANDEN = "vorhanden"
NICHT_GEFUNDEN = "nicht-gefunden"
MEHRDEUTIG = "mehrdeutig"
UNPRUEFBAR = "unpruefbar"


@dataclass(frozen=True)
class Fund:
    """Eine Referenz an ihrem Fundort im Ledger."""

    schluessel: str
    konto: str
    ref: Referenz
    nr: int | None
    eintrag: int


@dataclass
class Ergebnis:
    fund: Fund
    zustand: str
    anker: Anker | None = None
    hinweis: str = ""


def referenzen_im_ledger(ledger: dict, archiv: dict) -> dict[str, Fund]:
    """Schluessel → erster Fundort. Dieselbe Nummer in zwei Eintraegen ist EIN Anker."""
    funde: dict[str, Fund] = {}
    for v in ledger.get("vorgaenge", []):
        konto = str(v.get("konto") or "")
        if not konto:
            continue
        for i, text in enumerate(verlauf_eintraege(v, archiv), start=1):
            for ref in finde(text):
                key = schluessel(konto, ref.slug, ref.uid)
                funde.setdefault(key, Fund(key, konto, ref, v.get("nr"), i))
    return funde


def unverankert(funde: dict[str, Fund], anker: dict[str, Anker]) -> dict[str, Fund]:
    """Alle Funde, fuer die unter keinem Kandidaten-Schluessel ein Anker liegt."""
    return {
        key: fund
        for key, fund in funde.items()
        if not any(k in anker for k in schluessel_kandidaten(fund.konto, fund.ref))
    }


class Postfach:
    """Ein verbundenes IMAP-Konto mit seiner Ordnerkarte (Slug → Name)."""

    def __init__(self, konto: str, imap) -> None:
        self.konto = konto
        self.imap = imap
        namen, _ = alle_ordner(imap)
        self.nach_slug: dict[str, str] = {}
        for name in namen:
            self.nach_slug.setdefault(slugify(ordner_klartext(name)), name)

    def ordner_fuer(self, slug: str) -> str | None:
        """Slug → Ordnername; eindeutiger Anfang genuegt (wie im Mail-Dienst)."""
        if slug in self.nach_slug:
            return self.nach_slug[slug]
        anfang = [n for s, n in self.nach_slug.items() if s.startswith(slug)]
        return anfang[0] if len(anfang) == 1 else None

    def _hat_uid(self, name: str, uid: str) -> bool:
        try:
            typ, _ = self.imap.select(_mailbox_arg(name), readonly=True)
            if typ != "OK":
                return False
            typ, data = self.imap.uid("SEARCH", "UID", uid)
        except (imaplib.IMAP4.error, OSError):
            return False
        return typ == "OK" and bool(data and (data[0] or b"").split())

    def ordner_mit_uid(self, uid: str) -> list[str]:
        """Alle Suchordner, die diese UID fuehren — in der Reihenfolge von SUCHORDNER."""
        treffer: list[str] = []
        for slug in SUCHORDNER:
            name = self.nach_slug.get(slug)
            if name and self._hat_uid(name, uid):
                treffer.append(name)
        return treffer

    def message_id(self, name: str, uid: str) -> tuple[str, str]:
        """(message_id, betreff) der UID im Ordner — ('', '') wenn sie dort nicht liegt."""
        try:
            typ, _ = self.imap.select(_mailbox_arg(name), readonly=True)
            if typ != "OK":
                return "", ""
            mid = message_id_von_uid(self.imap, uid)
            return (mid, betreff_von_uid(self.imap, uid)) if mid else ("", "")
        except (imaplib.IMAP4.error, OSError):
            return "", ""


def verankere(fund: Fund, postfaecher: list[Postfach]) -> Ergebnis:
    """Einen Fund in den Postfaechern des Vorgangs-Kontos aufloesen."""
    ref = fund.ref
    for pf in postfaecher:
        if ref.slug:
            name = pf.ordner_fuer(ref.slug)
            if not name:
                continue
            kandidaten = [name]
        else:
            kandidaten = pf.ordner_mit_uid(ref.uid)
            if len(kandidaten) > 1:
                return Ergebnis(
                    fund,
                    MEHRDEUTIG,
                    hinweis=f"UID {ref.uid} liegt in {len(kandidaten)} Ordnern "
                    f"({', '.join(ordner_klartext(k) for k in kandidaten)}) — "
                    "im Eintrag den Ordner nennen",
                )
        for name in kandidaten:
            mid, betreff = pf.message_id(name, ref.uid)
            if mid:
                return Ergebnis(
                    fund,
                    NEU,
                    Anker(
                        item=fund.schluessel,
                        konto=pf.konto,
                        ordner=name,
                        uid=ref.uid,
                        message_id=mid,
                        betreff=betreff,
                    ),
                )
    return Ergebnis(
        fund,
        NICHT_GEFUNDEN,
        hinweis="UID in keinem Suchordner — verschoben, gesendet oder ersetzt, "
        "bevor sie verankert wurde",
    )


def _verbinde(konto: str):
    return connect(
        parse_env(_resolve_config(None, None if konto == "default" else konto))
    )


def verankere_alle(
    funde: dict[str, Fund],
    anker: dict[str, Anker],
    verbinde=None,
) -> list[Ergebnis]:
    """Alle unverankerten Funde aufloesen; ein Konto wird einmal verbunden."""
    # Zur Laufzeit aufgeloest, nicht als Default gebunden — sonst liesse sich
    # die Verbindung im Test nicht ersetzen (dieselbe Falle wie in kettencheck).
    verbinde = verbinde or _verbinde
    offen = unverankert(funde, anker)
    ergebnisse: list[Ergebnis] = [
        Ergebnis(f, VORHANDEN) for k, f in funde.items() if k not in offen
    ]
    verbindungen: dict[str, Postfach | None] = {}

    def postfach(konto: str) -> Postfach | None:
        if konto not in verbindungen:
            try:
                verbindungen[konto] = Postfach(konto, verbinde(konto))
            except Exception as fehler:  # Netz/Login — melden, nicht raten
                print(f"  Konto '{konto}' nicht erreichbar: {fehler}", file=sys.stderr)
                verbindungen[konto] = None
        return verbindungen[konto]

    try:
        for fund in offen.values():
            konten = IMAP_KONTEN.get(fund.konto, (fund.konto,))
            postfaecher = [pf for k in konten if (pf := postfach(k)) is not None]
            if not postfaecher:
                ergebnisse.append(
                    Ergebnis(
                        fund,
                        UNPRUEFBAR,
                        hinweis=f"kein erreichbares IMAP-Konto fuer '{fund.konto}'",
                    )
                )
                continue
            ergebnisse.append(verankere(fund, postfaecher))
    finally:
        for pf in verbindungen.values():
            if pf is not None:
                try:
                    pf.imap.logout()
                except Exception:
                    pass
    return ergebnisse


def uebernehme(ergebnisse: list[Ergebnis], anker: dict[str, Anker]) -> int:
    """Neue Anker eintragen. Rueckgabe: wie viele."""
    neu = [e for e in ergebnisse if e.zustand == NEU and e.anker is not None]
    for e in neu:
        anker[e.anker.item] = e.anker
    return len(neu)


def bericht(ergebnisse: list[Ergebnis]) -> str:
    zaehler = {z: 0 for z in (NEU, VORHANDEN, NICHT_GEFUNDEN, MEHRDEUTIG, UNPRUEFBAR)}
    for e in ergebnisse:
        zaehler[e.zustand] = zaehler.get(e.zustand, 0) + 1
    zeilen = [
        f"{len(ergebnisse)} Referenzen: {zaehler[NEU]} neu verankert, "
        f"{zaehler[VORHANDEN]} bereits verankert, {zaehler[NICHT_GEFUNDEN]} nicht "
        f"gefunden, {zaehler[MEHRDEUTIG]} mehrdeutig, {zaehler[UNPRUEFBAR]} unpruefbar"
    ]
    for e in ergebnisse:
        if e.zustand == NEU and e.anker:
            zeilen.append(
                f"  + {e.fund.schluessel:<32} #{e.fund.nr}-{e.fund.eintrag}  "
                f"{ordner_klartext(e.anker.ordner)}  {e.anker.betreff[:50]}"
            )
    for e in ergebnisse:
        if e.zustand in (NICHT_GEFUNDEN, MEHRDEUTIG, UNPRUEFBAR):
            zeilen.append(
                f"  - {e.fund.schluessel:<32} #{e.fund.nr}-{e.fund.eintrag}  "
                f"{e.zustand}: {e.hinweis}"
            )
    return "\n".join(zeilen)


def _lade_json(pfad: Path) -> dict:
    try:
        daten = json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return daten if isinstance(daten, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--ledger", default=str(LEDGER))
    ap.add_argument("--verlauf-archiv", default=str(VERLAUF_ARCHIV))
    ap.add_argument("--anker", default=str(ANKER_DATEI))
    ap.add_argument(
        "--trocken",
        action="store_true",
        help="nur berichten, Ankerdatei nicht schreiben",
    )
    ap.add_argument(
        "--nur-zaehlen",
        action="store_true",
        help="ohne Postfach: wie viele Referenzen sind (un)verankert",
    )
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    ledger = _lade_json(Path(args.ledger))
    archiv = _lade_json(Path(args.verlauf_archiv))
    anker = lade(Path(args.anker))
    funde = referenzen_im_ledger(ledger, archiv)

    if args.nur_zaehlen:
        offen = unverankert(funde, anker)
        print(f"{len(funde)} Referenzen, {len(offen)} ohne Anker")
        return 0

    ergebnisse = verankere_alle(funde, anker)
    if args.json:
        print(
            json.dumps(
                [
                    {
                        "schluessel": e.fund.schluessel,
                        "vorgang": e.fund.nr,
                        "eintrag": e.fund.eintrag,
                        "zustand": e.zustand,
                        "hinweis": e.hinweis,
                    }
                    for e in ergebnisse
                ],
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(bericht(ergebnisse))
    if not args.trocken:
        n = uebernehme(ergebnisse, anker)
        if n:
            speichere(anker, Path(args.anker))
            print(f"Geschrieben: {n} neue Anker → {Path(args.anker).name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
