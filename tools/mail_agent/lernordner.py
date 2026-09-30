#!/usr/bin/env python3
"""Lernordner: der Owner zieht eine Mail hinein, das Werkzeug lernt die Löschregel.

Zielzustand: platform#3629 (K1–K5), abgestimmt am 2026-09-30.

Zwei Ordner je Postfach (IIL über Graph, HNU und AD über IMAP):

* ``Lernen Absender loeschen`` — die Absenderadresse wird zur Regel.
* ``Lernen Domain loeschen``   — die Domain wird zur Regel (alle Adressen,
  Subdomains eingeschlossen). Eigene Domains, die Hochschul-Domain und
  Freemail-Domains werden abgewiesen: dort schreiben Menschen.

Ein Lauf mit ``--apply`` macht drei Dinge:

1. **Lernen** — jeder neue Eintrag landet in ``rausch_regeln.nach_ordner_zur_loeschung``
   und mit Datum, Konto und Typ in ``rausch_regeln.owner_gelernt``. Der Zug in den
   Ordner IST das Owner-Wort; niemand muss ihn noch einmal bestätigen.
2. **Ordner leeren** — die gezogenen Mails gehen in den Löschordner. Der Löschschutz
   gilt weiter: Belege und eigene Adressen bleiben geschützt und wandern zurück in
   den Posteingang. Die Gesendet-Historie übersteuert der Owner-Zug
   (siehe ``loeschschutz`` „Owner-Übersteuerung").
3. **Anwenden** — Mails gelernter Absender im Posteingang gehen ebenfalls in den
   Löschordner. So wirkt die Regel bei jedem ``/mailcheck`` auf neue Post.

Ohne ``--apply`` ist es ein Trockenlauf: nichts wird geschrieben oder verschoben.
Verschoben wird nur, nie gelöscht — der Owner leert „Zur Loeschung" selbst.

**Rücknahme.** Den Eintrag aus beiden Ledger-Listen entfernen und die Mails aus
dem Löschordner zurückziehen. Ein Werkzeug dafür gibt es bewusst nicht, solange
der Bedarf nicht belegt ist (Refs #3629).

    python3 tools/mail_agent/lernordner.py --anlegen          # Ordner in allen Konten
    python3 tools/mail_agent/lernordner.py                    # Trockenlauf
    python3 tools/mail_agent/lernordner.py --apply            # lernen + verschieben
    python3 tools/mail_agent/lernordner.py --konto iil --apply
"""

from __future__ import annotations

import argparse
import datetime as dt
import imaplib
import json
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))

import loeschschutz  # noqa: E402

KONTEN = ("iil", "hnu", "ad")

#: Typ → Ordnername. ASCII, damit keine IMAP-UTF-7-Kodierung im Spiel ist.
LERNORDNER = {
    "absender": "Lernen Absender loeschen",
    "domain": "Lernen Domain loeschen",
}

#: AD legt eigene Ordner unter INBOX an (vgl. Ledger ``zielordner_2026_08_07``).
PRAEFIX = {"iil": "", "hnu": "", "ad": "INBOX."}

#: Löschordner je Konto, wie am 2026-08-07 angelegt (``zielordner_2026_08_07``).
LOESCHORDNER = {
    "iil": "Zur Löschung",
    "hnu": "Zur Loeschung",
    "ad": "INBOX.Zur Loeschung",
}

#: Posteingang je Konto — Graph kennt den Namen ``inbox`` als festen Ordner.
POSTEINGANG = {"iil": "inbox", "hnu": "INBOX", "ad": "INBOX"}

#: Bereits im Repo (``rausch_kandidaten.EIGENE_DOMAENEN``): dort schreiben
#: Kollegen und System-Absender, eine Domain-Regel träfe alle.
HOCHSCHUL_DOMAENEN = ("hnu.de",)

#: Domains, die nie als Ganzes gelernt werden.
DOMAIN_GESPERRT = (
    loeschschutz.EIGENE_KONTO_DOMAENEN
    + HOCHSCHUL_DOMAENEN
    + loeschschutz.FREEMAIL_DOMAENEN
)

QUELLE = "lernordner.py"


def lernordner_pfad(konto: str, typ: str) -> str:
    return PRAEFIX[konto] + LERNORDNER[typ]


