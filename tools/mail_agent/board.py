#!/usr/bin/env python3
"""Das Mail-Action-Board aus dem Vorgangs-Ledger erzeugen — statt es zu pflegen.

Warum es das gibt: Drei lokale Dateien beschrieben denselben Sachverhalt und
liefen auseinander. Am 2026-08-10 gemessen:

    mail-vorgaenge.json   17 Vorgaenge, Stand 10.08.  (aktuell, aber ohne Nummer
                                                       und ohne Mail-Bezug)
    mail-anker.json        8 Anker,     Stand 30.07.  (Mail-Bezug, Schluessel ist
                                                       die Board-Nummer)
    mail-action-board.md   ~15 Posten,  Stand 31.07.  (Ansicht, von Hand gepflegt)

Der Ledger ist die einzige Datei, die jemand aktuell haelt — und ausgerechnet er
kann nicht angezeigt werden, weil ihm die beiden Felder fehlen, ueber die Ansicht
und Mail-Bezug zusammenfinden. Deshalb wandert die Nummer IN den Ledger, und die
Ansicht wird gerendert statt getippt. Eine von Hand gefuehrte Zweitschrift laeuft
weg; eine gerenderte kann es nicht.

Drei Zusagen an den Leser des Boards:

**Die Nummer ist stabil und wird nie wiederverwendet.** Sie ist die Anrede: „7 go"
muss morgen denselben Vorgang meinen wie heute. Die alte Pflege-Regel („die Liste
wird lueckenlos neu durchgezaehlt") widersprach dem und ist damit aufgehoben —
Luecken sind der Preis der Stabilitaet und ausdruecklich gewollt.

**Jeder Posten traegt einen Link in seine Mail**, und zwar ueber `/a/<nr>`, das
ueber die Message-ID aufloest und ein Verschieben ueberlebt. Der Linktext ist der
naechste Zug, nie Absender oder Betreff.

**Jeder Posten schlaegt naheliegende Aktionen vor**, abgeleitet aus `typ` und
`bucket` des Ledgers. Sie sind adressierbar (`7a`, `7b`), damit eine Anweisung
kurz sein kann. Kein Vorschlag sendet etwas: nach aussen entsteht immer erst ein
Entwurf, den ein Mensch abschickt.

Der Board-Inhalt bleibt lokal (Adressen, Betreffe — Charta Art. 2). In diesem
Repo liegt nur die Mechanik, nie eine Zeile Inhalt.

Kommandos:
  --pruefe            Invarianten pruefen (Exit 1 bei Verstoss)
  --vergib-nummern    fehlende Nummern vergeben (schreibt den Ledger)
  --render            Board erzeugen (stdout, mit --nach in die Board-Datei)
  --aktionen [TYP]    Aktionskatalog zeigen
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

TOOL_VERSION = "board.py/1"

#: Alle vier Dateien liegen unter ~/.claude, nie in einem Repo (Charta Art. 2).
LEDGER = Path.home() / ".claude" / "mail-vorgaenge.json"
ANKER = Path.home() / ".claude" / "mail-anker.json"
LINKS = Path.home() / ".claude" / "mail-links.json"
BOARD = Path.home() / ".claude" / "mail-action-board.md"

#: Die gewachsenen Pflege-Regeln des Boards. Sie stehen bewusst NICHT in diesem
#: Repo: mehrere von ihnen nennen den Realfall, an dem sie entstanden sind, und
#: damit Namen (Charta Art. 2). Rendern wuerde sie ohne diesen Anhang stillschweigend
#: ueberschreiben — Regeln, die ihre eigene Herkunft tragen, gehen so am leichtesten
#: verloren. Fehlt die Datei, faellt nichts aus; sie ist ein Anhang, keine Bedingung.
REGELN = Path.home() / ".claude" / "mail-board-regeln.md"

#: Der Link-Dienst haengt hinter Cloudflare Access und ist damit geraeteunabhaengig.
#: `/a/<nr>` loest ueber die Message-ID auf: ein Ordnerwechsel bricht ihn nicht.
LINK_BASIS = "https://mail.iil.pet"

#: Ledger-Bucket -> Abschnitt im Board. Die Reihenfolge ist die Anzeige-Reihenfolge.
BUCKETS: list[tuple[str, str]] = [
    ("owner", "🟢 Offen — dein Zug"),
    ("agent", "🔵 Offen — ich kann sofort"),
    ("warten", "🟡 Wartend — Ball liegt aussen"),
    ("erledigt", "✅ Erledigt"),
]

#: Wie lange ein geschlossener Vorgang im Board sichtbar bleibt.
#:
#: Warum es diesen Zustand ueberhaupt gibt: Bis 2026-08-18 kannte der Ledger nur
#: `owner`, `agent` und `warten`. Ein geschlossener Vorgang wurde deshalb **aus der
#: Datei entfernt** — obwohl der Mailcheck-Skill seit jeher einen Abschnitt
#: „✅ Erledigt seit letztem Check" vorsieht und `AKTIONEN_IMMER` die Aktion
#: „Erledigt — Vorgang schliessen" anbietet. Es gab die Aktion, aber kein Ziel.
#:
#: Das Loeschen kostet zweierlei: Man sieht nicht, was fertig wurde, und jede
#: Nachlogik, die am Abschluss haengt (z. B. die zugehoerigen Mails aus dem
#: Posteingang raeumen), verliert mit dem Posten auch ihren Ausloeser.
#:
#: Sichtbar bleiben heisst nicht ewig: Nach diesem Fenster zaehlt das Board sie nur
#: noch, statt sie zu zeigen. Der Eintrag selbst bleibt in der Datei — er traegt den
#: Anker, ueber den die Mails spaeter auffindbar sind.
ERLEDIGT_FENSTER_TAGE = 14

#: Naheliegende Aktionen je Vorgangstyp.
#:
#: Regel ueber allen Eintraegen: **nichts geht raus.** Jede Aktion nach aussen
#: erzeugt einen Entwurf; gesendet wird von Hand (Draft-first-Standard). Wo eine
#: Aktion eine Freigabe braucht, steht das im Text und nicht im Kleingedruckten.
AKTIONEN_JE_TYP: dict[str, list[tuple[str, str]]] = {
    "termin": [
        ("a", "Terminvorschlag entwerfen"),
        ("b", "Zusage entwerfen"),
        ("c", "Absage entwerfen"),
    ],
    "betreuung-masterarbeit": [
        ("a", "Anhang lesen, Feedback entwerfen"),
        ("b", "Zwischenstand-Rueckmeldung entwerfen"),
        ("c", "Abgabefrist bestaetigen"),
    ],
    "lehre": [
        ("a", "Stellungnahme entwerfen"),
        ("b", "Terminvorschlag entwerfen"),
    ],
    "dsb-beratung": [
        ("a", "Fachliche Antwort entwerfen"),
        ("b", "Rueckfragen buendeln"),
        ("c", "Unterlage pruefen"),
    ],
    "dsgvo-loeschung": [
        ("a", "Vollzug beim Verantwortlichen nachfragen"),
        ("b", "Loeschbestaetigung entwerfen"),
        # Dreistufig und ohne Vorgriff: erst Auftrag, dann Vollzugsmeldung,
        # dann Bestaetigung. Keine Stufe vorwegnehmen.
    ],
    "av-pruefung": [
        ("a", "Unterlage pruefen, Befund entwerfen"),
        ("b", "Nachforderung entwerfen"),
    ],
    "ausschreibung": [
        ("a", "Angebot vorbereiten"),
        ("b", "Absage entwerfen"),
        ("c", "Frist im Kalender sichern"),
    ],
    "geschaeftsanbahnung": [
        ("a", "Grobschaetzung entwerfen"),
        ("b", "Terminvorschlag entwerfen"),
        ("c", "Zwischennachricht entwerfen"),
    ],
    "foerderung": [
        ("a", "Antwort entwerfen"),
        ("b", "Unterlagen zusammenstellen"),
    ],
    "referenz": [
        ("a", "Zusage entwerfen"),
        ("b", "Ablehnung entwerfen"),
    ],
    "formalie": [
        ("a", "Formular ausfuellen, Entwurf zur Unterschrift"),
        ("b", "Rueckfrage entwerfen"),
    ],
    "todo-edv-beratung": [
        # Buchen erst nach ausdruecklicher Freigabe des Owners — der Entwurf ist
        # das Ende meines Wegs, nicht der Beleg.
        ("a", "sevdesk-Beleg-ENTWURF anlegen (nicht buchen)"),
        ("b", "Rechnung nach Paperless uebertragen"),
    ],
    "todo-privat": [
        ("a", "Nur zur Kenntnis — deine Entscheidung"),
    ],
    "vorgang": [
        ("a", "Antwort entwerfen"),
        ("b", "Sachstand zusammenstellen"),
    ],
}

#: Wartet der Ball aussen, sind andere Aktionen naheliegend als beim eigenen Zug.
AKTIONEN_WARTEN: list[tuple[str, str]] = [
    ("n", "Nachfassen entwerfen"),
    ("f", "Frist verlaengern"),
]

#: Haengt an jedem offenen Posten, unabhaengig vom Typ.
AKTIONEN_IMMER: list[tuple[str, str]] = [
    ("z", "Erledigt — Vorgang schliessen"),
]

#: Ein geschlossener Vorgang bekommt genau eine Aktion: die Ruecknahme. Ihm
#: „Nachfassen entwerfen" anzubieten waere sinnlos, „Erledigt schliessen" absurd.
AKTIONEN_ERLEDIGT: list[tuple[str, str]] = [
    ("o", "Wieder oeffnen — Bucket zuruecksetzen"),
]

#: Greift, wenn ein Typ (noch) nicht im Katalog steht. Bewusst nicht leer: ein
#: Posten ohne Aktion waere ein Posten, den man nur anschauen kann.
AKTIONEN_FALLBACK: list[tuple[str, str]] = [
    ("a", "Antwort entwerfen"),
    ("b", "Sachstand zusammenstellen"),
]


def lade(pfad: Path, standard: Any) -> Any:
    """JSON lesen; fehlende Datei ist kein Fehler, leere/kaputte schon."""
    if not pfad.exists():
        return standard
    try:
        return json.loads(pfad.read_text(encoding="utf-8"))
    except json.JSONDecodeError as fehler:
        raise SystemExit(f"FEHLER: {pfad} ist kein gueltiges JSON — {fehler}")


def vorgaenge_von(ledger: dict) -> list[dict]:
    return ledger.get("vorgaenge") or []


def aktionen_fuer(vorgang: dict) -> list[tuple[str, str]]:
    """Naheliegende Aktionen aus Typ und Bucket ableiten.

    Der Typ bestimmt die inhaltlichen Aktionen, der Bucket die verfahrens-
    maessigen. Ein wartender Vorgang bekommt zusaetzlich das Nachfassen — bei
    einem eigenen Zug waere das sinnlos.
    """
    if vorgang.get("bucket") == "erledigt":
        return list(AKTIONEN_ERLEDIGT)
    typ = (vorgang.get("typ") or "").strip()
    aktionen = list(AKTIONEN_JE_TYP.get(typ, AKTIONEN_FALLBACK))
    if vorgang.get("bucket") == "warten":
        aktionen += AKTIONEN_WARTEN
    return aktionen + AKTIONEN_IMMER


def anker_zustand(nr: int, anker: dict, links: dict) -> str:
    """IMAP-Anker, Graph-Kurz-ID oder gar nichts — als Wort, nicht als Bool.

    Beide Speicher sind ueber die Board-Nummer verschluesselt; `/a/<nr>` bedient
    sich aus dem einen, `/i/<nr>` aus dem anderen. Fehlt beides, ist der Posten
    nicht anklickbar — das ist ein Befund, kein Schoenheitsfehler.
    """
    schluessel = str(nr)
    if schluessel in anker:
        return "imap"
    if schluessel in links:
        return "graph"
    return "fehlt"


def link_fuer(nr: int, zustand: str) -> str | None:
    """Eine Linkform fuer alle Konten: `/a/<nr>`.

    Der Dienst loest sie fuer IMAP ueber die Message-ID auf und faellt fuer
    Graph-Konten auf die Kurz-ID-Registry zurueck. Zwei Linkformen im Board
    waeren eine Unterscheidung, die den Leser nichts angeht.
    """
    if zustand == "fehlt":
        return None
    return f"{LINK_BASIS}/a/{nr}"


def vergib_nummern(ledger: dict) -> tuple[dict, list[tuple[int, str]]]:
    """Fehlende Nummern vergeben, ohne je eine zu wiederholen.

    Der Zaehler `naechste_nr` steht im Ledger und geht nur nach oben. Er wird aus
    dem Bestand hochgezogen (auch aus Ankern, die aus der Zeit vor dem Ledger
    stammen), damit eine bereits vergebene Nummer nicht ein zweites Mal an einen
    anderen Vorgang faellt.
    """
    posten = vorgaenge_von(ledger)
    vergeben = {v["nr"] for v in posten if isinstance(v.get("nr"), int)}
    anker = lade(ANKER, {})
    links = lade(LINKS, {})
    historisch = {
        int(k)
        for k in list(anker.keys()) + list(links.keys())
        if str(k).lstrip("-").isdigit()
    }
    naechste = max(
        [ledger.get("naechste_nr", 0), *(n + 1 for n in vergeben | historisch), 1]
    )

    neu: list[tuple[int, str]] = []
    for vorgang in posten:
        if isinstance(vorgang.get("nr"), int):
            continue
        vorgang["nr"] = naechste
        neu.append((naechste, vorgang.get("kurz") or vorgang.get("thread_key") or "?"))
        naechste += 1

    ledger["naechste_nr"] = naechste
    return ledger, neu


def tage_seit(datum: str | None, stichtag: str | None = None) -> int | None:
    """Tage zwischen `datum` (ISO) und dem Stichtag; None, wenn unlesbar oder leer.

    Der Stichtag wird hereingereicht statt aus der Systemuhr gelesen — dieselbe
    Entscheidung wie bei `render(ledger, heute)`. Ein Board, dessen Ausgabe von der
    Uhr abhaengt, laesst sich nicht pruefen.

    Bewusst tolerant gegen Unfug im Ledger: ein kaputtes Datum ist ein Befund der
    Pruefung, kein Absturz der Anzeige.
    """
    if not datum:
        return None
    try:
        gemessen = date.fromisoformat(str(datum)[:10])
        bezug = date.fromisoformat(stichtag[:10]) if stichtag else date.today()
    except (ValueError, TypeError):
        return None
    return (bezug - gemessen).days


def pruefe(ledger: dict) -> list[str]:
    """Invarianten pruefen. Rueckgabe ist die Liste der Verstoesse, leer = gut."""
    posten = vorgaenge_von(ledger)
    anker = lade(ANKER, {})
    links = lade(LINKS, {})
    befunde: list[str] = []

    ohne_nr = [v for v in posten if not isinstance(v.get("nr"), int)]
    for vorgang in ohne_nr:
        befunde.append(
            f"ohne Nummer: '{vorgang.get('kurz') or vorgang.get('thread_key')}' "
            f"— nicht adressierbar (--vergib-nummern)"
        )

    gesehen: dict[int, str] = {}
    for vorgang in posten:
        nr = vorgang.get("nr")
        if not isinstance(nr, int):
            continue
        if nr in gesehen:
            befunde.append(
                f"Nummer {nr} doppelt vergeben: '{gesehen[nr]}' und "
                f"'{vorgang.get('kurz')}' — die Anrede waere mehrdeutig"
            )
        gesehen[nr] = vorgang.get("kurz") or "?"

    naechste = ledger.get("naechste_nr")
    if isinstance(naechste, int):
        zu_hoch = [nr for nr in gesehen if nr >= naechste]
        if zu_hoch:
            befunde.append(
                f"naechste_nr={naechste} liegt nicht ueber allen vergebenen "
                f"Nummern {sorted(zu_hoch)} — Wiederverwendung droht"
            )
    elif posten:
        befunde.append("naechste_nr fehlt im Ledger — Wiederverwendung droht")

    gueltige_buckets = {b for b, _ in BUCKETS}
    for vorgang in posten:
        if vorgang.get("bucket") not in gueltige_buckets:
            befunde.append(
                f"#{vorgang.get('nr', '?')} '{vorgang.get('kurz')}': bucket="
                f"{vorgang.get('bucket')!r} — gehoert in keinen Abschnitt"
            )

    # Ohne Abschlussdatum ist ein erledigter Vorgang nicht einordenbar: Er faellt
    # weder aus dem Anzeigefenster heraus noch kann eine spaetere Nachlogik sagen,
    # seit wann er geschlossen ist.
    for vorgang in posten:
        if vorgang.get("bucket") != "erledigt":
            continue
        if tage_seit(vorgang.get("erledigt_am")) is None:
            befunde.append(
                f"#{vorgang.get('nr', '?')} '{vorgang.get('kurz')}': bucket="
                f"'erledigt', aber erledigt_am fehlt oder ist unlesbar "
                f"({vorgang.get('erledigt_am')!r})"
            )

    for vorgang in posten:
        nr = vorgang.get("nr")
        if not isinstance(nr, int) or vorgang.get("bucket") not in {"owner", "agent"}:
            continue
        if anker_zustand(nr, anker, links) == "fehlt":
            befunde.append(
                f"#{nr} '{vorgang.get('kurz')}': keine Mail verankert — "
                f"der Posten hat keinen Link (anker.py bzw. --register)"
            )

    for vorgang in posten:
        if not aktionen_fuer(vorgang):
            befunde.append(f"#{vorgang.get('nr', '?')}: keine naheliegende Aktion")

    return befunde


def _posten_zeile(vorgang: dict, anker: dict, links: dict) -> list[str]:
    nr = vorgang.get("nr")
    kurz = vorgang.get("kurz") or vorgang.get("next_trigger") or "(ohne Kurztext)"
    zustand = anker_zustand(nr, anker, links) if isinstance(nr, int) else "fehlt"
    link = link_fuer(nr, zustand) if isinstance(nr, int) else None

    # Der Aktionstext IST der Link — keine rohe URL, keine eigene Link-Spalte.
    kopf = f"[{kurz}]({link})" if link else f"{kurz} ⚠️ keine Mail verankert"
    meta = " · ".join(
        teil
        for teil in (
            (vorgang.get("konto") or "").upper(),
            vorgang.get("typ"),
            f"Frist {vorgang['frist']}" if vorgang.get("frist") else None,
        )
        if teil
    )

    zeilen = [f"**{nr} · {kopf}** — {meta}"]
    if vorgang.get("next_trigger"):
        zeilen.append(f"    {vorgang['next_trigger']}")
    aktionen = " · ".join(
        f"**{nr}{kuerzel}** {text}" for kuerzel, text in aktionen_fuer(vorgang)
    )
    zeilen.append(f"    Naheliegend: {aktionen}")
    return zeilen


def render(ledger: dict, heute: str) -> str:
    posten = vorgaenge_von(ledger)
    anker = lade(ANKER, {})
    links = lade(LINKS, {})

    aus: list[str] = [
        "# Mail-Action-Board",
        "",
        f"> **Stand:** {heute} · erzeugt von `{TOOL_VERSION}` aus"
        " `mail-vorgaenge.json`.",
        "> Nicht von Hand bearbeiten — Änderungen gehören in den Ledger.",
        "> **NUR lokal**: Adressen und Betreffe, nie ins Repo (Charta Art. 2).",
        "",
        "> **Anrede:** `7` meint den Vorgang, `7a` die Aktion darunter.",
        "> Nummern sind stabil und werden nie wiederverwendet — Lücken sind normal"
        " und gewollt.",
        "> Der Linktext ist der nächste Zug und führt über `/a/<nr>` in die Mail;"
        " ein Ordnerwechsel bricht ihn nicht.",
        "> **Nach außen entsteht immer nur ein Entwurf** — gesendet wird von Hand.",
        "",
    ]

    for bucket, ueberschrift in BUCKETS:
        gruppe = sorted(
            (v for v in posten if v.get("bucket") == bucket),
            key=lambda v: (v.get("nr") is None, v.get("nr") or 0),
        )
        aelter = 0
        if bucket == "erledigt":
            # Nur die juengsten Abschluesse zeigen. Alles davor bleibt in der Datei
            # (der Anker wird gebraucht), verschwindet aber aus der Ansicht — sonst
            # waechst der Abschnitt, der am wenigsten Aufmerksamkeit braucht, am
            # staerksten.
            frisch = []
            for vorgang in gruppe:
                tage = tage_seit(vorgang.get("erledigt_am"), heute)
                if tage is not None and tage > ERLEDIGT_FENSTER_TAGE:
                    aelter += 1
                else:
                    frisch.append(vorgang)
            gruppe = frisch
        if not gruppe and not aelter:
            continue
        aus += [f"## {ueberschrift}", ""]
        for vorgang in gruppe:
            aus += _posten_zeile(vorgang, anker, links)
            aus.append("")
        if aelter:
            aus += [
                f"_{aelter} weitere vor mehr als {ERLEDIGT_FENSTER_TAGE} Tagen "
                f"geschlossen — im Ledger, nicht im Board._",
                "",
            ]

    ohne = [v for v in posten if v.get("bucket") not in {b for b, _ in BUCKETS}]
    if ohne:
        aus += ["## ⚠️ Ohne Zuordnung — brauchen einen Bucket", ""]
        for vorgang in ohne:
            aus.append(
                f"- {vorgang.get('kurz') or vorgang.get('thread_key')} "
                f"(bucket={vorgang.get('bucket')!r})"
            )
        aus.append("")

    befunde = pruefe(ledger)
    if befunde:
        aus += ["## ⚠️ Befunde der Pruefung", ""]
        aus += [f"{i}. {b}" for i, b in enumerate(befunde, 1)]
        aus.append("")

    if REGELN.exists():
        aus += [REGELN.read_text(encoding="utf-8").rstrip(), ""]

    return "\n".join(aus).rstrip() + "\n"


def _katalog_zeigen(typ: str | None) -> None:
    typen = [typ] if typ else sorted(AKTIONEN_JE_TYP)
    for eintrag in typen:
        if eintrag not in AKTIONEN_JE_TYP:
            print(f"{eintrag}: (nicht im Katalog — Fallback greift)")
            aktionen = AKTIONEN_FALLBACK
        else:
            aktionen = AKTIONEN_JE_TYP[eintrag]
        print(f"{eintrag}:")
        for kuerzel, text in [*aktionen, *AKTIONEN_IMMER]:
            print(f"   {kuerzel}  {text}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pruefe", action="store_true", help="Invarianten pruefen")
    parser.add_argument(
        "--vergib-nummern", action="store_true", help="fehlende Nummern vergeben"
    )
    parser.add_argument("--render", action="store_true", help="Board erzeugen")
    parser.add_argument(
        "--nach", metavar="DATEI", help=f"Board schreiben (Standard: {BOARD})"
    )
    parser.add_argument(
        "--aktionen", nargs="?", const="", metavar="TYP", help="Aktionskatalog zeigen"
    )
    parser.add_argument("--ledger", metavar="DATEI", help="anderer Ledger-Pfad")
    args = parser.parse_args(argv)

    if args.aktionen is not None:
        _katalog_zeigen(args.aktionen or None)
        return 0

    ledger_pfad = Path(args.ledger) if args.ledger else LEDGER
    ledger = lade(ledger_pfad, {"vorgaenge": []})

    if args.vergib_nummern:
        ledger, neu = vergib_nummern(ledger)
        ledger_pfad.write_text(
            json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        if neu:
            for nr, kurz in neu:
                print(f"  #{nr}  {kurz}")
            print(f"{len(neu)} Nummer(n) vergeben, naechste_nr={ledger['naechste_nr']}")
        else:
            print("Alle Vorgaenge haben bereits eine Nummer.")
        return 0

    if args.render:
        text = render(ledger, date.today().isoformat())
        ziel = Path(args.nach) if args.nach else None
        if ziel:
            ziel.write_text(text, encoding="utf-8")
            print(f"Board geschrieben: {ziel}")
        else:
            sys.stdout.write(text)
        return 0

    if args.pruefe:
        befunde = pruefe(ledger)
        for befund in befunde:
            print(f"  {befund}")
        anzahl = len(vorgaenge_von(ledger))
        if befunde:
            print(f"❌ {len(befunde)} Befund(e) bei {anzahl} Vorgaengen.")
            return 1
        print(f"✅ {anzahl} Vorgaenge: Nummern eindeutig, verankert, mit Aktionen.")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
