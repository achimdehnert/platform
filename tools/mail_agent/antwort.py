#!/usr/bin/env python3
"""Antwort-Entwurf aus einer Vorlage je Vorgangstyp (V5 zu #3015 K4).

Der Owner entscheidet mit einem Wort („213 ja"). Bis dahin brauchte der Entwurf
danach noch drei Angaben, die nirgends zusammenstanden: an wen (Absender der
verankerten Mail), in welchem Strang (Message-ID) und in welchem Ton. Genau die
holt dieses Werkzeug aus Ledger und Anker zusammen und setzt den Text aus einer
Vorlage je Vorgangstyp.

Was es NICHT tut:

* Es sendet nicht. Es legt einen Entwurf an — `draft_mail.py` (HNU/AD per IMAP)
  bzw. `graph_mail.py --draft` (IIL per Graph) — und der Owner sendet selbst
  (Lotsen-Charta Art. 2).
* Es schreibt das Ledger nicht fort. Ein Entwurf ist noch kein Sachstand; in den
  Verlauf gehoert erst, was wirklich hinausging (Regel 0 des Mailcheck-Skills).
* Es haengt keine Signatur an. Die kommt aus der Rolle (`--role` / `--role`),
  damit Signatur und Ton aus derselben Entscheidung stammen.

Usage:
  antwort.py --vorgang 213 --art zusage --trocken
  antwort.py --vorgang 213 --art zusage
  antwort.py --vorgang 214 --art rueckfrage --hinweis "Termin erst ab KW 40"
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

HIER = Path(__file__).resolve().parent
VORLAGEN = HIER / "vorlagen"
LEDGER = Path.home() / ".claude" / "mail-vorgaenge.json"
ANKER_DATEI = Path.home() / ".claude" / "mail-anker.json"
LINKS_DATEI = Path.home() / ".claude" / "mail-links.json"

#: Vorlagen-Ordner fuer jeden Typ ohne eigenen Satz.
RUECKFALL_TYP = "vorgang"

ARTEN = ("zusage", "absage", "rueckfrage")

#: Konto -> Rolle aus der Registry (KONZ-033). `ad` fehlt bewusst: die Rolle
#: `dehnert_team` hat transport `smtp`, `draft_mail` bedient nur `imap_append`
#: und bricht mit einer Rolle dieser Art ab. AD-Entwuerfe entstehen deshalb
#: ohne Rolle — also ohne Signatur, die haengt der Owner selbst an.
ROLLE_JE_KONTO = {"hnu": "hnu", "iil": "iil"}

#: Bei IIL entscheidet zusaetzlich der Typ: Datenschutz-Beratung geht unter der
#: DSB-Rolle hinaus, alles andere unter der IIL-Rolle.
ROLLE_DSB = "dsb"

_PRAEFIX = re.compile(r"^\s*(?:re|aw|wg|fwd|fw)\s*(?:\[\d+\])?\s*:\s*", re.IGNORECASE)
_KLAMMER = re.compile(r"\([^)]*\)")
_PLATZHALTER = re.compile(r"\{(\w+)\}")
_ISO_DATUM = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")

#: Titel und Anreden, die vor dem Vornamen stehen koennen.
_TITEL = {
    "herr",
    "frau",
    "hr",
    "fr",
    "dr",
    "prof",
    "dipl",
    "ing",
    "mag",
    "med",
    "rer",
    "nat",
    "pol",
    "habil",
}

#: Woerter, die eine Organisation statt einer Person anzeigen — dann gibt es
#: keinen Vornamen zu gruessen, auch wenn zwei Woerter dastehen.
_ORGANISATION = {
    "amt",
    "landratsamt",
    "hochschule",
    "universitaet",
    "universität",
    "gmbh",
    "ag",
    "kg",
    "ohg",
    "e.v.",
    "ev",
    "kanzlei",
    "team",
    "support",
    "sekretariat",
    "verlag",
    "referat",
    "dezernat",
    "praesidium",
    "präsidium",
    "pruefungsamt",
    "prüfungsamt",
    "service",
    "buchhaltung",
    "vertrieb",
    "info",
}


class AntwortFehler(Exception):
    """Etwas fehlt, das der Owner setzen muss — mit Hinweis, wie."""


# --------------------------------------------------------------------------
# Reine Funktionen (testbar ohne Postfach)
# --------------------------------------------------------------------------


def vorlage_waehlen(typ: str, art: str, basis: Path = VORLAGEN) -> Path:
    """Vorlagendatei zu Typ und Art; Rueckfall auf den Typ ``vorgang``.

    Ein neuer Vorgangstyp bekommt damit sofort einen brauchbaren Text, ohne dass
    jemand erst eine Vorlage anlegen muss — der Rueckfall ist neutral formuliert.
    """
    if art not in ARTEN:
        raise ValueError(f"unbekannte Art '{art}' — erlaubt: {', '.join(ARTEN)}")
    eigen = basis / (typ or RUECKFALL_TYP) / f"{art}.md"
    if eigen.is_file():
        return eigen
    rueckfall = basis / RUECKFALL_TYP / f"{art}.md"
    if rueckfall.is_file():
        return rueckfall
    raise FileNotFoundError(f"weder {eigen} noch {rueckfall} vorhanden — Vorlage fehlt")


def rendern(vorlage_text: str, felder: dict[str, str]) -> str:
    """Platzhalter einsetzen; unbesetzte Platzhalter loeschen ihren Absatz.

    Kein Platzhalter bleibt stehen: ein ``{hinweis}`` im fertigen Entwurf waere
    genau der Fehler, den niemand vor dem Senden bemerkt.
    """

    def ersetze(treffer: re.Match[str]) -> str:
        return str(felder.get(treffer.group(1), "")).strip()

    text = _PLATZHALTER.sub(ersetze, vorlage_text)
    absaetze = [a.strip() for a in text.split("\n\n")]
    return "\n\n".join(a for a in absaetze if a).rstrip() + "\n"


def anrede_aus(gegenueber: str) -> str:
    """``gegenueber`` -> Anrede. Vorname erkennbar: „Hallo X,", sonst „Guten Tag,".

    Klammerzusaetze (``Lena Baumgartner (Masterarbeit)``) und Titel fallen weg.
    Ein einzelnes Wort ist kein Vorname — es ist meist ein Nachname oder eine
    Stelle; dann wird neutral gegruesst statt geraten.
    """
    kern = _KLAMMER.sub(" ", gegenueber or "")
    kern = kern.split("<")[0]
    if "," in kern:
        # „Baumgartner, Lena" — hinter dem Komma steht der Vorname.
        nachname, _, rest = kern.partition(",")
        kern = f"{rest} {nachname}"
    woerter = [w.strip(".,;:") for w in kern.split()]
    woerter = [w for w in woerter if w]
    if any(w.lower().strip(".") in _ORGANISATION for w in woerter):
        return "Guten Tag,"
    ohne_titel = [w for w in woerter if w.lower().strip(".") not in _TITEL]
    ohne_titel = [w for w in ohne_titel if len(w) > 1 and not w.isupper()]
    if len(ohne_titel) < 2:
        return "Guten Tag,"
    vorname = ohne_titel[0]
    if not re.fullmatch(r"[^\W\d_][\w'\-]*", vorname, re.UNICODE):
        return "Guten Tag,"
    return f"Hallo {vorname},"


def thema_aus(thread_key: str) -> str:
    """Betreff ohne Antwort-Praefixe — das, worum es geht."""
    thema = thread_key or ""
    while True:
        gekuerzt = _PRAEFIX.sub("", thema, count=1)
        if gekuerzt == thema:
            return thema.strip()
        thema = gekuerzt


def betreff_aus(thread_key: str, konto: str) -> str:
    """Antwort-Betreff. IIL/Outlook schreibt „AW:", IMAP-Konten „Re:".

    Der Praefix des Kontos zaehlt, nicht der der eingegangenen Mail: ein Strang
    mit zwei Praefixen sieht im Postfach des Owners falsch aus.
    """
    praefix = "AW: " if konto == "iil" else "Re: "
    return praefix + thema_aus(thread_key)


def frist_text(frist: str | None) -> str:
    """Frist als Satzteil. Ohne Frist ein neutraler Zeitraum statt eines Datums.

    Eine erfundene Zusage ist schlimmer als eine unscharfe: „in den naechsten
    zwei Wochen" kann der Owner stehen lassen oder ueberschreiben.
    """
    treffer = _ISO_DATUM.match((frist or "").strip())
    if not treffer:
        return "in den nächsten zwei Wochen"
    jahr, monat, tag = treffer.groups()
    return f"bis zum {tag}.{monat}.{jahr}"


def vorgang_laden(ledger: dict, nr: str) -> dict:
    for vorgang in ledger.get("vorgaenge", []):
        if str(vorgang.get("nr")) == str(nr):
            return vorgang
    raise AntwortFehler(f"kein Vorgang mit Nummer {nr} im Ledger")


def felder_bauen(vorgang: dict, hinweis: str = "") -> dict[str, str]:
    return {
        "anrede": anrede_aus(str(vorgang.get("gegenueber") or "")),
        "thema": thema_aus(str(vorgang.get("thread_key") or "")),
        "hinweis": (hinweis or "").strip(),
        "frist": frist_text(vorgang.get("frist")),
    }


def rolle_waehlen(konto: str, typ: str) -> str | None:
    if konto == "iil" and str(typ or "").startswith("dsb"):
        return ROLLE_DSB
    return ROLLE_JE_KONTO.get(konto)


def kommando_bauen(
    *,
    konto: str,
    an: str,
    betreff: str,
    body_datei: str,
    kategorie: str,
    message_id: str = "",
    graph_id: str = "",
    rolle: str | None = None,
) -> list[str]:
    """Aufruf des passenden Entwurfs-Werkzeugs — als Liste, nie als Shell-Zeile."""
    if konto == "iil":
        kommando = [
            sys.executable,
            str(HIER / "graph_mail.py"),
            "--draft",
            "--subject",
            betreff,
            "--body-file",
            body_datei,
        ]
        if graph_id:
            kommando += ["--reply-to", graph_id]
        else:
            kommando += ["--to", an]
        if kategorie:
            kommando += ["--category", kategorie]
    else:
        kommando = [
            sys.executable,
            str(HIER / "draft_mail.py"),
            "--account",
            konto,
            "--to",
            an,
            "--subject",
            betreff,
            "--body-file",
            body_datei,
        ]
        if message_id:
            kommando += ["--in-reply-to", message_id]
        if kategorie:
            kommando += ["--kategorie", kategorie]
    if rolle:
        kommando += ["--role", rolle]
    return kommando


# --------------------------------------------------------------------------
# Anker und Postfach
# --------------------------------------------------------------------------


def _lade_json(pfad: Path) -> dict:
    if not pfad.exists():
        return {}
    try:
        daten = json.loads(pfad.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return daten if isinstance(daten, dict) else {}


def anker_eintrag(anker: dict, nr: str) -> dict:
    eintrag = anker.get(str(nr))
    if not isinstance(eintrag, dict) or not eintrag.get("message_id"):
        raise AntwortFehler(
            f"Vorgang {nr} ist nicht verankert — ohne Anker fehlen Empfaenger und "
            f"Strang. Erst verankern:\n"
            f"  python3 tools/mail_agent/anker.py --setze {nr} "
            f"--account <konto> --folder INBOX --uid <UID>"
        )
    return eintrag


def _absender_per_imap(konto: str, message_id: str) -> str:
    """From der verankerten Mail (read-only). Getrennt, damit Tests ihn ersetzen."""
    from email.utils import parseaddr

    from draft_mail import hole_ursprung
    from read_mail import _resolve_config
    from send_mail import parse_env

    cfg_datei = _resolve_config(None, None if konto == "default" else konto)
    if not cfg_datei.exists():
        raise AntwortFehler(
            f"{cfg_datei} fehlt — Konto '{konto}' ist nicht eingerichtet"
        )
    ursprung, _ = hole_ursprung(parse_env(cfg_datei), message_id)
    return parseaddr(ursprung.get("From") or "")[1]


def empfaenger_aus(eintrag: dict, konto: str, holer=None) -> str:
    """Empfaenger: aus dem Anker, sonst aus dem From der verankerten Mail.

    Der Anker traegt die Adresse erst, seit sie hier gebraucht wird; fuer
    Altbestand wird sie einmal aus dem Postfach nachgesehen (BODY.PEEK, kein
    Schreibzugriff).
    """
    fuer_hand = str(eintrag.get("absender") or eintrag.get("von") or "").strip()
    if fuer_hand:
        return fuer_hand
    holer = holer or _absender_per_imap
    adresse = holer(konto, str(eintrag.get("message_id") or ""))
    if not adresse:
        raise AntwortFehler(
            "kein Absender ermittelbar — Adresse als Feld 'absender' in den "
            "Anker eintragen oder den Entwurf von Hand anlegen"
        )
    return adresse


def graph_id_aus(nr: str, eintrag: dict, links: dict) -> str:
    """Graph-Id fuer ``--reply-to``: aus dem Anker, sonst aus der Link-Registry."""
    aus_anker = str(eintrag.get("graph_id") or "").strip()
    if aus_anker:
        return aus_anker
    aus_links = links.get(str(nr))
    if isinstance(aus_links, dict):
        return str(aus_links.get("graph_id") or "").strip()
    return ""


# --------------------------------------------------------------------------
# Ablauf
# --------------------------------------------------------------------------


def _kategorie(ledger: dict, nr: str) -> str:
    try:
        from board import kategorie

        return kategorie(ledger, nr)
    except (ImportError, KeyError):
        return ""


def baue(args: argparse.Namespace) -> tuple[dict, str, str]:
    """Alles zusammentragen: (Kopfdaten, Body, Vorlagenpfad)."""
    ledger = _lade_json(Path(args.ledger).expanduser() if args.ledger else LEDGER)
    vorgang = vorgang_laden(ledger, args.vorgang)
    konto = str(vorgang.get("konto") or "hnu")
    typ = str(vorgang.get("typ") or RUECKFALL_TYP)

    anker = _lade_json(Path(args.anker).expanduser() if args.anker else ANKER_DATEI)
    eintrag = anker_eintrag(anker, args.vorgang)

    vorlage = vorlage_waehlen(typ, args.art, VORLAGEN)
    body = rendern(
        vorlage.read_text(encoding="utf-8"), felder_bauen(vorgang, args.hinweis)
    )

    links = _lade_json(Path(args.links).expanduser() if args.links else LINKS_DATEI)
    graph_id = graph_id_aus(args.vorgang, eintrag, links) if konto == "iil" else ""
    an = "" if graph_id else empfaenger_aus(eintrag, konto)

    kopf = {
        "konto": konto,
        "typ": typ,
        "an": an or "(Empfaenger setzt Graph aus der Ursprungsmail)",
        "an_roh": an,
        "betreff": betreff_aus(str(vorgang.get("thread_key") or ""), konto),
        "kategorie": _kategorie(ledger, args.vorgang),
        "message_id": str(eintrag.get("message_id") or ""),
        "graph_id": graph_id,
        "rolle": rolle_waehlen(konto, typ) or "",
    }
    return kopf, body, str(vorlage.relative_to(HIER))


def _trocken_ausgeben(kopf: dict, body: str, vorlage: str) -> None:
    print(f"Konto:     {kopf['konto']} ({kopf['typ']})")
    print(f"An:        {kopf['an']}")
    print(f"Betreff:   {kopf['betreff']}")
    print(f"Kategorie: {kopf['kategorie'] or '(keine)'}")
    print(f"Rolle:     {kopf['rolle'] or '(ohne Rolle, ohne Signatur)'}")
    print(f"Vorlage:   {vorlage}")
    print("-" * 60)
    print(body, end="")
    print("-" * 60)
    print("TROCKEN: nichts angelegt.")


def _entwurf_anlegen(kopf: dict, body: str) -> int:
    fd, pfad = tempfile.mkstemp(prefix="antwort-", suffix=".txt")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as datei:
            datei.write(body)
        kommando = kommando_bauen(
            konto=kopf["konto"],
            an=kopf["an_roh"],
            betreff=kopf["betreff"],
            body_datei=pfad,
            kategorie=kopf["kategorie"],
            message_id=kopf["message_id"],
            graph_id=kopf["graph_id"],
            rolle=kopf["rolle"] or None,
        )
        ergebnis = subprocess.run(kommando, check=False)
        return ergebnis.returncode
    finally:
        Path(pfad).unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--vorgang", required=True, metavar="NR")
    ap.add_argument("--art", required=True, choices=ARTEN)
    ap.add_argument(
        "--hinweis", default="", help="ein Satz, der zusaetzlich hineingehoert"
    )
    ap.add_argument("--trocken", action="store_true", help="nur zeigen, nichts anlegen")
    ap.add_argument(
        "--ledger", help=f"alternativer Vorgangs-Speicher (Default {LEDGER})"
    )
    ap.add_argument("--anker", help=f"alternative Ankerdatei (Default {ANKER_DATEI})")
    ap.add_argument(
        "--links", help=f"alternative Link-Registry (Default {LINKS_DATEI})"
    )
    args = ap.parse_args(argv)

    try:
        kopf, body, vorlage = baue(args)
    except (AntwortFehler, FileNotFoundError, ValueError) as fehler:
        print(f"FEHLER: {fehler}", file=sys.stderr)
        return 1

    if args.trocken:
        _trocken_ausgeben(kopf, body, vorlage)
        return 0
    return _entwurf_anlegen(kopf, body)


if __name__ == "__main__":
    sys.exit(main())