# ---------- Rechnung (ohne Postfach prüfbar) ----------


def eintrag_fuer(typ: str, absender: str, eigene: set[str]) -> tuple[str | None, str]:
    """(Regel-Eintrag, Grund). Ohne Eintrag erklärt der Grund die Abweisung."""
    adresse = loeschschutz.adresse_von(absender)
    if not adresse or "@" not in adresse:
        return None, "Absenderadresse nicht lesbar"
    if loeschschutz.ist_eigene_adresse(adresse, eigene):
        return None, "eigene Adresse"
    if typ == "absender":
        return adresse, ""
    domain = adresse.rsplit("@", 1)[1]
    if any(domain == d or domain.endswith("." + d) for d in DOMAIN_GESPERRT):
        return None, f"Domain {domain} wird nie als Ganzes gelernt"
    return domain, ""


def ledger_ergaenzen(
    ledger: dict, lernungen: list[tuple[str, str, str]], heute: str
) -> list[str]:
    """Neue Einträge in Regel- und Owner-Liste; gibt die neu gelernten zurück.

    ``lernungen`` sind ``(eintrag, typ, konto)``. Steht ein Eintrag schon in der
    Regel, aber nicht als Owner-Eintrag, wird er Owner-Eintrag — der Zug ist
    auch dann eine Entscheidung (er übersteuert die Gesendet-Historie).
    """
    regeln = ledger.setdefault("rausch_regeln", {})
    liste = regeln.setdefault("nach_ordner_zur_loeschung", [])
    gelernt = regeln.setdefault(loeschschutz.GELERNT_SCHLUESSEL, [])
    in_liste = {e.lower() for e in liste if isinstance(e, str)}
    im_owner = {z.get("eintrag", "").lower() for z in gelernt if isinstance(z, dict)}
    neu: list[str] = []
    for eintrag, typ, konto in lernungen:
        if eintrag in im_owner:
            continue
        if eintrag not in in_liste:
            liste.append(eintrag)
            in_liste.add(eintrag)
        gelernt.append(
            {
                "eintrag": eintrag,
                "typ": typ,
                "konto": konto,
                "am": heute,
                "quelle": QUELLE,
            }
        )
        im_owner.add(eintrag)
        neu.append(eintrag)
    return neu


def gelernte_treffer(hits: list[tuple], gelernt: list[str]) -> list[tuple]:
    """Die Posteingangs-Mails, deren Absender ein gelernter Eintrag trifft."""
    return [
        h
        for h in hits
        if any(
            loeschschutz.trifft_eintrag(loeschschutz.adresse_von(h[2]), e)
            for e in gelernt
        )
    ]


# ---------- Postfächer ----------


class KontoNichtErreichbar(Exception):
    pass


class GraphPostfach:
    """IIL über Microsoft Graph — dieselben Wege wie ``graph_mail --move``."""

    def __init__(self) -> None:
        import graph_mail  # noqa: PLC0415

        self.gm = graph_mail
        cfg = graph_mail.load_cfg()
        konten = cfg.get("accounts") or []
        if not konten:
            raise KontoNichtErreichbar("kein Graph-Konto konfiguriert")
        self.tok = graph_mail.token(cfg, konten[0])
        if not self.tok:
            raise KontoNichtErreichbar(f"{konten[0]} nicht für Mail angemeldet")

    def ordner(self) -> list[str]:
        return [f["path"] for f in self.gm._folders(self.tok)]

    def anlegen(self, pfad: str) -> None:
        self.gm.ensure_path(self.tok, pfad)

    def liste(self, pfad: str) -> list[tuple]:
        return self.gm._find_messages(self.tok, "", pfad)

    def verschiebe(self, _quelle: str, ziel: str, kennungen: list) -> int:
        ziel_id = "inbox" if ziel == "inbox" else self.gm.ensure_path(self.tok, ziel)
        bewegt = 0
        for mid in kennungen:
            r = self.gm._http(
                "POST",
                f"{self.gm._basis()}/messages/{mid}/move",
                headers=self.gm._auth(self.tok),
                json_body={"destinationId": ziel_id},
            )
            if r.status_code in (200, 201):
                bewegt += 1
            else:
                print(
                    f"  ! Fehler bei einer Mail: HTTP {r.status_code}", file=sys.stderr
                )
        return bewegt

    def schliessen(self) -> None:
        pass


class ImapPostfach:
    """HNU/AD über IMAP — dieselben Wege wie ``organize_mail --move``."""

    def __init__(self, konto: str) -> None:
        import organize_mail  # noqa: PLC0415

        self.om = organize_mail
        self.imap, _ = organize_mail.connect(
            Path.home() / ".claude" / f"mail-{konto}.env"
        )

    def ordner(self) -> list[str]:
        from read_mail import ordner_klartext  # noqa: PLC0415

        return [ordner_klartext(n) for n in self.om.list_folders(self.imap)]

    def anlegen(self, pfad: str) -> None:
        self.om.cmd_create_folder(self.imap, pfad)

    def liste(self, pfad: str) -> list[tuple]:
        return self.om._matches(self.imap, pfad, None, None)

    def verschiebe(self, quelle: str, ziel: str, kennungen: list) -> int:
        if kennungen:
            self.om._move(self.imap, quelle, ziel, list(kennungen))
        return len(kennungen)

    def schliessen(self) -> None:
        try:
            self.imap.logout()
        except (OSError, imaplib.IMAP4.error):
            pass


def oeffne(konto: str):
    """Postfach öffnen. ``SystemExit`` wird mitgefangen: ``organize_mail.connect``
    beendet bei fehlender Konfiguration den Prozess statt zu werfen (vgl.
    ``ablage_erledigt.ordner_je_konto_live``)."""
    try:
        return GraphPostfach() if konto == "iil" else ImapPostfach(konto)
    except (
        KontoNichtErreichbar,
        OSError,
        imaplib.IMAP4.error,
        KeyError,
        ValueError,
        SystemExit,
    ) as fehler:
        raise KontoNichtErreichbar(str(fehler)[:160] or type(fehler).__name__)


# ---------- Ablauf ----------


def _zeile(h: tuple) -> str:
    return f"{str(h[1])[:16]:<16}  {h[2][:40]:<40} {(h[3] or '')[:50]}"


def lernordner_lesen(konto: str, postfach, eigene: set[str]):
    """(Lernungen, angenommene Treffer je Quellordner, abgewiesene Treffer je Quellordner)."""
    vorhanden = set(postfach.ordner())
    lernungen: list[tuple[str, str, str]] = []
    angenommen: dict[str, list[tuple]] = {}
    abgewiesen: dict[str, list[tuple]] = {}
    for typ in LERNORDNER:
        pfad = lernordner_pfad(konto, typ)
        if pfad not in vorhanden:
            print(f"  {konto}: Ordner '{pfad}' fehlt — erst --anlegen")
            continue
        for h in postfach.liste(pfad):
            eintrag, grund = eintrag_fuer(typ, h[2], eigene)
            if eintrag:
                lernungen.append((eintrag, typ, konto))
                angenommen.setdefault(pfad, []).append(h)
                print(f"  {konto}: lerne {typ:<8} {eintrag:<34} ← {_zeile(h)}")
            else:
                abgewiesen.setdefault(pfad, []).append(h)
                print(f"  {konto}: abgewiesen ({grund}) ← {_zeile(h)}")
    return lernungen, angenommen, abgewiesen


def in_loeschordner(
    konto: str,
    postfach,
    quelle: str,
    hits: list[tuple],
    gelernt: list[str],
    apply: bool,
) -> tuple[int, list[tuple]]:
    """Durch den Löschschutz in den Löschordner. Rückgabe: (bewegt, gehaltene Treffer)."""
    if not hits:
        return 0, []
    ziel = LOESCHORDNER[konto]
    frei, gehalten = loeschschutz.filtere_verschiebung(ziel, hits, gelernt=gelernt)
    loeschschutz.melde_zurueckgehalten(gehalten)
    for h in frei:
        print(f"  {konto}: → {ziel}  {_zeile(h)}")
    bewegt = postfach.verschiebe(quelle, ziel, [h[0] for h in frei]) if apply else 0
    return bewegt, [h for h, _ in gehalten]


def lauf(
    konten: list[str], *, apply: bool, oeffnen=oeffne, ledger_pfad: Path | None = None
):
    """Ein Lauf über alle Konten. Gibt eine Bilanz je Konto zurück."""
    ledger_pfad = ledger_pfad or loeschschutz.LEDGER
    eigene = loeschschutz.eigene_adressen()
    offen: dict[str, object] = {}
    bilanz: dict[str, dict] = {}
    gelesen: dict[str, tuple] = {}
    for konto in konten:
        try:
            offen[konto] = oeffnen(konto)
        except KontoNichtErreichbar as fehler:
            bilanz[konto] = {"nicht_erreichbar": str(fehler)}
            print(f"  {konto}: nicht erreichbar — {fehler}")
            continue
        gelesen[konto] = lernordner_lesen(konto, offen[konto], eigene)

    try:
        ledger = json.loads(ledger_pfad.read_text(encoding="utf-8"))
    except (OSError, ValueError) as fehler:
        sys.exit(
            f"FEHLER: Ledger nicht lesbar ({fehler}) — nichts gelernt, nichts verschoben."
        )
    lernungen = [ln for lg, _, _ in gelesen.values() for ln in lg]
    neu = ledger_ergaenzen(ledger, lernungen, dt.date.today().isoformat())
    if neu and apply:
        ledger_pfad.write_text(
            json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(
        f"Gelernt: {len(neu)} neue Einträge"
        + ("" if apply or not neu else " (Trockenlauf — nicht gespeichert)")
    )
    gelernt = [
        z["eintrag"]
        for z in ledger["rausch_regeln"].get(loeschschutz.GELERNT_SCHLUESSEL, [])
    ]

    for konto, postfach in offen.items():
        _, angenommen, abgewiesen = gelesen[konto]
        b = bilanz.setdefault(konto, {"geloescht": 0, "zurueck": 0, "posteingang": 0})
        try:
            for quelle, hits in angenommen.items():
                bewegt, gehalten = in_loeschordner(
                    konto, postfach, quelle, hits, gelernt, apply
                )
                b["geloescht"] += bewegt
                zurueck = gehalten + abgewiesen.pop(quelle, [])
                if zurueck and apply:
                    b["zurueck"] += postfach.verschiebe(
                        quelle, POSTEINGANG[konto], [h[0] for h in zurueck]
                    )
            for quelle, hits in abgewiesen.items():
                if apply:
                    b["zurueck"] += postfach.verschiebe(
                        quelle, POSTEINGANG[konto], [h[0] for h in hits]
                    )
            eingang = gelernte_treffer(postfach.liste(POSTEINGANG[konto]), gelernt)
            bewegt, _ = in_loeschordner(
                konto, postfach, POSTEINGANG[konto], eingang, gelernt, apply
            )
            b["posteingang"] += bewegt
        except RuntimeError as fehler:
            # Löschschutz nicht prüfbar (Index weg): fail-closed für dieses Konto.
            b["fehler"] = (
                f"Löschschutz nicht prüfbar ({fehler}) — nichts in den Löschordner"
            )
            print(f"  {konto}: {b['fehler']}")
        finally:
            postfach.schliessen()
    return bilanz


def anlegen(konten: list[str], oeffnen=oeffne) -> None:
    for konto in konten:
        try:
            postfach = oeffnen(konto)
        except KontoNichtErreichbar as fehler:
            print(f"  {konto}: nicht erreichbar — {fehler}")
            continue
        try:
            vorhanden = set(postfach.ordner())
            for typ in LERNORDNER:
                pfad = lernordner_pfad(konto, typ)
                if pfad in vorhanden:
                    print(f"  {konto}: '{pfad}' existiert")
                else:
                    postfach.anlegen(pfad)
                    print(f"  {konto}: '{pfad}' angelegt")
        finally:
            postfach.schliessen()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--anlegen", action="store_true", help="Lernordner anlegen")
    ap.add_argument("--apply", action="store_true", help="lernen und verschieben")
    ap.add_argument(
        "--konto", action="append", choices=KONTEN, help="nur dieses Konto (mehrfach)"
    )
    args = ap.parse_args()
    konten = args.konto or list(KONTEN)
    if args.anlegen:
        anlegen(konten)
        return
    bilanz = lauf(konten, apply=args.apply)
    modus = "" if args.apply else " (Trockenlauf)"
    for konto, b in bilanz.items():
        print(f"Bilanz {konto}{modus}: {json.dumps(b, ensure_ascii=False)}")


if __name__ == "__main__":
    main()
